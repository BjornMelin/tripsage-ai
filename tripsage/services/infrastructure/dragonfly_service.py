"""
DragonflyDB Service for TripSage

High-performance cache service using DragonflyDB (Redis-compatible).
Provides 25x performance improvement over traditional Redis implementations.
"""

import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

from tripsage.api.core.config import get_settings

logger = logging.getLogger(__name__)


class DragonflyService:
    """DragonflyDB cache service for high-performance caching operations."""

    def __init__(self):
        """Initialize the DragonflyDB service."""
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._settings = get_settings()
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to DragonflyDB."""
        return self._is_connected and self._client is not None

    async def connect(self) -> None:
        """Establish connection to DragonflyDB server."""
        if self._is_connected:
            return

        try:
            # DragonflyDB uses Redis protocol, so we use redis.Redis client
            # For production, you would use the DragonflyDB server endpoint
            redis_url = getattr(
                self._settings, "dragonfly_url", "redis://localhost:6379/0"
            )

            # Create connection pool for better performance
            self._connection_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                decode_responses=False,  # We handle JSON encoding/decoding manually
            )

            self._client = redis.Redis(connection_pool=self._connection_pool)

            # Test the connection
            await self._client.ping()
            self._is_connected = True

            logger.info("Successfully connected to DragonflyDB")

        except Exception as e:
            logger.error(f"Failed to connect to DragonflyDB: {e}")
            self._is_connected = False
            raise

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

        logger.info("Disconnected from DragonflyDB")

    async def ensure_connected(self) -> None:
        """Ensure the service is connected, reconnect if necessary."""
        if not self.is_connected:
            await self.connect()

    async def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Store a JSON-serializable value in DragonflyDB.

        Args:
            key: Cache key
            value: Value to store (must be JSON-serializable)
            ex: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        try:
            json_value = json.dumps(value, default=str)
            result = await self._client.set(key, json_value, ex=ex)
            return result is True
        except Exception as e:
            logger.error(f"Failed to set JSON value for key {key}: {e}")
            return False

    async def get_json(self, key: str, default: Any = None) -> Any:
        """
        Retrieve and deserialize a JSON value from DragonflyDB.

        Args:
            key: Cache key
            default: Default value if key doesn't exist

        Returns:
            Deserialized value or default
        """
        await self.ensure_connected()

        try:
            value = await self._client.get(key)
            if value is None:
                return default
            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to get JSON value for key {key}: {e}")
            return default

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from DragonflyDB.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        await self.ensure_connected()

        try:
            return await self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist in DragonflyDB.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        await self.ensure_connected()

        try:
            return await self._client.exists(*keys)
        except Exception as e:
            logger.error(f"Failed to check existence of keys {keys}: {e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        try:
            return await self._client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        await self.ensure_connected()

        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return -2

    def pipeline(self):
        """
        Create a pipeline for batch operations.

        Returns:
            Redis pipeline object for batching commands
        """
        if not self._client:
            raise RuntimeError("DragonflyDB service not connected")
        return self._client.pipeline()

    async def flushdb(self) -> bool:
        """
        Clear all data from the current database.
        WARNING: This will delete all data!

        Returns:
            True if successful, False otherwise
        """
        await self.ensure_connected()

        try:
            result = await self._client.flushdb()
            return result is True
        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False

    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get DragonflyDB server information.

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
        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            return {}


# Global service instance
_dragonfly_service: Optional[DragonflyService] = None


async def get_cache_service() -> DragonflyService:
    """
    Get the global DragonflyDB service instance.

    Returns:
        Connected DragonflyDB service instance
    """
    global _dragonfly_service

    if _dragonfly_service is None:
        _dragonfly_service = DragonflyService()
        await _dragonfly_service.connect()

    return _dragonfly_service


async def close_cache_service() -> None:
    """Close the global DragonflyDB service instance."""
    global _dragonfly_service

    if _dragonfly_service:
        await _dragonfly_service.disconnect()
        _dragonfly_service = None
