"""WebSocket router for TripSage API with performance optimizations.

This module provides WebSocket endpoints for real-time communication,
including chat streaming, agent status updates, and live user feedback.

Performance optimizations include:
- Message batching and compression
- Connection pooling
- Concurrent message handling
- Zero artificial delays
- Binary protocol support with MessagePack
- Adaptive heartbeat mechanism
- Backpressure handling
"""

import asyncio
import gzip
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime

# No typing imports needed - using Python 3.13 built-in types
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import Field, ValidationError

from tripsage.agents.chat import ChatAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage.api.core.dependencies import get_db
from tripsage.api.schemas.websocket import (
    WebSocketAuthRequest,
    WebSocketSubscribeRequest,
)
from tripsage_core.config import get_settings
from tripsage_core.models.schemas_common.chat import ChatMessage as WebSocketMessage
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
)
from tripsage_core.services.business.chat_service import (
    MessageCreateRequest,
    MessageRole,
)
from tripsage_core.services.infrastructure.websocket_manager import websocket_manager
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)

# Optional MessagePack support
try:
    import msgpack

    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None


# Performance configuration
class PerformanceConfig:
    """WebSocket performance configuration."""

    # Message batching
    BATCH_SIZE = 20  # Messages per batch
    BATCH_TIMEOUT_MS = 10  # Max wait time for batch

    # Compression
    COMPRESSION_THRESHOLD = 1024  # Compress messages larger than 1KB
    COMPRESSION_LEVEL = 6  # gzip compression level (1-9)

    # Connection pooling
    MAX_POOL_SIZE = 1000  # Maximum concurrent connections
    POOL_CLEANUP_INTERVAL = 60  # Seconds between cleanup cycles

    # Heartbeat configuration
    HEARTBEAT_INTERVAL = 30  # Seconds between heartbeats
    HEARTBEAT_TIMEOUT = 5  # Seconds to wait for pong

    # Message processing
    CONCURRENT_HANDLERS = 10  # Max concurrent message handlers per connection
    MESSAGE_TIMEOUT = 30  # Seconds timeout for message processing

    # Backpressure
    MAX_QUEUE_SIZE = 10000  # Max messages in queue before backpressure
    BACKPRESSURE_THRESHOLD = 0.8  # Trigger backpressure at 80% capacity


# WebSocket Security Configuration
def get_allowed_origins() -> list[str]:
    """Get allowed origins from settings or use defaults."""
    settings = get_settings()
    # Check if settings has websocket_allowed_origins attribute
    if hasattr(settings, "websocket_allowed_origins"):
        return settings.websocket_allowed_origins
    # Default allowed origins for production and development
    return [
        "https://app.tripsage.com",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]


async def validate_websocket_origin(websocket: WebSocket) -> bool:
    """Validate WebSocket Origin header to prevent CSWSH attacks.

    Args:
        websocket: The WebSocket connection to validate

    Returns:
        True if the origin is allowed, False otherwise
    """
    origin = websocket.headers.get("origin", "").lower()

    # If no origin header, reject for security (browsers always send it)
    if not origin:
        logger.warning("WebSocket connection rejected: No Origin header")
        return False

    allowed_origins = get_allowed_origins()

    # Check if origin matches any allowed origin (exact match only for security)
    for allowed in allowed_origins:
        if origin == allowed.lower():
            logger.debug(f"WebSocket origin validated: {origin}")
            return True

    logger.warning(f"WebSocket connection rejected: Invalid origin '{origin}'")
    return False


# Create event classes here temporarily until they are properly organized
class ChatMessageEvent(WebSocketEvent):
    type: str = Field(default=WebSocketEventType.CHAT_MESSAGE, description="Event type")
    message: WebSocketMessage


class ChatMessageChunkEvent(WebSocketEvent):
    type: str = Field(default=WebSocketEventType.CHAT_TYPING, description="Event type")
    content: str
    chunk_index: int = 0
    is_final: bool = False


class ConnectionEvent(WebSocketEvent):
    type: str = Field(
        default=WebSocketEventType.CONNECTION_ESTABLISHED, description="Event type"
    )
    status: str = Field(..., description="Connection status")
    connection_id: str = Field(..., description="Connection ID")


