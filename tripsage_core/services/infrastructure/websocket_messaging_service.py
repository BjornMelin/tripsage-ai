"""WebSocket messaging service.

This service consolidates all WebSocket message sending logic including:
- Connection-level messaging
- User-level messaging
- Session-level messaging
- Channel broadcasting
- Rate limiting integration
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .websocket_auth_service import WebSocketAuthService
from .websocket_connection_service import WebSocketConnection


logger = logging.getLogger(__name__)


class WebSocketEvent(BaseModel):
    """WebSocket event model."""

    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: UUID | None = None
    session_id: UUID | None = None
    connection_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, description="1=high, 2=medium, 3=low")
    retry_count: int = Field(default=0)
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to serializable dictionary for WebSocket transmission.

        Centralized JSON serialization logic to address code review comment.
        """
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "connection_id": self.connection_id,
            "payload": self.payload,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class WebSocketEventType:
    """WebSocket event type constants."""

    # Connection events
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_AUTHENTICATED = "connection.authenticated"
    CONNECTION_ERROR = "connection.error"
    CONNECTION_CLOSED = "connection.closed"
    CONNECTION_HEARTBEAT = "connection.heartbeat"
    CONNECTION_PONG = "connection.pong"
    CONNECTION_RECONNECTING = "connection.reconnecting"
    CONNECTION_RECOVERED = "connection.recovered"

    # Message events
    MESSAGE_SENT = "message.sent"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_BROADCAST = "message.broadcast"
    MESSAGE_FAILED = "message.failed"

    # Subscription events
    SUBSCRIPTION_ADDED = "subscription.added"
    SUBSCRIPTION_REMOVED = "subscription.removed"

    # Chat events
    CHAT_MESSAGE = "chat.message"
    CHAT_MESSAGE_COMPLETE = "chat.message_complete"
    CHAT_TYPING = "chat.typing"
    CHAT_TYPING_START = "chat.typing_start"
    CHAT_TYPING_STOP = "chat.typing_stop"
    CHAT_STATUS = "chat.status"

    # Agent events
    AGENT_STATUS = "agent.status"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"

    # Rate limiting events
    RATE_LIMIT_WARNING = "rate_limit.warning"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


