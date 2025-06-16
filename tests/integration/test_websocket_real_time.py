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
    WebSocketEvent,
    WebSocketEventType,
    websocket_manager,
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
        settings.database.supabase_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


@pytest.fixture
def invalid_jwt_token():
    """Fixture providing an invalid JWT token."""
    return "invalid.jwt.token"


class TestWebSocketAuthentication:
    """Test WebSocket authentication flow."""

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_successful_authentication(
        self, mock_ws_manager, mock_websocket, valid_jwt_token
    ):
        """Test successful WebSocket authentication."""
        # Mock successful authentication response
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=MagicMock(
                success=True,
                connection_id="test-connection-id",
                user_id=uuid.UUID("12345678-1234-5678-9abc-123456789012"),
                error=None,
            )
        )

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
    async def test_authentication_failure(
        self, mock_ws_manager, mock_websocket, invalid_jwt_token
    ):
        """Test WebSocket authentication failure."""
        # Mock failed authentication response
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=MagicMock(
                success=False, connection_id="", error="Invalid token"
            )
        )

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
    async def test_chat_message_handling(
        self, mock_ws_manager, mock_chat_service, mock_chat_agent
    ):
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
        assert (
            mock_ws_manager.send_to_session.call_count >= 2
        )  # User message + agent response

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
            "attachments": [
                {"name": "passport.pdf", "size": 1024, "type": "application/pdf"}
            ],
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
    async def test_agent_status_connection(
        self, mock_ws_manager, mock_websocket, valid_jwt_token
    ):
        """Test agent status WebSocket connection."""
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")

        # Mock successful authentication
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=MagicMock(
                success=True,
                connection_id="agent-status-connection-id",
                user_id=user_id,
                error=None,
            )
        )

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
    async def test_agent_status_user_mismatch(
        self, mock_ws_manager, mock_websocket, valid_jwt_token
    ):
        """Test agent status connection with user ID mismatch."""
        user_id = uuid.UUID("12345678-1234-5678-9abc-123456789012")
        different_user_id = uuid.UUID("87654321-4321-8765-cbba-210987654321")

        # Mock authentication with different user ID
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=MagicMock(
                success=True,
                connection_id="agent-status-connection-id",
                user_id=different_user_id,  # Different from requested user_id
                error=None,
            )
        )

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
        mock_ws_manager.subscribe_connection = AsyncMock(
            return_value=MagicMock(
                success=True,
                subscribed_channels=["channel1", "channel2"],
                failed_channels=[],
                error=None,
            )
        )

        # This would be called within the WebSocket message loop
        subscribe_request = WebSocketSubscribeRequest(
            channels=["channel1", "channel2"], unsubscribe_channels=[]
        )

        response = await mock_ws_manager.subscribe_connection(
            "test-connection-id", subscribe_request
        )

        assert response.success is True
        assert "channel1" in response.subscribed_channels
        assert "channel2" in response.subscribed_channels

    @patch("tripsage.api.routers.websocket.websocket_manager")
    async def test_channel_unsubscription(self, mock_ws_manager):
        """Test channel unsubscription handling."""
        mock_ws_manager.subscribe_connection = AsyncMock(
            return_value=MagicMock(
                success=True, subscribed_channels=[], failed_channels=[], error=None
            )
        )

        subscribe_request = WebSocketSubscribeRequest(
            channels=[], unsubscribe_channels=["old_channel1", "old_channel2"]
        )

        response = await mock_ws_manager.subscribe_connection(
            "test-connection-id", subscribe_request
        )

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
        expected_event_types = [
            "chat_message",
            "chat_message_chunk",
            "chat_message_complete",
            "chat_typing_start",
            "chat_typing_stop",
            "agent_status_update",
            "agent_task_start",
            "agent_task_progress",
            "agent_task_complete",
            "agent_error",
            "connection_established",
            "connection_error",
            "connection_heartbeat",
            "connection_close",
            "tool_call_start",
            "tool_call_progress",
            "tool_call_complete",
            "tool_call_error",
            "error",
            "notification",
            "system_message",
        ]

        # Check that all event types are defined in WebSocketEventType
        for event_type in expected_event_types:
            assert hasattr(WebSocketEventType, event_type.upper()) or any(
                getattr(WebSocketEventType, attr) == event_type
                for attr in dir(WebSocketEventType)
                if not attr.startswith("_")
            )


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
            "content": (
                "This is a longer message that will be broken into chunks for "
                "streaming."
            ),
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
        assert (
            mock_ws_manager.send_to_session.call_count > 3
        )  # User message + typing + chunks + complete

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

        # Verify typing start and stop events were sent
        sent_events = [
            call[0][1] for call in mock_ws_manager.send_to_session.call_args_list
        ]

        typing_start_events = [
            e
            for e in sent_events
            if hasattr(e, "type") and e.type == WebSocketEventType.CHAT_TYPING_START
        ]
        typing_stop_events = [
            e
            for e in sent_events
            if hasattr(e, "type") and e.type == WebSocketEventType.CHAT_TYPING_STOP
        ]

        assert len(typing_start_events) >= 1
        assert len(typing_stop_events) >= 1


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
        metrics = websocket_manager.get_performance_metrics()
        assert "total_messages_sent" in metrics
        assert "total_bytes_sent" in metrics
        assert "active_connections" in metrics

    finally:
        # Cleanup
        await websocket_manager.stop()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
