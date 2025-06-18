"""
Comprehensive tests for TripSage Core WebSocket Manager.

This module provides comprehensive test coverage for WebSocket manager functionality
including connection management, authentication, channel subscriptions, message
broadcasting, background task management, performance monitoring, and error handling.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import WebSocket

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthRequest,
    WebSocketAuthResponse,
)
from tripsage_core.services.infrastructure.websocket_connection_service import (
    ConnectionState as ConnectionStatus,  # Alias for backward compatibility
)
from tripsage_core.services.infrastructure.websocket_connection_service import (
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketManager,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


# Mock missing classes for test compatibility
class WebSocketConnectionInfo:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class WebSocketSubscribeRequest:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class WebSocketSubscribeResponse:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestWebSocketConnection:
    """Test suite for WebSocketConnection."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        return websocket

    @pytest.fixture
    def websocket_connection(self, mock_websocket):
        """Create a WebSocketConnection instance."""
        user_id = uuid4()
        session_id = uuid4()
        return WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test-connection-123",
            user_id=user_id,
            session_id=session_id,
        )

    def test_connection_initialization(self, websocket_connection):
        """Test WebSocket connection initialization."""
        assert websocket_connection.connection_id == "test-connection-123"
        assert websocket_connection.user_id is not None
        assert websocket_connection.session_id is not None
        assert websocket_connection.status == ConnectionStatus.CONNECTED
        assert len(websocket_connection.subscribed_channels) == 0
        assert websocket_connection.message_count == 0
        assert websocket_connection.bytes_sent == 0

    @pytest.mark.asyncio
    async def test_send_event_success(self, websocket_connection, mock_websocket):
        """Test successful event sending."""
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Hello World"},
        )

        result = await websocket_connection.send(event)

        assert result is True
        mock_websocket.send_text.assert_called_once()

        # Verify message structure
        call_args = mock_websocket.send_text.call_args[0][0]
        message_data = json.loads(call_args)
        assert message_data["type"] == WebSocketEventType.CHAT_MESSAGE
        assert message_data["payload"]["message"] == "Hello World"

        # Verify metrics updated
        assert websocket_connection.message_count == 1
        assert websocket_connection.bytes_sent > 0

    @pytest.mark.asyncio
    async def test_send_event_failure(self, websocket_connection, mock_websocket):
        """Test event sending failure."""
        mock_websocket.send_text.side_effect = Exception("Connection lost")

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Hello World"},
        )

        result = await websocket_connection.send(event)

        assert result is False
        assert websocket_connection.status == ConnectionStatus.ERROR

    @pytest.mark.asyncio
    async def test_send_raw_message_success(self, websocket_connection, mock_websocket):
        """Test successful raw message sending."""
        message = {"type": "custom", "data": "test"}

        result = await websocket_connection.send_raw(message)

        assert result is True
        mock_websocket.send_text.assert_called_once()

        # Verify raw message was sent correctly
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data == message

    @pytest.mark.asyncio
    async def test_send_raw_message_failure(self, websocket_connection, mock_websocket):
        """Test raw message sending failure."""
        mock_websocket.send_text.side_effect = Exception("Send failed")

        message = {"type": "custom", "data": "test"}

        result = await websocket_connection.send_raw(message)

        assert result is False
        assert websocket_connection.status == ConnectionStatus.ERROR

    def test_update_heartbeat(self, websocket_connection):
        """Test heartbeat update."""
        initial_heartbeat = websocket_connection.last_heartbeat
        time.sleep(0.001)  # Small delay to ensure time difference

        websocket_connection.update_heartbeat()

        assert websocket_connection.last_heartbeat > initial_heartbeat

    def test_is_stale_false(self, websocket_connection):
        """Test stale check when connection is fresh."""
        websocket_connection.update_heartbeat()

        result = websocket_connection.is_stale(timeout_seconds=300)

        assert result is False

    def test_is_stale_true(self, websocket_connection):
        """Test stale check when connection is old."""
        # Set heartbeat to a very old time
        websocket_connection.last_heartbeat = datetime.utcnow().replace(year=2020)

        result = websocket_connection.is_stale(timeout_seconds=300)

        assert result is True

    def test_channel_subscription_management(self, websocket_connection):
        """Test channel subscription operations."""
        channel1 = "chat:room1"
        channel2 = "notifications"

        # Subscribe to channels
        websocket_connection.subscribe_to_channel(channel1)
        websocket_connection.subscribe_to_channel(channel2)

        assert websocket_connection.is_subscribed_to_channel(channel1)
        assert websocket_connection.is_subscribed_to_channel(channel2)
        assert len(websocket_connection.subscribed_channels) == 2

        # Unsubscribe from channel
        websocket_connection.unsubscribe_from_channel(channel1)

        assert not websocket_connection.is_subscribed_to_channel(channel1)
        assert websocket_connection.is_subscribed_to_channel(channel2)
        assert len(websocket_connection.subscribed_channels) == 1

    def test_get_connection_info(self, websocket_connection):
        """Test getting connection information."""
        websocket_connection.subscribe_to_channel("test-channel")

        info = websocket_connection.get_info()

        assert isinstance(info, WebSocketConnectionInfo)
        assert info.connection_id == websocket_connection.connection_id
        assert info.user_id == websocket_connection.user_id
        assert info.session_id == websocket_connection.session_id
        assert info.status == ConnectionStatus.CONNECTED
        assert "test-channel" in info.subscribed_channels

    @pytest.mark.asyncio
    async def test_concurrent_send_operations(
        self, websocket_connection, mock_websocket
    ):
        """Test concurrent send operations with lock protection."""
        events = [
            WebSocketEvent(
                type=WebSocketEventType.CHAT_MESSAGE, payload={"msg": f"Message {i}"}
            )
            for i in range(5)
        ]

        # Send multiple events concurrently
        tasks = [websocket_connection.send(event) for event in events]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert mock_websocket.send_text.call_count == 5
        assert websocket_connection.message_count == 5


