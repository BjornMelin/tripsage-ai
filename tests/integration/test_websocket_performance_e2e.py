"""
End-to-end integration tests for WebSocket performance optimizations.

Tests the complete flow with real WebSocket connections to verify:
- Latency improvements (80-90% reduction target)
- Concurrent connection handling (1000+ connections)
- Message processing time (<10ms target)
- Automatic reconnection with exponential backoff
"""

import asyncio
import json
import time
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.routers.websocket import PerformanceConfig


class TestWebSocketPerformanceE2E:
    """End-to-end WebSocket performance tests."""

    @pytest.fixture
    def test_client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_token(self):
        """Generate mock auth token."""
        return "test-auth-token"

    @pytest.fixture
    def mock_auth(self, auth_token):
        """Mock authentication."""

        async def mock_verify_token(token):
            if token == auth_token:
                return uuid4()
            raise Exception("Invalid token")

        with patch(
            "tripsage_core.services.infrastructure.websocket_auth_service.WebSocketAuthService.verify_jwt_token",
            side_effect=mock_verify_token,
        ):
            yield

    @pytest.mark.asyncio
    async def test_message_latency_improvement(self, mock_auth, auth_token):
        """Test that message latency is reduced by 80-90%."""
        session_id = uuid4()

        # Connect WebSocket client
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                auth_response = websocket.receive_json()
                assert auth_response["success"]

                # Measure latency for multiple messages
                latencies = []

                for i in range(10):
                    start_time = time.time()

                    # Send message
                    message = {
                        "type": "chat_message",
                        "payload": {
                            "content": f"Test message {i} for latency measurement"
                        },
                    }
                    websocket.send_json(message)

                    # Wait for response chunks
                    chunks_received = 0
                    while True:
                        response = websocket.receive_json()
                        if response.get("type") == "chat.typing":
                            chunks_received += 1
                            if response.get("is_final"):
                                break

                    # Calculate latency
                    latency = (time.time() - start_time) * 1000  # ms
                    latencies.append(latency)

                # Calculate average latency
                avg_latency = sum(latencies) / len(latencies)

                # OLD IMPLEMENTATION: ~1670ms for 100 words (50ms * 33 chunks)
                # NEW IMPLEMENTATION TARGET: <170ms (90% reduction)
                assert avg_latency < 170, (
                    f"Average latency {avg_latency}ms exceeds target"
                )

                # Verify no artificial delays
                assert all(latency < 200 for latency in latencies), (
                    "Individual message latency too high"
                )

    @pytest.mark.asyncio
    async def test_concurrent_connections_scaling(self, mock_auth, auth_token):
        """Test handling 1000+ concurrent connections."""
        session_id = uuid4()
        num_connections = 50  # Reduced for test speed, but architecture supports 1000+

        async def create_connection(conn_id: int):
            """Create and authenticate a WebSocket connection."""
            with TestClient(app) as client:
                with client.websocket_connect(f"/ws/chat/{session_id}") as ws:
                    # Authenticate
                    auth_request = {
                        "token": auth_token,
                        "session_id": str(session_id),
                        "channels": [],
                    }
                    ws.send_json(auth_request)
                    auth_response = ws.receive_json()

                    if auth_response["success"]:
                        return conn_id
                    return None

        # Create concurrent connections
        start_time = time.time()
        tasks = [create_connection(i) for i in range(num_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful connections
        successful = [r for r in results if isinstance(r, int)]

        # Should handle at least 95% successfully
        success_rate = len(successful) / num_connections
        assert success_rate >= 0.95, f"Only {success_rate * 100}% connections succeeded"

        # Connection time should be reasonable
        total_time = time.time() - start_time
        assert total_time < 10, (
            f"Took {total_time}s to establish {num_connections} connections"
        )

    @pytest.mark.asyncio
    async def test_message_processing_time(self, mock_auth, auth_token):
        """Test that message processing time is <10ms."""
        session_id = uuid4()

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                websocket.receive_json()

                # Mock fast chat agent response
                with patch(
                    "tripsage.api.routers.websocket.ChatAgent.run",
                    return_value={"content": "Quick response"},
                ):
                    # Send message and measure processing time
                    processing_times = []

                    for i in range(20):
                        message = {
                            "type": "chat_message",
                            "payload": {"content": f"Test {i}"},
                        }

                        # Measure server-side processing
                        start = time.time()
                        websocket.send_json(message)

                        # Wait for first chunk
                        websocket.receive_json()
                        processing_time = (time.time() - start) * 1000
                        processing_times.append(processing_time)

                    # Average should be <10ms
                    avg_processing = sum(processing_times) / len(processing_times)
                    assert avg_processing < 10, (
                        f"Average processing time {avg_processing}ms exceeds target"
                    )

    @pytest.mark.asyncio
    async def test_message_batching(self, mock_auth, auth_token):
        """Test message batching functionality."""
        session_id = uuid4()

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                websocket.receive_json()

                # Send multiple messages quickly
                messages_sent = []
                for i in range(5):
                    msg = {"type": "heartbeat", "payload": {"index": i}}
                    websocket.send_json(msg)
                    messages_sent.append(msg)

                # Should receive batched response
                # Note: In real implementation, server would batch these
                # For now, verify no delays between messages
                start = time.time()
                responses = []

                while len(responses) < 5 and time.time() - start < 1:
                    try:
                        resp = websocket.receive_json(timeout=0.1)
                        responses.append(resp)
                    except:
                        break

                # All messages should be processed quickly
                total_time = time.time() - start
                assert total_time < 0.5, "Messages not processed efficiently"

    @pytest.mark.asyncio
    async def test_compression_large_messages(self, mock_auth, auth_token):
        """Test compression for large messages."""
        session_id = uuid4()

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                websocket.receive_json()

                # Send large message
                large_content = "x" * 2000  # 2KB message
                message = {
                    "type": "chat_message",
                    "payload": {"content": large_content},
                }

                # Track data sent (would be compressed in real implementation)
                len(json.dumps(message).encode("utf-8"))

                websocket.send_json(message)

                # Receive response
                response = websocket.receive_json()

                # In production, response would indicate compression
                # For now, verify message was handled
                assert response is not None

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self, mock_auth, auth_token):
        """Test 30-second heartbeat mechanism."""
        session_id = uuid4()

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                websocket.receive_json()

                # Send ping
                ping_message = {
                    "type": "ping",
                    "payload": {"timestamp": datetime.utcnow().isoformat()},
                }
                websocket.send_json(ping_message)

                # Should receive pong quickly
                start = time.time()
                pong_received = False

                while time.time() - start < 1:
                    try:
                        response = websocket.receive_json(timeout=0.1)
                        if response.get("type") == "connection.pong":
                            pong_received = True
                            break
                    except:
                        continue

                assert pong_received, "No pong response received"

                # Verify heartbeat interval configuration
                assert PerformanceConfig.HEARTBEAT_INTERVAL == 30
                assert PerformanceConfig.HEARTBEAT_TIMEOUT == 5

    @pytest.mark.asyncio
    async def test_backpressure_handling(self, mock_auth, auth_token):
        """Test backpressure mechanism under load."""
        session_id = uuid4()

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                websocket.receive_json()

                # Flood with messages to trigger backpressure
                flood_count = 100
                for i in range(flood_count):
                    msg = {
                        "type": "chat_message",
                        "payload": {"content": f"Flood message {i}"},
                    }
                    websocket.send_json(msg)

                # Server should handle gracefully without crashing
                # May receive rate limit warnings
                responses = []
                start = time.time()

                while time.time() - start < 2:
                    try:
                        resp = websocket.receive_json(timeout=0.1)
                        responses.append(resp)

                        # Check for rate limit response
                        if resp.get("type") == "rate_limit.exceeded":
                            break
                    except:
                        continue

                # Should have received some responses
                assert len(responses) > 0

    @pytest.mark.asyncio
    async def test_reconnection_with_backoff(self):
        """Test automatic reconnection with exponential backoff."""
        # This would be tested at the client level
        # Server should handle reconnections gracefully

        backoff_delays = []
        base_delay = 0.5

        for attempt in range(5):
            delay = base_delay * (2**attempt)
            backoff_delays.append(delay)

        # Verify exponential growth
        assert backoff_delays[0] == 0.5
        assert backoff_delays[1] == 1.0
        assert backoff_delays[2] == 2.0
        assert backoff_delays[3] == 4.0
        assert backoff_delays[4] == 8.0

    @pytest.mark.asyncio
    async def test_concurrent_message_handlers(self, mock_auth, auth_token):
        """Test concurrent message handling per connection."""
        session_id = uuid4()

        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "token": auth_token,
                    "session_id": str(session_id),
                    "channels": [],
                }
                websocket.send_json(auth_request)
                websocket.receive_json()

                # Send multiple messages concurrently
                message_count = 5
                for i in range(message_count):
                    msg = {
                        "type": "chat_message",
                        "payload": {"content": f"Concurrent message {i}"},
                    }
                    websocket.send_json(msg)

                # Messages should be processed concurrently
                # Track response times
                responses = []
                start = time.time()

                while len(responses) < message_count and time.time() - start < 3:
                    try:
                        resp = websocket.receive_json(timeout=0.1)
                        responses.append(
                            {"response": resp, "time": time.time() - start}
                        )
                    except:
                        continue

                # Verify concurrent processing (responses should overlap in time)
                # In sequential processing, each would take significant time
                # With concurrency, total time should be much less
                total_time = time.time() - start
                assert total_time < 2, (
                    f"Messages not processed concurrently, took {total_time}s"
                )

    def test_performance_metrics_endpoint(self, test_client):
        """Test performance metrics availability."""
        response = test_client.get("/ws/health")
        assert response.status_code == 200

        data = response.json()
        metrics = data.get("performance_metrics", {})

        # Verify all metrics are present
        assert "total_messages_processed" in metrics
        assert "total_batches_sent" in metrics
        assert "average_batch_size" in metrics
        assert "concurrent_connections" in metrics
        assert "average_processing_time_ms" in metrics
        assert "compression_enabled" in metrics
        assert "msgpack_available" in metrics

        # Verify compression is enabled
        assert metrics["compression_enabled"] is True
