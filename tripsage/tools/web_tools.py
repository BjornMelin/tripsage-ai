"""
Web tools for TripSage.

This module provides wrappers and utilities for web-based operations,
including caching for WebSearchTool from the OpenAI Agents SDK.
"""

import time
from typing import Any, Dict, Optional

from agents import WebSearchTool

from tripsage.mcp_abstraction.wrappers.redis_wrapper import ContentType
from tripsage.utils.cache_tools import (
    CacheStats,
    cached,
    determine_content_type,
    generate_cache_key,
    get_cache,
    get_cache_stats,
    invalidate_pattern,
    set_cache,
)
from tripsage.utils.error_handling import log_exception
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# Default namespace for web cache operations
WEB_CACHE_NAMESPACE = "web-search"


class CachedWebSearchTool(WebSearchTool):
    """Wrapper for WebSearchTool with Redis MCP-based caching.

    This class extends the OpenAI WebSearchTool to provide content-aware
    caching based on the query and search parameters using Redis MCP.
    """

    def __init__(
        self,
        namespace: str = WEB_CACHE_NAMESPACE,
        user_location: Optional[Any] = None,
        search_context_size: str = "medium",
    ):
        """Initialize the CachedWebSearchTool.

        Args:
            namespace: Cache namespace
            user_location: Optional user location for geographic context
            search_context_size: Context size ('low', 'medium', 'high')
        """
        super().__init__(
            user_location=user_location,
            search_context_size=search_context_size,
        )
        self.namespace = namespace
        logger.info(f"Initialized CachedWebSearchTool with namespace '{namespace}'")

    async def _run(self, query: str, *, skip_cache: bool = False, **kwargs: Any) -> Any:
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
            cache_key = generate_cache_key(
                "websearch",
                query,
                None,
                user_location=self.user_location,
                search_context_size=self.search_context_size,
                **kwargs,
            )

            # Try to get from cache
            cached_result = await get_cache(cache_key, namespace=self.namespace)
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
            await set_cache(
                cache_key, result, content_type=content_type, namespace=self.namespace
            )

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

        # Use content type detection logic
        return determine_content_type(query=query, domains=domains or None)


async def get_web_cache_stats(time_window: str = "1h") -> CacheStats:
    """Get statistics for the web cache.

    Args:
        time_window: Time window for stats ("1h", "24h", "7d")

    Returns:
        Cache statistics
    """
    return await get_cache_stats(namespace=WEB_CACHE_NAMESPACE, time_window=time_window)


async def invalidate_web_cache_for_query(query: str) -> int:
    """Invalidate cache entries for a specific query.

    Args:
        query: The query to invalidate cache for

    Returns:
        Number of keys invalidated
    """
    try:
        # Generate hash for the query
        import hashlib

        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()

        # Invalidate all entries containing this hash
        pattern = f"*{query_hash}*"
        count = await invalidate_pattern(pattern, namespace=WEB_CACHE_NAMESPACE)

        logger.info(f"Invalidated {count} cache entries for query: {query}")
        return count
    except Exception as e:
        logger.error(f"Error invalidating web cache for query '{query}': {str(e)}")
        return 0


def web_cached(content_type: ContentType, ttl: Optional[int] = None):
    """Decorator for adding web caching to any function.

    Args:
        content_type: Content type for TTL determination
        ttl: Optional TTL in seconds (overrides content_type TTL)

    Returns:
        The cached function decorator
    """
    return cached(
        content_type=content_type,
        ttl=ttl,
        namespace=WEB_CACHE_NAMESPACE,
    )


# Export API
__all__ = [
    "CachedWebSearchTool",
    "get_web_cache_stats",
    "invalidate_web_cache_for_query",
    "web_cached",
    "WEB_CACHE_NAMESPACE",
]
