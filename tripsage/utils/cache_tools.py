"""
Redis MCP-based caching functionality for TripSage.

This module provides Redis MCP-based caching utilities for TripSage, building on top of
the RedisMCPClient implementation to provide a standardized interface for caching
operations across the application.
"""

import functools
import hashlib
import json
import time
from typing import Any, Callable, List, Optional, TypeVar, Union, cast

from pydantic import BaseModel, Field

from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.mcp_abstraction.wrappers.redis_wrapper import ContentType
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# Type variables for type hinting
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class CacheStats(BaseModel):
    """Cache statistics model."""

    hits: int = Field(0, description="Number of cache hits")
    misses: int = Field(0, description="Number of cache misses")
    hit_ratio: float = Field(0.0, description="Cache hit ratio (0.0-1.0)")
    sets: int = Field(0, description="Number of cache sets")
    deletes: int = Field(0, description="Number of cache deletes")
    key_count: int = Field(0, description="Number of keys in cache")
    size_mb: float = Field(0.0, description="Estimated cache size in MB")
    time_window: str = Field("1h", description="Stats time window")


async def get_cache_stats(
    namespace: str = "tripsage", time_window: str = "1h"
) -> CacheStats:
    """Get statistics for the cache.

    Args:
        namespace: Cache namespace
        time_window: Time window for stats ("1h", "24h", "7d")

    Returns:
        Cache statistics
    """
    try:
        metrics = await mcp_manager.invoke(
            mcp_name="redis",
            method_name="get_stats",
            params={"time_window": time_window},
        )

        # Calculate hit ratio
        total_ops = metrics.hits + metrics.misses
        hit_ratio = metrics.hits / total_ops if total_ops > 0 else 0.0

        # Convert size to MB
        size_mb = (
            metrics.total_size_bytes / (1024 * 1024)
            if metrics.total_size_bytes > 0
            else 0.0
        )

        return CacheStats(
            cache_hits=metrics.hits,
            misses=metrics.misses,
            hit_ratio=hit_ratio,
            sets=metrics.sets,
            deletes=metrics.deletes,
            key_count=metrics.key_count,
            size_mb=size_mb,
            time_window=time_window,
        )
    except TripSageMCPError as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        # Return default stats on error
        return CacheStats(time_window=time_window)


