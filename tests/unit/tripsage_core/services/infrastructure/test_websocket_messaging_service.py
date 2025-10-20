"""Comprehensive tests for TripSage Core WebSocket Messaging Service.

This module provides comprehensive test coverage for WebSocket messaging functionality
including event handling, message routing, connection messaging, user messaging,
session messaging, channel messaging, broadcast messaging, and error handling.
"""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
    WebSocketMessagingService,
)


class TestWebSocketEvent:
    """Test suite for WebSocketEvent model."""

    def test_websocket_event_creation(self):
        """Test WebSocketEvent model creation."""
        event = WebSocketEvent(
            id="event_123",
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Hello World", "user": "alice"},
            metadata={"priority": "high", "encrypted": False},
            timestamp=datetime.now(UTC),
        )

        assert event.id == "event_123"
        assert event.type == WebSocketEventType.CHAT_MESSAGE
        assert event.payload["message"] == "Hello World"
        assert event.metadata["priority"] == "high"
        assert event.timestamp is not None

    def test_websocket_event_auto_id_generation(self):
        """Test automatic ID generation for WebSocketEvent."""
        event = WebSocketEvent(
            type=WebSocketEventType.USER_STATUS, payload={"status": "online"}
        )

        assert event.id is not None
        assert len(event.id) > 0

    def test_websocket_event_auto_timestamp(self):
        """Test automatic timestamp generation."""
        event = WebSocketEvent(type=WebSocketEventType.HEARTBEAT, payload={})

        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    def test_websocket_event_validation(self):
        """Test WebSocketEvent validation."""
        # Test invalid event type
        with pytest.raises(ValidationError):
            WebSocketEvent(
                type="invalid_type",  # Should be WebSocketEventType enum
                payload={},
            )

        # Test empty payload (should be allowed)
        event = WebSocketEvent(type=WebSocketEventType.HEARTBEAT, payload={})
        assert event.payload == {}

    def test_websocket_event_types(self):
        """Test WebSocketEventType enum values."""
        assert WebSocketEventType.CHAT_MESSAGE.value == "chat.message"
        assert WebSocketEventType.USER_STATUS.value == "user.status"
        assert WebSocketEventType.AGENT_STATUS.value == "agent.status"
        assert WebSocketEventType.CHANNEL_JOIN.value == "channel.join"
        assert WebSocketEventType.CHANNEL_LEAVE.value == "channel.leave"
        assert WebSocketEventType.HEARTBEAT.value == "heartbeat"
        assert WebSocketEventType.SYSTEM_ANNOUNCEMENT.value == "system.announcement"
        assert WebSocketEventType.ERROR.value == "error"

    def test_websocket_event_serialization(self):
        """Test WebSocketEvent serialization to dict and JSON."""
        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Test message"},
            metadata={"source": "test"},
        )

        # Test to_dict
        event_dict = event.model_dump()
        assert event_dict["type"] == "chat.message"
        assert event_dict["payload"]["message"] == "Test message"
        assert event_dict["metadata"]["source"] == "test"

        # Test JSON serialization
        event_json = event.model_dump_json()
        parsed = json.loads(event_json)
        assert parsed["type"] == "chat.message"
        assert parsed["payload"]["message"] == "Test message"


