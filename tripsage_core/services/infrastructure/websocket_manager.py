"""
WebSocket connection manager with integrated broadcasting and error recovery.

This module provides comprehensive WebSocket connection management including:
- Integration with Redis-backed broadcasting
- Automatic error recovery with exponential backoff
- 20-second heartbeat/keepalive mechanism
- Connection state management and monitoring
- Rate limiting and throttling
- Circuit breaker patterns for fault tolerance
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

import jwt
import redis.asyncio as redis
from fastapi import WebSocket
from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreServiceError,
)

logger = logging.getLogger(__name__)


class MonitoredDeque(deque):
    """Deque that logs when items are dropped due to maxlen."""

    def __init__(
        self, *args, priority_name: str = "", connection_id: str = "", **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.priority_name = priority_name
        self.connection_id = connection_id
        self.dropped_count = 0

    def append(self, item):
        if self.maxlen and len(self) >= self.maxlen:
            self.dropped_count += 1
            logger.warning(
                f"Message dropped from {self.priority_name} priority queue "
                f"for connection {self.connection_id}. "
                f"Total dropped: {self.dropped_count}"
            )
        super().append(item)

    def appendleft(self, item):
        if self.maxlen and len(self) >= self.maxlen:
            self.dropped_count += 1
            logger.warning(
                f"Message dropped from {self.priority_name} priority queue "
                f"for connection {self.connection_id}. "
                f"Total dropped: {self.dropped_count}"
            )
        super().appendleft(item)


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


class ConnectionState(str, Enum):
    """Enhanced connection state management."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SUSPENDED = "suspended"
    DEGRADED = "degraded"


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


