"""Connection context helpers for WebSocket handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from tripsage.agents.chat import ChatAgent
from tripsage_core.services.business.chat_service import ChatService
from tripsage_core.services.infrastructure.websocket_manager import WebSocketManager
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
)


@dataclass(slots=True)
class ConnectionContext:
    """Shared context injected into WebSocket message handlers.

    Attributes:
        websocket: Active FastAPI WebSocket connection.
        manager: WebSocket manager coordinating messaging fan-out.
        connection_id: Identifier assigned by the manager.
        user_id: Optional authenticated user identifier.
        session_id: Optional chat session identifier.
        chat_service: Service for persisting chat messages when applicable.
        chat_agent: Chat agent responsible for generating assistant replies.
    """

    websocket: WebSocket
    manager: WebSocketManager
    connection_id: str
    user_id: UUID | None
    session_id: UUID | None
    chat_service: ChatService | None = None
    chat_agent: ChatAgent | None = None

    async def send_event(self, event: WebSocketEvent) -> None:
        """Send an event directly to the current connection."""
        await self.manager.send_to_connection(self.connection_id, event)

    async def send_session_event(self, event: WebSocketEvent) -> None:
        """Broadcast an event to the current session if present."""
        if self.session_id is None:
            raise ValueError("Session identifier is required for session broadcasts")
        await self.manager.send_to_session(self.session_id, event)

    def as_payload(self) -> dict[str, Any]:
        """Return a serializable payload summarising the connection."""
        return {
            "connection_id": self.connection_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
        }
