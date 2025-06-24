"""
WebSocket message broadcasting service for TripSage Core.

This module provides message broadcasting capabilities for WebSocket connections,
including Redis/DragonflyDB integration for message persistence and scaling.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
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
            ) from e

    async def stop(self) -> None:
        """Stop the broadcaster service."""
        self._running = False

        # Cancel background tasks
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        if self._subscription_task:
            self._subscription_task.cancel()
            try:
                await self._subscription_task
            except asyncio.CancelledError:
                pass

        # Close Redis connections
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

        logger.info("WebSocket broadcaster stopped")

    async def register_connection(
        self,
        connection_id: str,
        user_id: UUID,
        session_id: UUID | None = None,
        channels: list[str] | None = None,
    ) -> None:
        """Register a WebSocket connection for broadcasting.

        Args:
            connection_id: Unique connection ID
            user_id: User ID
            session_id: Optional session ID
            channels: List of channels to subscribe to
        """
        if not self.redis_client:
            # Store locally if Redis not available
            for channel in channels or []:
                if channel not in self._subscribers:
                    self._subscribers[channel] = set()
                self._subscribers[channel].add(connection_id)
            return

        try:
            # Store connection info in Redis
            connection_data = {
                "user_id": str(user_id),
                "session_id": str(session_id) if session_id else None,
                "channels": channels or [],
                "connected_at": datetime.utcnow().isoformat(),
            }

            await self.redis_client.hset(
                f"{self.CONNECTION_INFO_KEY}:{connection_id}",
                mapping=connection_data,
            )

            # Add to user and session mappings
            await self.redis_client.sadd(
                f"{self.USER_CHANNELS_KEY}:{user_id}", connection_id
            )

            if session_id:
                await self.redis_client.sadd(
                    f"{self.SESSION_CHANNELS_KEY}:{session_id}", connection_id
                )

            # Subscribe to channels
            for channel in channels or []:
                await self.redis_client.sadd(f"channel:{channel}", connection_id)

            logger.info(
                f"Registered connection {connection_id} for user {user_id} with channels: {channels}"
            )

        except Exception as e:
            logger.error(f"Failed to register connection {connection_id}: {e}")

    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister a WebSocket connection.

        Args:
            connection_id: Connection ID to unregister
        """
        if not self.redis_client:
            # Remove from local storage
            for channel_connections in self._subscribers.values():
                channel_connections.discard(connection_id)
            return

        try:
            # Get connection info
            connection_data = await self.redis_client.hgetall(
                f"{self.CONNECTION_INFO_KEY}:{connection_id}"
            )

            if connection_data:
                user_id = connection_data.get("user_id")
                session_id = connection_data.get("session_id")
                channels = json.loads(connection_data.get("channels", "[]"))

                # Remove from user mapping
                if user_id:
                    await self.redis_client.srem(
                        f"{self.USER_CHANNELS_KEY}:{user_id}", connection_id
                    )

                # Remove from session mapping
                if session_id:
                    await self.redis_client.srem(
                        f"{self.SESSION_CHANNELS_KEY}:{session_id}", connection_id
                    )

                # Remove from channel subscriptions
                for channel in channels:
                    await self.redis_client.srem(f"channel:{channel}", connection_id)

            # Remove connection info
            await self.redis_client.delete(
                f"{self.CONNECTION_INFO_KEY}:{connection_id}"
            )

            logger.info(f"Unregistered connection {connection_id}")

        except Exception as e:
            logger.error(f"Failed to unregister connection {connection_id}: {e}")

    async def broadcast_to_channel(
        self, channel: str, event: dict[str, Any], priority: int = 2
    ) -> None:
        """Broadcast message to all connections subscribed to a channel.

        Args:
            channel: Channel name
            event: Event data to broadcast
            priority: Message priority (1=high, 2=medium, 3=low)
        """
        message = BroadcastMessage(
            id=event.get("id", ""),
            event=event,
            target_type="channel",
            target_id=channel,
            created_at=datetime.utcnow(),
            priority=priority,
        )

        await self._queue_broadcast_message(message)

    async def broadcast_to_user(
        self, user_id: UUID, event: dict[str, Any], priority: int = 2
    ) -> None:
        """Broadcast message to all connections for a user.

        Args:
            user_id: User ID
            event: Event data to broadcast
            priority: Message priority (1=high, 2=medium, 3=low)
        """
        message = BroadcastMessage(
            id=event.get("id", ""),
            event=event,
            target_type="user",
            target_id=str(user_id),
            created_at=datetime.utcnow(),
            priority=priority,
        )

        await self._queue_broadcast_message(message)

    async def broadcast_to_session(
        self, session_id: UUID, event: dict[str, Any], priority: int = 2
    ) -> None:
        """Broadcast message to all connections for a session.

        Args:
            session_id: Session ID
            event: Event data to broadcast
            priority: Message priority (1=high, 2=medium, 3=low)
        """
        message = BroadcastMessage(
            id=event.get("id", ""),
            event=event,
            target_type="session",
            target_id=str(session_id),
            created_at=datetime.utcnow(),
            priority=priority,
        )

        await self._queue_broadcast_message(message)

    async def _queue_broadcast_message(self, message: BroadcastMessage) -> None:
        """Queue a broadcast message for processing.

        Args:
            message: Message to queue
        """
        if not self.redis_client:
            logger.warning("Redis not available, cannot queue broadcast message")
            return

        # Check for duplicate messages
        if message.id in self._recent_message_ids:
            logger.debug(f"Skipping duplicate message {message.id}")
            return

        # Track message ID for deduplication
        self._recent_message_ids.add(message.id)
        self._message_id_cleanup_counter += 1

        # Cleanup old message IDs periodically
        if self._message_id_cleanup_counter >= self._max_recent_messages // 2:
            # Keep only the most recent half
            recent_ids = list(self._recent_message_ids)
            self._recent_message_ids = set(
                recent_ids[-self._max_recent_messages // 2 :]
            )
            self._message_id_cleanup_counter = 0

        try:
            # Queue message in Redis with priority
            message_data = message.model_dump_json()
            priority_key = f"{self.BROADCAST_QUEUE_KEY}:priority_{message.priority}"

            await self.redis_client.lpush(priority_key, message_data)

            logger.debug(
                f"Queued broadcast message {message.id} for {message.target_type}:{message.target_id}"
            )

        except Exception as e:
            logger.error(f"Failed to queue broadcast message: {e}")

    async def _process_broadcast_queue(self) -> None:
        """Background task to process queued broadcast messages."""
        while self._running:
            try:
                # Process messages by priority (1=high, 2=medium, 3=low)
                for priority in [1, 2, 3]:
                    priority_key = f"{self.BROADCAST_QUEUE_KEY}:priority_{priority}"

                    # Get message from queue (blocking with timeout)
                    result = await self.redis_client.brpop(priority_key, timeout=1)

                    if result:
                        _, message_data = result
                        message = BroadcastMessage.model_validate_json(message_data)
                        await self._deliver_broadcast_message(message)

                        # Process only one message per iteration to maintain
                        # priority ordering
                        break

            except Exception as e:
                logger.error(f"Error processing broadcast queue: {e}")
                await asyncio.sleep(1)

    async def _deliver_broadcast_message(self, message: BroadcastMessage) -> None:
        """Deliver a broadcast message to the appropriate targets.

        Args:
            message: Message to deliver
        """
        try:
            if message.target_type == "user" and message.target_id:
                # Broadcast to all connections for user
                connection_ids = await self.redis_client.smembers(
                    f"{self.USER_CHANNELS_KEY}:{message.target_id}"
                )
            elif message.target_type == "session" and message.target_id:
                # Broadcast to all connections for session
                connection_ids = await self.redis_client.smembers(
                    f"{self.SESSION_CHANNELS_KEY}:{message.target_id}"
                )
            elif message.target_type == "channel" and message.target_id:
                # Broadcast to all connections subscribed to channel
                connection_ids = await self.redis_client.smembers(
                    f"channel:{message.target_id}"
                )
            else:
                logger.warning(f"Unknown broadcast target: {message.target_type}")
                return

            # Publish to Redis pub/sub for each connection
            for connection_id in connection_ids:
                channel = f"tripsage:websocket:connection:{connection_id}"
                await self.redis_client.publish(channel, message.event)

            logger.debug(
                f"Delivered message {message.id} to {len(connection_ids)} connections"
            )

        except Exception as e:
            logger.error(f"Failed to deliver broadcast message {message.id}: {e}")

    async def _handle_subscriptions(self) -> None:
        """Background task to handle Redis pub/sub subscriptions."""
        if not self.pubsub:
            return

        try:
            # Subscribe to broadcast channels
            await self.pubsub.psubscribe("tripsage:websocket:connection:*")

            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Extract connection ID from channel
                        channel = message["channel"]
                        connection_id = channel.split(":")[-1]

                        # Forward message to local WebSocket manager
                        # This would be handled by the WebSocketManager
                        logger.debug(
                            f"Received broadcast for connection {connection_id}"
                        )

                    except Exception as e:
                        logger.error(f"Error handling subscription message: {e}")

        except Exception as e:
            logger.error(f"Error in subscription handler: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get broadcaster statistics.

        Returns:
            Dictionary with performance metrics
        """
        return {
            "running": self._running,
            "redis_connected": self.redis_client is not None,
            "local_subscribers": sum(len(subs) for subs in self._subscribers.values()),
            "local_channels": len(self._subscribers),
            "recent_message_ids": len(self._recent_message_ids),
        }


# Global WebSocket broadcaster instance
websocket_broadcaster = WebSocketBroadcaster()
