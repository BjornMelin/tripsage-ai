"""
Redis MCP Wrapper implementation.

This wrapper provides a standardized interface for the Redis MCP client,
mapping user-friendly method names to actual Redis MCP client methods.
"""

import asyncio
import json
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from pydantic import BaseModel, Field

from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class ContentType(str, Enum):
    """Content types for web operations with different TTL requirements."""

    # Real-time data that should never be cached for long periods
    # (weather, stock prices)
    REALTIME = "realtime"
    # Time-sensitive information that changes frequently (news, social media)
    TIME_SENSITIVE = "time_sensitive"
    # Information that changes daily but remains relevant (flight prices, events)
    DAILY = "daily"
    # Information that changes infrequently (restaurant menus, business details)
    SEMI_STATIC = "semi_static"
    # Information that rarely changes (historical data, documentation)
    STATIC = "static"


class CacheMetrics(BaseModel):
    """Cache metrics for monitoring performance."""

    hits: int = Field(0, description="Number of cache hits")
    misses: int = Field(0, description="Number of cache misses")
    sets: int = Field(0, description="Number of cache sets")
    deletes: int = Field(0, description="Number of cache deletes")
    key_count: int = Field(0, description="Number of keys in cache")
    total_size_bytes: int = Field(0, description="Estimated total size in bytes")


