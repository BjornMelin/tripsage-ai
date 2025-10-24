"""Minimal tests for the final WebSocketManager surface.

These tests validate basic start/stop behavior without Redis configured and
rate-limit checks in fallback mode.
"""

from uuid import uuid4

import pytest

from tripsage_core.services.infrastructure.websocket_manager import WebSocketManager


@pytest.mark.asyncio
async def test_manager_start_stop_without_redis() -> None:
    """Manager starts/stops when no redis_url is provided in settings."""
    mgr = WebSocketManager(broadcaster=None)
    await mgr.start()
    await mgr.stop()


@pytest.mark.asyncio
async def test_rate_limit_fallback_allows_connection() -> None:
    """Fallback rate limiter allows connection when no Redis client is configured."""
    mgr = WebSocketManager(broadcaster=None)
    # Do not start Redis; fallback path should allow connection
    allowed = await mgr._check_connection_rate_limit(user_id=uuid4(), session_id=None)
    assert allowed is True
