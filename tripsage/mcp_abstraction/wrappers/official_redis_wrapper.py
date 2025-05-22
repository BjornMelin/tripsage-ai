"""
Official Redis MCP Wrapper implementation.

This wrapper provides a standardized interface for the official Redis MCP server
from @modelcontextprotocol/server-redis, mapping TripSage methods to MCP tools.
"""

import json
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class RedisCacheStats(BaseModel):
    """Redis cache statistics."""

    total_keys: int = Field(0, description="Total number of keys")
    operations: Dict[str, int] = Field(
        default_factory=lambda: {"gets": 0, "sets": 0, "deletes": 0}
    )


class OfficialRedisMCPClient:
    """Client for the official Redis MCP server."""

    def __init__(self, config=None):
        """Initialize the Redis MCP client."""
        self.config = config or mcp_settings.redis
        self.stats = RedisCacheStats()
        self._client = None

    async def connect(self):
        """Connect to the MCP server (handled by manager)."""
        logger.info("Official Redis MCP client ready")

    async def disconnect(self):
        """Disconnect from the MCP server."""
        logger.info("Official Redis MCP client disconnected")

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        from tripsage.mcp_abstraction.manager import mcp_manager

        try:
            params = {"key": key, "value": value}
            if ttl:
                params["expireSeconds"] = ttl

            await mcp_manager.invoke(mcp_name="redis", method_name="set", **params)

            self.stats.operations["sets"] += 1
            logger.debug(f"Set Redis key: {key}")
            return True

        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {e}")
            raise TripSageMCPError(f"Redis set failed: {e}") from e

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis by key."""
        from tripsage.mcp_abstraction.manager import mcp_manager

        try:
            result = await mcp_manager.invoke(
                mcp_name="redis", method_name="get", key=key
            )

            self.stats.operations["gets"] += 1

            if result and "value" in result:
                logger.debug(f"Retrieved Redis key: {key}")
                return result["value"]

            logger.debug(f"Redis key not found: {key}")
            return None

        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {e}")
            return None

    async def delete(self, key: Union[str, List[str]]) -> int:
        """Delete one or more keys from Redis."""
        from tripsage.mcp_abstraction.manager import mcp_manager

        try:
            result = await mcp_manager.invoke(
                mcp_name="redis", method_name="delete", key=key
            )

            deleted_count = result.get("deletedCount", 0) if result else 0
            self.stats.operations["deletes"] += deleted_count

            if isinstance(key, list):
                logger.debug(f"Deleted {deleted_count} Redis keys from list")
            else:
                logger.debug(f"Deleted Redis key: {key}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting Redis key(s) {key}: {e}")
            raise TripSageMCPError(f"Redis delete failed: {e}") from e

    async def list_keys(self, pattern: str = "*") -> List[str]:
        """List Redis keys matching a pattern."""
        from tripsage.mcp_abstraction.manager import mcp_manager

        try:
            result = await mcp_manager.invoke(
                mcp_name="redis", method_name="list", pattern=pattern
            )

            keys = result.get("keys", []) if result else []
            self.stats.total_keys = len(keys)

            logger.debug(f"Listed {len(keys)} Redis keys with pattern: {pattern}")
            return keys

        except Exception as e:
            logger.error(f"Error listing Redis keys with pattern {pattern}: {e}")
            return []

    async def get_stats(self) -> RedisCacheStats:
        """Get cache statistics."""
        # Update total keys count
        keys = await self.list_keys()
        self.stats.total_keys = len(keys)
        return self.stats


class OfficialRedisMCPWrapper(BaseMCPWrapper):
    """Wrapper for the official Redis MCP server."""

    def __init__(self):
        """Initialize the Redis MCP wrapper."""
        super().__init__(mcp_name="redis")
        self._client = OfficialRedisMCPClient()

    async def initialize(self) -> bool:
        """Initialize the Redis MCP wrapper."""
        try:
            await self._client.connect()
            logger.info("Official Redis MCP wrapper initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Redis MCP wrapper: {e}")
            return False

    async def cleanup(self):
        """Clean up the Redis MCP wrapper."""
        if self._client:
            await self._client.disconnect()

    # Cache operations using TripSage naming conventions

    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a cache value with optional TTL."""
        # Serialize non-string values to JSON
        if not isinstance(value, str):
            value = json.dumps(value, default=str)

        return await self._client.set(key, value, ttl)

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cache value, attempting JSON deserialization."""
        raw_value = await self._client.get(key)
        if raw_value is None:
            return None

        # Try to deserialize JSON, fall back to raw string
        try:
            return json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            return raw_value

    async def cache_delete(self, key: Union[str, List[str]]) -> int:
        """Delete cache key(s)."""
        return await self._client.delete(key)

    async def cache_exists(self, key: str) -> bool:
        """Check if a cache key exists."""
        value = await self._client.get(key)
        return value is not None

    async def cache_keys(self, pattern: str = "*") -> List[str]:
        """List cache keys matching a pattern."""
        return await self._client.list_keys(pattern)

    async def cache_clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        keys = await self.cache_keys(pattern)
        if keys:
            return await self.cache_delete(keys)
        return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = await self._client.get_stats()
        return {
            "total_keys": stats.total_keys,
            "operations": stats.operations,
            "server_type": "official_redis_mcp",
        }

    # Direct Redis MCP tool access

    async def redis_set(
        self, key: str, value: str, expire_seconds: Optional[int] = None
    ) -> bool:
        """Direct access to Redis MCP set tool."""
        return await self._client.set(key, value, expire_seconds)

    async def redis_get(self, key: str) -> Optional[str]:
        """Direct access to Redis MCP get tool."""
        return await self._client.get(key)

    async def redis_delete(self, key: Union[str, List[str]]) -> int:
        """Direct access to Redis MCP delete tool."""
        return await self._client.delete(key)

    async def redis_list(self, pattern: str = "*") -> List[str]:
        """Direct access to Redis MCP list tool."""
        return await self._client.list_keys(pattern)