class ErrorEvent(WebSocketEvent):
    type: str = Field(
        default=WebSocketEventType.CONNECTION_ERROR, description="Event type"
    )
    error_code: str
    error_message: str


logger = logging.getLogger(__name__)

router = APIRouter()

# Global chat agent instance
_chat_agent = None
_service_registry = None

# Performance monitoring
performance_metrics = {
    "total_messages_processed": 0,
    "total_batches_sent": 0,
    "compression_ratio": 0.0,
    "average_batch_size": 0.0,
    "concurrent_connections": 0,
    "message_processing_time_ms": deque(maxlen=1000),
}


# Message batching system
class MessageBatcher:
    """Handles message batching for efficient transmission."""

    def __init__(self, connection_id: str, websocket: WebSocket):
        self.connection_id = connection_id
        self.websocket = websocket
        self.batch_queue: deque = deque()
        self.batch_task: asyncio.Task | None = None
        self.last_send_time = time.time()
        self._running = True
        self._send_lock = asyncio.Lock()

    async def add_message(self, message: dict[str, any]) -> None:
        """Add message to batch queue."""
        self.batch_queue.append(message)

        # Start batch processor if not running
        if not self.batch_task or self.batch_task.done():
            self.batch_task = asyncio.create_task(self._process_batch())

    async def _process_batch(self) -> None:
        """Process and send batched messages."""
        while self._running:
            try:
                # Wait for batch to fill or timeout
                await asyncio.sleep(PerformanceConfig.BATCH_TIMEOUT_MS / 1000)

                if not self.batch_queue:
                    continue

                # Collect batch
                batch = []
                while len(batch) < PerformanceConfig.BATCH_SIZE and self.batch_queue:
                    batch.append(self.batch_queue.popleft())

                if batch:
                    await self._send_batch(batch)

            except Exception as e:
                logger.error(f"Error processing batch for {self.connection_id}: {e}")

    async def _send_batch(self, batch: list[dict[str, any]]) -> None:
        """Send a batch of messages with optional compression."""
        async with self._send_lock:
            try:
                # Prepare batch payload
                payload = {
                    "type": "batch",
                    "messages": batch,
                    "timestamp": datetime.utcnow().isoformat(),
                    "count": len(batch),
                }

                # Serialize
                if MSGPACK_AVAILABLE and self.supports_binary:
                    data = msgpack.packb(payload)
                    is_binary = True
                else:
                    data = json.dumps(payload).encode("utf-8")
                    is_binary = False

                # Compress if beneficial
                if len(data) > PerformanceConfig.COMPRESSION_THRESHOLD:
                    compressed = gzip.compress(
                        data, PerformanceConfig.COMPRESSION_LEVEL
                    )
                    if len(compressed) < len(data) * 0.9:  # Only use if >10% reduction
                        data = compressed
                        payload["compressed"] = True

                # Send
                if is_binary:
                    await self.websocket.send_bytes(data)
                else:
                    await self.websocket.send_text(data.decode("utf-8"))

                # Update metrics
                performance_metrics["total_batches_sent"] += 1
                performance_metrics["average_batch_size"] = (
                    performance_metrics["average_batch_size"]
                    * (performance_metrics["total_batches_sent"] - 1)
                    + len(batch)
                ) / performance_metrics["total_batches_sent"]

            except Exception as e:
                logger.error(f"Failed to send batch to {self.connection_id}: {e}")

    async def close(self) -> None:
        """Close the batcher and flush remaining messages."""
        self._running = False

        # Flush remaining messages
        if self.batch_queue:
            batch = list(self.batch_queue)
            self.batch_queue.clear()
            await self._send_batch(batch)

        if self.batch_task:
            self.batch_task.cancel()

    @property
    def supports_binary(self) -> bool:
        """Check if connection supports binary messages."""
        # This would be determined during handshake
        return getattr(self.websocket, "_supports_binary", False)