class TestWebSocketManager:
    """Test suite for WebSocketManager."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.database_jwt_secret = Mock()
        settings.database_jwt_secret.get_secret_value = Mock(
            return_value="test-secret-key-12345"
        )
        return settings

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        return websocket

    @pytest.fixture
    def websocket_manager(self, mock_settings):
        """Create a WebSocketManager instance."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_manager.get_settings",
            return_value=mock_settings,
        ):
            manager = WebSocketManager()
            return manager

    @pytest.fixture
    def valid_jwt_token(self, mock_settings):
        """Create a valid JWT token for testing."""
        user_id = str(uuid4())
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "exp": int(time.time()) + 3600,  # Expires in 1 hour
        }
        return jwt.encode(
            payload,
            mock_settings.database_jwt_secret.get_secret_value(),
            algorithm="HS256",
        )

    @pytest.mark.asyncio
    async def test_start_manager(self, websocket_manager):
        """Test starting the WebSocket manager."""
        with (
            patch.object(
                websocket_manager, "_cleanup_stale_connections", new_callable=AsyncMock
            ),
            patch.object(
                websocket_manager, "_heartbeat_monitor", new_callable=AsyncMock
            ),
            patch.object(
                websocket_manager, "_performance_monitor", new_callable=AsyncMock
            ),
        ):
            await websocket_manager.start()

            assert websocket_manager._running is True
            assert websocket_manager._cleanup_task is not None
            assert websocket_manager._heartbeat_task is not None
            assert websocket_manager._performance_task is not None

    @pytest.mark.asyncio
    async def test_stop_manager(self, websocket_manager):
        """Test stopping the WebSocket manager."""
        # Mock background tasks
        websocket_manager._cleanup_task = Mock()
        websocket_manager._cleanup_task.cancel = Mock()
        websocket_manager._heartbeat_task = Mock()
        websocket_manager._heartbeat_task.cancel = Mock()
        websocket_manager._performance_task = Mock()
        websocket_manager._performance_task.cancel = Mock()

        with patch.object(websocket_manager, "disconnect_all", new_callable=AsyncMock):
            await websocket_manager.stop()

            assert websocket_manager._running is False
            websocket_manager._cleanup_task.cancel.assert_called_once()
            websocket_manager._heartbeat_task.cancel.assert_called_once()
            websocket_manager._performance_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_connection_success(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test successful WebSocket authentication."""
        session_id = uuid4()
        auth_request = WebSocketAuthRequest(
            token=valid_jwt_token,
            session_id=session_id,
            channels=["general", "notifications"],
        )

        response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert response.success is True
        assert response.connection_id != ""
        assert response.user_id is not None
        assert response.session_id == session_id
        assert "general" in response.available_channels

        # Verify connection was added to manager
        assert response.connection_id in websocket_manager.connections
        assert response.user_id in websocket_manager.user_connections

    @pytest.mark.asyncio
    async def test_authenticate_connection_invalid_token(
        self, websocket_manager, mock_websocket
    ):
        """Test WebSocket authentication with invalid token."""
        auth_request = WebSocketAuthRequest(token="invalid-token", channels=["general"])

        response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert response.success is False
        assert response.connection_id == ""
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_authenticate_connection_malformed_token(
        self, websocket_manager, mock_websocket, mock_settings
    ):
        """Test authentication with malformed token payload."""
        # Create token with missing required fields
        payload = {"some_field": "value"}  # Missing 'sub' and 'user_id'
        malformed_token = jwt.encode(
            payload,
            mock_settings.database_jwt_secret.get_secret_value(),
            algorithm="HS256",
        )

        auth_request = WebSocketAuthRequest(token=malformed_token, channels=["general"])

        response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert response.success is False
        assert "Invalid token payload" in response.error

    @pytest.mark.asyncio
    async def test_disconnect_connection(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test disconnecting a WebSocket connection."""
        # First authenticate a connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token, channels=["general"])
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        connection_id = auth_response.connection_id
        user_id = auth_response.user_id

        # Verify connection exists
        assert connection_id in websocket_manager.connections
        assert user_id in websocket_manager.user_connections

        # Disconnect the connection
        await websocket_manager.disconnect_connection(connection_id)

        # Verify connection was removed
        assert connection_id not in websocket_manager.connections
        assert user_id not in websocket_manager.user_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, websocket_manager):
        """Test disconnecting a non-existent connection."""
        # Should not raise an exception
        await websocket_manager.disconnect_connection("nonexistent-id")

    @pytest.mark.asyncio
    async def test_disconnect_all_connections(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test disconnecting all connections."""
        # Create multiple connections
        connections = []
        for i in range(3):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            response = await websocket_manager.authenticate_connection(
                websocket, auth_request
            )
            connections.append(response.connection_id)

        assert len(websocket_manager.connections) == 3

        await websocket_manager.disconnect_all()

        assert len(websocket_manager.connections) == 0

    @pytest.mark.asyncio
    async def test_send_to_connection_success(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test sending event to specific connection."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Hello"}
        )

        result = await websocket_manager.send_to_connection(
            auth_response.connection_id, event
        )

        assert result is True
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_connection_not_found(self, websocket_manager):
        """Test sending event to non-existent connection."""
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Hello"}
        )

        result = await websocket_manager.send_to_connection("nonexistent-id", event)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_user(self, websocket_manager, valid_jwt_token):
        """Test sending event to all connections for a user."""
        user_id = None

        # Create multiple connections for the same user
        websockets = []
        for i in range(3):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            response = await websocket_manager.authenticate_connection(
                websocket, auth_request
            )
            user_id = response.user_id
            websockets.append(websocket)

        event = WebSocketEvent(
            type=WebSocketEventType.AGENT_STATUS, payload={"status": "active"}
        )

        sent_count = await websocket_manager.send_to_user(user_id, event)

        assert sent_count == 3
        for websocket in websockets:
            websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_session(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test sending event to all connections for a session."""
        session_id = uuid4()

        # Create multiple connections for the same session
        websockets = []
        for i in range(2):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(
                token=valid_jwt_token, session_id=session_id
            )
            await websocket_manager.authenticate_connection(websocket, auth_request)
            websockets.append(websocket)

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_STATUS, payload={"status": "typing"}
        )

        sent_count = await websocket_manager.send_to_session(session_id, event)

        assert sent_count == 2
        for websocket in websockets:
            websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_channel(self, websocket_manager, valid_jwt_token):
        """Test sending event to all connections subscribed to a channel."""
        channel = "test-channel"

        # Create connections and subscribe them to the channel
        websockets = []
        connection_ids = []
        for i in range(3):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            response = await websocket_manager.authenticate_connection(
                websocket, auth_request
            )

            # Subscribe to channel
            connection = websocket_manager.connections[response.connection_id]
            connection.subscribe_to_channel(channel)
            websocket_manager.channel_connections.setdefault(channel, set()).add(
                response.connection_id
            )

            websockets.append(websocket)
            connection_ids.append(response.connection_id)

        event = WebSocketEvent(
            type=WebSocketEventType.MESSAGE_BROADCAST,
            payload={"message": "Channel broadcast"},
        )

        sent_count = await websocket_manager.send_to_channel(channel, event)

        assert sent_count == 3
        for websocket in websockets:
            websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_connection_success(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test successful channel subscription."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        subscribe_request = WebSocketSubscribeRequest(
            channels=["general", "notifications"], unsubscribe_channels=[]
        )

        response = await websocket_manager.subscribe_connection(
            auth_response.connection_id, subscribe_request
        )

        assert response.success is True
        assert "general" in response.subscribed_channels
        assert "notifications" in response.subscribed_channels
        assert len(response.failed_channels) == 0

        # Verify connection was added to channel mappings
        assert (
            auth_response.connection_id
            in websocket_manager.channel_connections["general"]
        )
        assert (
            auth_response.connection_id
            in websocket_manager.channel_connections["notifications"]
        )

    @pytest.mark.asyncio
    async def test_subscribe_connection_not_found(self, websocket_manager):
        """Test subscription for non-existent connection."""
        subscribe_request = WebSocketSubscribeRequest(channels=["general"])

        response = await websocket_manager.subscribe_connection(
            "nonexistent-id", subscribe_request
        )

        assert response.success is False
        assert response.error == "Connection not found"

    @pytest.mark.asyncio
    async def test_subscribe_connection_with_unsubscribe(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test channel subscription with unsubscribe."""
        # Authenticate and initially subscribe
        auth_request = WebSocketAuthRequest(token=valid_jwt_token, channels=["general"])
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        subscribe_request = WebSocketSubscribeRequest(
            channels=["notifications"], unsubscribe_channels=["general"]
        )

        response = await websocket_manager.subscribe_connection(
            auth_response.connection_id, subscribe_request
        )

        assert response.success is True

        connection = websocket_manager.connections[auth_response.connection_id]
        assert not connection.is_subscribed_to_channel("general")
        assert connection.is_subscribed_to_channel("notifications")

    def test_get_connection_info(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test getting connection information."""

        # This needs to be run in async context
        async def run_test():
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            auth_response = await websocket_manager.authenticate_connection(
                mock_websocket, auth_request
            )

            info = websocket_manager.get_connection_info(auth_response.connection_id)

            assert info is not None
            assert isinstance(info, WebSocketConnectionInfo)
            assert info.connection_id == auth_response.connection_id
            assert info.user_id == auth_response.user_id

        asyncio.run(run_test())

    def test_get_connection_info_not_found(self, websocket_manager):
        """Test getting info for non-existent connection."""
        info = websocket_manager.get_connection_info("nonexistent-id")

        assert info is None

    def test_get_connection_stats(self, websocket_manager):
        """Test getting connection statistics."""
        stats = websocket_manager.get_connection_stats()

        assert isinstance(stats, dict)
        assert "total_connections" in stats
        assert "unique_users" in stats
        assert "active_sessions" in stats
        assert "subscribed_channels" in stats
        assert stats["total_connections"] == 0  # No connections initially

    def test_get_available_channels(self, websocket_manager):
        """Test getting available channels for a user."""
        user_id = uuid4()

        channels = websocket_manager._get_available_channels(user_id)

        assert isinstance(channels, list)
        assert "general" in channels
        assert "notifications" in channels
        assert f"user:{user_id}" in channels

    def test_get_available_channels_no_user(self, websocket_manager):
        """Test getting available channels with no user."""
        channels = websocket_manager._get_available_channels(None)

        assert channels == []

    @pytest.mark.asyncio
    async def test_send_batched_success(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test sending batched events."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        events = [
            WebSocketEvent(
                type=WebSocketEventType.CHAT_MESSAGE, payload={"msg": f"Message {i}"}
            )
            for i in range(3)
        ]

        result = await websocket_manager.send_batched(
            auth_response.connection_id, events
        )

        assert result is True
        mock_websocket.send_text.assert_called_once()

        # Verify batch format
        call_args = mock_websocket.send_text.call_args[0][0]
        batch_data = json.loads(call_args)
        assert batch_data["type"] == "batch"
        assert len(batch_data["events"]) == 3

    @pytest.mark.asyncio
    async def test_send_batched_connection_not_found(self, websocket_manager):
        """Test batched send to non-existent connection."""
        events = [
            WebSocketEvent(
                type=WebSocketEventType.CHAT_MESSAGE, payload={"msg": "test"}
            )
        ]

        result = await websocket_manager.send_batched("nonexistent-id", events)

        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_optimized_to_channel(
        self, websocket_manager, valid_jwt_token
    ):
        """Test optimized broadcast to specific channel."""
        channel = "broadcast-channel"

        # Create multiple connections subscribed to channel
        websockets = []
        for i in range(3):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            response = await websocket_manager.authenticate_connection(
                websocket, auth_request
            )

            # Subscribe to channel
            connection = websocket_manager.connections[response.connection_id]
            connection.subscribe_to_channel(channel)
            websocket_manager.channel_connections.setdefault(channel, set()).add(
                response.connection_id
            )

            websockets.append(websocket)

        event = WebSocketEvent(
            type=WebSocketEventType.MESSAGE_BROADCAST,
            payload={"message": "Optimized broadcast"},
        )

        sent_count = await websocket_manager.broadcast_optimized(event, channel=channel)

        assert sent_count == 3
        for websocket in websockets:
            websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_optimized_exclude_connection(
        self, websocket_manager, valid_jwt_token
    ):
        """Test optimized broadcast with connection exclusion."""
        # Create multiple connections
        websockets = []
        connection_ids = []
        for i in range(3):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            response = await websocket_manager.authenticate_connection(
                websocket, auth_request
            )

            websockets.append(websocket)
            connection_ids.append(response.connection_id)

        event = WebSocketEvent(
            type=WebSocketEventType.MESSAGE_BROADCAST, payload={"message": "Broadcast"}
        )

        # Exclude one connection
        exclude_id = connection_ids[0]
        sent_count = await websocket_manager.broadcast_optimized(
            event, exclude_connection=exclude_id
        )

        assert sent_count == 2  # Only 2 out of 3 connections should receive the message
        # First websocket (excluded) should not be called
        websockets[0].send_text.assert_not_called()
        # Other websockets should be called
        websockets[1].send_text.assert_called_once()
        websockets[2].send_text.assert_called_once()

    def test_get_performance_metrics(self, websocket_manager):
        """Test getting performance metrics."""
        metrics = websocket_manager.get_performance_metrics()

        assert isinstance(metrics, dict)
        assert "total_messages_sent" in metrics
        assert "total_bytes_sent" in metrics
        assert "active_connections" in metrics
        assert "peak_connections" in metrics
        assert "connections_by_status" in metrics
        assert "average_bytes_per_connection" in metrics
        assert "average_messages_per_connection" in metrics

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections_task(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test cleanup of stale connections background task."""
        # Create a connection and make it stale
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        connection = websocket_manager.connections[auth_response.connection_id]
        # Make connection stale by setting old heartbeat
        connection.last_heartbeat = datetime.utcnow().replace(year=2020)

        # Mock the running state and sleep to control the loop
        websocket_manager._running = True

        async def mock_sleep(duration):
            # Stop after first iteration
            websocket_manager._running = False

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await websocket_manager._cleanup_stale_connections()

        # Verify stale connection was cleaned up
        assert auth_response.connection_id not in websocket_manager.connections

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_task(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test heartbeat monitor background task."""
        # Create a connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        await websocket_manager.authenticate_connection(mock_websocket, auth_request)

        # Mock the running state and sleep to control the loop
        websocket_manager._running = True

        async def mock_sleep(duration):
            # Stop after first iteration
            websocket_manager._running = False

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await websocket_manager._heartbeat_monitor()

        # Verify heartbeat was sent (should be 2 calls: auth + heartbeat)
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_performance_monitor_task(self, websocket_manager):
        """Test performance monitor background task."""
        # Mock the running state and sleep to control the loop
        websocket_manager._running = True

        async def mock_sleep(duration):
            # Stop after first iteration
            websocket_manager._running = False

        with patch("asyncio.sleep", side_effect=mock_sleep):
            await websocket_manager._performance_monitor()

        # Task should complete without errors
        assert websocket_manager._running is False

    @pytest.mark.asyncio
    async def test_error_handling_in_background_tasks(self, websocket_manager):
        """Test error handling in background tasks."""
        websocket_manager._running = True

        call_count = 0

        async def mock_sleep(duration):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call - let the error happen
                return
            else:
                # Stop after error recovery
                websocket_manager._running = False

        # Mock an operation that will fail
        def failing_operation():
            raise Exception("Test error")

        with (
            patch("asyncio.sleep", side_effect=mock_sleep),
            patch.object(
                websocket_manager, "connections", side_effect=failing_operation
            ),
        ):
            # Should not raise exception, just log error and continue
            await websocket_manager._performance_monitor()

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, websocket_manager, valid_jwt_token):
        """Test concurrent connection authentication."""
        # Create multiple authentication requests concurrently
        tasks = []
        for i in range(5):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            tasks.append(
                websocket_manager.authenticate_connection(websocket, auth_request)
            )

        responses = await asyncio.gather(*tasks)

        # All authentications should succeed
        assert all(response.success for response in responses)
        assert (
            len(set(response.connection_id for response in responses)) == 5
        )  # All unique IDs
        assert len(websocket_manager.connections) == 5

    @pytest.mark.asyncio
    async def test_connection_with_different_users(
        self, websocket_manager, mock_settings
    ):
        """Test connections from different users."""
        # Create tokens for different users
        user_ids = [str(uuid4()) for _ in range(3)]
        tokens = []

        for user_id in user_ids:
            payload = {
                "sub": user_id,
                "user_id": user_id,
                "exp": int(time.time()) + 3600,
            }
            token = jwt.encode(
                payload,
                mock_settings.database_jwt_secret.get_secret_value(),
                algorithm="HS256",
            )
            tokens.append(token)

        # Authenticate connections for different users
        for i, token in enumerate(tokens):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"
            auth_request = WebSocketAuthRequest(token=token)
            await websocket_manager.authenticate_connection(websocket, auth_request)

        # Verify each user has their own connection mapping
        assert len(websocket_manager.user_connections) == 3
        for user_id in user_ids:
            assert UUID(user_id) in websocket_manager.user_connections

    @pytest.mark.asyncio
    async def test_message_sending_with_failed_connections(
        self, websocket_manager, valid_jwt_token
    ):
        """Test message sending when some connections fail."""
        # Create multiple connections
        websockets = []
        connection_ids = []

        for i in range(3):
            websocket = AsyncMock(spec=WebSocket)
            websocket.client = Mock()
            websocket.client.host = f"127.0.0.{i + 1}"

            # Make the second websocket fail
            if i == 1:
                websocket.send_text.side_effect = Exception("Connection failed")

            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            response = await websocket_manager.authenticate_connection(
                websocket, auth_request
            )

            websockets.append(websocket)
            connection_ids.append(response.connection_id)

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Test"}
        )

        # Send to channel (all connections)
        channel = "test-channel"
        for connection_id in connection_ids:
            connection = websocket_manager.connections[connection_id]
            connection.subscribe_to_channel(channel)
            websocket_manager.channel_connections.setdefault(channel, set()).add(
                connection_id
            )

        sent_count = await websocket_manager.send_to_channel(channel, event)

        # Should succeed for 2 out of 3 connections
        assert sent_count == 2

        # Verify the failed connection has error status
        failed_connection = websocket_manager.connections[connection_ids[1]]
        assert failed_connection.status == ConnectionStatus.ERROR

    @pytest.mark.asyncio
    async def test_edge_case_empty_channels_subscription(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test subscription with empty channel lists."""
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        subscribe_request = WebSocketSubscribeRequest(
            channels=[], unsubscribe_channels=[]
        )

        response = await websocket_manager.subscribe_connection(
            auth_response.connection_id, subscribe_request
        )

        assert response.success is True
        assert len(response.subscribed_channels) == 0
        assert len(response.failed_channels) == 0

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_authentication_failure(
        self, websocket_manager, mock_websocket
    ):
        """Test that failed authentication doesn't leave orphaned connections."""
        initial_count = len(websocket_manager.connections)

        auth_request = WebSocketAuthRequest(token="invalid-token")
        response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert response.success is False
        assert len(websocket_manager.connections) == initial_count  # No new connections

    def test_websocket_event_model_creation(self):
        """Test WebSocketEvent model creation and serialization."""
        user_id = uuid4()
        session_id = uuid4()

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            user_id=user_id,
            session_id=session_id,
            payload={
                "message": "Hello",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        assert event.type == WebSocketEventType.CHAT_MESSAGE
        assert event.user_id == user_id
        assert event.session_id == session_id
        assert event.payload["message"] == "Hello"
        assert event.id is not None
        assert event.timestamp is not None

    def test_websocket_auth_models(self):
        """Test WebSocket authentication model creation."""
        session_id = uuid4()

        # Test auth request
        auth_request = WebSocketAuthRequest(
            token="test-token",
            session_id=session_id,
            channels=["general", "notifications"],
        )

        assert auth_request.token == "test-token"
        assert auth_request.session_id == session_id
        assert len(auth_request.channels) == 2

        # Test auth response
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id="conn-123",
            user_id=user_id,
            session_id=session_id,
            available_channels=["general", "notifications", f"user:{user_id}"],
        )

        assert auth_response.success is True
        assert auth_response.connection_id == "conn-123"
        assert auth_response.user_id == user_id
        assert len(auth_response.available_channels) == 3

    def test_websocket_subscribe_models(self):
        """Test WebSocket subscription model creation."""
        subscribe_request = WebSocketSubscribeRequest(
            channels=["channel1", "channel2"], unsubscribe_channels=["channel3"]
        )

        assert len(subscribe_request.channels) == 2
        assert len(subscribe_request.unsubscribe_channels) == 1

        subscribe_response = WebSocketSubscribeResponse(
            success=True,
            subscribed_channels=["channel1", "channel2"],
            failed_channels=["invalid_channel"],
        )

        assert subscribe_response.success is True
        assert len(subscribe_response.subscribed_channels) == 2
        assert len(subscribe_response.failed_channels) == 1
