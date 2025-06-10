"""
Comprehensive tests for chat service functionality.

Tests chat orchestration, message handling, and AI integration.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.factories import ChatFactory
from tripsage.api.schemas.responses.chat import ChatResponse
from tripsage_core.services.business.chat_service import ChatService


class TestChatService:
    """Test suite for ChatService functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Set up mock dependencies for ChatService."""
        return {
            "database_service": MagicMock(),
            "memory_service": AsyncMock(),
            "websocket_manager": AsyncMock(),
            "agent_orchestrator": AsyncMock(),
        }

    @pytest.fixture
    def chat_service(self, mock_dependencies):
        """Create ChatService instance with mocked dependencies."""
        service = ChatService()
        service.db = mock_dependencies["database_service"]
        service.memory = mock_dependencies["memory_service"]
        service.websocket = mock_dependencies["websocket_manager"]
        service.orchestrator = mock_dependencies["agent_orchestrator"]
        return service

    @pytest.mark.asyncio
    async def test_process_message_basic(self, chat_service):
        """Test basic message processing workflow."""
        # Arrange
        message_data = ChatFactory.create_message()
        chat_service.orchestrator.process_message.return_value = {
            "response": "I'd be happy to help you find a hotel in Tokyo!",
            "tool_calls": [],
            "session_id": message_data["session_id"],
        }

        # Act
        response = await chat_service.process_message(
            message=message_data["content"],
            user_id=message_data["user_id"],
            session_id=message_data["session_id"],
        )

        # Assert
        assert isinstance(response, ChatResponse)
        assert response.message == "I'd be happy to help you find a hotel in Tokyo!"
        assert response.session_id == message_data["session_id"]

        # Verify orchestrator was called
        chat_service.orchestrator.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_memory_context(self, chat_service):
        """Test message processing with memory context retrieval."""
        # Arrange
        message_data = ChatFactory.create_message()
        chat_service.memory.get_context.return_value = {
            "previous_searches": ["hotels in Tokyo", "flights to Japan"],
            "preferences": {"budget": "moderate", "location": "central"},
        }
        chat_service.orchestrator.process_message.return_value = {
            "response": "Based on your previous searches, here are some hotels...",
            "tool_calls": [],
            "session_id": message_data["session_id"],
        }

        # Act
        response = await chat_service.process_message(
            message=message_data["content"],
            user_id=message_data["user_id"],
            session_id=message_data["session_id"],
        )

        # Assert
        chat_service.memory.get_context.assert_called_once_with(
            user_id=message_data["user_id"]
        )
        assert "previous searches" in response.message.lower()

    @pytest.mark.asyncio
    async def test_process_message_with_tool_calls(self, chat_service):
        """Test message processing that triggers tool calls."""
        # Arrange
        message_data = ChatFactory.create_message(
            content="Find me hotels in Tokyo under $200 per night"
        )
        chat_service.orchestrator.process_message.return_value = {
            "response": "I found 5 hotels matching your criteria.",
            "tool_calls": [
                {
                    "tool": "accommodation_search",
                    "parameters": {
                        "destination": "Tokyo",
                        "max_price": 200,
                        "currency": "USD",
                    },
                    "result": {"hotels": ["Hotel A", "Hotel B"]},
                }
            ],
            "session_id": message_data["session_id"],
        }

        # Act
        response = await chat_service.process_message(
            message=message_data["content"],
            user_id=message_data["user_id"],
            session_id=message_data["session_id"],
        )

        # Assert
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["tool"] == "accommodation_search"
        assert response.tool_calls[0]["parameters"]["destination"] == "Tokyo"

    @pytest.mark.asyncio
    async def test_store_message_in_database(self, chat_service):
        """Test that messages are properly stored in database."""
        # Arrange
        message_data = ChatFactory.create_message()
        chat_service.db.store_chat_message = AsyncMock()

        # Act
        await chat_service.store_message(
            content=message_data["content"],
            role=message_data["role"],
            user_id=message_data["user_id"],
            session_id=message_data["session_id"],
        )

        # Assert
        chat_service.db.store_chat_message.assert_called_once()
        call_args = chat_service.db.store_chat_message.call_args[1]
        assert call_args["content"] == message_data["content"]
        assert call_args["role"] == message_data["role"]
        assert call_args["user_id"] == message_data["user_id"]

    @pytest.mark.asyncio
    async def test_get_chat_history(self, chat_service):
        """Test retrieving chat history for a session."""
        # Arrange
        conversation = ChatFactory.create_conversation(6)
        session_id = conversation[0]["session_id"]
        chat_service.db.get_chat_history = AsyncMock(return_value=conversation)

        # Act
        history = await chat_service.get_chat_history(session_id=session_id, limit=10)

        # Assert
        assert len(history) == 6
        assert all(msg["session_id"] == session_id for msg in history)
        chat_service.db.get_chat_history.assert_called_once_with(
            session_id=session_id, limit=10
        )

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, chat_service):
        """Test retrieving all sessions for a user."""
        # Arrange
        user_id = 1
        mock_sessions = [
            {
                "session_id": "session-1",
                "last_message": "Hello",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "session_id": "session-2",
                "last_message": "Find hotels",
                "created_at": datetime.now(timezone.utc),
            },
        ]
        chat_service.db.get_user_sessions = AsyncMock(return_value=mock_sessions)

        # Act
        sessions = await chat_service.get_user_sessions(user_id=user_id)

        # Assert
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "session-1"
        chat_service.db.get_user_sessions.assert_called_once_with(user_id=user_id)

    @pytest.mark.asyncio
    async def test_websocket_broadcast(self, chat_service):
        """Test WebSocket message broadcasting."""
        # Arrange
        message_data = ChatFactory.create_message()

        # Act
        await chat_service.broadcast_message(
            session_id=message_data["session_id"],
            message=message_data["content"],
            role=message_data["role"],
        )

        # Assert
        chat_service.websocket.broadcast_to_session.assert_called_once()
        call_args = chat_service.websocket.broadcast_to_session.call_args[1]
        assert call_args["session_id"] == message_data["session_id"]
        assert "message" in call_args["data"]

    @pytest.mark.asyncio
    async def test_error_handling_orchestrator_failure(self, chat_service):
        """Test error handling when orchestrator fails."""
        # Arrange
        message_data = ChatFactory.create_message()
        chat_service.orchestrator.process_message.side_effect = Exception(
            "Orchestrator error"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await chat_service.process_message(
                message=message_data["content"],
                user_id=message_data["user_id"],
                session_id=message_data["session_id"],
            )

        assert "Orchestrator error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_database_failure(self, chat_service):
        """Test error handling when database operations fail."""
        # Arrange
        message_data = ChatFactory.create_message()
        chat_service.db.store_chat_message.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await chat_service.store_message(
                content=message_data["content"],
                role=message_data["role"],
                user_id=message_data["user_id"],
                session_id=message_data["session_id"],
            )

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_memory_update_after_message(self, chat_service):
        """Test that memory is updated after processing a message."""
        # Arrange
        message_data = ChatFactory.create_message(
            content="I want to book a 5-star hotel in Tokyo"
        )
        chat_service.orchestrator.process_message.return_value = {
            "response": "I'll help you find luxury hotels in Tokyo.",
            "tool_calls": [],
            "session_id": message_data["session_id"],
        }

        # Act
        await chat_service.process_message(
            message=message_data["content"],
            user_id=message_data["user_id"],
            session_id=message_data["session_id"],
        )

        # Assert
        chat_service.memory.update_context.assert_called_once()
        call_args = chat_service.memory.update_context.call_args[1]
        assert call_args["user_id"] == message_data["user_id"]
        assert "5-star hotel" in call_args["content"].lower()

    @pytest.mark.asyncio
    async def test_session_management(self, chat_service):
        """Test chat session creation and management."""
        # Arrange
        user_id = 1

        # Act
        session_id = await chat_service.create_session(user_id=user_id)

        # Assert
        assert session_id is not None
        assert isinstance(session_id, str)
        chat_service.db.create_chat_session.assert_called_once_with(user_id=user_id)

    @pytest.mark.asyncio
    async def test_message_validation(self, chat_service):
        """Test message content validation."""
        # Test empty message
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            await chat_service.process_message(
                message="",
                user_id=1,
                session_id="test-session",
            )

        # Test None message
        with pytest.raises(ValueError, match="Message content cannot be empty"):
            await chat_service.process_message(
                message=None,
                user_id=1,
                session_id="test-session",
            )

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, chat_service):
        """Test handling concurrent messages in the same session."""
        import asyncio

        # Arrange
        session_id = "test-session"
        messages = [f"Message {i}" for i in range(3)]

        chat_service.orchestrator.process_message.return_value = {
            "response": "Response",
            "tool_calls": [],
            "session_id": session_id,
        }

        # Act
        tasks = [
            chat_service.process_message(
                message=msg,
                user_id=1,
                session_id=session_id,
            )
            for msg in messages
        ]

        responses = await asyncio.gather(*tasks)

        # Assert
        assert len(responses) == 3
        assert all(isinstance(resp, ChatResponse) for resp in responses)

    @pytest.mark.asyncio
    async def test_streaming_response_handling(self, chat_service):
        """Test handling of streaming responses."""
        # Arrange
        message_data = ChatFactory.create_message()

        async def mock_stream():
            yield {"chunk": "Hello"}
            yield {"chunk": " there!"}
            yield {"chunk": " How can I help?"}

        chat_service.orchestrator.process_message_stream = AsyncMock(
            return_value=mock_stream()
        )

        # Act
        chunks = []
        async for chunk in chat_service.process_message_stream(
            message=message_data["content"],
            user_id=message_data["user_id"],
            session_id=message_data["session_id"],
        ):
            chunks.append(chunk)

        # Assert
        assert len(chunks) == 3
        assert chunks[0]["chunk"] == "Hello"
        assert chunks[2]["chunk"] == " How can I help?"

    @pytest.mark.asyncio
    async def test_context_preservation(self, chat_service):
        """Test that conversation context is preserved across messages."""
        # Arrange
        conversation = ChatFactory.create_conversation(4)
        session_id = conversation[0]["session_id"]

        chat_service.db.get_chat_history = AsyncMock(return_value=conversation)
        chat_service.orchestrator.process_message.return_value = {
            "response": "Based on our conversation...",
            "tool_calls": [],
            "session_id": session_id,
        }

        # Act
        response = await chat_service.process_message(
            message="Continue our discussion",
            user_id=1,
            session_id=session_id,
        )

        # Assert
        # Verify that chat history was retrieved to provide context
        chat_service.db.get_chat_history.assert_called()
        assert "conversation" in response.message.lower()
