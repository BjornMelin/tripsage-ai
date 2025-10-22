"""Unit tests for WebSocketConnection queue/backpressure behavior.

These tests avoid real WebSocket I/O and focus on internal queue accounting.
"""

from __future__ import annotations

import uuid
from typing import cast

import pytest
from fastapi import WebSocket

from tripsage_core.services.infrastructure.websocket_connection_service import (
    MonitoredDeque,
    WebSocketConnection,
)


class _DummyWS:
    """Bare minimal placeholder to satisfy constructor typing."""


@pytest.mark.anyio
async def test_monitored_deque_drops_when_full() -> None:
    """MonitoredDeque increments drop counter when exceeding maxlen."""
    dq = MonitoredDeque(maxlen=2, priority_name="test", connection_id="c1")
    dq.append(1)
    dq.append(2)
    dq.append(3)
    assert dq.dropped_count == 1


@pytest.mark.anyio
async def test_backpressure_activates_when_threshold_crossed() -> None:
    """Backpressure toggles when total queue size crosses threshold."""
    conn = WebSocketConnection(
        cast(WebSocket, _DummyWS()), connection_id="c1", user_id=uuid.uuid4()
    )
    # Pre-fill main queue to 1000
    for i in range(1000):
        conn.message_queue.append(f"q{i}")
    # Fill priority queues to exceed threshold (1600)
    # Add 300 to medium and 400 to low => total = 1700
    for i in range(300):
        conn.priority_queue[2].append(f"m{i}")
    for i in range(400):
        conn.priority_queue[3].append(f"l{i}")
    assert conn.is_backpressure_active() is True
    assert conn.backpressure_active is True
