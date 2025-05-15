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
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import redis.asyncio as redis
from pydantic import BaseModel

from .logging import get_logger
from .settings import settings

logger = get_logger(__name__)

# Type variables for type hinting
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


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
    # Structured data (JSON, XML)
    JSON = "json"
    # Markdown formatted text
    MARKDOWN = "markdown"
    # HTML formatted text
    HTML = "html"
    # Binary data (images, PDFs, etc.)
    BINARY = "binary"


class CacheMetrics(BaseModel):
    """Cache metrics for monitoring performance."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    key_count: int = 0
    total_size_bytes: int = 0


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


class WebOperationsCache:
    """Redis-based content-aware caching system for web operations.

    This class extends the basic Redis cache with content-aware TTL settings,
    metrics collection, and specialized key generation for web operations.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        namespace: str = "webcache",
        sample_rate: float = 0.1,
    ):
        """Initialize the Web Operations Cache.

        Args:
            url: Redis connection URL, defaults to config value if not provided
            namespace: The namespace for cache keys and metrics
            sample_rate: Rate at which to sample operations for metrics (0.0-1.0)
        """
        self.url = url or str(settings.redis.url)
        self.redis = redis.from_url(self.url)
        self.namespace = namespace
        self.sample_rate = sample_rate

        # Define TTLs for content types from settings (in seconds)
        self.ttl_settings = {
            # 100s (default)
            ContentType.REALTIME: settings.redis.web_cache.realtime,
            # 5m (default)
            ContentType.TIME_SENSITIVE: settings.redis.web_cache.time_sensitive,
            # 1h (default)
            ContentType.DAILY: settings.redis.web_cache.daily,
            # 8h (default)
            ContentType.SEMI_STATIC: settings.redis.web_cache.semi_static,
            # 24h (default)
            ContentType.STATIC: settings.redis.web_cache.static,
        }

        # Time windows for metrics (in seconds)
        self.time_windows = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800,
        }

        logger.info(
            f"Initialized WebOperationsCache at {self.url} with namespace '{namespace}'"
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache with metrics tracking.

        Args:
            key: Cache key

        Returns:
            The cached value or None if not found
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)

            # Get value from Redis
            value = await self.redis.get(full_key)

            # Track metrics
            if self._should_track_metrics():
                await self._record_metric("get", bool(value))

            # Deserialize if value exists
            if value:
                logger.debug(f"Cache hit for {full_key}")
                return json.loads(value)

            logger.debug(f"Cache miss for {full_key}")
            return None
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {str(e)}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        content_type: Optional[Union[ContentType, str]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set a value in the cache with content-aware TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            content_type: ContentType enum value or string
            ttl: Explicit TTL in seconds (overrides content_type TTL)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)

            # Serialize the value
            serialized = json.dumps(value)

            # Determine TTL based on content_type if no explicit TTL provided
            if ttl is None and content_type is not None:
                # Convert string to enum if needed
                if isinstance(content_type, str):
                    content_type = ContentType(content_type)
                ttl = self.get_ttl_for_content_type(content_type)

            # Set value in Redis
            result = await self.redis.set(full_key, serialized, ex=ttl)

            # Track metrics
            if self._should_track_metrics():
                await self._record_metric("set")

            size_bytes = len(serialized)
            logger.debug(f"Cache set for {full_key} ({size_bytes} bytes, TTL: {ttl}s)")

            return bool(result)
        except Exception as e:
            logger.warning(f"Error setting cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found or error
        """
        try:
            # Add namespace to key if not already present
            full_key = self._ensure_namespaced_key(key)

            # Delete from Redis
            result = await self.redis.delete(full_key) > 0

            # Track metrics
            if self._should_track_metrics():
                await self._record_metric("delete")

            if result:
                logger.debug(f"Cache deleted key {full_key}")

            return result
        except Exception as e:
            logger.warning(f"Error deleting from cache: {str(e)}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching the pattern.

        Args:
            pattern: Redis key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            # Add namespace to pattern if not already present
            if not pattern.startswith(f"{self.namespace}:"):
                full_pattern = f"{self.namespace}:{pattern}"
            else:
                full_pattern = pattern

            # Get all keys matching the pattern
            keys = await self.redis.keys(full_pattern)

            # Delete matched keys
            if keys:
                count = await self.redis.delete(*keys)
                logger.info(f"Invalidated {count} keys matching pattern {full_pattern}")
                return count
            return 0
        except Exception as e:
            logger.warning(f"Error invalidating cache pattern: {str(e)}")
            return 0

    def generate_cache_key(self, tool_name: str, query: str, **kwargs: Any) -> str:
        """Generate a deterministic cache key for web operations.

        Args:
            tool_name: The name of the tool (e.g., 'websearch', 'webcrawl')
            query: The query string or URL
            **kwargs: Additional parameters that affect the result

        Returns:
            A deterministic cache key
        """
        # Normalize the query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()

        # Sort additional parameters for deterministic key generation
        param_str = ""
        if kwargs:
            sorted_items = sorted(kwargs.items())
            param_str = json.dumps(sorted_items, sort_keys=True)

        # Create a hash of the combined parameters
        combined = f"{tool_name}:{normalized_query}:{param_str}"
        hash_obj = hashlib.md5(combined.encode())
        query_hash = hash_obj.hexdigest()

        return f"{self.namespace}:{tool_name}:{query_hash}"

    def get_ttl_for_content_type(self, content_type: ContentType) -> int:
        """Get the appropriate TTL for a content type.

        Args:
            content_type: The ContentType enum value

        Returns:
            TTL in seconds
        """
        return self.ttl_settings.get(content_type, self.ttl_settings[ContentType.DAILY])

    def determine_content_type(
        self,
        query: str,
        source: Optional[str] = None,
        domains: Optional[List[str]] = None,
    ) -> ContentType:
        """Determine the content type based on the query and source.

        Args:
            query: The search query or URL
            source: The source of the data (optional)
            domains: List of domains being queried (optional)

        Returns:
            The appropriate ContentType enum value
        """
        # Keywords indicating real-time data
        realtime_keywords = [
            "current",
            "now",
            "live",
            "weather",
            "stock",
            "price",
            "today",
            "latest",
            "traffic",
            "update",
            "breaking",
            "forecast",
        ]

        # Keywords indicating time-sensitive data
        time_sensitive_keywords = [
            "news",
            "event",
            "announcement",
            "recent",
            "update",
            "change",
            "trending",
            "today",
            "this week",
            "happening",
        ]

        # Keywords indicating static data
        static_keywords = [
            "history",
            "definition",
            "concept",
            "biography",
            "documentation",
            "how to",
            "guide",
            "tutorial",
            "explained",
            "facts about",
            "established",
        ]

        # Domains that typically have real-time data
        realtime_domains = [
            "weather.com",
            "accuweather",
            "finance.yahoo.com",
            "marketwatch.com",
            "bloomberg.com",
            "investing.com",
            "tradingview.com",
        ]

        # Domains that typically have time-sensitive data
        time_sensitive_domains = [
            "news",
            "cnn.com",
            "bbc.com",
            "reuters.com",
            "nytimes.com",
            "theguardian.com",
            "washingtonpost.com",
            "twitter.com",
            "reddit.com",
        ]

        # Domains that typically have static data
        static_domains = [
            "wikipedia.org",
            "britannica.com",
            "docs.",
            "github.io",
            "education",
            "history",
            "archive",
            "encyclopedia",
            "research",
            "academic",
        ]

        # Convert query to lowercase for matching
        query_lower = query.lower()

        # Check domains (if provided)
        if domains:
            for domain in domains:
                domain_lower = domain.lower()

                # Check against domain categories
                if any(rd in domain_lower for rd in realtime_domains):
                    return ContentType.REALTIME

                if any(td in domain_lower for td in time_sensitive_domains):
                    return ContentType.TIME_SENSITIVE

                if any(sd in domain_lower for sd in static_domains):
                    return ContentType.STATIC

        # Check source (if provided)
        if source:
            source_lower = source.lower()

            # Check against domain categories
            if any(rd in source_lower for rd in realtime_domains):
                return ContentType.REALTIME

            if any(td in source_lower for td in time_sensitive_domains):
                return ContentType.TIME_SENSITIVE

            if any(sd in source_lower for sd in static_domains):
                return ContentType.STATIC

        # Check query keywords
        if any(keyword in query_lower for keyword in realtime_keywords):
            return ContentType.REALTIME

        if any(keyword in query_lower for keyword in time_sensitive_keywords):
            return ContentType.TIME_SENSITIVE

        if any(keyword in query_lower for keyword in static_keywords):
            return ContentType.STATIC

        # Default to DAILY if no clear category is determined
        return ContentType.DAILY

    async def get_stats(self, time_window: str = "1h") -> CacheMetrics:
        """Retrieve cache performance metrics for the specified time window.

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

            # Get metrics from Redis hash
            metrics_data = await self.redis.hgetall(metrics_key)

            # Convert bytes to strings/ints
            metrics = {}
            for k, v in metrics_data.items():
                if isinstance(k, bytes):
                    k = k.decode("utf-8")
                if isinstance(v, bytes):
                    v = v.decode("utf-8")
                metrics[k] = int(v)

            # Get current key count
            key_count = 0
            cursor = b"0"
            pattern = f"{self.namespace}:*"
            while cursor:
                cursor, keys = await self.redis.scan(
                    cursor=cursor, match=pattern, count=1000
                )
                key_count += len(keys)
                if cursor == b"0":
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

    def web_cached(
        self, content_type: Union[ContentType, str], ttl: Optional[int] = None
    ) -> Callable[[F], F]:
        """Decorator for caching web operation function results.

        Args:
            content_type: The ContentType or string representation
            ttl: Optional explicit TTL in seconds (overrides content_type TTL)

        Returns:
            Decorated function
        """
        # Convert string to enum if needed
        if isinstance(content_type, str):
            content_type_enum = ContentType(content_type)
        else:
            content_type_enum = content_type

        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Check if caching is enabled
                if not settings.use_cache:
                    return await func(*args, **kwargs)

                # Check for skip_cache parameter
                skip_cache = kwargs.pop("skip_cache", False)
                if skip_cache:
                    return await func(*args, **kwargs)

                # Determine cache key
                function_name = func.__name__

                # Extract query parameter (assume first string arg is query)
                query = None
                for arg in args:
                    if isinstance(arg, str):
                        query = arg
                        break

                if query is None and "query" in kwargs:
                    query = kwargs["query"]

                if not query:
                    # Can't determine query, fall back to function execution
                    return await func(*args, **kwargs)

                # Generate cache key
                cache_key = self.generate_cache_key(function_name, query, **kwargs)

                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Call the function
                result = await func(*args, **kwargs)

                # Cache the result if it's not None
                if result is not None:
                    effective_ttl = ttl or self.get_ttl_for_content_type(
                        content_type_enum
                    )
                    await self.set(cache_key, result, ttl=effective_ttl)

                return result

            return cast(F, wrapper)

        return decorator

    async def _record_metric(self, operation: str, is_hit: bool = False) -> None:
        """Record cache operation metrics.

        Args:
            operation: The operation type ('get', 'set', 'delete')
            is_hit: Whether the get operation was a hit
        """
        try:
            # Update metrics for all time windows
            for window, seconds in self.time_windows.items():
                metrics_key = f"{self.namespace}:metrics:{window}"

                # Determine which counter to increment
                if operation == "get":
                    if is_hit:
                        await self.redis.hincrby(metrics_key, "hits", 1)
                    else:
                        await self.redis.hincrby(metrics_key, "misses", 1)
                elif operation == "set":
                    await self.redis.hincrby(metrics_key, "sets", 1)
                elif operation == "delete":
                    await self.redis.hincrby(metrics_key, "deletes", 1)

                # Set expiration for metrics key
                await self.redis.expire(metrics_key, seconds)
        except Exception as e:
            logger.warning(f"Error recording cache metrics: {str(e)}")

    def _should_track_metrics(self) -> bool:
        """Determine whether to track metrics for this operation based on sample rate.

        Returns:
            True if metrics should be tracked, False otherwise
        """
        if self.sample_rate <= 0:
            return False
        if self.sample_rate >= 1:
            return True

        # Simple random sampling based on time
        return (time.time() * 1000) % (1.0 / self.sample_rate) < 1

    def _ensure_namespaced_key(self, key: str) -> str:
        """Ensure the key includes the namespace.

        Args:
            key: The original key

        Returns:
            Key with namespace
        """
        if key.startswith(f"{self.namespace}:"):
            return key
        return f"{self.namespace}:{key}"

    async def _estimate_cache_size(self) -> int:
        """Estimate the total size of the cache in bytes.

        Returns:
            Estimated size in bytes
        """
        try:
            # Sample keys to estimate size
            cursor = b"0"
            pattern = f"{self.namespace}:*"
            sample_size = 50
            sample_keys = []
            sample_total_size = 0

            # Get sample keys
            while cursor and len(sample_keys) < sample_size:
                cursor, keys = await self.redis.scan(
                    cursor=cursor, match=pattern, count=100
                )
                sample_keys.extend(keys[: sample_size - len(sample_keys)])
                if cursor == b"0" or len(sample_keys) >= sample_size:
                    break

            # Get size of sample keys
            if not sample_keys:
                return 0

            for key in sample_keys:
                val = await self.redis.get(key)
                if val:
                    # Size of key + size of value
                    sample_total_size += len(key) + len(val)

            # Get key count
            key_count = 0
            cursor = b"0"
            while cursor:
                cursor, keys = await self.redis.scan(
                    cursor=cursor, match=pattern, count=1000
                )
                key_count += len(keys)
                if cursor == b"0":
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


# Initialize caches
memory_cache = InMemoryCache()
web_cache = WebOperationsCache()

# Export for convenience
__all__ = [
    "memory_cache",
    "web_cache",
    "ContentType",
    "WebOperationsCache",
    "InMemoryCache",
]
