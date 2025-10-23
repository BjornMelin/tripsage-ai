"""Unit tests for WebSocketMessagingService basic routing and subscriptions."""

from __future__ import annotations

import uuid
from typing import cast

import pytest
from fastapi import WebSocket

from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthService,
)
from tripsage_core.services.infrastructure.websocket_connection_service import (
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketMessagingService,
)


class _StubAuthService:
    """No-op auth service placeholder for constructor."""


class _DummyWS:
    """Bare minimal placeholder to satisfy constructor typing."""


@pytest.mark.anyio
async def test_subscribe_unsubscribe_and_channel_send() -> None:
    """Connections subscribe/unsubscribe to channels; send routes to all members."""
    svc = WebSocketMessagingService(auth_service=WebSocketAuthService())
    # Two connections for same channel
    c1 = WebSocketConnection(
        cast(WebSocket, _DummyWS()), connection_id="c1", user_id=uuid.uuid4()
    )
    c2 = WebSocketConnection(
        cast(WebSocket, _DummyWS()), connection_id="c2", user_id=uuid.uuid4()
    )

    # Patch send to avoid I/O
    async def _ok_send(event, message_limits=None):
        return True

    c1.send = _ok_send  # type: ignore[method-assign]
    c2.send = _ok_send  # type: ignore[method-assign]

    svc.register_connection(c1)
    svc.register_connection(c2)
    assert svc.subscribe_to_channel("c1", "news") is True
    assert svc.subscribe_to_channel("c2", "news") is True

    ev = WebSocketEvent(type="message.broadcast", payload={"x": 1})
    sent = await svc.send_to_channel("news", ev)
    assert sent == 2

    assert svc.unsubscribe_from_channel("c2", "news") is True
    sent2 = await svc.send_to_channel("news", ev)
    assert sent2 == 1


@pytest.mark.anyio
async def test_send_by_user_session_and_connection() -> None:
    """send_to_* helpers route to correct connection sets."""
    svc = WebSocketMessagingService(auth_service=WebSocketAuthService())
    uid = uuid.uuid4()
    sid = uuid.uuid4()
    c = WebSocketConnection(
        cast(WebSocket, _DummyWS()),
        connection_id="cx",
        user_id=uid,
        session_id=sid,
    )

    async def _ok_send(event, message_limits=None):
        return True

    c.send = _ok_send  # type: ignore[method-assign]
    svc.register_connection(c)

    ev = WebSocketEvent(type="message.sent", payload={"y": 2})
    assert await svc.send_to_user(uid, ev) == 1
    assert await svc.send_to_session(sid, ev) == 1
    assert await svc.send_to_connection("cx", ev) is True
