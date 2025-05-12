"""
Redis-based caching implementation for TripSage.

This module provides a Redis-based caching system with TTL support,
serialization/deserialization of complex data structures, and
convenience decorators for caching function results.
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

import redis.asyncio as redis

from ..utils.logging import get_module_logger
from ..utils.settings import settings

logger = get_module_logger(__name__)

# Type variables for function decorator
T = TypeVar("T")
FuncT = TypeVar("FuncT", bound=Callable[..., Any])


class RedisCache:
    """Redis-based caching system for TripSage."""

    def __init__(self, url: Optional[str] = None):
        """Initialize the Redis cache.

        Args:
            url: Redis connection URL, defaults to config value if not provided
        """
        self.url = url or str(settings.redis.url)
        self.redis = redis.from_url(self.url)
        logger.info("Initialized Redis cache at %s", self.url)

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            The cached value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Error retrieving from cache: %s", str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value)
            return await self.redis.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.warning("Error setting cache: %s", str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found or error
        """
        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            logger.warning("Error deleting from cache: %s", str(e))
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching the pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Error invalidating cache pattern: %s", str(e))
            return 0

    def cache_key(self, prefix: str, *args: Any, **kwargs: Any) -> str:
        """Generate a cache key from function arguments.

        Args:
            prefix: Key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Generated cache key
        """
        # Convert args and kwargs to a stable string representation
        args_str = str(args) if args else ""
        kwargs_str = str(sorted(kwargs.items())) if kwargs else ""
        combined = f"{args_str}{kwargs_str}"

        # Create a hash of the arguments
        hash_obj = hashlib.md5(combined.encode())
        args_hash = hash_obj.hexdigest()

        return f"{prefix}:{args_hash}"

    def cached(
        self, prefix: str, ttl: Optional[int] = None
    ) -> Callable[[FuncT], FuncT]:
        """Decorator for caching function results.

        Args:
            prefix: Key prefix
            ttl: Cache TTL in seconds

        Returns:
            Decorator function
        """

        def decorator(func: FuncT) -> FuncT:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Skip cache if explicitly requested
                skip_cache = kwargs.pop("skip_cache", False)

                # Generate cache key
                key = self.cache_key(prefix, *args, **kwargs)

                if not skip_cache:
                    # Try to get from cache
                    cached_value = await self.get(key)
                    if cached_value is not None:
                        logger.debug("Cache hit for %s", key)
                        return cached_value

                # Execute the function
                logger.debug("Cache miss for %s", key)
                result = await func(*args, **kwargs)

                # Store in cache if result is not None
                if result is not None:
                    await self.set(key, result, ttl)

                return result

            return cast(FuncT, wrapper)

        return decorator


# Global cache instance
redis_cache = RedisCache()


def get_cache() -> RedisCache:
    """Get the global cache instance.

    Returns:
        The global RedisCache instance
    """
    return redis_cache