async def set_cache(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
    content_type: Optional[Union[ContentType, str]] = None,
    namespace: str = "tripsage",
) -> bool:
    """Set a value in the cache.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time-to-live in seconds (None for default TTL)
        content_type: ContentType enum value or string
        namespace: Cache namespace

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure key has namespace if not already present
        if not key.startswith(f"{namespace}:"):
            key = f"{namespace}:{key}"

        # Set cache value through Redis MCP
        result = await mcp_manager.invoke(
            mcp_name="redis",
            method_name="set",
            params={
                "key": key,
                "value": value,
                "ttl": ttl,
                "content_type": content_type,
            },
        )

        return bool(result)
    except TripSageMCPError as e:
        logger.error(f"Error setting cache value: {str(e)}")
        return False


async def get_cache(key: str, namespace: str = "tripsage") -> Optional[Any]:
    """Get a value from the cache.

    Args:
        key: Cache key
        namespace: Cache namespace

    Returns:
        The cached value or None if not found
    """
    try:
        # Ensure key has namespace if not already present
        if not key.startswith(f"{namespace}:"):
            key = f"{namespace}:{key}"

        # Get cache value through Redis MCP
        result = await mcp_manager.invoke(
            mcp_name="redis",
            method_name="get",
            params={"key": key},
        )

        return result
    except TripSageMCPError as e:
        logger.error(f"Error getting cache value: {str(e)}")
        return None


async def delete_cache(key: str, namespace: str = "tripsage") -> bool:
    """Delete a value from the cache.

    Args:
        key: Cache key
        namespace: Cache namespace

    Returns:
        True if deleted, False otherwise
    """
    try:
        # Ensure key has namespace if not already present
        if not key.startswith(f"{namespace}:"):
            key = f"{namespace}:{key}"

        # Delete cache value through Redis MCP
        result = await mcp_manager.invoke(
            mcp_name="redis",
            method_name="delete",
            params={"key": key},
        )

        return bool(result)
    except TripSageMCPError as e:
        logger.error(f"Error deleting cache value: {str(e)}")
        return False


async def invalidate_pattern(pattern: str, namespace: str = "tripsage") -> int:
    """Invalidate all keys matching the pattern.

    Args:
        pattern: Redis key pattern (e.g., "user:*")
        namespace: Cache namespace

    Returns:
        Number of keys deleted
    """
    try:
        # Ensure pattern has namespace if not already present
        if not pattern.startswith(f"{namespace}:"):
            pattern = f"{namespace}:{pattern}"

        # Invalidate pattern through Redis MCP
        result = await mcp_manager.invoke(
            mcp_name="redis",
            method_name="invalidate_pattern",
            params={"pattern": pattern},
        )

        return int(result)
    except TripSageMCPError as e:
        logger.error(f"Error invalidating cache pattern: {str(e)}")
        return 0


def generate_cache_key(
    prefix: str, query: str, args: Optional[List[Any]] = None, **kwargs: Any
) -> str:
    """Generate a deterministic cache key.

    Args:
        prefix: Key prefix (e.g., function name)
        query: The main query or identifier
        args: Additional positional arguments
        **kwargs: Additional keyword arguments

    Returns:
        A deterministic cache key
    """
    # Normalize the query (lowercase, strip whitespace)
    normalized_query = query.lower().strip()

    # Convert args to string if present
    args_str = ""
    if args:
        args_str = json.dumps([str(arg) for arg in args], sort_keys=True)

    # Sort additional parameters for deterministic key generation
    kwargs_str = ""
    if kwargs:
        sorted_items = sorted(kwargs.items())
        kwargs_str = json.dumps(sorted_items, sort_keys=True)

    # Create a hash of the combined parameters
    combined = f"{prefix}:{normalized_query}:{args_str}:{kwargs_str}"
    hash_obj = hashlib.md5(combined.encode())
    query_hash = hash_obj.hexdigest()

    return f"{prefix}:{query_hash}"


def determine_content_type(
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


def cached(
    content_type: Optional[Union[ContentType, str]] = None,
    ttl: Optional[int] = None,
    namespace: str = "tripsage",
    skip_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Decorator for caching async function results.

    Args:
        content_type: The ContentType enum or string representation
        ttl: Optional explicit TTL in seconds (overrides content_type TTL)
        namespace: Cache namespace
        skip_args: List of argument names to skip when generating cache key

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from tripsage.utils.settings import settings

            # Check if caching is enabled
            if not settings.use_cache:
                return await func(*args, **kwargs)

            # Check for skip_cache parameter
            skip_cache = kwargs.pop("skip_cache", False)
            if skip_cache:
                return await func(*args, **kwargs)

            # Filter out args to skip from key generation
            key_kwargs = kwargs.copy()
            if skip_args:
                for arg in skip_args:
                    key_kwargs.pop(arg, None)

            # Generate cache key
            function_name = func.__name__
            module_name = func.__module__
            cache_prefix = f"{namespace}:{module_name}.{function_name}"

            # Join all string args to form query string for key generation
            query_components = []
            for arg in args:
                if isinstance(arg, str):
                    query_components.append(arg)

            query = ":".join(query_components) if query_components else function_name
            cache_key = generate_cache_key(
                cache_prefix, query, list(args), **key_kwargs
            )

            # Try to get from cache
            cached_result = await get_cache(cache_key, namespace=namespace)
            if cached_result is not None:
                logger.debug(f"Cache hit for {function_name} (key: {cache_key})")
                return cached_result

            # Call the function
            logger.debug(f"Cache miss for {function_name} (key: {cache_key})")
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Cache the result if it's not None
            if result is not None:
                # Convert string content_type to enum if needed
                effective_content_type = content_type
                if isinstance(content_type, str):
                    effective_content_type = ContentType(content_type)

                await set_cache(
                    cache_key,
                    result,
                    ttl=ttl,
                    content_type=effective_content_type,
                    namespace=namespace,
                )
                logger.debug(
                    f"Cached result for {function_name} completed in {execution_time:.2f}s "
                    f"(key: {cache_key})"
                )

            return result

        # Add method to invalidate cache for specific args
        async def invalidate(*args: Any, **kwargs: Any) -> bool:
            """Invalidate cache for specific arguments."""
            # Filter out args to skip from key generation
            key_kwargs = kwargs.copy()
            if skip_args:
                for arg in skip_args:
                    key_kwargs.pop(arg, None)

            # Generate cache key
            function_name = func.__name__
            module_name = func.__module__
            cache_prefix = f"{namespace}:{module_name}.{function_name}"

            # Join all string args to form query string for key generation
            query_components = []
            for arg in args:
                if isinstance(arg, str):
                    query_components.append(arg)

            query = ":".join(query_components) if query_components else function_name
            cache_key = generate_cache_key(
                cache_prefix, query, list(args), **key_kwargs
            )

            # Delete specific cache entry
            result = await delete_cache(cache_key, namespace=namespace)
            logger.debug(f"Invalidated cache for {function_name} (key: {cache_key})")

            return result

        # Add method to invalidate all cache entries for this function
        async def invalidate_all() -> int:
            """Invalidate all cache entries for this function."""
            function_name = func.__name__
            module_name = func.__module__
            pattern = f"{namespace}:{module_name}.{function_name}:*"

            # Delete all cache entries for this function
            result = await invalidate_pattern(pattern, namespace=namespace)
            logger.debug(
                f"Invalidated all cache entries for {function_name} ({result} keys)"
            )

            return result

        # Attach invalidation methods to the wrapper
        wrapper.invalidate = invalidate  # type: ignore
        wrapper.invalidate_all = invalidate_all  # type: ignore

        return cast(F, wrapper)

    return decorator


# Content-specific cache decorators for convenience
def cached_realtime(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching realtime data.

    Args:
        ttl: Optional explicit TTL in seconds
        **kwargs: Additional arguments for cached decorator

    Returns:
        Decorated function
    """
    return cached(content_type=ContentType.REALTIME, ttl=ttl, **kwargs)


