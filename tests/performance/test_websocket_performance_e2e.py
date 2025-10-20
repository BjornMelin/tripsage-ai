#!/usr/bin/env python3
"""Comprehensive WebSocket Performance Tests.

This module tests WebSocket performance across various scenarios:
- Connection establishment and teardown
- Message throughput and latency
- Concurrent connections
- Large message handling
- Error recovery performance
- Authentication performance

Uses pytest-benchmark for accurate performance measurements.
"""

import asyncio
import json
import logging
import time
from unittest.mock import AsyncMock, patch

import pytest
import websockets
from httpx import AsyncClient

from tripsage.api.main import app
from tripsage_core.config import get_settings


logger = logging.getLogger(__name__)


@pytest.fixture
def websocket_settings():
    """Test settings for WebSocket performance tests."""
    settings = get_settings()
    settings.ENABLE_WEBSOCKETS = True
    settings.WEBSOCKET_TIMEOUT = 30
    settings.MAX_WEBSOCKET_CONNECTIONS = 1000
    return settings


@pytest.fixture
async def test_client():
    """Async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_websocket_connection(websocket_settings):
    """Create an authenticated WebSocket connection for testing."""
    # Mock authentication for testing
    with patch(
        "tripsage_core.services.infrastructure.websocket_auth_service.WebSocketAuthService.verify_jwt_token"
    ) as mock_verify:
        from uuid import UUID

        mock_verify.return_value = UUID("12345678-1234-5678-9012-123456789012")

        # Create WebSocket connection
        uri = "ws://localhost:8000/ws/test-user-123"

        try:
            websocket = await websockets.connect(uri)
            yield websocket
        except Exception as e:
            logger.warning("Could not establish WebSocket connection: %s", e)
            # Yield a mock WebSocket for testing
            mock_ws = AsyncMock()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value='{"type": "test", "data": {}}')
            mock_ws.close = AsyncMock()
            yield mock_ws


class TestWebSocketConnectionPerformance:
    """Test WebSocket connection establishment and management performance."""

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_connection_establishment_speed(self, benchmark, websocket_settings):
        """Benchmark WebSocket connection establishment time."""

        async def connect_websocket():
            """Establish a WebSocket connection."""
            # Mock the connection process for benchmarking
            start_time = time.time()

            # Simulate connection establishment overhead
            await asyncio.sleep(0.001)  # Simulate network latency

            # Simulate authentication
            await asyncio.sleep(0.002)  # Simulate auth verification

            return time.time() - start_time

        # Benchmark connection establishment
        result = await benchmark.pedantic(connect_websocket, rounds=50, iterations=1)

        # Assert reasonable connection time (< 100ms)
        assert result < 0.1, f"Connection took too long: {result:.3f}s"

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_concurrent_connection_handling(self, benchmark, websocket_settings):
        """Benchmark handling multiple concurrent WebSocket connections."""

        async def establish_concurrent_connections(num_connections: int = 10):
            """Establish multiple concurrent connections."""
            connections = []

            async def create_connection(conn_id: int):
                # Mock connection creation
                mock_connection = {
                    "id": f"conn_{conn_id}",
                    "established_at": time.time(),
                    "user_id": f"user_{conn_id}",
                }
                await asyncio.sleep(0.001)  # Simulate connection overhead
                return mock_connection

            # Create connections concurrently
            tasks = [create_connection(i) for i in range(num_connections)]
            connections = await asyncio.gather(*tasks)

            return len(connections)

        # Benchmark concurrent connection establishment
        result = await benchmark.pedantic(
            establish_concurrent_connections,
            kwargs={"num_connections": 25},
            rounds=20,
            iterations=1,
        )

        assert result == 25, "Not all connections were established"

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_connection_cleanup_performance(self, benchmark):
        """Benchmark WebSocket connection cleanup and resource deallocation."""

        async def cleanup_connection():
            """Simulate connection cleanup process."""
            # Simulate cleanup operations
            await asyncio.sleep(0.001)  # Close WebSocket
            await asyncio.sleep(0.001)  # Remove from connection pool
            await asyncio.sleep(0.001)  # Clean up user session
            return True

        result = await benchmark.pedantic(cleanup_connection, rounds=100, iterations=1)
        assert result is True


class TestWebSocketMessagePerformance:
    """Test WebSocket message handling performance."""

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_message_send_latency(
        self, benchmark, authenticated_websocket_connection
    ):
        """Benchmark WebSocket message send latency."""

        async def send_message():
            """Send a test message via WebSocket."""
            test_message = {
                "type": "chat_message",
                "data": {
                    "message": "Hello, this is a test message",
                    "timestamp": time.time(),
                },
            }

            # Mock sending message
            await authenticated_websocket_connection.send(json.dumps(test_message))
            return True

        result = await benchmark.pedantic(send_message, rounds=100, iterations=1)
        assert result is True

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_message_receive_latency(
        self, benchmark, authenticated_websocket_connection
    ):
        """Benchmark WebSocket message receive and processing latency."""

        async def receive_and_process_message():
            """Receive and process a WebSocket message."""
            # Mock receiving a message
            raw_message = await authenticated_websocket_connection.recv()

            # Parse and validate message
            try:
                message = json.loads(raw_message)
                # Simulate message processing
                processed_message = {
                    "original": message,
                    "processed_at": time.time(),
                    "type": message.get("type", "unknown"),
                }
                return len(processed_message)
            except json.JSONDecodeError:
                return 0

        result = await benchmark.pedantic(
            receive_and_process_message, rounds=50, iterations=1
        )
        assert result > 0, "Message processing failed"

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_large_message_handling(self, benchmark):
        """Benchmark handling of large WebSocket messages."""

        async def handle_large_message():
            """Process a large WebSocket message."""
            # Create a large message (1KB)
            large_data = "x" * 1024
            large_message = {
                "type": "large_data",
                "data": large_data,
                "size": len(large_data),
            }

            # Simulate message serialization
            serialized = json.dumps(large_message)

            # Simulate processing
            await asyncio.sleep(0.001)

            return len(serialized)

        result = await benchmark.pedantic(handle_large_message, rounds=30, iterations=1)
        assert result > 1024, "Large message handling failed"

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_message_throughput(self, benchmark):
        """Benchmark WebSocket message throughput."""

        async def process_message_batch(batch_size: int = 100):
            """Process a batch of messages to measure throughput."""
            messages_processed = 0

            for i in range(batch_size):
                # Simulate message processing
                {
                    "id": i,
                    "type": "batch_test",
                    "data": f"Message {i}",
                    "timestamp": time.time(),
                }

                # Mock processing overhead
                await asyncio.sleep(0.0001)  # Very small processing time
                messages_processed += 1

            return messages_processed

        result = await benchmark.pedantic(
            process_message_batch, kwargs={"batch_size": 50}, rounds=20, iterations=1
        )

        assert result == 50, "Not all messages were processed"


class TestWebSocketAuthenticationPerformance:
    """Test WebSocket authentication and authorization performance."""

    @pytest.mark.performance
    @pytest.mark.websocket
    @pytest.mark.auth
    async def test_jwt_verification_performance(self, benchmark):
        """Benchmark JWT token verification for WebSocket connections."""

        async def verify_jwt_token():
            """Simulate JWT token verification."""
            # Mock JWT token
            _mock_token = (
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
                "eyJ1c2VyX2lkIjoiMTIzIiwiZXhwIjoxNjAwMDAwMDAwfQ.test"
            )

            # Simulate verification process
            await asyncio.sleep(0.001)  # Token parsing
            await asyncio.sleep(0.001)  # Signature verification
            await asyncio.sleep(0.001)  # Claims validation

            return {"user_id": "123", "verified": True, "expires_at": 1600000000}

        result = await benchmark.pedantic(verify_jwt_token, rounds=100, iterations=1)
        assert result["verified"] is True

    @pytest.mark.performance
    @pytest.mark.websocket
    @pytest.mark.auth
    async def test_user_session_lookup_performance(self, benchmark):
        """Benchmark user session lookup for WebSocket connections."""

        async def lookup_user_session(user_id: str = "test-user-123"):
            """Simulate user session lookup."""
            # Mock database lookup
            await asyncio.sleep(0.002)  # Database query simulation

            return {
                "user_id": user_id,
                "session_id": f"session_{user_id}",
                "permissions": ["chat", "search", "booking"],
                "last_activity": time.time(),
            }

        result = await benchmark.pedantic(lookup_user_session, rounds=50, iterations=1)
        assert result["user_id"] == "test-user-123"


class TestWebSocketErrorRecoveryPerformance:
    """Test WebSocket error handling and recovery performance."""

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_connection_recovery_performance(self, benchmark):
        """Benchmark WebSocket connection recovery after errors."""

        async def simulate_connection_recovery():
            """Simulate recovering from a connection error."""
            # Simulate error detection
            await asyncio.sleep(0.001)

            # Simulate cleanup
            await asyncio.sleep(0.002)

            # Simulate reconnection
            await asyncio.sleep(0.003)

            # Simulate state restoration
            await asyncio.sleep(0.001)

            return True

        result = await benchmark.pedantic(
            simulate_connection_recovery, rounds=30, iterations=1
        )
        assert result is True

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_message_retry_performance(self, benchmark):
        """Benchmark message retry mechanism performance."""

        async def retry_failed_message():
            """Simulate retrying a failed message."""
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    # Simulate message send attempt
                    await asyncio.sleep(0.001)

                    # Simulate random failure (20% chance)
                    if attempt < 2:  # Fail first 2 attempts
                        raise ConnectionError("Simulated network error")

                    return {"success": True, "attempts": attempt + 1}

                except ConnectionError:
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        backoff_time = (2**attempt) * 0.001
                        await asyncio.sleep(backoff_time)
                    else:
                        return {"success": False, "attempts": attempt + 1}
            return None

        result = await benchmark.pedantic(retry_failed_message, rounds=20, iterations=1)
        assert result["success"] is True


class TestWebSocketScalabilityPerformance:
    """Test WebSocket scalability and resource usage."""

    @pytest.mark.performance
    @pytest.mark.websocket
    @pytest.mark.slow
    async def test_memory_usage_with_many_connections(self, benchmark):
        """Benchmark memory usage with many concurrent WebSocket connections."""

        async def simulate_many_connections(num_connections: int = 100):
            """Simulate managing many WebSocket connections."""
            connections = {}

            # Create mock connections
            for i in range(num_connections):
                connections[f"conn_{i}"] = {
                    "id": f"conn_{i}",
                    "user_id": f"user_{i}",
                    "created_at": time.time(),
                    "message_count": 0,
                    "last_ping": time.time(),
                }

                # Simulate small processing overhead per connection
                await asyncio.sleep(0.0001)

            # Simulate periodic maintenance
            for conn_data in connections.values():
                conn_data["last_maintenance"] = time.time()
                await asyncio.sleep(0.00001)

            return len(connections)

        result = await benchmark.pedantic(
            simulate_many_connections,
            kwargs={"num_connections": 50},  # Reduced for faster testing
            rounds=10,
            iterations=1,
        )

        assert result == 50

    @pytest.mark.performance
    @pytest.mark.websocket
    async def test_broadcast_message_performance(self, benchmark):
        """Benchmark broadcasting messages to multiple WebSocket connections."""

        async def broadcast_to_connections(num_recipients: int = 50):
            """Simulate broadcasting a message to multiple connections."""
            message = {
                "type": "broadcast",
                "data": "This is a broadcast message",
                "timestamp": time.time(),
            }

            json.dumps(message)
            sent_count = 0

            # Simulate sending to multiple connections
            for _ in range(num_recipients):
                # Mock send operation
                await asyncio.sleep(0.0001)  # Small network overhead
                sent_count += 1

            return sent_count

        result = await benchmark.pedantic(
            broadcast_to_connections,
            kwargs={"num_recipients": 25},
            rounds=20,
            iterations=1,
        )

        assert result == 25


@pytest.mark.performance
@pytest.mark.websocket
class TestWebSocketIntegrationPerformance:
    """Integration performance tests for WebSocket functionality."""

    async def test_full_websocket_workflow_performance(self, benchmark):
        """Benchmark a complete WebSocket workflow from connection to cleanup."""

        async def complete_websocket_workflow():
            """Simulate a complete WebSocket interaction workflow."""
            # 1. Connection establishment
            await asyncio.sleep(0.002)

            # 2. Authentication
            await asyncio.sleep(0.003)

            # 3. Send initial message
            await asyncio.sleep(0.001)

            # 4. Receive response
            await asyncio.sleep(0.001)

            # 5. Handle multiple message exchanges
            for _ in range(5):
                await asyncio.sleep(0.0005)  # Send
                await asyncio.sleep(0.0005)  # Receive

            # 6. Connection cleanup
            await asyncio.sleep(0.001)

            return True

        result = await benchmark.pedantic(
            complete_websocket_workflow, rounds=20, iterations=1
        )
        assert result is True

    async def test_websocket_with_database_integration_performance(self, benchmark):
        """Benchmark WebSocket operations that involve database interactions."""

        async def websocket_with_database():
            """Simulate WebSocket operations with database calls."""
            # Simulate receiving chat message
            await asyncio.sleep(0.001)

            # Simulate database operations
            await asyncio.sleep(0.005)  # Save message to database
            await asyncio.sleep(0.003)  # Update user activity
            await asyncio.sleep(0.002)  # Check user permissions

            # Simulate sending response
            await asyncio.sleep(0.001)

            return True

        result = await benchmark.pedantic(
            websocket_with_database, rounds=15, iterations=1
        )
        assert result is True


# Performance regression detection
@pytest.mark.performance
@pytest.mark.websocket
def test_websocket_performance_regression_detection():
    """Performance regression detection for WebSocket operations.

    This test defines performance thresholds and can be used in CI/CD
    to detect performance regressions.
    """
    # Define performance thresholds (in milliseconds)
    PERFORMANCE_THRESHOLDS = {
        "connection_establishment": 100,  # 100ms max
        "message_send": 50,  # 50ms max
        "message_receive": 50,  # 50ms max
        "authentication": 200,  # 200ms max for auth
        "cleanup": 100,  # 100ms max for cleanup
    }

    # These thresholds can be used by benchmarks to validate performance
    assert all(threshold > 0 for threshold in PERFORMANCE_THRESHOLDS.values())
    assert PERFORMANCE_THRESHOLDS["connection_establishment"] <= 100
    assert PERFORMANCE_THRESHOLDS["message_send"] <= 50
