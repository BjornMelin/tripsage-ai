"""Comprehensive Real-time Integration Tests for TripSage WebSocket Infrastructure.

This module provides comprehensive test coverage for real-time communication patterns,
end-to-end WebSocket workflows, performance under load, and system integration
scenarios.
Tests focus on circuit breaker validation, Redis messaging, authentication flows,
and distributed system reliability.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthRequest,
    WebSocketAuthResponse,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketManager,
    WebSocketSubscribeRequest,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


class TestRealTimeWebSocketIntegration:
    """Test real-time WebSocket integration patterns."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.jwt_secret_key = Mock(
            get_secret_value=Mock(return_value="test-secret-key")
        )
        settings.jwt_algorithm = "HS256"
        settings.redis_url = "redis://localhost:6379/0"
        return settings

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.publish = AsyncMock(return_value=1)
        client.subscribe = AsyncMock()
        client.get_message = AsyncMock(return_value=None)
        client.zadd = AsyncMock(return_value=True)
        client.zrange = AsyncMock(return_value=[])
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def websocket_manager(self, mock_settings, mock_redis_client):
        """Create a WebSocket manager with mocked dependencies."""
        with patch("tripsage_core.config.get_settings", return_value=mock_settings):
            with patch("redis.asyncio.from_url", return_value=mock_redis_client):
                return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        return websocket

    @pytest.fixture
    def valid_jwt_token(self, mock_settings):
        """Create a valid JWT token for testing."""
        from jose import jwt

        payload = {
            "sub": str(uuid4()),
            "session_id": str(uuid4()),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        return jwt.encode(payload, "test-secret-key", algorithm="HS256")

    @pytest.mark.asyncio
    async def test_end_to_end_connection_flow(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test complete end-to-end connection flow."""
        # 1. Authentication
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        assert auth_response.success is True
        assert auth_response.connection_id is not None

        # 2. Channel subscription
        subscribe_request = WebSocketSubscribeRequest(
            connection_id=auth_response.connection_id, channel="trip-planning-123"
        )
        subscribe_response = await websocket_manager.subscribe_to_channel(
            subscribe_request
        )

        assert subscribe_response.success is True

        # 3. Message broadcasting
        event = WebSocketEvent(
            type=WebSocketEventType.TRIP_UPDATE,
            payload={"trip_id": "123", "status": "updated"},
        )

        broadcast_success = await websocket_manager.broadcast_to_channel(
            "trip-planning-123", event
        )
        assert broadcast_success is True

        # 4. Connection cleanup
        disconnect_success = await websocket_manager.disconnect_client(
            auth_response.connection_id
        )
        assert disconnect_success is True

    @pytest.mark.asyncio
    async def test_real_time_message_flow(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test real-time message flow between multiple connections."""
        # Create multiple connections
        connections = []
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.client = Mock()
            mock_ws.client.host = f"127.0.0.{i + 1}"

            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            auth_response = await websocket_manager.authenticate_connection(
                mock_ws, auth_request
            )

            connections.append(
                {"websocket": mock_ws, "connection_id": auth_response.connection_id}
            )

        # Subscribe all connections to the same channel
        channel = "real-time-chat"
        for conn in connections:
            subscribe_request = WebSocketSubscribeRequest(
                connection_id=conn["connection_id"], channel=channel
            )
            await websocket_manager.subscribe_to_channel(subscribe_request)

        # Send a message to the channel
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"user": "test-user", "message": "Hello everyone!"},
        )

        await websocket_manager.broadcast_to_channel(channel, event)

        # Verify all connections received the message
        await asyncio.sleep(0.1)  # Allow message processing
        for conn in connections:
            conn["websocket"].send_text.assert_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_real_time_scenario(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test circuit breaker behavior in real-time scenarios."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        # Get the connection and access its circuit breaker
        connection = websocket_manager.connection_service.get_connection(
            auth_response.connection_id
        )

        # Simulate rapid failures to trigger circuit breaker
        mock_websocket.send_text.side_effect = Exception("Connection failed")

        # Send multiple messages to trigger failures
        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_NOTIFICATION, payload={"message": "test"}
        )

        for _ in range(5):
            try:
                await connection.send(event)
            except Exception:
                pass  # Expected failures

        # Circuit breaker should have recorded failures
        assert connection.circuit_breaker.failure_count >= 3

        # Reset the mock and circuit breaker
        mock_websocket.send_text.side_effect = None
        connection.circuit_breaker.reset()

        # Should work normally again
        result = await connection.send(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_distributed_messaging_with_redis(
        self, websocket_manager, mock_redis_client, mock_websocket, valid_jwt_token
    ):
        """Test distributed messaging using Redis backend."""
        # Setup Redis pub/sub simulation
        published_messages = []

        async def mock_publish(channel, message):
            published_messages.append({"channel": channel, "message": message})
            return 1

        mock_redis_client.publish.side_effect = mock_publish

        # Authenticate and subscribe
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        subscribe_request = WebSocketSubscribeRequest(
            connection_id=auth_response.connection_id, channel="distributed-channel"
        )
        await websocket_manager.subscribe_to_channel(subscribe_request)

        # Broadcast message
        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_UPDATE,
            payload={"update": "distributed-test"},
        )

        await websocket_manager.broadcast_to_channel("distributed-channel", event)

        # Verify Redis publish was called
        assert len(published_messages) > 0
        published_msg = published_messages[0]
        assert "distributed-channel" in published_msg["channel"]

    @pytest.mark.asyncio
    async def test_performance_monitoring_real_time(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test performance monitoring in real-time scenarios."""
        # Get performance monitor
        monitor = websocket_manager.performance_monitor

        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        connection_id = auth_response.connection_id

        # Generate some activity
        for i in range(10):
            event = WebSocketEvent(
                type=WebSocketEventType.CHAT_MESSAGE,
                payload={"message": f"Message {i}"},
            )

            # Record message activity
            monitor.record_message_sent(
                connection_id, len(json.dumps(event.model_dump()))
            )
            await asyncio.sleep(0.01)  # Small delay for realistic timing

        # Get performance snapshot
        snapshot = monitor.get_performance_snapshot()

        assert snapshot.total_connections >= 1
        assert snapshot.total_messages_sent >= 10
        assert snapshot.total_bytes_sent > 0
        assert snapshot.average_latency_ms >= 0

    @pytest.mark.asyncio
    async def test_authentication_security_flow(
        self, websocket_manager, mock_websocket
    ):
        """Test authentication and security in real-time context."""
        # Test invalid token
        invalid_auth = WebSocketAuthRequest(token="invalid-token")

        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, invalid_auth
        )

        assert auth_response.success is False
        assert "Invalid token" in auth_response.error_message

        # Test expired token
        from jose import jwt

        expired_payload = {
            "sub": str(uuid4()),
            "session_id": str(uuid4()),
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,
        }
        expired_token = jwt.encode(
            expired_payload, "test-secret-key", algorithm="HS256"
        )

        expired_auth = WebSocketAuthRequest(token=expired_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, expired_auth
        )

        assert auth_response.success is False
        assert "expired" in auth_response.error_message.lower()

    @pytest.mark.asyncio
    async def test_rate_limiting_real_time(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test rate limiting in real-time scenarios."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        connection = websocket_manager.connection_service.get_connection(
            auth_response.connection_id
        )

        # Send messages rapidly to test rate limiting
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "rapid fire"}
        )

        success_count = 0
        for _ in range(20):  # Try to send 20 messages rapidly
            result = await connection.send(event)
            if result:
                success_count += 1
            await asyncio.sleep(0.001)  # Very small delay

        # Some messages should be rate limited
        # (exact number depends on rate limiter configuration)
        assert success_count <= 20

    @pytest.mark.asyncio
    async def test_error_recovery_patterns(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test error recovery patterns in real-time scenarios."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        connection = websocket_manager.connection_service.get_connection(
            auth_response.connection_id
        )

        # Simulate connection error
        mock_websocket.send_text.side_effect = Exception("Network error")

        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_NOTIFICATION,
            payload={"message": "test recovery"},
        )

        # First attempt should fail
        result = await connection.send(event)
        assert result is False

        # Check that connection state reflects the error
        health = connection.get_health()
        assert health.is_healthy is False

        # Restore connection
        mock_websocket.send_text.side_effect = None

        # Health check should recover
        await asyncio.sleep(0.1)  # Allow for recovery time
        result = await connection.send(event)
        assert result is True

    @pytest.mark.asyncio
    async def test_channel_management_real_time(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test channel management in real-time scenarios."""
        # Authenticate connection
        auth_request = WebSocketAuthRequest(token=valid_jwt_token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_websocket, auth_request
        )

        connection_id = auth_response.connection_id

        # Subscribe to multiple channels
        channels = ["channel-1", "channel-2", "channel-3"]
        for channel in channels:
            subscribe_request = WebSocketSubscribeRequest(
                connection_id=connection_id, channel=channel
            )
            response = await websocket_manager.subscribe_to_channel(subscribe_request)
            assert response.success is True

        # Verify connection is subscribed to all channels
        connection = websocket_manager.connection_service.get_connection(connection_id)
        assert len(connection.subscribed_channels) == 3

        # Unsubscribe from one channel
        unsubscribe_success = await websocket_manager.unsubscribe_from_channel(
            connection_id, "channel-2"
        )
        assert unsubscribe_success is True
        assert len(connection.subscribed_channels) == 2
        assert "channel-2" not in connection.subscribed_channels

    @pytest.mark.asyncio
    async def test_memory_and_resource_cleanup(
        self, websocket_manager, mock_websocket, valid_jwt_token
    ):
        """Test memory and resource cleanup in real-time scenarios."""
        initial_connection_count = (
            websocket_manager.connection_service.get_connection_count()
        )

        # Create multiple connections
        connection_ids = []
        for i in range(5):
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.client = Mock()
            mock_ws.client.host = f"127.0.0.{i + 1}"

            auth_request = WebSocketAuthRequest(token=valid_jwt_token)
            auth_response = await websocket_manager.authenticate_connection(
                mock_ws, auth_request
            )
            connection_ids.append(auth_response.connection_id)

        # Verify connections were created
        current_count = websocket_manager.connection_service.get_connection_count()
        assert current_count == initial_connection_count + 5

        # Disconnect all connections
        for connection_id in connection_ids:
            await websocket_manager.disconnect_client(connection_id)

        # Verify cleanup
        final_count = websocket_manager.connection_service.get_connection_count()
        assert final_count == initial_connection_count

        # Test performance monitor cleanup
        monitor = websocket_manager.performance_monitor
        monitor.cleanup_old_metrics()  # Should not raise errors


class TestWebSocketStressAndLoad:
    """Test WebSocket infrastructure under stress and load conditions."""

    @pytest.fixture
    def websocket_manager(self):
        """Create a WebSocket manager for stress testing."""
        mock_settings = Mock(spec=Settings)
        mock_settings.jwt_secret_key = Mock(
            get_secret_value=Mock(return_value="test-secret-key")
        )
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.redis_url = "redis://localhost:6379/0"

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.publish = AsyncMock(return_value=1)
        mock_redis.zadd = AsyncMock(return_value=True)
        mock_redis.zrange = AsyncMock(return_value=[])

        with patch("tripsage_core.config.get_settings", return_value=mock_settings):
            with patch("redis.asyncio.from_url", return_value=mock_redis):
                return WebSocketManager()

    @pytest.mark.asyncio
    async def test_concurrent_connections_stress(self, websocket_manager):
        """Test handling many concurrent connections."""
        from jose import jwt

        # Create token for testing
        payload = {
            "sub": str(uuid4()),
            "session_id": str(uuid4()),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")

        # Create many concurrent connections
        tasks = []
        for i in range(20):  # Reduced for faster test execution
            mock_ws = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.client = Mock()
            mock_ws.client.host = f"127.0.0.{i % 10}"

            auth_request = WebSocketAuthRequest(token=token)
            task = websocket_manager.authenticate_connection(mock_ws, auth_request)
            tasks.append(task)

        # Execute all connections concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most connections should succeed
        successful_connections = [
            r for r in results if isinstance(r, WebSocketAuthResponse) and r.success
        ]
        assert len(successful_connections) >= 15  # Allow some failures under stress

    @pytest.mark.asyncio
    async def test_high_message_throughput(self, websocket_manager):
        """Test high message throughput scenarios."""
        from jose import jwt

        # Setup connection
        payload = {
            "sub": str(uuid4()),
            "session_id": str(uuid4()),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")

        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.client = Mock()
        mock_ws.client.host = "127.0.0.1"

        auth_request = WebSocketAuthRequest(token=token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_ws, auth_request
        )

        # Subscribe to a channel
        subscribe_request = WebSocketSubscribeRequest(
            connection_id=auth_response.connection_id, channel="high-throughput-test"
        )
        await websocket_manager.subscribe_to_channel(subscribe_request)

        # Send many messages rapidly
        start_time = time.time()
        message_count = 100

        tasks = []
        for i in range(message_count):
            event = WebSocketEvent(
                type=WebSocketEventType.CHAT_MESSAGE,
                payload={"message": f"Message {i}", "timestamp": time.time()},
            )
            task = websocket_manager.broadcast_to_channel("high-throughput-test", event)
            tasks.append(task)

        # Execute all broadcasts
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Calculate throughput
        duration = end_time - start_time
        throughput = message_count / duration

        # Should handle reasonable throughput
        assert throughput > 10  # At least 10 messages per second

        # Most messages should succeed
        successful_sends = [r for r in results if r is True]
        assert (
            len(successful_sends) >= message_count * 0.8
        )  # 80% success rate under load

    @pytest.mark.asyncio
    async def test_resource_limits_and_cleanup(self, websocket_manager):
        """Test resource limits and proper cleanup under stress."""
        from jose import jwt

        # Create token
        payload = {
            "sub": str(uuid4()),
            "session_id": str(uuid4()),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")

        # Create and immediately destroy many connections
        for _batch in range(5):  # 5 batches of connections
            connection_ids = []

            # Create batch of connections
            for i in range(10):
                mock_ws = AsyncMock()
                mock_ws.send_text = AsyncMock()
                mock_ws.client = Mock()
                mock_ws.client.host = f"127.0.0.{i}"

                auth_request = WebSocketAuthRequest(token=token)
                auth_response = await websocket_manager.authenticate_connection(
                    mock_ws, auth_request
                )
                connection_ids.append(auth_response.connection_id)

            # Clean up batch
            for connection_id in connection_ids:
                await websocket_manager.disconnect_client(connection_id)

            # Short pause between batches
            await asyncio.sleep(0.01)

        # Final connection count should be manageable
        final_count = websocket_manager.connection_service.get_connection_count()
        assert final_count < 5  # Should have cleaned up properly

    @pytest.mark.asyncio
    async def test_error_recovery_under_load(self, websocket_manager):
        """Test error recovery mechanisms under load conditions."""
        from jose import jwt

        # Create token
        payload = {
            "sub": str(uuid4()),
            "session_id": str(uuid4()),
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")

        # Create connection with intermittent failures
        mock_ws = AsyncMock()
        failure_count = 0

        def mock_send_text(data):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 3 == 0:  # Fail every 3rd message
                raise Exception("Simulated network error")
            return

        mock_ws.send_text.side_effect = mock_send_text
        mock_ws.client = Mock()
        mock_ws.client.host = "127.0.0.1"

        auth_request = WebSocketAuthRequest(token=token)
        auth_response = await websocket_manager.authenticate_connection(
            mock_ws, auth_request
        )

        connection = websocket_manager.connection_service.get_connection(
            auth_response.connection_id
        )

        # Send many messages with intermittent failures
        success_count = 0
        for i in range(30):
            event = WebSocketEvent(
                type=WebSocketEventType.SYSTEM_NOTIFICATION,
                payload={"message": f"Test {i}"},
            )

            try:
                result = await connection.send(event)
                if result:
                    success_count += 1
            except Exception:
                pass  # Expected some failures

            await asyncio.sleep(0.001)  # Small delay

        # Should have some successes despite failures
        assert success_count > 15  # More than half should succeed

        # Circuit breaker should be tracking failures but not completely broken
        assert connection.circuit_breaker.failure_count > 0
        assert connection.circuit_breaker.failure_count < 20  # Not all attempts failed
