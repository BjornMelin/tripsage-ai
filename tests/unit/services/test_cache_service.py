"""Unit tests for the CacheService adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from tripsage_core.services.infrastructure import cache_service as cache_module
from tripsage_core.services.infrastructure.cache_service import CacheService


class StubRedis:
    """In-memory Redis stub covering the CacheService surface area."""

    from_env_called = False
    last_instance: StubRedis | None = None

    def __init__(self, url: str | None = None, token: str | None = None) -> None:
        """Initialise in-memory storage for cache interactions."""
        self.url = url
        self.token = token
        self.store: dict[str, Any] = {}
        self.ttls: dict[str, int] = {}
        self.ping_called = False
        StubRedis.last_instance = self

    @classmethod
    def from_env(cls) -> StubRedis:
        """Simulate environment-based client creation."""
        instance = cls(url="env-url", token="env-token")
        instance.from_env_called = True
        StubRedis.last_instance = instance
        return instance

    async def ping(self) -> None:
        """Mark the client as having validated connectivity."""
        self.ping_called = True

    async def set(self, key: str, value: Any, ex: int | None = None) -> str:
        """Persist a key/value pair with optional TTL."""
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return "OK"

    async def get(self, key: str) -> Any | None:
        """Retrieve a cached value."""
        return self.store.get(key)

    async def delete(self, *keys: str) -> int:
        """Remove cached keys and return the number deleted."""
        removed = 0
        for key in keys:
            if key in self.store:
                removed += 1
                self.store.pop(key, None)
                self.ttls.pop(key, None)
        return removed

    async def exists(self, *keys: str) -> int:
        """Return the count of keys present in the store."""
        return sum(1 for key in keys if key in self.store)

    async def expire(self, key: str, seconds: int) -> int:
        """Record a TTL for an existing key."""
        if key not in self.store:
            return 0
        self.ttls[key] = seconds
        return 1

    async def ttl(self, key: str) -> int:
        """Expose the remaining TTL for a key."""
        if key not in self.store:
            return -2
        return self.ttls.get(key, -1)

    async def incr(self, key: str) -> int:
        """Increment a cached counter."""
        current = int(self.store.get(key, "0")) + 1
        self.store[key] = str(current)
        return current

    async def decr(self, key: str) -> int:
        """Decrement a cached counter."""
        current = int(self.store.get(key, "0")) - 1
        self.store[key] = str(current)
        return current

    async def mget(self, *keys: str) -> list[Any | None]:
        """Fetch multiple cached values."""
        return [self.store.get(key) for key in keys]

    async def mset(self, mapping: dict[str, str]) -> str:
        """Set multiple cached entries in one call."""
        for key, value in mapping.items():
            self.store[key] = value
        return "OK"


@pytest.mark.asyncio
async def test_connect_uses_explicit_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """CacheService should honour explicit credentials when connecting."""
    monkeypatch.setattr(cache_module, "UpstashRedis", StubRedis)
    settings = SimpleNamespace(
        upstash_redis_rest_url="https://example.com",
        upstash_redis_rest_token="token",
    )
    monkeypatch.setattr(cache_module, "get_settings", lambda: settings)
    service = CacheService()

    await service.connect()

    assert service.is_connected is True
    client = StubRedis.last_instance
    assert isinstance(client, StubRedis)
    assert client.url == "https://example.com"
    assert client.token == "token"
    assert client.ping_called is True


@pytest.mark.asyncio
async def test_set_and_get_json_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stored JSON payloads should round-trip through the service."""
    monkeypatch.setattr(cache_module, "UpstashRedis", StubRedis)
    settings = SimpleNamespace(
        upstash_redis_rest_url="https://example.com",
        upstash_redis_rest_token="token",
    )
    monkeypatch.setattr(cache_module, "get_settings", lambda: settings)
    service = CacheService()

    payload = {"user": "alice", "roles": ["admin"]}
    await service.set_json("profile", payload)
    result = await service.get_json("profile")

    assert result == payload


@pytest.mark.asyncio
async def test_delete_and_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delete operations should remove keys and adjust existence counts."""
    monkeypatch.setattr(cache_module, "UpstashRedis", StubRedis)
    settings = SimpleNamespace(
        upstash_redis_rest_url="https://example.com",
        upstash_redis_rest_token="token",
    )
    monkeypatch.setattr(cache_module, "get_settings", lambda: settings)
    service = CacheService()

    await service.set("counter", "1")
    exists_before = await service.exists("counter")
    deleted = await service.delete("counter")
    exists_after = await service.exists("counter")

    assert exists_before == 1
    assert deleted == 1
    assert exists_after == 0


@pytest.mark.asyncio
async def test_disconnect_resets_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disconnect should clear the cached client state."""
    monkeypatch.setattr(cache_module, "UpstashRedis", StubRedis)
    settings = SimpleNamespace(
        upstash_redis_rest_url="https://example.com",
        upstash_redis_rest_token="token",
    )
    monkeypatch.setattr(cache_module, "get_settings", lambda: settings)
    service = CacheService()

    await service.set("key", "value")
    await service.disconnect()

    assert service.is_connected is False
