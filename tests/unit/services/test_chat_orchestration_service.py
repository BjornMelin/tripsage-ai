"""
Comprehensive tests for Chat Orchestration Service - Phase 5 Implementation.

This test suite validates the chat orchestration with MCP tool calling,
session management, and structured service integration for Phase 5.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.chat_orchestration import (
    ChatOrchestrationError,
    ChatOrchestrationService,
)
from tripsage.services.tool_calling_service import (
    ToolCallResponse,
    ToolCallService,
)


class TestChatOrchestrationService:
    """Test suite for ChatOrchestrationService Phase 5 implementation."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager."""
        return AsyncMock(spec=MCPManager)

    @pytest.fixture
    def mock_tool_call_service(self):
        """Create mock tool calling service."""
        return AsyncMock(spec=ToolCallService)

    @pytest.fixture
    def chat_orchestration_service(self, mock_mcp_manager):
        """Create ChatOrchestrationService instance."""
        service = ChatOrchestrationService(mock_mcp_manager)
        # Replace tool_call_service with mock for testing
        service.tool_call_service = AsyncMock(spec=ToolCallService)
        return service

    @pytest.mark.asyncio
    async def test_create_chat_session_success(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test successful chat session creation using Supabase MCP."""
        # Arrange
        user_id = 123
        metadata = {"client": "web", "version": "1.0"}
        expected_session_id = "session_456"

        mock_mcp_manager.invoke.return_value = {
            "id": expected_session_id,
            "created_at": "2025-01-23T10:00:00Z",
            "updated_at": "2025-01-23T10:00:00Z",
        }

        # Act
        result = await chat_orchestration_service.create_chat_session(user_id, metadata)

        # Assert
        assert result["session_id"] == expected_session_id
        assert result["user_id"] == user_id
        assert result["status"] == "active"
        assert result["metadata"] == metadata

        # Verify MCP call
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="supabase",
            method_name="execute_sql",
            params={
                "query": """
                INSERT INTO chat_sessions (user_id, metadata)
                VALUES ($1, $2)
                RETURNING id, created_at, updated_at
            """,
            },
        )

    @pytest.mark.asyncio
    async def test_create_chat_session_failure(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test chat session creation failure handling."""
        # Arrange
        mock_mcp_manager.invoke.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(
            ChatOrchestrationError, match="Failed to create chat session"
        ):
            await chat_orchestration_service.create_chat_session(123, {})

    @pytest.mark.asyncio
    async def test_save_message_success(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test successful message saving using Supabase MCP."""
        # Arrange
        session_id = "session_123"
        role = "user"
        content = "Hello, I need help planning a trip"
        metadata = {"timestamp": "2025-01-23T10:00:00Z"}
        expected_message_id = "msg_456"

        mock_mcp_manager.invoke.return_value = {
            "id": expected_message_id,
            "created_at": "2025-01-23T10:00:00Z",
        }

        # Act
        result = await chat_orchestration_service.save_message(
            session_id, role, content, metadata
        )

        # Assert
        assert result["message_id"] == expected_message_id
        assert result["session_id"] == session_id
        assert result["role"] == role
        assert result["content"] == content
        assert result["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_search_flights_mcp_integration(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test flight search using Duffel MCP integration."""
        # Arrange
        flight_params = {
            "origin": "NYC",
            "destination": "LAX",
            "departure_date": "2025-06-01",
            "return_date": "2025-06-08",
        }

        expected_flight_results = {
            "offers": [
                {
                    "id": "offer_1",
                    "total_amount": "250.00",
                    "slices": [{"origin": "NYC", "destination": "LAX"}],
                }
            ]
        }

        mock_mcp_manager.invoke.return_value = expected_flight_results

        # Act
        result = await chat_orchestration_service.search_flights(flight_params)

        # Assert
        assert result["search_type"] == "flights"
        assert result["results"] == expected_flight_results
        assert result["cached"] is False
        assert "timestamp" in result

        # Verify MCP calls
        assert mock_mcp_manager.invoke.call_count == 2  # Flight search + memory storage

        # Check flight search call
        flight_call = mock_mcp_manager.invoke.call_args_list[0]
        assert flight_call[1]["mcp_name"] == "duffel_flights"
        assert flight_call[1]["method_name"] == "search_flights"
        assert flight_call[1]["params"] == flight_params

    @pytest.mark.asyncio
    async def test_search_accommodations_mcp_integration(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test accommodation search using Airbnb MCP integration."""
        # Arrange
        accommodation_params = {
            "location": "Los Angeles",
            "check_in": "2025-06-01",
            "check_out": "2025-06-05",
            "guests": 2,
        }

        expected_accommodation_results = {
            "properties": [
                {"id": "prop_1", "name": "Downtown Apartment", "price": 150},
                {"id": "prop_2", "name": "Beach House", "price": 200},
            ]
        }

        mock_mcp_manager.invoke.return_value = expected_accommodation_results

        # Act
        result = await chat_orchestration_service.search_accommodations(
            accommodation_params
        )

        # Assert
        assert result["search_type"] == "accommodations"
        assert result["results"] == expected_accommodation_results
        assert result["cached"] is False

        # Verify MCP call
        accommodation_call = mock_mcp_manager.invoke.call_args_list[0]
        assert accommodation_call[1]["mcp_name"] == "airbnb"
        assert accommodation_call[1]["method_name"] == "search_properties"
        assert accommodation_call[1]["params"] == accommodation_params

    @pytest.mark.asyncio
    async def test_get_location_info_mcp_integration(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test location information retrieval using Google Maps MCP."""
        # Arrange
        location = "Paris, France"
        expected_location_data = {
            "lat": 48.8566,
            "lng": 2.3522,
            "formatted_address": "Paris, France",
            "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
        }

        mock_mcp_manager.invoke.return_value = expected_location_data

        # Act
        result = await chat_orchestration_service.get_location_info(location)

        # Assert
        assert result["location"] == location
        assert result["data"] == expected_location_data
        assert "timestamp" in result

        # Verify MCP calls
        location_call = mock_mcp_manager.invoke.call_args_list[0]
        assert location_call[1]["mcp_name"] == "google_maps"
        assert location_call[1]["method_name"] == "geocode"
        assert location_call[1]["params"] == {"address": location}

    @pytest.mark.asyncio
    async def test_execute_parallel_tools_with_structured_service(
        self, chat_orchestration_service
    ):
        """Test parallel tool execution using structured tool calling service."""
        # Arrange
        tool_calls = [
            {
                "id": "flight_search",
                "service": "duffel_flights",
                "method": "search_flights",
                "params": {"origin": "NYC", "destination": "LAX"},
            },
            {
                "id": "weather_check",
                "service": "weather",
                "method": "get_weather",
                "params": {"location": "Los Angeles"},
            },
        ]

        mock_responses = [
            ToolCallResponse(
                id="flight_search",
                status="success",
                result={"flights": ["flight1"]},
                execution_time=1.5,
                service="duffel_flights",
                method="search_flights",
            ),
            ToolCallResponse(
                id="weather_check",
                status="success",
                result={"temperature": 75, "condition": "sunny"},
                execution_time=0.8,
                service="weather",
                method="get_weather",
            ),
        ]

        (
            chat_orchestration_service.tool_call_service.execute_parallel_tool_calls.return_value
        ) = mock_responses

        # Act
        result = await chat_orchestration_service.execute_parallel_tools(tool_calls)

        # Assert
        assert result["total_calls"] == 2
        assert result["success_count"] == 2
        assert "flight_search" in result["results"]
        assert "weather_check" in result["results"]
        assert result["results"]["flight_search"] == {"flights": ["flight1"]}
        assert result["results"]["weather_check"] == {
            "temperature": 75,
            "condition": "sunny",
        }
        assert "execution_summary" in result
        assert result["execution_summary"]["total_time"] == 1.5  # Max execution time
        assert result["execution_summary"]["average_time"] == 1.15  # Average

    @pytest.mark.asyncio
    async def test_execute_parallel_tools_with_errors(self, chat_orchestration_service):
        """Test parallel tool execution with some failures."""
        # Arrange
        tool_calls = [
            {
                "id": "successful_call",
                "service": "weather",
                "method": "get_weather",
                "params": {"location": "NYC"},
            },
            {
                "id": "failed_call",
                "service": "duffel_flights",
                "method": "search_flights",
                "params": {"invalid": "params"},
            },
        ]

        mock_responses = [
            ToolCallResponse(
                id="successful_call",
                status="success",
                result={"temperature": 65},
                execution_time=1.0,
                service="weather",
                method="get_weather",
            ),
            ToolCallResponse(
                id="failed_call",
                status="error",
                result=None,
                error="Invalid parameters",
                execution_time=0.5,
                service="duffel_flights",
                method="search_flights",
            ),
        ]

        (
            chat_orchestration_service.tool_call_service.execute_parallel_tool_calls.return_value
        ) = mock_responses

        # Act
        result = await chat_orchestration_service.execute_parallel_tools(tool_calls)

        # Assert
        assert result["total_calls"] == 2
        assert result["success_count"] == 1
        assert result["results"]["successful_call"] == {"temperature": 65}
        assert result["results"]["failed_call"]["error"] == "Invalid parameters"
        assert result["results"]["failed_call"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_execute_structured_tool_call(self, chat_orchestration_service):
        """Test executing a single structured tool call."""
        # Arrange
        service = "google_maps"
        method = "geocode"
        params = {"address": "New York City"}
        call_id = "test_call_123"

        expected_response = ToolCallResponse(
            id=call_id,
            status="success",
            result={"lat": 40.7128, "lng": -74.0060},
            execution_time=1.2,
            service=service,
            method=method,
        )

        chat_orchestration_service.tool_call_service.execute_tool_call.return_value = (
            expected_response
        )

        # Act
        response = await chat_orchestration_service.execute_structured_tool_call(
            service, method, params, call_id
        )

        # Assert
        assert response == expected_response

        # Verify tool call service was called correctly
        call_args = (
            chat_orchestration_service.tool_call_service.execute_tool_call.call_args[0][
                0
            ]
        )
        assert call_args.id == call_id
        assert call_args.service == service
        assert call_args.method == method
        assert call_args.params == params

    @pytest.mark.asyncio
    async def test_format_tool_response_for_chat(self, chat_orchestration_service):
        """Test formatting tool responses for chat interface."""
        # Arrange
        tool_response = ToolCallResponse(
            id="flight_search_123",
            status="success",
            result={"flights": ["flight1", "flight2"]},
            execution_time=2.5,
            service="duffel_flights",
            method="search_flights",
        )

        expected_formatted = {
            "type": "flights",
            "title": "Flight Search Results",
            "data": {"flights": ["flight1", "flight2"]},
            "actions": ["book", "compare", "save"],
        }

        (
            chat_orchestration_service.tool_call_service.format_tool_result_for_chat.return_value
        ) = expected_formatted

        # Act
        result = await chat_orchestration_service.format_tool_response_for_chat(
            tool_response
        )

        # Assert
        assert result["type"] == "flights"
        assert result["title"] == "Flight Search Results"
        assert "orchestration_metadata" in result
        assert result["orchestration_metadata"]["service_used"] == "duffel_flights"
        assert result["orchestration_metadata"]["method_called"] == "search_flights"
        assert result["orchestration_metadata"]["execution_time"] == 2.5

    @pytest.mark.asyncio
    async def test_get_chat_history_success(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test retrieving chat history using Supabase MCP."""
        # Arrange
        session_id = "session_123"
        expected_messages = [
            {"id": "msg_1", "role": "user", "content": "Hello"},
            {"id": "msg_2", "role": "assistant", "content": "Hi there!"},
            {"id": "msg_3", "role": "user", "content": "Plan my trip"},
        ]

        mock_mcp_manager.invoke.return_value = expected_messages

        # Act
        result = await chat_orchestration_service.get_chat_history(session_id, limit=10)

        # Assert
        assert result == expected_messages
        assert len(result) == 3

        # Verify MCP call
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="supabase",
            method_name="execute_sql",
            params={
                "query": "SELECT * FROM get_recent_messages($1, $2, $3, $4)",
            },
        )

    @pytest.mark.asyncio
    async def test_end_chat_session_success(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test ending a chat session successfully."""
        # Arrange
        session_id = "session_123"
        mock_mcp_manager.invoke.return_value = {"ended_at": "2025-01-23T12:00:00Z"}

        # Act
        result = await chat_orchestration_service.end_chat_session(session_id)

        # Assert
        assert result is True

        # Verify MCP call
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="supabase",
            method_name="execute_sql",
            params={
                "query": """
                UPDATE chat_sessions 
                SET ended_at = NOW(), updated_at = NOW()
                WHERE id = $1
                RETURNING ended_at
            """,
            },
        )

    @pytest.mark.asyncio
    async def test_end_chat_session_not_found(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test ending a chat session that doesn't exist."""
        # Arrange
        session_id = "nonexistent_session"
        mock_mcp_manager.invoke.return_value = None  # No session found

        # Act & Assert
        with pytest.raises(
            ChatOrchestrationError, match="Session nonexistent_session not found"
        ):
            await chat_orchestration_service.end_chat_session(session_id)

    @pytest.mark.asyncio
    async def test_memory_storage_search_result(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test storing search results in memory graph for future reference."""
        # Arrange
        flight_params = {"origin": "NYC", "destination": "LAX"}
        flight_results = {"offers": [{"id": "offer_1"}]}

        # Mock responses: flight search + memory storage
        mock_mcp_manager.invoke.side_effect = [
            flight_results,  # Flight search response
            {"entity_id": "search_result_123"},  # Memory storage response
        ]

        # Act
        await chat_orchestration_service.search_flights(flight_params)

        # Assert - Verify memory storage was called
        assert mock_mcp_manager.invoke.call_count == 2

        memory_call = mock_mcp_manager.invoke.call_args_list[1]
        assert memory_call[1]["mcp_name"] == "memory"
        assert memory_call[1]["method_name"] == "create_entities"

        # Check entity structure
        entity = memory_call[1]["params"]["entities"][0]
        assert entity["entityType"] == "SearchResult"
        assert "search_type:flight" in entity["observations"]

    @pytest.mark.asyncio
    async def test_memory_storage_location_data(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test storing location data in memory graph."""
        # Arrange
        location = "Paris, France"
        location_data = {"lat": 48.8566, "lng": 2.3522}

        # Mock responses: location lookup + memory storage
        mock_mcp_manager.invoke.side_effect = [
            location_data,  # Location lookup response
            {"entity_id": "destination_123"},  # Memory storage response
        ]

        # Act
        await chat_orchestration_service.get_location_info(location)

        # Assert - Verify memory storage was called
        assert mock_mcp_manager.invoke.call_count == 2

        memory_call = mock_mcp_manager.invoke.call_args_list[1]
        assert memory_call[1]["mcp_name"] == "memory"
        assert memory_call[1]["method_name"] == "create_entities"

        # Check entity structure
        entity = memory_call[1]["params"]["entities"][0]
        assert entity["name"] == location
        assert entity["entityType"] == "Destination"
        assert "latitude:48.8566" in entity["observations"]
        assert "longitude:2.3522" in entity["observations"]

    @pytest.mark.asyncio
    async def test_error_handling_in_search_operations(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test error handling in search operations."""
        # Arrange
        mock_mcp_manager.invoke.side_effect = Exception(
            "Service temporarily unavailable"
        )

        # Act & Assert
        with pytest.raises(ChatOrchestrationError, match="Flight search failed"):
            await chat_orchestration_service.search_flights({"origin": "NYC"})

        with pytest.raises(ChatOrchestrationError, match="Accommodation search failed"):
            await chat_orchestration_service.search_accommodations({"location": "NYC"})

        with pytest.raises(ChatOrchestrationError, match="Location lookup failed"):
            await chat_orchestration_service.get_location_info("NYC")

    @pytest.mark.asyncio
    async def test_memory_storage_error_handling(
        self, chat_orchestration_service, mock_mcp_manager
    ):
        """Test graceful handling of memory storage errors."""
        # Arrange - Flight search succeeds but memory storage fails
        mock_mcp_manager.invoke.side_effect = [
            {"offers": [{"id": "offer_1"}]},  # Flight search success
            Exception("Memory service unavailable"),  # Memory storage failure
        ]

        # Act - Should not raise exception due to graceful error handling
        result = await chat_orchestration_service.search_flights({"origin": "NYC"})

        # Assert - Flight search result should still be returned
        assert result["search_type"] == "flights"
        assert result["results"]["offers"][0]["id"] == "offer_1"


class TestChatOrchestrationIntegration:
    """Integration tests for chat orchestration service."""

    @pytest.mark.asyncio
    async def test_complete_chat_session_flow(self):
        """Test complete chat session flow from creation to completion."""
        # Arrange
        mock_manager = AsyncMock(spec=MCPManager)
        service = ChatOrchestrationService(mock_manager)

        # Mock session creation
        mock_manager.invoke.side_effect = [
            {
                "id": "session_123",
                "created_at": "2025-01-23T10:00:00Z",
            },  # Create session
            {"id": "msg_1", "created_at": "2025-01-23T10:01:00Z"},  # Save user message
            {"offers": [{"id": "offer_1", "price": "250.00"}]},  # Flight search
            {"entity_id": "search_123"},  # Memory storage
            {
                "id": "msg_2",
                "created_at": "2025-01-23T10:02:00Z",
            },  # Save assistant message
            {"ended_at": "2025-01-23T10:05:00Z"},  # End session
        ]

        # Act - Execute complete flow
        # 1. Create session
        session = await service.create_chat_session(
            user_id=123, metadata={"client": "web"}
        )
        session_id = session["session_id"]

        # 2. Save user message
        await service.save_message(
            session_id, "user", "Find flights from NYC to LAX", {}
        )

        # 3. Search flights
        flights = await service.search_flights(
            {"origin": "NYC", "destination": "LAX", "departure_date": "2025-06-01"}
        )

        # 4. Save assistant response
        await service.save_message(session_id, "assistant", "Found 1 flight option", {})

        # 5. End session
        ended = await service.end_chat_session(session_id)

        # Assert
        assert session["session_id"] == "session_123"
        assert flights["search_type"] == "flights"
        assert ended is True
        assert mock_manager.invoke.call_count == 6

    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self):
        """Test concurrent search operations performance."""
        mock_manager = AsyncMock(spec=MCPManager)
        service = ChatOrchestrationService(mock_manager)

        # Mock responses for concurrent operations
        mock_manager.invoke.side_effect = [
            {"offers": [{"id": "flight_1"}]},  # Flight search
            {"entity_id": "flight_search_123"},  # Flight memory storage
            {"properties": [{"id": "hotel_1"}]},  # Accommodation search
            {"entity_id": "accommodation_search_123"},  # Accommodation memory storage
            {"lat": 40.7128, "lng": -74.0060},  # Location lookup
            {"entity_id": "location_123"},  # Location memory storage
        ]

        # Execute concurrent operations
        flight_task = service.search_flights({"origin": "NYC", "destination": "LAX"})
        accommodation_task = service.search_accommodations({"location": "LAX"})
        location_task = service.get_location_info("New York City")

        results = await asyncio.gather(flight_task, accommodation_task, location_task)

        # Verify all operations completed successfully
        assert len(results) == 3
        assert results[0]["search_type"] == "flights"
        assert results[1]["search_type"] == "accommodations"
        assert results[2]["location"] == "New York City"

    @pytest.mark.asyncio
    async def test_tool_calling_error_recovery_integration(self):
        """Test integration with tool calling error recovery mechanisms."""
        mock_manager = AsyncMock(spec=MCPManager)
        service = ChatOrchestrationService(mock_manager)

        # Mock tool call service with error recovery
        mock_tool_service = AsyncMock()
        service.tool_call_service = mock_tool_service

        # Mock error recovery response
        mock_tool_service.execute_parallel_tool_calls.return_value = [
            ToolCallResponse(
                id="flight_search",
                status="success",
                result={"flights": ["recovered_flight"]},
                execution_time=2.0,
                service="amadeus_flights",  # Alternative service used
                method="search_flights",
            )
        ]

        tool_calls = [
            {
                "id": "flight_search",
                "service": "duffel_flights",
                "method": "search_flights",
                "params": {"origin": "NYC", "destination": "LAX"},
            }
        ]

        # Execute with error recovery
        result = await service.execute_parallel_tools(tool_calls)

        # Verify error recovery worked
        assert result["success_count"] == 1
        assert "recovered_flight" in str(result["results"]["flight_search"])
