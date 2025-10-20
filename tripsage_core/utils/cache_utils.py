"""Unified caching utilities for TripSage Core.

This module provides both in-memory and DragonflyDB-based caching functionality
with content-aware TTL settings and performance monitoring.
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import (
    Any,
    TypeVar,
    cast,
)

from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure import get_cache_service
from tripsage_core.utils.content_utils import ContentType, get_ttl_for_content_type


logger = logging.getLogger(__name__)

# Type variables
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Global cache service instance
_cache_service = None


async def get_cache_instance():
    """Get the global cache service instance (DragonflyDB/Redis)."""
    global _cache_service
    if _cache_service is None:
        _cache_service = await get_cache_service()
    return _cache_service


class CacheStats(BaseModel):
    """Cache statistics model."""

    hits: int = Field(0, description="Number of cache hits")
    misses: int = Field(0, description="Number of cache misses")
    hit_ratio: float = Field(0.0, description="Cache hit ratio (0.0-1.0)")
    sets: int = Field(0, description="Number of cache sets")
    deletes: int = Field(0, description="Number of cache deletes")
    key_count: int = Field(0, description="Number of keys in cache")
    size_mb: float = Field(0.0, description="Estimated cache size in MB")


class InMemoryCache:
    """Simple in-memory cache implementation for single-instance deployments."""

    def __init__(self):
        """Initialize the in-memory cache."""
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._stats = CacheStats()

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        async with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            cache_item = self._cache[key]

            # Check if item has expired
            if (
                "expires_at" in cache_item
                and cache_item["expires_at"] is not None
                and cache_item["expires_at"] < time.time()
            ):
                del self._cache[key]
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            return cache_item["value"]

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in the cache."""
        async with self._lock:
            expires_at = None if ttl is None else time.time() + ttl
            self._cache[key] = {"value": value, "expires_at": expires_at}
            self._stats.sets += 1
            return True

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1
                return True
            return False

    async def clear(self) -> None:
        """Clear all values from the cache."""
        async with self._lock:
            self._cache.clear()

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        async with self._lock:
            self._stats.key_count = len(self._cache)
            total = self._stats.hits + self._stats.misses
            self._stats.hit_ratio = self._stats.hits / total if total > 0 else 0.0
            return self._stats.model_copy()