def cached_time_sensitive(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching time-sensitive data.

    Args:
        ttl: Optional explicit TTL in seconds
        **kwargs: Additional arguments for cached decorator

    Returns:
        Decorated function
    """
    return cached(content_type=ContentType.TIME_SENSITIVE, ttl=ttl, **kwargs)


def cached_daily(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching daily data.

    Args:
        ttl: Optional explicit TTL in seconds
        **kwargs: Additional arguments for cached decorator

    Returns:
        Decorated function
    """
    return cached(content_type=ContentType.DAILY, ttl=ttl, **kwargs)


def cached_semi_static(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching semi-static data.

    Args:
        ttl: Optional explicit TTL in seconds
        **kwargs: Additional arguments for cached decorator

    Returns:
        Decorated function
    """
    return cached(content_type=ContentType.SEMI_STATIC, ttl=ttl, **kwargs)


def cached_static(ttl: Optional[int] = None, **kwargs: Any) -> Callable[[F], F]:
    """Decorator for caching static data.

    Args:
        ttl: Optional explicit TTL in seconds
        **kwargs: Additional arguments for cached decorator

    Returns:
        Decorated function
    """
    return cached(content_type=ContentType.STATIC, ttl=ttl, **kwargs)


__all__ = [
    "cached",
    "cached_realtime",
    "cached_time_sensitive",
    "cached_daily",
    "cached_semi_static",
    "cached_static",
    "get_cache",
    "set_cache",
    "delete_cache",
    "invalidate_pattern",
    "generate_cache_key",
    "determine_content_type",
    "get_cache_stats",
    "CacheStats",
    "ContentType",
]
