"""Minimal test for WebSocket performance monitor creation and start/stop."""

import asyncio

import pytest

from tripsage_core.services.infrastructure.websocket_performance_monitor import (
    WebSocketPerformanceMonitor,
)


@pytest.mark.asyncio
async def test_performance_monitor_start_stop() -> None:
    """Monitor starts and stops without raising exceptions."""
    mon = WebSocketPerformanceMonitor(
        collection_interval=0.01, aggregation_interval=0.05
    )
    await mon.start()
    # Let the tasks do a minimal cycle
    await asyncio.sleep(0.05)
    await mon.stop()
