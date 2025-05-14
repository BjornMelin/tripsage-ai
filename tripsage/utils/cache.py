"""
Caching utilities for TripSage.

This module provides caching functionality for TripSage, supporting
in-memory caching and Redis-based caching for distributed deployments.
"""

import asyncio
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from .logging import get_logger
from .settings import settings

logger = get_logger(__name__)

# Type variables for type hinting
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class InMemoryCache:
    """Simple in-memory cache implementation."""

    def __init__(self):
        """Initialize the in-memory cache."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        async with self._lock:
            if key not in self._cache:
                return None

            cache_item = self._cache[key]

            # Check if item has expired
            if "expires_at" in cache_item and cache_item["expires_at"] < time.time():
                del self._cache[key]
                return None

            return cache_item["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for no expiration)
        """
        async with self._lock:
            expires_at = None if ttl is None else time.time() + ttl
            self._cache[key] = {"value": value, "expires_at": expires_at}

    async def delete(self, key: str) -> None:
        """Delete a value from the cache.

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self) -> None:
        """Clear all values from the cache."""
        async with self._lock:
            self._cache.clear()

    def cached(self, namespace: str, ttl: Optional[int] = None) -> Callable[[F], F]:
        """Decorator for caching async function results.

        Args:
            namespace: Cache namespace
            ttl: Time-to-live in seconds (None for no expiration)

        Returns:
            Decorated function
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Check if caching is enabled
                if not settings.use_cache:
                    return await func(*args, **kwargs)

                # Check for skip_cache parameter
                skip_cache = False
                if "skip_cache" in kwargs:
                    skip_cache = kwargs["skip_cache"]

                if skip_cache:
                    return await func(*args, **kwargs)

                # Generate cache key
                cache_key = kwargs.get("cache_key")
                if not cache_key:
                    # Create a string representation of args and kwargs
                    args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
                    kwargs_str = json.dumps(
                        {k: str(v) for k, v in kwargs.items() if k != "skip_cache"},
                        sort_keys=True,
                    )

                    # Create hash of the function name and arguments
                    key_hash = hashlib.md5(
                        f"{namespace}:{func.__name__}:{args_str}:{kwargs_str}".encode()
                    ).hexdigest()

                    cache_key = f"{namespace}:{func.__name__}:{key_hash}"

                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result

                # Call the function and cache the result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl)

                return result

            return cast(F, wrapper)

        return decorator


# TODO: Implement RedisCache class for distributed deployments


# Create the appropriate cache instance
cache = InMemoryCache()


# Export the cache instance
__all__ = ["cache"]
