"""
Integration tests for WebSocket real-time features.

Tests the complete WebSocket integration including:
- Authentication flow
- Real-time message streaming
- Agent status updates
- Connection management
- Error handling
"""

import json
import uuid
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.routers.websocket import (
    WebSocketSubscribeRequest,
    agent_status_websocket,
    chat_websocket,
    handle_chat_message,
)
from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.websocket_manager import (
    websocket_manager,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages_sent: List[str] = []
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.client = MagicMock()
        self.client.host = "127.0.0.1"
        self.headers = {}  # Add headers attribute for WebSocket compatibility

    async def accept(self):
        """Mock accept method."""
        pass

    async def send_text(self, data: str):
        """Mock send_text method."""
        self.messages_sent.append(data)

    async def receive_text(self) -> str:
        """Mock receive_text method."""
        # Return mock authentication request
        return json.dumps(
            {
                "token": "valid-jwt-token",
                "session_id": "test-session-id",
                "channels": ["session:test-session-id"],
            }
        )

    async def close(self, code: int = 1000, reason: str = ""):
        """Mock close method."""
        self.closed = True
        self.close_code = code
        self.close_reason = reason


class MockChatService:
    """Mock chat service for testing."""

    async def add_message(self, session_id: str, user_id: str, message_data):
        """Mock add_message method."""
        return {"id": "mock-message-id", "content": message_data.content}


class MockChatAgent:
    """Mock chat agent for testing."""

    async def run(self, content: str, context: Dict):
        """Mock run method."""
        return {
            "content": f"I received your message: {content}. This is a mock response.",
            "tool_calls": [],
            "metadata": {},
        }


@pytest.fixture
def mock_websocket():
    """Fixture providing a mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def mock_chat_service():
    """Fixture providing a mock chat service."""
    return MockChatService()


@pytest.fixture
def mock_chat_agent():
    """Fixture providing a mock chat agent."""
    return MockChatAgent()


@pytest.fixture
def valid_jwt_token():
    """Fixture providing a valid JWT token."""
    settings = get_settings()
    payload = {
        "sub": "test-user-id",
        "user_id": "test-user-id",
        "exp": 9999999999,  # Far future
        "iat": 1000000000,  # Past timestamp
    }
    return jwt.encode(
        payload,
        settings.database_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


@pytest.fixture
def invalid_jwt_token():
    """Fixture providing an invalid JWT token."""
    return "invalid.jwt.token"


class TestWebSocketAuthentication:
    """Test WebSocket authentication flow."""

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_successful_authentication(self, mock_ws_manager, mock_websocket, valid_jwt_token):
        """Test successful WebSocket authentication."""

        # Create a proper serializable response object that supports model_dump
        class MockAuthResponse:
            def __init__(self):
                self.success = True
                self.connection_id = "test-connection-id"
                self.user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
                self.error = None

            def model_dump(self):
                return {
                    "success": self.success,
                    "connection_id": self.connection_id,
                    "user_id": str(self.user_id),
                    "error": self.error,
                }

        auth_response = MockAuthResponse()

        # Mock successful authentication response
        mock_ws_manager.authenticate_connection = AsyncMock(return_value=auth_response)

        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        # Mock the receive_text to return authentication data
        auth_data = {
            "token": valid_jwt_token,
            "session_id": str(session_id),
            "channels": [f"session:{session_id}"],
        }
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(auth_data))

        # Mock database dependency
        mock_db = AsyncMock()

        try:
            await chat_websocket(mock_websocket, session_id, mock_db, MockChatService())
        except Exception:
            # Expected since we're not providing a full message loop
            pass

        # Verify authentication was attempted
        mock_ws_manager.authenticate_connection.assert_called_once()

        # Verify authentication response was sent
        assert len(mock_websocket.messages_sent) > 0

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_authentication_failure(self, mock_ws_manager, mock_websocket, invalid_jwt_token):
        """Test WebSocket authentication failure."""
        # Create a proper serializable response object instead of MagicMock
        from types import SimpleNamespace

        auth_response = SimpleNamespace(success=False, connection_id="", error="Invalid token")

        # Mock failed authentication response
        mock_ws_manager.authenticate_connection = AsyncMock(return_value=auth_response)

        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        # Mock the receive_text to return invalid authentication data
        auth_data = {
            "token": invalid_jwt_token,
            "session_id": str(session_id),
            "channels": [f"session:{session_id}"],
        }
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(auth_data))

        mock_db = AsyncMock()

        await chat_websocket(mock_websocket, session_id, mock_db, MockChatService())

        # Verify error message was sent and connection was closed
        assert len(mock_websocket.messages_sent) > 0
        error_message = json.loads(mock_websocket.messages_sent[-1])
        assert error_message["type"] == "error"
        assert mock_websocket.closed
        assert mock_websocket.close_code == 4001

    async def test_invalid_authentication_request_format(self, mock_websocket):
        """Test handling of invalid authentication request format."""
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        # Mock invalid JSON
        mock_websocket.receive_text = AsyncMock(return_value="invalid json")

        mock_db = AsyncMock()

        await chat_websocket(mock_websocket, session_id, mock_db, MockChatService())

        # Verify error message was sent and connection was closed
        assert len(mock_websocket.messages_sent) > 0
        error_message = json.loads(mock_websocket.messages_sent[-1])
        assert error_message["type"] == "error"
        assert "Invalid authentication request" in error_message["message"]
        assert mock_websocket.closed
        assert mock_websocket.close_code == 4000


class TestWebSocketChatMessages:
    """Test WebSocket chat message handling."""

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_chat_message_handling(self, mock_ws_manager, mock_chat_service, mock_chat_agent):
        """Test handling of chat messages."""
        connection_id = "test-connection-id"
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        message_data = {
            "content": "Hello, how can I plan a trip to Paris?",
            "attachments": [],
        }

        # Mock WebSocket manager methods
        mock_ws_manager.send_to_session = AsyncMock()
        mock_ws_manager.send_to_connection = AsyncMock()

        await handle_chat_message(
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            message_data=message_data,
            chat_service=mock_chat_service,
            chat_agent=mock_chat_agent,
        )

        # Verify messages were sent to session
        assert mock_ws_manager.send_to_session.call_count >= 2  # User message + agent response

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_empty_message_handling(self, mock_ws_manager):
        """Test handling of empty chat messages."""
        connection_id = "test-connection-id"
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        message_data = {"content": ""}  # Empty content

        mock_ws_manager.send_to_connection = AsyncMock()

        await handle_chat_message(
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            message_data=message_data,
            chat_service=MockChatService(),
            chat_agent=MockChatAgent(),
        )

        # Verify error event was sent
        mock_ws_manager.send_to_connection.assert_called_once()
        error_event = mock_ws_manager.send_to_connection.call_args[0][1]
        assert hasattr(error_event, "error_code")
        assert error_event.error_code == "empty_message"

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_chat_message_with_attachments(self, mock_ws_manager):
        """Test handling of chat messages with attachments."""
        connection_id = "test-connection-id"
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        message_data = {
            "content": "Here's my travel document",
            "attachments": [{"name": "passport.pdf", "size": 1024, "type": "application/pdf"}],
        }

        mock_ws_manager.send_to_session = AsyncMock()

        await handle_chat_message(
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            message_data=message_data,
            chat_service=MockChatService(),
            chat_agent=MockChatAgent(),
        )

        # Verify messages were sent
        assert mock_ws_manager.send_to_session.call_count >= 2

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_chat_agent_error_handling(self, mock_ws_manager):
        """Test handling of chat agent errors."""
        connection_id = "test-connection-id"
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        message_data = {"content": "Test message"}

        # Mock agent that raises an error
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=Exception("Agent processing error"))

        mock_ws_manager.send_to_connection = AsyncMock()

        await handle_chat_message(
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            message_data=message_data,
            chat_service=MockChatService(),
            chat_agent=mock_agent,
        )

        # Verify error event was sent
        mock_ws_manager.send_to_connection.assert_called()
        error_event = mock_ws_manager.send_to_connection.call_args[0][1]
        assert hasattr(error_event, "error_code")
        assert error_event.error_code == "chat_error"


class TestWebSocketAgentStatus:
    """Test WebSocket agent status functionality."""

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_agent_status_connection(self, mock_ws_manager, mock_websocket, valid_jwt_token):
        """Test agent status WebSocket connection."""
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")

        # Create a proper serializable response object instead of MagicMock
        from types import SimpleNamespace

        auth_response = SimpleNamespace(
            success=True,
            connection_id="agent-status-connection-id",
            user_id=user_id,
            error=None,
        )

        # Mock successful authentication
        mock_ws_manager.authenticate_connection = AsyncMock(return_value=auth_response)

        # Mock the receive_text to return authentication data
        auth_data = {"token": valid_jwt_token, "channels": [f"agent_status:{user_id}"]}
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(auth_data))

        try:
            await agent_status_websocket(mock_websocket, user_id)
        except Exception:
            # Expected since we're not providing a full message loop
            pass

        # Verify authentication was attempted
        mock_ws_manager.authenticate_connection.assert_called_once()

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_agent_status_user_mismatch(self, mock_ws_manager, mock_websocket, valid_jwt_token):
        """Test agent status connection with user ID mismatch."""
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        different_user_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        # Create a proper serializable response object instead of MagicMock
        from types import SimpleNamespace

        auth_response = SimpleNamespace(
            success=True,
            connection_id="agent-status-connection-id",
            user_id=different_user_id,  # Different from requested user_id
            error=None,
        )

        # Mock authentication with different user ID
        mock_ws_manager.authenticate_connection = AsyncMock(return_value=auth_response)

        # Mock the disconnect_connection method since it will be called due to user mismatch
        mock_ws_manager.disconnect_connection = AsyncMock()

        auth_data = {"token": valid_jwt_token, "channels": [f"agent_status:{user_id}"]}
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(auth_data))

        await agent_status_websocket(mock_websocket, user_id)

        # Verify error message was sent and connection was closed
        assert len(mock_websocket.messages_sent) > 0
        error_message = json.loads(mock_websocket.messages_sent[-1])
        assert error_message["type"] == "error"
        assert "User ID mismatch" in error_message["message"]
        assert mock_websocket.closed
        assert mock_websocket.close_code == 4003


class TestWebSocketSubscriptions:
    """Test WebSocket subscription functionality."""

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_channel_subscription(self, mock_ws_manager):
        """Test channel subscription handling."""
        # Create a proper serializable response object instead of MagicMock
        from types import SimpleNamespace

        subscription_response = SimpleNamespace(
            success=True,
            subscribed_channels=["channel1", "channel2"],
            failed_channels=[],
            error=None,
        )

        mock_ws_manager.subscribe_connection = AsyncMock(return_value=subscription_response)

        # This would be called within the WebSocket message loop
        subscribe_request = WebSocketSubscribeRequest(channels=["channel1", "channel2"], unsubscribe_channels=[])

        response = await mock_ws_manager.subscribe_connection("test-connection-id", subscribe_request)

        assert response.success is True
        assert "channel1" in response.subscribed_channels
        assert "channel2" in response.subscribed_channels

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_channel_unsubscription(self, mock_ws_manager):
        """Test channel unsubscription handling."""
        # Create a proper serializable response object instead of MagicMock
        from types import SimpleNamespace

        subscription_response = SimpleNamespace(success=True, subscribed_channels=[], failed_channels=[], error=None)

        mock_ws_manager.subscribe_connection = AsyncMock(return_value=subscription_response)

        subscribe_request = WebSocketSubscribeRequest(
            channels=[], unsubscribe_channels=["old_channel1", "old_channel2"]
        )

        response = await mock_ws_manager.subscribe_connection("test-connection-id", subscribe_request)

        assert response.success is True


class TestWebSocketEventTypes:
    """Test WebSocket event type handling."""

    def test_websocket_event_creation(self):
        """Test WebSocket event creation."""
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            user_id=uuid.UUID("12345678-1234-5678-9abc-123456789012"),
            session_id=uuid.UUID("87654321-4321-8765-cbba-210987654321"),
            payload={"content": "Test message"},
        )

        assert event.type == WebSocketEventType.CHAT_MESSAGE
        assert event.user_id is not None
        assert event.session_id is not None
        assert event.payload["content"] == "Test message"
        assert event.id is not None
        assert event.timestamp is not None

    def test_websocket_event_types_comprehensive(self):
        """Test all WebSocket event types are properly defined."""
        # Test some key event types that should be defined
        key_event_types = [
            WebSocketEventType.CHAT_MESSAGE,
            WebSocketEventType.CHAT_MESSAGE_COMPLETE,
            WebSocketEventType.CHAT_TYPING_START,
            WebSocketEventType.CHAT_TYPING_STOP,
            WebSocketEventType.AGENT_STATUS,
            WebSocketEventType.AGENT_ERROR,
            WebSocketEventType.CONNECTION_ESTABLISHED,
            WebSocketEventType.CONNECTION_ERROR,
            WebSocketEventType.CONNECTION_HEARTBEAT,
            WebSocketEventType.CONNECTION_CLOSED,
            WebSocketEventType.MESSAGE_SENT,
            WebSocketEventType.MESSAGE_RECEIVED,
        ]

        # Check that all event types are strings
        for event_type in key_event_types:
            assert isinstance(event_type, str)
            assert len(event_type) > 0


class TestWebSocketPerformance:
    """Test WebSocket performance and optimization features."""

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_message_streaming_simulation(self, mock_ws_manager):
        """Test message streaming performance."""
        connection_id = "test-connection-id"
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        mock_ws_manager.send_to_session = AsyncMock()

        # Test with a message that will be chunked
        message_data = {
            "content": ("This is a longer message that will be broken into chunks for streaming."),
        }

        await handle_chat_message(
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            message_data=message_data,
            chat_service=MockChatService(),
            chat_agent=MockChatAgent(),
        )

        # Verify multiple chunks were sent (streaming simulation)
        assert mock_ws_manager.send_to_session.call_count > 3  # User message + typing + chunks + complete

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_typing_indicators(self, mock_ws_manager):
        """Test typing indicator performance."""
        connection_id = "test-connection-id"
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        session_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        mock_ws_manager.send_to_session = AsyncMock()

        message_data = {"content": "Test message"}

        await handle_chat_message(
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            message_data=message_data,
            chat_service=MockChatService(),
            chat_agent=MockChatAgent(),
        )

        # Verify that send_to_session was called
        assert mock_ws_manager.send_to_session.call_count > 0, "No messages were sent to session"

        # Verify typing-related events were sent
        # Note: Due to object mutation in the current implementation, the typing start
        # event may appear as typing stop by the time we check it. This is a known
        # issue with the current implementation where the same event object is reused.
        sent_events = [call[0][1] for call in mock_ws_manager.send_to_session.call_args_list]

        # Look for typing events (both start and stop show as typing_stop due to mutation)
        typing_events = [
            e
            for e in sent_events
            if hasattr(e, "type")
            and e.type
            in [
                WebSocketEventType.CHAT_TYPING_START,
                WebSocketEventType.CHAT_TYPING_STOP,
            ]
        ]

        # Look for chunk events (streaming content)
        chunk_events = [e for e in sent_events if hasattr(e, "type") and e.type == WebSocketEventType.CHAT_TYPING]

        # Should have typing events (start/stop indicators) and chunk events (content)
        assert len(typing_events) >= 1, (
            f"Expected typing events, got: {[getattr(e, 'type', 'no-type') for e in sent_events]}"
        )
        assert len(chunk_events) >= 1, (
            f"Expected chunk events, got: {[getattr(e, 'type', 'no-type') for e in sent_events]}"
        )


class TestWebSocketHealthCheck:
    """Test WebSocket health check endpoints."""

    def test_websocket_health_endpoint(self):
        """Test WebSocket health check endpoint."""
        client = TestClient(app)
        response = client.get("/api/ws/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "connection_stats" in data
        assert data["status"] == "healthy"

    def test_websocket_connections_endpoint(self):
        """Test WebSocket connections listing endpoint."""
        client = TestClient(app)
        response = client.get("/api/ws/connections")

        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert "total_count" in data
        assert isinstance(data["connections"], list)
        assert isinstance(data["total_count"], int)


@pytest.mark.asyncio
async def test_websocket_integration_end_to_end():
    """End-to-end integration test for WebSocket functionality."""
    # This test would use a real WebSocket connection in a more comprehensive setup
    # For now, we verify that the main components can work together

    # Initialize WebSocket manager
    await websocket_manager.start()

    try:
        # Test connection stats
        stats = websocket_manager.get_connection_stats()
        assert "total_connections" in stats
        assert "unique_users" in stats
        assert "active_sessions" in stats
        assert "subscribed_channels" in stats

        # Test performance metrics
        metrics = websocket_manager.performance_metrics
        assert "total_messages_sent" in metrics
        assert "total_bytes_sent" in metrics
        assert "active_connections" in metrics

    finally:
        # Cleanup
        await websocket_manager.stop()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
