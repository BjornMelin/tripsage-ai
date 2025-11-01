"""Chat Orchestration Service (FINAL-ONLY, no MCPBridge).

- Database operations via ``DatabaseService`` (Supabase RPC/SQL)
- Flights via ``FlightService`` with optional Duffel provider
- Accommodations via ``AirbnbMCPClient`` (only MCP-backed service retained)
- Google Maps via ``GoogleMapsService``
- Memory via ``MemoryService``
"""

import json
import time
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from typing import Any, cast

import httpx

from tripsage_core.clients.airbnb_mcp_client import AirbnbMCPClient
from tripsage_core.config import get_env_var
from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError
from tripsage_core.services.business.flight_service import (
    CabinClass,
    FlightSearchRequest,
    FlightService,
)
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    get_memory_service,
)
from tripsage_core.services.business.tool_calling_service import (
    ToolCallRequest,
    ToolCallResponse,
    ToolCallService,
)
from tripsage_core.services.external_apis.duffel_provider import DuffelProvider
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
)
from tripsage_core.services.infrastructure import get_database_service
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class ChatOrchestrationError(TripSageError):
    """Error raised when chat orchestration operations fail."""


class ChatOrchestrationService:
    """Orchestrate chat interactions with direct database operations."""

    def __init__(self):
        """Initialize the chat orchestration service."""
        self.database = None  # Will be initialized asynchronously
        # ToolCallService no longer accepts MCPBridge; keep for formatting helpers
        self.tool_call_service = ToolCallService()
        self.logger = logger
        # Lazy-initialized external services
        self._gmaps: GoogleMapsService | None = None
        self._airbnb: AirbnbMCPClient | None = None

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        """Best-effort conversion to int with a safe fallback.

        Args:
            value: Incoming value (possibly None or string)
            default: Default to use when conversion fails

        Returns:
            Integer value or the provided default.
        """
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    async def _ensure_database(self):
        """Ensure database service is initialized."""
        if self.database is None:
            self.database = await get_database_service()

    def _sanitize_sql_value(self, value: Any) -> str:
        """Sanitize SQL values to prevent injection attacks.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized SQL-safe string
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, dict):
            # For JSON/JSONB columns, properly escape
            json_str = json.dumps(value)
            escaped_json = json_str.replace("'", "''")
            return f"'{escaped_json}'::jsonb"
        # String values: escape single quotes and wrap in quotes
        str_value = str(value)
        escaped = str_value.replace("'", "''")
        return f"'{escaped}'"

    @tripsage_safe_execute()
    async def create_chat_session(
        self, user_id: int, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a new chat session using DatabaseService.

        Args:
            user_id: User ID for the session
            metadata: Optional session metadata

        Returns:
            Dictionary with session information

        Raises:
            ChatOrchestrationError: If session creation fails
        """
        try:
            self.logger.info("Creating chat session for user %s", user_id)

            # Sanitize values to prevent SQL injection
            safe_user_id = self._sanitize_sql_value(user_id)
            safe_metadata = self._sanitize_sql_value(metadata or {})

            # Use properly formatted query with sanitized values
            query = (
                "INSERT INTO chat_sessions (user_id, metadata) "
                f"VALUES ({safe_user_id}, {safe_metadata}::jsonb) "
                "RETURNING id, created_at, updated_at"
            )

            # Execute via DatabaseService
            await self._ensure_database()
            assert self.database is not None
            rows = await self.database.execute_sql(sql=query)
            if not rows:
                raise ChatOrchestrationError("No session data returned")
            result = rows[0]
            session_data = {
                "session_id": result.get("id"),
                "user_id": user_id,
                "created_at": result.get("created_at"),
                "metadata": metadata or {},
                "status": "active",
            }

            self.logger.info("Chat session created: %s", session_data["session_id"])
            return session_data

        except Exception as e:
            self.logger.exception("Failed to create chat session")
            raise ChatOrchestrationError(f"Failed to create chat session: {e!s}") from e

    @tripsage_safe_execute()
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save a chat message using DatabaseService.

        Args:
            session_id: Chat session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Returns:
            Dictionary with saved message information

        Raises:
            ChatOrchestrationError: If message saving fails
        """
        try:
            self.logger.info("Saving message to session %s", session_id)

            # Validate role to prevent injection
            valid_roles = {"user", "assistant", "system"}
            if role not in valid_roles:
                raise ChatOrchestrationError(f"Invalid role: {role}")

            # Sanitize values to prevent SQL injection
            safe_session_id = self._sanitize_sql_value(session_id)
            safe_role = self._sanitize_sql_value(role)
            safe_content = self._sanitize_sql_value(content)
            safe_metadata = self._sanitize_sql_value(metadata or {})

            # Use properly formatted query with sanitized values
            query = (
                "INSERT INTO chat_messages (session_id, role, content, metadata) "
                f"VALUES ({safe_session_id}, {safe_role}, {safe_content}, "
                f"{safe_metadata}::jsonb) RETURNING id, created_at"
            )

            await self._ensure_database()
            assert self.database is not None
            rows = await self.database.execute_sql(sql=query)
            if not rows:
                raise ChatOrchestrationError("No message data returned")
            result = rows[0]

            message_data = {
                "message_id": result.get("id"),
                "session_id": session_id,
                "role": role,
                "content": content,
                "created_at": result.get("created_at"),
                "metadata": metadata or {},
            }

            self.logger.info("Message saved: %s", message_data["message_id"])
            return message_data

        except Exception as e:
            self.logger.exception("Failed to save message")
            raise ChatOrchestrationError(f"Failed to save message: {e!s}") from e

    @tripsage_safe_execute()
    async def search_flights(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search flights using direct provider/FlightService (no MCP).

        Args:
            params: Flight search parameters

        Returns:
            Dictionary with flight search results

        Raises:
            ChatOrchestrationError: If flight search fails
        """
        try:
            self.logger.info("Searching flights via direct provider")

            # Build FlightSearchRequest from untyped params
            def _get(key: str, default: Any | None = None) -> Any | None:
                return params.get(key, default)

            # Required fields validation for static typing and runtime safety
            origin_val = _get("origin")
            destination_val = _get("destination")
            departure_val = _get("departure_date")
            if not origin_val or not destination_val or departure_val is None:
                raise ChatOrchestrationError(
                    "origin, destination, and departure_date are required"
                )

            fs_request = FlightSearchRequest(
                origin=cast(str, origin_val),
                destination=cast(str, destination_val),
                departure_date=cast(date | datetime, departure_val),
                return_date=_get("return_date"),
                adults=self._to_int(_get("adults", 1), 1),
                children=self._to_int(_get("children", 0), 0),
                infants=self._to_int(_get("infants", 0), 0),
                cabin_class=CabinClass(_get("cabin_class", CabinClass.ECONOMY.value)),
                max_stops=(
                    self._to_int(_get("max_connections") or _get("max_stops"), 0)
                    if (_get("max_connections") or _get("max_stops")) is not None
                    else None
                ),
                currency=cast(str, _get("currency", "USD")),
                passengers=None,
                max_price=_get("max_price"),
                preferred_airlines=_get("preferred_airlines"),
                excluded_airlines=_get("excluded_airlines"),
                trip_id=_get("trip_id"),
            )

            # Optionally wire Duffel provider if access token present
            duffel_token = await get_env_var("DUFFEL_ACCESS_TOKEN")
            external = (
                DuffelProvider(access_token=duffel_token) if duffel_token else None
            )

            await self._ensure_database()
            assert self.database is not None  # Ensure database is initialized
            flight_service = FlightService(
                database_service=self.database, external_flight_service=external
            )

            search_flights = cast(
                Callable[[FlightSearchRequest], Awaitable[Any]],
                flight_service.search_flights,
            )
            search_response = await search_flights(fs_request)
            # Convert to plain dict for chat payloads
            result = search_response.model_dump()

            # Store search results in memory graph for future reference
            store_search = cast(
                Callable[[str, dict[str, Any], Any], Awaitable[None]],
                self._store_search_result,
            )
            await store_search("flight", params, result)

            return {
                "search_type": "flights",
                "results": result,
                "timestamp": time.time(),
                "cached": bool(result.get("cached", False)),
            }

        except Exception as e:
            self.logger.exception("Flight search failed")
            raise ChatOrchestrationError(f"Flight search failed: {e!s}") from e

    @tripsage_safe_execute()
    async def search_accommodations(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search accommodations using Airbnb MCP client directly.

        Args:
            params: Accommodation search parameters

        Returns:
            Dictionary with accommodation search results

        Raises:
            ChatOrchestrationError: If accommodation search fails
        """
        try:
            self.logger.info("Searching accommodations via Airbnb MCP client")

            # Lazy init client
            if self._airbnb is None:
                self._airbnb = AirbnbMCPClient()

            location_value = params.get("location") or params.get("place")
            if not isinstance(location_value, str) or not location_value.strip():
                raise ChatOrchestrationError(
                    "'location' is required for accommodation search"
                )

            listings = await self._airbnb.search_accommodations(
                location=location_value,
                checkin=params.get("checkin") or params.get("check_in"),
                checkout=params.get("checkout") or params.get("check_out"),
                adults=self._to_int(params.get("adults", params.get("guests", 1)), 1),
                children=self._to_int(params.get("children", 0), 0),
                infants=self._to_int(params.get("infants", 0), 0),
                pets=self._to_int(params.get("pets", 0), 0),
                min_price=(params.get("price_min") or params.get("min_price")),
                max_price=(params.get("price_max") or params.get("max_price")),
                cursor=params.get("cursor"),
            )
            result = {"listings": listings}

            # Store search results in memory graph
            store_search = cast(
                Callable[[str, dict[str, Any], Any], Awaitable[None]],
                self._store_search_result,
            )
            await store_search("accommodation", params, result)

            return {
                "search_type": "accommodations",
                "results": result,
                "timestamp": time.time(),
                "cached": False,
            }

        except Exception as e:
            self.logger.exception("Accommodation search failed")
            raise ChatOrchestrationError(f"Accommodation search failed: {e!s}") from e

    @tripsage_safe_execute()
    async def get_location_info(self, location: str) -> dict[str, Any]:
        """Get location information using Google Maps service.

        Args:
            location: Location query string

        Returns:
            Dictionary with location information

        Raises:
            ChatOrchestrationError: If location lookup fails
        """
        try:
            self.logger.info("Getting location info for: %s", location)

            if self._gmaps is None:
                self._gmaps = GoogleMapsService()

            places = await self._gmaps.geocode(location)
            # Convert to plain dicts for chat payloads
            data = [p.model_dump() for p in places]

            # Store location data in memory
            if data:
                store_loc = cast(
                    Callable[[str, dict[str, Any]], Awaitable[None]],
                    self._store_location_data,
                )
                await store_loc(location, data[0])

            return {"location": location, "data": data, "timestamp": time.time()}

        except Exception as e:
            self.logger.exception("Location lookup failed")
            raise ChatOrchestrationError(f"Location lookup failed: {e!s}") from e

    @tripsage_safe_execute()
    async def execute_parallel_tools(
        self, tool_calls: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Execute multiple tool calls in parallel using structured tool call service.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            Dictionary with tool call results

        Raises:
            ChatOrchestrationError: If parallel execution fails
        """
        try:
            self.logger.info("Executing %s tool calls in parallel", len(tool_calls))

            # Convert to structured tool call requests
            requests: list[ToolCallRequest] = []
            for i, tool_call in enumerate(tool_calls):
                request = ToolCallRequest(
                    id=tool_call.get("id", f"tool_call_{i}"),
                    service=tool_call.get("service", "unknown"),
                    method=tool_call.get("method", "unknown"),
                    params=tool_call.get("params", {}),
                    timeout=tool_call.get("timeout", 30.0),
                    retry_count=tool_call.get("retry_count", 3),
                )
                requests.append(request)

            # Execute using structured tool calling service
            exec_parallel = cast(
                Callable[[list[ToolCallRequest]], Awaitable[list[ToolCallResponse]]],
                self.tool_call_service.execute_parallel_tool_calls,
            )
            responses: list[ToolCallResponse] = await exec_parallel(requests)

            # Convert responses to a simple mapping for callers
            results: dict[str, Any] = {}
            for response in responses:
                if response.status == "success":
                    results[response.id] = response.result
                else:
                    results[response.id] = {
                        "error": response.error,
                        "status": response.status,
                        "execution_time": response.execution_time,
                    }

            self.logger.info(
                "Parallel tool execution completed: %s results", len(results)
            )
            return {
                "results": results,
                "total_calls": len(tool_calls),
                "success_count": sum(1 for r in responses if r.status == "success"),
                "execution_summary": {
                    "total_time": max(r.execution_time for r in responses)
                    if responses
                    else 0,
                    "average_time": sum(r.execution_time for r in responses)
                    / len(responses)
                    if responses
                    else 0,
                },
            }

        except Exception as e:
            self.logger.exception("Parallel tool execution failed")
            raise ChatOrchestrationError(
                f"Parallel tool execution failed: {e!s}"
            ) from e

    @tripsage_safe_execute()
    async def execute_structured_tool_call(
        self,
        service: str,
        method: str,
        params: dict[str, Any],
        call_id: str | None = None,
    ) -> ToolCallResponse:
        """Execute a single structured tool call.

        Args:
            service: MCP service name
            method: Method to invoke
            params: Method parameters
            call_id: Optional call identifier

        Returns:
            Structured tool call response

        Raises:
            ChatOrchestrationError: If tool call fails
        """
        try:
            request = ToolCallRequest(
                id=call_id or f"call_{int(time.time())}",
                service=service,
                method=method,
                params=params,
            )

            exec_one = cast(
                Callable[[ToolCallRequest], Awaitable[ToolCallResponse]],
                self.tool_call_service.execute_tool_call,
            )
            return await exec_one(request)

        except Exception as e:
            self.logger.exception("Structured tool call failed")
            raise ChatOrchestrationError(f"Structured tool call failed: {e!s}") from e

    @tripsage_safe_execute()
    async def format_tool_response_for_chat(
        self, response: ToolCallResponse
    ) -> dict[str, Any]:
        """Format tool response for chat interface display.

        Args:
            response: Tool call response

        Returns:
            Formatted response for chat UI

        Raises:
            ChatOrchestrationError: If formatting fails
        """
        try:
            # Use tool calling service to format the response
            formatted = await self.tool_call_service.format_tool_result_for_chat(
                response
            )

            # Add orchestration-specific metadata
            formatted["orchestration_metadata"] = {
                "session_timestamp": time.time(),
                "execution_time": response.execution_time,
                "service_used": response.service,
                "method_called": response.method,
            }

            return formatted

        except Exception as e:
            self.logger.exception("Tool response formatting failed")
            raise ChatOrchestrationError(
                f"Tool response formatting failed: {e!s}"
            ) from e

    async def _execute_single_tool_call(self, tool_call: dict[str, Any]) -> Any:
        """Execute a single tool call.

        Args:
            tool_call: Tool call dictionary

        Returns:
            Tool call result
        """
        service = tool_call.get("service")
        method = tool_call.get("method")
        params = tool_call.get("params", {})

        # Minimal direct execution shim; expand as needed by callers
        if service == "airbnb":
            if self._airbnb is None:
                self._airbnb = AirbnbMCPClient()
            if method in ("search_properties", "search_listings"):
                return {
                    "listings": await self._airbnb.search_accommodations(
                        location=params.get("location") or params.get("place"),
                        checkin=params.get("checkin") or params.get("check_in"),
                        checkout=params.get("checkout") or params.get("check_out"),
                        adults=int(params.get("adults", params.get("guests", 1))),
                        children=int(params.get("children", 0)),
                        infants=int(params.get("infants", 0)),
                        pets=int(params.get("pets", 0)),
                        min_price=(params.get("price_min") or params.get("min_price")),
                        max_price=(params.get("price_max") or params.get("max_price")),
                        cursor=params.get("cursor"),
                    )
                }
            if method in ("get_listing_details", "listing_details"):
                if not params.get("listing_id") and not params.get("id"):
                    raise ChatOrchestrationError(
                        "listing_id (or id) is required for listing details"
                    )
                return await self._airbnb.get_listing_details(
                    listing_id=params.get("listing_id") or params.get("id"),
                    checkin=params.get("checkin") or params.get("check_in"),
                    checkout=params.get("checkout") or params.get("check_out"),
                    adults=int(params.get("adults", 1)),
                    children=int(params.get("children", 0)),
                    infants=int(params.get("infants", 0)),
                    pets=int(params.get("pets", 0)),
                )

        if service == "google_maps":
            if self._gmaps is None:
                self._gmaps = GoogleMapsService()
            if method == "geocode":
                addr = params.get("address") or params.get("location")
                if not addr:
                    raise ChatOrchestrationError("Missing address/location for geocode")
                places = await self._gmaps.geocode(addr)
                return [p.model_dump() for p in places]

        if service == "supabase":
            await self._ensure_database()
            sql = params.get("query") or params.get("sql")
            if not sql:
                raise ChatOrchestrationError("Missing SQL query for supabase.execute")
            assert self.database is not None
            return await self.database.execute_sql(sql=sql)

        if service == "duffel_flights":
            search_flights2 = cast(
                Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
                self.search_flights,
            )
            return await search_flights2(params)

        if service == "memory":
            # Map to memory service conversation entry
            mem = await get_memory_service()
            req = ConversationMemoryRequest(
                messages=[
                    {
                        "role": "system",
                        "content": f"Memory entity created: {json.dumps(params)[:500]}",
                    }
                ],
                session_id=None,
                trip_id=None,
                metadata=None,
            )
            add_conv = cast(
                Callable[[str, ConversationMemoryRequest], Awaitable[dict[str, Any]]],
                mem.add_conversation_memory,
            )
            return await add_conv("system", req)

        raise ChatOrchestrationError(
            f"Unsupported tool call service/method: {service}.{method}"
        )

    @tripsage_safe_execute()
    async def _store_search_result(
        self, search_type: str, params: dict[str, Any], results: Any
    ) -> None:
        """Store search results using MemoryService for future reference.

        Args:
            search_type: Type of search (flight, accommodation, etc.)
            params: Search parameters
            results: Search results
        """
        try:
            mem = await get_memory_service()
            count = len(cast(list[Any], results)) if isinstance(results, list) else 1
            summary = (
                f"{search_type} search stored (count={count}): {str(params)[:180]}"
            )
            req = ConversationMemoryRequest(
                messages=[{"role": "system", "content": summary}],
                session_id=None,
                trip_id=None,
                metadata={"search_type": search_type},
            )
            add_conv2 = cast(
                Callable[[str, ConversationMemoryRequest], Awaitable[dict[str, Any]]],
                mem.add_conversation_memory,
            )
            await add_conv2("system", req)

        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
            TripSageError,
        ) as e:
            self.logger.warning("Failed to store search result in memory: %s", e)
        except Exception as e:  # noqa: BLE001
            self.logger.warning("Unexpected error storing search result: %s", e)

    @tripsage_safe_execute()
    async def _store_location_data(self, location: str, data: dict[str, Any]) -> None:
        """Store location data using MemoryService.

        Args:
            location: Location query
            data: Location data from Maps API
        """
        try:
            # Extract coordinates if available
            lat = data.get("lat", "unknown")
            lng = data.get("lng", "unknown")

            mem = await get_memory_service()
            msg = f"Location stored: {location} (lat={lat}, lng={lng}) via Google Maps"
            req = ConversationMemoryRequest(
                messages=[{"role": "system", "content": msg}],
                session_id=None,
                trip_id=None,
                metadata={"source": "google_maps", "location": location},
            )
            add_conv3 = cast(
                Callable[[str, ConversationMemoryRequest], Awaitable[dict[str, Any]]],
                mem.add_conversation_memory,
            )
            await add_conv3("system", req)

        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValueError,
            TypeError,
            TripSageError,
        ) as e:
            self.logger.warning("Failed to store location data in memory: %s", e)
        except Exception as e:  # noqa: BLE001
            self.logger.warning("Unexpected error storing location data: %s", e)

    @tripsage_safe_execute()
    async def get_chat_history(
        self, session_id: str, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get chat history using DatabaseService.

        Args:
            session_id: Chat session ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of message dictionaries

        Raises:
            ChatOrchestrationError: If history retrieval fails
        """
        try:
            self.logger.info("Getting chat history for session %s", session_id)

            # Validate and sanitize inputs
            if limit < 1 or limit > 100:
                raise ChatOrchestrationError("Limit must be between 1 and 100")
            if offset < 0:
                raise ChatOrchestrationError("Offset must be non-negative")

            # Sanitize values to prevent SQL injection
            safe_session_id = self._sanitize_sql_value(session_id)
            safe_limit = self._sanitize_sql_value(limit)
            safe_offset = self._sanitize_sql_value(offset)

            # Use properly formatted query with sanitized values
            query = (
                "SELECT * FROM chat_messages "
                f"WHERE session_id = {safe_session_id} "
                "ORDER BY created_at DESC "
                f"LIMIT {safe_limit} OFFSET {safe_offset}"
            )

            await self._ensure_database()
            assert self.database is not None
            rows = await self.database.execute_sql(sql=query)
            messages: list[dict[str, Any]] = cast(list[dict[str, Any]], rows)

            self.logger.info("Retrieved %s messages from history", len(messages))
            return messages

        except Exception as e:
            self.logger.exception("Failed to get chat history")
            raise ChatOrchestrationError(f"Failed to get chat history: {e!s}") from e

    @tripsage_safe_execute()
    async def end_chat_session(self, session_id: str) -> bool:
        """End a chat session using DatabaseService.

        Args:
            session_id: Chat session ID to end

        Returns:
            True if session was ended successfully

        Raises:
            ChatOrchestrationError: If session ending fails
        """
        try:
            self.logger.info("Ending chat session %s", session_id)

            # Sanitize session_id to prevent SQL injection
            safe_session_id = self._sanitize_sql_value(session_id)

            query = (
                "UPDATE chat_sessions "
                "SET ended_at = NOW(), updated_at = NOW() "
                f"WHERE id = {safe_session_id} RETURNING ended_at"
            )

            await self._ensure_database()
            assert self.database is not None
            rows = await self.database.execute_sql(sql=query)
            if rows:
                self.logger.info("Chat session %s ended successfully", session_id)
                return True
            raise ChatOrchestrationError(f"Session {session_id} not found")

        except Exception as e:
            self.logger.exception("Failed to end chat session")
            raise ChatOrchestrationError(f"Failed to end chat session: {e!s}") from e


# Note: Standalone demo runner removed to keep library import-only and
# avoid static-analysis confusion around decorated async methods.
