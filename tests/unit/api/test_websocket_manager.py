"""
Tests for WebSocket connection manager.

This module tests the WebSocketManager class which handles WebSocket connections,
authentication, health monitoring, and message routing.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt

from tripsage.api.models.websocket import (
    ConnectionState,
    WebSocketAuthRequest,
    WebSocketAuthResponse,
    WebSocketConnectionStatus,
    WebSocketEvent,
    WebSocketEventType,
)
from tripsage.api.services.websocket_manager import WebSocketManager


@pytest.fixture
def websocket_manager():
    """Create a WebSocketManager instance for testing."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = MagicMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.receive_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_jwt_token():
    """Create a mock JWT token."""
    payload = {
        "user_id": str(uuid4()),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "sub": "test@example.com",
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


class TestWebSocketManager:
    """Test WebSocket connection manager functionality."""

    def test_manager_initialization(self, websocket_manager):
        """Test WebSocket manager initialization."""
        assert websocket_manager.active_connections == {}
        assert websocket_manager.user_connections == {}
        assert websocket_manager.session_connections == {}
        assert websocket_manager.connection_metadata == {}

    @pytest.mark.asyncio
    async def test_add_connection(self, websocket_manager, mock_websocket):
        """Test adding a WebSocket connection."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Verify connection is tracked
        assert connection_id in websocket_manager.active_connections
        assert user_id in websocket_manager.user_connections
        assert session_id in websocket_manager.session_connections
        assert connection_id in websocket_manager.connection_metadata

        # Verify connection metadata
        metadata = websocket_manager.connection_metadata[connection_id]
        assert metadata["user_id"] == user_id
        assert metadata["session_id"] == session_id
        assert isinstance(metadata["connected_at"], datetime)
        assert metadata["last_ping"] is None

    @pytest.mark.asyncio
    async def test_remove_connection(self, websocket_manager, mock_websocket):
        """Test removing a WebSocket connection."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection first
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Remove connection
        await websocket_manager.remove_connection(connection_id)

        # Verify connection is removed
        assert connection_id not in websocket_manager.active_connections
        assert connection_id not in websocket_manager.connection_metadata
        assert connection_id not in websocket_manager.user_connections.get(user_id, [])
        assert connection_id not in websocket_manager.session_connections.get(
            session_id, []
        )

    @pytest.mark.asyncio
    async def test_authenticate_connection_success(
        self, websocket_manager, mock_websocket, mock_jwt_token
    ):
        """Test successful WebSocket authentication."""
        session_id = str(uuid4())
        auth_request = WebSocketAuthRequest(token=mock_jwt_token, sessionId=session_id)

        with patch("tripsage.api.services.websocket_manager.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "user_id": str(uuid4()),
                "exp": datetime.utcnow() + timedelta(hours=1),
            }

            result = await websocket_manager.authenticate_connection(
                mock_websocket, auth_request
            )

            assert isinstance(result, WebSocketAuthResponse)
            assert result.success is True
            assert result.userId is not None
            assert "successful" in result.message.lower()

    @pytest.mark.asyncio
    async def test_authenticate_connection_invalid_token(
        self, websocket_manager, mock_websocket
    ):
        """Test WebSocket authentication with invalid token."""
        session_id = str(uuid4())
        auth_request = WebSocketAuthRequest(token="invalid-token", sessionId=session_id)

        result = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert isinstance(result, WebSocketAuthResponse)
        assert result.success is False
        assert result.userId is None
        assert "invalid" in result.message.lower() or "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_authenticate_connection_expired_token(
        self, websocket_manager, mock_websocket
    ):
        """Test WebSocket authentication with expired token."""
        # Create an expired token
        payload = {
            "user_id": str(uuid4()),
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=2),
        }
        expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")

        session_id = str(uuid4())
        auth_request = WebSocketAuthRequest(token=expired_token, sessionId=session_id)

        result = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert isinstance(result, WebSocketAuthResponse)
        assert result.success is False
        assert result.userId is None

    @pytest.mark.asyncio
    async def test_send_to_user(self, websocket_manager, mock_websocket):
        """Test sending a message to a specific user."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Create event to send
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Hello user!"},
        )

        # Send to user
        success = await websocket_manager.send_to_user(user_id, event)

        assert success is True
        mock_websocket.send_text.assert_called_once()

        # Verify the sent data
        sent_data = mock_websocket.send_text.call_args[0][0]
        assert "chat_message" in sent_data
        assert "Hello user!" in sent_data

    @pytest.mark.asyncio
    async def test_send_to_user_not_connected(self, websocket_manager):
        """Test sending a message to a user who is not connected."""
        user_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=str(uuid4()),
            payload={"content": "Hello user!"},
        )

        success = await websocket_manager.send_to_user(user_id, event)
        assert success is False

    @pytest.mark.asyncio
    async def test_send_to_session(self, websocket_manager, mock_websocket):
        """Test sending a message to all connections in a session."""
        session_id = str(uuid4())
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        connection1_id = str(uuid4())
        connection2_id = str(uuid4())

        mock_websocket2 = MagicMock(spec=WebSocket)
        mock_websocket2.send_text = AsyncMock()

        # Add two connections to the same session
        await websocket_manager.add_connection(
            connection_id=connection1_id,
            websocket=mock_websocket,
            user_id=user1_id,
            session_id=session_id,
        )

        await websocket_manager.add_connection(
            connection_id=connection2_id,
            websocket=mock_websocket2,
            user_id=user2_id,
            session_id=session_id,
        )

        # Create event to send
        event = WebSocketEvent(
            type=WebSocketEventType.AGENT_STATUS_UPDATE,
            sessionId=session_id,
            payload={"status": "processing"},
        )

        # Send to session
        success_count = await websocket_manager.send_to_session(session_id, event)

        assert success_count == 2
        mock_websocket.send_text.assert_called_once()
        mock_websocket2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, websocket_manager, mock_websocket):
        """Test broadcasting a message to all connections."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Create event to broadcast
        event = WebSocketEvent(
            type=WebSocketEventType.CONNECTION_STATUS,
            sessionId=session_id,
            payload={"message": "System maintenance in 5 minutes"},
        )

        # Broadcast to all
        success_count = await websocket_manager.broadcast_to_all(event)

        assert success_count == 1
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_connections(self, websocket_manager, mock_websocket):
        """Test health checking connections."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Perform health check
        healthy_count = await websocket_manager.health_check_connections()

        assert healthy_count == 1
        mock_websocket.send_text.assert_called_once()

        # Verify ping was sent
        sent_data = mock_websocket.send_text.call_args[0][0]
        assert "ping" in sent_data.lower()

    @pytest.mark.asyncio
    async def test_health_check_removes_unhealthy_connections(
        self, websocket_manager, mock_websocket
    ):
        """Test that health check removes unhealthy connections."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Mock WebSocket that will fail on send
        mock_websocket.send_text.side_effect = Exception("Connection lost")

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Perform health check
        healthy_count = await websocket_manager.health_check_connections()

        assert healthy_count == 0
        # Connection should be removed
        assert connection_id not in websocket_manager.active_connections

    @pytest.mark.asyncio
    async def test_get_connection_count(self, websocket_manager, mock_websocket):
        """Test getting connection count."""
        assert websocket_manager.get_connection_count() == 0

        # Add connection
        await websocket_manager.add_connection(
            connection_id=str(uuid4()),
            websocket=mock_websocket,
            user_id=str(uuid4()),
            session_id=str(uuid4()),
        )

        assert websocket_manager.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_get_user_count(self, websocket_manager, mock_websocket):
        """Test getting unique user count."""
        user_id = str(uuid4())
        session_id = str(uuid4())

        assert websocket_manager.get_user_count() == 0

        # Add two connections for the same user
        await websocket_manager.add_connection(
            connection_id=str(uuid4()),
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        mock_websocket2 = MagicMock(spec=WebSocket)
        await websocket_manager.add_connection(
            connection_id=str(uuid4()),
            websocket=mock_websocket2,
            user_id=user_id,
            session_id=session_id,
        )

        # Should still count as 1 unique user
        assert websocket_manager.get_user_count() == 1

    @pytest.mark.asyncio
    async def test_get_session_connections(self, websocket_manager, mock_websocket):
        """Test getting connections for a specific session."""
        session_id = str(uuid4())
        connection_id = str(uuid4())

        # Initially no connections
        connections = websocket_manager.get_session_connections(session_id)
        assert len(connections) == 0

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=str(uuid4()),
            session_id=session_id,
        )

        # Should now have one connection
        connections = websocket_manager.get_session_connections(session_id)
        assert len(connections) == 1
        assert connections[0] == connection_id

    @pytest.mark.asyncio
    async def test_get_connection_stats(self, websocket_manager, mock_websocket):
        """Test getting connection statistics."""
        # Initially empty stats
        stats = websocket_manager.get_connection_stats()
        assert stats["total_connections"] == 0
        assert stats["unique_users"] == 0
        assert stats["active_sessions"] == 0

        # Add connection
        await websocket_manager.add_connection(
            connection_id=str(uuid4()),
            websocket=mock_websocket,
            user_id=str(uuid4()),
            session_id=str(uuid4()),
        )

        # Check updated stats
        stats = websocket_manager.get_connection_stats()
        assert stats["total_connections"] == 1
        assert stats["unique_users"] == 1
        assert stats["active_sessions"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self, websocket_manager, mock_websocket):
        """Test cleanup of stale connections."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Manually set connection as stale (older than threshold)
        metadata = websocket_manager.connection_metadata[connection_id]
        metadata["connected_at"] = datetime.utcnow() - timedelta(hours=2)
        metadata["last_ping"] = datetime.utcnow() - timedelta(minutes=10)

        # Cleanup stale connections
        cleaned_count = await websocket_manager.cleanup_stale_connections(
            max_idle_minutes=5
        )

        assert cleaned_count == 1
        assert connection_id not in websocket_manager.active_connections

    @pytest.mark.asyncio
    async def test_send_connection_status(self, websocket_manager, mock_websocket):
        """Test sending connection status updates."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Send connection status
        status = WebSocketConnectionStatus(
            state=ConnectionState.CONNECTED,
            message="Connection established",
            connectedUsers=1,
        )

        success = await websocket_manager.send_connection_status(user_id, status)

        assert success is True
        mock_websocket.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_during_send(self, websocket_manager, mock_websocket):
        """Test error handling when sending messages fails."""
        connection_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Add connection
        await websocket_manager.add_connection(
            connection_id=connection_id,
            websocket=mock_websocket,
            user_id=user_id,
            session_id=session_id,
        )

        # Mock websocket to raise exception on send
        mock_websocket.send_text.side_effect = WebSocketDisconnect()

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Test message"},
        )

        # Send should handle the exception gracefully
        success = await websocket_manager.send_to_user(user_id, event)

        assert success is False
        # Connection should be cleaned up
        assert connection_id not in websocket_manager.active_connections
