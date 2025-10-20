"""WebSocket router for TripSage API.

This module provides WebSocket endpoints for real-time communication,
including chat streaming, agent status updates, and live user feedback.
"""

import asyncio
import json
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import Field, ValidationError

from tripsage.agents.chat import ChatAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage.api.core.config import get_settings
from tripsage.api.core.dependencies import get_db
from tripsage.api.schemas.websocket import (
    WebSocketAuthRequest,
    WebSocketSubscribeRequest,
)
from tripsage_core.models.schemas_common.chat import ChatMessage as WebSocketMessage
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
    MessageCreateRequest,
    MessageRole,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketMessageLimits,
    websocket_manager,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)
from tripsage_core.services.infrastructure.websocket_validation import (
    WebSocketMessageValidator,
)


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

# Message size limits for incoming messages
message_limits = WebSocketMessageLimits()


def validate_incoming_message_size(
    message_data: str, message_type: str = "message"
) -> bool:
    """Validate incoming WebSocket message size.

    Args:
        message_data: Raw message data as string
        message_type: Type of message for size limit determination

    Returns:
        True if message size is valid, False otherwise
    """
    try:
        message_size = len(message_data.encode("utf-8"))
        max_size = message_limits.get_limit_for_message_type(message_type)

        if message_size > max_size:
            logger.warning(
                f"Message size exceeds limit for type '{message_type}': "
                f"{message_size} > {max_size}"
            )
            return False
        return True
    except Exception:
        logger.exception("Error validating message size")
        return True  # Allow message if validation fails


def validate_and_parse_message(message_data: str) -> tuple[bool, dict, str]:
    """Validate and parse incoming WebSocket message with comprehensive security checks.

    Args:
        message_data: Raw message data as string

    Returns:
        Tuple of (is_valid, parsed_message_dict, error_message)
    """
    try:
        # First validate message size
        if not validate_incoming_message_size(message_data, "message"):
            return False, {}, "Message too large"

        # Validate using Pydantic models
        validated_message = WebSocketMessageValidator.validate_message(message_data)

        # Convert back to dict for processing
        if hasattr(validated_message, "model_dump"):
            message_dict = validated_message.model_dump()
        else:
            message_dict = validated_message.dict()

        return True, message_dict, ""

    except ValueError as e:
        logger.warning(f"Message validation failed: {e}")
        return False, {}, str(e)
    except Exception:
        logger.exception("Unexpected error validating message")
        return False, {}, "Message validation error"


# Services for test compatibility - tests expect these attributes to exist
auth_service = websocket_manager.auth_service


# Mock chat service for test compatibility - create a placeholder since the actual
# chat service is dependency injected and tests need to patch this module attribute
class MockChatService:
    """Placeholder chat service for test compatibility."""


chat_service = MockChatService()


async def validate_websocket_origin(websocket: WebSocket) -> bool:
    """Validate WebSocket Origin header to prevent CSWSH attacks.

    Args:
        websocket: The WebSocket connection to validate

    Returns:
        True if origin is valid, False otherwise
    """
    settings = get_settings()
    origin = websocket.headers.get("origin")

    if origin is None:
        # Allow connections without Origin header for development/testing
        # In production, you might want to be more strict
        logger.warning("WebSocket connection attempted without Origin header")
        if settings.is_production:
            logger.exception(
                "Origin header missing in production - rejecting connection"
            )
            return False
        return True

    # Check if origin is in allowed CORS origins
    if origin in settings.cors_origins:
        logger.info(f"WebSocket connection from authorized origin: {origin}")
        return True

    # Additional check for wildcard origins if configured
    for allowed_origin in settings.cors_origins:
        if allowed_origin == "*":
            logger.warning(
                "Wildcard CORS origin detected - allowing all origins (insecure)"
            )
            return True

    logger.exception(
        f"WebSocket connection rejected from unauthorized origin: {origin}"
    )
    return False


# Global chat agent instance
_chat_agent = None
_service_registry = None


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


