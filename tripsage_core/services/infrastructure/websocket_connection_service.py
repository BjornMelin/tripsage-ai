"""
WebSocket connection management service.

This service handles individual WebSocket connection lifecycle including:
- Connection establishment and authentication
- Message sending and receiving
- Health monitoring and metrics
- Error recovery and circuit breaking
"""

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Deque, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket
from pydantic import BaseModel, Field

from tripsage_core.exceptions.exceptions import CoreServiceError

logger = logging.getLogger(__name__)


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


class ConnectionHealth(BaseModel):
    """Connection health metrics."""

    latency: float = Field(description="Round-trip time in milliseconds")
    message_rate: float = Field(description="Messages per second")
    error_rate: float = Field(description="Errors per minute")
    reconnect_count: int = Field(description="Total reconnections")
    last_activity: datetime = Field(description="Last message timestamp")
    quality: str = Field(description="excellent/good/poor/critical")


class ExponentialBackoffException(Exception):
    """Custom exception for exponential backoff failures."""
    
    def __init__(self, message: str, max_attempts: int, last_delay: float):
        super().__init__(message)
        self.max_attempts = max_attempts
        self.last_delay = last_delay


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

        # Message queue with priority support - fix starvation issue
        self.message_queue: Deque[Any] = MonitoredDeque(
            maxlen=1000, priority_name="main", connection_id=connection_id
        )
        self.priority_queue: Dict[int, Deque[Any]] = {
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

        # Connection health - fix latency calculation for low sample counts
        self.latency_samples: Deque[float] = deque(maxlen=10)
        self.ping_sent_time: Optional[float] = None

        # Error recovery components that were moved from manager
        from .websocket_manager import CircuitBreaker, ExponentialBackoff
        self.circuit_breaker = CircuitBreaker()
        self.backoff = ExponentialBackoff()
        
        # Concurrency control
        self._send_lock = asyncio.Lock()
        self._ping_task: Optional[asyncio.Task] = None

    async def send(self, event: Dict[str, Any]) -> bool:
        """Send event to WebSocket connection with error handling."""
        if self.state not in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]:
            logger.warning(
                f"Cannot send to connection {self.connection_id} in state {self.state}"
            )
            return False

        # Add to priority queue if connection is busy
        priority = getattr(event, 'priority', 2) if hasattr(event, 'priority') else event.get('priority', 2)
        if self._send_lock.locked():
            self.priority_queue[priority].append(event)
            return True

        async with self._send_lock:
            try:
                # Handle both Pydantic models and dicts
                if hasattr(event, 'model_dump'):
                    event_dict = event.model_dump()
                    # Convert UUID fields to strings for JSON serialization
                    if 'user_id' in event_dict and event_dict['user_id']:
                        event_dict['user_id'] = str(event_dict['user_id'])
                    if 'session_id' in event_dict and event_dict['session_id']:
                        event_dict['session_id'] = str(event_dict['session_id'])
                    if 'timestamp' in event_dict and hasattr(event_dict['timestamp'], 'isoformat'):
                        event_dict['timestamp'] = event_dict['timestamp'].isoformat()
                    data = json.dumps(event_dict)
                else:
                    data = json.dumps(event)
                await self.websocket.send_text(data)

                # Update metrics
                self.last_activity = time.time()
                self.bytes_sent += len(data.encode("utf-8"))
                self.message_count += 1

                return True

            except Exception as e:
                logger.error(f"Failed to send message to {self.connection_id}: {e}")
                self.error_count += 1
                self.state = ConnectionState.ERROR

                # Queue for retry if not permanent error
                retry_count = getattr(event, 'retry_count', 0) if hasattr(event, 'retry_count') else event.get('retry_count', 0)
                if retry_count < 3:
                    if hasattr(event, 'retry_count'):
                        # For Pydantic models, create a new instance with updated retry count
                        event_dict = event.model_dump() if hasattr(event, 'model_dump') else event.__dict__
                        event_dict['retry_count'] = retry_count + 1
                        from .websocket_messaging_service import WebSocketEvent
                        retry_event = WebSocketEvent(**event_dict)
                        self.priority_queue[1].append(retry_event)  # High priority retry
                    else:
                        # For dict events
                        event['retry_count'] = retry_count + 1
                        self.priority_queue[1].append(event)  # High priority retry

                return False

    async def send_ping(self) -> bool:
        """Send ping and track latency."""
        try:
            ping_event = {
                "type": "connection.heartbeat",
                "payload": {"timestamp": datetime.utcnow().isoformat(), "ping": True},
            }

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
        """Get connection health metrics with improved latency calculation."""
        # Improved latency calculation for low sample counts
        if self.latency_samples:
            avg_latency = sum(self.latency_samples) / len(self.latency_samples)
        else:
            avg_latency = 0

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

    async def process_priority_queue(self, circuit_breaker_open: bool = False) -> int:
        """Process queued messages by priority with anti-starvation measures."""
        sent_count = 0
        max_batch_size = 5 if circuit_breaker_open else 10  # Limit queue size when circuit breaker is open
        
        # Anti-starvation: process each priority level fairly
        for _ in range(max_batch_size):
            # Round-robin through priorities to prevent starvation
            for priority in [3, 2, 1]:  # Process low priority first, then medium, then high
                queue = self.priority_queue[priority]
                if queue and sent_count < max_batch_size:
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


class WebSocketConnectionService:
    """Service for managing individual WebSocket connections."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        
    async def create_connection(
        self, 
        websocket: WebSocket, 
        connection_id: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None
    ) -> WebSocketConnection:
        """Create a new WebSocket connection."""
        connection = WebSocketConnection(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )
        
        # Extract client info
        if websocket.client:
            connection.client_ip = websocket.client.host
            
        self.connections[connection_id] = connection
        return connection
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a connection."""
        connection = self.connections.pop(connection_id, None)
        if connection:
            connection.state = ConnectionState.DISCONNECTED
            logger.info(f"Removed WebSocket connection {connection_id}")
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a connection by ID."""
        return self.connections.get(connection_id)
    
    def get_connections_for_user(self, user_id: UUID) -> Dict[str, WebSocketConnection]:
        """Get all connections for a user."""
        return {
            conn_id: conn for conn_id, conn in self.connections.items()
            if conn.user_id == user_id
        }
    
    def get_connections_for_session(self, session_id: UUID) -> Dict[str, WebSocketConnection]:
        """Get all connections for a session."""
        return {
            conn_id: conn for conn_id, conn in self.connections.items()
            if conn.session_id == session_id
        }
    
    def get_stale_connections(self, timeout_seconds: int = 60) -> list[str]:
        """Get list of stale connection IDs."""
        return [
            conn_id for conn_id, conn in self.connections.items()
            if conn.is_stale(timeout_seconds) or conn.is_ping_timeout()
        ]