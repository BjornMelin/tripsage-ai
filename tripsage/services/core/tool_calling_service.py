"""
Tool Calling Service for Phase 5 MCP Integration.

This service implements structured tool calling patterns for MCP servers
with validation, error handling, and result formatting.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.core.error_handling_service import (
    ErrorRecoveryService,
)
from tripsage.utils.decorators import with_error_handling
from tripsage.utils.error_handling import TripSageError
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class ToolCallError(TripSageError):
    """Error raised when tool calling fails."""

    pass


class ToolCallRequest(BaseModel):
    """Structured tool call request model."""

    id: str = Field(..., description="Unique identifier for the tool call")
    service: str = Field(..., description="MCP service name")
    method: str = Field(..., description="Method to invoke")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Method parameters"
    )
    timeout: Optional[float] = Field(default=30.0, description="Timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retries on failure")

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        """Validate service name."""
        allowed_services = [
            "duffel_flights",
            "airbnb",
            "google_maps",
            "weather",
            "supabase",
            "memory",
            "time",
            "firecrawl",
            "linkup",
        ]
        if v not in allowed_services:
            raise ValueError(
                f"Service '{v}' not in allowed services: {allowed_services}"
            )
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[float]) -> Optional[float]:
        """Validate timeout value."""
        if v is not None and (v <= 0 or v > 300):
            raise ValueError("Timeout must be between 0 and 300 seconds")
        return v


class ToolCallResponse(BaseModel):
    """Structured tool call response model."""

    id: str = Field(..., description="Tool call identifier")
    status: str = Field(..., description="Response status (success/error/timeout)")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Tool result data"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    service: str = Field(..., description="MCP service used")
    method: str = Field(..., description="Method invoked")
    timestamp: float = Field(
        default_factory=time.time, description="Response timestamp"
    )


class ToolCallValidationResult(BaseModel):
    """Tool call validation result."""

    is_valid: bool = Field(..., description="Whether tool call is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    sanitized_params: Optional[Dict[str, Any]] = Field(
        default=None, description="Sanitized parameters"
    )


class ToolCallService:
    """
    Service for executing MCP tool calls with validation and error handling.

    This service implements Phase 5 patterns for structured tool calling
    with proper validation, error handling, and result formatting.
    """

    def __init__(self, mcp_manager: MCPManager):
        """Initialize tool calling service.

        Args:
            mcp_manager: MCP manager instance for tool execution
        """
        self.mcp_manager = mcp_manager
        self.error_recovery = ErrorRecoveryService(mcp_manager)
        self.execution_history: List[ToolCallResponse] = []
        self.rate_limits: Dict[str, List[float]] = {}

    @with_error_handling
    async def execute_tool_call(self, request: ToolCallRequest) -> ToolCallResponse:
        """Execute a single tool call with comprehensive error handling.

        Args:
            request: Tool call request

        Returns:
            Tool call response

        Raises:
            ToolCallError: If tool call execution fails
        """
        start_time = time.time()

        try:
            # Validate and sanitize request
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

            # Check rate limits
            if not await self._check_rate_limit(request.service):
                return ToolCallResponse(
                    id=request.id,
                    status="error",
                    error="Rate limit exceeded for service",
                    execution_time=time.time() - start_time,
                    service=request.service,
                    method=request.method,
                )

            # Execute tool call with retries
            result = await self._execute_with_retries(
                request, validation.sanitized_params
            )

            response = ToolCallResponse(
                id=request.id,
                status="success",
                result=result,
                execution_time=time.time() - start_time,
                service=request.service,
                method=request.method,
            )

            # Log successful execution
            await self._log_tool_call(request.service)
            self.execution_history.append(response)

            return response

        except asyncio.TimeoutError:
            return ToolCallResponse(
                id=request.id,
                status="timeout",
                error=f"Tool call timed out after {request.timeout} seconds",
                execution_time=time.time() - start_time,
                service=request.service,
                method=request.method,
            )
        except Exception as e:
            logger.error(f"Tool call execution failed for {request.id}: {str(e)}")
            return ToolCallResponse(
                id=request.id,
                status="error",
                error=str(e),
                execution_time=time.time() - start_time,
                service=request.service,
                method=request.method,
            )

    @with_error_handling
    async def execute_parallel_tool_calls(
        self, requests: List[ToolCallRequest]
    ) -> List[ToolCallResponse]:
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
            logger.info(f"Executing {len(requests)} tool calls in parallel")

            # Create tasks for all requests
            tasks = [self.execute_tool_call(request) for request in requests]

            # Execute all tasks in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error responses
            processed_responses = []
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    error_response = ToolCallResponse(
                        id=requests[i].id,
                        status="error",
                        error=f"Parallel execution failed: {str(response)}",
                        execution_time=0.0,
                        service=requests[i].service,
                        method=requests[i].method,
                    )
                    processed_responses.append(error_response)
                else:
                    processed_responses.append(response)

            logger.info(f"Completed {len(processed_responses)} parallel tool calls")
            return processed_responses

        except Exception as e:
            logger.error(f"Parallel tool call execution failed: {str(e)}")
            raise ToolCallError(f"Parallel execution failed: {str(e)}") from e

    async def validate_tool_call(
        self, request: ToolCallRequest
    ) -> ToolCallValidationResult:
        """Validate and sanitize tool call request.

        Args:
            request: Tool call request to validate

        Returns:
            Validation result with sanitized parameters
        """
        errors = []
        sanitized_params = request.params.copy()

        # Service-specific validation
        if request.service == "duffel_flights":
            errors.extend(await self._validate_flight_params(sanitized_params))
        elif request.service == "airbnb":
            errors.extend(await self._validate_accommodation_params(sanitized_params))
        elif request.service == "google_maps":
            errors.extend(await self._validate_maps_params(sanitized_params))
        elif request.service == "weather":
            errors.extend(await self._validate_weather_params(sanitized_params))

        # General parameter sanitization
        sanitized_params = await self._sanitize_params(sanitized_params)

        return ToolCallValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized_params,
        )

    async def format_tool_result_for_chat(
        self, response: ToolCallResponse
    ) -> Dict[str, Any]:
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

        # Format successful results by service type
        if response.service == "duffel_flights":
            return await self._format_flight_results(response.result)
        elif response.service == "airbnb":
            return await self._format_accommodation_results(response.result)
        elif response.service == "google_maps":
            return await self._format_maps_results(response.result)
        elif response.service == "weather":
            return await self._format_weather_results(response.result)
        else:
            return {
                "type": "data",
                "service": response.service,
                "data": response.result,
                "execution_time": response.execution_time,
            }

    async def get_execution_history(
        self, limit: int = 100, service: Optional[str] = None
    ) -> List[ToolCallResponse]:
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

    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics and monitoring data.

        Returns:
            Dictionary with error statistics and system health metrics
        """
        base_stats = self.error_recovery.get_error_statistics()

        # Add tool calling specific metrics
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
            **base_stats,
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

    # Private helper methods

    async def _execute_with_retries(
        self, request: ToolCallRequest, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool call with comprehensive error recovery."""
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.mcp_manager.invoke(
                    service=request.service, method=request.method, params=params
                ),
                timeout=request.timeout,
            )

            # Store successful result for future fallback use
            await self.error_recovery.store_successful_result(
                request.service, request.method, params, result
            )

            return result

        except Exception as e:
            logger.warning(
                f"Tool call {request.id} failed, attempting error recovery: {str(e)}"
            )

            # Use error recovery service for comprehensive fallback handling
            fallback_result = await self.error_recovery.handle_mcp_error(
                error=e,
                service=request.service,
                method=request.method,
                params=params,
                retry_count=request.retry_count,
            )

            if fallback_result.success and fallback_result.result:
                logger.info(
                    f"Error recovery succeeded using "
                    f"{fallback_result.strategy_used.value}"
                )
                return fallback_result.result
            else:
                # All recovery attempts failed
                error_msg = (
                    f"Tool call failed after error recovery: "
                    f"{fallback_result.error or str(e)}"
                )
                raise ToolCallError(error_msg) from e

    async def _check_rate_limit(self, service: str) -> bool:
        """Check if service is within rate limits."""
        current_time = time.time()
        service_calls = self.rate_limits.get(service, [])

        # Remove calls older than 1 minute
        service_calls = [t for t in service_calls if current_time - t < 60]

        # Check if under limit (10 calls per minute per service)
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

    async def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters to remove potentially harmful content."""
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Remove potentially harmful characters
                sanitized[key] = value.replace("<", "").replace(">", "").strip()
            else:
                sanitized[key] = value
        return sanitized

    async def _validate_flight_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate flight search parameters."""
        errors = []

        required_fields = ["origin", "destination", "departure_date"]
        for field in required_fields:
            if field not in params:
                errors.append(f"Missing required field: {field}")

        return errors

    async def _validate_accommodation_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate accommodation search parameters."""
        errors = []

        required_fields = ["location", "check_in", "check_out"]
        for field in required_fields:
            if field not in params:
                errors.append(f"Missing required field: {field}")

        return errors

    async def _validate_maps_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate maps API parameters."""
        errors = []

        if "address" not in params and "location" not in params:
            errors.append("Either 'address' or 'location' is required")

        return errors

    async def _validate_weather_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate weather API parameters."""
        errors = []

        if "location" not in params:
            errors.append("'location' parameter is required")

        return errors

    async def _format_flight_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format flight search results for chat display."""
        return {
            "type": "flights",
            "title": "Flight Search Results",
            "data": result,
            "actions": ["book", "compare", "save"],
        }

    async def _format_accommodation_results(
        self, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format accommodation search results for chat display."""
        return {
            "type": "accommodations",
            "title": "Accommodation Options",
            "data": result,
            "actions": ["book", "favorite", "share"],
        }

    async def _format_maps_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format maps API results for chat display."""
        return {
            "type": "location",
            "title": "Location Information",
            "data": result,
            "actions": ["navigate", "save", "share"],
        }

    async def _format_weather_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format weather API results for chat display."""
        return {
            "type": "weather",
            "title": "Weather Information",
            "data": result,
            "actions": ["save", "alert"],
        }
