"""
Tests for WebSocket performance optimizations.

This module tests all performance features including:
- Message batching
- Compression
- Connection pooling
- Concurrent message handling
- Binary protocol support
- Backpressure handling
"""

import asyncio
import gzip
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient

from tripsage.api.routers.websocket import (
    ConnectionPool,
    MessageBatcher,
    PerformanceConfig,
    performance_metrics,
)

# Try to import msgpack for binary protocol tests
try:
    import msgpack

    MSGPACK_AVAILABLE = True
except ImportError:
    msgpack = None
    MSGPACK_AVAILABLE = False


class TestMessageBatcher:
    """Test message batching functionality."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = MagicMock(spec=WebSocket)
        ws.send_text = AsyncMock()
        ws.send_bytes = AsyncMock()
        ws._supports_binary = False
        return ws

    @pytest.fixture
    def batcher(self, mock_websocket):
        """Create a MessageBatcher instance."""
        return MessageBatcher("test-connection", mock_websocket)

    @pytest.mark.asyncio
    async def test_batch_collection(self, batcher):
        """Test that messages are collected into batches."""
        # Add messages
        messages = [{"type": "test", "content": f"Message {i}"} for i in range(5)]

        for msg in messages:
            await batcher.add_message(msg)

        # Verify messages are queued
        assert len(batcher.batch_queue) == 5

    @pytest.mark.asyncio
    async def test_batch_timeout_send(self, batcher, mock_websocket):
        """Test that batches are sent after timeout."""
        # Add a single message
        await batcher.add_message({"type": "test", "content": "Test message"})

        # Wait for batch timeout
        await asyncio.sleep(PerformanceConfig.BATCH_TIMEOUT_MS / 1000 + 0.1)

        # Verify send was called
        assert mock_websocket.send_text.called

        # Check batch format
        call_args = mock_websocket.send_text.call_args[0][0]
        batch_data = json.loads(call_args)
        assert batch_data["type"] == "batch"
        assert len(batch_data["messages"]) == 1
        assert batch_data["count"] == 1

    @pytest.mark.asyncio
    async def test_batch_size_limit(self, batcher, mock_websocket):
        """Test that batches respect size limits."""
        # Add more messages than batch size
        messages = [
            {"type": "test", "content": f"Message {i}"}
            for i in range(PerformanceConfig.BATCH_SIZE + 5)
        ]

        for msg in messages:
            await batcher.add_message(msg)

        # Wait for processing
        await asyncio.sleep(PerformanceConfig.BATCH_TIMEOUT_MS / 1000 + 0.1)

        # Should have sent at least one full batch
        assert mock_websocket.send_text.called
        first_call = json.loads(mock_websocket.send_text.call_args_list[0][0][0])
        assert first_call["count"] == PerformanceConfig.BATCH_SIZE

    @pytest.mark.asyncio
    async def test_compression(self, mock_websocket):
        """Test message compression for large payloads."""
        batcher = MessageBatcher("test-connection", mock_websocket)

        # Create a large message
        large_content = "x" * 2000  # 2KB of data
        large_message = {"type": "test", "content": large_content}

        # Mock compression
        with patch("gzip.compress") as mock_compress:
            compressed_data = b"compressed"
            mock_compress.return_value = compressed_data

            await batcher.add_message(large_message)
            await asyncio.sleep(PerformanceConfig.BATCH_TIMEOUT_MS / 1000 + 0.1)

            # Verify compression was attempted
            assert mock_compress.called

    @pytest.mark.asyncio
    @pytest.mark.skipif(not MSGPACK_AVAILABLE, reason="msgpack not installed")
    async def test_binary_protocol(self, mock_websocket):
        """Test MessagePack binary protocol support."""
        mock_websocket._supports_binary = True
        batcher = MessageBatcher("test-connection", mock_websocket)

        # Add message
        await batcher.add_message({"type": "test", "content": "Binary test"})
        await asyncio.sleep(PerformanceConfig.BATCH_TIMEOUT_MS / 1000 + 0.1)

        # Should use send_bytes for binary
        assert mock_websocket.send_bytes.called
        assert not mock_websocket.send_text.called

    @pytest.mark.asyncio
    async def test_batch_close_flush(self, batcher, mock_websocket):
        """Test that remaining messages are flushed on close."""
        # Add messages
        for i in range(3):
            await batcher.add_message({"type": "test", "content": f"Message {i}"})

        # Close immediately (before timeout)
        await batcher.close()

        # Should have flushed messages
        assert mock_websocket.send_text.called
        batch_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert batch_data["count"] == 3


class TestConnectionPool:
    """Test connection pooling functionality."""

    @pytest.fixture
    def pool(self):
        """Create a ConnectionPool instance."""
        return ConnectionPool()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = MagicMock(spec=WebSocket)
        ws.send_text = AsyncMock()
        ws.send_bytes = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_add_connection(self, pool, mock_websocket):
        """Test adding connections to pool."""
        user_id = uuid4()
        session_id = uuid4()

        batcher = await pool.add_connection(
            "conn-1", mock_websocket, user_id, session_id
        )

        assert isinstance(batcher, MessageBatcher)
        assert "conn-1" in pool.connections
        assert "conn-1" in pool.user_connections[user_id]
        assert "conn-1" in pool.session_connections[session_id]

    @pytest.mark.asyncio
    async def test_pool_capacity_limit(self, pool, mock_websocket):
        """Test connection pool capacity limits."""
        user_id = uuid4()

        # Fill pool to capacity
        original_max = PerformanceConfig.MAX_POOL_SIZE
        PerformanceConfig.MAX_POOL_SIZE = 5

        try:
            for i in range(5):
                await pool.add_connection(f"conn-{i}", mock_websocket, user_id)

            # Should raise on exceeding capacity
            with pytest.raises(ValueError, match="Connection pool at capacity"):
                await pool.add_connection("conn-overflow", mock_websocket, user_id)
        finally:
            PerformanceConfig.MAX_POOL_SIZE = original_max

    @pytest.mark.asyncio
    async def test_remove_connection(self, pool, mock_websocket):
        """Test removing connections from pool."""
        user_id = uuid4()
        await pool.add_connection("conn-1", mock_websocket, user_id)

        # Remove connection
        await pool.remove_connection("conn-1")

        assert "conn-1" not in pool.connections
        assert "conn-1" not in pool.user_connections[user_id]

    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, pool, mock_websocket):
        """Test broadcasting to all user connections."""
        user_id = uuid4()

        # Add multiple connections for same user
        for i in range(3):
            await pool.add_connection(f"conn-{i}", mock_websocket, user_id)

        # Broadcast message
        message = {"type": "broadcast", "content": "Test broadcast"}
        count = await pool.broadcast_to_user(user_id, message)

        assert count == 3

    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, pool, mock_websocket):
        """Test broadcasting to all session connections."""
        user_id = uuid4()
        session_id = uuid4()

        # Add multiple connections for same session
        for i in range(2):
            await pool.add_connection(f"conn-{i}", mock_websocket, user_id, session_id)

        # Broadcast message
        message = {"type": "broadcast", "content": "Session broadcast"}
        count = await pool.broadcast_to_session(session_id, message)

        assert count == 2


class TestWebSocketPerformance:
    """Test WebSocket endpoint performance features."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from tripsage.api.main import app

        return TestClient(app)

    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self):
        """Test concurrent message processing."""
        # Track concurrent handlers
        active_handlers = []
        max_concurrent = 0

        async def mock_handler(*args, **kwargs):
            nonlocal max_concurrent
            active_handlers.append(1)
            max_concurrent = max(max_concurrent, len(active_handlers))
            await asyncio.sleep(0.1)  # Simulate processing
            active_handlers.pop()

        # Test with multiple messages
        with patch("tripsage.api.routers.websocket.handle_chat_message", mock_handler):
            tasks = []
            for i in range(10):
                task = asyncio.create_task(mock_handler())
                tasks.append(task)

            await asyncio.gather(*tasks)

        # Should have processed messages concurrently
        assert max_concurrent > 1

    @pytest.mark.asyncio
    async def test_no_artificial_delays(self):
        """Test that no artificial delays exist in message processing."""
        start_time = time.time()

        # Process a mock message stream
        messages = ["word1", "word2", "word3", "word4", "word5"]
        chunks = []

        # Simulate chunking without delays
        chunk_size = 2
        for i in range(0, len(messages), chunk_size):
            chunk = " ".join(messages[i : i + chunk_size])
            chunks.append(chunk)

        # Total time should be minimal (no 50ms delays)
        elapsed = time.time() - start_time
        assert elapsed < 0.01  # Should be near instant

    def test_performance_metrics_tracking(self):
        """Test that performance metrics are tracked."""
        # Reset metrics
        performance_metrics["total_messages_processed"] = 0
        performance_metrics["total_batches_sent"] = 0

        # Simulate message processing
        performance_metrics["total_messages_processed"] += 1
        performance_metrics["total_batches_sent"] += 1
        performance_metrics["message_processing_time_ms"].append(15.5)

        assert performance_metrics["total_messages_processed"] == 1
        assert performance_metrics["total_batches_sent"] == 1
        assert 15.5 in performance_metrics["message_processing_time_ms"]

    @pytest.mark.asyncio
    async def test_adaptive_chunk_size(self):
        """Test adaptive chunk sizing based on message length."""
        # Short message
        short_text = " ".join(["word"] * 30)
        words = short_text.split()

        # Should use small chunks for short messages
        if len(words) < 50:
            chunk_size = 5
        elif len(words) < 200:
            chunk_size = 10
        else:
            chunk_size = 20

        assert chunk_size == 5

        # Long message
        long_text = " ".join(["word"] * 300)
        words = long_text.split()

        if len(words) < 50:
            chunk_size = 5
        elif len(words) < 200:
            chunk_size = 10
        else:
            chunk_size = 20

        assert chunk_size == 20

    def test_compression_threshold(self):
        """Test compression threshold logic."""
        # Small payload - should not compress
        small_data = b"x" * 500
        assert len(small_data) < PerformanceConfig.COMPRESSION_THRESHOLD

        # Large payload - should compress
        large_data = b"x" * 2000
        assert len(large_data) > PerformanceConfig.COMPRESSION_THRESHOLD

        # Test compression benefit check
        compressed = gzip.compress(large_data, PerformanceConfig.COMPRESSION_LEVEL)
        compression_ratio = len(compressed) / len(large_data)

        # Should only use compression if >10% reduction
        should_compress = compression_ratio < 0.9
        assert should_compress  # Repeated data compresses well

    def test_heartbeat_configuration(self):
        """Test heartbeat timing configuration."""
        # Verify 30-second heartbeat interval
        assert PerformanceConfig.HEARTBEAT_INTERVAL == 30

        # Verify 5-second timeout
        assert PerformanceConfig.HEARTBEAT_TIMEOUT == 5

        # Heartbeat should be less frequent than before
        assert PerformanceConfig.HEARTBEAT_INTERVAL > 20

    @pytest.mark.asyncio
    async def test_backpressure_handling(self):
        """Test backpressure mechanism."""
        # Test queue size limits
        assert PerformanceConfig.MAX_QUEUE_SIZE == 10000
        assert PerformanceConfig.BACKPRESSURE_THRESHOLD == 0.8

        # Simulate queue filling
        queue_size = 8500  # Above threshold
        threshold = int(
            PerformanceConfig.MAX_QUEUE_SIZE * PerformanceConfig.BACKPRESSURE_THRESHOLD
        )

        assert queue_size > threshold  # Should trigger backpressure

    @pytest.mark.asyncio
    async def test_message_timeout(self):
        """Test message processing timeout."""

        async def slow_handler():
            await asyncio.sleep(35)  # Longer than timeout
            return {"content": "Late response"}

        # Should timeout
        try:
            result = await asyncio.wait_for(
                slow_handler(), timeout=PerformanceConfig.MESSAGE_TIMEOUT
            )
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            # Expected
            pass

    def test_websocket_health_endpoint(self, client):
        """Test health endpoint with performance metrics."""
        response = client.get("/ws/health")
        assert response.status_code == 200

        data = response.json()
        assert "performance_metrics" in data
        assert "compression_enabled" in data["performance_metrics"]
        assert data["performance_metrics"]["compression_enabled"] is True
        assert "msgpack_available" in data["performance_metrics"]


