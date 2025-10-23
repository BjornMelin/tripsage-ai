"""Final WebSocket router implementation for TripSage."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket

from tripsage.agents.chat import ChatAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage.api.core.config import get_settings
from tripsage.api.core.dependencies import get_db, get_websocket_manager_dep
from tripsage.api.websocket.context import ConnectionContext
from tripsage.api.websocket.exceptions import (
    WebSocketAuthenticationError,
    WebSocketError,
    WebSocketMessageError,
    WebSocketOriginError,
)
from tripsage.api.websocket.handlers import announce_connection, run_message_loop
from tripsage.api.websocket.lifecycle import (
    establish_connection,
    format_auth_response,
    serialize_connection,
)
from tripsage_core.services.business.chat_service import ChatService as CoreChatService
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.websocket_manager import WebSocketManager
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
)


router = APIRouter()

DatabaseDep = Annotated[DatabaseService, Depends(get_db)]
ManagerDep = Annotated[WebSocketManager, Depends(get_websocket_manager_dep)]


@lru_cache(maxsize=1)
def get_service_registry() -> ServiceRegistry:
    """Return a singleton service registry instance."""
    return ServiceRegistry()


@lru_cache(maxsize=1)
def get_chat_agent() -> ChatAgent:
    """Return the singleton chat agent."""
    return ChatAgent(service_registry=get_service_registry())


async def get_core_chat_service(db: DatabaseDep) -> CoreChatService:
    """Construct the core chat service from the database dependency."""
    return CoreChatService(database_service=db)


def _manager_from_websocket(websocket: WebSocket) -> WebSocketManager:
    """Retrieve the WebSocket manager from application state."""
    manager = getattr(websocket.app.state, "websocket_manager", None)
    if manager is None:
        raise WebSocketError("WebSocket manager not initialised")
    return manager


async def _send_error_and_close(
    websocket: WebSocket, *, code: int, message: str
) -> None:
    """Send an error payload then close the WebSocket connection."""
    await websocket.send_text(json.dumps({"type": "error", "message": message}))
    await websocket.close(code=code, reason=message)


async def _handle_websocket_session(
    websocket: WebSocket,
    *,
    default_channels: Iterable[str] | None = None,
    enforce_session_id: UUID | None = None,
    chat_service: CoreChatService | None = None,
    chat_agent: ChatAgent | None = None,
    user_guard: UUID | None = None,
) -> None:
    """Shared connection lifecycle used by all websocket endpoints."""
    manager = _manager_from_websocket(websocket)
    settings = get_settings()
    context: ConnectionContext | None = None

    try:
        context, auth_response = await establish_connection(
            websocket,
            manager=manager,
            settings=settings,
            default_channels=default_channels,
            enforce_session_id=enforce_session_id,
        )

        if user_guard and context.user_id != user_guard:
            raise WebSocketAuthenticationError("User identity mismatch")

        if chat_service:
            context.chat_service = chat_service
        if chat_agent:
            context.chat_agent = chat_agent

        await websocket.send_text(json.dumps(format_auth_response(auth_response)))
        await announce_connection(context, auth_response)
        await run_message_loop(context, websocket=websocket)

    except WebSocketOriginError as exc:
        await websocket.close(code=4003, reason=str(exc))
    except WebSocketAuthenticationError as exc:
        await _send_error_and_close(websocket, code=4001, message=str(exc))
    except WebSocketMessageError as exc:
        if context is not None:
            error_event = WebSocketEvent(
                type="connection.error",
                connection_id=context.connection_id,
                user_id=context.user_id,
                session_id=context.session_id,
                payload={
                    "error_code": "message_error",
                    "error_message": str(exc),
                },
            )
            await context.send_event(error_event)
        else:
            await _send_error_and_close(websocket, code=4002, message=str(exc))
    finally:
        if context is not None:
            await manager.disconnect_connection(context.connection_id)


@router.websocket("/ws")
async def generic_websocket(websocket: WebSocket) -> None:
    """Generic WebSocket endpoint for feature discovery and debugging."""
    await _handle_websocket_session(websocket)


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: UUID,
    chat_service: Annotated[CoreChatService, Depends(get_core_chat_service)],
) -> None:
    """Chat WebSocket endpoint providing user <-> assistant streaming."""
    await _handle_websocket_session(
        websocket,
        enforce_session_id=session_id,
        chat_service=chat_service,
        chat_agent=get_chat_agent(),
    )


@router.websocket("/ws/agent-status/{user_id}")
async def agent_status_websocket(websocket: WebSocket, user_id: UUID) -> None:
    """Real-time agent-status updates for a specific user."""
    await _handle_websocket_session(
        websocket,
        default_channels=[f"agent_status:{user_id}"],
        user_guard=user_id,
    )


@router.get("/ws/health")
async def websocket_health(manager: ManagerDep) -> dict[str, object]:
    """Return health metrics for the WebSocket subsystem."""
    stats = manager.get_connection_stats()
    return {
        "status": "healthy",
        "websocket_manager_running": getattr(manager, "_running", False),
        "connection_stats": stats,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ws/connections")
async def list_websocket_connections(manager: ManagerDep) -> dict[str, object]:
    """List active WebSocket connections (admin use)."""
    connections = [
        serialize_connection(connection) for connection in manager.connections.values()
    ]
    return {"connections": connections, "total_count": len(connections)}


@router.delete("/ws/connections/{connection_id}")
async def disconnect_websocket_connection(
    connection_id: str,
    manager: ManagerDep,
) -> dict[str, str]:
    """Disconnect a specific WebSocket connection."""
    await manager.disconnect_connection(connection_id)
    return {"message": f"Connection {connection_id} disconnected"}
