"""WebSocket router for TripSage API.

This module provides WebSocket endpoints for real-time communication,
including chat streaming, agent status updates, and live user feedback.
"""

# pylint: disable=too-many-lines

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import Field, ValidationError

from tripsage.agents.chat import ChatAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage.api.core.config import get_settings
from tripsage.api.core.dependencies import get_db, get_websocket_manager_dep
from tripsage_core.models.schemas_common.chat import (
    ChatMessage as WebSocketMessage,
    MessageRole as ChatMessageRole,
)
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
    MessageCreateRequest,
)
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthRequest,
)
from tripsage_core.services.infrastructure.websocket_connection_service import (
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketMessageLimits,
    WebSocketSubscribeRequest,
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
    """Chat message WebSocket event."""

    type: str = Field(default=WebSocketEventType.CHAT_MESSAGE, description="Event type")
    message: WebSocketMessage


class ChatMessageChunkEvent(WebSocketEvent):
    """Chat message chunk WebSocket event."""

    type: str = Field(default=WebSocketEventType.CHAT_TYPING, description="Event type")
    content: str
    chunk_index: int = 0
    is_final: bool = False


class ConnectionEvent(WebSocketEvent):
    """Connection established WebSocket event."""

    type: str = Field(
        default=WebSocketEventType.CONNECTION_ESTABLISHED, description="Event type"
    )
    status: str = Field(..., description="Connection status")


class ErrorEvent(WebSocketEvent):
    """Connection error WebSocket event."""

    type: str = Field(
        default=WebSocketEventType.CONNECTION_ERROR, description="Event type"
    )
    error_code: str
    error_message: str


logger = logging.getLogger(__name__)

router = APIRouter()

# Message size limits for incoming messages
message_limits = WebSocketMessageLimits()


@dataclass(slots=True)
class MessageContext:
    """Context passed to message handlers."""

    websocket: WebSocket
    connection_id: str
    user_id: UUID | None
    session_id: UUID | None
    chat_service: CoreChatService | None = None
    chat_agent: ChatAgent | None = None


MessageHandler = Callable[[MessageContext, dict[str, Any]], Awaitable[None]]


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
                "Message size exceeds limit for type '%s': %s > %s",
                message_type,
                message_size,
                max_size,
            )
            return False
        return True
    except Exception:
        logger.exception("Error validating message size")
        return True  # Allow message if validation fails


def validate_and_parse_message(message_data: str) -> tuple[bool, dict[str, Any], str]:
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
        logger.warning("Message validation failed: %s", e)
        return False, {}, str(e)
    except Exception:
        logger.exception("Unexpected error validating message")
        return False, {}, "Message validation error"


