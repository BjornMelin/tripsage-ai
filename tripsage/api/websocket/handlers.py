"""Inbound WebSocket message handlers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from tripsage.api.websocket.context import ConnectionContext
from tripsage.api.websocket.exceptions import WebSocketMessageError
from tripsage.api.websocket.protocol import (
    ChatMessageCompleteEvent,
    ChatMessageEvent,
    ChatTypingEvent,
    ConnectionEvent,
    ErrorEvent,
    PongEvent,
)
from tripsage.api.websocket.validators import parse_and_validate
from tripsage_core.models.schemas_common.chat import (
    ChatMessage,
    MessageRole,
)
from tripsage_core.services.business.chat_service import MessageCreateRequest
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthResponse,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketSubscribeRequest,
)
from tripsage_core.services.infrastructure.websocket_validation import (
    WebSocketChatMessage,
    WebSocketHeartbeatMessage,
    WebSocketMessageValidator,
    WebSocketSubscribeMessage,
)


MessageHandler = Callable[[ConnectionContext, object], Awaitable[None]]


def attach_context_meta(event: ConnectionEvent, context: ConnectionContext) -> None:
    """Attach standard connection metadata to an event payload."""
    event.payload.update(context.as_payload())


async def handle_heartbeat(
    ctx: ConnectionContext, message: WebSocketHeartbeatMessage
) -> None:
    """Record heartbeat reception for the connection."""
    connection = ctx.manager.connections.get(ctx.connection_id)
    if connection:
        connection.update_heartbeat()
        connection.last_activity = datetime.now().timestamp()


async def handle_ping(
    ctx: ConnectionContext, message: WebSocketHeartbeatMessage
) -> None:
    """Respond to a ping message with a structured pong event."""
    await handle_heartbeat(ctx, message)
    pong_event = PongEvent(
        user_id=context_user_id(ctx),
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
        payload={
            "timestamp": datetime.now(UTC).isoformat(),
            "ping_id": message.ping_id,
        },
    )
    await ctx.send_event(pong_event)


async def handle_pong(
    ctx: ConnectionContext, message: WebSocketHeartbeatMessage
) -> None:
    """Mark pong acknowledgment on the connection."""
    connection = ctx.manager.connections.get(ctx.connection_id)
    if connection:
        connection.handle_pong()


async def handle_subscribe(
    ctx: ConnectionContext, message: WebSocketSubscribeMessage
) -> None:
    """Subscribe the connection to requested channels."""
    request = WebSocketSubscribeRequest.model_validate(message.model_dump())
    response = await ctx.manager.subscribe_connection(ctx.connection_id, request)
    await ctx.websocket.send_text(
        json.dumps(
            {
                "type": "subscribe_response",
                "payload": response.model_dump(),
            }
        )
    )


async def handle_chat_message(
    ctx: ConnectionContext, message: WebSocketChatMessage
) -> None:
    """Persist a chat message and stream the assistant response."""
    if ctx.chat_service is None or ctx.chat_agent is None:
        raise WebSocketMessageError("Chat services unavailable for this endpoint")
    if ctx.user_id is None or ctx.session_id is None:
        raise WebSocketMessageError(
            "Chat endpoint requires authenticated user and session"
        )

    sanitized_content = WebSocketMessageValidator.sanitize_message_content(
        message.content
    )

    user_message = ChatMessage(
        role=MessageRole.USER,
        content=sanitized_content,
        tool_calls=None,
        timestamp=None,
        metadata=None,
    )

    message_event = ChatMessageEvent(
        user_id=ctx.user_id,
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
        payload={"message": user_message},
    )
    await ctx.send_session_event(message_event)

    await ctx.chat_service.add_message(
        session_id=str(ctx.session_id),
        user_id=str(ctx.user_id),
        message_data=MessageCreateRequest(
            role=MessageRole.USER.value,
            content=sanitized_content,
            metadata=None,
            tool_calls=None,
        ),
    )

    typing_start = ChatTypingEvent(
        user_id=ctx.user_id,
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
        payload={"event": "start"},
    )
    await ctx.send_session_event(typing_start)

    agent_context = {
        "user_id": str(ctx.user_id),
        "session_id": str(ctx.session_id),
        "websocket_mode": True,
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
    }

    response = await ctx.chat_agent.run(
        sanitized_content,
        user_id=str(ctx.user_id),
        session_id=str(ctx.session_id),
        context=agent_context,
    )
    assistant_content = str(response.get("content", ""))

    chunks = build_chunks(assistant_content)
    for index, chunk in enumerate(chunks):
        typing_chunk = ChatTypingEvent(
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            connection_id=ctx.connection_id,
            payload={
                "chunk_index": index,
                "content": chunk,
                "is_final": index == len(chunks) - 1,
            },
        )
        await ctx.send_session_event(typing_chunk)

    typing_stop = ChatTypingEvent(
        user_id=ctx.user_id,
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
        payload={"event": "stop"},
    )
    await ctx.send_session_event(typing_stop)

    assistant_message = ChatMessage(
        role=MessageRole.ASSISTANT,
        content=assistant_content,
        tool_calls=None,
        timestamp=None,
        metadata=None,
    )

    complete_event = ChatMessageCompleteEvent(
        user_id=ctx.user_id,
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
        payload={"message": assistant_message},
    )
    await ctx.send_session_event(complete_event)

    await ctx.chat_service.add_message(
        session_id=str(ctx.session_id),
        user_id=str(ctx.user_id),
        message_data=MessageCreateRequest(
            role=MessageRole.ASSISTANT.value,
            content=assistant_content,
            metadata=None,
            tool_calls=None,
        ),
    )


def build_chunks(content: str, *, size: int = 64) -> list[str]:
    """Split assistant content into deterministic chunks for streaming."""
    if not content:
        return [""]
    return [content[i : i + size] for i in range(0, len(content), size)]


def context_user_id(ctx: ConnectionContext) -> UUID | None:
    """Helper returning the user identifier for current context."""
    return ctx.user_id


MESSAGE_TYPE_HANDLERS: dict[str, MessageHandler] = {
    "heartbeat": handle_heartbeat,
    "ping": handle_ping,
    "pong": handle_pong,
    "subscribe": handle_subscribe,
    "chat_message": handle_chat_message,
}


async def run_message_loop(
    ctx: ConnectionContext,
    *,
    websocket: WebSocket,
) -> None:
    """Main message-processing loop for a connection."""
    try:
        async for raw_message in websocket.iter_text():
            message_type, model = parse_and_validate(raw_message)
            handler = MESSAGE_TYPE_HANDLERS.get(message_type)

            if handler is None:
                event = ErrorEvent(
                    user_id=context_user_id(ctx),
                    session_id=ctx.session_id,
                    connection_id=ctx.connection_id,
                    payload={
                        "error_code": "unknown_message_type",
                        "error_message": f"Unsupported message type '{message_type}'",
                    },
                )
                await ctx.send_event(event)
                continue

            try:
                await handler(ctx, model)
            except WebSocketMessageError as exc:
                error_event = ErrorEvent(
                    user_id=context_user_id(ctx),
                    session_id=ctx.session_id,
                    connection_id=ctx.connection_id,
                    payload={
                        "error_code": "message_error",
                        "error_message": str(exc),
                    },
                )
                await ctx.send_event(error_event)

    except WebSocketDisconnect:
        pass


async def announce_connection(
    ctx: ConnectionContext,
    auth_response: WebSocketAuthResponse,
) -> None:
    """Notify the client about connection establishment."""
    event = ConnectionEvent(
        user_id=context_user_id(ctx),
        session_id=ctx.session_id,
        connection_id=ctx.connection_id,
        payload={
            "available_channels": auth_response.available_channels,
        },
    )
    attach_context_meta(event, ctx)
    await ctx.send_event(event)
