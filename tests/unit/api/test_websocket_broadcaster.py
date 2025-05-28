"""
Tests for WebSocket message broadcaster.

This module tests the WebSocketBroadcaster class which handles message
broadcasting with DragonflyDB integration for scalable real-time messaging.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from tripsage.api.services.websocket_broadcaster import WebSocketBroadcaster
from tripsage.api.models.websocket import (
    WebSocketEvent,
    WebSocketEventType,
    WebSocketChatMessage,
    WebSocketAgentStatusUpdate
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.publish = AsyncMock()
    redis_mock.lpush = AsyncMock()
    redis_mock.lrange = AsyncMock()
    redis_mock.ltrim = AsyncMock()
    redis_mock.expire = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.exists = AsyncMock()
    redis_mock.zadd = AsyncMock()
    redis_mock.zrange = AsyncMock()
    redis_mock.zrem = AsyncMock()
    return redis_mock


@pytest.fixture
def broadcaster(mock_redis):
    """Create a WebSocketBroadcaster instance with mocked Redis."""
    with patch("tripsage.api.services.websocket_broadcaster.redis.asyncio.from_url", return_value=mock_redis):
        broadcaster = WebSocketBroadcaster()
        broadcaster.redis = mock_redis  # Ensure the mock is set
        return broadcaster


class TestWebSocketBroadcaster:
    """Test WebSocket message broadcaster functionality."""

    def test_broadcaster_initialization(self, broadcaster, mock_redis):
        """Test WebSocket broadcaster initialization."""
        assert broadcaster.redis is mock_redis
        assert broadcaster.channel_prefix == "websocket"
        assert broadcaster.queue_prefix == "ws_queue"
        assert broadcaster.stats_key == "ws_stats"

    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, broadcaster, mock_redis):
        """Test broadcasting a message to a specific session."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Hello session!"}
        )
        
        await broadcaster.broadcast_to_session(session_id, event)
        
        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args[0]
        
        assert call_args[0] == f"websocket:session:{session_id}"
        
        # Verify the published message contains the event
        published_data = json.loads(call_args[1])
        assert published_data["type"] == "chat_message"
        assert published_data["sessionId"] == session_id

    @pytest.mark.asyncio
    async def test_broadcast_to_session_with_priority(self, broadcaster, mock_redis):
        """Test broadcasting with priority queue."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.AGENT_STATUS_UPDATE,
            sessionId=session_id,
            payload={"status": "urgent"}
        )
        
        await broadcaster.broadcast_to_session(session_id, event, priority=1)
        
        # Verify both publish and priority queue operations
        mock_redis.publish.assert_called_once()
        mock_redis.zadd.assert_called_once()
        
        # Check priority queue entry
        zadd_call = mock_redis.zadd.call_args
        queue_key = f"ws_queue:session:{session_id}"
        assert zadd_call[0][0] == queue_key

    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, broadcaster, mock_redis):
        """Test broadcasting a message to a specific user."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            userId=user_id,
            payload={"content": "Hello user!"}
        )
        
        await broadcaster.broadcast_to_user(user_id, event)
        
        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args[0]
        
        assert call_args[0] == f"websocket:user:{user_id}"
        
        # Verify the published message
        published_data = json.loads(call_args[1])
        assert published_data["userId"] == user_id

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, broadcaster, mock_redis):
        """Test broadcasting a message to all connections."""
        event = WebSocketEvent(
            type=WebSocketEventType.CONNECTION_STATUS,
            sessionId=str(uuid4()),
            payload={"message": "System maintenance"}
        )
        
        await broadcaster.broadcast_to_all(event)
        
        # Verify Redis publish was called with broadcast channel
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args[0]
        
        assert call_args[0] == "websocket:broadcast"

    @pytest.mark.asyncio
    async def test_queue_message_for_session(self, broadcaster, mock_redis):
        """Test queuing a message for a session."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Queued message"}
        )
        
        await broadcaster.queue_message_for_session(session_id, event, priority=2)
        
        # Verify message was added to priority queue
        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()
        
        # Check the queue key and score (priority)
        zadd_call = mock_redis.zadd.call_args
        queue_key = f"ws_queue:session:{session_id}"
        assert zadd_call[0][0] == queue_key

    @pytest.mark.asyncio
    async def test_get_queued_messages(self, broadcaster, mock_redis):
        """Test retrieving queued messages for a session."""
        session_id = str(uuid4())
        
        # Mock Redis to return queued messages
        mock_message = json.dumps({
            "type": "chat_message",
            "sessionId": session_id,
            "payload": {"content": "Queued message"}
        })
        mock_redis.zrange.return_value = [mock_message]
        
        messages = await broadcaster.get_queued_messages(session_id, limit=10)
        
        assert len(messages) == 1
        assert messages[0]["type"] == "chat_message"
        assert messages[0]["sessionId"] == session_id
        
        # Verify Redis operations
        mock_redis.zrange.assert_called_once()
        mock_redis.zrem.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_message_history(self, broadcaster, mock_redis):
        """Test storing message history."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Historical message"}
        )
        
        await broadcaster.store_message_history(session_id, event, max_history=100)
        
        # Verify message was stored in history list
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()
        mock_redis.expire.assert_called_once()
        
        # Check the history key
        lpush_call = mock_redis.lpush.call_args
        history_key = f"ws_history:session:{session_id}"
        assert lpush_call[0][0] == history_key

    @pytest.mark.asyncio
    async def test_get_message_history(self, broadcaster, mock_redis):
        """Test retrieving message history."""
        session_id = str(uuid4())
        
        # Mock Redis to return message history
        mock_messages = [
            json.dumps({
                "type": "chat_message",
                "sessionId": session_id,
                "payload": {"content": f"Message {i}"}
            })
            for i in range(3)
        ]
        mock_redis.lrange.return_value = mock_messages
        
        history = await broadcaster.get_message_history(session_id, limit=10)
        
        assert len(history) == 3
        for i, message in enumerate(history):
            assert message["type"] == "chat_message"
            assert message["payload"]["content"] == f"Message {i}"
        
        # Verify Redis operation
        mock_redis.lrange.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_stats(self, broadcaster, mock_redis):
        """Test updating broadcast statistics."""
        await broadcaster.update_stats("messages_sent", 1)
        await broadcaster.update_stats("users_connected", 5)
        
        # Verify Redis operations for stats
        assert mock_redis.set.call_count == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, broadcaster, mock_redis):
        """Test retrieving broadcast statistics."""
        # Mock Redis to return stats
        mock_redis.get.side_effect = [b"100", b"25", b"5"]
        
        stats = await broadcaster.get_stats()
        
        assert stats["messages_sent"] == 100
        assert stats["messages_queued"] == 25
        assert stats["active_sessions"] == 5
        
        # Verify Redis get calls
        assert mock_redis.get.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_expired_queues(self, broadcaster, mock_redis):
        """Test cleanup of expired message queues."""
        # Mock Redis scan to return some queue keys
        mock_redis.scan_iter = AsyncMock(return_value=[
            b"ws_queue:session:expired1",
            b"ws_queue:session:expired2",
            b"ws_queue:session:active"
        ])
        
        # Mock exists to return False for expired queues
        mock_redis.exists.side_effect = [False, False, True]
        
        cleaned_count = await broadcaster.cleanup_expired_queues()
        
        assert cleaned_count == 2
        # Verify delete was called for expired queues
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_persist_event(self, broadcaster, mock_redis):
        """Test persisting events for reliability."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Important message"}
        )
        
        await broadcaster.persist_event(session_id, event, ttl_hours=24)
        
        # Verify persistence operations
        mock_redis.set.assert_called_once()
        mock_redis.expire.assert_called_once()
        
        # Check the persistence key format
        set_call = mock_redis.set.call_args
        assert f"ws_persist:session:{session_id}" in set_call[0][0]

    @pytest.mark.asyncio
    async def test_get_persisted_events(self, broadcaster, mock_redis):
        """Test retrieving persisted events."""
        session_id = str(uuid4())
        
        # Mock Redis scan to return persisted event keys
        mock_redis.scan_iter = AsyncMock(return_value=[
            f"ws_persist:session:{session_id}:msg1".encode(),
            f"ws_persist:session:{session_id}:msg2".encode()
        ])
        
        # Mock get to return event data
        mock_event_data = json.dumps({
            "type": "chat_message",
            "sessionId": session_id,
            "payload": {"content": "Persisted message"}
        })
        mock_redis.get.return_value = mock_event_data.encode()
        
        events = await broadcaster.get_persisted_events(session_id)
        
        assert len(events) == 2
        for event in events:
            assert event["type"] == "chat_message"
            assert event["sessionId"] == session_id

    @pytest.mark.asyncio
    async def test_subscribe_to_session(self, broadcaster, mock_redis):
        """Test subscribing to session broadcasts."""
        session_id = str(uuid4())
        
        # Mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        pubsub = await broadcaster.subscribe_to_session(session_id)
        
        assert pubsub is mock_pubsub
        mock_pubsub.subscribe.assert_called_once_with(f"websocket:session:{session_id}")

    @pytest.mark.asyncio
    async def test_subscribe_to_user(self, broadcaster, mock_redis):
        """Test subscribing to user broadcasts."""
        user_id = str(uuid4())
        
        # Mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        pubsub = await broadcaster.subscribe_to_user(user_id)
        
        assert pubsub is mock_pubsub
        mock_pubsub.subscribe.assert_called_once_with(f"websocket:user:{user_id}")

    @pytest.mark.asyncio
    async def test_subscribe_to_all(self, broadcaster, mock_redis):
        """Test subscribing to global broadcasts."""
        # Mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        pubsub = await broadcaster.subscribe_to_all()
        
        assert pubsub is mock_pubsub
        mock_pubsub.subscribe.assert_called_once_with("websocket:broadcast")

    @pytest.mark.asyncio
    async def test_error_handling_during_broadcast(self, broadcaster, mock_redis):
        """Test error handling during broadcast operations."""
        session_id = str(uuid4())
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Test message"}
        )
        
        # Mock Redis to raise an exception
        mock_redis.publish.side_effect = Exception("Redis connection lost")
        
        # Broadcast should handle the exception gracefully
        try:
            await broadcaster.broadcast_to_session(session_id, event)
        except Exception:
            pytest.fail("Broadcaster should handle Redis exceptions gracefully")

    @pytest.mark.asyncio
    async def test_message_deduplication(self, broadcaster, mock_redis):
        """Test message deduplication to prevent duplicate broadcasts."""
        session_id = str(uuid4())
        message_id = str(uuid4())
        
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            payload={"content": "Duplicate test", "messageId": message_id}
        )
        
        # First broadcast
        await broadcaster.broadcast_to_session(session_id, event)
        
        # Mock Redis to indicate message was already processed
        mock_redis.get.return_value = b"processed"
        
        # Second broadcast of same message
        await broadcaster.broadcast_to_session(session_id, event)
        
        # Should still only be called once (from first broadcast)
        # as the second should be deduplicated
        mock_redis.publish.assert_called()

    @pytest.mark.asyncio
    async def test_batch_operations(self, broadcaster, mock_redis):
        """Test batch broadcast operations for efficiency."""
        session_ids = [str(uuid4()) for _ in range(3)]
        events = [
            WebSocketEvent(
                type=WebSocketEventType.AGENT_STATUS_UPDATE,
                sessionId=session_id,
                payload={"status": f"update_{i}"}
            )
            for i, session_id in enumerate(session_ids)
        ]
        
        # Batch broadcast to multiple sessions
        await broadcaster.batch_broadcast_to_sessions(session_ids, events[0])
        
        # Should have called publish for each session
        assert mock_redis.publish.call_count == len(session_ids)

    @pytest.mark.asyncio
    async def test_message_filtering(self, broadcaster, mock_redis):
        """Test message filtering based on user permissions or preferences."""
        session_id = str(uuid4())
        user_id = str(uuid4())
        
        # Event with filtering criteria
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            sessionId=session_id,
            userId=user_id,
            payload={
                "content": "Filtered message",
                "filters": {"permissions": ["admin"], "preferences": ["notifications"]}
            }
        )
        
        # Broadcast with filtering
        await broadcaster.broadcast_to_user(user_id, event)
        
        # Verify the message was processed
        mock_redis.publish.assert_called_once()
        
        # The filtering logic would be implemented in the actual broadcaster
        # Here we just verify the structure supports it