"""Cache implementation for WebCrawl MCP."""

import asyncio
import json
import time
from typing import Any, Dict, Optional, Union

from src.mcp.webcrawl.config import Config
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class CacheService:
    """Cache service for WebCrawl MCP.

    This service implements a two-level caching strategy:
    1. In-memory cache for fast access
    2. Redis cache for persistence across restarts (if available)
    """

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the cache service.

        Args:
            redis_url: Optional Redis URL for external cache
        """
        # Initialize in-memory cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

        # Initialize Redis connection if available
        self._redis = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self._redis = redis.from_url(redis_url)
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Redis cache: {str(e)}")

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        # Check in-memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]

            # Check if expired
            if entry["expires_at"] > time.time():
                logger.debug(f"Cache hit (memory): {key}")
                return entry["value"]
            else:
                # Remove expired entry
                del self._memory_cache[key]

        # Check Redis cache if available
        if self._redis:
            try:
                cached_data = await self._redis.get(f"webcrawl:{key}")

                if cached_data:
                    # Parse cached data
                    entry = json.loads(cached_data)

                    # Check if expired
                    if entry["expires_at"] > time.time():
                        # Update in-memory cache
                        self._memory_cache[key] = entry

                        logger.debug(f"Cache hit (redis): {key}")
                        return entry["value"]
                    else:
                        # Remove expired entry
                        await self._redis.delete(f"webcrawl:{key}")
            except Exception as e:
                logger.error(f"Redis cache error on get: {str(e)}")

        # Cache miss
        logger.debug(f"Cache miss: {key}")
        return None

    async def set(
        self, key: str, value: Any, ttl: int = Config.CACHE_TTL_DEFAULT
    ) -> bool:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        # Calculate expiration time
        expires_at = time.time() + ttl

        # Create cache entry
        entry = {"value": value, "expires_at": expires_at}

        # Update in-memory cache
        self._memory_cache[key] = entry

        # Update Redis cache if available
        if self._redis:
            try:
                # Serialize cache entry
                cached_data = json.dumps(entry)

                # Set in Redis with expiration
                await self._redis.setex(f"webcrawl:{key}", ttl, cached_data)
            except Exception as e:
                logger.error(f"Redis cache error on set: {str(e)}")
                # Continue even if Redis fails

        return True

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        # Remove from in-memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]

        # Remove from Redis cache if available
        if self._redis:
            try:
                await self._redis.delete(f"webcrawl:{key}")
            except Exception as e:
                logger.error(f"Redis cache error on delete: {str(e)}")
                return False

        return True

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get the remaining TTL for a cache key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds or None if key not found
        """
        # Check in-memory cache
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            remaining = entry["expires_at"] - time.time()

            if remaining > 0:
                return int(remaining)

        # Check Redis cache if available
        if self._redis:
            try:
                ttl = await self._redis.ttl(f"webcrawl:{key}")

                if ttl > 0:
                    return ttl
            except Exception as e:
                logger.error(f"Redis cache error on get_ttl: {str(e)}")

        return None

    async def clear(self) -> bool:
        """Clear the entire cache.

        Returns:
            True if successful, False otherwise
        """
        # Clear in-memory cache
        self._memory_cache.clear()

        # Clear Redis cache if available
        if self._redis:
            try:
                # Get all webcrawl keys
                keys = await self._redis.keys("webcrawl:*")

                # Delete all keys
                if keys:
                    await self._redis.delete(*keys)
            except Exception as e:
                logger.error(f"Redis cache error on clear: {str(e)}")
                return False

        return True

    async def get_or_set(
        self, key: str, getter: callable, ttl: int = Config.CACHE_TTL_DEFAULT
    ) -> Any:
        """Get a value from cache or compute and store it if not available.

        Args:
            key: Cache key
            getter: Async function to compute the value if not in cache
            ttl: Time-to-live in seconds

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        cached_value = await self.get(key)

        if cached_value is not None:
            return cached_value

        # Compute value
        computed_value = await getter()

        # Store in cache
        await self.set(key, computed_value, ttl)

        return computed_value

    def get_cache_ttl_for_url(self, url: str) -> int:
        """Determine appropriate TTL for a URL based on its characteristics.

        Args:
            url: The URL to analyze

        Returns:
            Appropriate TTL in seconds
        """
        # Check if it's a news or frequently updated site
        if any(domain in url.lower() for domain in Config.FREQUENT_UPDATE_DOMAINS):
            return Config.CACHE_TTL_NEWS

        # Default TTL
        return Config.CACHE_TTL_DEFAULT
