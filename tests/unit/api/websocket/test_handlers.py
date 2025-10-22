"""Unit tests for the WebSocket handler utilities."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import WebSocket

from tripsage.api.websocket.context import ConnectionContext
from tripsage.api.websocket.handlers import (
    build_chunks,
    handle_chat_message,
    handle_ping,
    run_message_loop,
)
from tripsage.api.websocket.protocol import PongEvent
from tripsage_core.services.infrastructure.websocket_validation import (
    WebSocketChatMessage,
    WebSocketHeartbeatMessage,
)


class StubManager:
    """Minimal stub for ``WebSocketManager`` used in tests."""

    def __init__(self) -> None:
        """Initialise stub manager with mocked connection helpers."""
        connection = SimpleNamespace(
            update_heartbeat=Mock(),
            handle_pong=Mock(),
        )
        self.connections = {"conn-1": connection}
        self.send_to_connection = AsyncMock()
        self.send_to_session = AsyncMock()
        self.subscribe_connection = AsyncMock()


def make_context(**overrides) -> ConnectionContext:
    """Create a ``ConnectionContext`` prepopulated with useful defaults."""
    manager = overrides.pop("manager", StubManager())
    ctx = ConnectionContext(
        websocket=overrides.pop("websocket", AsyncMock(spec=WebSocket)),
        manager=manager,
        connection_id=overrides.pop("connection_id", "conn-1"),
        user_id=overrides.pop("user_id", uuid4()),
        session_id=overrides.pop("session_id", uuid4()),
        chat_service=overrides.pop("chat_service", AsyncMock()),
        chat_agent=overrides.pop("chat_agent", AsyncMock()),
    )
    for key, value in overrides.items():
        setattr(ctx, key, value)
    return ctx


@pytest.mark.asyncio
async def test_handle_chat_message_persists_and_streams() -> None:
    """Persist the user message and stream assistant response events."""
    chat_service = AsyncMock()
    chat_agent = AsyncMock()
    chat_agent.run.return_value = {"content": "Hello traveller"}
    manager = StubManager()
    ctx = make_context(
        chat_service=chat_service, chat_agent=chat_agent, manager=manager
    )

    message = WebSocketChatMessage.model_validate(
        {
            "content": "Hello",
            "session_id": str(ctx.session_id),
            "user_id": str(ctx.user_id),
        }
    )

    await handle_chat_message(ctx, message)

    assert chat_service.add_message.await_count == 2
    assert manager.send_to_session.await_count >= 3
    chat_agent.run.assert_awaited()


@pytest.mark.asyncio
async def test_handle_ping_sends_pong() -> None:
    """Ensure ping messages trigger a pong event."""
    manager = StubManager()
    ctx = make_context(manager=manager)
    heartbeat = WebSocketHeartbeatMessage.model_validate({"type": "ping"})
    await handle_ping(ctx, heartbeat)

    assert manager.send_to_connection.await_count == 1
    call = manager.send_to_connection.await_args
    assert call is not None
    sent_event: PongEvent = call.args[1]
    assert sent_event.type == "connection.pong"


class DummyWebSocket:
    """Async iterable with predefined text frames."""

    def __init__(self, messages: list[str]) -> None:
        """Store the sequence of text frames to emit."""
        self._messages = messages

    async def iter_text(self):
        """Yield text frames as the router would receive them."""
        for message in self._messages:
            yield message


@pytest.mark.asyncio
async def test_run_message_loop_reports_unknown_messages() -> None:
    """Unknown message types should return a structured error event."""
    manager = StubManager()
    ctx = make_context(manager=manager)
    websocket = cast(
        WebSocket,
        DummyWebSocket(
            [
                json.dumps({"type": "message", "payload": {}}),
            ]
        ),
    )

    await run_message_loop(ctx, websocket=websocket)

    assert manager.send_to_connection.await_count == 1
    call = manager.send_to_connection.await_args
    assert call is not None
    sent_event = call.args[1]
    assert sent_event.payload["error_code"] == "unknown_message_type"


def test_build_chunks_returns_deterministic_segments() -> None:
    """Chunk helper must produce deterministic slices for streaming."""
    content = "abcdef"
    chunks = build_chunks(content, size=2)
    assert chunks == ["ab", "cd", "ef"]
