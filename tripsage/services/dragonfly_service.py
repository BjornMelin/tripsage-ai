"""DragonflyDB service implementation with ServiceProtocol compliance.

This module provides DragonflyDB integration using the Redis-compatible SDK,
offering 25x performance improvement over standard Redis with feature flag support.
"""

from typing import Optional

from tripsage.config.feature_flags import IntegrationMode, feature_flags
from tripsage.config.service_registry import ServiceAdapter, register_service
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.redis_service import RedisService, get_redis_service
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class DragonflyDBService(RedisService):
    """DragonflyDB service extending RedisService for compatibility.

    DragonflyDB is Redis-compatible, so we extend RedisService and add
    DragonflyDB-specific optimizations and monitoring.
    """

    def __init__(self):
        super().__init__()
        self.service_name = "dragonfly"

    async def connect(self) -> None:
        """Initialize DragonflyDB connection with optimizations."""
        try:
            # Use parent class connection logic
            await super().connect()

            # Log DragonflyDB-specific info
            if self._connected:
                info = await self.info("server")
                if info and "dragonfly_version" in str(info):
                    version = info.get("dragonfly_version", "unknown")
                    logger.info(f"Connected to DragonflyDB: {version}")
                else:
                    logger.info("Connected to Redis-compatible cache service")

        except Exception as e:
            logger.error(f"Failed to connect to DragonflyDB: {e}")
            self._connected = False
            raise

    async def health_check(self) -> bool:
        """Health check required by ServiceProtocol."""
        return await self.ping()

    # DragonflyDB-specific optimizations

    async def batch_get(self, keys: list[str]) -> dict[str, Optional[str]]:
        """Optimized batch get for DragonflyDB.

        DragonflyDB handles pipeline operations more efficiently than Redis.

        Args:
            keys: List of keys to fetch

        Returns:
            Dictionary mapping keys to values
        """
        try:
            async with self.pipeline() as pipe:
                for key in keys:
                    pipe.get(key)
                values = await pipe.execute()

            return {
                key: value.decode("utf-8") if value else None
                for key, value in zip(keys, values, strict=False)
            }
        except Exception as e:
            logger.error(f"DragonflyDB batch_get error: {e}")
            raise

    async def batch_set(self, items: dict[str, str], ex: Optional[int] = None) -> bool:
        """Optimized batch set for DragonflyDB.

        Args:
            items: Dictionary of key-value pairs
            ex: Optional expiration in seconds

        Returns:
            True if all operations succeeded
        """
        try:
            async with self.pipeline() as pipe:
                for key, value in items.items():
                    pipe.set(key, value, ex=ex)
                results = await pipe.execute()

            return all(results)
        except Exception as e:
            logger.error(f"DragonflyDB batch_set error: {e}")
            raise

    async def memory_usage(self, key: str) -> Optional[int]:
        """Get memory usage of a key (DragonflyDB optimized).

        Args:
            key: Key to check

        Returns:
            Memory usage in bytes or None if key doesn't exist
        """
        try:
            result = await self.client.memory_usage(key)
            return result
        except Exception as e:
            logger.warning(f"Memory usage command failed (might be Redis): {e}")
            return None


class DragonflyAdapter(ServiceAdapter):
    """Service adapter for DragonflyDB with MCP fallback support."""

    def __init__(self):
        super().__init__("cache")  # Use "cache" as service name for compatibility
        self._dragonfly_service = None

    async def get_mcp_client(self):
        """Get MCP client for Redis compatibility."""
        if not self._mcp_client:
            self._mcp_client = MCPManager()
        return self._mcp_client

    async def get_direct_service(self):
        """Get direct DragonflyDB service."""
        if not self._direct_service:
            # Check if we should use DragonflyDB or fall back to Redis
            if feature_flags.redis_integration == IntegrationMode.DIRECT:
                # Use DragonflyDB for performance
                self._direct_service = DragonflyDBService()
                await self._direct_service.connect()
                logger.info("Using DragonflyDB service for caching")
            else:
                # Fall back to standard Redis service
                self._direct_service = await get_redis_service()
                logger.info("Using Redis service for caching")

        return self._direct_service


class CacheService:
    """Unified cache interface supporting both MCP and direct DragonflyDB/Redis.

    This provides a consistent API regardless of whether we're using MCP wrappers
    or direct SDK integration.
    """

    def __init__(self):
        self.adapter = DragonflyAdapter()

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            return await service.get(key)
        else:
            # MCP fallback
            mcp = await self.adapter.get_mcp_client()
            result = await mcp.invoke("redis", "get", {"key": key})
            return result.get("value") if result else None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            return await service.set(key, value, ex=ex)
        else:
            # MCP fallback
            mcp = await self.adapter.get_mcp_client()
            params = {"key": key, "value": value}
            if ex:
                params["ex"] = ex
            result = await mcp.invoke("redis", "set", params)
            return bool(result)

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            return await service.delete(*keys)
        else:
            # MCP fallback
            mcp = await self.adapter.get_mcp_client()
            deleted = 0
            for key in keys:
                result = await mcp.invoke("redis", "del", {"key": key})
                if result:
                    deleted += 1
            return deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            return bool(await service.exists(key))
        else:
            # MCP fallback
            mcp = await self.adapter.get_mcp_client()
            result = await mcp.invoke("redis", "exists", {"key": key})
            return bool(result.get("exists", False))

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            return await service.expire(key, seconds)
        else:
            # MCP fallback
            mcp = await self.adapter.get_mcp_client()
            result = await mcp.invoke(
                "redis", "expire", {"key": key, "seconds": seconds}
            )
            return bool(result)

    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            return await service.ttl(key)
        else:
            # MCP fallback
            mcp = await self.adapter.get_mcp_client()
            result = await mcp.invoke("redis", "ttl", {"key": key})
            return result.get("ttl", -2)

    # Batch operations for performance

    async def batch_get(self, keys: list[str]) -> dict[str, Optional[str]]:
        """Batch get multiple keys (optimized for DragonflyDB)."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            if hasattr(service, "batch_get"):
                return await service.batch_get(keys)
            else:
                # Fallback to individual gets
                results = {}
                for key in keys:
                    results[key] = await service.get(key)
                return results
        else:
            # MCP doesn't support batch operations efficiently
            results = {}
            mcp = await self.adapter.get_mcp_client()
            for key in keys:
                result = await mcp.invoke("redis", "get", {"key": key})
                results[key] = result.get("value") if result else None
            return results

    async def batch_set(self, items: dict[str, str], ex: Optional[int] = None) -> bool:
        """Batch set multiple key-value pairs."""
        if self.adapter.is_direct:
            service = await self.adapter.get_direct_service()
            if hasattr(service, "batch_set"):
                return await service.batch_set(items, ex=ex)
            else:
                # Fallback to pipeline
                async with service.pipeline() as pipe:
                    for key, value in items.items():
                        pipe.set(key, value, ex=ex)
                    results = await pipe.execute()
                return all(results)
        else:
            # MCP fallback with individual sets
            mcp = await self.adapter.get_mcp_client()
            success = True
            for key, value in items.items():
                params = {"key": key, "value": value}
                if ex:
                    params["ex"] = ex
                result = await mcp.invoke("redis", "set", params)
                success = success and bool(result)
            return success


# Global cache service instance
cache_service = CacheService()

# Register with service registry
register_service("cache", DragonflyAdapter())


async def get_cache_service() -> CacheService:
    """Get the global cache service instance.

    Returns:
        CacheService instance
    """
    return cache_service
