"""Tests for cache utility functions and decorators.

This module contains unit tests for the cache utilities in
tripsage_core.utils.cache_utils, including cache operations, decorators,
key generation, locking, and invalidation.
"""

import asyncio

import pytest
from cashews import cache as cashews_cache

import tripsage_core.utils.cache_utils as cu
from tripsage_core.utils.cache_utils import (
    cache_lock,
    cached,
    generate_cache_key,
    get_cache,
    invalidate_pattern,
    set_cache,
)


pytestmark = pytest.mark.asyncio

# Force in-memory cache backend for tests regardless of environment
cashews_cache.setup("mem://")
cu._CACHE_URL = "mem://"


async def test_set_get_roundtrip() -> None:
    """Test basic cache set and get operations work correctly."""
    key = generate_cache_key("unit", "roundtrip", x=1)
    assert await get_cache(key) is None
    await set_cache(key, {"ok": True}, ttl=1)
    assert await get_cache(key) == {"ok": True}


async def test_cached_decorator_memoizes() -> None:
    """Test that the cached decorator properly memoizes function results."""
    calls = {"n": 0}

    @cached(ttl=2)
    async def compute(x: int) -> int:
        calls["n"] += 1
        return x * 2

    assert await compute(2) == 4
    assert await compute(2) == 4
    assert calls["n"] == 1


async def test_generate_cache_key_deterministic() -> None:
    """Test that cache key generation produces deterministic results."""
    k1 = generate_cache_key("scope", "a", b=2)
    k2 = generate_cache_key("scope", "a", b=2)
    assert k1 == k2


async def test_cache_lock_exclusion() -> None:
    """Test that cache locks provide mutual exclusion between concurrent operations."""
    order: list[str] = []

    async def worker(name: str):
        async with cache_lock("lock-test", timeout=2):
            order.append(f"enter:{name}")
            await asyncio.sleep(0.05)
            order.append(f"exit:{name}")

    await asyncio.gather(worker("a"), worker("b"))
    # Ensure no interleaving in critical section
    assert order[0].startswith("enter:") and order[1].startswith("exit:")


async def test_invalidate_pattern_mem_backend_returns_zero() -> None:
    """Test that pattern invalidation returns zero for mem:// backend."""
    # When mem:// is active by default, pattern invalidation returns 0
    deleted = await invalidate_pattern("nonexistent*")
    assert deleted == 0