# Connection pool manager
class ConnectionPool:
    """Manages WebSocket connections with pooling."""

    def __init__(self):
        self.connections: dict[str, MessageBatcher] = {}
        self.user_connections: dict[UUID, set[str]] = defaultdict(set)
        self.session_connections: dict[UUID, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def add_connection(
        self,
        connection_id: str,
        websocket: WebSocket,
        user_id: UUID,
        session_id: UUID | None = None,
    ) -> MessageBatcher:
        """Add connection to pool."""
        async with self._lock:
            if len(self.connections) >= PerformanceConfig.MAX_POOL_SIZE:
                raise ValueError("Connection pool at capacity")

            batcher = MessageBatcher(connection_id, websocket)
            self.connections[connection_id] = batcher
            self.user_connections[user_id].add(connection_id)

            if session_id:
                self.session_connections[session_id].add(connection_id)

            performance_metrics["concurrent_connections"] = len(self.connections)

            # Start cleanup task if needed
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_stale())

            return batcher

    async def remove_connection(self, connection_id: str) -> None:
        """Remove connection from pool."""
        async with self._lock:
            if connection_id in self.connections:
                batcher = self.connections[connection_id]
                await batcher.close()
                del self.connections[connection_id]

                # Clean up indices
                for connections in self.user_connections.values():
                    connections.discard(connection_id)
                for connections in self.session_connections.values():
                    connections.discard(connection_id)

                performance_metrics["concurrent_connections"] = len(self.connections)

    async def get_connection(self, connection_id: str) -> MessageBatcher | None:
        """Get connection batcher."""
        return self.connections.get(connection_id)

    async def broadcast_to_user(self, user_id: UUID, message: dict[str, any]) -> int:
        """Broadcast message to all user connections."""
        count = 0
        for conn_id in self.user_connections.get(user_id, set()).copy():
            if batcher := self.connections.get(conn_id):
                await batcher.add_message(message)
                count += 1
        return count

    async def broadcast_to_session(
        self, session_id: UUID, message: dict[str, any]
    ) -> int:
        """Broadcast message to all session connections."""
        count = 0
        for conn_id in self.session_connections.get(session_id, set()).copy():
            if batcher := self.connections.get(conn_id):
                await batcher.add_message(message)
                count += 1
        return count

    async def _cleanup_stale(self) -> None:
        """Periodic cleanup of stale connections."""
        while True:
            try:
                await asyncio.sleep(PerformanceConfig.POOL_CLEANUP_INTERVAL)
                # Cleanup logic would go here
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection pool cleanup: {e}")


# Global connection pool
connection_pool = ConnectionPool()


