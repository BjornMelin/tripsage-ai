"""Cache-related fixtures for tests."""

from __future__ import annotations

import fakeredis
import pytest_asyncio


@pytest_asyncio.fixture
async def fake_redis():
    """Provide an in-memory Redis-compatible client."""
    async with fakeredis.FakeAsyncRedis() as client:
        yield client
