"""
Comprehensive tests for ChatOrchestrationService.

This module provides extensive testing for the chat orchestration service
including all methods, error handling, and edge cases.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.services.core.chat_orchestration import (
    ChatOrchestrationError,
    ChatOrchestrationService,
)
from tripsage.services.core.tool_calling_service import ToolCallResponse


class TestChatOrchestrationService:
    """Comprehensive tests for ChatOrchestrationService."""

    @pytest.fixture
    def service(self):
        """Create a ChatOrchestrationService instance."""
        return ChatOrchestrationService()

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager."""
        mock = MagicMock()
        mock.invoke = AsyncMock()
        return mock

    @pytest.fixture
    def mock_tool_service(self):
        """Mock tool calling service."""
        mock = MagicMock()
        mock.execute_parallel_tool_calls = AsyncMock()
        mock.execute_tool_call = AsyncMock()
        mock.format_tool_result_for_chat = AsyncMock()
        return mock

    def test_initialization(self, service):
        """Test service initialization."""
        assert service.database is None
        assert service.tool_call_service is not None
        assert service.mcp_manager is not None
        assert service.logger is not None

    def test_sanitize_sql_value_none(self, service):
        """Test SQL sanitization with None value."""
        result = service._sanitize_sql_value(None)
        assert result == "NULL"

    def test_sanitize_sql_value_boolean(self, service):
        """Test SQL sanitization with boolean values."""
        assert service._sanitize_sql_value(True) == "TRUE"
        assert service._sanitize_sql_value(False) == "FALSE"

    def test_sanitize_sql_value_number(self, service):
        """Test SQL sanitization with numbers."""
        assert service._sanitize_sql_value(42) == "42"
        assert service._sanitize_sql_value(3.14) == "3.14"

    def test_sanitize_sql_value_dict(self, service):
        """Test SQL sanitization with dictionary."""
        test_dict = {"key": "value", "number": 123}
        result = service._sanitize_sql_value(test_dict)
        assert "::jsonb" in result
        assert "key" in result
        assert "value" in result

    def test_sanitize_sql_value_string(self, service):
        """Test SQL sanitization with strings."""
        assert service._sanitize_sql_value("test") == "'test'"
        assert service._sanitize_sql_value("test'quote") == "'test''quote'"

    @pytest.mark.asyncio
    async def test_create_chat_session_success(self, service, mock_mcp_manager):
        """Test successful chat session creation."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.return_value = {
            "id": "session_123",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
        }

        result = await service.create_chat_session(user_id=1, metadata={"test": "data"})

        assert result["session_id"] == "session_123"
        assert result["user_id"] == 1
        assert result["metadata"] == {"test": "data"}
        assert result["status"] == "active"
        mock_mcp_manager.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_chat_session_no_result(self, service, mock_mcp_manager):
        """Test chat session creation with no result."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.return_value = None

        with pytest.raises(ChatOrchestrationError, match="No session data returned"):
            await service.create_chat_session(user_id=1)

    @pytest.mark.asyncio
    async def test_create_chat_session_exception(self, service, mock_mcp_manager):
        """Test chat session creation with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Database error")

        with pytest.raises(
            ChatOrchestrationError, match="Failed to create chat session"
        ):
            await service.create_chat_session(user_id=1)

    @pytest.mark.asyncio
    async def test_save_message_success(self, service, mock_mcp_manager):
        """Test successful message saving."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.return_value = {
            "id": "msg_123",
            "created_at": "2023-01-01T00:00:00Z",
        }

        result = await service.save_message(
            session_id="session_123",
            role="user",
            content="Hello world",
            metadata={"test": "data"},
        )

        assert result["message_id"] == "msg_123"
        assert result["session_id"] == "session_123"
        assert result["role"] == "user"
        assert result["content"] == "Hello world"
        assert result["metadata"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_save_message_invalid_role(self, service, mock_mcp_manager):
        """Test message saving with invalid role."""
        service.mcp_manager = mock_mcp_manager

        with pytest.raises(ChatOrchestrationError, match="Invalid role"):
            await service.save_message(
                session_id="session_123", role="invalid_role", content="Hello world"
            )

    @pytest.mark.asyncio
    async def test_save_message_exception(self, service, mock_mcp_manager):
        """Test message saving with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Database error")

        with pytest.raises(ChatOrchestrationError, match="Failed to save message"):
            await service.save_message(
                session_id="session_123", role="user", content="Hello world"
            )

    @pytest.mark.asyncio
    async def test_search_flights_success(self, service, mock_mcp_manager):
        """Test successful flight search."""
        service.mcp_manager = mock_mcp_manager
        mock_flight_data = {"offers": [{"id": "flight_123", "price": 500}]}
        mock_mcp_manager.invoke.return_value = mock_flight_data

        with patch.object(service, "_store_search_result") as mock_store:
            result = await service.search_flights(
                {"origin": "NYC", "destination": "LAX", "departure_date": "2023-06-01"}
            )

            assert result["search_type"] == "flights"
            assert result["results"] == mock_flight_data
            assert "timestamp" in result
            assert result["cached"] is False
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_flights_exception(self, service, mock_mcp_manager):
        """Test flight search with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Flight API error")

        with pytest.raises(ChatOrchestrationError, match="Flight search failed"):
            await service.search_flights({"origin": "NYC"})

    @pytest.mark.asyncio
    async def test_search_accommodations_success(self, service, mock_mcp_manager):
        """Test successful accommodation search."""
        service.mcp_manager = mock_mcp_manager
        mock_accommodation_data = {"properties": [{"id": "prop_123", "price": 200}]}
        mock_mcp_manager.invoke.return_value = mock_accommodation_data

        with patch.object(service, "_store_search_result") as mock_store:
            result = await service.search_accommodations(
                {
                    "location": "San Francisco",
                    "check_in": "2023-06-01",
                    "check_out": "2023-06-05",
                }
            )

            assert result["search_type"] == "accommodations"
            assert result["results"] == mock_accommodation_data
            assert "timestamp" in result
            assert result["cached"] is False
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_accommodations_exception(self, service, mock_mcp_manager):
        """Test accommodation search with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Accommodation API error")

        with pytest.raises(ChatOrchestrationError, match="Accommodation search failed"):
            await service.search_accommodations({"location": "SF"})

    @pytest.mark.asyncio
    async def test_get_location_info_success(self, service, mock_mcp_manager):
        """Test successful location info retrieval."""
        service.mcp_manager = mock_mcp_manager
        mock_location_data = {"lat": 37.7749, "lng": -122.4194}
        mock_mcp_manager.invoke.return_value = mock_location_data

        with patch.object(service, "_store_location_data") as mock_store:
            result = await service.get_location_info("San Francisco")

            assert result["location"] == "San Francisco"
            assert result["data"] == mock_location_data
            assert "timestamp" in result
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_location_info_exception(self, service, mock_mcp_manager):
        """Test location info retrieval with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Maps API error")

        with pytest.raises(ChatOrchestrationError, match="Location lookup failed"):
            await service.get_location_info("Invalid Location")

    @pytest.mark.asyncio
    async def test_execute_parallel_tools_success(self, service, mock_tool_service):
        """Test successful parallel tool execution."""
        service.tool_call_service = mock_tool_service

        mock_responses = [
            ToolCallResponse(
                id="tool_1",
                service="test_service",
                method="test_method",
                status="success",
                result={"data": "result1"},
                execution_time=0.5,
            ),
            ToolCallResponse(
                id="tool_2",
                service="test_service",
                method="test_method",
                status="success",
                result={"data": "result2"},
                execution_time=0.3,
            ),
        ]
        mock_tool_service.execute_parallel_tool_calls.return_value = mock_responses

        tool_calls = [
            {
                "id": "tool_1",
                "service": "test_service",
                "method": "test_method",
                "params": {},
            },
            {
                "id": "tool_2",
                "service": "test_service",
                "method": "test_method",
                "params": {},
            },
        ]

        result = await service.execute_parallel_tools(tool_calls)

        assert result["total_calls"] == 2
        assert result["success_count"] == 2
        assert "results" in result
        assert "execution_summary" in result
        assert result["execution_summary"]["total_time"] == 0.5
        assert result["execution_summary"]["average_time"] == 0.4

    @pytest.mark.asyncio
    async def test_execute_parallel_tools_with_failures(
        self, service, mock_tool_service
    ):
        """Test parallel tool execution with some failures."""
        service.tool_call_service = mock_tool_service

        mock_responses = [
            ToolCallResponse(
                id="tool_1",
                service="test_service",
                method="test_method",
                status="success",
                result={"data": "result1"},
                execution_time=0.5,
            ),
            ToolCallResponse(
                id="tool_2",
                service="test_service",
                method="test_method",
                status="failed",
                error="Test error",
                execution_time=0.2,
            ),
        ]
        mock_tool_service.execute_parallel_tool_calls.return_value = mock_responses

        tool_calls = [
            {"id": "tool_1", "service": "test_service", "method": "test_method"},
            {"id": "tool_2", "service": "test_service", "method": "test_method"},
        ]

        result = await service.execute_parallel_tools(tool_calls)

        assert result["total_calls"] == 2
        assert result["success_count"] == 1
        assert result["results"]["tool_1"]["data"] == "result1"
        assert result["results"]["tool_2"]["error"] == "Test error"

    @pytest.mark.asyncio
    async def test_execute_parallel_tools_exception(self, service, mock_tool_service):
        """Test parallel tool execution with exception."""
        service.tool_call_service = mock_tool_service
        mock_tool_service.execute_parallel_tool_calls.side_effect = Exception(
            "Tool error"
        )

        with pytest.raises(
            ChatOrchestrationError, match="Parallel tool execution failed"
        ):
            await service.execute_parallel_tools([])

    @pytest.mark.asyncio
    async def test_execute_structured_tool_call_success(
        self, service, mock_tool_service
    ):
        """Test successful structured tool call."""
        service.tool_call_service = mock_tool_service

        mock_response = ToolCallResponse(
            id="test_call",
            service="test_service",
            method="test_method",
            status="success",
            result={"data": "test_result"},
            execution_time=0.3,
        )
        mock_tool_service.execute_tool_call.return_value = mock_response

        result = await service.execute_structured_tool_call(
            service="test_service",
            method="test_method",
            params={"param": "value"},
            call_id="test_call",
        )

        assert result.id == "test_call"
        assert result.status == "success"
        assert result.result == {"data": "test_result"}

    @pytest.mark.asyncio
    async def test_execute_structured_tool_call_exception(
        self, service, mock_tool_service
    ):
        """Test structured tool call with exception."""
        service.tool_call_service = mock_tool_service
        mock_tool_service.execute_tool_call.side_effect = Exception("Tool error")

        with pytest.raises(ChatOrchestrationError, match="Structured tool call failed"):
            await service.execute_structured_tool_call(
                service="test_service", method="test_method", params={}
            )

    @pytest.mark.asyncio
    async def test_format_tool_response_for_chat_success(
        self, service, mock_tool_service
    ):
        """Test successful tool response formatting."""
        service.tool_call_service = mock_tool_service

        mock_response = ToolCallResponse(
            id="test_call",
            service="test_service",
            method="test_method",
            status="success",
            result={"data": "test_result"},
            execution_time=0.3,
        )

        mock_formatted = {"formatted": "response", "display": "formatted data"}
        mock_tool_service.format_tool_result_for_chat.return_value = mock_formatted

        result = await service.format_tool_response_for_chat(mock_response)

        assert result["formatted"] == "response"
        assert result["display"] == "formatted data"
        assert "orchestration_metadata" in result
        assert result["orchestration_metadata"]["execution_time"] == 0.3
        assert result["orchestration_metadata"]["service_used"] == "test_service"
        assert result["orchestration_metadata"]["method_called"] == "test_method"

    @pytest.mark.asyncio
    async def test_format_tool_response_for_chat_exception(
        self, service, mock_tool_service
    ):
        """Test tool response formatting with exception."""
        service.tool_call_service = mock_tool_service
        mock_tool_service.format_tool_result_for_chat.side_effect = Exception(
            "Format error"
        )

        mock_response = ToolCallResponse(
            id="test_call",
            service="test_service",
            method="test_method",
            status="success",
            result={},
            execution_time=0.1,
        )

        with pytest.raises(
            ChatOrchestrationError, match="Tool response formatting failed"
        ):
            await service.format_tool_response_for_chat(mock_response)

    @pytest.mark.asyncio
    async def test_get_chat_history_success(self, service, mock_mcp_manager):
        """Test successful chat history retrieval."""
        service.mcp_manager = mock_mcp_manager
        mock_messages = [
            {"id": "msg_1", "role": "user", "content": "Hello"},
            {"id": "msg_2", "role": "assistant", "content": "Hi there!"},
        ]
        mock_mcp_manager.invoke.return_value = mock_messages

        result = await service.get_chat_history("session_123", limit=10, offset=0)

        assert result == mock_messages
        mock_mcp_manager.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_chat_history_invalid_limit(self, service):
        """Test chat history retrieval with invalid limit."""
        with pytest.raises(
            ChatOrchestrationError, match="Limit must be between 1 and 100"
        ):
            await service.get_chat_history("session_123", limit=0)

        with pytest.raises(
            ChatOrchestrationError, match="Limit must be between 1 and 100"
        ):
            await service.get_chat_history("session_123", limit=101)

    @pytest.mark.asyncio
    async def test_get_chat_history_invalid_offset(self, service):
        """Test chat history retrieval with invalid offset."""
        with pytest.raises(ChatOrchestrationError, match="Offset must be non-negative"):
            await service.get_chat_history("session_123", offset=-1)

    @pytest.mark.asyncio
    async def test_get_chat_history_exception(self, service, mock_mcp_manager):
        """Test chat history retrieval with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Database error")

        with pytest.raises(ChatOrchestrationError, match="Failed to get chat history"):
            await service.get_chat_history("session_123")

    @pytest.mark.asyncio
    async def test_end_chat_session_success(self, service, mock_mcp_manager):
        """Test successful chat session ending."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.return_value = {"ended_at": "2023-01-01T01:00:00Z"}

        result = await service.end_chat_session("session_123")

        assert result is True
        mock_mcp_manager.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_chat_session_not_found(self, service, mock_mcp_manager):
        """Test chat session ending with session not found."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.return_value = None

        with pytest.raises(
            ChatOrchestrationError, match="Session session_123 not found"
        ):
            await service.end_chat_session("session_123")

    @pytest.mark.asyncio
    async def test_end_chat_session_exception(self, service, mock_mcp_manager):
        """Test chat session ending with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Database error")

        with pytest.raises(ChatOrchestrationError, match="Failed to end chat session"):
            await service.end_chat_session("session_123")

    @pytest.mark.asyncio
    async def test_store_search_result_success(self, service, mock_mcp_manager):
        """Test successful search result storage."""
        service.mcp_manager = mock_mcp_manager

        await service._store_search_result(
            search_type="flight",
            params={"origin": "NYC", "destination": "LAX"},
            results=[{"id": "flight_123"}],
        )

        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="memory",
            method_name="create_entities",
            params={"entities": [pytest.any]},
        )

    @pytest.mark.asyncio
    async def test_store_search_result_exception(self, service, mock_mcp_manager):
        """Test search result storage with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Memory error")

        # Should not raise exception, just log warning
        await service._store_search_result(
            search_type="flight", params={"origin": "NYC"}, results=[]
        )

    @pytest.mark.asyncio
    async def test_store_location_data_success(self, service, mock_mcp_manager):
        """Test successful location data storage."""
        service.mcp_manager = mock_mcp_manager

        await service._store_location_data(
            location="San Francisco", data={"lat": 37.7749, "lng": -122.4194}
        )

        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="memory",
            method_name="create_entities",
            params={"entities": [pytest.any]},
        )

    @pytest.mark.asyncio
    async def test_store_location_data_exception(self, service, mock_mcp_manager):
        """Test location data storage with exception."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.side_effect = Exception("Memory error")

        # Should not raise exception, just log warning
        await service._store_location_data(
            location="San Francisco", data={"lat": 37.7749, "lng": -122.4194}
        )

    @pytest.mark.asyncio
    async def test_execute_single_tool_call(self, service, mock_mcp_manager):
        """Test single tool call execution."""
        service.mcp_manager = mock_mcp_manager
        mock_mcp_manager.invoke.return_value = {"result": "success"}

        tool_call = {
            "service": "test_service",
            "method": "test_method",
            "params": {"param": "value"},
        }

        result = await service._execute_single_tool_call(tool_call)

        assert result == {"result": "success"}
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="test_service",
            method_name="test_method",
            params={"param": "value"},
        )