class TestWebSocketMessagingService:
    """Test suite for WebSocketMessagingService."""

    @pytest.fixture
    def messaging_service(self):
        """Create WebSocketMessagingService instance."""
        return WebSocketMessagingService()

    @pytest.fixture
    def mock_connection_service(self):
        """Create mock connection service."""
        service = AsyncMock()
        service.get_connection = Mock()
        service.get_connections_by_user = Mock(return_value=[])
        service.get_connections_by_session = Mock(return_value=[])
        service.get_connections_by_channel = Mock(return_value=[])
        service.get_all_connections = Mock(return_value=[])
        return service

    @pytest.fixture
    def mock_broadcaster(self):
        """Create mock broadcaster."""
        broadcaster = AsyncMock()
        broadcaster.broadcast_to_connection = AsyncMock(return_value=True)
        broadcaster.broadcast_to_user = AsyncMock(return_value=True)
        broadcaster.broadcast_to_session = AsyncMock(return_value=True)
        broadcaster.broadcast_to_channel = AsyncMock(return_value=True)
        broadcaster.broadcast_to_all = AsyncMock(return_value=True)
        return broadcaster

    @pytest.fixture
    def setup_messaging_service(
        self, messaging_service, mock_connection_service, mock_broadcaster
    ):
        """Setup messaging service with mocked dependencies."""
        messaging_service.connection_service = mock_connection_service
        messaging_service.broadcaster = mock_broadcaster
        return messaging_service

    @pytest.mark.asyncio
    async def test_send_to_connection_success(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test successful message sending to specific connection."""
        connection_id = "conn_123"

        # Mock connection exists
        mock_connection = AsyncMock()
        mock_connection.send = AsyncMock(return_value=True)
        mock_connection_service.get_connection.return_value = mock_connection

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Hello Connection"},
        )

        result = await setup_messaging_service.send_to_connection(connection_id, event)

        assert result is True
        mock_connection_service.get_connection.assert_called_once_with(connection_id)
        mock_connection.send.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_send_to_connection_not_found(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test sending to non-existent connection."""
        connection_id = "nonexistent_conn"

        # Mock connection not found
        mock_connection_service.get_connection.return_value = None

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Hello"}
        )

        result = await setup_messaging_service.send_to_connection(connection_id, event)

        assert result is False
        mock_connection_service.get_connection.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_send_to_connection_send_failure(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test connection send failure."""
        connection_id = "conn_123"

        # Mock connection exists but send fails
        mock_connection = AsyncMock()
        mock_connection.send = AsyncMock(return_value=False)
        mock_connection_service.get_connection.return_value = mock_connection

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Hello"}
        )

        result = await setup_messaging_service.send_to_connection(connection_id, event)

        assert result is False
        mock_connection.send.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_send_to_user_with_connections(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test sending to user with active connections."""
        user_id = uuid4()

        # Mock user has connections
        mock_conn1 = AsyncMock()
        mock_conn1.send = AsyncMock(return_value=True)
        mock_conn2 = AsyncMock()
        mock_conn2.send = AsyncMock(return_value=True)

        mock_connection_service.get_connections_by_user.return_value = [
            mock_conn1,
            mock_conn2,
        ]

        event = WebSocketEvent(
            type=WebSocketEventType.USER_STATUS, payload={"status": "online"}
        )

        results = await setup_messaging_service.send_to_user(user_id, event)

        assert len(results) == 2
        assert all(results)
        mock_connection_service.get_connections_by_user.assert_called_once_with(user_id)
        mock_conn1.send.assert_called_once_with(event)
        mock_conn2.send.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(
        self, setup_messaging_service, mock_connection_service, mock_broadcaster
    ):
        """Test sending to user with no active connections (uses broadcaster)."""
        user_id = uuid4()

        # Mock user has no connections
        mock_connection_service.get_connections_by_user.return_value = []

        event = WebSocketEvent(
            type=WebSocketEventType.USER_STATUS, payload={"status": "away"}
        )

        results = await setup_messaging_service.send_to_user(user_id, event)

        assert len(results) == 1
        assert results[0] is True
        mock_connection_service.get_connections_by_user.assert_called_once_with(user_id)
        mock_broadcaster.broadcast_to_user.assert_called_once_with(
            user_id, event.model_dump()
        )

    @pytest.mark.asyncio
    async def test_send_to_user_mixed_results(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test sending to user with mixed send results."""
        user_id = uuid4()

        # Mock connections with mixed success
        mock_conn1 = AsyncMock()
        mock_conn1.send = AsyncMock(return_value=True)
        mock_conn2 = AsyncMock()
        mock_conn2.send = AsyncMock(return_value=False)

        mock_connection_service.get_connections_by_user.return_value = [
            mock_conn1,
            mock_conn2,
        ]

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            payload={"message": "Mixed results test"},
        )

        results = await setup_messaging_service.send_to_user(user_id, event)

        assert len(results) == 2
        assert results[0] is True
        assert results[1] is False

    @pytest.mark.asyncio
    async def test_send_to_session_with_connections(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test sending to session with active connections."""
        session_id = uuid4()

        # Mock session has connections
        mock_conn1 = AsyncMock()
        mock_conn1.send = AsyncMock(return_value=True)

        mock_connection_service.get_connections_by_session.return_value = [mock_conn1]

        event = WebSocketEvent(
            type=WebSocketEventType.AGENT_STATUS,
            payload={"agent": "active", "task": "planning"},
        )

        results = await setup_messaging_service.send_to_session(session_id, event)

        assert len(results) == 1
        assert results[0] is True
        mock_connection_service.get_connections_by_session.assert_called_once_with(
            session_id
        )
        mock_conn1.send.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_send_to_session_no_connections(
        self, setup_messaging_service, mock_connection_service, mock_broadcaster
    ):
        """Test sending to session with no active connections."""
        session_id = uuid4()

        # Mock session has no connections
        mock_connection_service.get_connections_by_session.return_value = []

        event = WebSocketEvent(
            type=WebSocketEventType.AGENT_STATUS, payload={"agent": "idle"}
        )

        results = await setup_messaging_service.send_to_session(session_id, event)

        assert len(results) == 1
        assert results[0] is True
        mock_broadcaster.broadcast_to_session.assert_called_once_with(
            session_id, event.model_dump()
        )

    @pytest.mark.asyncio
    async def test_send_to_channel_with_subscribers(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test sending to channel with subscribers."""
        channel = "general"

        # Mock channel has subscribers
        mock_conn1 = AsyncMock()
        mock_conn1.send = AsyncMock(return_value=True)
        mock_conn2 = AsyncMock()
        mock_conn2.send = AsyncMock(return_value=True)

        mock_connection_service.get_connections_by_channel.return_value = [
            mock_conn1,
            mock_conn2,
        ]

        event = WebSocketEvent(
            type=WebSocketEventType.CHANNEL_MESSAGE,
            payload={"message": "Channel announcement", "channel": channel},
        )

        results = await setup_messaging_service.send_to_channel(channel, event)

        assert len(results) == 2
        assert all(results)
        mock_connection_service.get_connections_by_channel.assert_called_once_with(
            channel
        )
        mock_conn1.send.assert_called_once_with(event)
        mock_conn2.send.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_send_to_channel_no_subscribers(
        self, setup_messaging_service, mock_connection_service, mock_broadcaster
    ):
        """Test sending to channel with no subscribers."""
        channel = "empty_channel"

        # Mock channel has no subscribers
        mock_connection_service.get_connections_by_channel.return_value = []

        event = WebSocketEvent(
            type=WebSocketEventType.CHANNEL_MESSAGE,
            payload={"message": "No subscribers"},
        )

        results = await setup_messaging_service.send_to_channel(channel, event)

        assert len(results) == 1
        assert results[0] is True
        mock_broadcaster.broadcast_to_channel.assert_called_once_with(
            channel, event.model_dump()
        )

    @pytest.mark.asyncio
    async def test_broadcast_to_all_connections(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test broadcasting to all connections."""
        # Mock all connections
        mock_conn1 = AsyncMock()
        mock_conn1.send = AsyncMock(return_value=True)
        mock_conn2 = AsyncMock()
        mock_conn2.send = AsyncMock(return_value=True)
        mock_conn3 = AsyncMock()
        mock_conn3.send = AsyncMock(return_value=False)

        mock_connection_service.get_all_connections.return_value = [
            mock_conn1,
            mock_conn2,
            mock_conn3,
        ]

        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_ANNOUNCEMENT,
            payload={"message": "System maintenance in 10 minutes"},
        )

        results = await setup_messaging_service.broadcast_to_all(event)

        assert len(results) == 3
        assert results[0] is True
        assert results[1] is True
        assert results[2] is False
        mock_connection_service.get_all_connections.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_all_no_connections(
        self, setup_messaging_service, mock_connection_service, mock_broadcaster
    ):
        """Test broadcasting when no connections exist."""
        # Mock no connections
        mock_connection_service.get_all_connections.return_value = []

        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_ANNOUNCEMENT,
            payload={"message": "No active connections"},
        )

        results = await setup_messaging_service.broadcast_to_all(event)

        assert len(results) == 1
        assert results[0] is True
        mock_broadcaster.broadcast_to_all.assert_called_once_with(event.model_dump())

    @pytest.mark.asyncio
    async def test_send_error_event(self, setup_messaging_service):
        """Test sending error events."""
        connection_id = "conn_123"
        error_message = "Authentication failed"
        error_code = "AUTH_FAILED"

        with patch.object(
            setup_messaging_service, "send_to_connection", return_value=True
        ) as mock_send:
            result = await setup_messaging_service.send_error(
                connection_id, error_message, error_code
            )

            assert result is True
            mock_send.assert_called_once()

            # Verify error event structure
            call_args = mock_send.call_args
            sent_event = call_args[0][1]  # Second argument is the event

            assert sent_event.type == WebSocketEventType.ERROR
            assert sent_event.payload["message"] == error_message
            assert sent_event.payload["code"] == error_code

    @pytest.mark.asyncio
    async def test_send_heartbeat(self, setup_messaging_service):
        """Test sending heartbeat events."""
        connection_id = "conn_123"

        with patch.object(
            setup_messaging_service, "send_to_connection", return_value=True
        ) as mock_send:
            result = await setup_messaging_service.send_heartbeat(connection_id)

            assert result is True
            mock_send.assert_called_once()

            # Verify heartbeat event
            call_args = mock_send.call_args
            sent_event = call_args[0][1]

            assert sent_event.type == WebSocketEventType.HEARTBEAT
            assert "timestamp" in sent_event.payload

    @pytest.mark.asyncio
    async def test_handle_user_status_change(self, setup_messaging_service):
        """Test handling user status changes."""
        user_id = uuid4()
        status = "away"
        metadata = {"last_seen": "2024-01-15T10:30:00Z"}

        with patch.object(
            setup_messaging_service, "send_to_user", return_value=[True]
        ) as mock_send:
            result = await setup_messaging_service.handle_user_status_change(
                user_id, status, metadata
            )

            assert result == [True]
            mock_send.assert_called_once()

            # Verify status change event
            call_args = mock_send.call_args
            sent_event = call_args[0][1]

            assert sent_event.type == WebSocketEventType.USER_STATUS
            assert sent_event.payload["user_id"] == str(user_id)
            assert sent_event.payload["status"] == status
            assert sent_event.payload["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_handle_agent_status_update(self, setup_messaging_service):
        """Test handling agent status updates."""
        session_id = uuid4()
        agent_status = "processing"
        task_info = {"task_id": "task_123", "progress": 0.75}

        with patch.object(
            setup_messaging_service, "send_to_session", return_value=[True]
        ) as mock_send:
            result = await setup_messaging_service.handle_agent_status_update(
                session_id, agent_status, task_info
            )

            assert result == [True]
            mock_send.assert_called_once()

            # Verify agent status event
            call_args = mock_send.call_args
            sent_event = call_args[0][1]

            assert sent_event.type == WebSocketEventType.AGENT_STATUS
            assert sent_event.payload["session_id"] == str(session_id)
            assert sent_event.payload["status"] == agent_status
            assert sent_event.payload["task_info"] == task_info

    @pytest.mark.asyncio
    async def test_handle_channel_join(self, setup_messaging_service):
        """Test handling channel join events."""
        user_id = uuid4()
        channel = "general"
        connection_id = "conn_123"

        with patch.object(
            setup_messaging_service, "send_to_channel", return_value=[True, True]
        ) as mock_send:
            result = await setup_messaging_service.handle_channel_join(
                user_id, channel, connection_id
            )

            assert result == [True, True]
            mock_send.assert_called_once()

            # Verify channel join event
            call_args = mock_send.call_args
            sent_event = call_args[0][1]

            assert sent_event.type == WebSocketEventType.CHANNEL_JOIN
            assert sent_event.payload["user_id"] == str(user_id)
            assert sent_event.payload["channel"] == channel
            assert sent_event.payload["connection_id"] == connection_id

    @pytest.mark.asyncio
    async def test_handle_channel_leave(self, setup_messaging_service):
        """Test handling channel leave events."""
        user_id = uuid4()
        channel = "notifications"
        connection_id = "conn_456"

        with patch.object(
            setup_messaging_service, "send_to_channel", return_value=[True]
        ) as mock_send:
            result = await setup_messaging_service.handle_channel_leave(
                user_id, channel, connection_id
            )

            assert result == [True]
            mock_send.assert_called_once()

            # Verify channel leave event
            call_args = mock_send.call_args
            sent_event = call_args[0][1]

            assert sent_event.type == WebSocketEventType.CHANNEL_LEAVE
            assert sent_event.payload["user_id"] == str(user_id)
            assert sent_event.payload["channel"] == channel
            assert sent_event.payload["connection_id"] == connection_id

    @pytest.mark.asyncio
    async def test_send_chat_message(self, setup_messaging_service):
        """Test sending chat messages."""
        channel = "general"
        user_id = uuid4()
        message = "Hello everyone!"
        metadata = {"thread_id": "thread_789"}

        with patch.object(
            setup_messaging_service, "send_to_channel", return_value=[True, True]
        ) as mock_send:
            result = await setup_messaging_service.send_chat_message(
                channel, user_id, message, metadata
            )

            assert result == [True, True]
            mock_send.assert_called_once()

            # Verify chat message event
            call_args = mock_send.call_args
            sent_event = call_args[0][1]

            assert sent_event.type == WebSocketEventType.CHAT_MESSAGE
            assert sent_event.payload["channel"] == channel
            assert sent_event.payload["user_id"] == str(user_id)
            assert sent_event.payload["message"] == message
            assert sent_event.payload["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_send_system_announcement(self, setup_messaging_service):
        """Test sending system announcements."""
        message = "System will be down for maintenance"
        severity = "warning"
        scheduled_time = "2024-01-15T22:00:00Z"

        with patch.object(
            setup_messaging_service, "broadcast_to_all", return_value=[True, True, True]
        ) as mock_broadcast:
            result = await setup_messaging_service.send_system_announcement(
                message, severity, scheduled_time
            )

            assert result == [True, True, True]
            mock_broadcast.assert_called_once()

            # Verify system announcement event
            call_args = mock_broadcast.call_args
            sent_event = call_args[0][0]

            assert sent_event.type == WebSocketEventType.SYSTEM_ANNOUNCEMENT
            assert sent_event.payload["message"] == message
            assert sent_event.payload["severity"] == severity
            assert sent_event.payload["scheduled_time"] == scheduled_time

    @pytest.mark.asyncio
    async def test_concurrent_messaging(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test concurrent message sending."""
        # Setup multiple connections
        connections = []
        for _i in range(5):
            mock_conn = AsyncMock()
            mock_conn.send = AsyncMock(return_value=True)
            connections.append(mock_conn)

        mock_connection_service.get_all_connections.return_value = connections

        event = WebSocketEvent(
            type=WebSocketEventType.SYSTEM_ANNOUNCEMENT,
            payload={"message": "Concurrent test"},
        )

        # Send multiple messages concurrently
        tasks = [setup_messaging_service.broadcast_to_all(event) for _ in range(3)]

        results = await asyncio.gather(*tasks)

        # All broadcasts should succeed
        for result in results:
            assert len(result) == 5
            assert all(result)

    @pytest.mark.asyncio
    async def test_message_filtering(self, setup_messaging_service):
        """Test message filtering based on content."""
        # This would test content filtering if implemented

    @pytest.mark.asyncio
    async def test_message_rate_limiting(self, setup_messaging_service):
        """Test message rate limiting functionality."""
        # This would test rate limiting if implemented

    @pytest.mark.asyncio
    async def test_message_encryption(self, setup_messaging_service):
        """Test message encryption for sensitive data."""
        # This would test message encryption if implemented

    @pytest.mark.asyncio
    async def test_message_persistence(self, setup_messaging_service):
        """Test message persistence for offline users."""
        # This would test message queuing/persistence if implemented

    @pytest.mark.asyncio
    async def test_error_handling_in_messaging(
        self, setup_messaging_service, mock_connection_service
    ):
        """Test error handling during message operations."""
        # Mock connection service error
        mock_connection_service.get_connection.side_effect = Exception("Service error")

        event = WebSocketEvent(
            type=WebSocketEventType.CHAT_MESSAGE, payload={"message": "Error test"}
        )

        # Should handle error gracefully
        result = await setup_messaging_service.send_to_connection("conn_123", event)
        assert result is False

    def test_message_validation(self, messaging_service):
        """Test message validation before sending."""
        # Test invalid event type
        with pytest.raises(ValidationError):
            WebSocketEvent(type="invalid_type", payload={})

        # Test missing required fields
        with pytest.raises(ValidationError):
            WebSocketEvent(
                payload={}  # Missing type
            )


@pytest.mark.integration
class TestWebSocketMessagingIntegration:
    """Integration tests for WebSocket messaging functionality."""

    @pytest.mark.asyncio
    async def test_full_messaging_flow(self):
        """Test complete messaging flow with real services."""
        # This would require actual WebSocket connections and services

    @pytest.mark.asyncio
    async def test_messaging_performance_under_load(self):
        """Test messaging performance under high load."""
        # Performance testing for messaging service

    @pytest.mark.asyncio
    async def test_multi_channel_messaging(self):
        """Test messaging across multiple channels simultaneously."""
        # Test complex multi-channel scenarios
