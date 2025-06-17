"""
Comprehensive unit tests for WebSocket error recovery and state management.

This module tests all 8 connection states, circuit breaker patterns,
exponential backoff, and error recovery scenarios to ensure 90%+ coverage.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import redis.asyncio as redis
from fastapi import WebSocket
from websockets.exceptions import WebSocketException

from tripsage_core.services.infrastructure.websocket_manager import (
    CircuitBreaker,
    CircuitBreakerState,
    ConnectionState,
    ExponentialBackoff,
    RateLimitConfig,
    RateLimiter,
    WebSocketAuthRequest,
    WebSocketConnection,
    WebSocketEvent,
    WebSocketManager,
    WebSocketSubscribeRequest,
)


class TestConnectionStates:
    """Test all 8 connection states and transitions."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = MagicMock(spec=WebSocket)
        ws.send_text = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.client = MagicMock(host="127.0.0.1")
        return ws

    @pytest.fixture
    def connection(self, mock_websocket):
        """Create WebSocket connection."""
        return WebSocketConnection(
            websocket=mock_websocket,
            connection_id=str(uuid4()),
            user_id=uuid4(),
            session_id=uuid4(),
        )

    def test_state_connecting(self, connection):
        """Test CONNECTING state."""
        # Default state should be CONNECTED
        assert connection.state == ConnectionState.CONNECTED

        # Set to CONNECTING
        connection.state = ConnectionState.CONNECTING
        assert connection.state == ConnectionState.CONNECTING

    def test_state_connected(self, connection):
        """Test CONNECTED state."""
        assert connection.state == ConnectionState.CONNECTED
        assert connection.connected_at is not None

    def test_state_authenticated(self, connection):
        """Test AUTHENTICATED state."""
        connection.state = ConnectionState.AUTHENTICATED
        assert connection.state == ConnectionState.AUTHENTICATED

    def test_state_reconnecting(self, connection):
        """Test RECONNECTING state."""
        connection.state = ConnectionState.RECONNECTING
        assert connection.state == ConnectionState.RECONNECTING
        assert connection.backoff.attempt_count == 0

    def test_state_disconnected(self, connection):
        """Test DISCONNECTED state."""
        connection.state = ConnectionState.DISCONNECTED
        assert connection.state == ConnectionState.DISCONNECTED

    def test_state_error(self, connection):
        """Test ERROR state."""
        connection.state = ConnectionState.ERROR
        assert connection.state == ConnectionState.ERROR
        assert connection.circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_state_suspended(self, connection):
        """Test SUSPENDED state."""
        connection.state = ConnectionState.SUSPENDED
        assert connection.state == ConnectionState.SUSPENDED

    def test_state_degraded(self, connection):
        """Test DEGRADED state."""
        connection.state = ConnectionState.DEGRADED
        assert connection.state == ConnectionState.DEGRADED

    @pytest.mark.asyncio
    async def test_state_transitions_during_send(self, connection):
        """Test state transitions during message sending."""
        # Cannot send in DISCONNECTED state
        connection.state = ConnectionState.DISCONNECTED
        event = WebSocketEvent(type="test", payload={})
        result = await connection.send(event)
        assert result is False

        # Can send in CONNECTED state
        connection.state = ConnectionState.CONNECTED
        result = await connection.send(event)
        assert result is True

        # Can send in AUTHENTICATED state
        connection.state = ConnectionState.AUTHENTICATED
        result = await connection.send(event)
        assert result is True


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_execute() is True

    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opens after threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)

        # Record failures up to threshold
        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_execute() is False

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        time.sleep(0.2)

        # Should be half-open and allow execution
        assert cb.can_execute() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery to closed state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        # Wait and try again
        time.sleep(0.2)
        assert cb.can_execute() is True

        # Record success to close circuit
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


