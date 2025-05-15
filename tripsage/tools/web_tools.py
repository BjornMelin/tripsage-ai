"""
Web tools for TripSage.

This module provides wrappers and utilities for web-based operations,
including caching for WebSearchTool from the OpenAI Agents SDK.
"""

import time
from typing import Any, Dict, List, Optional

from openai.types.beta.assistant_tools_function_execution_tool import (
    ActualExecutionResult,
)
from openai.types.beta.assistant_tools_web_search import WebSearchTool
from pydantic import BaseModel, Field

from tripsage.utils.cache import ContentType, WebOperationsCache
from tripsage.utils.error_handling import log_exception
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# Global web cache instance
web_cache = WebOperationsCache(namespace="web-search")


class CachedWebSearchTool(WebSearchTool):
    """Wrapper for WebSearchTool with Redis-based caching.

    This class extends the OpenAI WebSearchTool to provide content-aware
    caching based on the query and search parameters.
    """

    def __init__(
        self,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        cache: Optional[WebOperationsCache] = None,
    ):
        """Initialize the CachedWebSearchTool.

        Args:
            allowed_domains: List of domains to allow in search results
            blocked_domains: List of domains to block from search results
            cache: Cache instance to use (defaults to global web_cache)
        """
        super().__init__(
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
        )
        self.cache = cache or web_cache
        logger.info(
            f"Initialized CachedWebSearchTool with "
            f"allowed_domains={allowed_domains}, blocked_domains={blocked_domains}"
        )

    async def _run(
        self, query: str, *, skip_cache: bool = False, **kwargs: Any
    ) -> ActualExecutionResult:
        """Execute the web search with caching.

        Args:
            query: The search query
            skip_cache: Whether to skip the cache
            **kwargs: Additional search parameters

        Returns:
            Search results
        """
        try:
            start_time = time.time()

            # Skip cache if explicitly requested
            if skip_cache:
                logger.debug(f"Skipping cache for query: {query}")
                return await super()._run(query, **kwargs)

            # Generate cache key
            cache_key = self.cache.generate_cache_key(
                "websearch",
                query,
                allowed_domains=self.allowed_domains,
                blocked_domains=self.blocked_domains,
                **kwargs,
            )

            # Try to get from cache
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(
                    f"Cache hit for web search query: {query} "
                    f"(key: {cache_key.split(':')[-1][:8]}...)"
                )
                return cached_result

            logger.info(
                f"Cache miss for web search query: {query} "
                f"(key: {cache_key.split(':')[-1][:8]}...)"
            )

            # Execute the actual search
            result = await super()._run(query, **kwargs)

            # Determine content type
            content_type = self._determine_content_type(query, result)
            logger.debug(f"Determined content type {content_type} for query: {query}")

            # Store in cache
            await self.cache.set(cache_key, result, content_type=content_type)

            # Log execution time
            execution_time = time.time() - start_time
            logger.debug(f"Web search for '{query}' completed in {execution_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Error in CachedWebSearchTool._run: {str(e)}")
            log_exception(e)
            # Return error information in the format expected by the agents SDK
            return {
                "status": "error",
                "error": {"message": str(e)},
                "search_results": [],
            }

    def _determine_content_type(
        self, query: str, result: Optional[Dict[str, Any]] = None
    ) -> ContentType:
        """Determine content type from query and results.

        Args:
            query: The search query
            result: The search result (if available)

        Returns:
            The ContentType enum value
        """
        # Extract domains from search results if available
        domains = []
        if result and isinstance(result, dict) and "search_results" in result:
            for item in result.get("search_results", []):
                if "link" in item:
                    try:
                        from urllib.parse import urlparse

                        domain = urlparse(item["link"]).netloc
                        domains.append(domain)
                    except Exception:
                        pass

        # Use cache's content type detection logic
        return self.cache.determine_content_type(query=query, domains=domains or None)


class WebCacheStats(BaseModel):
    """Statistics for WebOperationsCache."""

    cache_hits: int = Field(0, description="Number of cache hits")
    cache_misses: int = Field(0, description="Number of cache misses")
    hit_ratio: float = Field(0.0, description="Cache hit ratio (0.0-1.0)")
    key_count: int = Field(0, description="Number of keys in cache")
    size_mb: float = Field(0.0, description="Estimated cache size in MB")
    time_window: str = Field("1h", description="Stats time window")


async def get_web_cache_stats(time_window: str = "1h") -> WebCacheStats:
    """Get statistics for the web cache.

    Args:
        time_window: Time window for stats ("1h", "24h", "7d")

    Returns:
        Cache statistics
    """
    metrics = await web_cache.get_stats(time_window)

    # Calculate hit ratio
    total_ops = metrics.hits + metrics.misses
    hit_ratio = metrics.hits / total_ops if total_ops > 0 else 0.0

    # Convert size to MB
    size_mb = (
        metrics.total_size_bytes / (1024 * 1024)
        if metrics.total_size_bytes > 0
        else 0.0
    )

    return WebCacheStats(
        cache_hits=metrics.hits,
        cache_misses=metrics.misses,
        hit_ratio=hit_ratio,
        key_count=metrics.key_count,
        size_mb=size_mb,
        time_window=time_window,
    )


async def invalidate_web_cache_for_query(query: str) -> int:
    """Invalidate cache entries for a specific query.

    Args:
        query: The query to invalidate cache for

    Returns:
        Number of keys invalidated
    """
    # Generate hash for the query
    import hashlib

    query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()

    # Invalidate all entries containing this hash
    pattern = f"*{query_hash}*"
    count = await web_cache.invalidate_pattern(pattern)

    logger.info(f"Invalidated {count} cache entries for query: {query}")
    return count


async def web_cached(func: Any, content_type: ContentType) -> Any:
    """Decorator for adding web caching to any function.

    Args:
        func: The function to decorate
        content_type: Content type for TTL determination

    Returns:
        The wrapped function
    """
    return web_cache.web_cached(content_type)(func)


# Export API
__all__ = [
    "CachedWebSearchTool",
    "WebCacheStats",
    "web_cache",
    "get_web_cache_stats",
    "invalidate_web_cache_for_query",
    "web_cached",
]
