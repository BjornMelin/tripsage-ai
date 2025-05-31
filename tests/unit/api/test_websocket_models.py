"""
Tests for WebSocket Pydantic models.

This module tests the WebSocket event models, ensuring proper validation,
serialization, and type safety.
"""

import json
import os
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from tripsage.api.models.requests.websocket import WebSocketAuthRequest
from tripsage.api.models.responses.websocket import WebSocketAuthResponse
from tripsage_core.models.schemas_common.chat import (
    ChatMessage as WebSocketMessage,
)
from tripsage_core.models.schemas_common.chat import (
    MessageRole,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    ConnectionStatus,
    WebSocketEvent,
    WebSocketEventType,
)


# Define temporary test models
class ChatMessageChunkEvent(WebSocketEvent):
    content: str = ""


class ConnectionEvent(WebSocketEvent):
    pass


class ErrorEvent(WebSocketEvent):
    error_code: str = ""
    error_message: str = ""


class WebSocketAgentStatus:
    IDLE = "idle"
    BUSY = "busy"


# Test constants
TEST_JWT_TOKEN = os.getenv("TEST_JWT_TOKEN", "mock-jwt-token-for-models-test")


class TestWebSocketEventType:
    """Test WebSocket event type enumeration."""

    def test_event_types_exist(self):
        """Test that all expected event types are defined."""
        expected_types = [
            "auth",
            "auth_response",
            "chat_message",
            "chat_message_chunk",
            "agent_status_update",
            "user_typing",
            "user_stop_typing",
            "connection_status",
            "error",
        ]

        for event_type in expected_types:
            assert hasattr(WebSocketEventType, event_type.upper())
            assert getattr(WebSocketEventType, event_type.upper()).value == event_type

    def test_event_type_serialization(self):
        """Test that event types serialize correctly."""
        event_type = WebSocketEventType.CHAT_MESSAGE
        assert str(event_type) == "chat_message"
        assert event_type.value == "chat_message"