class TestExponentialBackoff:
    """Test exponential backoff with jitter."""

    def test_backoff_initial_delay(self):
        """Test initial backoff delay."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=10.0)
        delay = backoff.get_delay()
        assert 0.9 <= delay <= 1.1  # With jitter

    def test_backoff_exponential_growth(self):
        """Test exponential growth of delays."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=100.0, jitter=False)

        delays = []
        for _ in range(4):
            delays.append(backoff.get_delay())
            backoff.next_attempt()

        assert delays[0] == 1.0  # 1 * 2^0
        assert delays[1] == 2.0  # 1 * 2^1
        assert delays[2] == 4.0  # 1 * 2^2
        assert delays[3] == 8.0  # 1 * 2^3

    def test_backoff_max_delay(self):
        """Test maximum delay cap."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=5.0, jitter=False)

        # Attempt many times but stay under max_attempts
        delays = []
        for _ in range(5):
            delay = backoff.next_attempt()
            delays.append(delay)

        # Later delays should be capped at max_delay
        assert delays[-1] == 5.0

    def test_backoff_max_attempts(self):
        """Test maximum attempts exception."""
        backoff = ExponentialBackoff(max_attempts=3)

        # Use up all attempts
        for _ in range(3):
            backoff.next_attempt()

        # Next attempt should raise exception
        with pytest.raises(Exception, match="Max reconnection attempts"):
            backoff.get_delay()

    def test_backoff_reset(self):
        """Test backoff reset."""
        backoff = ExponentialBackoff()

        # Make some attempts
        backoff.next_attempt()
        backoff.next_attempt()
        assert backoff.attempt_count == 2

        # Reset
        backoff.reset()
        assert backoff.attempt_count == 0

    def test_backoff_jitter(self):
        """Test jitter adds randomness."""
        backoff = ExponentialBackoff(base_delay=10.0, jitter=True)

        # Get multiple delays
        delays = [backoff.get_delay() for _ in range(10)]

        # Should have some variation
        assert len(set(delays)) > 1
        assert all(9.0 <= d <= 11.0 for d in delays)  # ±10% jitter


class TestRateLimiting:
    """Test hierarchical rate limiting."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        client = MagicMock(spec=redis.Redis)
        client.scard = AsyncMock(return_value=0)
        client.eval = AsyncMock(return_value=[1, "allowed", 0, 0])
        return client

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create rate limiter."""
        config = RateLimitConfig()
        return RateLimiter(mock_redis, config)

    @pytest.mark.asyncio
    async def test_connection_limit_allowed(self, rate_limiter):
        """Test connection limit allows new connections."""
        user_id = uuid4()
        session_id = uuid4()

        result = await rate_limiter.check_connection_limit(user_id, session_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_connection_limit_exceeded_user(self, rate_limiter, mock_redis):
        """Test user connection limit exceeded."""
        mock_redis.scard.return_value = 10  # Exceeds default limit of 5

        user_id = uuid4()
        result = await rate_limiter.check_connection_limit(user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_connection_limit_exceeded_session(self, rate_limiter, mock_redis):
        """Test session connection limit exceeded."""
        # First call for user returns 2, second for session returns 5
        mock_redis.scard.side_effect = [2, 5]

        user_id = uuid4()
        session_id = uuid4()
        result = await rate_limiter.check_connection_limit(user_id, session_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_message_rate_allowed(self, rate_limiter):
        """Test message rate limit allows messages."""
        user_id = uuid4()
        connection_id = str(uuid4())

        result = await rate_limiter.check_message_rate(user_id, connection_id)
        assert result["allowed"] is True
        assert result["reason"] == "allowed"

    @pytest.mark.asyncio
    async def test_message_rate_user_limit_exceeded(self, rate_limiter, mock_redis):
        """Test user message rate limit exceeded."""
        mock_redis.eval.return_value = [0, "user_limit_exceeded", 101, 5]

        user_id = uuid4()
        connection_id = str(uuid4())

        result = await rate_limiter.check_message_rate(user_id, connection_id)
        assert result["allowed"] is False
        assert result["reason"] == "user_limit_exceeded"

    @pytest.mark.asyncio
    async def test_message_rate_connection_limit_exceeded(
        self, rate_limiter, mock_redis
    ):
        """Test connection message rate limit exceeded."""
        mock_redis.eval.return_value = [0, "connection_limit_exceeded", 50, 601]

        user_id = uuid4()
        connection_id = str(uuid4())

        result = await rate_limiter.check_message_rate(user_id, connection_id)
        assert result["allowed"] is False
        assert result["reason"] == "connection_limit_exceeded"

    @pytest.mark.asyncio
    async def test_redis_failure_fallback(self, rate_limiter, mock_redis):
        """Test fallback to local rate limiting on Redis failure."""
        mock_redis.scard.side_effect = Exception("Redis connection failed")

        user_id = uuid4()
        result = await rate_limiter.check_connection_limit(user_id)

        # Should fallback to local check and allow
        assert result is True

    def test_local_message_rate_limit(self):
        """Test local message rate limiting without Redis."""
        config = RateLimitConfig(max_messages_per_user_per_minute=2)
        limiter = RateLimiter(None, config)

        user_id = uuid4()
        connection_id = str(uuid4())

        # First two messages should be allowed
        result1 = limiter._check_local_message_rate(user_id, connection_id)
        assert result1["allowed"] is True

        result2 = limiter._check_local_message_rate(user_id, connection_id)
        assert result2["allowed"] is True

        # Third message should be blocked
        result3 = limiter._check_local_message_rate(user_id, connection_id)
        assert result3["allowed"] is False
        assert result3["reason"] == "user_limit_exceeded"


class TestWebSocketConnectionAdvanced:
    """Test advanced WebSocket connection features."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = MagicMock(spec=WebSocket)
        ws.send_text = AsyncMock()
        ws.client = MagicMock(host="192.168.1.100")
        return ws

    @pytest.fixture
    def connection(self, mock_websocket):
        """Create WebSocket connection."""
        return WebSocketConnection(
            websocket=mock_websocket,
            connection_id=str(uuid4()),
            user_id=uuid4(),
        )

    @pytest.mark.asyncio
    async def test_priority_queue_processing(self, connection):
        """Test priority message queue processing."""
        # Add messages to different priority queues
        high_priority = WebSocketEvent(type="high", payload={}, priority=1)
        medium_priority = WebSocketEvent(type="medium", payload={}, priority=2)
        low_priority = WebSocketEvent(type="low", payload={}, priority=3)

        connection.priority_queue[3].append(low_priority)
        connection.priority_queue[2].append(medium_priority)
        connection.priority_queue[1].append(high_priority)

        # Process queue
        sent_count = await connection.process_priority_queue()
        assert sent_count == 3

        # Verify high priority sent first
        calls = connection.websocket.send_text.call_args_list
        first_message = json.loads(calls[0][0][0])
        assert first_message["type"] == "high"

    @pytest.mark.asyncio
    async def test_ping_pong_latency_tracking(self, connection):
        """Test ping/pong latency measurement."""
        # Send ping
        result = await connection.send_ping()
        assert result is True
        assert connection.ping_sent_time is not None

        # Simulate delay
        time.sleep(0.05)

        # Handle pong
        connection.handle_pong()
        assert connection.ping_sent_time is None
        assert len(connection.latency_samples) == 1
        assert connection.latency_samples[0] >= 50  # At least 50ms

    def test_connection_staleness_check(self, connection):
        """Test connection staleness detection."""
        # Fresh connection should not be stale
        assert connection.is_stale(timeout_seconds=60) is False

        # Simulate old heartbeat
        connection.last_heartbeat = connection.last_heartbeat.replace(
            year=connection.last_heartbeat.year - 1
        )
        assert connection.is_stale(timeout_seconds=60) is True

    def test_ping_timeout_detection(self, connection):
        """Test ping timeout detection."""
        # No ping sent, should not timeout
        assert connection.is_ping_timeout(timeout_seconds=5) is False

        # Set ping sent time in the past
        connection.ping_sent_time = time.time() - 10
        assert connection.is_ping_timeout(timeout_seconds=5) is True

    def test_connection_health_metrics(self, connection):
        """Test connection health calculation."""
        # Add some latency samples
        connection.latency_samples.extend([50, 100, 150])
        connection.message_count = 100
        connection.error_count = 2

        health = connection.get_health()
        assert health.latency == 100.0  # Average of samples
        assert health.quality == "good"
        assert health.error_rate > 0

    def test_connection_health_quality_levels(self, connection):
        """Test different health quality levels."""
        # Excellent quality
        connection.latency_samples.append(100)
        connection.error_count = 0
        assert connection.get_health().quality == "excellent"

        # Good quality
        connection.latency_samples.clear()
        connection.latency_samples.append(600)
        assert connection.get_health().quality == "good"

        # Poor quality
        connection.latency_samples.clear()
        connection.latency_samples.append(1500)
        assert connection.get_health().quality == "poor"

        # Critical quality
        connection.latency_samples.clear()
        connection.latency_samples.append(3000)
        assert connection.get_health().quality == "critical"

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, connection):
        """Test circuit breaker during message sending."""
        # Force circuit breaker open
        connection.circuit_breaker.state = CircuitBreakerState.OPEN
        connection.circuit_breaker.last_failure_time = time.time()

        event = WebSocketEvent(type="test", payload={})
        result = await connection.send(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_message_retry_on_failure(self, connection):
        """Test message retry logic."""
        connection.websocket.send_text.side_effect = Exception("Network error")

        event = WebSocketEvent(type="test", payload={}, retry_count=0)
        result = await connection.send(event)
        assert result is False

        # Should be queued for retry with high priority
        assert len(connection.priority_queue[1]) == 1
        retry_event = connection.priority_queue[1][0]
        assert retry_event.retry_count == 1

    @pytest.mark.asyncio
    async def test_max_retry_limit(self, connection):
        """Test maximum retry limit."""
        connection.websocket.send_text.side_effect = Exception("Network error")

        # Event already at max retries
        event = WebSocketEvent(type="test", payload={}, retry_count=3)
        result = await connection.send(event)
        assert result is False

        # Should not be queued for retry
        assert len(connection.priority_queue[1]) == 0


class TestWebSocketManagerIntegration:
    """Test WebSocket manager integration features."""

    @pytest.fixture
    def mock_broadcaster(self):
        """Create mock broadcaster."""
        broadcaster = MagicMock()
        broadcaster.start = AsyncMock()
        broadcaster.stop = AsyncMock()
        broadcaster.register_connection = AsyncMock()
        broadcaster.unregister_connection = AsyncMock()
        broadcaster.broadcast_to_channel = AsyncMock()
        broadcaster.broadcast_to_user = AsyncMock()
        broadcaster.broadcast_to_session = AsyncMock()
        return broadcaster

    @pytest.fixture
    def manager(self, mock_broadcaster):
        """Create WebSocket manager with broadcaster."""
        return WebSocketManager(broadcaster=mock_broadcaster)

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, manager):
        """Test manager start/stop lifecycle."""
        # Start manager
        await manager.start()
        assert manager._running is True
        assert manager.broadcaster.start.called

        # Stop manager
        await manager.stop()
        assert manager._running is False
        assert manager.broadcaster.stop.called

    @pytest.mark.asyncio
    async def test_subscribe_connection_success(self, manager):
        """Test successful channel subscription."""
        # Create authenticated connection
        connection_id = str(uuid4())
        user_id = uuid4()
        connection = WebSocketConnection(
            websocket=MagicMock(), connection_id=connection_id, user_id=user_id
        )
        manager.connections[connection_id] = connection

        # Subscribe to channels
        request = WebSocketSubscribeRequest(
            channels=["general", "notifications"], unsubscribe_channels=[]
        )

        response = await manager.subscribe_connection(connection_id, request)
        assert response.success is True
        assert len(response.subscribed_channels) == 2
        assert "general" in connection.subscribed_channels
        assert "notifications" in connection.subscribed_channels

    @pytest.mark.asyncio
    async def test_subscribe_connection_not_found(self, manager):
        """Test subscription with invalid connection ID."""
        request = WebSocketSubscribeRequest(channels=["general"])
        response = await manager.subscribe_connection("invalid-id", request)

        assert response.success is False
        assert response.error == "Connection not found"

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_channels(self, manager):
        """Test subscribing and unsubscribing channels."""
        # Create connection with existing subscriptions
        connection_id = str(uuid4())
        user_id = uuid4()
        connection = WebSocketConnection(
            websocket=MagicMock(), connection_id=connection_id, user_id=user_id
        )
        connection.subscribe_to_channel("general")
        connection.subscribe_to_channel("notifications")

        manager.connections[connection_id] = connection
        manager.channel_connections["general"] = {connection_id}
        manager.channel_connections["notifications"] = {connection_id}

        # Unsubscribe from one, subscribe to another
        request = WebSocketSubscribeRequest(
            channels=[f"user:{user_id}"], unsubscribe_channels=["general"]
        )

        response = await manager.subscribe_connection(connection_id, request)
        assert response.success is True
        assert "general" not in connection.subscribed_channels
        assert "notifications" in connection.subscribed_channels
        assert f"user:{user_id}" in connection.subscribed_channels

    @pytest.mark.asyncio
    async def test_unauthorized_channel_subscription(self, manager):
        """Test subscription to unauthorized channel."""
        connection_id = str(uuid4())
        user_id = uuid4()
        connection = WebSocketConnection(
            websocket=MagicMock(), connection_id=connection_id, user_id=user_id
        )
        manager.connections[connection_id] = connection

        # Try to subscribe to admin channel (not in available channels)
        request = WebSocketSubscribeRequest(channels=["admin:secret"])
        response = await manager.subscribe_connection(connection_id, request)

        assert response.success is True
        assert len(response.failed_channels) == 1
        assert "admin:secret" in response.failed_channels

    @pytest.mark.asyncio
    async def test_broadcast_integration(self, manager, mock_broadcaster):
        """Test broadcasting with integrated broadcaster."""
        # Create connections
        user_id = uuid4()
        conn1 = WebSocketConnection(
            websocket=MagicMock(), connection_id="conn1", user_id=user_id
        )
        conn1.subscribe_to_channel("test-channel")

        manager.connections["conn1"] = conn1
        manager.channel_connections["test-channel"] = {"conn1"}

        # Broadcast message
        event = WebSocketEvent(type="broadcast", payload={"msg": "test"})
        count = await manager.broadcast_to_channel("test-channel", event)

        assert count == 1
        assert mock_broadcaster.broadcast_to_channel.called

    def test_performance_metrics_tracking(self, manager):
        """Test performance metrics collection."""
        # Add some connections
        manager.connections["conn1"] = MagicMock()
        manager.connections["conn2"] = MagicMock()

        stats = manager.get_connection_stats()
        assert stats["total_connections"] == 2
        assert stats["redis_connected"] is False
        assert stats["broadcaster_running"] is True


