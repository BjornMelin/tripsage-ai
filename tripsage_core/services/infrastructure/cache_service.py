"""
Cache service for TripSage Core using DragonflyDB.

This module provides high-performance caching capabilities
using DragonflyDB (Redis-compatible) with 25x performance improvement
over traditional Redis implementations.
"""

import gzip
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import redis.asyncio as redis

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreServiceError

logger = logging.getLogger(__name__)


class CacheService:
    """
    DragonflyDB cache service for high-performance caching operations.

    This service provides:
    - Redis-compatible interface with DragonflyDB backend
    - JSON value serialization/deserialization
    - TTL-based expiration management
    - Batch operations support
    - Performance monitoring
    - Connection pooling
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the cache service.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
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
                        f"{parsed.username}:{self.settings.redis_password}"
                        f"@{parsed.hostname}"
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
            logger.error(f"Failed to connect to DragonflyDB: {e}")
            self._is_connected = False
            raise CoreServiceError(
                message=f"Failed to connect to cache service: {str(e)}",
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

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
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
            logger.error(f"Failed to set JSON value for key {key}: {e}")
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
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON value for key {key}: {e}")
            return default
        except Exception as e:
            logger.error(f"Failed to get JSON value for key {key}: {e}")
            raise CoreServiceError(
                message=f"Failed to get cache value for key '{key}'",
                code="CACHE_GET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    # String operations

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
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
            logger.error(f"Failed to set key {key}: {e}")
            raise CoreServiceError(
                message=f"Failed to set cache key '{key}'",
                code="CACHE_SET_FAILED",
                service="CacheService",
                details={"key": key, "error": str(e)},
            ) from e

    async def get(self, key: str) -> Optional[str]:
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
            logger.error(f"Failed to get key {key}: {e}")
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
            logger.error(f"Failed to delete keys {keys}: {e}")
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
            logger.error(f"Failed to check existence of keys {keys}: {e}")
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
            logger.error(f"Failed to set expiration for key {key}: {e}")
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
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return -2

    # Atomic operations

    async def incr(self, key: str) -> Optional[int]:
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
        except Exception as e:
            logger.error(f"Failed to increment key {key}: {e}")
            return None

    async def decr(self, key: str) -> Optional[int]:
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
        except Exception as e:
            logger.error(f"Failed to decrement key {key}: {e}")
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

    async def mget(self, keys: List[str]) -> List[Optional[str]]:
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
            logger.error(f"Failed to mget keys: {e}")
            raise CoreServiceError(
                message="Failed to get multiple cache keys",
                code="CACHE_MGET_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    async def mset(self, mapping: Dict[str, str]) -> bool:
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
            logger.error(f"Failed to mset: {e}")
            raise CoreServiceError(
                message="Failed to set multiple cache keys",
                code="CACHE_MSET_FAILED",
                service="CacheService",
                details={"error": str(e)},
            ) from e

    # Pattern-based operations

    async def keys(self, pattern: str = "*") -> List[str]:
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
        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
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
        except Exception as e:
            logger.error(f"Failed to flush database: {e}")
            return False

    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
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
        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
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
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
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


class QueryResultCache:
    """
    Intelligent query result caching with advanced features.

    Features:
    - Query fingerprinting and intelligent cache key generation
    - Multi-level caching (L1: in-memory, L2: DragonflyDB)
    - Compression for large result sets
    - Smart TTL based on query patterns and data freshness
    - Cache invalidation strategies tied to data mutations
    - Access pattern learning and LRU eviction
    - Vector search result caching with similarity thresholds
    """

    def __init__(self, cache_service: CacheService, namespace: str = "query_cache"):
        """Initialize query result cache.

        Args:
            cache_service: Underlying cache service instance
            namespace: Cache namespace for organization
        """
        self.cache_service = cache_service
        self.namespace = namespace
        self._l1_cache: Dict[str, Dict[str, Any]] = {}  # In-memory L1 cache
        self._l1_max_size = 1000  # Maximum L1 cache entries
        self._l1_access_times: Dict[str, float] = {}  # LRU tracking
        self._access_patterns: Dict[str, Dict[str, Any]] = {}  # Access pattern learning
        self._compression_threshold = 10240  # Compress data > 10KB

    def _generate_query_fingerprint(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        table: Optional[str] = None,
    ) -> str:
        """Generate deterministic fingerprint for query caching.

        Args:
            query: SQL query or operation identifier
            params: Query parameters
            table: Table name for dependency tracking

        Returns:
            Unique fingerprint for the query
        """
        # Normalize query (remove extra whitespace, convert to lowercase)
        normalized_query = " ".join(query.lower().split())

        # Create content for hashing
        content_parts = [normalized_query]

        if params:
            # Sort parameters for consistent hashing
            sorted_params = json.dumps(params, sort_keys=True, default=str)
            content_parts.append(sorted_params)

        if table:
            content_parts.append(table)

        # Generate hash
        content = ":".join(content_parts)
        fingerprint = hashlib.sha256(content.encode()).hexdigest()[:16]

        return f"{self.namespace}:query:{fingerprint}"

    def _determine_intelligent_ttl(
        self, query: str, table: Optional[str] = None, result_size: int = 0
    ) -> int:
        """Determine intelligent TTL based on query patterns and data characteristics.

        Args:
            query: SQL query or operation
            table: Table name
            result_size: Size of result set

        Returns:
            TTL in seconds
        """
        base_ttl = 3600  # 1 hour default

        # Query pattern analysis
        query_lower = query.lower()

        # Real-time data (short TTL)
        if any(
            keyword in query_lower for keyword in ["price", "stock", "live", "current"]
        ):
            base_ttl = 60  # 1 minute

        # Time-sensitive data (medium TTL)
        elif any(
            keyword in query_lower for keyword in ["today", "recent", "latest", "now"]
        ):
            base_ttl = 300  # 5 minutes

        # Historical/reference data (long TTL)
        elif any(
            keyword in query_lower for keyword in ["history", "reference", "static"]
        ):
            base_ttl = 86400  # 24 hours

        # Aggregate queries (longer TTL as they're expensive to compute)
        elif any(
            keyword in query_lower for keyword in ["count", "sum", "avg", "group by"]
        ):
            base_ttl = 7200  # 2 hours

        # Large result sets get shorter TTL to manage memory
        if result_size > 1000000:  # > 1MB
            base_ttl = min(base_ttl, 1800)  # Max 30 minutes

        # Table-specific adjustments
        if table:
            table_lower = table.lower()
            if table_lower in ["users", "api_keys", "sessions"]:
                base_ttl = min(base_ttl, 600)  # Max 10 minutes for user data
            elif table_lower in ["destinations", "airports", "airlines"]:
                base_ttl = max(base_ttl, 3600)  # Min 1 hour for reference data

        return base_ttl

    def _should_compress(self, data: Any) -> bool:
        """Determine if data should be compressed.

        Args:
            data: Data to evaluate

        Returns:
            True if data should be compressed
        """
        try:
            serialized = json.dumps(data, default=str)
            return len(serialized.encode()) > self._compression_threshold
        except (TypeError, ValueError):
            return False

    def _compress_data(self, data: Any) -> bytes:
        """Compress data for storage.

        Args:
            data: Data to compress

        Returns:
            Compressed data as bytes
        """
        serialized = json.dumps(data, default=str)
        return gzip.compress(serialized.encode())

    def _decompress_data(self, compressed_data: bytes) -> Any:
        """Decompress data from storage.

        Args:
            compressed_data: Compressed data bytes

        Returns:
            Original data
        """
        decompressed = gzip.decompress(compressed_data)
        return json.loads(decompressed.decode())

    def _evict_l1_lru(self) -> None:
        """Evict least recently used items from L1 cache."""
        if len(self._l1_cache) <= self._l1_max_size:
            return

        # Find LRU item
        if not self._l1_access_times:
            return

        lru_key = min(
            self._l1_access_times.keys(), key=lambda k: self._l1_access_times[k]
        )

        # Remove from L1 cache
        self._l1_cache.pop(lru_key, None)
        self._l1_access_times.pop(lru_key, None)

    def _update_access_pattern(self, cache_key: str, hit: bool) -> None:
        """Update access patterns for learning.

        Args:
            cache_key: Cache key that was accessed
            hit: Whether it was a cache hit or miss
        """
        current_time = time.time()

        if cache_key not in self._access_patterns:
            self._access_patterns[cache_key] = {
                "hits": 0,
                "misses": 0,
                "last_access": current_time,
                "access_frequency": 0.0,
            }

        pattern = self._access_patterns[cache_key]

        if hit:
            pattern["hits"] += 1
        else:
            pattern["misses"] += 1

        # Calculate access frequency (accesses per hour)
        time_diff = current_time - pattern["last_access"]
        if time_diff > 0:
            pattern["access_frequency"] = 1.0 / (time_diff / 3600.0)

        pattern["last_access"] = current_time

    async def get_query_result(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        table: Optional[str] = None,
    ) -> Optional[Any]:
        """Get cached query result.

        Args:
            query: SQL query or operation identifier
            params: Query parameters
            table: Table name for dependency tracking

        Returns:
            Cached result or None if not found
        """
        cache_key = self._generate_query_fingerprint(query, params, table)
        current_time = time.time()

        # Try L1 cache first
        if cache_key in self._l1_cache:
            cache_item = self._l1_cache[cache_key]

            # Check expiration
            if cache_item.get("expires_at", 0) > current_time:
                self._l1_access_times[cache_key] = current_time
                self._update_access_pattern(cache_key, hit=True)

                # Decompress if needed
                data = cache_item["data"]
                if cache_item.get("compressed", False):
                    data = self._decompress_data(data)

                logger.debug(f"L1 cache hit for query: {cache_key}")
                return data
            else:
                # Expired, remove from L1
                self._l1_cache.pop(cache_key, None)
                self._l1_access_times.pop(cache_key, None)

        # Try L2 cache (DragonflyDB)
        try:
            await self.cache_service.ensure_connected()

            cached_result = await self.cache_service.get_json(cache_key)
            if cached_result is not None:
                # Restore to L1 cache for faster future access
                cache_item = {
                    "data": cached_result["data"],
                    "compressed": cached_result.get("compressed", False),
                    "expires_at": current_time + 300,  # 5 min in L1
                }

                self._l1_cache[cache_key] = cache_item
                self._l1_access_times[cache_key] = current_time
                self._evict_l1_lru()
                self._update_access_pattern(cache_key, hit=True)

                # Decompress if needed
                data = cached_result["data"]
                if cached_result.get("compressed", False):
                    data = self._decompress_data(data)

                logger.debug(f"L2 cache hit for query: {cache_key}")
                return data

        except Exception as e:
            logger.error(f"Error retrieving from L2 cache: {e}")

        # Cache miss
        self._update_access_pattern(cache_key, hit=False)
        return None

    async def cache_query_result(
        self,
        query: str,
        result: Any,
        params: Optional[Dict[str, Any]] = None,
        table: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache query result with intelligent TTL and compression.

        Args:
            query: SQL query or operation identifier
            result: Query result to cache
            params: Query parameters
            table: Table name for dependency tracking
            ttl: Override TTL (otherwise calculated intelligently)

        Returns:
            True if successfully cached
        """
        if result is None:
            return False

        cache_key = self._generate_query_fingerprint(query, params, table)
        current_time = time.time()

        # Determine TTL
        if ttl is None:
            try:
                result_size = len(json.dumps(result, default=str).encode())
            except (TypeError, ValueError):
                result_size = 0
            ttl = self._determine_intelligent_ttl(query, table, result_size)

        # Determine if compression is needed
        should_compress = self._should_compress(result)

        # Prepare cache item
        cache_data = {
            "data": self._compress_data(result) if should_compress else result,
            "compressed": should_compress,
            "cached_at": current_time,
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
            "table": table,
        }

        # Store in L1 cache
        l1_expires_at = current_time + min(ttl, 1800)  # Max 30 min in L1
        self._l1_cache[cache_key] = {
            "data": cache_data["data"],
            "compressed": should_compress,
            "expires_at": l1_expires_at,
        }
        self._l1_access_times[cache_key] = current_time
        self._evict_l1_lru()

        # Store in L2 cache (DragonflyDB)
        try:
            await self.cache_service.ensure_connected()
            success = await self.cache_service.set_json(cache_key, cache_data, ttl=ttl)

            # Also maintain table dependency mapping for invalidation
            if table and success:
                dep_key = f"{self.namespace}:deps:{table}"
                existing_deps = await self.cache_service.get_json(dep_key, default=[])
                if existing_deps is None:
                    existing_deps = []
                if cache_key not in existing_deps:
                    existing_deps.append(cache_key)
                    await self.cache_service.set_json(
                        dep_key, existing_deps, ttl=ttl * 2
                    )

            logger.debug(
                f"Cached query result: {cache_key} (TTL: {ttl}s, "
                f"Compressed: {should_compress})"
            )
            return success

        except Exception as e:
            logger.error(f"Error caching query result: {e}")
            return False

    async def invalidate_table_cache(self, table: str) -> int:
        """Invalidate all cached queries for a specific table.

        Args:
            table: Table name to invalidate

        Returns:
            Number of cache entries invalidated
        """
        try:
            await self.cache_service.ensure_connected()

            # Get dependent cache keys
            dep_key = f"{self.namespace}:deps:{table}"
            dependent_keys = await self.cache_service.get_json(dep_key, default=[])

            if not dependent_keys:
                return 0

            # Remove from L1 cache
            l1_removed = 0
            for cache_key in dependent_keys:
                if cache_key in self._l1_cache:
                    self._l1_cache.pop(cache_key, None)
                    self._l1_access_times.pop(cache_key, None)
                    l1_removed += 1

            # Remove from L2 cache
            l2_removed = await self.cache_service.delete(*dependent_keys)

            # Clear dependency mapping
            await self.cache_service.delete(dep_key)

            logger.info(
                f"Invalidated {l2_removed} cache entries for table {table} "
                f"(L1: {l1_removed}, L2: {l2_removed})"
            )
            return l2_removed

        except Exception as e:
            logger.error(f"Error invalidating table cache: {e}")
            return 0

    async def cache_vector_search_result(
        self,
        query_vector: List[float],
        result: List[Dict[str, Any]],
        similarity_threshold: float = 0.7,
        limit: int = 10,
        table: str = "vector_search",
        ttl: int = 1800,
    ) -> bool:
        """Cache vector search results with similarity-based key generation.

        Args:
            query_vector: The search vector
            result: Search results
            similarity_threshold: Similarity threshold used
            limit: Number of results
            table: Table/index searched
            ttl: Time to live in seconds

        Returns:
            True if successfully cached
        """
        # Generate vector-specific cache key
        vector_str = ",".join(
            f"{v:.4f}" for v in query_vector[:10]
        )  # First 10 dimensions
        vector_hash = hashlib.md5(vector_str.encode()).hexdigest()[:8]

        cache_key = (
            f"{self.namespace}:vector:{table}:{vector_hash}:"
            f"{similarity_threshold}:{limit}"
        )

        cache_data = {
            "results": result,
            "query_vector_hash": vector_hash,
            "similarity_threshold": similarity_threshold,
            "limit": limit,
            "cached_at": time.time(),
        }

        try:
            await self.cache_service.ensure_connected()
            return await self.cache_service.set_json(cache_key, cache_data, ttl=ttl)
        except Exception as e:
            logger.error(f"Error caching vector search result: {e}")
            return False

    async def get_vector_search_result(
        self,
        query_vector: List[float],
        similarity_threshold: float = 0.7,
        limit: int = 10,
        table: str = "vector_search",
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached vector search results.

        Args:
            query_vector: The search vector
            similarity_threshold: Similarity threshold
            limit: Number of results expected
            table: Table/index to search

        Returns:
            Cached results or None if not found
        """
        vector_str = ",".join(f"{v:.4f}" for v in query_vector[:10])
        vector_hash = hashlib.md5(vector_str.encode()).hexdigest()[:8]

        cache_key = (
            f"{self.namespace}:vector:{table}:{vector_hash}:"
            f"{similarity_threshold}:{limit}"
        )

        try:
            await self.cache_service.ensure_connected()
            cached_data = await self.cache_service.get_json(cache_key)

            if cached_data:
                return cached_data.get("results")

        except Exception as e:
            logger.error(f"Error retrieving vector search cache: {e}")

        return None

    async def warm_cache(
        self,
        queries: List[Tuple[str, Optional[Dict[str, Any]], Optional[str]]],
        execute_func: Callable,
    ) -> int:
        """Warm cache with frequently accessed queries.

        Args:
            queries: List of (query, params, table) tuples
            execute_func: Function to execute queries and get results

        Returns:
            Number of queries successfully cached
        """
        warmed = 0

        for query, params, table in queries:
            try:
                # Check if already cached
                cached = await self.get_query_result(query, params, table)
                if cached is not None:
                    continue

                # Execute and cache
                result = await execute_func(query, params)
                if result is not None:
                    success = await self.cache_query_result(
                        query, result, params, table
                    )
                    if success:
                        warmed += 1

            except Exception as e:
                logger.error(f"Error warming cache for query: {e}")

        logger.info(f"Cache warming completed: {warmed} queries cached")
        return warmed

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        l1_size = len(self._l1_cache)
        l1_memory_est = (
            sum(
                len(json.dumps(item, default=str).encode())
                for item in self._l1_cache.values()
            )
            / 1024
            / 1024
        )  # MB

        # Calculate hit ratios from access patterns
        total_hits = sum(p["hits"] for p in self._access_patterns.values())
        total_misses = sum(p["misses"] for p in self._access_patterns.values())
        total_accesses = total_hits + total_misses
        hit_ratio = total_hits / total_accesses if total_accesses > 0 else 0.0

        # Most frequently accessed queries
        frequent_queries = sorted(
            self._access_patterns.items(),
            key=lambda x: x[1]["hits"] + x[1]["misses"],
            reverse=True,
        )[:5]

        return {
            "l1_cache_size": l1_size,
            "l1_max_size": self._l1_max_size,
            "l1_memory_mb": round(l1_memory_est, 2),
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_ratio": round(hit_ratio, 3),
            "access_patterns_tracked": len(self._access_patterns),
            "frequent_queries": [
                {
                    "key": key,
                    "hits": data["hits"],
                    "misses": data["misses"],
                    "frequency": round(data["access_frequency"], 2),
                }
                for key, data in frequent_queries
            ],
        }

    async def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance based on access patterns.

        Returns:
            Optimization results
        """
        current_time = time.time()
        optimizations = {
            "l1_evictions": 0,
            "pattern_cleanups": 0,
            "recommendations": [],
        }

        # Clean up old access patterns (older than 24 hours)
        old_patterns = [
            key
            for key, pattern in self._access_patterns.items()
            if current_time - pattern["last_access"] > 86400
        ]

        for key in old_patterns:
            self._access_patterns.pop(key, None)
            optimizations["pattern_cleanups"] += 1

        # Evict unused L1 cache entries
        unused_l1 = [
            key
            for key, access_time in self._l1_access_times.items()
            if current_time - access_time > 1800  # 30 minutes
        ]

        for key in unused_l1:
            self._l1_cache.pop(key, None)
            self._l1_access_times.pop(key, None)
            optimizations["l1_evictions"] += 1

        # Generate recommendations
        if len(self._l1_cache) > self._l1_max_size * 0.8:
            optimizations["recommendations"].append("Consider increasing L1 cache size")

        low_hit_ratio_queries = [
            key
            for key, pattern in self._access_patterns.items()
            if (
                "hits" in pattern
                and "misses" in pattern
                and pattern["hits"] + pattern["misses"] > 10
                and pattern["hits"] / (pattern["hits"] + pattern["misses"]) < 0.3
            )
        ]

        if low_hit_ratio_queries:
            optimizations["recommendations"].append(
                f"Consider adjusting TTL for {len(low_hit_ratio_queries)} "
                f"low-hit-ratio queries"
            )

        return optimizations


# Global service instances
_cache_service: Optional[CacheService] = None
_query_result_cache: Optional[QueryResultCache] = None


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


async def get_query_result_cache() -> QueryResultCache:
    """Get the global query result cache instance.

    Returns:
        QueryResultCache instance
    """
    global _query_result_cache

    if _query_result_cache is None:
        cache_service = await get_cache_service()
        _query_result_cache = QueryResultCache(cache_service)

    return _query_result_cache


async def close_cache_service() -> None:
    """Close the global cache service instance."""
    global _cache_service, _query_result_cache

    if _cache_service:
        await _cache_service.disconnect()
        _cache_service = None

    # Query result cache doesn't need explicit closing
    _query_result_cache = None
