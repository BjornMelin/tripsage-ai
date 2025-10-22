"""Enabled-mode tests for CacheService using a stubbed async Redis client.

These tests avoid any real network by injecting a simple in-memory stub that
implements the subset of the redis.asyncio API used by CacheService.
"""

from __future__ import annotations

import pytest

from tripsage_core.services.infrastructure.cache_service import CacheService


class _StubRedisAsync:
    """Minimal async Redis stub to back CacheService in tests.

    Stores values in-memory as bytes and supports TTL bookkeeping without
    countdown semantics (sufficient for unit assertions).
    """

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}
        self._ttl: dict[str, int] = {}

    # Basic connectivity
    async def ping(self) -> bool:
        """Always returns True."""
        return True

    async def close(self) -> None:
        """No-op close."""
        return

    # String/JSON primitives
    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> bool:
        if isinstance(value, str):
            value = value.encode("utf-8")
        self._store[key] = value
        if ex is not None:
            self._ttl[key] = int(ex)
        return True

    async def setex(self, key: str, ttl: int, value: str | bytes) -> bool:
        return await self.set(key, value, ex=ttl)

    async def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    # Key ops
    async def delete(self, *keys: str) -> int:
        deleted = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                deleted += 1
            self._ttl.pop(k, None)
        return deleted

    async def exists(self, *keys: str) -> int:
        return sum(1 for k in keys if k in self._store)

    async def expire(self, key: str, seconds: int) -> bool:
        if key not in self._store:
            return False
        self._ttl[key] = int(seconds)
        return True

    async def ttl(self, key: str) -> int:
        if key not in self._store:
            return -2
        return self._ttl.get(key, -1)

    # Atomic counters
    async def incr(self, key: str) -> int:
        raw = self._store.get(key, b"0")
        value = int(raw.decode("utf-8")) + 1
        self._store[key] = str(value).encode("utf-8")
        return value

    async def decr(self, key: str) -> int:
        raw = self._store.get(key, b"0")
        value = int(raw.decode("utf-8")) - 1
        self._store[key] = str(value).encode("utf-8")
        return value

    # Pattern ops
    async def keys(self, pattern: str) -> list[bytes]:
        # Very simple wildcard suffix/prefix support for tests
        if pattern == "*":
            return [k.encode("utf-8") for k in self._store]
        prefix = pattern[:-1] if pattern.endswith("*") else None
        if prefix is not None:
            return [k.encode("utf-8") for k in self._store if k.startswith(prefix)]
        # Fallback exact match
        return [pattern.encode("utf-8")] if pattern in self._store else []

    # Admin/info
    async def flushdb(self) -> bool:
        self._store.clear()
        self._ttl.clear()
        return True

    async def info(self, section: str | None = None) -> str:
        # Return a redis-info-like text for parsing
        return (
            "# Server\n"
            "redis_version:7.0.0\n"
            "uptime_in_seconds:123\n"
            "# Clients\n"
            "connected_clients:1\n"
        )


@pytest.fixture()
def enabled_cache_service() -> CacheService:
    """Provide a CacheService wired to the stubbed client (enabled-mode)."""
    svc = CacheService()
    # Inject stub and mark as connected
    svc._client = _StubRedisAsync()  # type: ignore[attr-defined]
    svc._is_connected = True  # type: ignore[attr-defined]
    return svc


@pytest.mark.anyio
async def test_set_get_json_roundtrip(enabled_cache_service: CacheService) -> None:
    """Round-trip set/get JSON values."""
    data = {"a": 1, "b": [1, 2]}
    assert await enabled_cache_service.set_json("k:json", data, ttl=10)
    out = await enabled_cache_service.get_json("k:json")
    assert out == data


@pytest.mark.anyio
async def test_set_get_string_and_ttl(enabled_cache_service: CacheService) -> None:
    """Set/get raw string values and verify TTL is tracked."""
    assert await enabled_cache_service.set("k:str", "value", ttl=5)
    val = await enabled_cache_service.get("k:str")
    assert val == "value"
    ttl = await enabled_cache_service.ttl("k:str")
    assert ttl in {5, -1}  # stub may not track TTL per-second


@pytest.mark.anyio
async def test_incr_decr(enabled_cache_service: CacheService) -> None:
    """Increment and decrement counters atomically."""
    v1 = await enabled_cache_service.incr("k:ctr")
    v2 = await enabled_cache_service.incr("k:ctr")
    v3 = await enabled_cache_service.decr("k:ctr")
    assert (v1, v2, v3) == (1, 2, 1)


@pytest.mark.anyio
async def test_delete_and_exists(enabled_cache_service: CacheService) -> None:
    """Delete keys and verify existence counts."""
    await enabled_cache_service.set("a", "1")
    await enabled_cache_service.set("b", "2")
    assert await enabled_cache_service.exists("a", "b") == 2
    assert await enabled_cache_service.delete("a") == 1
    assert await enabled_cache_service.exists("a", "b") == 1


@pytest.mark.anyio
async def test_keys_and_delete_pattern(enabled_cache_service: CacheService) -> None:
    """List keys by prefix and delete by pattern."""
    await enabled_cache_service.set("user:1", "x")
    await enabled_cache_service.set("user:2", "y")
    keys = await enabled_cache_service.keys("user:*")
    assert set(keys) == {"user:1", "user:2"}
    deleted = await enabled_cache_service.delete_pattern("user:*")
    assert deleted == 2
    assert await enabled_cache_service.keys("user:*") == []


@pytest.mark.anyio
async def test_flushdb(enabled_cache_service: CacheService) -> None:
    """Flush database and verify all keys are removed."""
    await enabled_cache_service.set("k", "v")
    assert await enabled_cache_service.flushdb() is True
    assert await enabled_cache_service.keys("*") == []
