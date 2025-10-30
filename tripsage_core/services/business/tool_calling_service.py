"""Tool Calling Service for Phase 5 MCP Integration.

This service implements structured tool calling patterns for MCP servers
with validation, error handling, and result formatting.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from functools import partial
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field, field_validator

from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


if TYPE_CHECKING:
    from datetime import date, datetime

    from tripsage_core.services.business.memory_service import (
        ConversationMemoryRequest,
        MemorySearchRequest,
        MemoryService,
    )
    from tripsage_core.services.external_apis.duffel_provider import DuffelProvider
    from tripsage_core.services.infrastructure.database_service import (
        DatabaseService,
    )


logger = logging.getLogger(__name__)


class ToolCallError(TripSageError):
    """Error raised when tool calling fails."""


class ToolCallRequest(BaseModel):
    """Structured tool call request model."""

    id: str = Field(..., description="Unique identifier for the tool call")
    service: str = Field(..., description="MCP service name")
    method: str = Field(..., description="Method to invoke")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Method parameters"
    )
    timeout: float | None = Field(default=30.0, description="Timeout in seconds")
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
    def validate_timeout(cls, v: float | None) -> float | None:
        """Validate timeout value."""
        if v is not None and (v <= 0 or v > 300):
            raise ValueError("Timeout must be between 0 and 300 seconds")
        return v


class ToolCallResponse(BaseModel):
    """Structured tool call response model."""

    id: str = Field(..., description="Tool call identifier")
    status: str = Field(..., description="Response status (success/error/timeout)")
    result: dict[str, Any] | None = Field(default=None, description="Tool result data")
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    service: str = Field(..., description="MCP service used")
    method: str = Field(..., description="Method invoked")
    timestamp: float = Field(
        default_factory=time.time, description="Response timestamp"
    )


class ToolCallValidationResult(BaseModel):
    """Tool call validation result."""

    is_valid: bool = Field(..., description="Whether tool call is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    sanitized_params: dict[str, Any] | None = Field(
        default=None, description="Sanitized parameters"
    )


class ToolCallService:
    """Service for executing MCP tool calls with validation and error handling.

    This service implements Phase 5 patterns for structured tool calling
    with proper validation, error handling, and result formatting.
    """

    db: DatabaseService | None

    def __init__(self, db: DatabaseService | None = None):
        """Initialize tool calling service.

        Args:
            db: Optional database service for Supabase-backed operations.
        """
        # Error recovery removed - over-engineered stub
        self.execution_history: list[ToolCallResponse] = []
        self.rate_limits: dict[str, list[float]] = {}
        self.db = db
        self._memory_service: Any = None  # Lazy initialization

        # Minimal whitelist of safe tables for generic DB ops
        # Extend centrally as schema evolves; keep restrictive by default.
        self._safe_tables: set[str] = {
            "users",
            "trips",
            "chat_sessions",
            "chat_messages",
            "flight_searches",
            "accommodation_searches",
            "flight_options",
            "accommodation_options",
            "api_keys",
            "trip_collaborators",
            "flights",
            "accommodations",
        }

        self._service_handlers: dict[
            str, Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
        ] = {
            "google_maps": self._handle_google_maps,
            "weather": self._handle_weather,
            "airbnb": self._handle_airbnb,
            "duffel_flights": self._handle_duffel_flights,
            "supabase": self._handle_supabase,
            "memory": self._handle_memory,
        }

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

            # Log successful execution
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

            # Create tasks for all requests
            tasks = [self.execute_tool_call(request) for request in requests]

            # Execute all tasks in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error responses
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

        # Format successful results by service type
        formatters = {
            "duffel_flights": self._format_flight_results,
            "airbnb": self._format_accommodation_results,
            "google_maps": self._format_maps_results,
            "weather": self._format_weather_results,
        }
        formatter = formatters.get(response.service)
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
        base_stats = {}  # Initialize base stats instead of recursive call

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
        self, request: ToolCallRequest, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool call with retry and timeout handling."""
        attempts = max(1, request.retry_count)
        for attempt in range(1, attempts + 1):
            try:
                coroutine = self._dispatch_service_call(
                    request.service, request.method, params
                )
                if request.timeout is not None:
                    return await asyncio.wait_for(coroutine, timeout=request.timeout)
                return await coroutine
            except TimeoutError as exc:
                if attempt == attempts:
                    timeout_value = request.timeout
                    timeout_msg = (
                        f"{request.service}/{request.method} timed out after "
                        f"{timeout_value}s"
                        if timeout_value is not None
                        else f"{request.service}/{request.method} timed out"
                    )
                    raise TimeoutError(timeout_msg) from exc
                await self._apply_retry_backoff(attempt)
            except self._retryable_exception_types() as exc:
                if attempt == attempts:
                    raise ToolCallError(f"Tool call failed: {exc!s}") from exc
                await self._apply_retry_backoff(attempt)
        raise ToolCallError("Tool call failed after retries")

    async def _dispatch_service_call(
        self, service: str, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch to the appropriate service handler."""
        handler = self._service_handlers.get(service)
        if handler is None:
            raise ToolCallError(f"Unsupported service: {service}")
        return await handler(method, params)

    async def _handle_google_maps(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Google Maps service calls."""
        from tripsage_core.services.external_apis.google_maps_service import (
            GoogleMapsService,
        )

        maps_service = GoogleMapsService()
        normalized = method.lower()

        if normalized == "geocode":
            address = params.get("address") or params.get("location")
            if not address:
                raise ToolCallError("Missing address/location for geocode")
            places = await maps_service.geocode(address)
            return {"places": [place.model_dump() for place in places]}

        if normalized == "search_places":
            places = await maps_service.search_places(
                query=params.get("query", ""),
                location=params.get("location"),
                radius=params.get("radius"),
            )
            return {"places": [place.model_dump() for place in places]}

        if normalized == "get_directions":
            directions = await maps_service.get_directions(
                origin=params.get("origin", ""),
                destination=params.get("destination", ""),
                mode=params.get("mode", "driving"),
            )
            return {"directions": [direction.model_dump() for direction in directions]}

        raise ToolCallError(f"Unsupported google_maps method: {method}")

    async def _handle_weather(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle weather service calls."""
        from tripsage_core.services.external_apis.weather_service import WeatherService

        weather_service = WeatherService()
        normalized = self._normalize_method(
            method,
            {
                "current": "get_current_weather",
                "current_weather": "get_current_weather",
                "get_current_weather": "get_current_weather",
                "forecast": "get_forecast",
                "get_forecast": "get_forecast",
            },
        )

        if normalized == "get_current_weather":
            weather = await weather_service.get_current_weather(
                latitude=params.get("lat", 0),
                longitude=params.get("lon", 0),
                units=params.get("units", "metric"),
            )
            return {"weather": weather}

        if normalized == "get_forecast":
            forecast = await weather_service.get_forecast(
                latitude=params.get("lat", 0),
                longitude=params.get("lon", 0),
                days=params.get("days", 5),
            )
            return {"forecast": forecast}

        raise ToolCallError(f"Unsupported weather method: {method}")

    async def _handle_airbnb(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Airbnb service calls."""
        from tripsage_core.clients.airbnb_mcp_client import AirbnbMCPClient

        airbnb_client = AirbnbMCPClient()
        normalized = self._normalize_method(
            method,
            {
                "search_properties": "search",
                "search_listings": "search",
                "search": "search",
                "get_listing_details": "details",
                "listing_details": "details",
            },
        )

        if normalized == "search":
            location_param = params.get("location") or params.get("place")
            if not location_param:
                raise ToolCallError("location or place is required")
            listings = await airbnb_client.search_accommodations(
                location=location_param,
                checkin=params.get("checkin") or params.get("check_in"),
                checkout=params.get("checkout") or params.get("check_out"),
                adults=int(params.get("adults", params.get("guests", 1))),
                children=int(params.get("children", 0)),
                infants=int(params.get("infants", 0)),
                pets=int(params.get("pets", 0)),
                min_price=params.get("price_min") or params.get("min_price"),
                max_price=params.get("price_max") or params.get("max_price"),
                cursor=params.get("cursor"),
            )
            return {"listings": listings}

        if normalized == "details":
            listing_id_param = params.get("listing_id") or params.get("id")
            if not listing_id_param:
                raise ToolCallError("listing_id is required for listing details")
            details = await airbnb_client.get_listing_details(
                listing_id=listing_id_param,
                checkin=params.get("checkin") or params.get("check_in"),
                checkout=params.get("checkout") or params.get("check_out"),
                adults=int(params.get("adults", 1)),
                children=int(params.get("children", 0)),
                infants=int(params.get("infants", 0)),
                pets=int(params.get("pets", 0)),
            )
            return {"details": details}

        raise ToolCallError(f"Unsupported airbnb method: {method}")

    async def _handle_duffel_flights(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel flights service calls."""
        normalized = self._normalize_method(
            method,
            {
                "get_flight_details": "offer_details",
                "get_offer_details": "offer_details",
                "offer_details": "offer_details",
                "create_order": "create_order",
                "book_flight": "create_order",
                "create_booking": "create_order",
            },
        )

        provider = await self._create_duffel_provider(params)
        try:
            if normalized == "search_flights":
                return await self._duffel_search_flights(provider, params)
            if normalized == "offer_details":
                return await self._duffel_get_offer_details(provider, params)
            if normalized == "create_order":
                return await self._duffel_create_order(provider, params)
            raise ToolCallError(f"Unsupported duffel_flights method: {method}")
        except Exception as exc:
            raise ToolCallError(f"Duffel flights error: {exc!s}") from exc
        finally:
            with contextlib.suppress(Exception):
                await provider.aclose()

    async def _handle_supabase(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Supabase operations."""
        from tripsage_core.exceptions.exceptions import CoreDatabaseError
        from tripsage_core.services.infrastructure.database_service import (
            DatabaseService,
            get_database_service,
        )

        async def ensure_db() -> DatabaseService:
            """Ensure a database service is available."""
            if self.db is None:
                self.db = await get_database_service()
            assert isinstance(self.db, DatabaseService)
            return self.db

        def require_table() -> str:
            """Require a table for Supabase operations."""
            table = params.get("table")
            if not isinstance(table, str) or not table:
                raise ToolCallError("'table' parameter is required for supabase ops")
            if table not in self._safe_tables:
                raise ToolCallError(
                    f"Table '{table}' is not allowed for this operation"
                )
            return table

        try:
            dbi = await ensure_db()
            normalized = method.lower()
            handlers: dict[
                str,
                Callable[
                    [
                        DatabaseService,
                        dict[str, Any],
                        Callable[[], str],
                    ],
                    Awaitable[dict[str, Any]],
                ],
            ] = {
                "query": self._supabase_query,
                "insert": self._supabase_insert,
                "update": self._supabase_update,
                "delete": self._supabase_delete,
                "upsert": self._supabase_upsert,
                "search": self._supabase_vector_search,
            }

            handler = handlers.get(normalized)
            if handler is None:
                raise ToolCallError(f"Unsupported supabase method: {method}")

            return await handler(dbi, params, require_table)

        except CoreDatabaseError as exc:
            message = exc.message if hasattr(exc, "message") else str(exc)
            raise ToolCallError(f"Supabase error: {message}") from exc

    async def _handle_memory(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle memory operations."""
        from tripsage_core.services.business.memory_service import (
            ConversationMemoryRequest,
            MemorySearchRequest,
        )

        memory_service = await self._get_memory_service()

        user_id_val = params.get("user_id") or params.get("uid")
        if not user_id_val or not str(user_id_val).strip():
            raise ToolCallError("'user_id' is required for memory operations")
        user_id = str(user_id_val)

        normalized = self._normalize_method(
            method,
            {
                "store_fact": "store",
                "add_memory": "store",
                "add_fact": "store",
                "search_memories": "search",
                "search": "search",
                "retrieve_facts": "retrieve",
                "retrieve": "retrieve",
                "delete_fact": "delete",
                "delete": "delete",
                "update_fact": "update",
                "update": "update",
            },
        )

        handlers: dict[str, Callable[[], Awaitable[dict[str, Any]]]] = {
            "store": partial(
                self._memory_store,
                memory_service,
                user_id,
                params,
                ConversationMemoryRequest,
            ),
            "search": partial(
                self._memory_search,
                memory_service,
                user_id,
                params,
                MemorySearchRequest,
            ),
            "retrieve": partial(
                self._memory_retrieve,
                memory_service,
                user_id,
                params,
                MemorySearchRequest,
            ),
            "delete": partial(
                self._memory_delete,
                memory_service,
                user_id,
                params,
            ),
            "update": partial(
                self._memory_update,
                memory_service,
                user_id,
                params,
                ConversationMemoryRequest,
            ),
        }

        handler = handlers.get(normalized)
        if handler is None:
            raise ToolCallError(f"Unsupported memory method: {method}")

        return await handler()

    async def _memory_store(
        self,
        memory_service: MemoryService,
        user_id: str,
        params: dict[str, Any],
        conversation_cls: type[ConversationMemoryRequest],
    ) -> dict[str, Any]:
        """Handle memory store operations."""
        messages_param = params.get("messages")
        fact_text = (
            params.get("fact_text") or params.get("memory") or params.get("text")
        )
        if not messages_param and not fact_text:
            raise ToolCallError("Either 'messages' or 'fact_text' must be provided")

        if messages_param and isinstance(messages_param, list):
            messages = cast(list[dict[str, str]], messages_param)
        else:
            messages = [
                {
                    "role": "user",
                    "content": str(fact_text),
                }
            ]

        metadata = self._memory_build_metadata(params)
        conv_req = conversation_cls(
            messages=messages,
            session_id=params.get("session_id"),
            trip_id=params.get("trip_id"),
            metadata=metadata,
        )
        result = await memory_service.add_conversation_memory(
            user_id=user_id,
            memory_request=conv_req,
        )
        return {"result": result}

    async def _memory_search(
        self,
        memory_service: MemoryService,
        user_id: str,
        params: dict[str, Any],
        search_cls: type[MemorySearchRequest],
    ) -> dict[str, Any]:
        """Handle memory search operations."""
        query = params.get("query") or params.get("q")
        if not query or not str(query).strip():
            raise ToolCallError("'query' is required for search_memories")

        limit = int(params.get("limit", 5))
        filters = self._memory_filters_with_category(params)
        threshold = float(params.get("similarity_threshold", 0.3))
        search_req = search_cls(
            query=str(query),
            limit=limit,
            filters=filters,
            similarity_threshold=threshold,
        )
        items = await memory_service.search_memories(user_id, search_req)
        return {"results": [item.model_dump() for item in items]}

    async def _memory_retrieve(
        self,
        memory_service: MemoryService,
        user_id: str,
        params: dict[str, Any],
        search_cls: type[MemorySearchRequest],
    ) -> dict[str, Any]:
        """Handle memory retrieve operations."""
        query = params.get("query") or params.get("q") or "*"
        limit = int(params.get("limit", 10))
        filters = self._memory_filters_with_category(params)
        threshold = float(params.get("similarity_threshold", 0.0))
        search_req = search_cls(
            query=str(query),
            limit=limit,
            filters=filters,
            similarity_threshold=threshold,
        )
        items = await memory_service.search_memories(user_id, search_req)
        return {
            "results": [item.model_dump() for item in items],
            "count": len(items),
        }

    async def _memory_delete(
        self,
        memory_service: MemoryService,
        user_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle memory delete operations."""
        memory_ids = params.get("memory_ids") or params.get("ids")
        memory_id = params.get("memory_id") or params.get("id")
        ids: list[str] | None
        if isinstance(memory_ids, list):
            typed_ids = cast(list[Any], memory_ids)
            ids = [str(item) for item in typed_ids]
        elif memory_id:
            ids = [str(memory_id)]
        else:
            ids = None
        result = await memory_service.delete_user_memories(user_id, ids)
        return {"result": result}

    async def _memory_update(
        self,
        memory_service: MemoryService,
        user_id: str,
        params: dict[str, Any],
        conversation_cls: type[ConversationMemoryRequest],
    ) -> dict[str, Any]:
        """Handle memory update operations."""
        memory_id = params.get("memory_id") or params.get("id")
        if not memory_id:
            raise ToolCallError("'memory_id' is required for update_fact")

        await memory_service.delete_user_memories(user_id, [str(memory_id)])

        fact_text = (
            params.get("fact_text") or params.get("memory") or params.get("text")
        )
        if not fact_text:
            raise ToolCallError("Updated 'fact_text' (or 'memory'/'text') is required")
        metadata = {
            **self._memory_build_metadata(params),
            "supersedes_id": str(memory_id),
        }
        conv_req = conversation_cls(
            messages=[{"role": "user", "content": str(fact_text)}],
            session_id=params.get("session_id"),
            trip_id=params.get("trip_id"),
            metadata=metadata,
        )
        result = await memory_service.add_conversation_memory(
            user_id=user_id,
            memory_request=conv_req,
        )
        return {"result": result}

    def _memory_build_metadata(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build memory metadata with category."""
        metadata = cast(dict[str, Any], params.get("metadata") or {})
        category = params.get("category")
        if category:
            metadata = {**metadata, "category": category}
        return metadata

    def _memory_filters_with_category(self, params: dict[str, Any]) -> dict[str, Any]:
        """Build memory filters with category."""
        filters = cast(dict[str, Any], params.get("filters") or {})
        category = params.get("category")
        if category:
            filters = {**filters, "categories": [category]}
        return filters

    async def _create_duffel_provider(self, params: dict[str, Any]) -> DuffelProvider:
        """Create a Duffel provider instance."""
        from tripsage_core.config import get_env_var
        from tripsage_core.services.external_apis.duffel_provider import (
            DuffelProvider,
        )

        access_token = cast(
            str | None,
            params.get("access_token")
            or params.get("api_key")
            or await get_env_var("DUFFEL_ACCESS_TOKEN")
            or await get_env_var("DUFFEL_API_KEY"),
        )
        if not access_token:
            raise ToolCallError(
                "Duffel access token is required "
                "(set access_token or DUFFEL_ACCESS_TOKEN)"
            )
        return DuffelProvider(access_token=access_token)

    async def _duffel_search_flights(
        self, provider: DuffelProvider, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel search flights operations."""
        from tripsage_core.models.mappers.flights_mapper import (
            duffel_offer_to_service_offer,
        )

        origin = cast(str | None, params.get("origin"))
        destination = cast(str | None, params.get("destination"))
        if not origin or not destination:
            raise ToolCallError("origin and destination are required")

        departure_date = self._parse_date_like(
            params.get("departure_date"), "departure_date"
        )
        return_date_val = params.get("return_date")
        return_date = (
            self._parse_date_like(return_date_val, "return_date")
            if return_date_val is not None
            else None
        )

        passengers = self._build_duffel_passengers(params)

        cabin_class = cast(str | None, params.get("cabin_class"))
        max_connections = cast(
            int | None,
            params.get("max_connections") or params.get("max_stops"),
        )
        currency = cast(str, params.get("currency", "USD"))

        offers = await provider.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            max_connections=max_connections,
            currency=currency,
        )
        canonical = [
            duffel_offer_to_service_offer(offer).model_dump() for offer in offers
        ]
        return {"offers": canonical}

    async def _duffel_get_offer_details(
        self, provider: DuffelProvider, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel get offer details operations."""
        from tripsage_core.models.mappers.flights_mapper import (
            duffel_offer_to_service_offer,
        )

        offer_id = cast(str | None, params.get("offer_id") or params.get("id"))
        if not offer_id:
            raise ToolCallError("offer_id is required for offer details")
        offer = await provider.get_offer_details(offer_id)
        if offer is None:
            return {"offer": None}
        return {"offer": duffel_offer_to_service_offer(offer).model_dump()}

    async def _duffel_create_order(
        self, provider: DuffelProvider, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle Duffel create order operations."""
        offer_id = cast(str | None, params.get("offer_id") or params.get("id"))
        if not offer_id:
            raise ToolCallError("offer_id is required to create an order")
        passengers = cast(list[dict[str, Any]] | None, params.get("passengers"))
        if not passengers:
            raise ToolCallError(
                "passengers list with identity/contact is required to create an order"
            )
        payment = cast(
            dict[str, Any],
            params.get("payment", {"type": "balance", "amount": 0}),
        )
        order = await provider.create_order(
            offer_id=offer_id, passengers=passengers, payment=payment
        )
        return {"order": order}

    async def _supabase_query(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase query operations."""
        table = require_table()
        columns = params.get("columns", "*")
        filters = cast(dict[str, Any], params.get("filters") or {})
        order_by = params.get("order_by")
        limit = params.get("limit")
        offset = params.get("offset")
        rows = await dbi.select(
            table,
            columns,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        return {"rows": rows}

    async def _supabase_insert(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase insert operations."""
        table = require_table()
        data = cast(dict[str, Any], params.get("data") or {})
        user_id = params.get("user_id")
        rows = await dbi.insert(table, data, user_id)
        return {"rows": rows, "row_count": len(rows)}

    async def _supabase_update(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase update operations."""
        table = require_table()
        update_data = cast(
            dict[str, Any], params.get("data") or params.get("update") or {}
        )
        filters = cast(dict[str, Any], params.get("filters") or {})
        user_id = params.get("user_id")
        rows = await dbi.update(table, update_data, filters, user_id)
        return {"rows": rows, "row_count": len(rows)}

    async def _supabase_delete(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase delete operations."""
        table = require_table()
        filters = cast(dict[str, Any], params.get("filters") or {})
        user_id = params.get("user_id")
        rows = await dbi.delete(table, filters, user_id)
        return {"rows": rows, "row_count": len(rows)}

    async def _supabase_upsert(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase upsert operations."""
        table = require_table()
        data = cast(dict[str, Any], params.get("data") or {})
        on_conflict = params.get("on_conflict")
        user_id = params.get("user_id")
        rows = await dbi.upsert(table, data, on_conflict, user_id)
        return {"rows": rows, "row_count": len(rows)}

    async def _supabase_vector_search(
        self,
        dbi: DatabaseService,
        params: dict[str, Any],
        require_table: Callable[[], str],
    ) -> dict[str, Any]:
        """Handle Supabase vector search operations."""
        table = require_table()
        vector_column = params.get("vector_column") or params.get("embedding_column")
        if not isinstance(vector_column, str) or not vector_column:
            raise ToolCallError("'vector_column' is required for vector search")
        query_vector = params.get("query_vector") or params.get("embedding")
        if not isinstance(query_vector, list):
            raise ToolCallError("'query_vector' must be a list of numbers")
        typed_vector = cast(list[Any], query_vector)
        if not all(isinstance(value, (int, float)) for value in typed_vector):
            raise ToolCallError("'query_vector' must be a list of numbers")
        limit = params.get("limit", 10)
        similarity_threshold = params.get("similarity_threshold")
        filters = cast(dict[str, Any] | None, params.get("filters"))
        user_id = params.get("user_id")
        rows = await dbi.vector_search(
            table,
            vector_column,
            [float(x) for x in cast(list[int | float], typed_vector)],
            limit=limit,
            similarity_threshold=similarity_threshold,
            filters=filters,
            user_id=user_id,
        )
        return {"rows": rows, "row_count": len(rows)}

    def _retryable_exception_types(self) -> tuple[type[Exception], ...]:
        """Return exception types considered retryable."""
        return (ConnectionError, OSError)

    async def _apply_retry_backoff(self, attempt: int) -> None:
        """Sleep using a simple linear backoff between retries."""
        delay = min(0.5 * attempt, 2.0)
        await asyncio.sleep(delay)

    @staticmethod
    def _normalize_method(method: str, aliases: dict[str, str]) -> str:
        """Normalize method name using provided aliases."""
        lowered = method.lower()
        return aliases.get(lowered, lowered)

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        """Safely coerce a value to int, returning a default on failure."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_duffel_passengers(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Build Duffel passenger list from explicit entries or counts."""
        passengers_param = cast(list[dict[str, Any]] | None, params.get("passengers"))
        if passengers_param is not None:
            return passengers_param

        adults = self._to_int(params.get("adults", params.get("guests", 1)), 1)
        children = self._to_int(params.get("children", 0), 0)
        infants = self._to_int(params.get("infants", 0), 0)
        return (
            [{"type": "adult"} for _ in range(max(0, adults))]
            + [{"type": "child"} for _ in range(max(0, children))]
            + [{"type": "infant"} for _ in range(max(0, infants))]
        )

    @staticmethod
    def _parse_date_like(value: Any, field_name: str) -> date | datetime:
        """Parse date-like values coming from parameters."""
        from datetime import date, datetime

        if value is None:
            raise ToolCallError(f"{field_name} must be provided")
        if isinstance(value, (date, datetime)):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                try:
                    return date.fromisoformat(value)
                except ValueError as exc:
                    raise ToolCallError(f"Invalid date format: {value!r}") from exc
        raise ToolCallError(f"{field_name} must be a date/datetime or ISO string")

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

    async def _get_memory_service(self) -> Any:
        """Lazily initialize and cache the MemoryService instance.

        Returns:
            MemoryService: The cached memory service instance.
        """
        # Local import to avoid import at module load
        from tripsage_core.services.business.memory_service import MemoryService

        if self._memory_service is None:
            self._memory_service = MemoryService()
        return cast("MemoryService", self._memory_service)

    async def _sanitize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Sanitize parameters to remove potentially harmful content."""
        sanitized: dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Remove potentially harmful characters
                sanitized[key] = value.replace("<", "").replace(">", "").strip()
            else:
                sanitized[key] = value
        return sanitized

    async def _validate_flight_params(self, params: dict[str, Any]) -> list[str]:
        """Validate flight search parameters."""
        required_fields = ["origin", "destination", "departure_date"]
        return [
            f"Missing required field: {field}"
            for field in required_fields
            if field not in params
        ]

    async def _validate_accommodation_params(self, params: dict[str, Any]) -> list[str]:
        """Validate accommodation search parameters."""
        required_fields = ["location", "check_in", "check_out"]
        return [
            f"Missing required field: {field}"
            for field in required_fields
            if field not in params
        ]

    async def _validate_maps_params(self, params: dict[str, Any]) -> list[str]:
        """Validate maps API parameters."""
        if "address" not in params and "location" not in params:
            return ["Either 'address' or 'location' is required"]
        return []

    async def _validate_weather_params(self, params: dict[str, Any]) -> list[str]:
        """Validate weather API parameters."""
        if "location" not in params:
            return ["'location' parameter is required"]
        return []

    async def _format_flight_results(
        self, result: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Format flight search results for chat display."""
        data: dict[str, Any] = result or {}
        return {
            "type": "flights",
            "title": "Flight Search Results",
            "data": data,
            "actions": ["book", "compare", "save"],
        }

    async def _format_accommodation_results(
        self, result: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Format accommodation search results for chat display."""
        data: dict[str, Any] = result or {}
        return {
            "type": "accommodations",
            "title": "Accommodation Options",
            "data": data,
            "actions": ["book", "favorite", "share"],
        }

    async def _format_maps_results(
        self, result: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Format maps API results for chat display."""
        data: dict[str, Any] = result or {}
        return {
            "type": "location",
            "title": "Location Information",
            "data": data,
            "actions": ["navigate", "save", "share"],
        }

    async def _format_weather_results(
        self, result: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Format weather API results for chat display."""
        data: dict[str, Any] = result or {}
        return {
            "type": "weather",
            "title": "Weather Information",
            "data": data,
            "actions": ["save", "alert"],
        }


# Dependency function for FastAPI
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
