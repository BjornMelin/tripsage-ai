"""Cache façade built on cashews with Redis (Upstash) support."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from typing import Any, Final

from cashews import Cache, cache
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from tripsage_core.config import get_settings
from tripsage_core.utils.content_utils import ContentType, get_ttl_for_content_type


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# Setup (one-time)
# --------------------------------------------------------------------------------------
_settings = get_settings()
_CACHE_URL: str = (
    "mem://"
    if getattr(_settings, "is_testing", False)
    else (_settings.redis_url or "mem://")
)
_CACHE_PREFIX: Final[str] = "tripsage"
_cache: Cache = cache
_cache.setup(_CACHE_URL)  # pyright: ignore[reportUnknownMemberType]

# Local lock registry for mem backend
_LOCAL_LOCKS: dict[str, asyncio.Lock] = {}


class CacheStats(BaseModel):
    """Lightweight cache statistics container."""

    hits: int = Field(0)
    misses: int = Field(0)
    hit_ratio: float = Field(0.0)
    sets: int = Field(0)
    deletes: int = Field(0)
    key_count: int = Field(0)
    size_mb: float = Field(0.0)


def _ns_key(key: str, namespace: str | None = None) -> str:
    ns = namespace or _CACHE_PREFIX
    return f"{ns}:{key}"


def generate_cache_key(scope: str, *parts: Any, **kwargs: Any) -> str:
    """Generate a deterministic cache key.

    Args:
        scope: Logical scope (e.g., "websearch")
        *parts: Positional key parts (e.g., query)
        **kwargs: Additional context that affects the key

    Returns:
        Stable namespaced key string
    """
    payload = {"parts": parts, "kwargs": kwargs}
    digest = hashlib.sha1(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    return f"{scope}:{digest}"


def determine_content_type(_: Any) -> ContentType:
    """Best-effort content type selection; callers may override.

    Maintained for compatibility; prefer explicit ContentType at call sites.
    """
    return ContentType.DAILY


def cached(*, content_type: ContentType | None = None, ttl: int | None = None):
    """Decorator that caches function results via cashews.

    Args:
        content_type: Optional content type to derive TTL
        ttl: Optional explicit TTL seconds; wins over content_type
    """
    ttl_seconds = (
        ttl
        if ttl is not None
        else (get_ttl_for_content_type(content_type) if content_type else None)
    )

    def _decorate(func: Callable[..., Any]):
        if ttl_seconds is None:
            # Default 1 hour if not specified
            return _cache(ttl=3600)(func)
        return _cache(ttl=ttl_seconds)(func)

    return _decorate


async def get_cache(key: str, *, namespace: str | None = None) -> Any | None:
    """Get a cached value by key.

    Args:
        key: Cache key (without namespace prefix)
        namespace: Optional namespace to prefix

    Returns:
        Cached value or None when missing.
    """
    return await _cache.get(_ns_key(key, namespace))


async def set_cache(
    key: str,
    value: Any,
    *,
    content_type: ContentType | None = None,
    ttl: int | None = None,
    namespace: str | None = None,
) -> bool:
    """Set a cached value with TTL.

    Args:
        key: Cache key (without namespace prefix)
        value: Serializable value
        content_type: Optional content type for TTL derivation
        ttl: Explicit TTL seconds (overrides content_type)
        namespace: Optional namespace to prefix

    Returns:
        True on success.
    """
    ttl_seconds = (
        ttl
        if ttl is not None
        else (get_ttl_for_content_type(content_type) if content_type else 3600)
    )
    await _cache.set(_ns_key(key, namespace), value, expire=ttl_seconds)
    return True


async def delete_cache(key: str, *, namespace: str | None = None) -> bool:
    """Delete a cached value by key.

    Args:
        key: Cache key (without namespace prefix)
        namespace: Optional namespace to prefix

    Returns:
        True on success.
    """
    await _cache.delete(_ns_key(key, namespace))
    return True


async def batch_cache_get(
    keys: Iterable[str], *, namespace: str | None = None
) -> dict[str, Any]:
    """Get multiple keys concurrently (best-effort)."""
    tasks: dict[str, asyncio.Task[Any]] = {}
    for key in keys:
        tasks[key] = asyncio.create_task(_cache.get(_ns_key(key, namespace)))
    results: dict[str, Any] = {}
    for key, task in tasks.items():
        results[key] = await task
    return results


async def prefetch_cache_keys(
    keys: Iterable[str], *, namespace: str | None = None
) -> None:
    """Warm up cache entries asynchronously."""
    # Best-effort warmup; use gather for concurrency
    await asyncio.gather(*(get_cache(key, namespace=namespace) for key in keys))


async def invalidate_pattern(pattern: str, *, namespace: str | None = None) -> int:
    """Delete keys matching pattern using Redis scan when available.

    Falls back to a no-op when not backed by Redis/Dragonfly.
    """
    if _CACHE_URL.startswith(("redis://", "rediss://")):
        redis: Redis = Redis.from_url(_CACHE_URL)  # pyright: ignore[reportUnknownMemberType]
        ns = (namespace or _CACHE_PREFIX) + ":"
        full_pattern = ns + pattern
        cursor = 0
        deleted = 0
        try:
            while True:
                cursor, keys = await redis.scan(  # pyright: ignore[reportUnknownMemberType]
                    cursor=cursor, match=full_pattern, count=1000
                )
                if keys:
                    deleted += await redis.delete(*keys)
                if cursor == 0:
                    break
        finally:
            await redis.aclose()
        return int(deleted)
    # Memory backend: cashews has no pattern API here; return 0
    return 0


async def get_cache_stats() -> CacheStats:
    """Return basic cache stats (backend-agnostic stub)."""
    return CacheStats(
        hits=0,
        misses=0,
        hit_ratio=0.0,
        sets=0,
        deletes=0,
        key_count=0,
        size_mb=0.0,
    )


@asynccontextmanager
async def cache_lock(
    name: str, *, timeout: int = 5, namespace: str | None = None
) -> AsyncIterator[None]:
    """Distributed lock using Redis when available; local lock otherwise."""
    if _CACHE_URL.startswith(("redis://", "rediss://")):
        redis: Redis = Redis.from_url(_CACHE_URL)  # pyright: ignore[reportUnknownMemberType]
        lock = redis.lock(_ns_key(f"lock:{name}", namespace), timeout=timeout)
        try:
            acquired = await lock.acquire(blocking=True, blocking_timeout=timeout)
            if not acquired:
                logger.warning("Failed to acquire cache lock: %s", name)
                yield
            else:
                yield
        finally:
            try:
                if await lock.locked():
                    await lock.release()
            finally:
                await redis.aclose()
    else:
        # Fallback per-process named lock
        lock_key = _ns_key(f"lock:{name}", namespace)
        lock = _LOCAL_LOCKS.setdefault(lock_key, asyncio.Lock())
        async with lock:
            yield


# --------------------------------------------------------------------------------------
# Minimal object used by call sites (e.g., planning tools)
# --------------------------------------------------------------------------------------
class _RedisFacade:
    async def get(self, key: str) -> Any | None:
        """Get a value by key using the configured backend."""
        return await _cache.get(_ns_key(key))

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value with TTL in seconds using the configured backend."""
        exp = ttl if ttl is not None else 3600
        await _cache.set(_ns_key(key), value, expire=exp)
        return True

    async def delete(self, key: str) -> bool:
        """Delete a value by key."""
        await _cache.delete(_ns_key(key))
        return True


redis_cache = _RedisFacade()


__all__ = [
    "CacheStats",
    "batch_cache_get",
    "cache_lock",
    "cached",
    "delete_cache",
    "determine_content_type",
    "generate_cache_key",
    "get_cache",
    "get_cache_stats",
    "invalidate_pattern",
    "prefetch_cache_keys",
    "redis_cache",
    "set_cache",
]