class WebSocketMessagingService:
    """Service for consolidating WebSocket messaging operations."""

    def __init__(self, auth_service: WebSocketAuthService):
        """Initialize WebSocket messaging service."""
        self.auth_service = auth_service

        # Connection tracking
        self.connections: dict[str, WebSocketConnection] = {}
        self.user_connections: dict[UUID, set[str]] = {}
        self.session_connections: dict[UUID, set[str]] = {}
        self.channel_connections: dict[str, set[str]] = {}

        # Performance metrics
        self.performance_metrics = {
            "total_messages_sent": 0,
            "total_bytes_sent": 0,
            "rate_limit_hits": 0,
        }

    def register_connection(self, connection: WebSocketConnection) -> None:
        """Register a connection for messaging."""
        connection_id = connection.connection_id
        self.connections[connection_id] = connection

        # Track by user
        if connection.user_id:
            if connection.user_id not in self.user_connections:
                self.user_connections[connection.user_id] = set()
            self.user_connections[connection.user_id].add(connection_id)

        # Track by session
        if connection.session_id:
            if connection.session_id not in self.session_connections:
                self.session_connections[connection.session_id] = set()
            self.session_connections[connection.session_id].add(connection_id)

    def unregister_connection(self, connection_id: str) -> None:
        """Unregister a connection from messaging."""
        connection = self.connections.pop(connection_id, None)
        if not connection:
            return

        # Remove from user connections
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]

        # Remove from session connections
        if connection.session_id and connection.session_id in self.session_connections:
            self.session_connections[connection.session_id].discard(connection_id)
            if not self.session_connections[connection.session_id]:
                del self.session_connections[connection.session_id]

        # Remove from channels
        for channel in connection.subscribed_channels:
            if channel in self.channel_connections:
                self.channel_connections[channel].discard(connection_id)
                if not self.channel_connections[channel]:
                    del self.channel_connections[channel]

    def subscribe_to_channel(self, connection_id: str, channel: str) -> bool:
        """Subscribe connection to a channel."""
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        connection.subscribe_to_channel(channel)

        if channel not in self.channel_connections:
            self.channel_connections[channel] = set()
        self.channel_connections[channel].add(connection_id)

        return True

    def unsubscribe_from_channel(self, connection_id: str, channel: str) -> bool:
        """Unsubscribe connection from a channel."""
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        connection.unsubscribe_from_channel(channel)

        if channel in self.channel_connections:
            self.channel_connections[channel].discard(connection_id)
            if not self.channel_connections[channel]:
                del self.channel_connections[channel]

        return True

    async def send_to_connection(
        self,
        connection_id: str,
        event: WebSocketEvent,
        rate_limiter=None,
        message_limits=None,
    ) -> bool:
        """Send event to specific connection with rate limiting and size validation.

        Consolidated send logic to address code review comment about duplicate
        send_to_* logic.
        """
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        # Check message rate limit if rate limiter is provided
        if rate_limiter and connection.user_id:
            rate_check = await rate_limiter.check_message_rate(
                connection.user_id, connection_id
            )
            if not rate_check["allowed"]:
                self.performance_metrics["rate_limit_hits"] += 1

                # Send rate limit warning
                warning_event = {
                    "id": f"rate_limit_{connection_id}",
                    "type": WebSocketEventType.RATE_LIMIT_EXCEEDED,
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "reason": rate_check["reason"],
                        "retry_after": 60,  # Default window
                    },
                }
                # Send warning without rate limiting and size validation to
                # avoid recursion
                await connection.send(warning_event)
                return False

        # Convert event to dict for sending using centralized serialization
        event_dict = event.to_dict()

        success = await connection.send(event_dict, message_limits)
        if success:
            self.performance_metrics["total_messages_sent"] += 1

        return success

    async def send_to_user(
        self,
        user_id: UUID,
        event: WebSocketEvent,
        rate_limiter=None,
        message_limits=None,
    ) -> int:
        """Send event to all connections for a user.

        Consolidated logic for user messaging.
        """
        connection_ids = self.user_connections.get(user_id, set())
        sent_count = 0

        for connection_id in connection_ids.copy():
            if await self.send_to_connection(
                connection_id, event, rate_limiter, message_limits
            ):
                sent_count += 1

        return sent_count

    async def send_to_session(
        self,
        session_id: UUID,
        event: WebSocketEvent,
        rate_limiter=None,
        message_limits=None,
    ) -> int:
        """Send event to all connections for a session.

        Consolidated logic for session messaging.
        """
        connection_ids = self.session_connections.get(session_id, set())
        sent_count = 0

        for connection_id in connection_ids.copy():
            if await self.send_to_connection(
                connection_id, event, rate_limiter, message_limits
            ):
                sent_count += 1

        return sent_count

    async def send_to_channel(
        self,
        channel: str,
        event: WebSocketEvent,
        rate_limiter=None,
        message_limits=None,
    ) -> int:
        """Send event to all connections subscribed to a channel.

        Consolidated logic for channel messaging.
        """
        connection_ids = self.channel_connections.get(channel, set())
        sent_count = 0

        for connection_id in connection_ids.copy():
            if await self.send_to_connection(
                connection_id, event, rate_limiter, message_limits
            ):
                sent_count += 1

        return sent_count

    async def broadcast_to_all(
        self, event: WebSocketEvent, rate_limiter=None, message_limits=None
    ) -> int:
        """Broadcast event to all connections.

        Consolidated logic for broadcasting.
        """
        sent_count = 0

        for connection_id in list(self.connections.keys()):
            if await self.send_to_connection(
                connection_id, event, rate_limiter, message_limits
            ):
                sent_count += 1

        return sent_count

    async def send_by_target(
        self,
        target_type: str,
        target_id: str | None,
        event: WebSocketEvent,
        rate_limiter=None,
        message_limits=None,
    ) -> int:
        """Send message by target type and ID.

        Unified sending method that routes to appropriate send_to_* method.
        """
        if target_type == "connection" and target_id:
            success = await self.send_to_connection(
                target_id, event, rate_limiter, message_limits
            )
            return 1 if success else 0
        if target_type == "user" and target_id:
            return await self.send_to_user(
                UUID(target_id), event, rate_limiter, message_limits
            )
        if target_type == "session" and target_id:
            return await self.send_to_session(
                UUID(target_id), event, rate_limiter, message_limits
            )
        if target_type == "channel" and target_id:
            return await self.send_to_channel(
                target_id, event, rate_limiter, message_limits
            )
        if target_type == "broadcast":
            return await self.broadcast_to_all(event, rate_limiter, message_limits)
        logger.warning("Unknown target type: %s", target_type)
        return 0

    def get_connection_stats(self) -> dict[str, Any]:
        """Get messaging statistics."""
        total_queued = sum(
            len(conn.message_queue) + sum(len(q) for q in conn.priority_queue.values())
            for conn in self.connections.values()
        )

        health_distribution = {"excellent": 0, "good": 0, "poor": 0, "critical": 0}
        for conn in self.connections.values():
            health = conn.get_health()
            health_distribution[health.quality] += 1

        return {
            "total_connections": len(self.connections),
            "unique_users": len(self.user_connections),
            "active_sessions": len(self.session_connections),
            "subscribed_channels": len(self.channel_connections),
            "total_queued_messages": total_queued,
            "health_distribution": health_distribution,
            "performance_metrics": self.performance_metrics,
        }
