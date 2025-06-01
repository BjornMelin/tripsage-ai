"""WebSocket router for TripSage API.

This module provides WebSocket endpoints for real-time communication,
including chat streaming, agent status updates, and live user feedback.
"""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import Field, ValidationError

from tripsage.agents.chat import ChatAgent
from tripsage.api.core.dependencies import get_db
from tripsage.api.models.requests.websocket import (
    WebSocketAuthRequest,
    WebSocketSubscribeRequest,
)
from tripsage.services.core.chat_service import ChatService
from tripsage_core.models.schemas_common.chat import (
    ChatMessage as WebSocketMessage,
)
from tripsage_core.services.business.chat_service import MessageRole
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketEvent,
    WebSocketEventType,
    websocket_manager,
)


# Create event classes here temporarily until they are properly organized
class ChatMessageEvent(WebSocketEvent):
    message: WebSocketMessage


class ChatMessageChunkEvent(WebSocketEvent):
    content: str
    chunk_index: int = 0
    is_final: bool = False


class ConnectionEvent(WebSocketEvent):
    status: str = Field(..., description="Connection status")
    connection_id: str = Field(..., description="Connection ID")


class ErrorEvent(WebSocketEvent):
    error_code: str
    error_message: str


logger = logging.getLogger(__name__)

router = APIRouter()

# Global chat agent instance
_chat_agent = None


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: UUID,
):
    """WebSocket endpoint for real-time chat communication.

    Args:
        websocket: WebSocket connection
        session_id: Chat session ID
    """
    connection_id = None

    try:
        # Accept WebSocket connection
        await websocket.accept()
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

        # Create chat service with database session
        db_session = await get_db()
        chat_service = ChatService(db_session)
        chat_agent = get_chat_agent()

        logger.info(
            f"Chat WebSocket authenticated: connection_id={connection_id}, "
            f"user_id={user_id}",
        )

        # Message handling loop
        while True:
            try:
                # Receive message from client
                message_data = await websocket.receive_text()
                message_json = json.loads(message_data)

                message_type = message_json.get("type", "")

                if message_type == "chat_message":
                    # Handle chat message
                    await handle_chat_message(
                        connection_id=connection_id,
                        user_id=user_id,
                        session_id=session_id,
                        message_data=message_json.get("payload", {}),
                        chat_service=chat_service,
                        chat_agent=chat_agent,
                    )

                elif message_type == "heartbeat":
                    # Handle heartbeat
                    connection = websocket_manager.connections.get(connection_id)
                    if connection:
                        connection.update_heartbeat()

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
        # Clean up connection
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
    chat_service: ChatService,
    chat_agent: ChatAgent,
) -> None:
    """Handle incoming chat message and stream response.

    Args:
        connection_id: WebSocket connection ID
        user_id: User ID
        session_id: Chat session ID
        message_data: Message data from client
        chat_service: Chat service instance
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
        await chat_service.add_message(
            session_id=session_id,
            role="user",
            content=content,
            user_id=user_id,
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

        # Get agent response (this will be streaming in the future)
        response = await chat_agent.run_with_tools(content, context, available_tools)
        response_content = response.get("content", "")

        # Send stop typing indicator
        typing_event.type = WebSocketEventType.CHAT_TYPING_STOP
        await websocket_manager.send_to_session(session_id, typing_event)

        # Simulate streaming by splitting response into chunks
        words = response_content.split()
        chunk_size = 3  # Send 3 words at a time

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "

            full_content += chunk

            # Send chunk event
            chunk_event = ChatMessageChunkEvent(
                content=chunk,
                chunk_index=chunk_index,
                is_final=(i + chunk_size >= len(words)),
                user_id=user_id,
                session_id=session_id,
            )
            await websocket_manager.send_to_session(session_id, chunk_event)

            chunk_index += 1

            # Small delay to simulate streaming
            await asyncio.sleep(0.05)

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
        await chat_service.add_message(
            session_id=session_id,
            role="assistant",
            content=full_content,
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


# WebSocket manager lifecycle hooks
@router.on_event("startup")
async def start_websocket_manager():
    """Start the WebSocket manager on application startup."""
    await websocket_manager.start()
    logger.info("WebSocket manager started")


@router.on_event("shutdown")
async def stop_websocket_manager():
    """Stop the WebSocket manager on application shutdown."""
    await websocket_manager.stop()
    logger.info("WebSocket manager stopped")


# Health check endpoint for WebSocket service
@router.get("/ws/health")
async def websocket_health():
    """WebSocket service health check endpoint.

    Returns:
        Health status and connection statistics
    """
    stats = websocket_manager.get_connection_stats()

    return {
        "status": "healthy",
        "websocket_manager_running": websocket_manager._running,
        "connection_stats": stats,
        "timestamp": "2024-01-01T00:00:00Z",  # This would be current timestamp
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
