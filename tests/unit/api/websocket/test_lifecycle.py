"""Unit tests for lifecycle helpers in the WebSocket router."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import WebSocket

from tripsage.api.core.config import Settings
from tripsage.api.websocket.exceptions import (
    WebSocketAuthenticationError,
    WebSocketOriginError,
)
from tripsage.api.websocket.lifecycle import ensure_origin_allowed, establish_connection
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthResponse,
)


class DummySettings(SimpleNamespace):
    """Lightweight settings stub used for origin validation tests."""


@pytest.mark.asyncio
async def test_establish_connection_appends_default_channels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default channels should be merged into the auth request."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.headers = {"origin": "http://client.test"}
    websocket.accept = AsyncMock()
    websocket.receive_text.return_value = json.dumps(
        {
            "type": "auth",
            "token": "aaa.bbb.ccc",
            "channels": ["chat:primary"],
            "session_id": str(uuid4()),
        }
    )

    user_id = uuid4()
    session_id = uuid4()
    manager = AsyncMock()
    manager.authenticate_connection.return_value = WebSocketAuthResponse(
        success=True,
        connection_id="conn-123",
        user_id=user_id,
        session_id=session_id,
        available_channels=["chat:primary"],
    )

    settings = cast(
        Settings,
        DummySettings(cors_origins=["http://client.test"], is_production=False),
    )

    context, response = await establish_connection(
        websocket,
        manager=manager,
        settings=settings,
        default_channels=["agent_status:foo"],
    )

    assert context.connection_id == "conn-123"
    assert context.user_id == user_id
    assert context.session_id == session_id
    auth_call = manager.authenticate_connection.await_args
    _, auth_request = auth_call.args
    assert sorted(auth_request.channels) == sorted(["chat:primary", "agent_status:foo"])
    assert response.success is True


@pytest.mark.asyncio
async def test_establish_connection_enforces_session_id() -> None:
    """Session mismatch should trigger an authentication error."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.headers = {"origin": "http://client.test"}
    websocket.accept = AsyncMock()
    websocket.receive_text.return_value = json.dumps(
        {
            "type": "auth",
            "token": "aaa.bbb.ccc",
            "session_id": str(uuid4()),
        }
    )

    settings = cast(
        Settings,
        DummySettings(cors_origins=["http://client.test"], is_production=False),
    )

    with pytest.raises(WebSocketAuthenticationError):
        await establish_connection(
            websocket,
            manager=AsyncMock(),
            settings=settings,
            enforce_session_id=uuid4(),
        )


def test_ensure_origin_allowed_allows_wildcard() -> None:
    """Wildcard configuration should accept any origin."""
    websocket = Mock(spec=WebSocket)
    websocket.headers = {"origin": "https://example.com"}
    settings = cast(Settings, DummySettings(cors_origins=["*"], is_production=False))
    ensure_origin_allowed(websocket, settings)


def test_ensure_origin_allowed_rejects_missing_in_production() -> None:
    """Missing origins must fail when running in production mode."""
    websocket = Mock(spec=WebSocket)
    websocket.headers = {}
    settings = cast(
        Settings,
        DummySettings(cors_origins=["https://example.com"], is_production=True),
    )
    with pytest.raises(WebSocketOriginError):
        ensure_origin_allowed(websocket, settings)


def test_ensure_origin_allowed_accepts_known_origin() -> None:
    """Origins present in the allow-list should be accepted."""
    websocket = Mock(spec=WebSocket)
    websocket.headers = {"origin": "https://app.example.com"}
    settings = cast(
        Settings,
        DummySettings(
            cors_origins=["https://app.example.com", "https://admin.example.com"],
            is_production=True,
        ),
    )
    ensure_origin_allowed(websocket, settings)


def test_ensure_origin_allowed_rejects_unlisted_origin() -> None:
    """Unknown origins should result in a validation error."""
    websocket = Mock(spec=WebSocket)
    websocket.headers = {"origin": "https://evil.example"}
    settings = cast(
        Settings,
        DummySettings(cors_origins=["https://app.example"], is_production=True),
    )
    with pytest.raises(WebSocketOriginError):
        ensure_origin_allowed(websocket, settings)