class RedisMCPClient:
    """Client for Redis MCP server based operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        namespace: str = "tripsage",
        default_ttl: int = 3600,
        sample_rate: float = 0.1,
    ):
        """
        Initialize the Redis MCP client.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database index
            password: Redis password
            namespace: Namespace for cache keys
            default_ttl: Default TTL in seconds
            sample_rate: Rate at which to sample operations for metrics
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.sample_rate = sample_rate
        self.connection_pool = None
        self._redis = None
        self._lock = asyncio.Lock()

        # TTL settings for different content types (in seconds)
        self.ttl_settings = {
            ContentType.REALTIME: 100,  # 100s
            ContentType.TIME_SENSITIVE: 300,  # 5m
            ContentType.DAILY: 3600,  # 1h
            ContentType.SEMI_STATIC: 28800,  # 8h
            ContentType.STATIC: 86400,  # 24h
        }

        # Time windows for metrics (in seconds)
        self.time_windows = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
        }

        logger.info(
            f"Initialized RedisMCPClient for {host}:{port}/{db} with namespace '{namespace}'"
        )

    async def _get_redis_client(self) -> redis.Redis:
        """
        Get Redis client, creating connection if needed.
        
        Returns:
            redis.asyncio.Redis client
        """
        async with self._lock:
            if self._redis is None:
                logger.debug(f"Creating Redis connection to {self.host}:{self.port}/{self.db}")
                self._redis = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                )
                # Test connection
                try:
                    await self._redis.ping()
                    logger.info(f"Successfully connected to Redis at {self.host}:{self.port}/{self.db}")
                except redis.RedisError as e:
                    logger.error(f"Failed to connect to Redis: {str(e)}")
                    self._redis = None
                    raise TripSageMCPError(f"Redis connection failed: {str(e)}")
            return self._redis

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Key to retrieve
            
        Returns:
            The value or None if not found
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Get value from Redis
            value = await client.get(full_key)
            
            # Track metrics
            if await self._should_track_metrics():
                await self._record_metric("get", bool(value))
                
            if value:
                logger.debug(f"Cache hit for {full_key}")
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, return as is
                    return value
                    
            logger.debug(f"Cache miss for {full_key}")
            return None
        except Exception as e:
            logger.warning(f"Error retrieving from Redis: {str(e)}")
            return None
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        content_type: Optional[Union[ContentType, str]] = None,
    ) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: Key to set
            value: Value to store (must be JSON serializable)
            ttl: TTL in seconds (overrides content_type TTL)
            content_type: Content type for TTL determination
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Serialize the value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                # For non-JSON serializable values, convert to string
                serialized = str(value)
            
            # Determine TTL based on content_type if no explicit TTL provided
            if ttl is None and content_type is not None:
                # Convert string to enum if needed
                if isinstance(content_type, str):
                    content_type = ContentType(content_type)
                ttl = self.ttl_settings.get(content_type, self.default_ttl)
            elif ttl is None:
                ttl = self.default_ttl
                
            # Set value in Redis
            result = await client.set(full_key, serialized, ex=ttl)
            
            # Track metrics
            if await self._should_track_metrics():
                await self._record_metric("set")
                
            size_bytes = len(serialized)
            logger.debug(f"Cache set for {full_key} ({size_bytes} bytes, TTL: {ttl}s)")
            
            return bool(result)
        except Exception as e:
            logger.warning(f"Error setting cache in Redis: {str(e)}")
            return False
            
    async def delete(self, key: str) -> bool:
        """
        Delete a value from Redis.
        
        Args:
            key: Key to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Delete from Redis
            result = await client.delete(full_key) > 0
            
            # Track metrics
            if await self._should_track_metrics():
                await self._record_metric("delete")
                
            if result:
                logger.debug(f"Cache deleted key {full_key}")
                
            return result
        except Exception as e:
            logger.warning(f"Error deleting from Redis: {str(e)}")
            return False
            
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Key to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Check if key exists
            result = await client.exists(full_key) > 0
            return result
        except Exception as e:
            logger.warning(f"Error checking key existence in Redis: {str(e)}")
            return False
            
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Key to set expiration for
            ttl: TTL in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Set expiration
            result = await client.expire(full_key, ttl)
            return bool(result)
        except Exception as e:
            logger.warning(f"Error setting expiration in Redis: {str(e)}")
            return False
            
    async def ttl(self, key: str) -> int:
        """
        Get TTL for a key.
        
        Args:
            key: Key to get TTL for
            
        Returns:
            TTL in seconds (-2 if key doesn't exist, -1 if no TTL)
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Get TTL
            result = await client.ttl(full_key)
            return result
        except Exception as e:
            logger.warning(f"Error getting TTL from Redis: {str(e)}")
            return -2
            
    async def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to the left of a list.
        
        Args:
            key: List key
            *values: Values to push
            
        Returns:
            Length of the list after push
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Serialize values
            serialized_values = [
                json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for v in values
            ]
            
            # Push to list
            result = await client.lpush(full_key, *serialized_values)
            return result
        except Exception as e:
            logger.warning(f"Error pushing to list in Redis: {str(e)}")
            return 0
            
    async def rpop(self, key: str) -> Optional[Any]:
        """
        Pop value from the right of a list.
        
        Args:
            key: List key
            
        Returns:
            Popped value or None
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Pop from list
            value = await client.rpop(full_key)
            
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, return as is
                    return value
                    
            return None
        except Exception as e:
            logger.warning(f"Error popping from list in Redis: {str(e)}")
            return None
            
    async def sadd(self, key: str, *values: Any) -> int:
        """
        Add values to a set.
        
        Args:
            key: Set key
            *values: Values to add
            
        Returns:
            Number of elements added to the set
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Serialize values
            serialized_values = [
                json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for v in values
            ]
            
            # Add to set
            result = await client.sadd(full_key, *serialized_values)
            return result
        except Exception as e:
            logger.warning(f"Error adding to set in Redis: {str(e)}")
            return 0
            
    async def srem(self, key: str, *values: Any) -> int:
        """
        Remove values from a set.
        
        Args:
            key: Set key
            *values: Values to remove
            
        Returns:
            Number of elements removed from the set
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Serialize values
            serialized_values = [
                json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for v in values
            ]
            
            # Remove from set
            result = await client.srem(full_key, *serialized_values)
            return result
        except Exception as e:
            logger.warning(f"Error removing from set in Redis: {str(e)}")
            return 0
            
    async def hset(self, key: str, field: str, value: Any) -> int:
        """
        Set hash field to value.
        
        Args:
            key: Hash key
            field: Hash field
            value: Value to set
            
        Returns:
            1 if field is new, 0 if field was updated
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)
                
            # Set hash field
            result = await client.hset(full_key, field, serialized)
            return result
        except Exception as e:
            logger.warning(f"Error setting hash field in Redis: {str(e)}")
            return 0
            
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """
        Get value of hash field.
        
        Args:
            key: Hash key
            field: Hash field
            
        Returns:
            Field value or None
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)
            client = await self._get_redis_client()
            
            # Get hash field
            value = await client.hget(full_key, field)
            
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, return as is
                    return value
                    
            return None
        except Exception as e:
            logger.warning(f"Error getting hash field from Redis: {str(e)}")
            return None
            
    async def keys(self, pattern: str) -> List[str]:
        """
        Find all keys matching pattern.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            List of matching keys
        """
        try:
            client = await self._get_redis_client()
            
            # Add namespace to pattern if not already present
            if not pattern.startswith(f"{self.namespace}:"):
                full_pattern = f"{self.namespace}:{pattern}"
            else:
                full_pattern = pattern
                
            # Get matching keys
            keys = await client.keys(full_pattern)
            return keys
        except Exception as e:
            logger.warning(f"Error finding keys in Redis: {str(e)}")
            return []
            
    async def scan(
        self, cursor: int = 0, match: Optional[str] = None, count: int = 10
    ) -> tuple[int, List[str]]:
        """
        Incrementally iterate over keys.
        
        Args:
            cursor: Cursor position
            match: Pattern to match
            count: Number of keys to return per call
            
        Returns:
            (next cursor, list of keys)
        """
        try:
            client = await self._get_redis_client()
            
            # Add namespace to match pattern if not already present
            if match and not match.startswith(f"{self.namespace}:"):
                full_match = f"{self.namespace}:{match}"
            else:
                full_match = match
                
            # Scan keys
            cursor, keys = await client.scan(cursor=cursor, match=full_match, count=count)
            return int(cursor), keys
        except Exception as e:
            logger.warning(f"Error scanning keys in Redis: {str(e)}")
            return 0, []
            
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching the pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = await self._get_redis_client()
            
            # Add namespace to pattern if not already present
            if not pattern.startswith(f"{self.namespace}:"):
                full_pattern = f"{self.namespace}:{pattern}"
            else:
                full_pattern = pattern
                
            # Get all keys matching the pattern
            keys = await client.keys(full_pattern)
            
            # Delete matched keys
            if keys:
                count = await client.delete(*keys)
                logger.info(f"Invalidated {count} keys matching pattern {full_pattern}")
                return count
            return 0
        except Exception as e:
            logger.warning(f"Error invalidating cache pattern: {str(e)}")
            return 0
            
    async def get_stats(self, time_window: str = "1h") -> CacheMetrics:
        """
        Retrieve cache performance metrics for the specified time window.
        
        Args:
            time_window: The time window for metrics ("1h", "24h", "7d")
            
        Returns:
            CacheMetrics object with performance statistics
        """
        try:
            # Ensure time window is valid
            if time_window not in self.time_windows:
                time_window = "1h"  # Default to 1 hour if invalid
                
            # Create metrics key with time window
            metrics_key = f"{self.namespace}:metrics:{time_window}"
            
            client = await self._get_redis_client()
            
            # Get metrics from Redis hash
            metrics_data = await client.hgetall(metrics_key)
            
            # Convert to integers
            metrics = {}
            for k, v in metrics_data.items():
                metrics[k] = int(v)
                
            # Get current key count
            key_count = 0
            cursor = 0
            pattern = f"{self.namespace}:*"
            while True:
                cursor, keys = await self.scan(cursor=cursor, match=pattern, count=1000)
                key_count += len(keys)
                if cursor == 0:
                    break
                    
            # Estimate total size
            total_size_bytes = await self._estimate_cache_size()
            
            # Create metrics object
            cache_metrics = CacheMetrics(
                hits=metrics.get("hits", 0),
                misses=metrics.get("misses", 0),
                sets=metrics.get("sets", 0),
                deletes=metrics.get("deletes", 0),
                key_count=key_count,
                total_size_bytes=total_size_bytes,
            )
            
            return cache_metrics
        except Exception as e:
            logger.warning(f"Error retrieving cache stats: {str(e)}")
            return CacheMetrics()
            
    def _ensure_namespaced_key(self, key: str) -> str:
        """
        Ensure the key includes the namespace.
        
        Args:
            key: The original key
            
        Returns:
            Key with namespace
        """
        if key.startswith(f"{self.namespace}:"):
            return key
        return f"{self.namespace}:{key}"
        
    async def _should_track_metrics(self) -> bool:
        """
        Determine whether to track metrics for this operation based on sample rate.
        
        Returns:
            True if metrics should be tracked, False otherwise
        """
        import random
        
        if self.sample_rate <= 0:
            return False
        if self.sample_rate >= 1:
            return True
            
        # Simple random sampling
        return random.random() < self.sample_rate
        
    async def _record_metric(self, operation: str, is_hit: bool = False) -> None:
        """
        Record cache operation metrics.
        
        Args:
            operation: The operation type ('get', 'set', 'delete')
            is_hit: Whether the get operation was a hit
        """
        try:
            client = await self._get_redis_client()
            
            # Update metrics for all time windows
            for window, seconds in self.time_windows.items():
                metrics_key = f"{self.namespace}:metrics:{window}"
                
                # Determine which counter to increment
                if operation == "get":
                    if is_hit:
                        await client.hincrby(metrics_key, "hits", 1)
                    else:
                        await client.hincrby(metrics_key, "misses", 1)
                elif operation == "set":
                    await client.hincrby(metrics_key, "sets", 1)
                elif operation == "delete":
                    await client.hincrby(metrics_key, "deletes", 1)
                    
                # Set expiration for metrics key
                await client.expire(metrics_key, seconds)
        except Exception as e:
            logger.warning(f"Error recording cache metrics: {str(e)}")
            
    async def _estimate_cache_size(self) -> int:
        """
        Estimate the total size of the cache in bytes.
        
        Returns:
            Estimated size in bytes
        """
        try:
            client = await self._get_redis_client()
            
            # Sample keys to estimate size
            sample_size = 50
            sample_keys = []
            sample_total_size = 0
            
            # Get sample keys
            cursor = 0
            pattern = f"{self.namespace}:*"
            while len(sample_keys) < sample_size:
                cursor, keys = await self.scan(cursor=cursor, match=pattern, count=100)
                sample_keys.extend(keys[: sample_size - len(sample_keys)])
                if cursor == 0 or len(sample_keys) >= sample_size:
                    break
                    
            # Get size of sample keys
            if not sample_keys:
                return 0
                
            for key in sample_keys:
                val = await client.get(key)
                if val:
                    # Size of key + size of value
                    sample_total_size += len(key) + len(val)
                    
            # Get key count
            key_count = 0
            cursor = 0
            while True:
                cursor, keys = await self.scan(cursor=cursor, match=pattern, count=1000)
                key_count += len(keys)
                if cursor == 0:
                    break
                    
            # Calculate average size per key
            if len(sample_keys) > 0:
                avg_size_per_key = sample_total_size / len(sample_keys)
            else:
                avg_size_per_key = 0
                
            # Estimate total size
            estimated_size = int(key_count * avg_size_per_key)
            
            return estimated_size
        except Exception as e:
            logger.warning(f"Error estimating cache size: {str(e)}")
            return 0


class RedisMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Redis MCP client."""

    def __init__(self, client: Optional[RedisMCPClient] = None, mcp_name: str = "redis"):
        """
        Initialize the Redis MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration using mcp_settings
            redis_config = mcp_settings.redis
            client = RedisMCPClient(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db_index,
                password=redis_config.password.get_secret_value() if redis_config.password else None,
                namespace=redis_config.namespace,
                default_ttl=redis_config.default_ttl,
            )
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Basic key operations
            "get_key": "get",
            "get": "get",
            "set_key": "set",
            "set": "set",
            "delete_key": "delete",
            "delete": "delete",
            "del": "delete",
            "exists": "exists",
            "key_exists": "exists",
            # TTL operations
            "expire": "expire",
            "set_expiry": "expire",
            "ttl": "ttl",
            "get_ttl": "ttl",
            # List operations
            "push": "lpush",
            "list_push": "lpush",
            "pop": "rpop",
            "list_pop": "rpop",
            # Set operations
            "add_to_set": "sadd",
            "set_add": "sadd",
            "remove_from_set": "srem",
            "set_remove": "srem",
            # Hash operations
            "hash_set": "hset",
            "hset": "hset",
            "hash_get": "hget",
            "hget": "hget",
            # Pattern operations
            "keys": "keys",
            "find_keys": "keys",
            "scan": "scan",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
