"""Comprehensive tests for TripSage Core WebSocket Connection Service.

This module provides comprehensive test coverage for WebSocket connection functionality
including connection lifecycle management, health monitoring, state transitions,
circuit breaker patterns, backpressure handling, rate limiting, and error recovery.
"""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import WebSocket
from pydantic import ValidationError

from tripsage_core.services.infrastructure.websocket_connection_service import (
    ConnectionHealth,
    ConnectionState,
    WebSocketConnection,
    WebSocketConnectionService,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


class TestConnectionHealth:
    """Test suite for ConnectionHealth model."""

    def test_connection_health_creation(self):
        """Test ConnectionHealth model creation."""
        health = ConnectionHealth(
            latency=50.0,
            message_rate=10.5,
            error_rate=0.02,
            reconnect_count=1,
            last_activity=datetime.now(UTC),
            quality="good",
            queue_size=25,
            backpressure_active=False,
            dropped_messages=0,
        )

        assert health.latency == 50.0
        assert health.message_rate == 10.5
        assert health.error_rate == 0.02
        assert health.reconnect_count == 1
        assert health.quality == "good"
        assert health.queue_size == 25
        assert health.backpressure_active is False
        assert health.dropped_messages == 0

    def test_connection_health_validation(self):
        """Test ConnectionHealth model validation."""
        # Test invalid latency
        with pytest.raises(ValidationError):
            ConnectionHealth(
                latency=-10.0,  # Negative latency should be invalid
                message_rate=5.0,
                error_rate=0.01,
                reconnect_count=0,
                last_activity=datetime.now(UTC),
                quality="good",
                queue_size=10,
                backpressure_active=False,
                dropped_messages=0,
            )

        # Test invalid error rate
        with pytest.raises(ValidationError):
            ConnectionHealth(
                latency=30.0,
                message_rate=5.0,
                error_rate=1.5,  # Error rate > 1.0 should be invalid
                reconnect_count=0,
                last_activity=datetime.now(UTC),
                quality="good",
                queue_size=10,
                backpressure_active=False,
                dropped_messages=0,
            )


class TestWebSocketConnection:
    """Test suite for WebSocketConnection."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.send_bytes = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 12345
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
        assert websocket_connection.state == ConnectionState.CONNECTED
        assert len(websocket_connection.subscribed_channels) == 0
        assert websocket_connection.message_count == 0
        assert websocket_connection.error_count == 0
        assert websocket_connection.bytes_sent == 0
        assert websocket_connection.bytes_received == 0
        assert len(websocket_connection.outbound_queue) == 0

    def test_connection_state_enum(self):
        """Test ConnectionState enum values."""
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.DISCONNECTING.value == "disconnecting"
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.ERROR.value == "error"

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
        assert websocket_connection.error_count == 1
        assert websocket_connection.state == ConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_send_with_queue_full(self, websocket_connection):
        """Test sending when outbound queue is full."""
        # Fill up the queue
        for i in range(websocket_connection.max_queue_size + 1):
            websocket_connection.outbound_queue.append(f"message_{i}")

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Overflow message"},
        )

        result = await websocket_connection.send(event)
        assert result is False
        # Should increment dropped message count
        assert websocket_connection.get_health().dropped_messages > 0

    @pytest.mark.asyncio
    async def test_send_with_backpressure(self, websocket_connection, mock_websocket):
        """Test sending with backpressure detection."""
        # Simulate slow WebSocket
        mock_websocket.send_text = AsyncMock(side_effect=lambda x: asyncio.sleep(0.1))

        # Fill queue to trigger backpressure
        for i in range(websocket_connection.backpressure_threshold + 1):
            websocket_connection.outbound_queue.append(f"message_{i}")

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Backpressure test"},
        )

        await websocket_connection.send(event)
        health = websocket_connection.get_health()

        assert health.backpressure_active is True
        assert health.queue_size > websocket_connection.backpressure_threshold

    @pytest.mark.asyncio
    async def test_receive_message_success(self, websocket_connection, mock_websocket):
        """Test successful message receiving."""
        mock_websocket.receive_text.return_value = '{"type": "ping", "payload": {}}'

        message = await websocket_connection.receive()

        assert message is not None
        assert message["type"] == "ping"
        assert websocket_connection.bytes_received > 0

    @pytest.mark.asyncio
    async def test_receive_message_failure(self, websocket_connection, mock_websocket):
        """Test message receiving failure."""
        mock_websocket.receive_text.side_effect = Exception("Receive error")

        message = await websocket_connection.receive()

        assert message is None
        assert websocket_connection.error_count == 1

    @pytest.mark.asyncio
    async def test_receive_invalid_json(self, websocket_connection, mock_websocket):
        """Test receiving invalid JSON."""
        mock_websocket.receive_text.return_value = "invalid json{"

        message = await websocket_connection.receive()

        assert message is None
        assert websocket_connection.error_count == 1

    def test_subscribe_to_channel(self, websocket_connection):
        """Test subscribing to channels."""
        websocket_connection.subscribe_to_channel("general")
        websocket_connection.subscribe_to_channel("notifications")

        assert "general" in websocket_connection.subscribed_channels
        assert "notifications" in websocket_connection.subscribed_channels
        assert len(websocket_connection.subscribed_channels) == 2

    def test_unsubscribe_from_channel(self, websocket_connection):
        """Test unsubscribing from channels."""
        websocket_connection.subscribe_to_channel("general")
        websocket_connection.subscribe_to_channel("notifications")

        websocket_connection.unsubscribe_from_channel("general")

        assert "general" not in websocket_connection.subscribed_channels
        assert "notifications" in websocket_connection.subscribed_channels
        assert len(websocket_connection.subscribed_channels) == 1

    def test_unsubscribe_from_nonexistent_channel(self, websocket_connection):
        """Test unsubscribing from non-existent channel."""
        # Should not raise exception
        websocket_connection.unsubscribe_from_channel("nonexistent")
        assert len(websocket_connection.subscribed_channels) == 0

    @pytest.mark.asyncio
    async def test_close_connection(self, websocket_connection, mock_websocket):
        """Test closing connection."""
        await websocket_connection.close(code=1000, reason="Normal closure")

        mock_websocket.close.assert_called_once_with(code=1000, reason="Normal closure")
        assert websocket_connection.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_close_connection_error(self, websocket_connection, mock_websocket):
        """Test closing connection with error."""
        mock_websocket.close.side_effect = Exception("Close error")

        await websocket_connection.close()

        # Should handle error gracefully
        assert websocket_connection.state == ConnectionState.DISCONNECTED

    def test_get_health_metrics(self, websocket_connection):
        """Test health metrics calculation."""
        # Simulate some activity
        websocket_connection.message_count = 100
        websocket_connection.error_count = 2
        websocket_connection.bytes_sent = 5000
        websocket_connection.last_activity = time.time()

        health = websocket_connection.get_health()

        assert isinstance(health, ConnectionHealth)
        assert health.error_rate == 0.02  # 2/100
        assert health.queue_size == len(websocket_connection.outbound_queue)
        assert health.quality in ["excellent", "good", "fair", "poor", "critical"]

    def test_health_quality_calculation(self, websocket_connection):
        """Test health quality calculation with different metrics."""
        # Test excellent quality
        websocket_connection.message_count = 100
        websocket_connection.error_count = 0
        websocket_connection._latency_samples = [10.0, 15.0, 12.0]
        health = websocket_connection.get_health()
        assert health.quality == "excellent"

        # Test poor quality with high error rate
        websocket_connection.error_count = 20  # 20% error rate
        health = websocket_connection.get_health()
        assert health.quality in ["poor", "critical"]

    def test_latency_tracking(self, websocket_connection):
        """Test latency tracking functionality."""
        # Add some latency samples
        websocket_connection._add_latency_sample(25.0)
        websocket_connection._add_latency_sample(30.0)
        websocket_connection._add_latency_sample(20.0)

        health = websocket_connection.get_health()
        assert health.latency == 25.0  # Average of samples

    def test_latency_sample_limit(self, websocket_connection):
        """Test latency sample collection limit."""
        # Add more samples than the limit
        for i in range(websocket_connection.max_latency_samples + 10):
            websocket_connection._add_latency_sample(float(i))

        assert (
            len(websocket_connection._latency_samples)
            <= websocket_connection.max_latency_samples
        )

    def test_rate_limiting_check(self, websocket_connection):
        """Test rate limiting functionality."""
        # Simulate rapid message sending
        current_time = time.time()
        websocket_connection.rate_limit_requests = 5
        websocket_connection.rate_limit_window = 1.0

        # Add requests within window
        for _i in range(3):
            websocket_connection._add_rate_limit_request(current_time)

        # Should be within limit
        assert websocket_connection._check_rate_limit() is True

        # Add more requests to exceed limit
        for _i in range(3):
            websocket_connection._add_rate_limit_request(current_time)

        # Should exceed limit
        assert websocket_connection._check_rate_limit() is False

    def test_rate_limiting_window_reset(self, websocket_connection):
        """Test rate limiting window reset."""
        old_time = time.time() - 2.0  # 2 seconds ago
        time.time()

        websocket_connection.rate_limit_window = 1.0

        # Add old requests
        for _i in range(10):
            websocket_connection._add_rate_limit_request(old_time)

        # Should be reset due to time window
        assert websocket_connection._check_rate_limit() is True

    @pytest.mark.asyncio
    async def test_heartbeat_functionality(self, websocket_connection, mock_websocket):
        """Test heartbeat/ping functionality."""
        result = await websocket_connection.ping()

        assert result is True
        mock_websocket.send_text.assert_called_once()
        # Check that a ping event was sent
        call_args = mock_websocket.send_text.call_args[0][0]
        assert "ping" in call_args.lower()

    @pytest.mark.asyncio
    async def test_heartbeat_failure(self, websocket_connection, mock_websocket):
        """Test heartbeat failure."""
        mock_websocket.send_text.side_effect = Exception("Ping failed")

        result = await websocket_connection.ping()

        assert result is False
        assert websocket_connection.error_count == 1

    def test_circuit_breaker_initialization(self, websocket_connection):
        """Test circuit breaker initialization."""
        assert websocket_connection.circuit_breaker is not None
        assert websocket_connection.circuit_breaker.state.name == "CLOSED"

    @pytest.mark.asyncio
    async def test_circuit_breaker_trip(self, websocket_connection, mock_websocket):
        """Test circuit breaker tripping on errors."""
        # Simulate multiple failures to trip circuit breaker
        mock_websocket.send_text.side_effect = Exception("Repeated failure")

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Test"},
        )

        # Send multiple messages to trigger circuit breaker
        for _ in range(10):  # Should exceed circuit breaker threshold
            await websocket_connection.send(event)

        # Circuit breaker should trip
        assert websocket_connection.circuit_breaker.state.name in ["OPEN", "HALF_OPEN"]

    def test_message_queue_management(self, websocket_connection):
        """Test message queue management."""
        # Test queue operations
        initial_size = len(websocket_connection.outbound_queue)

        # Add message to queue
        websocket_connection._queue_message("test message")
        assert len(websocket_connection.outbound_queue) == initial_size + 1

        # Dequeue message
        message = websocket_connection._dequeue_message()
        assert message == "test message"
        assert len(websocket_connection.outbound_queue) == initial_size

    def test_connection_info_dict(self, websocket_connection):
        """Test connection info dictionary generation."""
        info = websocket_connection.to_dict()

        assert info["connection_id"] == websocket_connection.connection_id
        assert info["user_id"] == str(websocket_connection.user_id)
        assert info["session_id"] == str(websocket_connection.session_id)
        assert info["state"] == websocket_connection.state.value
        assert "connected_at" in info
        assert "message_count" in info
        assert "error_count" in info


class TestWebSocketConnectionService:
    """Test suite for WebSocketConnectionService."""

    @pytest.fixture
    def connection_service(self):
        """Create WebSocketConnectionService instance."""
        return WebSocketConnectionService()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        return websocket

    @pytest.mark.asyncio
    async def test_create_connection(self, connection_service, mock_websocket):
        """Test creating a new connection."""
        user_id = uuid4()
        session_id = uuid4()

        connection = await connection_service.create_connection(
            websocket=mock_websocket, user_id=user_id, session_id=session_id
        )

        assert connection is not None
        assert connection.user_id == user_id
        assert connection.session_id == session_id
        assert connection.state == ConnectionState.CONNECTED
        assert connection.connection_id in connection_service.connections

    @pytest.mark.asyncio
    async def test_get_connection_by_id(self, connection_service, mock_websocket):
        """Test retrieving connection by ID."""
        user_id = uuid4()

        connection = await connection_service.create_connection(
            websocket=mock_websocket, user_id=user_id
        )

        retrieved = connection_service.get_connection(connection.connection_id)
        assert retrieved == connection

    def test_get_nonexistent_connection(self, connection_service):
        """Test retrieving non-existent connection."""
        result = connection_service.get_connection("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_connection(self, connection_service, mock_websocket):
        """Test removing connection."""
        user_id = uuid4()

        connection = await connection_service.create_connection(
            websocket=mock_websocket, user_id=user_id
        )

        connection_id = connection.connection_id
        removed = await connection_service.remove_connection(connection_id)

        assert removed == connection
        assert connection_id not in connection_service.connections

    @pytest.mark.asyncio
    async def test_remove_nonexistent_connection(self, connection_service):
        """Test removing non-existent connection."""
        result = await connection_service.remove_connection("nonexistent-id")
        assert result is None

    def test_get_connections_by_user(self, connection_service):
        """Test retrieving connections by user ID."""
        user_id = uuid4()

        # Create mock connections for user
        conn1 = Mock()
        conn1.user_id = user_id
        conn1.connection_id = "conn1"

        conn2 = Mock()
        conn2.user_id = user_id
        conn2.connection_id = "conn2"

        conn3 = Mock()
        conn3.user_id = uuid4()  # Different user
        conn3.connection_id = "conn3"

        connection_service.connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }

        user_connections = connection_service.get_connections_by_user(user_id)
        assert len(user_connections) == 2
        assert conn1 in user_connections
        assert conn2 in user_connections
        assert conn3 not in user_connections

    def test_get_connections_by_session(self, connection_service):
        """Test retrieving connections by session ID."""
        session_id = uuid4()

        # Create mock connections for session
        conn1 = Mock()
        conn1.session_id = session_id
        conn1.connection_id = "conn1"

        conn2 = Mock()
        conn2.session_id = uuid4()  # Different session
        conn2.connection_id = "conn2"

        connection_service.connections = {"conn1": conn1, "conn2": conn2}

        session_connections = connection_service.get_connections_by_session(session_id)
        assert len(session_connections) == 1
        assert conn1 in session_connections

    def test_get_connections_by_channel(self, connection_service):
        """Test retrieving connections by channel."""
        channel = "general"

        # Create mock connections
        conn1 = Mock()
        conn1.subscribed_channels = {"general", "notifications"}
        conn1.connection_id = "conn1"

        conn2 = Mock()
        conn2.subscribed_channels = {"private"}
        conn2.connection_id = "conn2"

        conn3 = Mock()
        conn3.subscribed_channels = {"general"}
        conn3.connection_id = "conn3"

        connection_service.connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }

        channel_connections = connection_service.get_connections_by_channel(channel)
        assert len(channel_connections) == 2
        assert conn1 in channel_connections
        assert conn3 in channel_connections
        assert conn2 not in channel_connections

    def test_get_all_connections(self, connection_service):
        """Test retrieving all connections."""
        # Add mock connections
        conn1 = Mock()
        conn2 = Mock()

        connection_service.connections = {"conn1": conn1, "conn2": conn2}

        all_connections = connection_service.get_all_connections()
        assert len(all_connections) == 2
        assert conn1 in all_connections
        assert conn2 in all_connections

    def test_get_connection_count(self, connection_service):
        """Test getting total connection count."""
        connection_service.connections = {
            "conn1": Mock(),
            "conn2": Mock(),
            "conn3": Mock(),
        }

        count = connection_service.get_connection_count()
        assert count == 3

    def test_get_user_connection_count(self, connection_service):
        """Test getting connection count for specific user."""
        user_id = uuid4()

        conn1 = Mock()
        conn1.user_id = user_id

        conn2 = Mock()
        conn2.user_id = user_id

        conn3 = Mock()
        conn3.user_id = uuid4()  # Different user

        connection_service.connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }

        count = connection_service.get_user_connection_count(user_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, connection_service):
        """Test broadcasting to all connections."""
        # Create mock connections
        conn1 = AsyncMock()
        conn2 = AsyncMock()

        connection_service.connections = {"conn1": conn1, "conn2": conn2}

        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_ANNOUNCEMENT,
            payload={"message": "System maintenance"},
        )

        results = await connection_service.broadcast_to_all(event)

        assert len(results) == 2
        conn1.send.assert_called_once_with(event)
        conn2.send.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, connection_service):
        """Test broadcasting to channel subscribers."""
        channel = "general"

        # Create mock connections
        conn1 = AsyncMock()
        conn1.subscribed_channels = {"general", "notifications"}

        conn2 = AsyncMock()
        conn2.subscribed_channels = {"private"}

        conn3 = AsyncMock()
        conn3.subscribed_channels = {"general"}

        connection_service.connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }

        event = WebSocketEvent(
            type=WebSocketEventType.CHANNEL_MESSAGE,
            payload={"message": "Channel announcement"},
        )

        results = await connection_service.broadcast_to_channel(channel, event)

        assert len(results) == 2
        conn1.send.assert_called_once_with(event)
        conn3.send.assert_called_once_with(event)
        conn2.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_dead_connections(self, connection_service):
        """Test cleanup of dead connections."""
        # Create mock connections with different states
        conn1 = Mock()
        conn1.state = ConnectionState.CONNECTED
        conn1.connection_id = "conn1"

        conn2 = Mock()
        conn2.state = ConnectionState.DISCONNECTED
        conn2.connection_id = "conn2"

        conn3 = Mock()
        conn3.state = ConnectionState.ERROR
        conn3.connection_id = "conn3"

        connection_service.connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }

        cleaned_count = await connection_service.cleanup_dead_connections()

        assert cleaned_count == 2  # conn2 and conn3 should be removed
        assert "conn1" in connection_service.connections
        assert "conn2" not in connection_service.connections
        assert "conn3" not in connection_service.connections

    def test_get_connection_stats(self, connection_service):
        """Test getting connection statistics."""
        # Create mock connections with different states
        conn1 = Mock()
        conn1.state = ConnectionState.CONNECTED
        conn1.message_count = 100
        conn1.error_count = 1

        conn2 = Mock()
        conn2.state = ConnectionState.CONNECTED
        conn2.message_count = 200
        conn2.error_count = 5

        conn3 = Mock()
        conn3.state = ConnectionState.DISCONNECTED
        conn3.message_count = 50
        conn3.error_count = 10

        connection_service.connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }

        stats = connection_service.get_connection_stats()

        assert stats["total_connections"] == 3
        assert stats["connected"] == 2
        assert stats["disconnected"] == 1
        assert stats["total_messages"] == 350
        assert stats["total_errors"] == 16

    @pytest.mark.asyncio
    async def test_health_check_all_connections(self, connection_service):
        """Test health check for all connections."""
        # Create mock connections
        conn1 = Mock()
        conn1.connection_id = "conn1"
        conn1.get_health.return_value = Mock(quality="good")

        conn2 = Mock()
        conn2.connection_id = "conn2"
        conn2.get_health.return_value = Mock(quality="poor")

        connection_service.connections = {"conn1": conn1, "conn2": conn2}

        health_report = await connection_service.health_check_all()

        assert len(health_report) == 2
        assert "conn1" in health_report
        assert "conn2" in health_report
        assert health_report["conn1"]["quality"] == "good"
        assert health_report["conn2"]["quality"] == "poor"

    @pytest.mark.asyncio
    async def test_ping_all_connections(self, connection_service):
        """Test pinging all connections."""
        # Create mock connections
        conn1 = AsyncMock()
        conn1.connection_id = "conn1"
        conn1.ping.return_value = True

        conn2 = AsyncMock()
        conn2.connection_id = "conn2"
        conn2.ping.return_value = False

        connection_service.connections = {"conn1": conn1, "conn2": conn2}

        ping_results = await connection_service.ping_all()

        assert len(ping_results) == 2
        assert ping_results["conn1"] is True
        assert ping_results["conn2"] is False


@pytest.mark.integration
class TestWebSocketConnectionIntegration:
    """Integration tests for WebSocket connection functionality."""

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self):
        """Test complete connection lifecycle."""
        # This would require actual WebSocket connection
        # Implementation depends on test environment setup

    @pytest.mark.asyncio
    async def test_concurrent_connection_handling(self):
        """Test handling multiple concurrent connections."""
        # Test concurrent connection creation, messaging, and cleanup

    @pytest.mark.asyncio
    async def test_connection_performance_under_load(self):
        """Test connection performance under high load."""
        # Performance testing for connection management
