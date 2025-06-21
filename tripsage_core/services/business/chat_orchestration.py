"""
Chat Orchestration Service using direct database integration.

This service provides chat orchestration with direct database operations
for improved performance and simplified architecture.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError
from tripsage_core.mcp_abstraction.manager import MCPManager
from tripsage_core.services.business.tool_calling_service import (
    ToolCallRequest,
    ToolCallResponse,
    ToolCallService,
)
from tripsage_core.services.infrastructure import get_database_service
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ChatOrchestrationError(TripSageError):
    """Error raised when chat orchestration operations fail."""

    pass


class ChatOrchestrationService:
    """Orchestrate chat interactions with direct database operations."""

    def __init__(self):
        """Initialize the chat orchestration service."""
        self.database = None  # Will be initialized async
        self.mcp_manager = MCPManager()
        self.tool_call_service = ToolCallService(self.mcp_manager)
        self.logger = logger

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
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, dict):
            # For JSON/JSONB columns, properly escape
            json_str = json.dumps(value)
            escaped_json = json_str.replace("'", "''")
            return f"'{escaped_json}'::jsonb"
        else:
            # String values: escape single quotes and wrap in quotes
            str_value = str(value)
            escaped = str_value.replace("'", "''")
            return f"'{escaped}'"

    @with_error_handling()
    async def create_chat_session(self, user_id: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new chat session using Supabase MCP.

        Args:
            user_id: User ID for the session
            metadata: Optional session metadata

        Returns:
            Dictionary with session information

        Raises:
            ChatOrchestrationError: If session creation fails
        """
        try:
            self.logger.info(f"Creating chat session for user {user_id}")

            # Sanitize values to prevent SQL injection
            safe_user_id = self._sanitize_sql_value(user_id)
            safe_metadata = self._sanitize_sql_value(metadata or {})

            # Use properly formatted query with sanitized values
            query = f"""
                INSERT INTO chat_sessions (user_id, metadata)
                VALUES ({safe_user_id}, {safe_metadata}::jsonb)
                RETURNING id, created_at, updated_at
            """

            result = await self.mcp_manager.invoke(
                mcp_name="supabase",
                method_name="execute_sql",
                params={
                    "query": query,
                },
            )

            if not result:
                raise ChatOrchestrationError("No session data returned")

            session_data = {
                "session_id": result.get("id"),
                "user_id": user_id,
                "created_at": result.get("created_at"),
                "metadata": metadata or {},
                "status": "active",
            }

            self.logger.info(f"Chat session created: {session_data['session_id']}")
            return session_data

        except Exception as e:
            self.logger.error(f"Failed to create chat session: {e}")
            raise ChatOrchestrationError(f"Failed to create chat session: {str(e)}") from e

    @with_error_handling()
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save a chat message using Supabase MCP.

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
            self.logger.info(f"Saving message to session {session_id}")

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
            query = f"""
                INSERT INTO chat_messages (session_id, role, content, metadata)
                VALUES ({safe_session_id}, ",
                    f"{safe_role}, {safe_content}, {safe_metadata}::jsonb"
                )
                RETURNING id, created_at
            """

            result = await self.mcp_manager.invoke(
                mcp_name="supabase",
                method_name="execute_sql",
                params={
                    "query": query,
                },
            )

            message_data = {
                "message_id": result.get("id"),
                "session_id": session_id,
                "role": role,
                "content": content,
                "created_at": result.get("created_at"),
                "metadata": metadata or {},
            }

            self.logger.info(f"Message saved: {message_data['message_id']}")
            return message_data

        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise ChatOrchestrationError(f"Failed to save message: {str(e)}") from e

    @with_error_handling()
    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights using Duffel MCP.

        Args:
            params: Flight search parameters

        Returns:
            Dictionary with flight search results

        Raises:
            ChatOrchestrationError: If flight search fails
        """
        try:
            self.logger.info("Searching flights via Duffel MCP")

            result = await self.mcp_manager.invoke(
                mcp_name="duffel_flights",
                method_name="search_flights",
                params=params,
            )

            # Store search results in memory graph for future reference
            await self._store_search_result("flight", params, result)

            return {
                "search_type": "flights",
                "results": result,
                "timestamp": time.time(),
                "cached": False,
            }

        except Exception as e:
            self.logger.error(f"Flight search failed: {e}")
            raise ChatOrchestrationError(f"Flight search failed: {str(e)}") from e

    @with_error_handling()
    async def search_accommodations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search accommodations using Airbnb MCP.

        Args:
            params: Accommodation search parameters

        Returns:
            Dictionary with accommodation search results

        Raises:
            ChatOrchestrationError: If accommodation search fails
        """
        try:
            self.logger.info("Searching accommodations via Airbnb MCP")

            result = await self.mcp_manager.invoke(
                mcp_name="airbnb",
                method_name="search_properties",
                params=params,
            )

            # Store search results in memory graph
            await self._store_search_result("accommodation", params, result)

            return {
                "search_type": "accommodations",
                "results": result,
                "timestamp": time.time(),
                "cached": False,
            }

        except Exception as e:
            self.logger.error(f"Accommodation search failed: {e}")
            raise ChatOrchestrationError(f"Accommodation search failed: {str(e)}") from e

    @with_error_handling()
    async def get_location_info(self, location: str) -> Dict[str, Any]:
        """Get location information using Google Maps MCP.

        Args:
            location: Location query string

        Returns:
            Dictionary with location information

        Raises:
            ChatOrchestrationError: If location lookup fails
        """
        try:
            self.logger.info(f"Getting location info for: {location}")

            result = await self.mcp_manager.invoke(
                mcp_name="google_maps",
                method_name="geocode",
                params={"address": location},
            )

            # Store location data in memory graph
            if result:
                await self._store_location_data(location, result)

            return {
                "location": location,
                "data": result,
                "timestamp": time.time(),
            }

        except Exception as e:
            self.logger.error(f"Location lookup failed: {e}")
            raise ChatOrchestrationError(f"Location lookup failed: {str(e)}") from e

    @with_error_handling()
    async def execute_parallel_tools(self, tool_calls: List[Dict]) -> Dict[str, Any]:
        """Execute multiple tool calls in parallel using structured tool calling service

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            Dictionary with tool call results

        Raises:
            ChatOrchestrationError: If parallel execution fails
        """
        try:
            self.logger.info(f"Executing {len(tool_calls)} tool calls in parallel")

            # Convert to structured tool call requests
            requests = []
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
            responses = await self.tool_call_service.execute_parallel_tool_calls(requests)

            # Convert responses to legacy format for backward compatibility
            results = {}
            for response in responses:
                if response.status == "success":
                    results[response.id] = response.result
                else:
                    results[response.id] = {
                        "error": response.error,
                        "status": response.status,
                        "execution_time": response.execution_time,
                    }

            self.logger.info(f"Parallel tool execution completed: {len(results)} results")
            return {
                "results": results,
                "total_calls": len(tool_calls),
                "success_count": sum(1 for r in responses if r.status == "success"),
                "execution_summary": {
                    "total_time": max(r.execution_time for r in responses) if responses else 0,
                    "average_time": sum(r.execution_time for r in responses) / len(responses) if responses else 0,
                },
            }

        except Exception as e:
            self.logger.error(f"Parallel tool execution failed: {e}")
            raise ChatOrchestrationError(f"Parallel tool execution failed: {str(e)}") from e

    @with_error_handling()
    async def execute_structured_tool_call(
        self,
        service: str,
        method: str,
        params: Dict[str, Any],
        call_id: Optional[str] = None,
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

            response = await self.tool_call_service.execute_tool_call(request)
            return response

        except Exception as e:
            self.logger.error(f"Structured tool call failed: {e}")
            raise ChatOrchestrationError(f"Structured tool call failed: {str(e)}") from e

    @with_error_handling()
    async def format_tool_response_for_chat(self, response: ToolCallResponse) -> Dict[str, Any]:
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
            formatted = await self.tool_call_service.format_tool_result_for_chat(response)

            # Add orchestration-specific metadata
            formatted["orchestration_metadata"] = {
                "session_timestamp": time.time(),
                "execution_time": response.execution_time,
                "service_used": response.service,
                "method_called": response.method,
            }

            return formatted

        except Exception as e:
            self.logger.error(f"Tool response formatting failed: {e}")
            raise ChatOrchestrationError(f"Tool response formatting failed: {str(e)}") from e

    async def _execute_single_tool_call(self, tool_call: Dict) -> Any:
        """Execute a single tool call.

        Args:
            tool_call: Tool call dictionary

        Returns:
            Tool call result
        """
        service = tool_call.get("service")
        method = tool_call.get("method")
        params = tool_call.get("params", {})

        return await self.mcp_manager.invoke(
            mcp_name=service,
            method_name=method,
            params=params,
        )

    @with_error_handling()
    async def _store_search_result(self, search_type: str, params: Dict[str, Any], results: Any) -> None:
        """Store search results in memory graph for future reference.

        Args:
            search_type: Type of search (flight, accommodation, etc.)
            params: Search parameters
            results: Search results
        """
        try:
            # Create a search result entity in the memory graph
            entity = {
                "name": f"{search_type}_search_{int(time.time())}",
                "entityType": "SearchResult",
                "observations": [
                    f"search_type:{search_type}",
                    f"timestamp:{time.time()}",
                    f"params:{str(params)[:200]}",  # Truncate for storage
                    f"result_count:{len(results) if isinstance(results, list) else 1}",
                ],
            }

            await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="create_entities",
                params={"entities": [entity]},
            )

        except Exception as e:
            self.logger.warning(f"Failed to store search result in memory: {e}")

    @with_error_handling()
    async def _store_location_data(self, location: str, data: Dict[str, Any]) -> None:
        """Store location data in memory graph.

        Args:
            location: Location query
            data: Location data from Maps API
        """
        try:
            # Extract coordinates if available
            lat = data.get("lat", "unknown")
            lng = data.get("lng", "unknown")

            entity = {
                "name": location,
                "entityType": "Destination",
                "observations": [
                    f"latitude:{lat}",
                    f"longitude:{lng}",
                    "source:google_maps",
                    f"timestamp:{time.time()}",
                ],
            }

            await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="create_entities",
                params={"entities": [entity]},
            )

        except Exception as e:
            self.logger.warning(f"Failed to store location data in memory: {e}")

    @with_error_handling()
    async def get_chat_history(self, session_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get chat history using Supabase MCP.

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
            self.logger.info(f"Getting chat history for session {session_id}")

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
            query = f"""
                SELECT * FROM chat_messages 
                WHERE session_id = {safe_session_id}
                ORDER BY created_at DESC
                LIMIT {safe_limit} OFFSET {safe_offset}
            """

            result = await self.mcp_manager.invoke(
                mcp_name="supabase",
                method_name="execute_sql",
                params={
                    "query": query,
                },
            )

            messages = result if isinstance(result, list) else []

            self.logger.info(f"Retrieved {len(messages)} messages from history")
            return messages

        except Exception as e:
            self.logger.error(f"Failed to get chat history: {e}")
            raise ChatOrchestrationError(f"Failed to get chat history: {str(e)}") from e

    @with_error_handling()
    async def end_chat_session(self, session_id: str) -> bool:
        """End a chat session using Supabase MCP.

        Args:
            session_id: Chat session ID to end

        Returns:
            True if session was ended successfully

        Raises:
            ChatOrchestrationError: If session ending fails
        """
        try:
            self.logger.info(f"Ending chat session {session_id}")

            # Sanitize session_id to prevent SQL injection
            safe_session_id = self._sanitize_sql_value(session_id)

            query = f"""
                UPDATE chat_sessions 
                SET ended_at = NOW(), updated_at = NOW()
                WHERE id = {safe_session_id}
                RETURNING ended_at
            """

            result = await self.mcp_manager.invoke(
                mcp_name="supabase",
                method_name="execute_sql",
                params={"query": query},
            )

            if result:
                self.logger.info(f"Chat session {session_id} ended successfully")
                return True
            else:
                raise ChatOrchestrationError(f"Session {session_id} not found")

        except Exception as e:
            self.logger.error(f"Failed to end chat session: {e}")
            raise ChatOrchestrationError(f"Failed to end chat session: {str(e)}") from e


async def main():
    """Main function for testing chat orchestration service."""
    # Initialize the service
    service = ChatOrchestrationService()

    try:
        # Example: Create a chat session
        session = await service.create_chat_session(user_id=1)
        print(f"Created session: {session}")

        # Example: Search flights
        flight_params = {
            "origin": "NYC",
            "destination": "LAX",
            "departure_date": "2025-06-01",
            "return_date": "2025-06-08",
        }
        flights = await service.search_flights(flight_params)
        print(f"Flight search completed: {len(flights.get('results', []))} results")

        # Example: Get location info
        location_info = await service.get_location_info("Paris, France")
        print(f"Location info: {location_info}")

    except ChatOrchestrationError as e:
        print(f"Chat orchestration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
