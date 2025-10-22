"""Typed WebSocket events emitted by the TripSage API router."""

from __future__ import annotations

from pydantic import Field

from tripsage_core.models.schemas_common.chat import ChatMessage
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


class ConnectionEvent(WebSocketEvent):
    """Event describing connection lifecycle state."""

    type: str = Field(
        default=WebSocketEventType.CONNECTION_ESTABLISHED,
        description="Connection lifecycle event type",
    )
    payload: dict[str, str | None] = Field(default_factory=dict)


class ErrorEvent(WebSocketEvent):
    """Structured error event for WebSocket clients."""

    type: str = Field(
        default=WebSocketEventType.CONNECTION_ERROR,
        description="Error event type",
    )
    payload: dict[str, str] = Field(default_factory=dict)


class PongEvent(WebSocketEvent):
    """Heartbeat acknowledgement sent to clients."""

    type: str = Field(
        default=WebSocketEventType.CONNECTION_PONG,
        description="Pong event type",
    )


class ChatTypingEvent(WebSocketEvent):
    """Streaming chat typing indicator chunk."""

    type: str = Field(
        default=WebSocketEventType.CHAT_TYPING,
        description="Typing chunk event type",
    )
    payload: dict[str, str | int | bool] = Field(default_factory=dict)


class ChatMessageEvent(WebSocketEvent):
    """Chat message event communicated to clients."""

    type: str = Field(
        default=WebSocketEventType.CHAT_MESSAGE,
        description="Chat message event type",
    )
    payload: dict[str, ChatMessage] = Field(default_factory=dict)


class ChatMessageCompleteEvent(WebSocketEvent):
    """Event indicating completion of an assistant response."""

    type: str = Field(
        default=WebSocketEventType.CHAT_MESSAGE_COMPLETE,
        description="Chat completion event type",
    )
    payload: dict[str, ChatMessage] = Field(default_factory=dict)
