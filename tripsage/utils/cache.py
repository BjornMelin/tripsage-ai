"""
Unified caching utilities for TripSage.

This module provides both in-memory and Redis-based caching functionality
with content-aware TTL settings and performance monitoring.
"""

import asyncio
import functools
import hashlib
import json
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, TypeVar, Union, cast

from pydantic import BaseModel, Field

from tripsage.services.redis_service import redis_service
from tripsage.utils.content_types import ContentType
from tripsage.utils.logging import get_logger
from tripsage.utils.settings import settings

logger = get_logger(__name__)

# Type variables
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


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
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._stats = CacheStats()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        async with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            cache_item = self._cache[key]

            # Check if item has expired
            if "expires_at" in cache_item and cache_item["expires_at"] < time.time():
                del self._cache[key]
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            return cache_item["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
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


class RedisCache:
    """Redis-based cache implementation for distributed deployments."""

    def __init__(self, namespace: str = "tripsage"):
        """Initialize the Redis cache."""
        self.namespace = namespace
        self._stats_key = f"{namespace}:stats"

    async def _ensure_connected(self) -> None:
        """Ensure Redis is connected."""
        if not redis_service.is_connected:
            await redis_service.connect()

    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        if key.startswith(f"{self.namespace}:"):
            return key
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        try:
            await self._ensure_connected()
            full_key = self._make_key(key)
            
            # Try JSON first, fallback to string
            result = await redis_service.get_json(full_key)
            if result is not None:
                await self._increment_stat("hits")
                return result
            
            result = await redis_service.get(full_key)
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
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set a value in the cache."""
        try:
            await self._ensure_connected()
            full_key = self._make_key(key)
            
            # Auto-serialize complex objects
            if isinstance(value, (dict, list)):
                result = await redis_service.set_json(full_key, value, ex=ttl)
            else:
                result = await redis_service.set(full_key, value, ex=ttl, nx=nx, xx=xx)
                
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
            
            result = await redis_service.delete(full_key)
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
            
            # Get all matching keys
            keys = []
            async for key in redis_service.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                count = await redis_service.delete(*keys)
                logger.info(f"Invalidated {count} keys matching pattern {full_pattern}")
                return count
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache pattern: {e}")
            return 0

    async def _increment_stat(self, stat: str) -> None:
        """Increment a statistics counter."""
        try:
            await redis_service.hincrby(self._stats_key, stat, 1)
            await redis_service.expire(self._stats_key, 86400)  # 24h expiry
        except Exception:
            pass  # Don't fail on stats errors

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        try:
            await self._ensure_connected()
            
            # Get stats from hash
            stats_data = await redis_service.hgetall(self._stats_key)
            
            # Get key count
            key_count = 0
            async for _ in redis_service.scan_iter(match=f"{self.namespace}:*"):
                key_count += 1
            
            # Get memory info
            info = await redis_service.info("memory")
            used_memory = info.get("used_memory", 0)
            size_mb = used_memory / (1024 * 1024) if used_memory > 0 else 0.0
            
            # Calculate hit ratio
            hits = int(stats_data.get("hits", 0))
            misses = int(stats_data.get("misses", 0))
            total = hits + misses
            hit_ratio = hits / total if total > 0 else 0.0
            
            return CacheStats(
                hits=hits,
                misses=misses,
                hit_ratio=hit_ratio,
                sets=int(stats_data.get("sets", 0)),
                deletes=int(stats_data.get("deletes", 0)),
                key_count=key_count,
                size_mb=size_mb
            )
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return CacheStats()


def generate_cache_key(
    prefix: str, 
    query: str, 
    args: Optional[List[Any]] = None, 
    **kwargs: Any
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
    hash_obj = hashlib.md5(combined.encode())
    query_hash = hash_obj.hexdigest()
    
    return f"{prefix}:{query_hash}"


def get_ttl_for_content_type(content_type: ContentType) -> int:
    """Get the appropriate TTL for a content type."""
    ttl_map = {
        ContentType.REALTIME: 60,        # 1 minute
        ContentType.TIME_SENSITIVE: 300,  # 5 minutes
        ContentType.DAILY: 3600,         # 1 hour
        ContentType.SEMI_STATIC: 28800,  # 8 hours
        ContentType.STATIC: 86400,       # 24 hours
    }
    return ttl_map.get(content_type, 3600)  # Default 1 hour


def cached(
    content_type: Optional[Union[ContentType, str]] = None,
    ttl: Optional[int] = None,
    namespace: str = "tripsage",
    skip_args: Optional[List[str]] = None,
    use_redis: bool = True
) -> Callable[[F], F]:
    """Decorator for caching async function results."""
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if caching is enabled
            if not settings.use_cache:
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
            cache_key = generate_cache_key(cache_prefix, query, list(args), **key_kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {function_name}")
                return cached_result
            
            # Call the function
            logger.debug(f"Cache miss for {function_name}")
            result = await func(*args, **kwargs)
            
            # Determine TTL
            if ttl is None and content_type is not None:
                if isinstance(content_type, str):
                    content_type_enum = ContentType(content_type)
                else:
                    content_type_enum = content_type
                ttl = get_ttl_for_content_type(content_type_enum)
            
            # Cache the result if not None
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return cast(F, wrapper)
    
    return decorator


# Content-specific cache decorators
def cached_realtime(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching realtime data (short TTL)."""
    return cached(content_type=ContentType.REALTIME, ttl=ttl or 60, **kwargs)


def cached_time_sensitive(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching time-sensitive data."""
    return cached(content_type=ContentType.TIME_SENSITIVE, ttl=ttl or 300, **kwargs)


def cached_daily(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching daily data."""
    return cached(content_type=ContentType.DAILY, ttl=ttl or 3600, **kwargs)


def cached_semi_static(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching semi-static data."""
    return cached(content_type=ContentType.SEMI_STATIC, ttl=ttl or 28800, **kwargs)


def cached_static(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching static data."""
    return cached(content_type=ContentType.STATIC, ttl=ttl or 86400, **kwargs)


async def batch_cache_set(
    items: List[Dict[str, Any]], 
    namespace: str = "tripsage",
    use_redis: bool = True
) -> List[bool]:
    """Set multiple values in cache using pipeline for performance."""
    if not use_redis:
        # Fallback to sequential for in-memory cache
        results = []
        for item in items:
            result = await memory_cache.set(
                item["key"], 
                item["value"], 
                ttl=item.get("ttl")
            )
            results.append(result)
        return results
    
    try:
        await redis_cache._ensure_connected()
        
        async with redis_service.pipeline() as pipe:
            for item in items:
                key = redis_cache._make_key(item["key"])
                value = item["value"]
                ttl = item.get("ttl")
                
                if isinstance(value, (dict, list)):
                    pipe.set(key, json.dumps(value, default=str), ex=ttl)
                else:
                    pipe.set(key, str(value), ex=ttl)
            
            results = await pipe.execute()
            return [bool(result) for result in results]
            
    except Exception as e:
        logger.error(f"Error batch setting cache values: {e}")
        return [False] * len(items)


async def batch_cache_get(
    keys: List[str], 
    namespace: str = "tripsage",
    use_redis: bool = True
) -> List[Optional[Any]]:
    """Get multiple values from cache using pipeline for performance."""
    if not use_redis:
        # Fallback to sequential for in-memory cache
        results = []
        for key in keys:
            result = await memory_cache.get(key)
            results.append(result)
        return results
    
    try:
        await redis_cache._ensure_connected()
        
        # Prepare namespaced keys
        full_keys = [redis_cache._make_key(key) for key in keys]
        
        async with redis_service.pipeline() as pipe:
            for key in full_keys:
                pipe.get(key)
            
            results = await pipe.execute()
            
            # Process results (auto-deserialize JSON)
            processed_results = []
            for result in results:
                if result is None:
                    processed_results.append(None)
                else:
                    try:
                        # Try to parse as JSON
                        processed_results.append(json.loads(result))
                    except (json.JSONDecodeError, TypeError):
                        # Fallback to string
                        processed_results.append(result)
            
            return processed_results
            
    except Exception as e:
        logger.error(f"Error batch getting cache values: {e}")
        return [None] * len(keys)


@asynccontextmanager
async def cache_lock(
    lock_name: str,
    timeout: int = 60,
    retry_delay: float = 0.1,
    retry_count: int = 50,
    namespace: str = "tripsage"
) -> AsyncIterator[bool]:
    """Distributed lock using Redis."""
    await redis_cache._ensure_connected()
    
    lock_key = f"{namespace}:lock:{lock_name}"
    lock_value = f"{time.time()}:{asyncio.current_task().get_name()}"
    
    # Try to acquire lock
    acquired = False
    for _ in range(retry_count):
        success = await redis_service.set(lock_key, lock_value, ex=timeout, nx=True)
        if success:
            acquired = True
            break
        await asyncio.sleep(retry_delay)
    
    try:
        yield acquired
    finally:
        # Release lock if we acquired it
        if acquired:
            # Only delete if we still own the lock
            current_value = await redis_service.get(lock_key)
            if current_value == lock_value:
                await redis_service.delete(lock_key)


# Initialize cache instances
memory_cache = InMemoryCache()
redis_cache = RedisCache()

# Export convenience functions using Redis by default
async def get_cache(key: str, namespace: str = "tripsage") -> Optional[Any]:
    """Get a value from the cache (Redis by default)."""
    return await redis_cache.get(key)


async def set_cache(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
    content_type: Optional[Union[ContentType, str]] = None,
    namespace: str = "tripsage"
) -> bool:
    """Set a value in the cache (Redis by default)."""
    if ttl is None and content_type is not None:
        if isinstance(content_type, str):
            content_type = ContentType(content_type)
        ttl = get_ttl_for_content_type(content_type)
    return await redis_cache.set(key, value, ttl=ttl)


async def delete_cache(key: str, namespace: str = "tripsage") -> bool:
    """Delete a value from the cache (Redis by default)."""
    return await redis_cache.delete(key)


async def get_cache_stats() -> CacheStats:
    """Get cache statistics (Redis by default)."""
    return await redis_cache.get_stats()


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