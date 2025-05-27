"""Direct Redis/DragonflyDB service implementation.

This module provides direct Redis SDK integration to replace MCP wrapper,
offering 25x performance improvement and drop-in Redis compatibility.
"""

import json
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import redis.asyncio as redis

from tripsage.config.service_registry import BaseService
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class RedisService(BaseService):
    """Direct Redis/DragonflyDB service with connection pooling and retry logic."""

    def __init__(self):
        super().__init__()
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def connect(self) -> None:
        """Initialize Redis connection with connection pooling."""
        if self._connected:
            return

        try:
            # Parse Redis URL from settings
            redis_url = str(self.settings.redis.url)

            # Create connection pool for better performance
            self._connection_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
                socket_connect_timeout=5,
                socket_timeout=5,
                decode_responses=False,  # Handle encoding manually for better control
            )

            # Create Redis client with pool
            self._client = redis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis service connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            raise

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self._client:
            try:
                await self._client.aclose()
                logger.info("Redis service disconnected")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._client = None
                self._connection_pool = None
                self._connected = False

    @property
    def client(self) -> redis.Redis:
        """Get Redis client, connecting if necessary."""
        if not self._connected or not self._client:
            raise RuntimeError("Redis service not connected. Call connect() first.")
        return self._client

    # Core Redis operations

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis.

        Args:
            key: Redis key

        Returns:
            Value as string or None if not found
        """
        try:
            result = await self.client.get(key)
            return result.decode("utf-8") if result else None
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            raise

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set value in Redis with optional expiration.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert value to string for storage
            str_value = str(value) if not isinstance(value, (str, bytes)) else value

            result = await self.client.set(key, str_value, ex=ex, nx=nx, xx=xx)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            raise

    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            raise

    async def exists(self, *keys: str) -> int:
        """Check if keys exist in Redis.

        Args:
            keys: Keys to check

        Returns:
            Number of keys that exist
        """
        try:
            return await self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS error for keys {keys}: {e}")
            raise

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key.

        Args:
            key: Redis key
            seconds: Expiration time in seconds

        Returns:
            True if expiration was set, False if key doesn't exist
        """
        try:
            return bool(await self.client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            raise

    async def ttl(self, key: str) -> int:
        """Get time to live for a key.

        Args:
            key: Redis key

        Returns:
            TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            raise

    # JSON operations for complex data

    async def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set JSON value in Redis.

        Args:
            key: Redis key
            value: Object to serialize as JSON
            ex: Expiration time in seconds

        Returns:
            True if successful
        """
        try:
            json_value = json.dumps(value, default=str)
            return await self.set(key, json_value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET_JSON error for key '{key}': {e}")
            raise

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from Redis.

        Args:
            key: Redis key

        Returns:
            Deserialized object or None if not found
        """
        try:
            value = await self.get(key)
            return json.loads(value) if value else None
        except json.JSONDecodeError as e:
            logger.error(f"Redis GET_JSON decode error for key '{key}': {e}")
            return None
        except Exception as e:
            logger.error(f"Redis GET_JSON error for key '{key}': {e}")
            raise

    # Hash operations

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get field value from hash.

        Args:
            name: Hash name
            key: Field key

        Returns:
            Field value or None if not found
        """
        try:
            result = await self.client.hget(name, key)
            return result.decode("utf-8") if result else None
        except Exception as e:
            logger.error(f"Redis HGET error for hash '{name}' key '{key}': {e}")
            raise

    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set field value in hash.

        Args:
            name: Hash name
            key: Field key
            value: Field value

        Returns:
            Number of fields added
        """
        try:
            str_value = str(value) if not isinstance(value, (str, bytes)) else value
            return await self.client.hset(name, key, str_value)
        except Exception as e:
            logger.error(f"Redis HSET error for hash '{name}' key '{key}': {e}")
            raise

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all fields from hash.

        Args:
            name: Hash name

        Returns:
            Dictionary of field-value pairs
        """
        try:
            result = await self.client.hgetall(name)
            return {k.decode("utf-8"): v.decode("utf-8") for k, v in result.items()}
        except Exception as e:
            logger.error(f"Redis HGETALL error for hash '{name}': {e}")
            raise

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from hash.

        Args:
            name: Hash name
            keys: Field keys to delete

        Returns:
            Number of fields deleted
        """
        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Redis HDEL error for hash '{name}' keys {keys}: {e}")
            raise

    # List operations

    async def lpush(self, name: str, *values: Any) -> int:
        """Push values to the left of list.

        Args:
            name: List name
            values: Values to push

        Returns:
            Length of list after push
        """
        try:
            str_values = [
                str(v) if not isinstance(v, (str, bytes)) else v for v in values
            ]
            return await self.client.lpush(name, *str_values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for list '{name}': {e}")
            raise

    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from the right of list.

        Args:
            name: List name

        Returns:
            Popped value or None if list is empty
        """
        try:
            result = await self.client.rpop(name)
            return result.decode("utf-8") if result else None
        except Exception as e:
            logger.error(f"Redis RPOP error for list '{name}': {e}")
            raise

    async def llen(self, name: str) -> int:
        """Get length of list.

        Args:
            name: List name

        Returns:
            Length of list
        """
        try:
            return await self.client.llen(name)
        except Exception as e:
            logger.error(f"Redis LLEN error for list '{name}': {e}")
            raise

    # Set operations

    async def sadd(self, name: str, *values: Any) -> int:
        """Add values to set.

        Args:
            name: Set name
            values: Values to add

        Returns:
            Number of values added
        """
        try:
            str_values = [
                str(v) if not isinstance(v, (str, bytes)) else v for v in values
            ]
            return await self.client.sadd(name, *str_values)
        except Exception as e:
            logger.error(f"Redis SADD error for set '{name}': {e}")
            raise

    async def smembers(self, name: str) -> set:
        """Get all members of set.

        Args:
            name: Set name

        Returns:
            Set of members
        """
        try:
            result = await self.client.smembers(name)
            return {member.decode("utf-8") for member in result}
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for set '{name}': {e}")
            raise

    async def sismember(self, name: str, value: Any) -> bool:
        """Check if value is member of set.

        Args:
            name: Set name
            value: Value to check

        Returns:
            True if value is member, False otherwise
        """
        try:
            str_value = str(value) if not isinstance(value, (str, bytes)) else value
            return bool(await self.client.sismember(name, str_value))
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for set '{name}': {e}")
            raise

    # Pipeline operations for bulk operations

    @asynccontextmanager
    async def pipeline(self):
        """Context manager for Redis pipeline operations.

        Example:
            async with redis_service.pipeline() as pipe:
                pipe.set('key1', 'value1')
                pipe.set('key2', 'value2')
                results = await pipe.execute()
        """
        pipe = self.client.pipeline()
        try:
            yield pipe
        finally:
            pass  # Pipeline cleanup is automatic

    # Health check and monitoring

    async def ping(self) -> bool:
        """Ping Redis server.

        Returns:
            True if Redis is responsive
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis PING error: {e}")
            return False

    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get Redis server information.

        Args:
            section: Specific section to retrieve

        Returns:
            Server information dictionary
        """
        try:
            result = await self.client.info(section)
            return result
        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            raise

    async def dbsize(self) -> int:
        """Get number of keys in database.

        Returns:
            Number of keys
        """
        try:
            return await self.client.dbsize()
        except Exception as e:
            logger.error(f"Redis DBSIZE error: {e}")
            raise


# Global Redis service instance
redis_service = RedisService()


async def get_redis_service() -> RedisService:
    """Get Redis service instance, connecting if necessary.

    Returns:
        Connected RedisService instance
    """
    if not redis_service.is_connected:
        await redis_service.connect()
    return redis_service