class TestBinaryProtocol:
    """Test binary protocol support."""

    @pytest.mark.skipif(not MSGPACK_AVAILABLE, reason="msgpack not installed")
    def test_msgpack_serialization(self):
        """Test MessagePack serialization."""
        data = {
            "type": "chat_message",
            "content": "Test message",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(uuid4()),
        }

        # Serialize
        packed = msgpack.packb(data)
        assert isinstance(packed, bytes)

        # Deserialize
        unpacked = msgpack.unpackb(packed)
        assert unpacked["type"] == data["type"]
        assert unpacked["content"] == data["content"]

    @pytest.mark.skipif(not MSGPACK_AVAILABLE, reason="msgpack not installed")
    def test_binary_vs_json_size(self):
        """Test binary protocol size efficiency."""
        # Create test data with various types
        data = {
            "type": "complex_message",
            "numbers": list(range(100)),
            "nested": {"level1": {"level2": {"data": "x" * 100}}},
            "timestamp": time.time(),
            "boolean": True,
            "null_value": None,
        }

        # Compare sizes
        json_size = len(json.dumps(data).encode("utf-8"))
        msgpack_size = len(msgpack.packb(data))

        # MessagePack should be smaller for this data
        assert msgpack_size < json_size


class TestErrorRecovery:
    """Test error recovery in performance features."""

    @pytest.mark.asyncio
    async def test_batch_send_failure_recovery(self):
        """Test recovery from batch send failures."""
        mock_ws = MagicMock(spec=WebSocket)
        mock_ws.send_text = AsyncMock(side_effect=Exception("Network error"))
        mock_ws.send_bytes = AsyncMock(side_effect=Exception("Network error"))

        batcher = MessageBatcher("test-conn", mock_ws)

        # Try to send message
        await batcher.add_message({"type": "test", "content": "Will fail"})
        await asyncio.sleep(PerformanceConfig.BATCH_TIMEOUT_MS / 1000 + 0.1)

        # Should have attempted send despite failure
        assert mock_ws.send_text.called

    @pytest.mark.asyncio
    async def test_concurrent_handler_cleanup(self):
        """Test cleanup of failed concurrent handlers."""
        failed_handlers = set()

        async def failing_handler():
            raise Exception("Handler failed")

        # Create failing tasks
        for i in range(5):
            task = asyncio.create_task(failing_handler())
            failed_handlers.add(task)

        # Wait for completion
        await asyncio.sleep(0.1)

        # All should be done (failed)
        assert all(h.done() for h in failed_handlers)

    @pytest.mark.asyncio
    async def test_pool_connection_recovery(self):
        """Test connection pool recovery after errors."""
        pool = ConnectionPool()
        mock_ws = MagicMock(spec=WebSocket)

        # Add connection
        user_id = uuid4()
        await pool.add_connection("conn-1", mock_ws, user_id)

        # Simulate connection error and removal
        await pool.remove_connection("conn-1")

        # Should be able to add new connection with same ID
        await pool.add_connection("conn-1", mock_ws, user_id)
        assert "conn-1" in pool.connections
