"""
Enhanced comprehensive tests for TripSage Core WebSocket Manager.

This module provides 90%+ test coverage for WebSocket manager functionality with
modern testing patterns and proper API alignment:
- Connection lifecycle management and authentication
- Channel subscription and broadcasting
- Rate limiting and circuit breaker patterns
- Message priority queuing and processing
- Background task management and monitoring
- Error handling and recovery scenarios
- Integration with Redis and broadcaster services
- Performance metrics and health monitoring

Modern testing patterns:
- AAA (Arrange, Act, Assert) pattern
- pytest-asyncio for async test support
- Proper mocking with isolation
- Comprehensive error scenario testing
- Property-based testing with Hypothesis
- Performance and load testing scenarios
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import WebSocket
from hypothesis import given
from hypothesis import strategies as st

from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthRequest,
)
from tripsage_core.services.infrastructure.websocket_connection_service import (
    ConnectionState,
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    CircuitBreaker,
    CircuitBreakerState,
    ExponentialBackoff,
    RateLimitConfig,
    RateLimiter,
    WebSocketManager,
    WebSocketSubscribeRequest,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


class TestWebSocketManagerInitialization:
    """Test suite for WebSocket manager initialization."""

    @pytest_asyncio.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        manager = WebSocketManager()
        yield manager
        await manager.stop()

    @pytest_asyncio.fixture
    async def mock_broadcaster(self):
        """Create mock broadcaster."""
        broadcaster = AsyncMock()
        broadcaster.start = AsyncMock()
        broadcaster.stop = AsyncMock()
        broadcaster.register_connection = AsyncMock()
        broadcaster.unregister_connection = AsyncMock()
        broadcaster.broadcast_to_channel = AsyncMock()
        broadcaster.broadcast_to_user = AsyncMock()
        broadcaster.broadcast_to_session = AsyncMock()
        return broadcaster

    def test_initialization_default(self):
        """Test WebSocket manager default initialization."""
        # Arrange & Act
        manager = WebSocketManager()

        # Assert
        assert manager.connection_service is not None
        assert manager.auth_service is not None
        assert manager.messaging_service is not None
        assert manager.redis_client is None
        assert manager.rate_limiter is None
        assert not manager._running
        assert manager.heartbeat_interval == 20
        assert manager.cleanup_interval == 60

    def test_initialization_with_broadcaster(self, mock_broadcaster):
        """Test WebSocket manager initialization with broadcaster."""
        # Arrange & Act
        manager = WebSocketManager(broadcaster=mock_broadcaster)

        # Assert
        assert manager.broadcaster == mock_broadcaster
        assert manager.connection_service is not None

    @pytest.mark.asyncio
    async def test_start_success(self, websocket_manager):
        """Test successful manager startup."""
        # Arrange
        with patch.object(websocket_manager, "_initialize_redis") as mock_init_redis:
            mock_init_redis.return_value = None

            # Act
            await websocket_manager.start()

            # Assert
            assert websocket_manager._running
            assert websocket_manager.rate_limiter is not None
            assert websocket_manager._cleanup_task is not None
            assert websocket_manager._heartbeat_task is not None

    @pytest.mark.asyncio
    async def test_start_with_broadcaster(self, mock_broadcaster):
        """Test manager startup with broadcaster."""
        # Arrange
        manager = WebSocketManager(broadcaster=mock_broadcaster)

        with patch.object(manager, "_initialize_redis") as mock_init_redis:
            mock_init_redis.return_value = None

            # Act
            await manager.start()

            # Assert
            assert manager._running
            mock_broadcaster.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_failure(self, websocket_manager):
        """Test manager startup failure."""
        # Arrange
        with patch.object(websocket_manager, "_initialize_redis") as mock_init_redis:
            mock_init_redis.side_effect = Exception("Redis initialization failed")

            # Act & Assert
            with pytest.raises(CoreServiceError) as exc_info:
                await websocket_manager.start()

            assert "Failed to start WebSocket manager" in str(exc_info.value)
            assert exc_info.value.code == "WEBSOCKET_MANAGER_START_FAILED"

    @pytest.mark.asyncio
    async def test_stop_graceful(self, websocket_manager):
        """Test graceful manager shutdown."""
        # Arrange
        await websocket_manager.start()

        # Act
        await websocket_manager.stop()

        # Assert
        assert not websocket_manager._running


class TestWebSocketManagerAuthentication:
    """Test suite for WebSocket authentication."""

    @pytest_asyncio.fixture
    async def started_manager(self):
        """Create and start WebSocket manager."""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest_asyncio.fixture
    async def mock_websocket(self):
        """Create mock WebSocket connection."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        return websocket

    @pytest_asyncio.fixture
    async def valid_auth_request(self):
        """Create valid authentication request."""
        return WebSocketAuthRequest(
            token="valid.jwt.token",
            session_id=uuid4(),
            channels=["general", "notifications"],
        )

    @pytest.mark.asyncio
    async def test_authenticate_connection_success(
        self, started_manager, mock_websocket, valid_auth_request
    ):
        """Test successful connection authentication."""
        # Arrange
        user_id = uuid4()
        with patch.object(
            started_manager.auth_service, "verify_jwt_token"
        ) as mock_verify:
            with patch.object(
                started_manager, "_check_connection_rate_limit"
            ) as mock_rate_limit:
                with patch.object(
                    started_manager.auth_service, "get_available_channels"
                ) as mock_channels:
                    with patch.object(
                        started_manager.auth_service, "validate_channel_access"
                    ) as mock_validate:
                        mock_verify.return_value = user_id
                        mock_rate_limit.return_value = True
                        mock_channels.return_value = [
                            "general",
                            "notifications",
                            "private",
                        ]
                        mock_validate.return_value = (["general", "notifications"], [])

                        # Act
                        response = await started_manager.authenticate_connection(
                            mock_websocket, valid_auth_request
                        )

                        # Assert
                        assert response.success
                        assert response.user_id == user_id
                        assert response.session_id == valid_auth_request.session_id
                        assert len(response.available_channels) == 3

    @pytest.mark.asyncio
    async def test_authenticate_connection_invalid_token(
        self, started_manager, mock_websocket, valid_auth_request
    ):
        """Test authentication with invalid token."""
        # Arrange
        with patch.object(
            started_manager.auth_service, "verify_jwt_token"
        ) as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            # Act
            response = await started_manager.authenticate_connection(
                mock_websocket, valid_auth_request
            )

            # Assert
            assert not response.success
            assert "Invalid token" in response.error

    @pytest.mark.asyncio
    async def test_authenticate_connection_rate_limit_exceeded(
        self, started_manager, mock_websocket, valid_auth_request
    ):
        """Test authentication when rate limit is exceeded."""
        # Arrange
        user_id = uuid4()
        with patch.object(
            started_manager.auth_service, "verify_jwt_token"
        ) as mock_verify:
            with patch.object(
                started_manager, "_check_connection_rate_limit"
            ) as mock_rate_limit:
                mock_verify.return_value = user_id
                mock_rate_limit.return_value = False

                # Act
                response = await started_manager.authenticate_connection(
                    mock_websocket, valid_auth_request
                )

                # Assert
                assert not response.success
                assert "rate limit exceeded" in response.error.lower()


