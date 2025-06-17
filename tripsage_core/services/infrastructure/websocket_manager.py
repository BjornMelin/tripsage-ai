"""
WebSocket connection manager with integrated broadcasting and error recovery.

This module provides comprehensive WebSocket connection management including:
- Integration with Redis-backed broadcasting
- Automatic error recovery with exponential backoff
- 20-second heartbeat/keepalive mechanism
- Connection state management and monitoring
- Rate limiting and throttling
- Circuit breaker patterns for fault tolerance

This refactored version extracts responsibilities into focused services.
"""

import asyncio
import json
import logging
import random
import time
from collections import defaultdict, deque
from datetime import datetime
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set
from uuid import UUID, uuid4

import redis.asyncio as redis
from fastapi import WebSocket
from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import CoreServiceError
from .websocket_connection_service import (
    WebSocketConnectionService, 
    WebSocketConnection,
    ExponentialBackoffException
)
from .websocket_auth_service import (
    WebSocketAuthService,
    WebSocketAuthRequest,
    WebSocketAuthResponse
)
from .websocket_messaging_service import (
    WebSocketMessagingService,
    WebSocketEvent,
    WebSocketEventType
)

logger = logging.getLogger(__name__)


# Lua script for atomic rate limiting
RATE_LIMIT_LUA_SCRIPT = """
    local user_key = KEYS[1]
    local conn_key = KEYS[2]
    local window_start = tonumber(ARGV[1])
    local now = tonumber(ARGV[2])
    local user_limit = tonumber(ARGV[3])
    local conn_limit = tonumber(ARGV[4])
    
    -- Clean old entries
    redis.call('ZREMRANGEBYSCORE', user_key, 0, window_start)
    redis.call('ZREMRANGEBYSCORE', conn_key, 0, window_start)
    
    -- Check current counts
    local user_count = redis.call('ZCARD', user_key)
    local conn_count = redis.call('ZCARD', conn_key)
    
    if user_count >= user_limit then
        return {0, 'user_limit_exceeded', user_count, conn_count}
    end
    
    if conn_count >= conn_limit then
        return {0, 'connection_limit_exceeded', user_count, conn_count}
    end
    
    -- Add current request
    local score = tostring(now) .. '-' .. math.random()
    redis.call('ZADD', user_key, now, score)
    redis.call('ZADD', conn_key, now, score)
    redis.call('EXPIRE', user_key, 60)
    redis.call('EXPIRE', conn_key, 60)
    
    return {1, 'allowed', user_count + 1, conn_count + 1}
"""


# Duplicate classes removed - now using imported services


class WebSocketSubscribeRequest(BaseModel):
    """WebSocket subscription request."""

    channels: List[str] = Field(default_factory=list)
    unsubscribe_channels: List[str] = Field(default_factory=list)