class TestWebSocketEvent:
    """Test base WebSocket event model."""

    def test_create_basic_event(self):
        """Test creating a basic WebSocket event."""
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=str(uuid4()),
            payload={"message": "Hello World"},
        )

        assert event.type == WebSocketEventType.CHAT_MESSAGE
        assert isinstance(UUID(event.sessionId), UUID)
        assert event.payload == {"message": "Hello World"}
        assert isinstance(event.timestamp, datetime)

    def test_event_with_user_id(self):
        """Test event with optional user ID."""
        user_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.USER_TYPING,
            sessionId=str(uuid4()),
            userId=user_id,
            payload={},
        )

        assert event.userId == user_id

    def test_event_serialization(self):
        """Test event serialization to JSON."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Test message"},
        )

        event_dict = event.model_dump()
        assert event_dict["type"] == "chat_message"
        assert event_dict["sessionId"] == session_id
        assert event_dict["payload"]["content"] == "Test message"
        assert "timestamp" in event_dict

    def test_event_json_serialization(self):
        """Test event JSON serialization."""
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=str(uuid4()),
            payload={"test": "data"},
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "chat_message"
        assert "timestamp" in parsed

    def test_invalid_session_id(self):
        """Test validation with invalid session ID."""
        with pytest.raises(ValidationError) as exc_info:
            WebSocketEvent(
                type=WebSocketEventType.CHAT_MESSAGE,
                sessionId="invalid-uuid",
                payload={},
            )

        errors = exc_info.value.errors()
        assert any("sessionId" in str(error) for error in errors)


class TestWebSocketAuthRequest:
    """Test WebSocket authentication request model."""

    def test_create_auth_request(self):
        """Test creating authentication request."""
        session_id = str(uuid4())
        auth_request = WebSocketAuthRequest(token=TEST_JWT_TOKEN, sessionId=session_id)

        assert auth_request.token == TEST_JWT_TOKEN
        assert auth_request.sessionId == session_id

    def test_auth_request_validation(self):
        """Test auth request validation."""
        # Test missing token
        with pytest.raises(ValidationError):
            WebSocketAuthRequest(token="", sessionId=str(uuid4()))

        # Test missing session ID
        with pytest.raises(ValidationError):
            WebSocketAuthRequest(token="valid-token", sessionId="")


class TestWebSocketAuthResponse:
    """Test WebSocket authentication response model."""

    def test_successful_auth_response(self):
        """Test successful authentication response."""
        user_id = str(uuid4())
        response = WebSocketAuthResponse(
            success=True, userId=user_id, message="Authentication successful"
        )

        assert response.success is True
        assert response.userId == user_id
        assert response.message == "Authentication successful"

    def test_failed_auth_response(self):
        """Test failed authentication response."""
        response = WebSocketAuthResponse(success=False, message="Invalid token")

        assert response.success is False
        assert response.userId is None
        assert response.message == "Invalid token"


class TestWebSocketMessage:
    """Test WebSocket message model."""

    def test_create_chat_message(self):
        """Test creating a chat message."""
        session_id = uuid4()
        user_id = uuid4()

        chat_message = WebSocketMessage(
            role=MessageRole.USER,
            content="Hello, how can you help me?",
            session_id=session_id,
            user_id=user_id,
        )

        assert chat_message.session_id == session_id
        assert chat_message.user_id == user_id
        assert chat_message.role == MessageRole.USER
        assert chat_message.content == "Hello, how can you help me?"
        assert isinstance(chat_message.id, str)
        assert isinstance(chat_message.timestamp, datetime)

    def test_chat_message_with_tool_calls(self):
        """Test chat message with tool calls."""
        from tripsage.api.models.common.websocket import WebSocketToolCall

        tool_call = WebSocketToolCall(
            name="get_weather",
            arguments={"location": "New York"},
        )

        chat_message = WebSocketMessage(
            role=MessageRole.ASSISTANT,
            content="Let me check the weather for you.",
            tool_calls=[tool_call],
        )

        assert len(chat_message.tool_calls) == 1
        assert chat_message.tool_calls[0].name == "get_weather"
        assert chat_message.tool_calls[0].arguments["location"] == "New York"

    def test_invalid_role(self):
        """Test validation with invalid role."""
        with pytest.raises(ValidationError):
            WebSocketMessage(
                role="invalid_role",  # type: ignore
                content="Test message",
            )


class TestChatMessageChunkEvent:
    """Test chat message chunk event model."""

    def test_create_message_chunk(self):
        """Test creating a message chunk event."""
        session_id = uuid4()
        user_id = uuid4()

        chunk = ChatMessageChunkEvent(
            session_id=session_id,
            user_id=user_id,
            content="This is a ",
            chunk_index=0,
            is_final=False,
        )

        assert chunk.session_id == session_id
        assert chunk.user_id == user_id
        assert chunk.content == "This is a "
        assert chunk.chunk_index == 0
        assert chunk.is_final is False
        assert chunk.type == WebSocketEventType.CHAT_MESSAGE_CHUNK

    def test_final_chunk(self):
        """Test creating a final message chunk."""
        chunk = ChatMessageChunkEvent(
            session_id=uuid4(),
            content="complete message.",
            chunk_index=5,
            is_final=True,
        )

        assert chunk.is_final is True
        assert chunk.chunk_index == 5


class TestWebSocketAgentStatus:
    """Test WebSocket agent status model."""

    def test_create_status_update(self):
        """Test creating an agent status."""
        agent_status = WebSocketAgentStatus(
            agent_id="flight-agent",
            is_active=True,
            current_task="Searching for flights",
            progress=75,
            status_message="Found 10 flights matching your criteria",
        )

        assert agent_status.agent_id == "flight-agent"
        assert agent_status.is_active is True
        assert agent_status.current_task == "Searching for flights"
        assert agent_status.progress == 75
        assert agent_status.status_message == "Found 10 flights matching your criteria"
        assert isinstance(agent_status.last_activity, datetime)

    def test_inactive_status(self):
        """Test inactive agent status."""
        agent_status = WebSocketAgentStatus(agent_id="idle-agent", is_active=False)

        assert agent_status.is_active is False
        assert agent_status.current_task is None
        assert agent_status.progress == 0

    def test_progress_validation(self):
        """Test progress validation."""
        # Test negative progress
        with pytest.raises(ValidationError):
            WebSocketAgentStatus(agent_id="test-agent", is_active=True, progress=-1)

        # Test progress over 100
        with pytest.raises(ValidationError):
            WebSocketAgentStatus(agent_id="test-agent", is_active=True, progress=101)


class TestWebSocketTypingEvent:
    """Test WebSocket typing events."""

    def test_create_typing_start_event(self):
        """Test creating a typing start event."""
        session_id = uuid4()
        user_id = uuid4()

        typing_event = WebSocketEvent(
            type=WebSocketEventType.CHAT_TYPING_START,
            session_id=session_id,
            user_id=user_id,
            payload={"username": "john_doe"},
        )

        assert typing_event.session_id == session_id
        assert typing_event.user_id == user_id
        assert typing_event.type == WebSocketEventType.CHAT_TYPING_START
        assert typing_event.payload["username"] == "john_doe"

    def test_typing_stop_event(self):
        """Test creating a typing stop event."""
        typing_event = WebSocketEvent(
            type=WebSocketEventType.CHAT_TYPING_STOP,
            session_id=uuid4(),
            user_id=uuid4(),
        )

        assert typing_event.type == WebSocketEventType.CHAT_TYPING_STOP


class TestConnectionEvent:
    """Test WebSocket connection event model."""

    def test_create_connection_event(self):
        """Test creating connection event."""
        connection_id = str(uuid4())

        event = ConnectionEvent(
            status=ConnectionStatus.CONNECTED,
            connection_id=connection_id,
            user_id=uuid4(),
        )

        assert event.status == ConnectionStatus.CONNECTED
        assert event.connection_id == connection_id
        assert event.type == WebSocketEventType.CONNECTION_ESTABLISHED

    def test_connection_states(self):
        """Test all connection states."""
        states = [
            ConnectionStatus.CONNECTING,
            ConnectionStatus.CONNECTED,
            ConnectionStatus.DISCONNECTED,
            ConnectionStatus.ERROR,
        ]

        for state in states:
            event = ConnectionEvent(
                status=state,
                connection_id=str(uuid4()),
                user_id=uuid4(),
            )
            assert event.status == state


class TestErrorEvent:
    """Test WebSocket error event model."""

    def test_create_error(self):
        """Test creating WebSocket error event."""
        error = ErrorEvent(
            error_code="AUTH_FAILED",
            error_message="Authentication failed: Invalid token",
            details={"token_expired": True},
            user_id=uuid4(),
        )

        assert error.error_code == "AUTH_FAILED"
        assert error.error_message == "Authentication failed: Invalid token"
        assert error.details["token_expired"] is True
        assert error.type == WebSocketEventType.ERROR

    def test_error_without_details(self):
        """Test error without details."""
        error = ErrorEvent(
            error_code="CONNECTION_LOST", error_message="Connection to server lost"
        )

        assert error.error_code == "CONNECTION_LOST"
        assert error.details is None


class TestModelIntegration:
    """Test model integration and real-world scenarios."""

    def test_full_event_workflow(self):
        """Test a complete event workflow."""
        session_id = uuid4()
        user_id = uuid4()
        connection_id = str(uuid4())

        # Auth request
        auth_request = WebSocketAuthRequest(token=TEST_JWT_TOKEN, session_id=session_id)

        # Auth response
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )

        # Chat message
        chat_message = WebSocketMessage(
            role=MessageRole.USER,
            content="Plan a trip to Tokyo",
            session_id=session_id,
            user_id=user_id,
        )

        # Agent status
        agent_status = WebSocketAgentStatus(
            agent_id="travel-agent",
            is_active=True,
            current_task="Researching Tokyo travel options",
            progress=25,
            status_message="Gathering information about Tokyo attractions",
        )

        # Verify all models work together
        assert auth_request.session_id == session_id
        assert auth_response.user_id == user_id
        assert chat_message.session_id == session_id
        assert agent_status.agent_id == "travel-agent"

    def test_json_round_trip(self):
        """Test JSON serialization and deserialization."""
        original_message = WebSocketMessage(
            role=MessageRole.ASSISTANT,
            content="I can help you plan your trip to Tokyo!",
            session_id=uuid4(),
            user_id=uuid4(),
            metadata={
                "attachments": [
                    {
                        "id": str(uuid4()),
                        "name": "tokyo_guide.pdf",
                        "contentType": "application/pdf",
                    }
                ]
            },
        )

        # Serialize to JSON
        json_str = original_message.model_dump_json()

        # Deserialize from JSON
        data = json.loads(json_str)
        reconstructed_message = WebSocketMessage(**data)

        # Verify they match
        assert reconstructed_message.session_id == original_message.session_id
        assert reconstructed_message.user_id == original_message.user_id
        assert reconstructed_message.role == original_message.role
        assert reconstructed_message.content == original_message.content
        assert reconstructed_message.metadata == original_message.metadata