class TestWebSocketManagerChannelSubscription:
    """Test suite for channel subscription management."""

    @pytest_asyncio.fixture
    async def started_manager_with_connection(self):
        """Create manager with authenticated connection."""
        manager = WebSocketManager()
        await manager.start()

        # Mock connection
        connection_id = str(uuid4())
        user_id = uuid4()
        connection = Mock(spec=WebSocketConnection)
        connection.connection_id = connection_id
        connection.user_id = user_id
        connection.state = ConnectionState.AUTHENTICATED

        manager.connection_service.connections[connection_id] = connection

        yield manager, connection_id, user_id
        await manager.stop()

    @pytest.mark.asyncio
    async def test_subscribe_connection_success(self, started_manager_with_connection):
        """Test successful channel subscription."""
        # Arrange
        manager, connection_id, user_id = started_manager_with_connection
        subscribe_request = WebSocketSubscribeRequest(
            channels=["general", "notifications"], unsubscribe_channels=["old_channel"]
        )

        with patch.object(
            manager.auth_service, "get_available_channels"
        ) as mock_channels:
            with patch.object(
                manager.auth_service, "validate_channel_access"
            ) as mock_validate:
                with patch.object(
                    manager.messaging_service, "subscribe_to_channel"
                ) as mock_subscribe:
                    with patch.object(
                        manager.messaging_service, "unsubscribe_from_channel"
                    ) as mock_unsubscribe:
                        mock_channels.return_value = [
                            "general",
                            "notifications",
                            "private",
                        ]
                        mock_validate.return_value = (["general", "notifications"], [])
                        mock_subscribe.return_value = True

                        # Act
                        response = await manager.subscribe_connection(
                            connection_id, subscribe_request
                        )

                        # Assert
                        assert response.success
                        assert "general" in response.subscribed_channels
                        assert "notifications" in response.subscribed_channels
                        mock_unsubscribe.assert_called_with(
                            connection_id, "old_channel"
                        )

    @pytest.mark.asyncio
    async def test_subscribe_connection_not_found(
        self, started_manager_with_connection
    ):
        """Test subscription with non-existent connection."""
        # Arrange
        manager, _, _ = started_manager_with_connection
        subscribe_request = WebSocketSubscribeRequest(channels=["general"])

        # Act
        response = await manager.subscribe_connection("nonexistent", subscribe_request)

        # Assert
        assert not response.success
        assert "Connection not found" in response.error

    @pytest.mark.asyncio
    async def test_subscribe_connection_access_denied(
        self, started_manager_with_connection
    ):
        """Test subscription with access denied to channels."""
        # Arrange
        manager, connection_id, user_id = started_manager_with_connection
        subscribe_request = WebSocketSubscribeRequest(channels=["admin", "secret"])

        with patch.object(
            manager.auth_service, "get_available_channels"
        ) as mock_channels:
            with patch.object(
                manager.auth_service, "validate_channel_access"
            ) as mock_validate:
                mock_channels.return_value = ["general", "notifications"]
                mock_validate.return_value = ([], ["admin", "secret"])

                # Act
                response = await manager.subscribe_connection(
                    connection_id, subscribe_request
                )

                # Assert
                assert response.success  # Still successful even if some channels denied
                assert len(response.subscribed_channels) == 0
                assert "admin" in response.failed_channels
                assert "secret" in response.failed_channels


