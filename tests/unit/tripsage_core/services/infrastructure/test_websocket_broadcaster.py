"""
Comprehensive tests for TripSage Core WebSocket Broadcaster.

This module provides comprehensive test coverage for WebSocket broadcaster functionality
including message broadcasting, Redis pub/sub integration, priority queuing,
connection management, channel subscriptions, and error handling.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.websocket_broadcaster import (
    BroadcastMessage,
    WebSocketBroadcaster,
)

class TestBroadcastMessage:
    """Test suite for BroadcastMessage model."""

    def test_broadcast_message_creation(self):
        """Test BroadcastMessage model creation."""
        event = {
            "id": "event-123",
            "type": "chat.message",
            "payload": {"message": "Hello World"},
        }

        message = BroadcastMessage(
            id="broadcast-456",
            event=event,
            target_type="user",
            target_id="user-789",
            created_at=datetime.utcnow(),
            priority=1,
        )

        assert message.id == "broadcast-456"
        assert message.event == event
        assert message.target_type == "user"
        assert message.target_id == "user-789"
        assert message.priority == 1
        assert message.expires_at is None

    def test_broadcast_message_with_expiration(self):
        """Test BroadcastMessage with expiration time."""
        expires_at = datetime.utcnow()

        message = BroadcastMessage(
            id="broadcast-456",
            event={"type": "test"},
            target_type="connection",
            target_id="conn-123",
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            priority=2,
        )

        assert message.expires_at == expires_at
        assert message.priority == 2

    def test_broadcast_message_default_priority(self):
        """Test BroadcastMessage with default priority."""
        message = BroadcastMessage(
            id="broadcast-456",
            event={"type": "test"},
            target_type="broadcast",
            created_at=datetime.utcnow(),
        )

        assert message.priority == 1  # Default priority
        assert message.target_id is None

class TestWebSocketBroadcaster:
    """Test suite for WebSocketBroadcaster."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        return settings

    @pytest.fixture
    def mock_redis_client(self):
        """Create a comprehensive mock Redis client."""
        client = AsyncMock()

        # Basic operations
        client.ping = AsyncMock(return_value=True)
        client.close = AsyncMock()

        # Hash operations
        client.hset = AsyncMock(return_value=True)
        client.hgetall = AsyncMock(return_value={})
        client.delete = AsyncMock(return_value=1)

        # Set operations
        client.sadd = AsyncMock(return_value=1)
        client.srem = AsyncMock(return_value=1)
        client.scard = AsyncMock(return_value=0)

        # Sorted set operations
        client.zadd = AsyncMock(return_value=1)
        client.zrange = AsyncMock(return_value=[])
        client.zrem = AsyncMock(return_value=1)

        # Pub/Sub operations
        client.publish = AsyncMock(return_value=1)

        # PubSub object
        pubsub = AsyncMock()
        pubsub.psubscribe = AsyncMock()
        pubsub.close = AsyncMock()
        pubsub.listen = AsyncMock(return_value=iter([]))
        client.pubsub = Mock(return_value=pubsub)

        return client

    @pytest.fixture
    def websocket_broadcaster(self, mock_settings, mock_redis_client):
        """Create a WebSocketBroadcaster instance with mocked dependencies."""
        with (
            patch(
                "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
                return_value=mock_settings,
            ),
            patch("redis.asyncio.from_url", return_value=mock_redis_client),
        ):
            broadcaster = WebSocketBroadcaster()
            broadcaster.redis_client = mock_redis_client
            broadcaster.pubsub = mock_redis_client.pubsub()
            broadcaster._running = True
            return broadcaster

    @pytest.mark.asyncio
    async def test_start_broadcaster_success(self, mock_settings, mock_redis_client):
        """Test successful broadcaster startup."""
        with (
            patch(
                "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
                return_value=mock_settings,
            ),
            patch("redis.asyncio.from_url", return_value=mock_redis_client),
        ):
            broadcaster = WebSocketBroadcaster()

            with (
                patch.object(
                    broadcaster, "_process_broadcast_queue", new_callable=AsyncMock
                ),
                patch.object(
                    broadcaster, "_handle_subscriptions", new_callable=AsyncMock
                ),
            ):
                await broadcaster.start()

                assert broadcaster._running is True
                assert broadcaster.redis_client is not None
                assert broadcaster.pubsub is not None
                mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_broadcaster_without_redis(self, mock_settings):
        """Test broadcaster startup without Redis URL."""
        mock_settings.dragonfly.url = None

        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster()

            await broadcaster.start()

            assert broadcaster._running is True
            assert broadcaster.redis_client is None

    @pytest.mark.asyncio
    async def test_start_broadcaster_connection_failure(
        self, mock_settings, mock_redis_client
    ):
        """Test broadcaster startup with Redis connection failure."""
        mock_redis_client.ping.side_effect = Exception("Connection failed")

        with (
            patch(
                "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
                return_value=mock_settings,
            ),
            patch("redis.asyncio.from_url", return_value=mock_redis_client),
        ):
            broadcaster = WebSocketBroadcaster()

            with pytest.raises(
                CoreServiceError, match="Failed to start WebSocket broadcaster"
            ):
                await broadcaster.start()

    @pytest.mark.asyncio
    async def test_stop_broadcaster(self, websocket_broadcaster):
        """Test stopping the broadcaster."""
        # Mock background tasks
        websocket_broadcaster._broadcast_task = Mock()
        websocket_broadcaster._broadcast_task.cancel = Mock()
        websocket_broadcaster._subscription_task = Mock()
        websocket_broadcaster._subscription_task.cancel = Mock()

        await websocket_broadcaster.stop()

        assert websocket_broadcaster._running is False
        websocket_broadcaster._broadcast_task.cancel.assert_called_once()
        websocket_broadcaster._subscription_task.cancel.assert_called_once()
        websocket_broadcaster.pubsub.close.assert_called_once()
        websocket_broadcaster.redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_connection(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcasting to specific connection."""
        connection_id = "conn-123"
        event = {
            "id": "event-456",
            "type": "chat.message",
            "payload": {"message": "Hello"},
        }

        result = await websocket_broadcaster.broadcast_to_connection(
            connection_id, event, priority=1
        )

        assert result is True
        mock_redis_client.zadd.assert_called_once()

        # Verify message was queued correctly
        call_args = mock_redis_client.zadd.call_args
        queue_key = call_args[0][0]
        message_data = call_args[0][1]

        assert queue_key == websocket_broadcaster.BROADCAST_QUEUE_KEY
        assert len(message_data) == 1

        # Parse the queued message
        message_json = list(message_data.keys())[0]
        message = json.loads(message_json)
        assert message["target_type"] == "connection"
        assert message["target_id"] == connection_id
        assert message["event"] == event
        assert message["priority"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_user(self, websocket_broadcaster, mock_redis_client):
        """Test broadcasting to user."""
        user_id = uuid4()
        event = {
            "id": "event-789",
            "type": "agent.status",
            "payload": {"status": "active"},
        }

        result = await websocket_broadcaster.broadcast_to_user(
            user_id, event, priority=2
        )

        assert result is True
        mock_redis_client.zadd.assert_called_once()

        # Verify message content
        call_args = mock_redis_client.zadd.call_args
        message_json = list(call_args[0][1].keys())[0]
        message = json.loads(message_json)
        assert message["target_type"] == "user"
        assert message["target_id"] == str(user_id)
        assert message["event"] == event
        assert message["priority"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, websocket_broadcaster, mock_redis_client):
        """Test broadcasting to session."""
        session_id = uuid4()
        event = {"id": "event-abc", "type": "chat.typing", "payload": {"typing": True}}

        result = await websocket_broadcaster.broadcast_to_session(session_id, event)

        assert result is True
        mock_redis_client.zadd.assert_called_once()

        # Verify message content
        call_args = mock_redis_client.zadd.call_args
        message_json = list(call_args[0][1].keys())[0]
        message = json.loads(message_json)
        assert message["target_type"] == "session"
        assert message["target_id"] == str(session_id)
        assert message["priority"] == 1  # Default priority

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, websocket_broadcaster, mock_redis_client):
        """Test broadcasting to channel."""
        channel = "general"
        event = {
            "id": "event-def",
            "type": "message.broadcast",
            "payload": {"announcement": "Server maintenance scheduled"},
        }

        result = await websocket_broadcaster.broadcast_to_channel(
            channel, event, priority=3
        )

        assert result is True
        mock_redis_client.zadd.assert_called_once()

        # Verify message content
        call_args = mock_redis_client.zadd.call_args
        message_json = list(call_args[0][1].keys())[0]
        message = json.loads(message_json)
        assert message["target_type"] == "channel"
        assert message["target_id"] == channel
        assert message["priority"] == 3

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, websocket_broadcaster, mock_redis_client):
        """Test broadcasting to all connections."""
        event = {
            "id": "event-ghi",
            "type": "system.announcement",
            "payload": {"message": "System update complete"},
        }

        result = await websocket_broadcaster.broadcast_to_all(event)

        assert result is True
        mock_redis_client.zadd.assert_called_once()

        # Verify message content
        call_args = mock_redis_client.zadd.call_args
        message_json = list(call_args[0][1].keys())[0]
        message = json.loads(message_json)
        assert message["target_type"] == "broadcast"
        assert message["target_id"] is None
        assert message["priority"] == 2  # Default priority for broadcast

    @pytest.mark.asyncio
    async def test_broadcast_without_redis(self, mock_settings):
        """Test broadcasting without Redis connection."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster()
            broadcaster.redis_client = None

            event = {"type": "test"}
            result = await broadcaster.broadcast_to_connection("conn-123", event)

            assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_redis_error(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcasting with Redis error."""
        mock_redis_client.zadd.side_effect = Exception("Redis error")

        event = {"type": "test"}
        result = await websocket_broadcaster.broadcast_to_connection("conn-123", event)

        assert result is False

    @pytest.mark.asyncio
    async def test_register_connection_success(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test successful connection registration."""
        connection_id = "conn-123"
        user_id = uuid4()
        session_id = uuid4()
        channels = ["general", "notifications"]

        await websocket_broadcaster.register_connection(
            connection_id, user_id, session_id, channels
        )

        # Verify connection info was stored
        mock_redis_client.hset.assert_called_once()
        call_args = mock_redis_client.hset.call_args
        assert (
            f"{websocket_broadcaster.CONNECTION_INFO_KEY}:{connection_id}"
            in call_args[0]
        )

        # Verify user and session mappings
        expected_sadd_calls = [
            f"{websocket_broadcaster.USER_CHANNELS_KEY}:{user_id}",
            f"{websocket_broadcaster.SESSION_CHANNELS_KEY}:{session_id}",
        ]
        sadd_calls = [call[0][0] for call in mock_redis_client.sadd.call_args_list]

        for expected_call in expected_sadd_calls:
            assert expected_call in sadd_calls

    @pytest.mark.asyncio
    async def test_register_connection_without_session(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test connection registration without session ID."""
        connection_id = "conn-456"
        user_id = uuid4()

        await websocket_broadcaster.register_connection(connection_id, user_id)

        # Verify connection info was stored
        mock_redis_client.hset.assert_called_once()

        # Verify only user mapping was created (no session)
        sadd_calls = [call[0][0] for call in mock_redis_client.sadd.call_args_list]
        assert any(str(user_id) in call for call in sadd_calls)

    @pytest.mark.asyncio
    async def test_register_connection_without_redis(self, mock_settings):
        """Test connection registration without Redis."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster()
            broadcaster.redis_client = None

            # Should not raise exception
            await broadcaster.register_connection("conn-123", uuid4())

    @pytest.mark.asyncio
    async def test_register_connection_redis_error(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test connection registration with Redis error."""
        mock_redis_client.hset.side_effect = Exception("Redis error")

        # Should not raise exception, just log error
        await websocket_broadcaster.register_connection("conn-123", uuid4())

    @pytest.mark.asyncio
    async def test_unregister_connection_success(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test successful connection unregistration."""
        connection_id = "conn-123"
        user_id = str(uuid4())
        session_id = str(uuid4())

        # Mock connection info
        connection_info = {
            "connection_id": connection_id,
            "user_id": user_id,
            "session_id": session_id,
            "channels": "general,notifications",
        }
        mock_redis_client.hgetall.return_value = connection_info

        await websocket_broadcaster.unregister_connection(connection_id)

        # Verify connection info was retrieved
        mock_redis_client.hgetall.assert_called_once_with(
            f"{websocket_broadcaster.CONNECTION_INFO_KEY}:{connection_id}"
        )

        # Verify removals from user and session mappings
        expected_srem_calls = [
            f"{websocket_broadcaster.USER_CHANNELS_KEY}:{user_id}",
            f"{websocket_broadcaster.SESSION_CHANNELS_KEY}:{session_id}",
        ]
        srem_calls = [call[0][0] for call in mock_redis_client.srem.call_args_list]

        for expected_call in expected_srem_calls:
            assert expected_call in srem_calls

        # Verify connection info was deleted
        mock_redis_client.delete.assert_called_once_with(
            f"{websocket_broadcaster.CONNECTION_INFO_KEY}:{connection_id}"
        )

    @pytest.mark.asyncio
    async def test_unregister_connection_not_found(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test unregistering non-existent connection."""
        mock_redis_client.hgetall.return_value = {}

        # Should not raise exception
        await websocket_broadcaster.unregister_connection("nonexistent-conn")

        mock_redis_client.hgetall.assert_called_once()
        # Should not perform other operations
        mock_redis_client.srem.assert_not_called()
        mock_redis_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_unregister_connection_without_redis(self, mock_settings):
        """Test connection unregistration without Redis."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster()
            broadcaster.redis_client = None

            # Should not raise exception
            await broadcaster.unregister_connection("conn-123")

    @pytest.mark.asyncio
    async def test_subscribe_connection_to_channel(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test subscribing connection to channel."""
        connection_id = "conn-123"
        channel = "test-channel"

        await websocket_broadcaster.subscribe_connection_to_channel(
            connection_id, channel
        )

        # Verify local subscription
        assert channel in websocket_broadcaster._subscribers
        assert connection_id in websocket_broadcaster._subscribers[channel]

        # Verify Redis operation
        mock_redis_client.sadd.assert_called_once_with(
            f"tripsage:websocket:channel:{channel}", connection_id
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_connection_from_channel(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test unsubscribing connection from channel."""
        connection_id = "conn-123"
        channel = "test-channel"

        # Set up initial subscription
        websocket_broadcaster._subscribers[channel] = {connection_id}

        await websocket_broadcaster.unsubscribe_connection_from_channel(
            connection_id, channel
        )

        # Verify local unsubscription
        assert channel not in websocket_broadcaster._subscribers

        # Verify Redis operation
        mock_redis_client.srem.assert_called_once_with(
            f"tripsage:websocket:channel:{channel}", connection_id
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_connection_multiple_subscribers(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test unsubscribing when channel has multiple subscribers."""
        connection_id1 = "conn-123"
        connection_id2 = "conn-456"
        channel = "test-channel"

        # Set up initial subscriptions
        websocket_broadcaster._subscribers[channel] = {connection_id1, connection_id2}

        await websocket_broadcaster.unsubscribe_connection_from_channel(
            connection_id1, channel
        )

        # Verify only one connection was removed, channel still exists
        assert channel in websocket_broadcaster._subscribers
        assert connection_id1 not in websocket_broadcaster._subscribers[channel]
        assert connection_id2 in websocket_broadcaster._subscribers[channel]

    @pytest.mark.asyncio
    async def test_get_connection_count_user(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test getting connection count for user."""
        user_id = str(uuid4())
        mock_redis_client.scard.return_value = 3

        count = await websocket_broadcaster.get_connection_count("user", user_id)

        assert count == 3
        mock_redis_client.scard.assert_called_once_with(
            f"{websocket_broadcaster.USER_CHANNELS_KEY}:{user_id}"
        )

    @pytest.mark.asyncio
    async def test_get_connection_count_session(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test getting connection count for session."""
        session_id = str(uuid4())
        mock_redis_client.scard.return_value = 2

        count = await websocket_broadcaster.get_connection_count("session", session_id)

        assert count == 2
        mock_redis_client.scard.assert_called_once_with(
            f"{websocket_broadcaster.SESSION_CHANNELS_KEY}:{session_id}"
        )

    @pytest.mark.asyncio
    async def test_get_connection_count_channel(self, websocket_broadcaster):
        """Test getting connection count for channel."""
        channel = "test-channel"
        websocket_broadcaster._subscribers[channel] = {"conn1", "conn2", "conn3"}

        count = await websocket_broadcaster.get_connection_count("channel", channel)

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_connection_count_channel_not_found(self, websocket_broadcaster):
        """Test getting connection count for non-existent channel."""
        count = await websocket_broadcaster.get_connection_count(
            "channel", "nonexistent"
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_invalid_type(self, websocket_broadcaster):
        """Test getting connection count for invalid target type."""
        count = await websocket_broadcaster.get_connection_count("invalid", "test")

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_without_redis(self, mock_settings):
        """Test getting connection count without Redis."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster()
            broadcaster.redis_client = None

            count = await broadcaster.get_connection_count("user", "test")

            assert count == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_redis_error(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test getting connection count with Redis error."""
        mock_redis_client.scard.side_effect = Exception("Redis error")

        count = await websocket_broadcaster.get_connection_count("user", "test")

        assert count == 0

    @pytest.mark.skip(
        reason=(
            "Test hangs due to complex async loop - needs refactoring for "
            "proper mocking"
        )
    )
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Explicit timeout for this test
    async def test_process_broadcast_queue_success(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test successful broadcast queue processing."""
        # TODO: Refactor this test to properly mock the async loop and Redis calls
        # The issue is that _process_broadcast_queue has a complex while loop with
        # multiple async Redis operations that are difficult to mock properly.
        # This test should be rewritten to test the functionality without the loop
        # or use a more sophisticated async mocking approach.
        pass

    @pytest.mark.skip(
        reason=(
            "Test hangs due to complex async loop - needs refactoring for "
            "proper mocking"
        )
    )
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Explicit timeout for this test
    async def test_process_broadcast_queue_no_messages(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcast queue processing with no messages."""
        # TODO: Same issue as test_process_broadcast_queue_success
        # Needs proper async mocking strategy
        pass

    @pytest.mark.skip(
        reason=(
            "Test hangs due to complex async loop - needs refactoring for "
            "proper mocking"
        )
    )
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Explicit timeout for this test
    async def test_process_broadcast_queue_invalid_message(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcast queue processing with invalid message."""
        # TODO: Refactor this test to properly mock the async loop and Redis calls
        # Same issue as other _process_broadcast_queue tests - complex while loop
        # that's difficult to mock properly without hanging
        pass

    @pytest.mark.skip(
        reason=(
            "Test hangs due to complex async loop - needs refactoring for "
            "proper mocking"
        )
    )
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Explicit timeout for this test
    async def test_process_broadcast_queue_without_redis(self, mock_settings):
        """Test broadcast queue processing without Redis."""
        # TODO: Same issue as other _process_broadcast_queue tests
        pass

    @pytest.mark.asyncio
    async def test_process_broadcast_message_success(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test successful broadcast message processing."""
        message_data = {
            "target_type": "user",
            "target_id": "user-123",
            "event": {"type": "test", "payload": {"msg": "hello"}},
        }

        await websocket_broadcaster._process_broadcast_message(message_data)

        # Verify Redis publish was called
        mock_redis_client.publish.assert_called_once()

        call_args = mock_redis_client.publish.call_args
        channel_name = call_args[0][0]
        published_data = json.loads(call_args[0][1])

        assert channel_name == "tripsage:websocket:broadcast:user:user-123"
        assert published_data == message_data

    @pytest.mark.asyncio
    async def test_process_broadcast_message_no_target_id(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcast message processing without target ID."""
        message_data = {"target_type": "broadcast", "event": {"type": "test"}}

        await websocket_broadcaster._process_broadcast_message(message_data)

        # Verify Redis publish was called with correct channel
        mock_redis_client.publish.assert_called_once()

        call_args = mock_redis_client.publish.call_args
        channel_name = call_args[0][0]

        assert channel_name == "tripsage:websocket:broadcast:broadcast"

    @pytest.mark.asyncio
    async def test_handle_subscriptions_success(self, websocket_broadcaster):
        """Test successful subscription handling."""
        # Mock pubsub messages
        messages = [
            {
                "type": "pmessage",
                "channel": "tripsage:websocket:broadcast:user:123",
                "data": "test",
            }
        ]

        async def mock_listen():
            for message in messages:
                yield message

        websocket_broadcaster.pubsub.listen = mock_listen

        # Should complete without errors
        await websocket_broadcaster._handle_subscriptions()

        websocket_broadcaster.pubsub.psubscribe.assert_called_once_with(
            "tripsage:websocket:broadcast:*"
        )

    @pytest.mark.asyncio
    async def test_handle_subscriptions_without_pubsub(self, mock_settings):
        """Test subscription handling without pubsub."""
        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster()
            broadcaster.pubsub = None

            # Should complete without errors
            await broadcaster._handle_subscriptions()

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test message priority queue ordering."""
        # Create messages with different priorities
        high_priority_event = {"id": "high", "type": "urgent"}
        low_priority_event = {"id": "low", "type": "normal"}

        # Queue high priority message (priority 1)
        await websocket_broadcaster.broadcast_to_connection(
            "conn1", high_priority_event, priority=1
        )

        # Queue low priority message (priority 3)
        await websocket_broadcaster.broadcast_to_connection(
            "conn2", low_priority_event, priority=3
        )

        # Verify both messages were queued
        assert mock_redis_client.zadd.call_count == 2

        # Verify priority scores (lower score = higher priority)
        calls = mock_redis_client.zadd.call_args_list

        # First message (high priority) should have lower score
        high_priority_score = list(calls[0][0][1].values())[0]
        low_priority_score = list(calls[1][0][1].values())[0]

        assert high_priority_score < low_priority_score

    @pytest.mark.asyncio
    async def test_concurrent_broadcasting(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test concurrent message broadcasting."""
        events = [
            {"id": f"event-{i}", "type": "test", "data": f"message {i}"}
            for i in range(5)
        ]

        # Broadcast messages concurrently
        tasks = [
            websocket_broadcaster.broadcast_to_connection(f"conn-{i}", event)
            for i, event in enumerate(events)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)
        assert mock_redis_client.zadd.call_count == 5

    @pytest.mark.asyncio
    async def test_channel_subscription_management(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test channel subscription management."""
        connection_id = "conn-123"
        channels = ["channel1", "channel2", "channel3"]

        # Subscribe to multiple channels
        for channel in channels:
            await websocket_broadcaster.subscribe_connection_to_channel(
                connection_id, channel
            )

        # Verify local subscriptions
        for channel in channels:
            assert channel in websocket_broadcaster._subscribers
            assert connection_id in websocket_broadcaster._subscribers[channel]

        # Unsubscribe from one channel
        await websocket_broadcaster.unsubscribe_connection_from_channel(
            connection_id, "channel2"
        )

        # Verify partial unsubscription
        assert "channel1" in websocket_broadcaster._subscribers
        assert "channel3" in websocket_broadcaster._subscribers
        assert "channel2" not in websocket_broadcaster._subscribers

    @pytest.mark.skip(
        reason=(
            "Test hangs due to complex async loop - needs refactoring for "
            "proper mocking"
        )
    )
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Explicit timeout for this test
    async def test_error_handling_in_background_tasks(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test error handling in background tasks."""
        # TODO: Same issue as other _process_broadcast_queue tests
        pass

    @pytest.mark.asyncio
    async def test_message_expiration_handling(self, websocket_broadcaster):
        """Test handling of expired messages."""
        now = datetime.utcnow()

        # Create message with expiration
        message = BroadcastMessage(
            id="expired-msg",
            event={"type": "test"},
            target_type="user",
            target_id="user-123",
            created_at=now,
            expires_at=now,  # Already expired
            priority=1,
        )

        # The message structure should support expiration
        assert message.expires_at is not None
        assert message.expires_at <= now

    @pytest.mark.asyncio
    async def test_redis_key_prefixes(self, websocket_broadcaster):
        """Test Redis key prefix constants."""
        assert (
            websocket_broadcaster.BROADCAST_QUEUE_KEY == "tripsage:websocket:broadcast"
        )
        assert websocket_broadcaster.USER_CHANNELS_KEY == "tripsage:websocket:users"
        assert (
            websocket_broadcaster.SESSION_CHANNELS_KEY == "tripsage:websocket:sessions"
        )
        assert (
            websocket_broadcaster.CONNECTION_INFO_KEY
            == "tripsage:websocket:connections"
        )

    @pytest.mark.asyncio
    async def test_custom_redis_url(self, mock_settings):
        """Test broadcaster with custom Redis URL."""
        custom_url = "redis://custom-host:6380/1"

        with patch(
            "tripsage_core.services.infrastructure.websocket_broadcaster.get_settings",
            return_value=mock_settings,
        ):
            broadcaster = WebSocketBroadcaster(redis_url=custom_url)

            assert broadcaster.redis_url == custom_url

    @pytest.mark.asyncio
    async def test_edge_case_empty_event(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcasting with empty event."""
        empty_event = {}

        result = await websocket_broadcaster.broadcast_to_connection(
            "conn-123", empty_event
        )

        assert result is True
        mock_redis_client.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_edge_case_large_payload(
        self, websocket_broadcaster, mock_redis_client
    ):
        """Test broadcasting with large payload."""
        large_event = {
            "id": "large-event",
            "type": "data.transfer",
            "payload": {"data": "x" * 10000},  # 10KB of data
        }

        result = await websocket_broadcaster.broadcast_to_connection(
            "conn-123", large_event
        )

        assert result is True
        mock_redis_client.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscriber_cleanup_edge_cases(self, websocket_broadcaster):
        """Test edge cases in subscriber cleanup."""
        connection_id = "conn-123"

        # Try to unsubscribe from non-existent channel
        await websocket_broadcaster.unsubscribe_connection_from_channel(
            connection_id, "nonexistent"
        )

        # Should not raise exception
        assert "nonexistent" not in websocket_broadcaster._subscribers

    def test_global_broadcaster_instance(self):
        """Test that global broadcaster instance exists."""
        from tripsage_core.services.infrastructure.websocket_broadcaster import (
            websocket_broadcaster,
        )

        assert websocket_broadcaster is not None
        assert isinstance(websocket_broadcaster, WebSocketBroadcaster)