def _parse_uuid(value: Any) -> UUID | None:
    """Parse a value into a UUID if possible."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid UUID format") from exc


def build_auth_request(
    auth_payload: dict[str, Any],
    *,
    default_channels: list[str] | None = None,
) -> WebSocketAuthRequest:
    """Build a core WebSocketAuthRequest from validated payload."""
    token = auth_payload.get("token", "")
    session_id = _parse_uuid(auth_payload.get("session_id"))
    channels_raw = auth_payload.get("channels") or []
    if not isinstance(channels_raw, list):
        raise TypeError("Channels must be provided as a list")

    channels: list[str] = []
    for channel in channels_raw:
        if not isinstance(channel, str):
            raise TypeError("Channel names must be strings")
        channels.append(channel)

    if not channels and default_channels:
        channels = list(default_channels)

    return WebSocketAuthRequest(
        token=token,
        session_id=session_id,
        channels=channels,
    )


# Services for test compatibility - tests expect these attributes to exist
auth_service = None  # resolved per-request via DI
chat_service: CoreChatService | None = None
MessageRole = ChatMessageRole


def serialize_connection(connection: WebSocketConnection) -> dict[str, Any]:
    """Serialize a WebSocketConnection for API responses."""
    state_value = getattr(connection.state, "value", str(connection.state))
    connected_at = getattr(connection, "connected_at", None)
    last_heartbeat = getattr(connection, "last_heartbeat", None)
    subscribed_channels = getattr(connection, "subscribed_channels", [])
    return {
        "connection_id": connection.connection_id,
        "user_id": str(connection.user_id) if connection.user_id else None,
        "session_id": str(connection.session_id) if connection.session_id else None,
        "state": state_value,
        "connected_at": connected_at.isoformat()
        if isinstance(connected_at, datetime)
        else None,
        "last_heartbeat": last_heartbeat.isoformat()
        if isinstance(last_heartbeat, datetime)
        else None,
        "subscribed_channels": sorted(subscribed_channels)
        if isinstance(subscribed_channels, (set, list, tuple))
        else [],
        "client_ip": getattr(connection, "client_ip", None),
        "user_agent": getattr(connection, "user_agent", None),
    }


async def _send_error_event(
    ctx: MessageContext,
    error_code: str,
    error_message: str,
) -> None:
    """Send a structured error event to the connection."""
    error_event = ErrorEvent(
        error_code=error_code,
        error_message=error_message,
        user_id=ctx.user_id,
        session_id=ctx.session_id,
    )
    ws_mgr = await get_websocket_manager_dep()  # type: ignore[misc]
    await ws_mgr.send_to_connection(ctx.connection_id, error_event)


async def _handle_heartbeat(ctx: MessageContext, _message: dict[str, Any]) -> None:
    """Update heartbeat timestamp for the connection."""
    connection = websocket_manager.connections.get(ctx.connection_id)
    if connection:
        connection.update_heartbeat()


async def _handle_ping(ctx: MessageContext, _message: dict[str, Any]) -> None:
    """Respond to ping with pong and update heartbeat."""
    await _handle_heartbeat(ctx, _message)
    pong_event = WebSocketEvent(
        type=WebSocketEventType.CONNECTION_PONG,
        payload={"timestamp": datetime.now(UTC).isoformat(), "pong": True},
        user_id=ctx.user_id,
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
    )
    await websocket_manager.send_to_connection(ctx.connection_id, pong_event)


async def _handle_pong(ctx: MessageContext, _message: dict[str, Any]) -> None:
    """Handle pong response from the client."""
    connection = websocket_manager.connections.get(ctx.connection_id)
    if connection:
        connection.handle_pong()


async def _handle_subscribe(ctx: MessageContext, message: dict[str, Any]) -> None:
    """Subscribe connection to channels provided in the payload."""
    payload = message.get("payload", {})
    try:
        subscribe_request = WebSocketSubscribeRequest.model_validate(payload)
    except ValidationError as exc:
        await _send_error_event(ctx, "invalid_subscription_request", str(exc))
        return

    response = await websocket_manager.subscribe_connection(
        ctx.connection_id, subscribe_request
    )
    await ctx.websocket.send_text(
        json.dumps({"type": "subscribe_response", "payload": response.model_dump()})
    )


async def _handle_echo(ctx: MessageContext, message: dict[str, Any]) -> None:
    """Echo unknown messages back to the sender for debugging."""
    echo_event = WebSocketEvent(
        type="echo",
        payload=message,
        user_id=ctx.user_id,
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
    )
    await websocket_manager.send_to_connection(ctx.connection_id, echo_event)


async def _handle_chat_payload(ctx: MessageContext, message: dict[str, Any]) -> None:
    """Dispatch chat payload to the chat message handler."""
    await handle_chat_message(ctx, message.get("payload", {}))


async def _log_unknown_message(ctx: MessageContext, message: dict[str, Any]) -> None:
    """Log unknown message types for observability."""
    logger.warning(
        "Unknown message type on connection %s: %s",
        ctx.connection_id,
        message.get("type"),
    )


async def run_message_loop(
    ctx: MessageContext,
    handlers: dict[str, MessageHandler],
    *,
    fallback: MessageHandler | None = None,
) -> None:
    """Run the incoming message loop for a WebSocket connection."""
    while True:
        try:
            message_data = await ctx.websocket.receive_text()
            is_valid, message_json, error_msg = validate_and_parse_message(message_data)
            if not is_valid:
                await _send_error_event(ctx, "message_validation_failed", error_msg)
                continue

            message_type = message_json.get("type", "")
            handler = handlers.get(message_type)

            if handler:
                await handler(ctx, message_json)
            elif fallback:
                await fallback(ctx, message_json)

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected: connection_id=%s", ctx.connection_id)
            break
        except json.JSONDecodeError:
            logger.exception(
                "Invalid JSON received from connection %s", ctx.connection_id
            )
            await _send_error_event(
                ctx,
                "invalid_json",
                "Invalid JSON format",
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Error handling message from connection %s", ctx.connection_id
            )
            await _send_error_event(ctx, "message_error", str(exc))
            break


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

    parsed_origin = urlparse(origin)
    is_authorized = False

    if not parsed_origin.scheme or not parsed_origin.netloc:
        logger.exception("Invalid origin format: %s", origin)
    else:
        host = parsed_origin.hostname or ""
        host_normalized = host.lower()

        try:
            host_ascii = host_normalized.encode("idna").decode("ascii")
        except UnicodeError:
            logger.exception("Origin host could not be IDNA-encoded: %s", host)
            host_ascii = None

        host_is_ascii = host_ascii is not None and host_ascii == host_normalized
        if not host_is_ascii:
            logger.exception("Origin host contains non-ASCII characters: %s", host)
        else:
            canonical_origin = f"{parsed_origin.scheme.lower()}://{host_ascii}"
            if parsed_origin.port:
                canonical_origin = f"{canonical_origin}:{parsed_origin.port}"

            allowed_canonicals = set()
            for allowed_origin in settings.cors_origins:
                if allowed_origin == "*":
                    continue
                allowed_parsed = urlparse(allowed_origin)
                if not allowed_parsed.scheme or not allowed_parsed.hostname:
                    continue
                allowed_host_ascii = (
                    allowed_parsed.hostname.lower().encode("idna").decode("ascii")
                )
                allowed_canonical = (
                    f"{allowed_parsed.scheme.lower()}://{allowed_host_ascii}"
                )
                if allowed_parsed.port:
                    allowed_canonical = f"{allowed_canonical}:{allowed_parsed.port}"
                allowed_canonicals.add(allowed_canonical)

            if canonical_origin in allowed_canonicals:
                logger.info("WebSocket connection from authorized origin: %s", origin)
                is_authorized = True
            elif "*" in settings.cors_origins:
                logger.warning(
                    "Wildcard CORS origin detected - allowing all origins (insecure)"
                )
                is_authorized = True
            else:
                logger.exception(
                    "WebSocket connection rejected from unauthorized origin: %s",
                    origin,
                )

    return is_authorized


# Global chat agent instance
_chat_agent = None
_service_registry = None


def get_service_registry() -> ServiceRegistry:
    """Get or create the service registry singleton."""
    global _service_registry  # pylint: disable=global-statement
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton."""
    global _chat_agent  # pylint: disable=global-statement
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
    connection_id: str | None = None
    ctx: MessageContext | None = None

    try:
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=4003, reason="Unauthorized origin")
            return

        await websocket.accept()
        logger.info("Generic WebSocket connection accepted")

        auth_data = await websocket.receive_text()
        try:
            validated_auth = WebSocketMessageValidator.validate_message(auth_data)
            auth_dict = (
                validated_auth.model_dump()
                if hasattr(validated_auth, "model_dump")
                else validated_auth.dict()
            )
            auth_request = build_auth_request(auth_dict)
        except (ValueError, ValidationError) as exc:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid authentication request",
                        "details": str(exc),
                    }
                )
            )
            await websocket.close(code=4000)
            return

        auth_response = await websocket_manager.authenticate_connection(
            websocket, auth_request
        )

        if not auth_response.success:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": auth_response.error or "Authentication failed",
                    }
                )
            )
            await websocket.close(code=4001)
            return

        connection_id = auth_response.connection_id
        ctx = MessageContext(
            websocket=websocket,
            connection_id=connection_id,
            user_id=auth_response.user_id,
            session_id=auth_response.session_id,
        )

        auth_response_dict = auth_response.model_dump()
        if auth_response_dict.get("user_id"):
            auth_response_dict["user_id"] = str(auth_response_dict["user_id"])
        if auth_response_dict.get("session_id"):
            auth_response_dict["session_id"] = str(auth_response_dict["session_id"])
        await websocket.send_text(json.dumps(auth_response_dict))

        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=auth_response.user_id,
            session_id=auth_response.session_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        handlers: dict[str, MessageHandler] = {
            "heartbeat": _handle_heartbeat,
            "ping": _handle_ping,
            "pong": _handle_pong,
            "subscribe": _handle_subscribe,
        }

        await run_message_loop(ctx, handlers, fallback=_handle_echo)

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Generic WebSocket error")
        if ctx is not None:
            await _send_error_event(ctx, "websocket_error", str(exc))

    finally:
        if connection_id:
            await websocket_manager.disconnect_connection(connection_id)


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: UUID,
    chat_service: CoreChatService = Depends(get_core_chat_service),
):
    """WebSocket endpoint for real-time chat communication.

    Args:
        websocket: WebSocket connection
        session_id: Chat session ID
        db: Database service from dependency injection
        chat_service: CoreChatService instance from dependency injection
    """
    connection_id: str | None = None
    ctx: MessageContext | None = None

    try:
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=4003, reason="Unauthorized origin")
            return

        await websocket.accept()
        logger.info("WebSocket connection accepted for chat session %s", session_id)

        auth_data = await websocket.receive_text()
        try:
            validated_auth = WebSocketMessageValidator.validate_message(auth_data)
            auth_dict = (
                validated_auth.model_dump()
                if hasattr(validated_auth, "model_dump")
                else validated_auth.dict()
            )
            request_from_payload = build_auth_request(auth_dict)
            if (
                request_from_payload.session_id is not None
                and request_from_payload.session_id != session_id
            ):
                raise ValueError("Session ID mismatch")

            auth_request = request_from_payload.model_copy(
                update={"session_id": session_id}
            )
        except (ValueError, ValidationError) as exc:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid authentication request",
                        "details": str(exc),
                    }
                )
            )
            await websocket.close(code=4000)
            return

        auth_response = await websocket_manager.authenticate_connection(
            websocket, auth_request
        )

        if not auth_response.success:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": auth_response.error or "Authentication failed",
                    }
                )
            )
            await websocket.close(code=4001)
            return

        connection_id = auth_response.connection_id
        user_id_optional = auth_response.user_id

        if user_id_optional is None:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "User ID mismatch",
                    }
                )
            )
            await websocket.close(code=4003)
            return

        assert isinstance(user_id_optional, UUID)
        user_id = cast(UUID, user_id_optional)

        auth_response_dict = auth_response.model_dump()
        if auth_response_dict.get("user_id"):
            auth_response_dict["user_id"] = str(auth_response_dict["user_id"])
        if auth_response_dict.get("session_id"):
            auth_response_dict["session_id"] = str(auth_response_dict["session_id"])
        await websocket.send_text(json.dumps(auth_response_dict))

        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        chat_agent = get_chat_agent()
        ctx = MessageContext(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
            chat_service=chat_service,
            chat_agent=chat_agent,
        )

        handlers: dict[str, MessageHandler] = {
            "chat_message": _handle_chat_payload,
            "heartbeat": _handle_heartbeat,
            "ping": _handle_ping,
            "pong": _handle_pong,
            "subscribe": _handle_subscribe,
        }

        await run_message_loop(ctx, handlers, fallback=_log_unknown_message)

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Chat WebSocket error")
        if ctx is not None:
            await _send_error_event(ctx, "websocket_error", str(exc))

    finally:
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
    connection_id: str | None = None
    ctx: MessageContext | None = None

    try:
        if not await validate_websocket_origin(websocket):
            await websocket.close(code=4003, reason="Unauthorized origin")
            return

        await websocket.accept()
        logger.info("Agent status WebSocket connection accepted for user %s", user_id)

        auth_data = await websocket.receive_text()
        try:
            validated_auth = WebSocketMessageValidator.validate_message(auth_data)
            auth_dict = (
                validated_auth.model_dump()
                if hasattr(validated_auth, "model_dump")
                else validated_auth.dict()
            )
            auth_request = build_auth_request(
                auth_dict,
                default_channels=[f"agent_status:{user_id}"],
            )
        except (ValueError, ValidationError) as exc:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid authentication request",
                        "details": str(exc),
                    }
                )
            )
            await websocket.close(code=4000)
            return

        auth_response = await websocket_manager.authenticate_connection(
            websocket, auth_request
        )

        if not auth_response.success:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": auth_response.error or "Authentication failed",
                    }
                )
            )
            await websocket.close(code=4001)
            return

        connection_id = auth_response.connection_id
        authenticated_user_id = auth_response.user_id

        if authenticated_user_id != user_id:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "User ID mismatch"}),
            )
            await websocket.close(code=4003)
            return

        ctx = MessageContext(
            websocket=websocket,
            connection_id=connection_id,
            user_id=authenticated_user_id,
            session_id=auth_response.session_id,
        )

        auth_response_dict = auth_response.model_dump()
        if auth_response_dict.get("user_id"):
            auth_response_dict["user_id"] = str(auth_response_dict["user_id"])
        if auth_response_dict.get("session_id"):
            auth_response_dict["session_id"] = str(auth_response_dict["session_id"])
        await websocket.send_text(json.dumps(auth_response_dict))

        connection_event = ConnectionEvent(
            status="connected",
            connection_id=connection_id,
            user_id=authenticated_user_id,
            session_id=auth_response.session_id,
        )
        await websocket_manager.send_to_connection(connection_id, connection_event)

        handlers: dict[str, MessageHandler] = {
            "heartbeat": _handle_heartbeat,
            "ping": _handle_ping,
            "pong": _handle_pong,
            "subscribe": _handle_subscribe,
        }

        await run_message_loop(ctx, handlers, fallback=_log_unknown_message)

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Agent status WebSocket error")
        if ctx is not None:
            await _send_error_event(ctx, "websocket_error", str(exc))

    finally:
        if connection_id:
            await websocket_manager.disconnect_connection(connection_id)