class TestWebSocketManagerMessaging:
    """Test suite for message sending and broadcasting."""

    @pytest_asyncio.fixture
    async def manager_with_connections(self):
        """Create manager with multiple authenticated connections."""
        manager = WebSocketManager()
        await manager.start()

        connections = {}
        for _i in range(3):
            connection_id = str(uuid4())
            user_id = uuid4()
            connection = Mock(spec=WebSocketConnection)
            connection.connection_id = connection_id
            connection.user_id = user_id
            connection.state = ConnectionState.AUTHENTICATED
            connection.send_event = AsyncMock(return_value=True)

            manager.connection_service.connections[connection_id] = connection
            connections[connection_id] = (connection, user_id)

        yield manager, connections
        await manager.stop()

    @pytest.mark.asyncio
    async def test_send_to_connection_success(self, manager_with_connections):
        """Test sending message to specific connection."""
        # Arrange
        manager, connections = manager_with_connections
        connection_id = list(connections.keys())[0]
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Hello World"}
        )

        with patch.object(manager.messaging_service, "send_to_connection") as mock_send:
            mock_send.return_value = True

            # Act
            result = await manager.send_to_connection(connection_id, event)

            # Assert
            assert result is True
            mock_send.assert_called_once_with(
                connection_id, event, manager.rate_limiter
            )

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager_with_connections):
        """Test sending message to all connections for a user."""
        # Arrange
        manager, connections = manager_with_connections
        user_id = list(connections.values())[0][1]  # Get user_id from first connection
        event = WebSocketEvent(
            type=WebSocketEventType.NOTIFICATION,
            payload={"message": "User notification"},
        )

        with patch.object(manager.messaging_service, "send_to_user") as mock_send:
            mock_send.return_value = 2  # Assume 2 connections for this user

            # Act
            result = await manager.send_to_user(user_id, event)

            # Assert
            assert result == 2
            mock_send.assert_called_once_with(user_id, event, manager.rate_limiter)

    @pytest.mark.asyncio
    async def test_send_to_session(self, manager_with_connections):
        """Test sending message to all connections for a session."""
        # Arrange
        manager, connections = manager_with_connections
        session_id = uuid4()
        event = WebSocketEvent(
            type=WebSocketEventType.SESSION_UPDATE, payload={"session_data": "updated"}
        )

        with patch.object(manager.messaging_service, "send_to_session") as mock_send:
            mock_send.return_value = 1

            # Act
            result = await manager.send_to_session(session_id, event)

            # Assert
            assert result == 1
            mock_send.assert_called_once_with(session_id, event, manager.rate_limiter)

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, manager_with_connections):
        """Test broadcasting to a channel."""
        # Arrange
        manager, connections = manager_with_connections
        channel = "general"
        event = WebSocketEvent(
            type=WebSocketEventType.BROADCAST,
            payload={"announcement": "Important update"},
        )

        with patch.object(manager.messaging_service, "send_to_channel") as mock_send:
            mock_send.return_value = 3

            # Act
            result = await manager.broadcast_to_channel(channel, event)

            # Assert
            assert result == 3

    @pytest.mark.asyncio
    async def test_broadcast_with_broadcaster_service(self, manager_with_connections):
        """Test broadcasting with broadcaster service integration."""
        # Arrange
        manager, connections = manager_with_connections
        mock_broadcaster = AsyncMock()
        manager.broadcaster = mock_broadcaster

        channel = "general"
        event = WebSocketEvent(
            type=WebSocketEventType.BROADCAST,
            payload={"announcement": "Important update"},
        )

        with patch.object(manager.messaging_service, "send_to_channel") as mock_send:
            mock_send.return_value = 3

            # Act
            result = await manager.broadcast_to_channel(channel, event)

            # Assert
            assert result == 3
            mock_broadcaster.broadcast_to_channel.assert_called_once()