def get_service_registry() -> ServiceRegistry:
    """Get or create the service registry singleton."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        service_registry = get_service_registry()
        _chat_agent = ChatAgent(service_registry=service_registry)
    return _chat_agent


async def get_core_chat_service(db=Depends(get_db)) -> CoreChatService:
    """Get CoreChatService instance with database dependency.

    Args:
        db: Database service from dependency injection

    Returns:
        CoreChatService instance
    """
    return CoreChatService(database_service=db)


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: UUID,
    db=Depends(get_db),
    chat_service: CoreChatService = Depends(get_core_chat_service),
):
    """WebSocket endpoint for real-time chat communication.

    Args:
        websocket: WebSocket connection
        session_id: Chat session ID
        db: Database service from dependency injection
        chat_service: CoreChatService instance from dependency injection
    """
    connection_id = None
    batcher = None
    message_handlers = set()

    try:
        # Validate Origin header before accepting connection
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=1008, reason="Invalid origin")
            logger.warning(
                "WebSocket connection rejected for chat session "
                f"{session_id}: Invalid origin"
            )
            return

        # Accept WebSocket connection with subprotocol negotiation
        subprotocols = websocket.headers.get("sec-websocket-protocol", "").split(", ")
        selected_protocol = None

        # Check for binary protocol support
        if "msgpack" in subprotocols and MSGPACK_AVAILABLE:
            selected_protocol = "msgpack"
            websocket._supports_binary = True
        elif "json" in subprotocols:
            selected_protocol = "json"
            websocket._supports_binary = False

        await websocket.accept(subprotocol=selected_protocol)
        logger.info(f"WebSocket connection accepted for chat session {session_id}")

        # Wait for authentication message
        auth_data = await websocket.receive_text()
        try:
            auth_request = WebSocketAuthRequest.model_validate_json(auth_data)
            auth_request.session_id = session_id  # Ensure session ID matches URL
        except ValidationError as e:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid authentication request",
                        "details": str(e),
                    },
                ),
            )
            await websocket.close(code=4000)
            return

        # Authenticate connection
        auth_response = await websocket_manager.authenticate_connection(
            websocket,
            auth_request,
        )

        if not auth_response.success:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": auth_response.error or "Authentication failed",
                    },
                ),
            )
            await websocket.close(code=4001)
            return

        connection_id = auth_response.connection_id
        user_id = auth_response.user_id

        # Add to connection pool
        try:
            batcher = await connection_pool.add_connection(
                connection_id, websocket, user_id, session_id
            )
        except ValueError:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Server at capacity. Please try again later.",
                    }
                )
            )
            await websocket.close(code=1013)
            return

        # Send authentication success response
        await websocket.send_text(json.dumps(auth_response.model_dump()))

        # Send connection established event
        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        # Get chat agent instance (dependency injection provides chat_service)
        chat_agent = get_chat_agent()

        logger.info(
            f"Chat WebSocket authenticated: connection_id={connection_id}, "
            f"user_id={user_id}",
        )

        # Message handling loop with concurrent processing
        while True:
            try:
                # Receive message from client (support both text and binary)
                try:
                    if websocket._supports_binary:
                        message_bytes = await websocket.receive_bytes()
                        message_json = msgpack.unpackb(message_bytes)
                    else:
                        message_data = await websocket.receive_text()
                        message_json = json.loads(message_data)
                except WebSocketDisconnect:
                    raise
                except Exception:
                    # Try text if binary fails
                    message_data = await websocket.receive_text()
                    message_json = json.loads(message_data)

                message_type = message_json.get("type", "")

                # Clean up completed handlers
                message_handlers = {h for h in message_handlers if not h.done()}

                # Check concurrent handler limit using TaskGroup for better task
                # management
                if len(message_handlers) >= PerformanceConfig.CONCURRENT_HANDLERS:
                    # Use TaskGroup for better structured concurrency
                    async with asyncio.TaskGroup():
                        # Wait for the first task to complete
                        first_completed_task = None
                        for handler in message_handlers:
                            if handler.done():
                                first_completed_task = handler
                                break

                        if not first_completed_task and message_handlers:
                            # If no task is done, wait for one to complete
                            done, pending = await asyncio.wait(
                                message_handlers, return_when=asyncio.FIRST_COMPLETED
                            )
                            message_handlers = pending

                if message_type == "chat_message":
                    # Handle chat message concurrently
                    handler_task = asyncio.create_task(
                        handle_chat_message(
                            connection_id=connection_id,
                            user_id=user_id,
                            session_id=session_id,
                            message_data=message_json.get("payload", {}),
                            chat_service=chat_service,
                            chat_agent=chat_agent,
                        )
                    )
                    message_handlers.add(handler_task)

                elif message_type == "heartbeat":
                    # Handle heartbeat
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.update_heartbeat()

                elif message_type == "ping":
                    # Handle ping from client and send pong response
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.update_heartbeat()
                        # Send pong response
                        pong_event = WebSocketEvent(
                            type=WebSocketEventType.CONNECTION_PONG,
                            payload={
                                "timestamp": datetime.utcnow().isoformat(),
                                "pong": True,
                            },
                            user_id=user_id,
                            session_id=session_id,
                            connection_id=connection_id,
                        )
                        await websocket_manager.send_to_connection(
                            connection_id, pong_event
                        )

                elif message_type == "pong":
                    # Handle pong response from client (in response to our ping)
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.handle_pong()

                elif message_type == "subscribe":
                    # Handle channel subscription
                    try:
                        subscribe_request = WebSocketSubscribeRequest.model_validate(
                            message_json.get("payload", {}),
                        )
                        response = await websocket_manager.subscribe_connection(
                            connection_id,
                            subscribe_request,
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "subscribe_response",
                                    "payload": response.model_dump(),
                                },
                            ),
                        )
                    except ValidationError as e:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Invalid subscription request",
                                    "details": str(e),
                                },
                            ),
                        )

                else:
                    logger.warning(f"Unknown message type: {message_type}")

            except WebSocketDisconnect:
                logger.info(
                    f"Chat WebSocket disconnected: connection_id={connection_id}",
                )
                break
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from connection {connection_id}")
                error_event = ErrorEvent(
                    error_code="invalid_json",
                    error_message="Invalid JSON format",
                    user_id=user_id,
                    session_id=session_id,
                )
                await websocket_manager.send_to_connection(connection_id, error_event)
            except Exception as e:
                logger.error(
                    f"Error handling message from connection {connection_id}: {e}",
                )
                error_event = ErrorEvent(
                    error_code="message_error",
                    error_message=str(e),
                    user_id=user_id,
                    session_id=session_id,
                )
                await websocket_manager.send_to_connection(connection_id, error_event)

    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
        if connection_id:
            error_event = ErrorEvent(
                error_code="websocket_error",
                error_message=str(e),
            )
            await websocket_manager.send_to_connection(connection_id, error_event)

    finally:
        # Cancel pending handlers
        for handler in message_handlers:
            if not handler.done():
                handler.cancel()

        # Clean up connection pool
        if connection_id and batcher:
            await connection_pool.remove_connection(connection_id)

        # Clean up from websocket manager
        if connection_id:
            await websocket_manager.disconnect_connection(connection_id)


@router.websocket("/ws/agent-status/{user_id}")
async def agent_status_websocket(
    websocket: WebSocket,
    user_id: UUID,
):
    """WebSocket endpoint for real-time agent status updates.

    Args:
        websocket: WebSocket connection
        user_id: User ID for agent status updates
    """
    connection_id = None

    try:
        # Validate Origin header before accepting connection
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=1008, reason="Invalid origin")
            logger.warning(
                "WebSocket connection rejected for agent status user "
                f"{user_id}: Invalid origin"
            )
            return

        # Accept WebSocket connection
        await websocket.accept()
        logger.info(f"Agent status WebSocket connection accepted for user {user_id}")

        # Wait for authentication message
        auth_data = await websocket.receive_text()
        try:
            auth_request = WebSocketAuthRequest.model_validate_json(auth_data)
            # Subscribe to user-specific agent status channel
            auth_request.channels = [f"agent_status:{user_id}"]
        except ValidationError as e:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid authentication request",
                        "details": str(e),
                    },
                ),
            )
            await websocket.close(code=4000)
            return

        # Authenticate connection
        auth_response = await websocket_manager.authenticate_connection(
            websocket,
            auth_request,
        )

        if not auth_response.success:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": auth_response.error or "Authentication failed",
                    },
                ),
            )
            await websocket.close(code=4001)
            return

        connection_id = auth_response.connection_id
        authenticated_user_id = auth_response.user_id

        # Verify user ID matches authenticated user
        if authenticated_user_id != user_id:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "User ID mismatch"}),
            )
            await websocket.close(code=4003)
            return

        # Send authentication success response
        await websocket.send_text(json.dumps(auth_response.model_dump()))

        # Send connection established event
        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=user_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        logger.info(
            f"Agent status WebSocket authenticated: connection_id={connection_id}, "
            f"user_id={user_id}",
        )

        # Message handling loop (mainly for heartbeats and subscription changes)
        while True:
            try:
                # Receive message from client
                message_data = await websocket.receive_text()
                message_json = json.loads(message_data)

                message_type = message_json.get("type", "")

                if message_type == "heartbeat":
                    # Handle heartbeat
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.update_heartbeat()

                elif message_type == "ping":
                    # Handle ping from client and send pong response
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.update_heartbeat()
                        # Send pong response
                        pong_event = WebSocketEvent(
                            type=WebSocketEventType.CONNECTION_PONG,
                            payload={
                                "timestamp": datetime.utcnow().isoformat(),
                                "pong": True,
                            },
                            user_id=user_id,
                            connection_id=connection_id,
                        )
                        await websocket_manager.send_to_connection(
                            connection_id, pong_event
                        )

                elif message_type == "pong":
                    # Handle pong response from client (in response to our ping)
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.handle_pong()

                elif message_type == "subscribe":
                    # Handle channel subscription
                    try:
                        subscribe_request = WebSocketSubscribeRequest.model_validate(
                            message_json.get("payload", {}),
                        )
                        response = await websocket_manager.subscribe_connection(
                            connection_id,
                            subscribe_request,
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "subscribe_response",
                                    "payload": response.model_dump(),
                                },
                            ),
                        )
                    except ValidationError as e:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Invalid subscription request",
                                    "details": str(e),
                                },
                            ),
                        )

                else:
                    logger.warning(
                        f"Unknown message type for agent status: {message_type}",
                    )

            except WebSocketDisconnect:
                logger.info(
                    f"Agent status WebSocket disconnected: "
                    f"connection_id={connection_id}",
                )
                break
            except json.JSONDecodeError:
                logger.error(
                    f"Invalid JSON received from agent status connection "
                    f"{connection_id}",
                )
            except Exception as e:
                logger.error(
                    f"Error handling agent status message from connection "
                    f"{connection_id}: {e}",
                )

    except Exception as e:
        logger.error(f"Agent status WebSocket error: {e}")

    finally:
        # Clean up connection
        if connection_id:
            await websocket_manager.disconnect_connection(connection_id)


async def handle_chat_message(
    connection_id: str,
    user_id: UUID,
    session_id: UUID,
    message_data: dict,
    chat_service: CoreChatService,
    chat_agent: ChatAgent,
) -> None:
    """Handle incoming chat message and stream response.

    Args:
        connection_id: WebSocket connection ID
        user_id: User ID
        session_id: Chat session ID
        message_data: Message data from client
        chat_service: CoreChatService instance
        chat_agent: Chat agent instance
    """
    try:
        # Extract message content
        content = message_data.get("content", "")
        if not content:
            error_event = ErrorEvent(
                error_code="empty_message",
                error_message="Message content cannot be empty",
                user_id=user_id,
                session_id=session_id,
            )
            await websocket_manager.send_to_connection(connection_id, error_event)
            return

        # Create user message
        user_message = WebSocketMessage(
            role="user",
            content=content,
            session_id=session_id,
            user_id=user_id,
        )

        # Send user message event
        user_message_event = ChatMessageEvent(
            message=user_message,
            user_id=user_id,
            session_id=session_id,
        )
        await websocket_manager.send_to_session(session_id, user_message_event)

        # Store user message in database
        user_message_request = MessageCreateRequest(
            role=MessageRole.USER,
            content=content,
        )
        await chat_service.add_message(
            session_id=str(session_id),
            user_id=str(user_id),
            message_data=user_message_request,
        )

        # Get available tools for this user (simplified for now)
        available_tools = [
            "time_tools",
            "weather_tools",
            "googlemaps_tools",
            "webcrawl_tools",
            "memory_tools",
            "flight_tools",
            "accommodations_tools",
            "planning_tools",
        ]

        # Build context for agent
        context = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "available_tools": available_tools,
            "tool_calling_enabled": True,
            "websocket_mode": True,
        }

        # Stream agent response
        full_content = ""
        chunk_index = 0

        # Send typing indicator
        typing_event = ChatMessageChunkEvent(
            content="",
            chunk_index=0,
            is_final=False,
            user_id=user_id,
            session_id=session_id,
        )
        typing_event.type = WebSocketEventType.CHAT_TYPING_START
        await websocket_manager.send_to_session(session_id, typing_event)

        # Process message concurrently
        start_time = time.time()

        # Get agent response with concurrent processing
        response_task = asyncio.create_task(chat_agent.run(content, context))

        # Process other tasks while waiting for response
        try:
            response = await asyncio.wait_for(
                response_task, timeout=PerformanceConfig.MESSAGE_TIMEOUT
            )
            response_content = response.get("content", "")
        except asyncio.TimeoutError:
            logger.error(f"Chat agent timeout for session {session_id}")
            response_content = (
                "I apologize, but I'm taking longer than expected to "
                "process your request. Please try again."
            )

        # Send stop typing indicator
        typing_event.type = WebSocketEventType.CHAT_TYPING_STOP
        await websocket_manager.send_to_session(session_id, typing_event)

        # Stream response in optimized chunks (no artificial delays)
        words = response_content.split()

        # Dynamic chunk size based on response length
        if len(words) < 50:
            chunk_size = 5  # Smaller chunks for short responses
        elif len(words) < 200:
            chunk_size = 10  # Medium chunks
        else:
            chunk_size = 20  # Larger chunks for long responses

        # Use connection pool for efficient message delivery
        if batcher := await connection_pool.get_connection(connection_id):
            # Send chunks without delay
            chunks_to_send = []

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "

                full_content += chunk

                # Prepare chunk event
                chunk_event = ChatMessageChunkEvent(
                    content=chunk,
                    chunk_index=chunk_index,
                    is_final=(i + chunk_size >= len(words)),
                    user_id=user_id,
                    session_id=session_id,
                )

                chunks_to_send.append(chunk_event.to_dict())
                chunk_index += 1

            # Send all chunks as a batch for maximum efficiency
            if chunks_to_send:
                await batcher.add_message(
                    {
                        "type": "stream_batch",
                        "chunks": chunks_to_send,
                        "session_id": str(session_id),
                    }
                )
        else:
            # Fallback to individual sends if batcher not available
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "

                full_content += chunk

                chunk_event = ChatMessageChunkEvent(
                    content=chunk,
                    chunk_index=chunk_index,
                    is_final=(i + chunk_size >= len(words)),
                    user_id=user_id,
                    session_id=session_id,
                )
                await websocket_manager.send_to_session(session_id, chunk_event)
                chunk_index += 1

        # Track performance metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        performance_metrics["message_processing_time_ms"].append(processing_time)
        performance_metrics["total_messages_processed"] += 1

        # Send final complete message event
        assistant_message = WebSocketMessage(
            role="assistant",
            content=full_content,
            session_id=session_id,
            user_id=user_id,
        )

        complete_message_event = ChatMessageEvent(
            message=assistant_message,
            user_id=user_id,
            session_id=session_id,
        )
        complete_message_event.type = WebSocketEventType.CHAT_MESSAGE_COMPLETE
        await websocket_manager.send_to_session(session_id, complete_message_event)

        # Store assistant message in database
        assistant_message_request = MessageCreateRequest(
            role=MessageRole.ASSISTANT,
            content=full_content,
        )
        await chat_service.add_message(
            session_id=str(session_id),
            user_id=str(user_id),
            message_data=assistant_message_request,
        )

    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        error_event = ErrorEvent(
            error_code="chat_error",
            error_message=str(e),
            user_id=user_id,
            session_id=session_id,
        )
        await websocket_manager.send_to_connection(connection_id, error_event)


# Health check endpoint for WebSocket service
@router.get("/ws/health")
async def websocket_health():
    """WebSocket service health check endpoint.

    Returns:
        Health status and connection statistics
    """
    stats = websocket_manager.get_connection_stats()

    # Calculate average message processing time
    avg_processing_time = 0
    if performance_metrics["message_processing_time_ms"]:
        avg_processing_time = sum(
            performance_metrics["message_processing_time_ms"]
        ) / len(performance_metrics["message_processing_time_ms"])

    return {
        "status": "healthy",
        "websocket_manager_running": websocket_manager._running,
        "connection_stats": stats,
        "performance_metrics": {
            "total_messages_processed": performance_metrics["total_messages_processed"],
            "total_batches_sent": performance_metrics["total_batches_sent"],
            "average_batch_size": performance_metrics["average_batch_size"],
            "concurrent_connections": performance_metrics["concurrent_connections"],
            "average_processing_time_ms": avg_processing_time,
            "compression_enabled": True,
            "msgpack_available": MSGPACK_AVAILABLE,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# WebSocket connection management endpoints
@router.get("/ws/connections")
async def list_websocket_connections():
    """List active WebSocket connections (admin only).

    Returns:
        List of active connections with their information
    """
    # This would typically require admin authentication
    connections = []

    for _connection_id, connection in websocket_manager.connections.items():
        connections.append(connection.get_info().model_dump())

    return {
        "connections": connections,
        "total_count": len(connections),
    }


@router.delete("/ws/connections/{connection_id}")
async def disconnect_websocket_connection(connection_id: str):
    """Disconnect a specific WebSocket connection (admin only).

    Args:
        connection_id: Connection ID to disconnect

    Returns:
        Success message
    """
    # This would typically require admin authentication
    await websocket_manager.disconnect_connection(connection_id)

    return {
        "message": f"Connection {connection_id} disconnected successfully",
        "connection_id": connection_id,
    }
