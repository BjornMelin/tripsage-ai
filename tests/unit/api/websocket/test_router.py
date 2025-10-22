"""Unit tests for WebSocket router orchestration helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import WebSocket

from tripsage.api.websocket.context import ConnectionContext
from tripsage.api.websocket.exceptions import (
    WebSocketAuthenticationError,
    WebSocketOriginError,
)
from tripsage.api.websocket.router import (
    _handle_websocket_session,
    _send_error_and_close,
    list_websocket_connections,
    websocket_health,
)
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthResponse,
)
from tripsage_core.services.infrastructure.websocket_manager import WebSocketManager


class ManagerStub:
    """Minimal stub emulating WebSocket manager behaviour."""

    def __init__(self) -> None:
        """Prepare fake connection data and async helpers."""
        self.disconnect_connection = AsyncMock()
        self.get_connection_stats = lambda: {"total": 1}

        connection = SimpleNamespace(
            connection_id="conn-1",
            user_id=None,
            session_id=None,
            state=SimpleNamespace(value="connected"),
            connected_at=None,
            last_heartbeat=None,
            subscribed_channels=set(),
            client_ip=None,
            user_agent=None,
        )

        self.connections = {"conn-1": connection}


@pytest.mark.asyncio
async def test_send_error_and_close() -> None:
    """Ensure helper sends an error payload then closes the socket."""
    websocket = AsyncMock(spec=WebSocket)
    await _send_error_and_close(websocket, code=4001, message="nope")

    websocket.send_text.assert_awaited()
    sent_payload = json.loads(websocket.send_text.await_args.args[0])
    assert sent_payload["message"] == "nope"
    websocket.close.assert_awaited_with(code=4001, reason="nope")


@pytest.mark.asyncio
async def test_handle_websocket_session_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path should authenticate, announce, and enter message loop."""
    user_id = uuid4()
    session_id = uuid4()
    manager = ManagerStub()

    websocket = AsyncMock(spec=WebSocket)
    websocket.headers = {"origin": "http://client.test"}
    websocket.app = SimpleNamespace(state=SimpleNamespace(websocket_manager=manager))

    context = ConnectionContext(
        websocket=websocket,
        manager=cast(WebSocketManager, manager),
        connection_id="conn-1",
        user_id=user_id,
        session_id=session_id,
    )

    auth_response = WebSocketAuthResponse(
        success=True,
        connection_id="conn-1",
        user_id=user_id,
        session_id=session_id,
        available_channels=[],
    )

    establish = AsyncMock(return_value=(context, auth_response))
    announce = AsyncMock()
    loop = AsyncMock()

    monkeypatch.setattr("tripsage.api.websocket.router.establish_connection", establish)
    monkeypatch.setattr("tripsage.api.websocket.router.announce_connection", announce)
    monkeypatch.setattr("tripsage.api.websocket.router.run_message_loop", loop)
    monkeypatch.setattr(
        "tripsage.api.websocket.router.get_settings",
        lambda: SimpleNamespace(cors_origins=["*"], is_production=False),
    )

    await _handle_websocket_session(websocket)

    establish.assert_awaited()
    announce.assert_awaited()
    loop.assert_awaited()
    manager.disconnect_connection.assert_awaited_with("conn-1")


@pytest.mark.asyncio
async def test_handle_websocket_session_origin_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Origin failures should close the connection with appropriate code."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.headers = {"origin": "http://client.test"}
    websocket.app = SimpleNamespace(
        state=SimpleNamespace(websocket_manager=ManagerStub())
    )

    async def raise_origin(*args, **kwargs):
        raise WebSocketOriginError("bad origin")

    monkeypatch.setattr(
        "tripsage.api.websocket.router.establish_connection", raise_origin
    )
    monkeypatch.setattr(
        "tripsage.api.websocket.router.get_settings",
        lambda: SimpleNamespace(cors_origins=["https://app"], is_production=True),
    )

    await _handle_websocket_session(websocket)

    websocket.close.assert_awaited_with(code=4003, reason="bad origin")


@pytest.mark.asyncio
async def test_handle_websocket_session_authentication_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authentication errors should delegate to the error send helper."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.headers = {"origin": "http://client.test"}
    websocket.app = SimpleNamespace(
        state=SimpleNamespace(websocket_manager=ManagerStub())
    )

    async def raise_auth(*args, **kwargs):
        raise WebSocketAuthenticationError("invalid")

    monkeypatch.setattr(
        "tripsage.api.websocket.router.establish_connection", raise_auth
    )
    monkeypatch.setattr(
        "tripsage.api.websocket.router.get_settings",
        lambda: SimpleNamespace(cors_origins=["*"], is_production=False),
    )

    close_helper = AsyncMock()
    monkeypatch.setattr(
        "tripsage.api.websocket.router._send_error_and_close", close_helper
    )

    await _handle_websocket_session(websocket)

    close_helper.assert_awaited()


@pytest.mark.asyncio
async def test_websocket_health_includes_timestamp() -> None:
    """Health endpoint must include a timestamp for observability."""
    manager = ManagerStub()
    result = await websocket_health(manager=cast(WebSocketManager, manager))
    assert result["status"] == "healthy"
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_list_websocket_connections_returns_serialized() -> None:
    """Listing endpoint should serialize active connections."""
    manager = ManagerStub()
    result = await list_websocket_connections(manager=cast(WebSocketManager, manager))
    assert result["total_count"] == 1
    assert isinstance(result["connections"], list)
