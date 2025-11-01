"""Cache-related fixtures for tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import fakeredis
import pytest_asyncio


@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[fakeredis.FakeAsyncRedis]:
    """Provide an in-memory Redis-compatible client.

    Yields:
        AsyncIterator[fakeredis.FakeAsyncRedis]: Async Redis stub for cache tests.
    """
    async with fakeredis.FakeAsyncRedis() as client:
        yield client
