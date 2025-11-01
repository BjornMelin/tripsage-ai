"""Tool Calling Service orchestrator for MCP tool calls."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

from tripsage_core.infrastructure.retry_policies import tripsage_retry
from tripsage_core.observability.otel import record_histogram, trace_span
from tripsage_core.services.business.tool_calling.core import (
    HandlerContext,
    ServiceFactory,
    format_accommodation_results,
    format_flight_results,
    format_maps_results,
    format_weather_results,
    sanitize_params,
    validate_accommodation_params,
    validate_flight_params,
    validate_maps_params,
    validate_weather_params,
)
from tripsage_core.services.business.tool_calling.models import (
    ToolCallError,
    ToolCallRequest,
    ToolCallResponse,
    ToolCallValidationResult,
)
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


if TYPE_CHECKING:
    from tripsage_core.services.infrastructure.database_service import (
        DatabaseService,
    )


logger = logging.getLogger(__name__)


class ToolCallService:
    """Service for executing MCP tool calls with validation and error handling."""

    def __init__(self, db: DatabaseService | None = None):
        """Initialize tool calling service.

        Args:
            db: Optional database service for Supabase-backed operations.
        """
        self.execution_history: list[ToolCallResponse] = []
        self.rate_limits: dict[str, list[float]] = {}
        self.db = db
        self._factory = ServiceFactory()

        safe_tables = {
            "users",
            "trips",
            "chat_sessions",
            "chat_messages",
            "flight_searches",
            "accommodation_searches",
            "flight_options",
            "accommodation_options",
            "trip_collaborators",
            "flights",
            "accommodations",
        }
        self._handler_context = HandlerContext(
            factory=self._factory, db=self.db, safe_tables=safe_tables
        )

        self._service_handlers: dict[
            str, Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
        ] = {
            "google_maps": self._handler_context.handle_google_maps,
            "weather": self._handler_context.handle_weather,
            "airbnb": self._handler_context.handle_airbnb,
            "duffel_flights": self._handler_context.handle_duffel_flights,
            "supabase": self._handler_context.handle_supabase,
            "memory": self._handler_context.handle_memory,
        }

        self._validation_handlers: dict[
            str, Callable[[dict[str, Any], str], Awaitable[list[str]]]
        ] = {
            "duffel_flights": validate_flight_params,
            "airbnb": validate_accommodation_params,
            "google_maps": validate_maps_params,
            "weather": validate_weather_params,
        }

        self._formatter_handlers: dict[
            str, Callable[[dict[str, Any] | None], Awaitable[dict[str, Any]]]
        ] = {
            "duffel_flights": format_flight_results,
            "airbnb": format_accommodation_results,
            "google_maps": format_maps_results,
            "weather": format_weather_results,
        }

    @trace_span(name="svc.tool_call.execute")
    @record_histogram("svc.tool_call.duration", unit="s")
    @tripsage_safe_execute()
    async def execute_tool_call(self, request: ToolCallRequest) -> ToolCallResponse:
        """Execute a single tool call with error handling.

        Args:
            request: Tool call request

        Returns:
            Tool call response

        Raises:
            ToolCallError: If tool call execution fails
        """
        start_time = time.time()

        try:
            validation = await self.validate_tool_call(request)
            if not validation.is_valid:
                return ToolCallResponse(
                    id=request.id,
                    status="error",
                    error=f"Validation failed: {'; '.join(validation.errors)}",
                    execution_time=time.time() - start_time,
                    service=request.service,
                    method=request.method,
                )

            if not await self._check_rate_limit(request.service):
                return ToolCallResponse(
                    id=request.id,
                    status="error",
                    error="Rate limit exceeded for service",
                    execution_time=time.time() - start_time,
                    service=request.service,
                    method=request.method,
                )

            sanitized_params: dict[str, Any] = validation.sanitized_params or {}
            result = await self._execute_with_retries(request, sanitized_params)

            response = ToolCallResponse(
                id=request.id,
                status="success",
                result=result,
                execution_time=time.time() - start_time,
                service=request.service,
                method=request.method,
            )

            await self._log_tool_call(request.service)
            self.execution_history.append(response)

            return response

        except TimeoutError:
            return ToolCallResponse(
                id=request.id,
                status="timeout",
                error=f"Tool call timed out after {request.timeout} seconds",
                execution_time=time.time() - start_time,
                service=request.service,
                method=request.method,
            )
        except Exception as e:
            logger.exception("Tool call execution failed for %s", request.id)
            return ToolCallResponse(
                id=request.id,
                status="error",
                error=str(e),
                execution_time=time.time() - start_time,
                service=request.service,
                method=request.method,
            )

    @trace_span(name="svc.tool_call.parallel")
    @tripsage_safe_execute()
    async def execute_parallel_tool_calls(
        self, requests: list[ToolCallRequest]
    ) -> list[ToolCallResponse]:
        """Execute multiple tool calls in parallel for efficiency.

        Args:
            requests: List of tool call requests

        Returns:
            List of tool call responses

        Raises:
            ToolCallError: If parallel execution fails
        """
        if not requests:
            return []

        try:
            logger.info("Executing %s tool calls in parallel", len(requests))

            tasks = [self.execute_tool_call(request) for request in requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            final_responses: list[ToolCallResponse] = [
                cast(ToolCallResponse, response)
                if not isinstance(response, Exception)
                else ToolCallResponse(
                    id=requests[i].id,
                    status="error",
                    error=f"Parallel execution failed: {response!s}",
                    execution_time=0.0,
                    service=requests[i].service,
                    method=requests[i].method,
                )
                for i, response in enumerate(responses)
            ]

            logger.info("Completed %s parallel tool calls", len(final_responses))
            return final_responses

        except Exception as e:
            logger.exception("Parallel tool call execution failed")
            raise ToolCallError(f"Parallel execution failed: {e!s}") from e

    async def validate_tool_call(
        self, request: ToolCallRequest
    ) -> ToolCallValidationResult:
        """Validate and sanitize tool call request.

        Args:
            request: Tool call request to validate

        Returns:
            Validation result with sanitized parameters
        """
        errors: list[str] = []
        sanitized_params = request.params.copy()

        validator = self._validation_handlers.get(request.service)
        if validator:
            errors.extend(await validator(sanitized_params, request.method))

        sanitized_params = sanitize_params(sanitized_params)

        return ToolCallValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized_params,
        )

    async def format_tool_result_for_chat(
        self, response: ToolCallResponse
    ) -> dict[str, Any]:
        """Format tool call result for chat display.

        Args:
            response: Tool call response

        Returns:
            Formatted result for chat interface
        """
        if response.status == "error":
            return {
                "type": "error",
                "message": f"Tool call failed: {response.error}",
                "service": response.service,
                "retry_available": True,
            }

        if response.status == "timeout":
            return {
                "type": "timeout",
                "message": f"Tool call timed out after {response.execution_time:.1f}s",
                "service": response.service,
                "retry_available": True,
            }

        formatter = self._formatter_handlers.get(response.service)
        if formatter:
            return await formatter(response.result)
        return {
            "type": "data",
            "service": response.service,
            "data": response.result,
            "execution_time": response.execution_time,
        }

    async def get_execution_history(
        self, limit: int = 100, service: str | None = None
    ) -> list[ToolCallResponse]:
        """Get tool call execution history.

        Args:
            limit: Maximum number of records to return
            service: Optional service filter

        Returns:
            List of tool call responses
        """
        history = self.execution_history

        if service:
            history = [r for r in history if r.service == service]

        return sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def get_error_statistics(self) -> dict[str, Any]:
        """Get error statistics and monitoring data.

        Returns:
            Dictionary with error statistics and system health metrics
        """
        total_calls = len(self.execution_history)
        success_calls = sum(1 for r in self.execution_history if r.status == "success")
        error_calls = sum(1 for r in self.execution_history if r.status == "error")
        timeout_calls = sum(1 for r in self.execution_history if r.status == "timeout")

        avg_execution_time = (
            sum(r.execution_time for r in self.execution_history) / total_calls
            if total_calls > 0
            else 0
        )

        return {
            "tool_calling_stats": {
                "total_calls": total_calls,
                "success_rate": success_calls / total_calls if total_calls > 0 else 0,
                "error_rate": error_calls / total_calls if total_calls > 0 else 0,
                "timeout_rate": timeout_calls / total_calls if total_calls > 0 else 0,
                "average_execution_time": avg_execution_time,
            },
            "rate_limit_status": {
                service: len(calls) for service, calls in self.rate_limits.items()
            },
        }

    async def _execute_with_retries(
        self, request: ToolCallRequest, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool call with retry and timeout handling."""
        attempts = max(1, request.retry_count)

        @tripsage_retry(
            attempts=attempts,
            max_delay=10.0,
            exceptions=(ConnectionError, OSError, TimeoutError),
            backoff_strategy="exponential",
        )
        async def _attempt() -> dict[str, Any]:
            coro = self._dispatch_service_call(request.service, request.method, params)
            if request.timeout is not None:
                timeout_msg = (
                    f"{request.service}/{request.method} timed out after "
                    f"{request.timeout}s"
                )
                try:
                    return await asyncio.wait_for(coro, timeout=request.timeout)
                except TimeoutError as exc:
                    raise TimeoutError(timeout_msg) from exc
            return await coro

        return await _attempt()

    async def _dispatch_service_call(
        self, service: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch service call to appropriate handler.

        Args:
            service: Service name to dispatch to
            method: Method name within the service
            params: Method parameters

        Returns:
            Service handler result

        Raises:
            ToolCallError: If service is not supported
        """
        handler = self._service_handlers.get(service)
        if handler is None:
            raise ToolCallError(f"Unsupported service: {service}")
        return await handler(method, params)

    async def _check_rate_limit(self, service: str) -> bool:
        """Check if service is within rate limits."""
        current_time = time.time()
        service_calls = self.rate_limits.get(service, [])

        service_calls = [t for t in service_calls if current_time - t < 60]

        if len(service_calls) >= 10:
            return False

        self.rate_limits[service] = service_calls
        return True

    async def _log_tool_call(self, service: str) -> None:
        """Log tool call for rate limiting."""
        current_time = time.time()
        if service not in self.rate_limits:
            self.rate_limits[service] = []
        self.rate_limits[service].append(current_time)


async def get_tool_calling_service() -> ToolCallService:
    """Get tool calling service instance for dependency injection.

    Returns:
        ToolCallService instance
    """
    from tripsage_core.services.infrastructure.database_service import (
        get_database_service,
    )

    db = await get_database_service()
    return ToolCallService(db=db)