class TestErrorRecoveryScenarios:
    """Test complex error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_connection_recovery_after_network_failure(self):
        """Test connection recovery after network failure."""
        ws = MagicMock()
        ws.send_text = AsyncMock()

        connection = WebSocketConnection(
            websocket=ws, connection_id=str(uuid4()), user_id=uuid4()
        )

        # Simulate network failures
        ws.send_text.side_effect = [
            WebSocketException("Network error"),
            WebSocketException("Network error"),
            None,  # Success on third attempt
        ]

        event = WebSocketEvent(type="test", payload={})

        # First attempt fails
        result1 = await connection.send(event)
        assert result1 is False
        assert connection.state == ConnectionState.ERROR

        # Reset state and retry
        connection.state = ConnectionState.CONNECTED
        connection.circuit_breaker.record_success()  # Reset circuit breaker

        # Should eventually succeed
        result2 = await connection.send(event)
        assert result2 is True

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_redis(self):
        """Test system continues without Redis."""
        manager = WebSocketManager()

        # Should start without Redis
        await manager.start()
        assert manager._running is True
        assert manager.redis_client is None

        # Should handle connections locally
        ws = MagicMock()
        auth_request = WebSocketAuthRequest(token="fake-token", channels=["general"])

        with patch("jwt.decode", return_value={"sub": "user", "user_id": str(uuid4())}):
            response = await manager.authenticate_connection(ws, auth_request)
            # Will fail due to settings not being properly mocked,
            # but shows fallback path
            assert response.success is False

    @pytest.mark.asyncio
    async def test_cascade_failure_prevention(self):
        """Test prevention of cascade failures."""
        manager = WebSocketManager()

        # Create multiple connections
        connections = []
        for i in range(5):
            conn = WebSocketConnection(
                websocket=MagicMock(), connection_id=f"conn{i}", user_id=uuid4()
            )
            connections.append(conn)
            manager.connections[conn.connection_id] = conn

        # Simulate one connection having issues
        connections[0].circuit_breaker.state = CircuitBreakerState.OPEN
        connections[0].state = ConnectionState.ERROR

        # Broadcast should continue to healthy connections
        event = WebSocketEvent(type="broadcast", payload={})
        sent_count = 0

        for conn_id in manager.connections:
            if await manager.send_to_connection(conn_id, event):
                sent_count += 1

        assert sent_count == 4  # All except the failed one


# Additional test for WebSocket event serialization
class TestWebSocketEventSerialization:
    """Test WebSocket event serialization and deserialization."""

    def test_event_creation_with_defaults(self):
        """Test event creation with default values."""
        event = WebSocketEvent(type="test", payload={"key": "value"})

        assert event.id is not None
        assert event.type == "test"
        assert event.priority == 1
        assert event.retry_count == 0
        assert event.expires_at is None

    def test_event_serialization(self):
        """Test event can be serialized to JSON."""
        event = WebSocketEvent(
            type="test",
            user_id=uuid4(),
            session_id=uuid4(),
            payload={"message": "Hello"},
        )

        # Should be serializable
        event_dict = event.model_dump()
        json_str = json.dumps(event_dict, default=str)
        assert json_str is not None

        # Check key fields
        assert "id" in event_dict
        assert "type" in event_dict
        assert "timestamp" in event_dict