async def handle_chat_message(
    ctx: MessageContext, message_data: dict[str, Any]
) -> None:
    """Handle incoming chat message and stream agent response."""
    if ctx.chat_service is None or ctx.chat_agent is None:
        raise ValueError("Chat dependencies unavailable")

    if ctx.user_id is None or ctx.session_id is None:
        await _send_error_event(
            ctx,
            "chat_context_missing",
            "User or session not established",
        )
        return

    chat_service = ctx.chat_service
    chat_agent = ctx.chat_agent
    user_id = ctx.user_id
    session_id = ctx.session_id

    try:
        content = message_data.get("content", "")
        if not content:
            await _send_error_event(
                ctx,
                "empty_message",
                "Message content cannot be empty",
            )
            return

        sanitized_content = WebSocketMessageValidator.sanitize_message_content(content)

        user_message = WebSocketMessage(
            role=ChatMessageRole.USER,
            content=sanitized_content,
            tool_calls=None,
            timestamp=None,
            metadata=None,
        )

        user_message_event = ChatMessageEvent(
            type=WebSocketEventType.CHAT_MESSAGE,
            message=user_message,
            user_id=user_id,
            session_id=session_id,
        )
        await websocket_manager.send_to_session(session_id, user_message_event)

        user_message_request = MessageCreateRequest(
            role=ChatMessageRole.USER.value,
            content=sanitized_content,
            metadata=None,
            tool_calls=None,
        )
        await chat_service.add_message(
            session_id=str(session_id),
            user_id=str(user_id),
            message_data=user_message_request,
        )

        context = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "available_tools": [
                "time_tools",
                "weather_tools",
                "googlemaps_tools",
                "webcrawl_tools",
                "memory_tools",
                "flight_tools",
                "accommodations_tools",
                "planning_tools",
            ],
            "tool_calling_enabled": True,
            "websocket_mode": True,
        }

        full_content = ""

        typing_start_event = WebSocketEvent(
            type=WebSocketEventType.CHAT_TYPING_START,
            user_id=user_id,
            session_id=session_id,
            connection_id=ctx.connection_id,
        )
        await websocket_manager.send_to_session(session_id, typing_start_event)

        response = await chat_agent.run(
            sanitized_content,
            user_id=str(user_id),
            session_id=str(session_id),
            context=context,
        )
        response_content = response.get("content", "")

        typing_stop_event = WebSocketEvent(
            type=WebSocketEventType.CHAT_TYPING_STOP,
            user_id=user_id,
            session_id=session_id,
            connection_id=ctx.connection_id,
        )
        await websocket_manager.send_to_session(session_id, typing_stop_event)

        words = response_content.split()
        chunk_size = 3

        for chunk_index, i in enumerate(range(0, len(words), chunk_size)):
            chunk = " ".join(words[i : i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "

            full_content += chunk

            chunk_event = ChatMessageChunkEvent(
                type=WebSocketEventType.CHAT_TYPING,
                content=chunk,
                chunk_index=chunk_index,
                is_final=(i + chunk_size >= len(words)),
                user_id=user_id,
                session_id=session_id,
                connection_id=ctx.connection_id,
            )
            await websocket_manager.send_to_session(session_id, chunk_event)

            await asyncio.sleep(0.05)

        assistant_message = WebSocketMessage(
            role=ChatMessageRole.ASSISTANT,
            content=full_content,
            tool_calls=None,
            timestamp=None,
            metadata=None,
        )

        complete_message_event = ChatMessageEvent(
            type=WebSocketEventType.CHAT_MESSAGE_COMPLETE,
            message=assistant_message,
            user_id=user_id,
            session_id=session_id,
        )
        await websocket_manager.send_to_session(session_id, complete_message_event)

        assistant_message_request = MessageCreateRequest(
            role=ChatMessageRole.ASSISTANT.value,
            content=full_content,
            metadata=None,
            tool_calls=None,
        )
        await chat_service.add_message(
            session_id=str(session_id),
            user_id=str(user_id),
            message_data=assistant_message_request,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error handling chat message")
        await _send_error_event(ctx, "chat_error", str(exc))


@router.get("/ws/health")
async def websocket_health():
    """WebSocket service health check endpoint.

    Returns:
        Health status and connection statistics
    """
    ws_mgr = await get_websocket_manager_dep()  # type: ignore[misc]
    stats = ws_mgr.get_connection_stats()

    return {
        "status": "healthy",
        "websocket_manager_running": getattr(websocket_manager, "_running", False),
        "connection_stats": stats,
        "timestamp": datetime.now(UTC).isoformat(),
    }


# WebSocket connection management endpoints
@router.get("/ws/connections")
async def list_websocket_connections():
    """List active WebSocket connections (admin only)."""
    # This would typically require admin authentication
    connections = [
        serialize_connection(connection)
        for connection in ws_mgr.connections.values()
    ]

    return {"connections": connections, "total_count": len(connections)}


@router.delete("/ws/connections/{connection_id}")
async def disconnect_websocket_connection(connection_id: str):
    """Disconnect a specific WebSocket connection (admin only)."""
    # This would typically require admin authentication
    ws_mgr = await get_websocket_manager_dep()  # type: ignore[misc]
    await ws_mgr.disconnect_connection(connection_id)

    return {
        "message": f"Connection {connection_id} disconnected successfully",
        "connection_id": connection_id,
    }
