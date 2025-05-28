"""
Tests for WebSocket Pydantic models.

This module tests the WebSocket event models, ensuring proper validation,
serialization, and type safety.
"""

import json
import pytest
from datetime import datetime
from uuid import uuid4, UUID
from pydantic import ValidationError

from tripsage.api.models.websocket import (
    WebSocketEventType,
    WebSocketEvent,
    WebSocketAuthRequest,
    WebSocketAuthResponse,
    WebSocketChatMessage,
    WebSocketChatMessageChunk,
    WebSocketAgentStatusUpdate,
    WebSocketUserTyping,
    WebSocketUserStopTyping,
    WebSocketConnectionStatus,
    WebSocketError,
    ConnectionState,
)


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
            payload={"message": "Hello World"}
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
            payload={}
        )
        
        assert event.userId == user_id

    def test_event_serialization(self):
        """Test event serialization to JSON."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Test message"}
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
            payload={"test": "data"}
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
                payload={}
            )
        
        errors = exc_info.value.errors()
        assert any("sessionId" in str(error) for error in errors)


class TestWebSocketAuthRequest:
    """Test WebSocket authentication request model."""

    def test_create_auth_request(self):
        """Test creating authentication request."""
        session_id = str(uuid4())
        auth_request = WebSocketAuthRequest(
            token="jwt-token-here",
            sessionId=session_id
        )
        
        assert auth_request.token == "jwt-token-here"
        assert auth_request.sessionId == session_id

    def test_auth_request_validation(self):
        """Test auth request validation."""
        # Test missing token
        with pytest.raises(ValidationError):
            WebSocketAuthRequest(
                token="",
                sessionId=str(uuid4())
            )
        
        # Test missing session ID
        with pytest.raises(ValidationError):
            WebSocketAuthRequest(
                token="valid-token",
                sessionId=""
            )


class TestWebSocketAuthResponse:
    """Test WebSocket authentication response model."""

    def test_successful_auth_response(self):
        """Test successful authentication response."""
        user_id = str(uuid4())
        response = WebSocketAuthResponse(
            success=True,
            userId=user_id,
            message="Authentication successful"
        )
        
        assert response.success is True
        assert response.userId == user_id
        assert response.message == "Authentication successful"

    def test_failed_auth_response(self):
        """Test failed authentication response."""
        response = WebSocketAuthResponse(
            success=False,
            message="Invalid token"
        )
        
        assert response.success is False
        assert response.userId is None
        assert response.message == "Invalid token"


class TestWebSocketChatMessage:
    """Test WebSocket chat message model."""

    def test_create_chat_message(self):
        """Test creating a chat message."""
        session_id = str(uuid4())
        message_id = str(uuid4())
        
        chat_message = WebSocketChatMessage(
            sessionId=session_id,
            messageId=message_id,
            role="user",
            content="Hello, how can you help me?"
        )
        
        assert chat_message.sessionId == session_id
        assert chat_message.messageId == message_id
        assert chat_message.role == "user"
        assert chat_message.content == "Hello, how can you help me?"

    def test_chat_message_with_attachments(self):
        """Test chat message with attachments."""
        attachments = [
            {
                "id": str(uuid4()),
                "name": "document.pdf",
                "contentType": "application/pdf",
                "size": 1024
            }
        ]
        
        chat_message = WebSocketChatMessage(
            sessionId=str(uuid4()),
            messageId=str(uuid4()),
            role="user",
            content="Please review this document",
            attachments=attachments
        )
        
        assert len(chat_message.attachments) == 1
        assert chat_message.attachments[0]["name"] == "document.pdf"

    def test_chat_message_with_tool_calls(self):
        """Test chat message with tool calls."""
        tool_calls = [
            {
                "id": str(uuid4()),
                "name": "get_weather",
                "arguments": {"location": "New York"}
            }
        ]
        
        chat_message = WebSocketChatMessage(
            sessionId=str(uuid4()),
            messageId=str(uuid4()),
            role="assistant",
            content="Let me check the weather for you.",
            toolCalls=tool_calls
        )
        
        assert len(chat_message.toolCalls) == 1
        assert chat_message.toolCalls[0]["name"] == "get_weather"

    def test_invalid_role(self):
        """Test validation with invalid role."""
        with pytest.raises(ValidationError):
            WebSocketChatMessage(
                sessionId=str(uuid4()),
                messageId=str(uuid4()),
                role="invalid_role",
                content="Test message"
            )


class TestWebSocketChatMessageChunk:
    """Test WebSocket chat message chunk model."""

    def test_create_message_chunk(self):
        """Test creating a message chunk."""
        session_id = str(uuid4())
        message_id = str(uuid4())
        
        chunk = WebSocketChatMessageChunk(
            sessionId=session_id,
            messageId=message_id,
            content="This is a ",
            isComplete=False
        )
        
        assert chunk.sessionId == session_id
        assert chunk.messageId == message_id
        assert chunk.content == "This is a "
        assert chunk.isComplete is False

    def test_final_chunk(self):
        """Test creating a final message chunk."""
        chunk = WebSocketChatMessageChunk(
            sessionId=str(uuid4()),
            messageId=str(uuid4()),
            content="complete message.",
            isComplete=True
        )
        
        assert chunk.isComplete is True


class TestWebSocketAgentStatusUpdate:
    """Test WebSocket agent status update model."""

    def test_create_status_update(self):
        """Test creating an agent status update."""
        session_id = str(uuid4())
        
        status_update = WebSocketAgentStatusUpdate(
            sessionId=session_id,
            isActive=True,
            currentTask="Searching for flights",
            progress=75,
            statusMessage="Found 10 flights matching your criteria"
        )
        
        assert status_update.sessionId == session_id
        assert status_update.isActive is True
        assert status_update.currentTask == "Searching for flights"
        assert status_update.progress == 75
        assert status_update.statusMessage == "Found 10 flights matching your criteria"

    def test_inactive_status(self):
        """Test inactive agent status."""
        status_update = WebSocketAgentStatusUpdate(
            sessionId=str(uuid4()),
            isActive=False
        )
        
        assert status_update.isActive is False
        assert status_update.currentTask is None
        assert status_update.progress == 0

    def test_progress_validation(self):
        """Test progress validation."""
        # Test negative progress
        with pytest.raises(ValidationError):
            WebSocketAgentStatusUpdate(
                sessionId=str(uuid4()),
                isActive=True,
                progress=-1
            )
        
        # Test progress over 100
        with pytest.raises(ValidationError):
            WebSocketAgentStatusUpdate(
                sessionId=str(uuid4()),
                isActive=True,
                progress=101
            )


class TestWebSocketUserTyping:
    """Test WebSocket user typing model."""

    def test_create_typing_event(self):
        """Test creating a typing event."""
        session_id = str(uuid4())
        user_id = str(uuid4())
        
        typing_event = WebSocketUserTyping(
            sessionId=session_id,
            userId=user_id,
            username="john_doe"
        )
        
        assert typing_event.sessionId == session_id
        assert typing_event.userId == user_id
        assert typing_event.username == "john_doe"

    def test_typing_without_username(self):
        """Test typing event without username."""
        typing_event = WebSocketUserTyping(
            sessionId=str(uuid4()),
            userId=str(uuid4())
        )
        
        assert typing_event.username is None


class TestWebSocketConnectionStatus:
    """Test WebSocket connection status model."""

    def test_create_connection_status(self):
        """Test creating connection status."""
        status = WebSocketConnectionStatus(
            state=ConnectionState.CONNECTED,
            message="Successfully connected to real-time messaging",
            connectedUsers=5
        )
        
        assert status.state == ConnectionState.CONNECTED
        assert status.message == "Successfully connected to real-time messaging"
        assert status.connectedUsers == 5

    def test_connection_states(self):
        """Test all connection states."""
        states = [
            ConnectionState.CONNECTING,
            ConnectionState.CONNECTED,
            ConnectionState.DISCONNECTED,
            ConnectionState.ERROR
        ]
        
        for state in states:
            status = WebSocketConnectionStatus(state=state)
            assert status.state == state


class TestWebSocketError:
    """Test WebSocket error model."""

    def test_create_error(self):
        """Test creating WebSocket error."""
        error = WebSocketError(
            code="AUTH_FAILED",
            message="Authentication failed: Invalid token",
            details={"token_expired": True}
        )
        
        assert error.code == "AUTH_FAILED"
        assert error.message == "Authentication failed: Invalid token"
        assert error.details["token_expired"] is True

    def test_error_without_details(self):
        """Test error without details."""
        error = WebSocketError(
            code="CONNECTION_LOST",
            message="Connection to server lost"
        )
        
        assert error.code == "CONNECTION_LOST"
        assert error.details is None


class TestModelIntegration:
    """Test model integration and real-world scenarios."""

    def test_full_event_workflow(self):
        """Test a complete event workflow."""
        session_id = str(uuid4())
        user_id = str(uuid4())
        message_id = str(uuid4())
        
        # Auth request
        auth_request = WebSocketAuthRequest(
            token="jwt-token",
            sessionId=session_id
        )
        
        # Auth response
        auth_response = WebSocketAuthResponse(
            success=True,
            userId=user_id,
            message="Authentication successful"
        )
        
        # Chat message
        chat_message = WebSocketChatMessage(
            sessionId=session_id,
            messageId=message_id,
            role="user",
            content="Plan a trip to Tokyo"
        )
        
        # Agent status update
        status_update = WebSocketAgentStatusUpdate(
            sessionId=session_id,
            isActive=True,
            currentTask="Researching Tokyo travel options",
            progress=25,
            statusMessage="Gathering information about Tokyo attractions"
        )
        
        # Verify all models work together
        assert auth_request.sessionId == session_id
        assert auth_response.userId == user_id
        assert chat_message.sessionId == session_id
        assert status_update.sessionId == session_id

    def test_json_round_trip(self):
        """Test JSON serialization and deserialization."""
        original_message = WebSocketChatMessage(
            sessionId=str(uuid4()),
            messageId=str(uuid4()),
            role="assistant",
            content="I can help you plan your trip to Tokyo!",
            attachments=[{
                "id": str(uuid4()),
                "name": "tokyo_guide.pdf",
                "contentType": "application/pdf"
            }]
        )
        
        # Serialize to JSON
        json_str = original_message.model_dump_json()
        
        # Deserialize from JSON
        data = json.loads(json_str)
        reconstructed_message = WebSocketChatMessage(**data)
        
        # Verify they match
        assert reconstructed_message.sessionId == original_message.sessionId
        assert reconstructed_message.messageId == original_message.messageId
        assert reconstructed_message.role == original_message.role
        assert reconstructed_message.content == original_message.content
        assert len(reconstructed_message.attachments) == len(original_message.attachments)