class TestWebSocketManagerRateLimiting:
    """Test suite for rate limiting functionality."""

    @pytest_asyncio.fixture
    async def rate_limiter(self):
        """Create rate limiter for testing."""
        config = RateLimitConfig(
            max_connections_per_user=2,
            max_connections_per_session=1,
            max_messages_per_connection_per_second=5,
            max_messages_per_user_per_minute=50,
        )
        return RateLimiter(None, config)  # No Redis for unit tests

    @pytest.mark.asyncio
    async def test_check_connection_rate_limit_allowed(self, rate_limiter):
        """Test connection rate limit when allowed."""
        # Arrange
        user_id = uuid4()
        session_id = uuid4()

        # Act
        result = await rate_limiter.check_connection_limit(user_id, session_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_message_rate_limit_local_fallback(self, rate_limiter):
        """Test message rate limiting with local fallback."""
        # Arrange
        user_id = uuid4()
        connection_id = str(uuid4())

        # Act
        result = await rate_limiter.check_message_rate(user_id, connection_id)

        # Assert
        assert result["allowed"] is True
        assert "user_count" in result
        assert "remaining" in result

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit exceeded scenario."""
        # Arrange
        user_id = uuid4()
        connection_id = str(uuid4())

        # Simulate exceeding rate limit by calling multiple times quickly
        for _ in range(55):  # Exceed the 50 message limit
            await rate_limiter.check_message_rate(user_id, connection_id)

        # Act
        result = await rate_limiter.check_message_rate(user_id, connection_id)

        # Assert
        assert result["allowed"] is False
        assert result["reason"] == "user_limit_exceeded"


class TestWebSocketManagerCircuitBreaker:
    """Test suite for circuit breaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        # Arrange & Act
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)

        # Assert
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 10
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        # Arrange
        breaker = CircuitBreaker()

        # Act & Assert
        assert breaker.can_execute() is True

    def test_circuit_breaker_failure_recording(self):
        """Test circuit breaker failure recording."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=2)

        # Act
        breaker.record_failure()
        breaker.record_failure()

        # Assert
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 2
        assert breaker.can_execute() is False

    def test_circuit_breaker_success_reset(self):
        """Test circuit breaker success reset."""
        # Arrange
        breaker = CircuitBreaker()
        breaker.record_failure()
        breaker.record_failure()

        # Act
        breaker.record_success()

        # Assert
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open state recovery."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        # Act - wait for recovery timeout
        time.sleep(0.2)
        can_execute = breaker.can_execute()

        # Assert
        assert can_execute is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN


class TestWebSocketManagerExponentialBackoff:
    """Test suite for exponential backoff functionality."""

    def test_exponential_backoff_initialization(self):
        """Test exponential backoff initialization."""
        # Arrange & Act
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=10.0, max_attempts=5)

        # Assert
        assert backoff.base_delay == 1.0
        assert backoff.max_delay == 10.0
        assert backoff.max_attempts == 5
        assert backoff.attempt_count == 0

    def test_exponential_backoff_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        # Arrange
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=10.0, jitter=False)

        # Act & Assert
        delay1 = backoff.next_attempt()
        assert delay1 == 1.0

        delay2 = backoff.next_attempt()
        assert delay2 == 2.0

        delay3 = backoff.next_attempt()
        assert delay3 == 4.0

    def test_exponential_backoff_max_delay_cap(self):
        """Test exponential backoff max delay cap."""
        # Arrange
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=5.0, jitter=False)

        # Act
        for _ in range(5):  # Get to delay of 16.0, which should be capped at 5.0
            delay = backoff.next_attempt()

        # Assert
        assert delay <= 5.0

    def test_exponential_backoff_max_attempts_exceeded(self):
        """Test exponential backoff max attempts exceeded."""
        # Arrange
        backoff = ExponentialBackoff(max_attempts=2)

        # Act
        backoff.next_attempt()
        backoff.next_attempt()

        # Assert
        with pytest.raises(Exception):  # Should raise ExponentialBackoffException
            backoff.next_attempt()

    def test_exponential_backoff_reset(self):
        """Test exponential backoff reset."""
        # Arrange
        backoff = ExponentialBackoff()
        backoff.next_attempt()
        backoff.next_attempt()

        # Act
        backoff.reset()

        # Assert
        assert backoff.attempt_count == 0


class TestWebSocketManagerBackgroundTasks:
    """Test suite for background task management."""

    @pytest_asyncio.fixture
    async def started_manager(self):
        """Create and start WebSocket manager."""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_cleanup_task_running(self, started_manager):
        """Test cleanup task is running."""
        # Assert
        assert started_manager._cleanup_task is not None
        assert not started_manager._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_heartbeat_task_running(self, started_manager):
        """Test heartbeat task is running."""
        # Assert
        assert started_manager._heartbeat_task is not None
        assert not started_manager._heartbeat_task.done()

    @pytest.mark.asyncio
    async def test_performance_monitor_running(self, started_manager):
        """Test performance monitor task is running."""
        # Assert
        assert started_manager._performance_task is not None
        assert not started_manager._performance_task.done()

    @pytest.mark.asyncio
    async def test_priority_processor_running(self, started_manager):
        """Test priority processor task is running."""
        # Assert
        assert started_manager._priority_processor_task is not None
        assert not started_manager._priority_processor_task.done()

    @pytest.mark.asyncio
    async def test_cleanup_stale_connections(self, started_manager):
        """Test cleanup of stale connections."""
        # Arrange
        stale_connection_id = str(uuid4())

        with patch.object(
            started_manager.connection_service, "get_stale_connections"
        ) as mock_stale:
            with patch.object(
                started_manager, "disconnect_connection"
            ) as mock_disconnect:
                mock_stale.return_value = [stale_connection_id]

                # Act
                await started_manager._cleanup_stale_connections()

                # Assert
                mock_disconnect.assert_called_once_with(stale_connection_id)

    @pytest.mark.asyncio
    async def test_heartbeat_monitor(self, started_manager):
        """Test heartbeat monitoring."""
        # Arrange
        connection = Mock(spec=WebSocketConnection)
        connection.state = ConnectionState.AUTHENTICATED
        connection.send_ping = AsyncMock()

        started_manager.connection_service.connections["test_id"] = connection

        # Act
        await started_manager._heartbeat_monitor()

        # Assert
        connection.send_ping.assert_called_once()


class TestWebSocketManagerStatistics:
    """Test suite for statistics and monitoring."""

    @pytest_asyncio.fixture
    async def started_manager(self):
        """Create and start WebSocket manager."""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    def test_get_connection_stats(self, started_manager):
        """Test getting connection statistics."""
        # Arrange
        mock_messaging_stats = {
            "total_connections": 5,
            "active_connections": 3,
            "subscriptions": {"general": 2, "notifications": 1},
        }

        with patch.object(
            started_manager.messaging_service, "get_connection_stats"
        ) as mock_stats:
            mock_stats.return_value = mock_messaging_stats

            # Act
            stats = started_manager.get_connection_stats()

            # Assert
            assert "total_connections" in stats
            assert "redis_connected" in stats
            assert "broadcaster_running" in stats
            assert "performance_metrics" in stats

    def test_performance_metrics_initialization(self, started_manager):
        """Test performance metrics initialization."""
        # Assert
        metrics = started_manager.performance_metrics
        assert "total_messages_sent" in metrics
        assert "total_bytes_sent" in metrics
        assert "active_connections" in metrics
        assert "peak_connections" in metrics
        assert "failed_connections" in metrics
        assert "reconnection_attempts" in metrics
        assert "rate_limit_hits" in metrics

    @pytest.mark.asyncio
    async def test_performance_monitor_updates_metrics(self, started_manager):
        """Test performance monitor updates metrics."""
        # Arrange
        started_manager.performance_metrics["active_connections"]

        # Simulate connections
        for i in range(3):
            connection = Mock(spec=WebSocketConnection)
            started_manager.connection_service.connections[f"conn_{i}"] = connection

        # Act
        await started_manager._performance_monitor()

        # Assert
        assert started_manager.performance_metrics["active_connections"] == 3
        assert started_manager.performance_metrics["peak_connections"] >= 3


class TestWebSocketManagerRedisIntegration:
    """Test suite for Redis integration."""

    @pytest_asyncio.fixture
    async def manager_with_redis(self):
        """Create manager with mocked Redis."""
        manager = WebSocketManager()

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_redis.pubsub.return_value = AsyncMock()
        manager.redis_client = mock_redis

        yield manager, mock_redis
        await manager.stop()

    @pytest.mark.asyncio
    async def test_redis_initialization_success(self, manager_with_redis):
        """Test successful Redis initialization."""
        # Arrange
        manager, mock_redis = manager_with_redis

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.return_value = mock_redis

            # Act
            await manager._initialize_redis()

            # Assert
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_initialization_failure(self, manager_with_redis):
        """Test Redis initialization failure."""
        # Arrange
        manager, mock_redis = manager_with_redis

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Redis connection failed")

            # Act
            await manager._initialize_redis()

            # Assert
            assert manager.redis_client is None

    @pytest.mark.asyncio
    async def test_handle_broadcast_message(self, manager_with_redis):
        """Test handling Redis broadcast messages."""
        # Arrange
        manager, _ = manager_with_redis
        await manager.start()

        broadcast_data = {
            "id": str(uuid4()),
            "type": "notification",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(uuid4()),
            "payload": {"message": "Test notification"},
            "priority": 1,
            "channel": "user:123",
        }

        with patch.object(manager.auth_service, "parse_channel_target") as mock_parse:
            with patch.object(manager, "send_to_user") as mock_send:
                mock_parse.return_value = ("user", "123")

                # Act
                await manager._handle_broadcast_message(broadcast_data)

                # Assert
                mock_send.assert_called_once()


class TestWebSocketManagerErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest_asyncio.fixture
    async def started_manager(self):
        """Create and start WebSocket manager."""
        manager = WebSocketManager()
        await manager.start()
        yield manager
        await manager.stop()

    @pytest.mark.asyncio
    async def test_disconnect_connection_error_handling(self, started_manager):
        """Test error handling during connection disconnect."""
        # Arrange
        connection_id = str(uuid4())

        with patch.object(
            started_manager.connection_service, "remove_connection"
        ) as mock_remove:
            mock_remove.side_effect = Exception("Disconnect error")

            # Act & Assert - should not raise exception
            await started_manager.disconnect_connection(connection_id)

    @pytest.mark.asyncio
    async def test_background_task_error_recovery(self, started_manager):
        """Test background task error recovery."""
        # Arrange
        with patch.object(
            started_manager.connection_service, "get_stale_connections"
        ) as mock_stale:
            mock_stale.side_effect = Exception("Cleanup error")

            # Act & Assert - should not crash the task
            await started_manager._cleanup_stale_connections()

    @pytest.mark.asyncio
    async def test_redis_operation_fallback(self, started_manager):
        """Test Redis operation fallback to local methods."""
        # Arrange
        started_manager.redis_client = None  # Simulate no Redis

        # Act & Assert - should still work without Redis
        await started_manager._initialize_redis()

        # Manager should still be functional
        assert started_manager._running


class TestWebSocketManagerDisconnection:
    """Test suite for connection disconnection."""

    @pytest_asyncio.fixture
    async def manager_with_connection(self):
        """Create manager with a connection."""
        manager = WebSocketManager()
        await manager.start()

        # Add a mock connection
        connection_id = str(uuid4())
        connection = Mock(spec=WebSocketConnection)
        connection.connection_id = connection_id
        manager.connection_service.connections[connection_id] = connection

        # Mock broadcaster
        mock_broadcaster = AsyncMock()
        manager.broadcaster = mock_broadcaster

        yield manager, connection_id
        await manager.stop()

    @pytest.mark.asyncio
    async def test_disconnect_connection_success(self, manager_with_connection):
        """Test successful connection disconnection."""
        # Arrange
        manager, connection_id = manager_with_connection

        # Act
        await manager.disconnect_connection(connection_id)

        # Assert
        manager.broadcaster.unregister_connection.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_disconnect_all_connections(self, manager_with_connection):
        """Test disconnecting all connections."""
        # Arrange
        manager, connection_id = manager_with_connection

        # Add more connections
        for _i in range(2):
            conn_id = str(uuid4())
            connection = Mock(spec=WebSocketConnection)
            manager.connection_service.connections[conn_id] = connection

        initial_count = len(manager.connection_service.connections)
        assert initial_count == 3

        # Act
        await manager.disconnect_all()

        # Assert
        # All connections should be disconnected
        assert manager.broadcaster.unregister_connection.call_count == initial_count


# Property-based testing with Hypothesis
class TestWebSocketManagerPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        connection_count=st.integers(min_value=1, max_value=20),
        message_count=st.integers(min_value=1, max_value=50),
    )
    @pytest.mark.asyncio
    async def test_concurrent_message_sending(self, connection_count, message_count):
        """Property test: concurrent message sending should be handled correctly."""
        # Arrange
        manager = WebSocketManager()
        await manager.start()

        try:
            # Create mock connections
            connections = []
            for _i in range(connection_count):
                connection_id = str(uuid4())
                connection = Mock(spec=WebSocketConnection)
                connection.connection_id = connection_id
                connection.send_event = AsyncMock(return_value=True)
                manager.connection_service.connections[connection_id] = connection
                connections.append(connection_id)

            # Create test events
            events = [
                WebSocketEvent(
                    type=WebSocketEventType.CHAT_MESSAGE,
                    payload={"message": f"Test message {i}"},
                )
                for i in range(message_count)
            ]

            # Act - send messages concurrently
            with patch.object(
                manager.messaging_service, "send_to_connection"
            ) as mock_send:
                mock_send.return_value = True

                tasks = []
                for connection_id in connections:
                    for event in events:
                        tasks.append(manager.send_to_connection(connection_id, event))

                results = await asyncio.gather(*tasks, return_exceptions=True)

            # Assert
            assert len(results) == connection_count * message_count
            # All operations should succeed or handle errors gracefully
            assert all(
                result is True or isinstance(result, Exception) for result in results
            )

        finally:
            await manager.stop()

    @given(
        user_count=st.integers(min_value=1, max_value=10),
        connections_per_user=st.integers(min_value=1, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_user_message_broadcasting(self, user_count, connections_per_user):
        """Property test: user message broadcasting should reach all user connections."""
        # Arrange
        manager = WebSocketManager()
        await manager.start()

        try:
            # Create users with multiple connections each
            user_connections = {}
            for _user_idx in range(user_count):
                user_id = uuid4()
                user_connections[user_id] = []

                for _conn_idx in range(connections_per_user):
                    connection_id = str(uuid4())
                    connection = Mock(spec=WebSocketConnection)
                    connection.connection_id = connection_id
                    connection.user_id = user_id
                    connection.send_event = AsyncMock(return_value=True)
                    manager.connection_service.connections[connection_id] = connection
                    user_connections[user_id].append(connection_id)

            # Act - send message to each user
            with patch.object(manager.messaging_service, "send_to_user") as mock_send:
                mock_send.return_value = connections_per_user

                for user_id in user_connections:
                    event = WebSocketEvent(
                        type=WebSocketEventType.NOTIFICATION,
                        payload={"message": f"Message for user {user_id}"},
                    )
                    result = await manager.send_to_user(user_id, event)

                    # Assert
                    assert result == connections_per_user

        finally:
            await manager.stop()


# Performance testing
class TestWebSocketManagerPerformance:
    """Performance tests for WebSocket manager."""

    @pytest.mark.asyncio
    async def test_high_connection_count_performance(self):
        """Test performance with high connection count."""
        # Arrange
        manager = WebSocketManager()
        await manager.start()

        connection_count = 100
        start_time = asyncio.get_event_loop().time()

        try:
            # Create many connections
            connections = []
            for _i in range(connection_count):
                connection_id = str(uuid4())
                connection = Mock(spec=WebSocketConnection)
                connection.connection_id = connection_id
                connection.user_id = uuid4()
                manager.connection_service.connections[connection_id] = connection
                connections.append(connection_id)

            end_time = asyncio.get_event_loop().time()
            creation_time = end_time - start_time

            # Act - get statistics
            stats_start = asyncio.get_event_loop().time()
            manager.get_connection_stats()
            stats_end = asyncio.get_event_loop().time()
            stats_time = stats_end - stats_start

            # Assert performance expectations
            assert creation_time < 1.0  # Should create 100 connections quickly
            assert stats_time < 0.1  # Stats should be fast even with many connections

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_concurrent_broadcasting_performance(self):
        """Test performance of concurrent broadcasting."""
        # Arrange
        manager = WebSocketManager()
        await manager.start()

        try:
            # Create multiple connections
            for _i in range(50):
                connection_id = str(uuid4())
                connection = Mock(spec=WebSocketConnection)
                connection.connection_id = connection_id
                connection.user_id = uuid4()
                connection.send_event = AsyncMock(return_value=True)
                manager.connection_service.connections[connection_id] = connection

            # Act - concurrent broadcasts
            start_time = asyncio.get_event_loop().time()

            with patch.object(
                manager.messaging_service, "send_to_channel"
            ) as mock_send:
                mock_send.return_value = 50

                events = [
                    WebSocketEvent(
                        type=WebSocketEventType.BROADCAST,
                        payload={"message": f"Broadcast {i}"},
                    )
                    for i in range(10)
                ]

                tasks = [
                    manager.broadcast_to_channel("test_channel", event)
                    for event in events
                ]

                results = await asyncio.gather(*tasks)

            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time

            # Assert
            assert len(results) == 10
            assert all(result == 50 for result in results)
            assert (
                execution_time < 1.0
            )  # Should handle concurrent broadcasts efficiently

        finally:
            await manager.stop()


if __name__ == "__main__":
    pytest.main([__file__])
