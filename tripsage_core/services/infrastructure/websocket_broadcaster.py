"""
WebSocket message broadcasting service for TripSage Core.

This module provides message broadcasting capabilities for WebSocket connections,
including Redis/DragonflyDB integration for message persistence and scaling.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import CoreServiceError

logger = logging.getLogger(__name__)

class BroadcastMessage(BaseModel):
    """Message for broadcasting across WebSocket connections."""

    id: str
    event: dict[str, Any]  # Simplified from WebSocketEvent for serialization
    target_type: str  # "connection", "user", "session", "channel", "broadcast"
    target_id: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    priority: int = Field(default=1)  # 1=high, 2=medium, 3=low

class WebSocketBroadcaster:
    """
    WebSocket message broadcaster with Redis/DragonflyDB backend.

    This service provides:
    - Message broadcasting to different target types
    - Priority queue management
    - Redis pub/sub integration
    - Connection registration and tracking
    - Performance monitoring
    """

    def __init__(self, redis_url: str | None = None):
        """Initialize the WebSocket broadcaster.

        Args:
            redis_url: Redis/DragonflyDB connection URL
        """
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.redis_url
        self.redis_client: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self._running = False
        self._subscribers: dict[str, set[str]] = {}  # channel -> connection_ids

        # Message deduplication - track recent message IDs to prevent duplicates
        self._recent_message_ids: set[str] = set()
        self._max_recent_messages = 10000  # Keep track of last 10k message IDs
        self._message_id_cleanup_counter = 0

        # Redis key prefixes
        self.BROADCAST_QUEUE_KEY = "tripsage:websocket:broadcast"
        self.USER_CHANNELS_KEY = "tripsage:websocket:users"
        self.SESSION_CHANNELS_KEY = "tripsage:websocket:sessions"
        self.CONNECTION_INFO_KEY = "tripsage:websocket:connections"

        # Message processing
        self._broadcast_task: asyncio.Task | None = None
        self._subscription_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the broadcaster service."""
        if self._running:
            return

        try:
            # Initialize Redis connection
            if self.redis_url:
                self.redis_client = redis.from_url(
                    self.redis_url, decode_responses=True
                )
                self.pubsub = self.redis_client.pubsub()

                # Test connection
                await self.redis_client.ping()
                logger.info("Connected to Redis/DragonflyDB for WebSocket broadcasting")
            else:
                logger.warning("No Redis URL provided, broadcasting will be local only")

            self._running = True

            # Start background tasks
            if self.redis_client:
                self._broadcast_task = asyncio.create_task(
                    self._process_broadcast_queue()
                )
                self._subscription_task = asyncio.create_task(
                    self._handle_subscriptions()
                )

            logger.info("WebSocket broadcaster started")

        except Exception as e:
            logger.error(f"Failed to start WebSocket broadcaster: {e}")
            raise CoreServiceError(
                message=f"Failed to start WebSocket broadcaster: {str(e)}",
                code="BROADCASTER_START_FAILED",
                service="WebSocketBroadcaster",
                details={"error": str(e)},
            ) from e

    async def stop(self) -> None:
        """Stop the broadcaster service."""
        self._running = False

        # Cancel background tasks
        if self._broadcast_task:
            self._broadcast_task.cancel()
        if self._subscription_task:
            self._subscription_task.cancel()

        # Close Redis connections
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

        logger.info("WebSocket broadcaster stopped")

    def _is_duplicate_message(self, message_id: str) -> bool:
        """Check if message is a duplicate and update tracking.

        Args:
            message_id: Unique message identifier

        Returns:
            True if message is a duplicate, False otherwise
        """
        if message_id in self._recent_message_ids:
            logger.debug(f"Duplicate message detected: {message_id}")
            return True

        # Add to tracking set
        self._recent_message_ids.add(message_id)

        # Cleanup old message IDs periodically to prevent memory growth
        self._message_id_cleanup_counter += 1
        if self._message_id_cleanup_counter >= 1000:  # Every 1000 messages
            if len(self._recent_message_ids) > self._max_recent_messages:
                # Remove oldest half of message IDs (simple cleanup strategy)
                messages_to_remove = len(self._recent_message_ids) - (
                    self._max_recent_messages // 2
                )
                message_list = list(self._recent_message_ids)
                for msg_id in message_list[:messages_to_remove]:
                    self._recent_message_ids.discard(msg_id)
                logger.debug(
                    f"Cleaned up {messages_to_remove} old message IDs from "
                    f"deduplication cache"
                )
            self._message_id_cleanup_counter = 0

        return False

    async def broadcast_to_connection(
        self, connection_id: str, event: dict[str, Any], priority: int = 1
    ) -> bool:
        """Broadcast event to specific connection.

        Args:
            connection_id: Target connection ID
            event: Event to broadcast
            priority: Message priority (1=high, 2=medium, 3=low)

        Returns:
            True if broadcast was queued successfully
        """
        message_id = f"conn_{connection_id}_{event.get('id', '')}"

        # Check for duplicates
        if self._is_duplicate_message(message_id):
            logger.debug(f"Skipping duplicate broadcast to connection {connection_id}")
            return True  # Return True since message was "handled" (by being skipped)

        message = BroadcastMessage(
            id=message_id,
            event=event,
            target_type="connection",
            target_id=connection_id,
            created_at=datetime.utcnow(),
            priority=priority,
        )

        return await self._queue_broadcast_message(message)

    async def broadcast_to_user(
        self, user_id: UUID, event: dict[str, Any], priority: int = 1
    ) -> bool:
        """Broadcast event to all connections for a user.

        Args:
            user_id: Target user ID
            event: Event to broadcast
            priority: Message priority

        Returns:
            True if broadcast was queued successfully
        """
        message_id = f"user_{user_id}_{event.get('id', '')}"

        # Check for duplicates
        if self._is_duplicate_message(message_id):
            logger.debug(f"Skipping duplicate broadcast to user {user_id}")
            return True

        message = BroadcastMessage(
            id=message_id,
            event=event,
            target_type="user",
            target_id=str(user_id),
            created_at=datetime.utcnow(),
            priority=priority,
        )

        return await self._queue_broadcast_message(message)

    async def broadcast_to_session(
        self, session_id: UUID, event: dict[str, Any], priority: int = 1
    ) -> bool:
        """Broadcast event to all connections for a session.

        Args:
            session_id: Target session ID
            event: Event to broadcast
            priority: Message priority

        Returns:
            True if broadcast was queued successfully
        """
        message_id = f"session_{session_id}_{event.get('id', '')}"

        # Check for duplicates
        if self._is_duplicate_message(message_id):
            logger.debug(f"Skipping duplicate broadcast to session {session_id}")
            return True

        message = BroadcastMessage(
            id=message_id,
            event=event,
            target_type="session",
            target_id=str(session_id),
            created_at=datetime.utcnow(),
            priority=priority,
        )

        return await self._queue_broadcast_message(message)

    async def broadcast_to_channel(
        self, channel: str, event: dict[str, Any], priority: int = 1
    ) -> bool:
        """Broadcast event to all connections subscribed to a channel.

        Args:
            channel: Target channel
            event: Event to broadcast
            priority: Message priority

        Returns:
            True if broadcast was queued successfully
        """
        message_id = f"channel_{channel}_{event.get('id', '')}"

        # Check for duplicates
        if self._is_duplicate_message(message_id):
            logger.debug(f"Skipping duplicate broadcast to channel {channel}")
            return True

        message = BroadcastMessage(
            id=message_id,
            event=event,
            target_type="channel",
            target_id=channel,
            created_at=datetime.utcnow(),
            priority=priority,
        )

        return await self._queue_broadcast_message(message)

    async def broadcast_to_all(self, event: dict[str, Any], priority: int = 2) -> bool:
        """Broadcast event to all connections.

        Args:
            event: Event to broadcast
            priority: Message priority

        Returns:
            True if broadcast was queued successfully
        """
        message_id = f"broadcast_{event.get('id', '')}"

        # Check for duplicates
        if self._is_duplicate_message(message_id):
            logger.debug("Skipping duplicate broadcast to all")
            return True

        message = BroadcastMessage(
            id=message_id,
            event=event,
            target_type="broadcast",
            created_at=datetime.utcnow(),
            priority=priority,
        )

        return await self._queue_broadcast_message(message)

    async def register_connection(
        self,
        connection_id: str,
        user_id: UUID,
        session_id: UUID | None = None,
        channels: list[str] | None = None,
    ) -> None:
        """Register a connection for broadcasting.

        Args:
            connection_id: Connection ID
            user_id: User ID
            session_id: Optional session ID
            channels: Optional list of channels to subscribe to
        """
        if not self.redis_client:
            return

        try:
            # Store connection info
            connection_info = {
                "connection_id": connection_id,
                "user_id": str(user_id),
                "session_id": str(session_id) if session_id else None,
                "channels": channels or [],
                "connected_at": datetime.utcnow().isoformat(),
            }

            await self.redis_client.hset(
                f"{self.CONNECTION_INFO_KEY}:{connection_id}",
                mapping=connection_info,
            )

            # Add to user connections
            await self.redis_client.sadd(
                f"{self.USER_CHANNELS_KEY}:{user_id}",
                connection_id,
            )

            # Add to session connections if session_id provided
            if session_id:
                await self.redis_client.sadd(
                    f"{self.SESSION_CHANNELS_KEY}:{session_id}",
                    connection_id,
                )

            # Subscribe to channels
            if channels:
                for channel in channels:
                    await self._subscribe_connection_to_channel(connection_id, channel)

            logger.debug(
                f"Registered WebSocket connection {connection_id} for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to register connection {connection_id}: {e}")

    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister a connection from broadcasting.

        Args:
            connection_id: Connection ID to unregister
        """
        if not self.redis_client:
            return

        try:
            # Get connection info
            connection_info = await self.redis_client.hgetall(
                f"{self.CONNECTION_INFO_KEY}:{connection_id}"
            )

            if not connection_info:
                return

            user_id = connection_info.get("user_id")
            session_id = connection_info.get("session_id")
            channels = (
                connection_info.get("channels", "").split(",")
                if connection_info.get("channels")
                else []
            )

            # Remove from user connections
            if user_id:
                await self.redis_client.srem(
                    f"{self.USER_CHANNELS_KEY}:{user_id}",
                    connection_id,
                )

            # Remove from session connections
            if session_id:
                await self.redis_client.srem(
                    f"{self.SESSION_CHANNELS_KEY}:{session_id}",
                    connection_id,
                )

            # Unsubscribe from channels
            for channel in channels:
                if channel:
                    await self._unsubscribe_connection_from_channel(
                        connection_id, channel
                    )

            # Remove connection info
            await self.redis_client.delete(
                f"{self.CONNECTION_INFO_KEY}:{connection_id}"
            )

            logger.debug(f"Unregistered WebSocket connection {connection_id}")

        except Exception as e:
            logger.error(f"Failed to unregister connection {connection_id}: {e}")

    async def subscribe_connection_to_channel(
        self, connection_id: str, channel: str
    ) -> None:
        """Subscribe a connection to a channel.

        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        await self._subscribe_connection_to_channel(connection_id, channel)

    async def unsubscribe_connection_from_channel(
        self, connection_id: str, channel: str
    ) -> None:
        """Unsubscribe a connection from a channel.

        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        await self._unsubscribe_connection_from_channel(connection_id, channel)

    async def get_connection_count(self, target_type: str, target_id: str) -> int:
        """Get the number of connections for a target.

        Args:
            target_type: Type of target ("user", "session", "channel")
            target_id: Target identifier

        Returns:
            Number of connections
        """
        if not self.redis_client:
            return 0

        try:
            if target_type == "user":
                return await self.redis_client.scard(
                    f"{self.USER_CHANNELS_KEY}:{target_id}"
                )
            elif target_type == "session":
                return await self.redis_client.scard(
                    f"{self.SESSION_CHANNELS_KEY}:{target_id}"
                )
            elif target_type == "channel":
                if target_id in self._subscribers:
                    return len(self._subscribers[target_id])
                return 0
            else:
                return 0

        except Exception as e:
            logger.error(
                f"Failed to get connection count for {target_type}:{target_id}: {e}"
            )
            return 0

    async def _queue_broadcast_message(self, message: BroadcastMessage) -> bool:
        """Queue a broadcast message for processing.

        Args:
            message: Broadcast message to queue

        Returns:
            True if queued successfully
        """
        if not self.redis_client:
            # Fallback to local broadcasting (would need WebSocketManager reference)
            logger.warning("Redis not available, cannot queue broadcast message")
            return False

        try:
            # Serialize message
            message_data = {
                "id": message.id,
                "event": message.event,
                "target_type": message.target_type,
                "target_id": message.target_id,
                "created_at": message.created_at.isoformat(),
                "priority": message.priority,
            }

            # Add to priority queue (lower score = higher priority)
            score = message.priority * 1000 + message.created_at.timestamp()

            await self.redis_client.zadd(
                self.BROADCAST_QUEUE_KEY,
                {json.dumps(message_data): score},
            )

            return True

        except Exception as e:
            logger.error(f"Failed to queue broadcast message: {e}")
            return False

    async def _process_broadcast_queue(self) -> None:
        """Background task to process the broadcast message queue."""
        while self._running:
            try:
                if not self.redis_client:
                    await asyncio.sleep(5)
                    continue

                # Get highest priority messages
                messages = await self.redis_client.zrange(
                    self.BROADCAST_QUEUE_KEY,
                    0,
                    9,  # Process up to 10 messages at a time
                    withscores=True,
                )

                if not messages:
                    await asyncio.sleep(0.1)
                    continue

                # Process messages
                for message_json, _score in messages:
                    try:
                        message_data = json.loads(message_json)
                        await self._process_broadcast_message(message_data)

                        # Remove from queue
                        await self.redis_client.zrem(
                            self.BROADCAST_QUEUE_KEY, message_json
                        )

                    except Exception as e:
                        logger.error(f"Failed to process broadcast message: {e}")
                        # Remove failed message from queue
                        await self.redis_client.zrem(
                            self.BROADCAST_QUEUE_KEY, message_json
                        )

            except Exception as e:
                logger.error(f"Error in broadcast queue processing: {e}")
                await asyncio.sleep(1)

    async def _process_broadcast_message(self, message_data: dict[str, Any]) -> None:
        """Process a single broadcast message.

        Args:
            message_data: Message data dictionary
        """
        try:
            target_type = message_data["target_type"]
            target_id = message_data.get("target_id")
            _event_data = message_data["event"]

            # Publish to Redis channel for the WebSocket manager to pick up
            channel_name = f"tripsage:websocket:broadcast:{target_type}"
            if target_id:
                channel_name += f":{target_id}"

            await self.redis_client.publish(channel_name, json.dumps(message_data))

        except Exception as e:
            logger.error(f"Failed to process broadcast message: {e}")

    async def _handle_subscriptions(self) -> None:
        """Background task to handle Redis pub/sub subscriptions."""
        if not self.pubsub:
            return

        try:
            # Subscribe to broadcast channels
            await self.pubsub.psubscribe("tripsage:websocket:broadcast:*")

            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # This would be handled by the WebSocket manager
                        # when it receives the Redis pub/sub message
                        pass
                    except Exception as e:
                        logger.error(f"Failed to handle subscription message: {e}")

        except Exception as e:
            logger.error(f"Error in subscription handling: {e}")

    async def _subscribe_connection_to_channel(
        self, connection_id: str, channel: str
    ) -> None:
        """Subscribe a connection to a channel.

        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        if channel not in self._subscribers:
            self._subscribers[channel] = set()

        self._subscribers[channel].add(connection_id)

        if self.redis_client:
            try:
                await self.redis_client.sadd(
                    f"tripsage:websocket:channel:{channel}", connection_id
                )
            except Exception as e:
                logger.error(
                    f"Failed to subscribe connection {connection_id} to channel "
                    f"{channel}: {e}"
                )

    async def _unsubscribe_connection_from_channel(
        self, connection_id: str, channel: str
    ) -> None:
        """Unsubscribe a connection from a channel.

        Args:
            connection_id: Connection ID
            channel: Channel name
        """
        if channel in self._subscribers:
            self._subscribers[channel].discard(connection_id)
            if not self._subscribers[channel]:
                del self._subscribers[channel]

        if self.redis_client:
            try:
                await self.redis_client.srem(
                    f"tripsage:websocket:channel:{channel}", connection_id
                )
            except Exception as e:
                logger.error(
                    f"Failed to unsubscribe connection {connection_id} from channel "
                    f"{channel}: {e}"
                )

# Global broadcaster instance
websocket_broadcaster = WebSocketBroadcaster()
