"""Cache service for TripSage Core using DragonflyDB.

This module provides high-performance caching capabilities
using DragonflyDB (Redis-compatible) with 25x performance improvement
over traditional Redis implementations.
"""

import json
import logging
from typing import Any

import redis.asyncio as redis

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreServiceError


logger = logging.getLogger(__name__)


class CacheService:
    """DragonflyDB cache service for high-performance caching operations.

    This service provides:
    - Redis-compatible interface with DragonflyDB backend
    - JSON value serialization/deserialization
    - TTL-based expiration management
    - Batch operations support
    - Performance monitoring
    - Connection pooling
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the cache service.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self._client: redis.Redis | None = None
        self._connection_pool: redis.ConnectionPool | None = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to DragonflyDB."""
        return self._is_connected and self._client is not None

    async def connect(self) -> None:
        """Establish connection to DragonflyDB server."""
        if self._is_connected:
            return

        # Skip connection if redis_url is None (testing/disabled mode)
        if self.settings.redis_url is None:
            logger.info(
                "Redis URL not configured, cache service will operate in disabled mode"
            )
            self._is_connected = False
            return

        try:
            # Get DragonflyDB URL from settings
            redis_url = self.settings.redis_url

            # Add password to URL if configured
            if self.settings.redis_password:
                # Parse URL and add password
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(redis_url)
                # Reconstruct with password
                if parsed.username:
                    netloc = (
                        f"{parsed.username}:{self.settings.redis_password}@"
                        f"{parsed.hostname}"
                    )
                else:
                    netloc = f":{self.settings.redis_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                redis_url = urlunparse(
                    (
                        parsed.scheme,
                        netloc,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )

            safe_url = redis_url.replace(self.settings.redis_password or "", "***")
            logger.info(f"Connecting to DragonflyDB at {safe_url}")

            # Create connection pool for better performance
            self._connection_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=self.settings.redis_max_connections,
                retry_on_timeout=True,
                decode_responses=False,  # We handle JSON encoding/decoding manually
            )

            self._client = redis.Redis(connection_pool=self._connection_pool)

            # Test the connection
            await self._client.ping()
            self._is_connected = True

            logger.info("Successfully connected to DragonflyDB cache service")

        except Exception as e:
            logger.exception("Failed to connect to DragonflyDB")
            self._is_connected = False
            raise CoreServiceError(
                message=f"Failed to connect to cache service: {e!s}",
                code="CACHE_CONNECTION_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Close connection to DragonflyDB server."""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"Error closing DragonflyDB connection: {e}")
            finally:
                self._client = None
                self._is_connected = False

        if self._connection_pool:
            try:
                await self._connection_pool.disconnect()
            except Exception as e:
                logger.warning(f"Error closing DragonflyDB connection pool: {e}")
            finally:
                self._connection_pool = None

        logger.info("Disconnected from DragonflyDB cache service")

    async def ensure_connected(self) -> None:
        """Ensure the service is connected, reconnect if necessary."""
        if not self.is_connected:
            await self.connect()

    # JSON operations

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store a JSON-serializable value in cache.

        Args:
            key: Cache key
            value: Value to store (must be JSON-serializable)
            ttl: Time to live in seconds (uses default if not specified)

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        # Return success in disabled mode
        if not self.is_connected:
            return True

        try:
            # Use default TTL if not specified (flat config)
            if ttl is None:
                ttl = 3600  # Default medium TTL (1 hour)

            json_value = json.dumps(value, default=str)
            result = await self._client.set(key, json_value, ex=ttl)
            return result is True
        except Exception as e:
            logger.exception(f"Failed to set JSON value for key {key}")
            raise CoreServiceError(
                message=f"Failed to set cache value for key '{key}'",
                code="CACHE_SET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    async def get_json(self, key: str, default: Any = None) -> Any:
        """Retrieve and deserialize a JSON value from cache.

        Args:
            key: Cache key
            default: Default value if key doesn't exist

        Returns:
            Deserialized value or default
        """
        await self.ensure_connected()

        # Return default in disabled mode
        if not self.is_connected:
            return default

        try:
            value = await self._client.get(key)
            if value is None:
                return default
            return json.loads(value)
        except json.JSONDecodeError:
            logger.exception(f"Failed to decode JSON value for key {key}")
            return default
        except Exception as e:
            logger.exception(f"Failed to get JSON value for key {key}")
            raise CoreServiceError(
                message=f"Failed to get cache value for key '{key}'",
                code="CACHE_GET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # String operations

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set a string value in cache.

        Args:
            key: Cache key
            value: String value to store
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        # Return success in disabled mode
        if not self.is_connected:
            return True

        try:
            if ttl is None:
                ttl = 3600  # Default medium TTL (1 hour)

            return await self._client.setex(key, ttl, value)
        except Exception as e:
            logger.exception(f"Failed to set key {key}")
            raise CoreServiceError(
                message=f"Failed to set cache key '{key}'",
                code="CACHE_SET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    async def get(self, key: str) -> str | None:
        """Get a string value from cache.

        Args:
            key: Cache key

        Returns:
            The value as string or None if not found
        """
        await self.ensure_connected()

        # Return None in disabled mode
        if not self.is_connected:
            return None

        try:
            value = await self._client.get(key)
            return value.decode("utf-8") if value else None
        except Exception as e:
            logger.exception(f"Failed to get key {key}")
            raise CoreServiceError(
                message=f"Failed to get cache key '{key}'",
                code="CACHE_GET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # Key operations

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys from cache.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        await self.ensure_connected()

        # Return length of keys in disabled mode (simulate successful deletion)
        if not self.is_connected:
            return len(keys)

        try:
            return await self._client.delete(*keys)
        except Exception as e:
            logger.exception(f"Failed to delete keys {keys}")
            raise CoreServiceError(
                message="Failed to delete cache keys",
                code="CACHE_DELETE_FAILED",
                service="CacheService",
                details={"keys": keys, "error": str(e)},
            ) from e

    async def exists(self, *keys: str) -> int:
        """Check if keys exist in cache.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        await self.ensure_connected()

        # Return 0 in disabled mode (no keys exist)
        if not self.is_connected:
            return 0

        try:
            return await self._client.exists(*keys)
        except Exception as e:
            logger.exception(f"Failed to check existence of keys {keys}")
            raise CoreServiceError(
                message="Failed to check cache key existence",
                code="CACHE_EXISTS_FAILED",
                service="CacheService",
                details={"keys": keys, "error": str(e)},
            ) from e

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        # Return True in disabled mode (simulate success)
        if not self.is_connected:
            return True

        try:
            return await self._client.expire(key, seconds)
        except Exception as e:
            logger.exception(f"Failed to set expiration for key {key}")
            raise CoreServiceError(
                message=f"Failed to set expiration for cache key '{key}'",
                code="CACHE_EXPIRE_FAILED",
                service="CacheService",
                details={"key": key, "seconds": seconds, "error": str(e)},
            ) from e

    async def ttl(self, key: str) -> int:
        """Get time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        await self.ensure_connected()

        # Return -2 in disabled mode (key doesn't exist)
        if not self.is_connected:
            return -2

        try:
            return await self._client.ttl(key)
        except Exception:
            logger.exception(f"Failed to get TTL for key {key}")
            return -2

    # Atomic operations

    async def incr(self, key: str) -> int | None:
        """Increment a counter in cache.

        Args:
            key: Counter key

        Returns:
            The new counter value or None if failed
        """
        await self.ensure_connected()

        # Return None in disabled mode (operation not available)
        if not self.is_connected:
            return None

        try:
            return await self._client.incr(key)
        except Exception:
            logger.exception(f"Failed to increment key {key}")
            return None

    async def decr(self, key: str) -> int | None:
        """Decrement a counter in cache.

        Args:
            key: Counter key

        Returns:
            The new counter value or None if failed
        """
        await self.ensure_connected()

        # Return None in disabled mode (operation not available)
        if not self.is_connected:
            return None

        try:
            return await self._client.decr(key)
        except Exception:
            logger.exception(f"Failed to decrement key {key}")
            return None

    # Batch operations

    def pipeline(self):
        """Create a pipeline for batch operations.

        Returns:
            Redis pipeline object for batching commands

        Raises:
            CoreServiceError: If not connected
        """
        if not self._client:
            raise CoreServiceError(
                message="Cache service not connected",
                code="CACHE_NOT_CONNECTED",
                service="CacheService",
            )
        return self._client.pipeline()

    async def mget(self, keys: list[str]) -> list[str | None]:
        """Get multiple values at once.

        Args:
            keys: List of keys to get

        Returns:
            List of values (None for missing keys)
        """
        await self.ensure_connected()

        # Return list of None values in disabled mode
        if not self.is_connected:
            return [None] * len(keys)

        try:
            values = await self._client.mget(keys)
            return [v.decode("utf-8") if v else None for v in values]
        except Exception as e:
            logger.exception("Failed to mget keys")
            raise CoreServiceError(
                message="Failed to get multiple cache keys",
                code="CACHE_MGET_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    async def mset(self, mapping: dict[str, str]) -> bool:
        """Set multiple key-value pairs at once.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            True if successful
        """
        await self.ensure_connected()

        # Return True in disabled mode (simulate success)
        if not self.is_connected:
            return True

        try:
            return await self._client.mset(mapping)
        except Exception as e:
            logger.exception("Failed to mset")
            raise CoreServiceError(
                message="Failed to set multiple cache keys",
                code="CACHE_MSET_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    # Pattern-based operations

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            List of matching keys
        """
        await self.ensure_connected()

        # Return empty list in disabled mode
        if not self.is_connected:
            return []

        try:
            keys = await self._client.keys(pattern)
            return [k.decode("utf-8") for k in keys]
        except Exception:
            logger.exception(f"Failed to get keys with pattern {pattern}")
            return []

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Key pattern to delete

        Returns:
            Number of keys deleted
        """
        keys = await self.keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0

    # Cache management

    async def flushdb(self) -> bool:
        """Clear all data from the current database.

        WARNING: This will delete all data!

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        try:
            result = await self._client.flushdb()
            return result is True
        except Exception:
            logger.exception("Failed to flush database")
            return False

    async def info(self, section: str | None = None) -> dict[str, Any]:
        """Get DragonflyDB server information.

        Args:
            section: Specific info section to retrieve

        Returns:
            Server information dictionary
        """
        await self.ensure_connected()

        try:
            info_str = await self._client.info(section)
            # Parse the info string into a dictionary
            info_dict = {}
            for line in info_str.split("\n"):
                if ":" in line and not line.startswith("#"):
                    key, value = line.split(":", 1)
                    info_dict[key] = value
            return info_dict
        except Exception:
            logger.exception("Failed to get server info")
            return {}

    # Health check

    async def health_check(self) -> bool:
        """Check cache service connectivity.

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.ensure_connected()

            # Return False in disabled mode (not healthy)
            if not self.is_connected:
                return False

            return await self._client.ping()
        except Exception:
            logger.exception("Cache health check failed")
            return False

    # Convenience methods with TTL presets

    async def set_short(self, key: str, value: Any) -> bool:
        """Set a value with short TTL (5 minutes by default).

        Args:
            key: Cache key
            value: Value to store

        Returns:
            True if successful
        """
        return await self.set_json(key, value, ttl=300)  # Short TTL (5 minutes)

    async def set_medium(self, key: str, value: Any) -> bool:
        """Set a value with medium TTL (1 hour by default).

        Args:
            key: Cache key
            value: Value to store

        Returns:
            True if successful
        """
        return await self.set_json(key, value, ttl=3600)  # Medium TTL (1 hour)

    async def set_long(self, key: str, value: Any) -> bool:
        """Set a value with long TTL (24 hours by default).

        Args:
            key: Cache key
            value: Value to store

        Returns:
            True if successful
        """
        return await self.set_json(key, value, ttl=86400)  # Long TTL (24 hours)


# Global service instance
_cache_service: CacheService | None = None


async def get_cache_service() -> CacheService:
    """Get the global cache service instance.

    Returns:
        Connected CacheService instance
    """
    global _cache_service

    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.connect()

    return _cache_service


async def close_cache_service() -> None:
    """Close the global cache service instance."""
    global _cache_service

    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None