class DragonflyCache:
    """DragonflyDB-based cache implementation for distributed deployments."""

    def __init__(self, namespace: str = "tripsage"):
        """Initialize the DragonflyDB cache."""
        self.namespace = namespace
        self._stats_key = f"{namespace}:stats"
        self._cache_service = None

    async def _ensure_connected(self) -> None:
        """Ensure DragonflyDB is connected."""
        if self._cache_service is None:
            self._cache_service = await get_cache_instance()

        # Additional connection check if the service has an is_connected property
        if hasattr(self._cache_service, "adapter") and hasattr(
            self._cache_service.adapter, "_direct_service"
        ):
            direct_service = self._cache_service.adapter._direct_service
            if (
                direct_service
                and hasattr(direct_service, "_connected")
                and not direct_service._connected
            ):
                await direct_service.connect()

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        if key.startswith(f"{self.namespace}:"):
            return key
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache."""
        try:
            await self._ensure_connected()
            full_key = self._make_key(key)

            # Use the unified cache service
            result = await self._cache_service.get(full_key)
            if result is not None:
                await self._increment_stat("hits")
                return result

            await self._increment_stat("misses")
            return None

        except Exception as e:
            logger.error(f"Error getting cache value: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in the cache."""
        try:
            await self._ensure_connected()
            full_key = self._make_key(key)

            # Use the unified cache service
            result = await self._cache_service.set(full_key, value, ttl=ttl)

            if result:
                await self._increment_stat("sets")
            return bool(result)

        except Exception as e:
            logger.error(f"Error setting cache value: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        try:
            await self._ensure_connected()
            full_key = self._make_key(key)

            result = await self._cache_service.delete(full_key)
            if result > 0:
                await self._increment_stat("deletes")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting cache value: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching the pattern."""
        try:
            await self._ensure_connected()
            full_pattern = self._make_key(pattern)

            # Get all matching keys - scan_iter might not be available in unified cache
            # Fall back to basic pattern matching if needed
            try:
                keys = []
                # If scan_iter is available on the cache service
                if hasattr(self._cache_service, "scan_iter"):
                    async for key in self._cache_service.scan_iter(match=full_pattern):
                        keys.append(key)
                else:
                    # Alternative approach if scan_iter not available
                    logger.warning(
                        "scan_iter not available, pattern invalidation limited"
                    )
                    return 0

                if keys:
                    count = await self._cache_service.delete(*keys)
                    logger.info(
                        f"Invalidated {count} keys matching pattern {full_pattern}"
                    )
                    return count
                return 0

            except Exception as scan_error:
                logger.warning(f"Pattern scan failed: {scan_error}")
                return 0

        except Exception as e:
            logger.error(f"Error invalidating pattern: {e}")
            return 0

    async def _increment_stat(self, stat: str) -> None:
        """Increment a statistics counter."""
        try:
            await self._ensure_connected()
            # Use basic operations if hincrby not available
            if hasattr(self._cache_service, "hincrby"):
                await self._cache_service.hincrby(self._stats_key, stat, 1)
                await self._cache_service.expire(self._stats_key, 86400)  # 24h expiry
            else:
                # Fallback: use simple counter
                stat_key = f"{self._stats_key}:{stat}"
                current = await self._cache_service.get(stat_key) or "0"
                try:
                    new_value = int(current) + 1
                    await self._cache_service.set(stat_key, str(new_value), ttl=86400)
                except ValueError:
                    await self._cache_service.set(stat_key, "1", ttl=86400)
        except Exception as stats_error:
            logger.debug(
                "Suppressed cache stat increment failure for '%s': %s",
                stat,
                stats_error,
            )

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        try:
            await self._ensure_connected()

            stats = CacheStats()

            # Try to get stats from hash first, then fallback to individual keys
            try:
                if hasattr(self._cache_service, "hgetall"):
                    stats_data = await self._cache_service.hgetall(self._stats_key)
                    if stats_data:
                        stats.hits = int(stats_data.get("hits", 0))
                        stats.misses = int(stats_data.get("misses", 0))
                        stats.sets = int(stats_data.get("sets", 0))
                        stats.deletes = int(stats_data.get("deletes", 0))
                else:
                    # Fallback to individual key retrieval
                    for stat_name in ["hits", "misses", "sets", "deletes"]:
                        stat_key = f"{self._stats_key}:{stat_name}"
                        value = await self._cache_service.get(stat_key) or "0"
                        try:
                            setattr(stats, stat_name, int(value))
                        except ValueError:
                            setattr(stats, stat_name, 0)
            except Exception as stats_error:
                # Use default values if stats retrieval fails
                logger.debug(
                    "Falling back to default cache stats due to error: %s",
                    stats_error,
                )

            # Calculate hit ratio
            total = stats.hits + stats.misses
            stats.hit_ratio = stats.hits / total if total > 0 else 0.0

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return CacheStats()


def generate_cache_key(
    prefix: str, query: str, args: list[Any] | None = None, **kwargs: Any
) -> str:
    """Generate a deterministic cache key."""
    # Normalize the query
    normalized_query = query.lower().strip()

    # Convert args to string
    args_str = ""
    if args:
        args_str = json.dumps([str(arg) for arg in args], sort_keys=True)

    # Sort kwargs for deterministic key generation
    kwargs_str = ""
    if kwargs:
        sorted_items = sorted(kwargs.items())
        kwargs_str = json.dumps(sorted_items, sort_keys=True)

    # Create hash of combined parameters
    combined = f"{prefix}:{normalized_query}:{args_str}:{kwargs_str}"
    hash_obj = hashlib.md5(combined.encode(), usedforsecurity=False)
    query_hash = hash_obj.hexdigest()

    return f"{prefix}:{query_hash}"


def cached(
    content_type: ContentType | str | None = None,
    ttl: int | None = None,
    namespace: str = "tripsage",
    skip_args: list[str] | None = None,
    use_redis: bool = True,
) -> Callable[[F], F]:
    """Decorator for caching async function results."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get settings
            settings = get_settings()

            # Check if Redis/caching is available
            if not settings.redis_url:
                return await func(*args, **kwargs)

            # Check for skip_cache parameter
            skip_cache = kwargs.pop("skip_cache", False)
            if skip_cache:
                return await func(*args, **kwargs)

            # Select cache backend
            cache = redis_cache if use_redis else memory_cache

            # Filter out args to skip from key generation
            key_kwargs = kwargs.copy()
            if skip_args:
                for arg in skip_args:
                    key_kwargs.pop(arg, None)

            # Generate cache key
            function_name = func.__name__
            module_name = func.__module__
            cache_prefix = f"{module_name}.{function_name}"

            # Join string args for query
            query_components = []
            for arg in args:
                if isinstance(arg, str):
                    query_components.append(arg)

            query = ":".join(query_components) if query_components else function_name
            cache_key = generate_cache_key(
                cache_prefix, query, list(args), **key_kwargs
            )

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {function_name}")
                return cached_result

            # Call the function
            logger.debug(f"Cache miss for {function_name}")
            result = await func(*args, **kwargs)

            # Determine TTL
            effective_ttl = ttl
            if effective_ttl is None and content_type is not None:
                if isinstance(content_type, str):
                    content_type_enum = ContentType(content_type)
                else:
                    content_type_enum = content_type
                effective_ttl = get_ttl_for_content_type(content_type_enum)
            elif effective_ttl is None:
                # Use default medium TTL from settings
                settings = get_settings()
                effective_ttl = 3600  # Default medium TTL (1 hour)

            # Cache the result if not None
            if result is not None:
                await cache.set(cache_key, result, ttl=effective_ttl)

            return result

        return cast(F, wrapper)

    return decorator


# Content-specific cache decorators
def cached_realtime(ttl: int | None = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching realtime data (short TTL)."""
    return cached(content_type=ContentType.REALTIME, ttl=ttl or 60, **kwargs)


def cached_time_sensitive(ttl: int | None = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching time-sensitive data."""
    return cached(content_type=ContentType.TIME_SENSITIVE, ttl=ttl or 300, **kwargs)


def cached_daily(ttl: int | None = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching daily data."""
    return cached(content_type=ContentType.DAILY, ttl=ttl or 3600, **kwargs)


def cached_semi_static(ttl: int | None = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching semi-static data."""
    return cached(content_type=ContentType.SEMI_STATIC, ttl=ttl or 28800, **kwargs)


def cached_static(ttl: int | None = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching static data."""
    return cached(content_type=ContentType.STATIC, ttl=ttl or 86400, **kwargs)


async def batch_cache_set(
    items: list[dict[str, Any]], namespace: str = "tripsage", use_redis: bool = True
) -> list[bool]:
    """Set multiple cache entries in batch for improved performance.

    Args:
        items: List of cache items with 'key', 'value', and optional 'ttl' fields
        namespace: Cache namespace
        use_redis: Use DragonflyDB/Redis vs in-memory cache

    Returns:
        List of success/failure booleans for each item
    """
    settings = get_settings()
    if not use_redis or not settings.redis_url:
        results = []
        for item in items:
            success = await memory_cache.set(
                item["key"], item["value"], ttl=item.get("ttl")
            )
            results.append(success)
        return results

    # DragonflyDB batch operations
    try:
        cache_service = await get_cache_instance()

        # Use batch operations if available
        if hasattr(cache_service, "batch_set"):
            # Convert to format expected by batch_set
            batch_items = {}
            ttl = None
            for item in items:
                key = (
                    f"{namespace}:{item['key']}"
                    if not item["key"].startswith(f"{namespace}:")
                    else item["key"]
                )
                batch_items[key] = item["value"]
                if "ttl" in item:
                    ttl = item[
                        "ttl"
                    ]  # Use last TTL found - limitation of batch operation

            success = await cache_service.batch_set(batch_items, ex=ttl)
            return [success] * len(items)  # Return same result for all items

        # Fallback to individual operations
        results = []
        for item in items:
            key = (
                f"{namespace}:{item['key']}"
                if not item["key"].startswith(f"{namespace}:")
                else item["key"]
            )
            success = await cache_service.set(key, item["value"], ttl=item.get("ttl"))
            results.append(bool(success))
        return results

    except Exception as e:
        logger.error(f"Batch cache set failed: {e}")
        return [False] * len(items)


async def batch_cache_get(
    keys: list[str], namespace: str = "tripsage", use_redis: bool = True
) -> list[Any | None]:
    """Get multiple cache entries in batch for improved performance.

    Args:
        keys: List of cache keys to retrieve
        namespace: Cache namespace
        use_redis: Use DragonflyDB/Redis vs in-memory cache

    Returns:
        List of values (None for missing keys)
    """
    settings = get_settings()
    if not use_redis or not settings.redis_url:
        results = []
        for key in keys:
            value = await memory_cache.get(key)
            results.append(value)
        return results

    # DragonflyDB batch operations
    try:
        cache_service = await get_cache_instance()

        # Prepare namespaced keys
        full_keys = [
            f"{namespace}:{key}" if not key.startswith(f"{namespace}:") else key
            for key in keys
        ]

        # Use batch operations if available
        if hasattr(cache_service, "batch_get"):
            result_dict = await cache_service.batch_get(full_keys)
            return [result_dict.get(key) for key in full_keys]

        # Fallback to individual operations
        results = []
        for key in full_keys:
            value = await cache_service.get(key)
            results.append(value)
        return results

    except Exception as e:
        logger.error(f"Batch cache get failed: {e}")
        return [None] * len(keys)


@asynccontextmanager
async def cache_lock(
    lock_name: str,
    timeout: int = 60,
    retry_delay: float = 0.1,
    retry_count: int = 50,
    namespace: str = "tripsage",
) -> AsyncIterator[bool]:
    """Distributed lock using DragonflyDB/Redis for synchronization.

    Args:
        lock_name: Name of the lock
        timeout: Lock timeout in seconds
        retry_delay: Delay between lock acquisition attempts
        retry_count: Maximum number of retry attempts
        namespace: Lock namespace

    Yields:
        True if lock was acquired, False otherwise
    """
    settings = get_settings()
    if not settings.redis_url:
        # Simple local lock for development
        yield True
        return

    cache_service = await get_cache_instance()

    lock_key = f"{namespace}:lock:{lock_name}"
    lock_value = f"{time.time()}:{id(asyncio.current_task())}"

    acquired = False
    for _ in range(retry_count):
        # Check if lock exists
        existing = await cache_service.get(lock_key)
        if existing is None:
            # Try to acquire lock
            success = await cache_service.set(lock_key, lock_value, ttl=timeout)
            if success:
                # Verify we got the lock (handle race condition)
                check_value = await cache_service.get(lock_key)
                if check_value == lock_value:
                    acquired = True
                    break
        await asyncio.sleep(retry_delay)

    try:
        yield acquired
    finally:
        if acquired:
            # Only delete if we still own the lock
            current_value = await cache_service.get(lock_key)
            if current_value == lock_value:
                await cache_service.delete(lock_key)


# Create alias for backward compatibility
RedisCache = DragonflyCache

# Initialize cache instances
memory_cache = InMemoryCache()
redis_cache = DragonflyCache()


# Export convenience functions using DragonflyDB by default
async def get_cache(key: str, namespace: str = "tripsage") -> Any | None:
    """Get a value from the cache (DragonflyDB by default)."""
    return await redis_cache.get(key)


async def set_cache(
    key: str,
    value: Any,
    ttl: int | None = None,
    namespace: str = "tripsage",
) -> bool:
    """Set a value in the cache (DragonflyDB by default)."""
    return await redis_cache.set(key, value, ttl=ttl)


async def delete_cache(key: str, namespace: str = "tripsage") -> bool:
    """Delete a value from the cache (DragonflyDB by default)."""
    return await redis_cache.delete(key)


async def get_cache_stats() -> CacheStats:
    """Get cache statistics (DragonflyDB by default)."""
    return await redis_cache.get_stats()


async def invalidate_pattern(pattern: str, namespace: str = "tripsage") -> int:
    """Invalidate all cache keys matching the pattern."""
    return await redis_cache.invalidate_pattern(pattern)


def determine_content_type(query: str, domains: list[str] | None = None) -> ContentType:
    """Determine content type based on query and domains."""
    # Simple heuristic-based content type determination
    query_lower = query.lower()

    # Check for time-sensitive keywords
    time_keywords = ["news", "latest", "breaking", "current"]
    if any(keyword in query_lower for keyword in time_keywords):
        return ContentType.TIME_SENSITIVE

    # Check for realtime keywords
    if any(keyword in query_lower for keyword in ["live", "real-time", "now", "price"]):
        return ContentType.REALTIME

    # Check for static content keywords
    static_keywords = ["history", "documentation", "guide", "tutorial"]
    if any(keyword in query_lower for keyword in static_keywords):
        return ContentType.STATIC

    # Check domains if provided
    if domains:
        # News domains are time-sensitive
        news_domains = ["cnn.com", "bbc.com", "reuters.com", "ap.org", "nytimes.com"]
        if any(domain in domains for domain in news_domains):
            return ContentType.TIME_SENSITIVE

        # Documentation domains are static
        doc_domains = ["wikipedia.org", "docs.", "github.io", "readthedocs.io"]
        for domain in domains:
            if any(doc_domain in domain for doc_domain in doc_domains):
                return ContentType.STATIC

    # Default to daily for most travel-related content
    return ContentType.DAILY


async def prefetch_cache_keys(pattern: str, namespace: str = "tripsage") -> list[str]:
    """Prefetch cache keys matching a pattern for batch operations."""
    try:
        cache_service = await get_cache_instance()

        # Build the full pattern
        full_pattern = (
            f"{namespace}:{pattern}"
            if not pattern.startswith(f"{namespace}:")
            else pattern
        )

        keys = []
        # If scan_iter is available on the cache service
        if hasattr(cache_service, "scan_iter"):
            async for key in cache_service.scan_iter(match=full_pattern):
                keys.append(key)
        else:
            logger.warning("scan_iter not available, prefetch operation limited")

        return keys

    except Exception as e:
        logger.error(f"Error prefetching cache keys: {e}")
        return []


__all__ = [
    # Cache instances
    "memory_cache",
    "redis_cache",
    # Basic operations
    "get_cache",
    "set_cache",
    "delete_cache",
    "get_cache_stats",
    # Utility functions
    "generate_cache_key",
    "get_ttl_for_content_type",
    "determine_content_type",
    "invalidate_pattern",
    "prefetch_cache_keys",
    # Batch operations
    "batch_cache_set",
    "batch_cache_get",
    # Distributed locks
    "cache_lock",
    # Decorators
    "cached",
    "cached_realtime",
    "cached_time_sensitive",
    "cached_daily",
    "cached_semi_static",
    "cached_static",
    # Models
    "CacheStats",
    "ContentType",
]