class WebSocketSubscribeResponse(BaseModel):
    """WebSocket subscription response."""

    success: bool
    subscribed_channels: List[str] = Field(default_factory=list)
    failed_channels: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    max_connections_per_user: int = 5
    max_connections_per_session: int = 3
    max_messages_per_connection_per_second: int = 10
    max_messages_per_user_per_minute: int = 100
    window_seconds: int = 60


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for Redis operations."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitBreakerState.CLOSED

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class ExponentialBackoff:
    """Exponential backoff with jitter for reconnection attempts."""

    def __init__(
        self,
        base_delay: float = 0.5,
        max_delay: float = 30.0,
        max_attempts: int = 10,
        jitter: bool = True,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.jitter = jitter
        self.attempt_count = 0

    def get_delay(self) -> float:
        """Calculate delay for current attempt."""
        if self.attempt_count >= self.max_attempts:
            # Use custom exception as requested in code review
            raise ExponentialBackoffException(
                f"Max reconnection attempts ({self.max_attempts}) exceeded",
                self.max_attempts,
                self.max_delay
            )

        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self.base_delay * (2**self.attempt_count)
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = random.uniform(-0.1, 0.1) * delay  # ±10% jitter
            delay += jitter_amount

        return delay

    def next_attempt(self) -> float:
        """Move to next attempt and return delay."""
        delay = self.get_delay()
        self.attempt_count += 1
        return delay

    def reset(self):
        """Reset attempt counter on successful connection."""
        self.attempt_count = 0


class RateLimiter:
    """Hierarchical rate limiter using Redis sliding window."""

    def __init__(self, redis_client: Optional[redis.Redis], config: RateLimitConfig):
        self.redis = redis_client
        self.config = config
        self.local_counters: Dict[str, Dict] = defaultdict(
            lambda: {"count": 0, "window_start": time.time()}
        )

    async def check_connection_limit(
        self, user_id: UUID, session_id: Optional[UUID] = None
    ) -> bool:
        """Check if user/session can create new connection."""
        if not self.redis:
            return self._check_local_connection_limit(user_id, session_id)

        user_key = f"connections:user:{user_id}"
        session_key = f"connections:session:{session_id}" if session_id else None

        try:
            user_count = await self.redis.scard(user_key)

            if user_count >= self.config.max_connections_per_user:
                return False

            if session_key:
                session_count = await self.redis.scard(session_key)
                if session_count >= self.config.max_connections_per_session:
                    return False

            return True

        except Exception as e:
            logger.error(f"Rate limit check failed, using local fallback: {e}")
            return self._check_local_connection_limit(user_id, session_id)

    async def check_message_rate(
        self, user_id: UUID, connection_id: str
    ) -> Dict[str, Any]:
        """Check message rate limits."""
        if not self.redis:
            return self._check_local_message_rate(user_id, connection_id)

        user_key = f"messages:user:{user_id}"
        conn_key = f"messages:connection:{connection_id}"
        now = time.time()
        window_start = now - self.config.window_seconds

        try:
            # Use Redis script for atomic rate limiting
            result = await self.redis.eval(
                RATE_LIMIT_LUA_SCRIPT,
                2,
                user_key,
                conn_key,
                window_start,
                now,
                self.config.max_messages_per_user_per_minute,
                self.config.max_messages_per_connection_per_second
                * self.config.window_seconds,
            )

            allowed, reason, user_count, conn_count = result

            return {
                "allowed": bool(allowed),
                "reason": reason,
                "user_count": user_count,
                "connection_count": conn_count,
                "remaining": max(
                    0, self.config.max_messages_per_user_per_minute - user_count
                ),
            }

        except Exception as e:
            logger.error(f"Redis rate limit check failed, using local fallback: {e}")
            return self._check_local_message_rate(user_id, connection_id)

    def _check_local_connection_limit(
        self, user_id: UUID, session_id: Optional[UUID]
    ) -> bool:
        """Fallback local connection limit check."""
        # Simplified local implementation
        return True

    def _check_local_message_rate(
        self, user_id: UUID, connection_id: str
    ) -> Dict[str, Any]:
        """Fallback local message rate check."""
        now = time.time()
        counter = self.local_counters[f"user:{user_id}"]

        # Reset window if expired
        if now - counter["window_start"] >= self.config.window_seconds:
            counter["count"] = 0
            counter["window_start"] = now

        if counter["count"] >= self.config.max_messages_per_user_per_minute:
            return {
                "allowed": False,
                "reason": "user_limit_exceeded",
                "user_count": counter["count"],
                "connection_count": 0,
                "remaining": 0,
            }

        counter["count"] += 1
        return {
            "allowed": True,
            "reason": "allowed",
            "user_count": counter["count"],
            "connection_count": 0,
            "remaining": self.config.max_messages_per_user_per_minute
            - counter["count"],
        }


# WebSocketConnection class moved to websocket_connection_service.py


class WebSocketManager:
    """Enhanced WebSocket connection manager with broadcasting integration.
    
    Refactored to use extracted services for better separation of concerns.
    """

    def __init__(self, broadcaster=None):
        # Extracted services
        self.connection_service = WebSocketConnectionService()
        self.auth_service = WebSocketAuthService()
        self.messaging_service = WebSocketMessagingService(self.auth_service)

        # Redis integration
        self.redis_client: Optional[redis.Redis] = None
        self.redis_pubsub: Optional[redis.client.PubSub] = None
        self.broadcaster = broadcaster

        # Rate limiting
        self.rate_limiter: Optional[RateLimiter] = None

        # Performance monitoring
        self.performance_metrics = {
            "total_messages_sent": 0,
            "total_bytes_sent": 0,
            "active_connections": 0,
            "peak_connections": 0,
            "failed_connections": 0,
            "reconnection_attempts": 0,
            "rate_limit_hits": 0,
        }

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._performance_task: Optional[asyncio.Task] = None
        self._redis_listener_task: Optional[asyncio.Task] = None
        self._priority_processor_task: Optional[asyncio.Task] = None
        self._running = False

        # Settings
        self.settings = get_settings()

        # Configuration
        self.heartbeat_interval = 20  # 20 seconds as per research
        self.heartbeat_timeout = 5  # 5 second timeout for pong
        self.cleanup_interval = 60  # 1 minute cleanup cycle

        # Rate limiting configuration
        self.rate_limit_config = RateLimitConfig(
            max_connections_per_user=10,
            max_connections_per_session=3,
            max_messages_per_connection_per_second=10,
            max_messages_per_user_per_minute=600,
            window_seconds=60,
        )

    async def start(self) -> None:
        """Start the WebSocket manager with full integration."""
        if self._running:
            return

        self._running = True

        try:
            # Initialize Redis connection
            await self._initialize_redis()

            # Initialize rate limiter
            self.rate_limiter = RateLimiter(self.redis_client, self.rate_limit_config)

            # Start broadcaster if provided
            if self.broadcaster:
                await self.broadcaster.start()
                logger.info("WebSocket broadcaster started")

            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            self._performance_task = asyncio.create_task(self._performance_monitor())
            self._priority_processor_task = asyncio.create_task(
                self._process_priority_queues()
            )

            if self.redis_client:
                self._redis_listener_task = asyncio.create_task(
                    self._redis_message_listener()
                )

            logger.info("Enhanced WebSocket manager started with full integration")

        except Exception as e:
            logger.error(f"Failed to start WebSocket manager: {e}")
            self._running = False
            raise CoreServiceError(
                message=f"Failed to start WebSocket manager: {str(e)}",
                code="WEBSOCKET_MANAGER_START_FAILED",
                service="WebSocketManager",
            ) from e

    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        self._running = False

        # Cancel background tasks
        tasks = [
            self._cleanup_task,
            self._heartbeat_task,
            self._performance_task,
            self._redis_listener_task,
            self._priority_processor_task,
        ]

        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Stop broadcaster
        if self.broadcaster:
            await self.broadcaster.stop()

        # Close all connections
        await self.disconnect_all()

        # Close Redis connections
        if self.redis_pubsub:
            await self.redis_pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

        logger.info("Enhanced WebSocket manager stopped")

    async def _initialize_redis(self) -> None:
        """Initialize Redis connection for broadcasting."""
        redis_url = getattr(self.settings, "redis_url", None)
        if not redis_url:
            logger.warning(
                "No Redis URL configured, running without distributed features"
            )
            return

        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()

            self.redis_pubsub = self.redis_client.pubsub()
            # Subscribe to broadcast channels
            await self.redis_pubsub.psubscribe("tripsage:websocket:broadcast:*")

            logger.info("Redis connection initialized for WebSocket broadcasting")

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self.redis_client = None
            self.redis_pubsub = None

    async def authenticate_connection(
        self, websocket: WebSocket, auth_request: WebSocketAuthRequest
    ) -> WebSocketAuthResponse:
        """Authenticate a WebSocket connection with rate limiting.
        
        Refactored to use extracted authentication helper methods.
        """
        try:
            # Use auth service to verify token
            user_id = await self.auth_service.verify_jwt_token(auth_request.token)

            # Check rate limits
            if not await self._check_connection_rate_limit(
                user_id, auth_request.session_id
            ):
                return WebSocketAuthResponse(
                    success=False,
                    connection_id="",
                    error="Connection rate limit exceeded",
                )

            # Create connection using connection service
            connection_id = str(uuid4())
            connection = await self.connection_service.create_connection(
                websocket=websocket,
                connection_id=connection_id,
                user_id=user_id,
                session_id=auth_request.session_id,
            )

            # Register with messaging service
            self.messaging_service.register_connection(connection)

            # Validate and subscribe to channels
            available_channels = self.auth_service.get_available_channels(user_id)
            allowed_channels, _denied_channels = self.auth_service.validate_channel_access(
                user_id, auth_request.channels
            )
            
            for channel in allowed_channels:
                self.messaging_service.subscribe_to_channel(connection_id, channel)

            # Register with broadcaster
            if self.broadcaster:
                await self.broadcaster.register_connection(
                    connection_id,
                    user_id,
                    auth_request.session_id,
                    allowed_channels,
                )

            # Update connection state
            from .websocket_connection_service import ConnectionState
            connection.state = ConnectionState.AUTHENTICATED

            logger.info(
                f"Authenticated WebSocket connection {connection_id} for user {user_id}"
            )

            return WebSocketAuthResponse(
                success=True,
                connection_id=connection_id,
                user_id=user_id,
                session_id=auth_request.session_id,
                available_channels=available_channels,
            )

        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            self.performance_metrics["failed_connections"] += 1
            return WebSocketAuthResponse(
                success=False,
                connection_id="",
                error=str(e),
            )

    async def subscribe_connection(
        self, connection_id: str, subscribe_request: WebSocketSubscribeRequest
    ) -> WebSocketSubscribeResponse:
        """Subscribe connection to channels."""
        connection = self.connection_service.get_connection(connection_id)
        if not connection:
            return WebSocketSubscribeResponse(
                success=False, error="Connection not found"
            )

        subscribed = []
        failed = []

        # Subscribe to new channels
        if subscribe_request.channels:
            available_channels = self.auth_service.get_available_channels(connection.user_id)
            allowed_channels, denied_channels = self.auth_service.validate_channel_access(
                connection.user_id, subscribe_request.channels
            )
            
            for channel in allowed_channels:
                if self.messaging_service.subscribe_to_channel(connection_id, channel):
                    subscribed.append(channel)
                else:
                    failed.append(channel)
            
            failed.extend(denied_channels)

        # Unsubscribe from channels
        if subscribe_request.unsubscribe_channels:
            for channel in subscribe_request.unsubscribe_channels:
                self.messaging_service.unsubscribe_from_channel(connection_id, channel)

        return WebSocketSubscribeResponse(
            success=True, subscribed_channels=subscribed, failed_channels=failed
        )

    async def _check_connection_rate_limit(
        self, user_id: UUID, session_id: Optional[UUID] = None
    ) -> bool:
        """Check if connection is allowed under rate limits.

        Args:
            user_id: User ID
            session_id: Optional session ID

        Returns:
            True if connection is allowed
        """
        if not self.rate_limiter:
            return True

        can_connect = await self.rate_limiter.check_connection_limit(
            user_id, session_id
        )

        if not can_connect:
            self.performance_metrics["rate_limit_hits"] += 1

        return can_connect

    async def disconnect_connection(self, connection_id: str) -> None:
        """Disconnect a WebSocket connection with cleanup."""
        try:
            # Unregister from broadcaster
            if self.broadcaster:
                await self.broadcaster.unregister_connection(connection_id)

            # Remove from messaging service
            self.messaging_service.unregister_connection(connection_id)

            # Remove from connection service
            await self.connection_service.remove_connection(connection_id)

            logger.info(f"Disconnected WebSocket connection {connection_id}")

        except Exception as e:
            logger.error(f"Error disconnecting connection {connection_id}: {e}")

    async def send_to_connection(
        self, connection_id: str, event: WebSocketEvent
    ) -> bool:
        """Send event to specific connection with rate limiting."""
        return await self.messaging_service.send_to_connection(
            connection_id, event, self.rate_limiter
        )

    async def broadcast_to_channel(self, channel: str, event: WebSocketEvent) -> int:
        """Broadcast event to channel using integrated broadcaster."""
        if self.broadcaster:
            # Use broadcaster for distributed broadcasting
            event_dict = {
                "id": event.id,
                "type": event.type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": str(event.user_id) if event.user_id else None,
                "session_id": str(event.session_id) if event.session_id else None,
                "payload": event.payload,
            }
            await self.broadcaster.broadcast_to_channel(
                channel, event_dict, event.priority
            )

            # Also send to local connections via messaging service
            return await self.messaging_service.send_to_channel(channel, event, self.rate_limiter)
        else:
            # Fallback to local broadcasting
            return await self.send_to_channel(channel, event)

    async def send_to_channel(self, channel: str, event: WebSocketEvent) -> int:
        """Send event to all connections subscribed to a channel."""
        return await self.messaging_service.send_to_channel(
            channel, event, self.rate_limiter
        )

    async def send_to_user(self, user_id: UUID, event: WebSocketEvent) -> int:
        """Send event to all connections for a user."""
        # Use broadcaster for distributed messaging if available
        if self.broadcaster:
            event_dict = {
                "id": event.id,
                "type": event.type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": str(event.user_id) if event.user_id else None,
                "session_id": str(event.session_id) if event.session_id else None,
                "payload": event.payload,
            }
            await self.broadcaster.broadcast_to_user(
                user_id, event_dict, event.priority
            )

        # Send to local connections via messaging service
        return await self.messaging_service.send_to_user(
            user_id, event, self.rate_limiter
        )

    async def send_to_session(self, session_id: UUID, event: WebSocketEvent) -> int:
        """Send event to all connections for a session."""
        # Use broadcaster for distributed messaging if available
        if self.broadcaster:
            event_dict = {
                "id": event.id,
                "type": event.type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": str(event.user_id) if event.user_id else None,
                "session_id": str(event.session_id) if event.session_id else None,
                "payload": event.payload,
            }
            await self.broadcaster.broadcast_to_session(
                session_id, event_dict, event.priority
            )

        # Send to local connections via messaging service
        return await self.messaging_service.send_to_session(
            session_id, event, self.rate_limiter
        )

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections."""
        connection_ids = list(self.connection_service.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect_connection(connection_id)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        # Get stats from messaging service and combine with local metrics
        messaging_stats = self.messaging_service.get_connection_stats()
        
        combined_stats = {
            **messaging_stats,
            "redis_connected": self.redis_client is not None,
            "broadcaster_running": self.broadcaster is not None,
            "performance_metrics": {
                **self.performance_metrics,
                **messaging_stats.get("performance_metrics", {})
            }
        }
        
        return combined_stats

    # Helper methods moved to auth service

    async def _cleanup_stale_connections(self) -> None:
        """Background task to cleanup stale connections."""
        while self._running:
            try:
                # Get stale connections from connection service
                stale_connections = self.connection_service.get_stale_connections()

                for connection_id in stale_connections:
                    logger.info(f"Cleaning up stale connection {connection_id}")
                    await self.disconnect_connection(connection_id)

                await asyncio.sleep(self.cleanup_interval)

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def _heartbeat_monitor(self) -> None:
        """Background task to send heartbeat messages."""
        while self._running:
            try:
                from .websocket_connection_service import ConnectionState
                tasks = []
                for connection in self.connection_service.connections.values():
                    if connection.state in [
                        ConnectionState.CONNECTED,
                        ConnectionState.AUTHENTICATED,
                    ]:
                        tasks.append(connection.send_ping())

                # Send pings concurrently
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(self.heartbeat_interval)

            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _performance_monitor(self) -> None:
        """Background task to monitor and log performance metrics."""
        while self._running:
            try:
                # Update active connections count
                active_count = len(self.connection_service.connections)
                self.performance_metrics["active_connections"] = active_count

                if active_count > self.performance_metrics["peak_connections"]:
                    self.performance_metrics["peak_connections"] = active_count

                # Log performance metrics every 5 minutes
                if int(time.time()) % 300 == 0:
                    stats = self.get_connection_stats()
                    logger.info(f"WebSocket Performance Metrics: {stats}")

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
                await asyncio.sleep(30)

    async def _redis_message_listener(self) -> None:
        """Background task to listen for Redis pub/sub messages."""
        if not self.redis_pubsub:
            return

        try:
            async for message in self.redis_pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Parse broadcast message
                        data = json.loads(message["data"])
                        await self._handle_broadcast_message(data)
                    except Exception as e:
                        logger.error(f"Failed to handle broadcast message: {e}")

        except Exception as e:
            logger.error(f"Error in Redis message listener: {e}")

    async def _handle_broadcast_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming broadcast message from Redis."""
        try:
            event = WebSocketEvent(
                id=data.get("id", str(uuid4())),
                type=data["type"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                user_id=UUID(data["user_id"]) if data.get("user_id") else None,
                session_id=UUID(data["session_id"]) if data.get("session_id") else None,
                payload=data["payload"],
                priority=data.get("priority", 2),
            )

            # Use centralized channel parsing logic from auth service
            channel = data.get("channel", "")
            if ":" in channel:
                # Parse channel using auth service for consistency
                target_type, target_id = self.auth_service.parse_channel_target(channel)
                
                # Route based on parsed target
                if target_type == "user" and target_id:
                    await self.send_to_user(UUID(target_id), event)
                elif target_type == "session" and target_id:
                    await self.send_to_session(UUID(target_id), event)
                elif target_type == "channel" and target_id:
                    await self.send_to_channel(target_id, event)
                else:
                    # Fallback to broadcast
                    await self.messaging_service.broadcast_to_all(event, self.rate_limiter)
            else:
                # Broadcast to all local connections
                await self.messaging_service.broadcast_to_all(event, self.rate_limiter)

        except Exception as e:
            logger.error(f"Failed to handle broadcast message: {e}")

    async def _process_priority_queues(self) -> None:
        """Background task to process priority message queues with anti-starvation."""
        while self._running:
            try:
                from .websocket_connection_service import ConnectionState
                
                # Only process connections with non-empty queues
                connections_to_process = []
                for connection in self.connection_service.connections.values():
                    if connection.state in [
                        ConnectionState.CONNECTED,
                        ConnectionState.AUTHENTICATED,
                    ]:
                        # Check if any priority queue has messages
                        has_messages = any(
                            len(queue) > 0
                            for queue in connection.priority_queue.values()
                        )
                        if has_messages:
                            connections_to_process.append(connection)

                # Process connections with messages - include circuit breaker status
                for connection in connections_to_process:
                    circuit_breaker_open = not connection.circuit_breaker.can_execute()
                    await connection.process_priority_queue(circuit_breaker_open)

                # Sleep longer if no messages to process
                if connections_to_process:
                    await asyncio.sleep(0.1)  # Process queues frequently
                else:
                    await asyncio.sleep(0.5)  # Sleep longer when idle

            except Exception as e:
                logger.error(f"Error in priority queue processor: {e}")
                await asyncio.sleep(1)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