class WebSocketEvent(BaseModel):
    """Enhanced WebSocket event model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    connection_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, description="1=high, 2=medium, 3=low")
    retry_count: int = Field(default=0)
    expires_at: Optional[datetime] = None


class WebSocketAuthRequest(BaseModel):
    """WebSocket authentication request."""

    token: str
    session_id: Optional[UUID] = None
    channels: List[str] = Field(default_factory=list)


class WebSocketAuthResponse(BaseModel):
    """WebSocket authentication response."""

    success: bool
    connection_id: str
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    available_channels: List[str] = Field(default_factory=list)
    error: Optional[str] = None


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


class ConnectionHealth(BaseModel):
    """Connection health metrics."""

    latency: float = Field(description="Round-trip time in milliseconds")
    message_rate: float = Field(description="Messages per second")
    error_rate: float = Field(description="Errors per minute")
    reconnect_count: int = Field(description="Total reconnections")
    last_activity: datetime = Field(description="Last message timestamp")
    quality: str = Field(description="excellent/good/poor/critical")


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
            raise Exception(f"Max reconnection attempts ({self.max_attempts}) exceeded")

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


class WebSocketConnection:
    """Enhanced WebSocket connection wrapper with health monitoring."""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.session_id = session_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.last_pong = datetime.utcnow()
        self.state = ConnectionState.CONNECTED
        self.subscribed_channels: Set[str] = set()
        self.client_ip: Optional[str] = None
        self.user_agent: Optional[str] = None

        # Message queue with priority support
        self.message_queue: Deque[WebSocketEvent] = MonitoredDeque(
            maxlen=1000, priority_name="main", connection_id=connection_id
        )
        self.priority_queue: Dict[int, Deque[WebSocketEvent]] = {
            1: MonitoredDeque(
                maxlen=100, priority_name="high", connection_id=connection_id
            ),
            2: MonitoredDeque(
                maxlen=500, priority_name="medium", connection_id=connection_id
            ),
            3: MonitoredDeque(
                maxlen=1000, priority_name="low", connection_id=connection_id
            ),
        }

        # Performance metrics
        self.last_activity = time.time()
        self.bytes_sent = 0
        self.bytes_received = 0
        self.message_count = 0
        self.error_count = 0
        self.reconnect_count = 0

        # Connection health
        self.latency_samples: Deque[float] = deque(maxlen=10)
        self.ping_sent_time: Optional[float] = None

        # Concurrency control
        self._send_lock = asyncio.Lock()
        self._ping_task: Optional[asyncio.Task] = None

        # Error recovery
        self.backoff = ExponentialBackoff()
        self.circuit_breaker = CircuitBreaker()

    async def send(self, event: WebSocketEvent) -> bool:
        """Send event to WebSocket connection with error handling."""
        if self.state not in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
            logger.warning(
                f"Cannot send to connection {self.connection_id} in state {self.state}"
            )
            return False

        # Add to priority queue if connection is busy
        if self._send_lock.locked():
            self.priority_queue[event.priority].append(event)
            return True

        async with self._send_lock:
            try:
                if not self.circuit_breaker.can_execute():
                    logger.warning(
                        f"Circuit breaker open for connection {self.connection_id}"
                    )
                    # Queue the event for later retry
                    self.priority_queue[event.priority].append(event)
                    return True

                message = {
                    "id": event.id,
                    "type": event.type,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": str(event.user_id) if event.user_id else None,
                    "session_id": str(event.session_id) if event.session_id else None,
                    "payload": event.payload,
                }

                data = json.dumps(message)
                await self.websocket.send_text(data)

                # Update metrics
                self.last_activity = time.time()
                self.bytes_sent += len(data.encode("utf-8"))
                self.message_count += 1
                self.circuit_breaker.record_success()

                return True

            except Exception as e:
                logger.error(f"Failed to send message to {self.connection_id}: {e}")
                self.error_count += 1
                self.circuit_breaker.record_failure()
                self.state = ConnectionState.ERROR

                # Queue for retry if not permanent error
                if event.retry_count < 3:
                    event.retry_count += 1
                    self.priority_queue[1].append(event)  # High priority retry

                return False

    async def send_ping(self) -> bool:
        """Send ping and track latency."""
        try:
            ping_event = WebSocketEvent(
                type=WebSocketEventType.CONNECTION_HEARTBEAT,
                payload={"timestamp": datetime.utcnow().isoformat(), "ping": True},
            )

            self.ping_sent_time = time.time()
            success = await self.send(ping_event)

            if not success:
                self.state = ConnectionState.ERROR

            return success

        except Exception as e:
            logger.error(f"Failed to send ping to {self.connection_id}: {e}")
            self.state = ConnectionState.ERROR
            return False

    def handle_pong(self):
        """Handle pong response and calculate latency."""
        if self.ping_sent_time:
            latency = (time.time() - self.ping_sent_time) * 1000  # Convert to ms
            self.latency_samples.append(latency)
            self.ping_sent_time = None

        self.last_pong = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()

    def is_stale(self, timeout_seconds: int = 60) -> bool:
        """Check if connection is stale based on last heartbeat."""
        return (
            datetime.utcnow() - self.last_heartbeat
        ).total_seconds() > timeout_seconds

    def is_ping_timeout(self, timeout_seconds: int = 5) -> bool:
        """Check if ping response is overdue."""
        if not self.ping_sent_time:
            return False
        return time.time() - self.ping_sent_time > timeout_seconds

    def get_health(self) -> ConnectionHealth:
        """Get connection health metrics."""
        avg_latency = (
            sum(self.latency_samples) / len(self.latency_samples)
            if self.latency_samples
            else 0
        )

        # Determine quality based on latency and error rate
        if avg_latency > 2000 or self.error_count > 10:
            quality = "critical"
        elif avg_latency > 1000 or self.error_count > 5:
            quality = "poor"
        elif avg_latency > 500 or self.error_count > 1:
            quality = "good"
        else:
            quality = "excellent"

        return ConnectionHealth(
            latency=avg_latency,
            message_rate=self.message_count
            / max(1, (time.time() - self.connected_at.timestamp())),
            error_rate=self.error_count
            / max(1, (time.time() - self.connected_at.timestamp()) / 60),
            reconnect_count=self.reconnect_count,
            last_activity=datetime.fromtimestamp(self.last_activity),
            quality=quality,
        )

    async def process_priority_queue(self) -> int:
        """Process queued messages by priority."""
        sent_count = 0

        # Process high priority first
        for priority in [1, 2, 3]:
            queue = self.priority_queue[priority]
            while queue and sent_count < 10:  # Limit batch size
                event = queue.popleft()
                if await self.send(event):
                    sent_count += 1
                else:
                    break  # Stop on failure

        return sent_count

    def subscribe_to_channel(self, channel: str) -> None:
        """Subscribe to a channel."""
        self.subscribed_channels.add(channel)
        logger.debug(f"Connection {self.connection_id} subscribed to {channel}")

    def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        self.subscribed_channels.discard(channel)
        logger.debug(f"Connection {self.connection_id} unsubscribed from {channel}")

    def is_subscribed_to_channel(self, channel: str) -> bool:
        """Check if subscribed to a channel."""
        return channel in self.subscribed_channels


class WebSocketManager:
    """Enhanced WebSocket connection manager with broadcasting integration."""

    def __init__(self, broadcaster=None):
        # Core storage
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[UUID, Set[str]] = {}
        self.session_connections: Dict[UUID, Set[str]] = {}
        self.channel_connections: Dict[str, Set[str]] = {}

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
        """Authenticate a WebSocket connection with rate limiting."""
        try:
            # Verify JWT token
            user_id = await self._verify_jwt_token(auth_request.token)

            # Check rate limits
            if not await self._check_connection_rate_limit(
                user_id, auth_request.session_id
            ):
                return WebSocketAuthResponse(
                    success=False,
                    connection_id="",
                    error="Connection rate limit exceeded",
                )

            # Create connection
            connection_id = str(uuid4())
            connection = WebSocketConnection(
                websocket=websocket,
                connection_id=connection_id,
                user_id=user_id,
                session_id=auth_request.session_id,
            )

            # Extract client info
            if websocket.client:
                connection.client_ip = websocket.client.host

            # Add to connection pools
            self.connections[connection_id] = connection

            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

            if auth_request.session_id:
                if auth_request.session_id not in self.session_connections:
                    self.session_connections[auth_request.session_id] = set()
                self.session_connections[auth_request.session_id].add(connection_id)

            # Subscribe to requested channels
            available_channels = self._get_available_channels(user_id)
            for channel in auth_request.channels:
                if channel in available_channels:
                    connection.subscribe_to_channel(channel)
                    if channel not in self.channel_connections:
                        self.channel_connections[channel] = set()
                    self.channel_connections[channel].add(connection_id)

            # Register with broadcaster
            if self.broadcaster:
                await self.broadcaster.register_connection(
                    connection_id,
                    user_id,
                    auth_request.session_id,
                    auth_request.channels,
                )

            # Update state
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
        connection = self.connections.get(connection_id)
        if not connection:
            return WebSocketSubscribeResponse(
                success=False, error="Connection not found"
            )

        subscribed = []
        failed = []

        # Subscribe to new channels
        if subscribe_request.channels:
            available_channels = self._get_available_channels(connection.user_id)
            for channel in subscribe_request.channels:
                if channel in available_channels:
                    connection.subscribe_to_channel(channel)
                    if channel not in self.channel_connections:
                        self.channel_connections[channel] = set()
                    self.channel_connections[channel].add(connection_id)
                    subscribed.append(channel)
                else:
                    failed.append(channel)

        # Unsubscribe from channels
        if subscribe_request.unsubscribe_channels:
            for channel in subscribe_request.unsubscribe_channels:
                connection.unsubscribe_from_channel(channel)
                if channel in self.channel_connections:
                    self.channel_connections[channel].discard(connection_id)
                    if not self.channel_connections[channel]:
                        del self.channel_connections[channel]

        return WebSocketSubscribeResponse(
            success=True, subscribed_channels=subscribed, failed_channels=failed
        )

    async def _verify_jwt_token(self, token: str) -> UUID:
        """Verify JWT token and extract user ID.

        Args:
            token: JWT token to verify

        Returns:
            User ID from token

        Raises:
            CoreAuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key.get_secret_value(),
                algorithms=["HS256"],
            )

            if "sub" not in payload or "user_id" not in payload:
                raise CoreAuthenticationError(
                    message="Invalid token payload",
                    details={"reason": "Missing required fields"},
                )

            return UUID(payload["user_id"])
        except jwt.InvalidTokenError as e:
            raise CoreAuthenticationError(
                message="Invalid token",
                details={"reason": str(e)},
            ) from e

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
        connection = self.connections.get(connection_id)
        if not connection:
            return

        try:
            # Unregister from broadcaster
            if self.broadcaster:
                await self.broadcaster.unregister_connection(connection_id)

            # Remove from all pools
            self.connections.pop(connection_id, None)

            if connection.user_id and connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]

            if (
                connection.session_id
                and connection.session_id in self.session_connections
            ):
                self.session_connections[connection.session_id].discard(connection_id)
                if not self.session_connections[connection.session_id]:
                    del self.session_connections[connection.session_id]

            # Remove from channels
            for channel in connection.subscribed_channels:
                if channel in self.channel_connections:
                    self.channel_connections[channel].discard(connection_id)
                    if not self.channel_connections[channel]:
                        del self.channel_connections[channel]

            connection.state = ConnectionState.DISCONNECTED
            logger.info(f"Disconnected WebSocket connection {connection_id}")

        except Exception as e:
            logger.error(f"Error disconnecting connection {connection_id}: {e}")

    async def send_to_connection(
        self, connection_id: str, event: WebSocketEvent
    ) -> bool:
        """Send event to specific connection with rate limiting."""
        connection = self.connections.get(connection_id)
        if not connection:
            return False

        # Check message rate limit
        if self.rate_limiter and connection.user_id:
            rate_check = await self.rate_limiter.check_message_rate(
                connection.user_id, connection_id
            )
            if not rate_check["allowed"]:
                self.performance_metrics["rate_limit_hits"] += 1

                # Send rate limit warning
                warning_event = WebSocketEvent(
                    type=WebSocketEventType.RATE_LIMIT_EXCEEDED,
                    payload={
                        "reason": rate_check["reason"],
                        "retry_after": self.rate_limit_config.window_seconds,
                    },
                )
                # Send warning without rate limiting
                await connection.send(warning_event)
                return False

        success = await connection.send(event)
        if success:
            self.performance_metrics["total_messages_sent"] += 1

        return success

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

            # Also send to local connections
            connection_ids = self.channel_connections.get(channel, set())
            sent_count = 0
            for connection_id in connection_ids.copy():
                if await self.send_to_connection(connection_id, event):
                    sent_count += 1

            return sent_count
        else:
            # Fallback to local broadcasting
            return await self.send_to_channel(channel, event)

    async def send_to_channel(self, channel: str, event: WebSocketEvent) -> int:
        """Send event to all connections subscribed to a channel."""
        connection_ids = self.channel_connections.get(channel, set())
        sent_count = 0

        for connection_id in connection_ids.copy():
            if await self.send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def send_to_user(self, user_id: UUID, event: WebSocketEvent) -> int:
        """Send event to all connections for a user."""
        if self.broadcaster:
            # Use broadcaster for distributed messaging
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

        # Send to local connections
        connection_ids = self.user_connections.get(user_id, set())
        sent_count = 0

        for connection_id in connection_ids.copy():
            if await self.send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def send_to_session(self, session_id: UUID, event: WebSocketEvent) -> int:
        """Send event to all connections for a session."""
        if self.broadcaster:
            # Use broadcaster for distributed messaging
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

        # Send to local connections
        connection_ids = self.session_connections.get(session_id, set())
        sent_count = 0

        for connection_id in connection_ids.copy():
            if await self.send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket connections."""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect_connection(connection_id)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
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
            "redis_connected": self.redis_client is not None,
            "broadcaster_running": self.broadcaster is not None,
        }

    def _get_available_channels(self, user_id: Optional[UUID]) -> List[str]:
        """Get available channels for a user."""
        if not user_id:
            return []

        # Base channels available to all authenticated users
        channels = [
            "general",
            "notifications",
            f"user:{user_id}",
            f"agent_status:{user_id}",
        ]

        return channels

    async def _cleanup_stale_connections(self) -> None:
        """Background task to cleanup stale connections."""
        while self._running:
            try:
                stale_connections = []

                for connection_id, connection in self.connections.items():
                    if connection.is_stale() or connection.is_ping_timeout():
                        stale_connections.append(connection_id)

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
                tasks = []
                for connection in self.connections.values():
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
                active_count = len(self.connections)
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

            # Route message based on target type from channel pattern
            channel = data.get("channel", "")
            if ":user:" in channel:
                user_id = UUID(channel.split(":user:")[1])
                await self.send_to_user(user_id, event)
            elif ":session:" in channel:
                session_id = UUID(channel.split(":session:")[1])
                await self.send_to_session(session_id, event)
            elif ":channel:" in channel:
                channel_name = channel.split(":channel:")[1]
                await self.send_to_channel(channel_name, event)
            else:
                # Broadcast to all local connections
                for connection_id in list(self.connections.keys()):
                    await self.send_to_connection(connection_id, event)

        except Exception as e:
            logger.error(f"Failed to handle broadcast message: {e}")

    async def _process_priority_queues(self) -> None:
        """Background task to process priority message queues."""
        while self._running:
            try:
                # Only process connections with non-empty queues
                connections_to_process = []
                for connection in self.connections.values():
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

                # Process connections with messages
                for connection in connections_to_process:
                    await connection.process_priority_queue()

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