@router.websocket("/ws")
async def generic_websocket(websocket: WebSocket):
    """Generic WebSocket endpoint for testing and simple connections.

    This endpoint provides a minimal WebSocket connection for testing purposes.
    For production use, prefer the specific endpoints like /ws/chat/{session_id}.

    Args:
        websocket: WebSocket connection
    """
    connection_id = None

    try:
        # Validate Origin header before accepting connection (CSWSH protection)
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=4003, reason="Unauthorized origin")
            return

        # Accept WebSocket connection
        await websocket.accept()
        logger.info("Generic WebSocket connection accepted")

        # Wait for authentication message
        auth_data = await websocket.receive_text()

        # Validate authentication message using comprehensive validation
        try:
            # Use the new validation for auth messages
            validated_auth = WebSocketMessageValidator.validate_message(auth_data)
            if hasattr(validated_auth, "model_dump"):
                auth_dict = validated_auth.model_dump()
            else:
                auth_dict = validated_auth.dict()

            # Create WebSocketAuthRequest from validated data
            auth_request = WebSocketAuthRequest(
                token=auth_dict.get("token", ""),
                session_id=auth_dict.get("session_id"),
                channels=auth_dict.get("channels", []),
            )
        except (ValueError, ValidationError) as e:
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
        auth_response_dict = auth_response.model_dump()
        # Convert UUID fields to strings for JSON serialization
        if auth_response_dict.get("user_id"):
            auth_response_dict["user_id"] = str(auth_response_dict["user_id"])
        if auth_response_dict.get("session_id"):
            auth_response_dict["session_id"] = str(auth_response_dict["session_id"])
        await websocket.send_text(json.dumps(auth_response_dict))

        # Send connection established event
        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=user_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        logger.info(
            (
                f"Generic WebSocket authenticated: connection_id={connection_id}, "
                f"user_id={user_id}"
            ),
        )

        # Basic message handling loop
        while True:
            try:
                # Receive message from client
                message_data = await websocket.receive_text()

                # Validate and parse message using comprehensive validation
                is_valid, message_json, error_msg = validate_and_parse_message(
                    message_data
                )
                if not is_valid:
                    error_event = ErrorEvent(
                        error_code="message_validation_failed",
                        error_message=error_msg,
                        user_id=user_id,
                    )
                    await websocket_manager.send_to_connection(
                        connection_id, error_event
                    )
                    continue

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

                elif message_type == "chat_message":
                    # Handle chat message and broadcast to session
                    payload = message_json.get("payload", {})
                    message_session_id = payload.get("session_id")
                    content = payload.get("content", "")

                    if message_session_id and content:
                        # Create chat message event
                        chat_event = WebSocketEvent(
                            type="chat_message",
                            payload={
                                "content": content,
                                "session_id": message_session_id,
                                "user_id": str(user_id),
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                            user_id=user_id,
                            connection_id=connection_id,
                        )
                        # Broadcast to session
                        await websocket_manager.send_to_session(
                            UUID(message_session_id), chat_event
                        )
                    else:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Invalid chat message format",
                                },
                            ),
                        )

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
                    # Echo back unknown messages for testing
                    echo_event = WebSocketEvent(
                        type="echo",
                        payload=message_json,
                        user_id=user_id,
                        connection_id=connection_id,
                    )
                    await websocket_manager.send_to_connection(
                        connection_id, echo_event
                    )

            except WebSocketDisconnect:
                logger.info(
                    f"Generic WebSocket disconnected: connection_id={connection_id}",
                )
                break
            except json.JSONDecodeError:
                logger.exception(
                    f"Invalid JSON received from connection {connection_id}"
                )
                error_event = ErrorEvent(
                    error_code="invalid_json",
                    error_message="Invalid JSON format",
                    user_id=user_id,
                )
                await websocket_manager.send_to_connection(connection_id, error_event)
            except Exception as e:
                logger.exception(
                    f"Error handling message from connection {connection_id}",
                )
                error_event = ErrorEvent(
                    error_code="message_error",
                    error_message=str(e),
                    user_id=user_id,
                )
                await websocket_manager.send_to_connection(connection_id, error_event)

    except Exception as e:
        logger.exception("Generic WebSocket error")
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

    try:
        # Validate Origin header before accepting connection (CSWSH protection)
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=4003, reason="Unauthorized origin")
            return

        # Accept WebSocket connection
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for chat session {session_id}")

        # Wait for authentication message
        auth_data = await websocket.receive_text()

        # Validate authentication message using comprehensive validation
        try:
            # Use the new validation for auth messages
            validated_auth = WebSocketMessageValidator.validate_message(auth_data)
            if hasattr(validated_auth, "model_dump"):
                auth_dict = validated_auth.model_dump()
            else:
                auth_dict = validated_auth.dict()

            # Create WebSocketAuthRequest from validated data
            auth_request = WebSocketAuthRequest(
                token=auth_dict.get("token", ""),
                session_id=session_id,  # Ensure session ID matches URL
                channels=auth_dict.get("channels", []),
            )
        except (ValueError, ValidationError) as e:
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
        auth_response_dict = auth_response.model_dump()
        # Convert UUID fields to strings for JSON serialization
        if auth_response_dict.get("user_id"):
            auth_response_dict["user_id"] = str(auth_response_dict["user_id"])
        if auth_response_dict.get("session_id"):
            auth_response_dict["session_id"] = str(auth_response_dict["session_id"])
        await websocket.send_text(json.dumps(auth_response_dict))

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
            (
                f"Chat WebSocket authenticated: connection_id={connection_id}, "
                f"user_id={user_id}"
            ),
        )

        # Message handling loop
        while True:
            try:
                # Receive message from client
                message_data = await websocket.receive_text()

                # Validate and parse message using comprehensive validation
                is_valid, message_json, error_msg = validate_and_parse_message(
                    message_data
                )
                if not is_valid:
                    error_event = ErrorEvent(
                        error_code="message_validation_failed",
                        error_message=error_msg,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    await websocket_manager.send_to_connection(
                        connection_id, error_event
                    )
                    continue

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
                logger.exception(
                    f"Invalid JSON received from connection {connection_id}"
                )
                error_event = ErrorEvent(
                    error_code="invalid_json",
                    error_message="Invalid JSON format",
                    user_id=user_id,
                    session_id=session_id,
                )
                await websocket_manager.send_to_connection(connection_id, error_event)
            except Exception as e:
                logger.exception(
                    f"Error handling message from connection {connection_id}",
                )
                error_event = ErrorEvent(
                    error_code="message_error",
                    error_message=str(e),
                    user_id=user_id,
                    session_id=session_id,
                )
                await websocket_manager.send_to_connection(connection_id, error_event)

    except Exception as e:
        logger.exception("Chat WebSocket error")
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
        # Validate Origin header before accepting connection (CSWSH protection)
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=4003, reason="Unauthorized origin")
            return

        # Accept WebSocket connection
        await websocket.accept()
        logger.info(f"Agent status WebSocket connection accepted for user {user_id}")

        # Wait for authentication message
        auth_data = await websocket.receive_text()

        # Validate authentication message using comprehensive validation
        try:
            # Use the new validation for auth messages
            validated_auth = WebSocketMessageValidator.validate_message(auth_data)
            if hasattr(validated_auth, "model_dump"):
                auth_dict = validated_auth.model_dump()
            else:
                auth_dict = validated_auth.dict()

            # Create WebSocketAuthRequest from validated data
            auth_request = WebSocketAuthRequest(
                token=auth_dict.get("token", ""),
                session_id=auth_dict.get("session_id"),
                channels=[
                    f"agent_status:{user_id}"
                ],  # Subscribe to user-specific channel
            )
        except (ValueError, ValidationError) as e:
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
        auth_response_dict = auth_response.model_dump()
        # Convert UUID fields to strings for JSON serialization
        if auth_response_dict.get("user_id"):
            auth_response_dict["user_id"] = str(auth_response_dict["user_id"])
        if auth_response_dict.get("session_id"):
            auth_response_dict["session_id"] = str(auth_response_dict["session_id"])
        await websocket.send_text(json.dumps(auth_response_dict))

        # Send connection established event
        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=user_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        logger.info(
            (
                f"Agent status WebSocket authenticated: connection_id={connection_id}, "
                f"user_id={user_id}"
            ),
        )

        # Message handling loop (mainly for heartbeats and subscription changes)
        while True:
            try:
                # Receive message from client
                message_data = await websocket.receive_text()

                # Validate and parse message using comprehensive validation
                is_valid, message_json, error_msg = validate_and_parse_message(
                    message_data
                )
                if not is_valid:
                    logger.warning(
                        f"Message validation failed for agent status connection "
                        f"{connection_id}: {error_msg}"
                    )
                    continue

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
                    f"connection_id={connection_id}"
                )
                break
            except json.JSONDecodeError:
                logger.exception(
                    f"Invalid JSON received from agent status connection "
                    f"{connection_id}"
                )
            except Exception:
                logger.exception(
                    f"Error handling agent status message from connection "
                    f"{connection_id}"
                )

    except Exception:
        logger.exception("Agent status WebSocket error")

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
        # Extract and sanitize message content
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

        # Sanitize content to prevent XSS and injection attacks
        sanitized_content = WebSocketMessageValidator.sanitize_message_content(content)

        # Create user message with sanitized content
        user_message = WebSocketMessage(
            role="user",
            content=sanitized_content,
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

        # Store user message in database with sanitized content
        user_message_request = MessageCreateRequest(
            role=MessageRole.USER,
            content=sanitized_content,
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

        # Get agent response (this will be streaming in the future)
        response = await chat_agent.run(content, context)
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
        logger.exception("Error handling chat message")
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

    for connection in websocket_manager.connections.values():
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
