"""Web tools for TripSage.

This module provides wrappers and utilities for web-based operations,
including caching for WebSearchTool from the OpenAI Agents SDK.

Features include:
- CachedWebSearchTool - A WebSearchTool with direct Redis/DragonflyDB caching
- Content-aware caching based on query characteristics
- Batch caching operations for improved performance
- Web cache statistics and management

This module uses the direct Redis/DragonflyDB service for persistent caching,
allowing sharing of cached web search results across multiple application instances.
"""

import time
from typing import Any

from tripsage_core.utils.cache_utils import (
    CacheStats,
    batch_cache_get,
    cache_lock,
    cached,
    determine_content_type,
    generate_cache_key,
    get_cache,
    get_cache_stats,
    invalidate_pattern,
    prefetch_cache_keys,
    set_cache,
)
from tripsage_core.utils.content_utils import ContentType
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger


# NOTE: Temporarily using mock implementation due to missing agents dependency
# from agents import WebSearchTool


class MockWebSearchTool:
    """Mock WebSearchTool for testing and development.

    This class provides a basic implementation to replace the missing
    OpenAI Agents SDK WebSearchTool for testing purposes.
    """

    def __init__(
        self,
        user_location: Any | None = None,
        search_context_size: str = "medium",
    ):
        """Initialize the MockWebSearchTool.

        Args:
            user_location: Optional user location for geographic context
            search_context_size: Context size ('low', 'medium', 'high')
        """
        self.user_location = user_location
        self.search_context_size = search_context_size

    async def _run(self, query: str, **kwargs: Any) -> Any:
        """Execute a mock web search.

        Args:
            query: The search query
            **kwargs: Additional search parameters

        Returns:
            Mock search results
        """
        # Return mock search results for testing
        return {
            "status": "success",
            "search_results": [
                {
                    "title": f"Mock result for: {query}",
                    "snippet": f"This is a mock search result for the query '{query}'. "
                    "In a real implementation, this would contain actual web search "
                    "results.",
                    "link": f"https://example.com/search?q={query.replace(' ', '+')}",
                }
            ],
            "query": query,
            "search_metadata": {
                "total_results": 1,
                "search_time": "0.1s",
                "provider": "MockSearchProvider",
            },
        }


# Use the mock implementation
WebSearchTool = MockWebSearchTool

logger = get_logger(__name__)

# Default namespace for web cache operations
WEB_CACHE_NAMESPACE = "web-search"


class CachedWebSearchTool(WebSearchTool):
    """Wrapper for WebSearchTool with direct Redis/DragonflyDB caching.

    This class extends the OpenAI WebSearchTool to provide content-aware
    caching based on the query and search parameters using direct Redis/DragonflyDB.

    Features:
    - Content type detection for optimal TTL settings
    - Namespace isolation for web search caching
    - Enhanced error handling with logging
    - Performance metrics tracking
    """

    def __init__(
        self,
        namespace: str = WEB_CACHE_NAMESPACE,
        user_location: Any | None = None,
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

            # Try to get from cache with distributed lock to prevent thundering herd
            # when multiple instances request the same uncached query
            async with cache_lock(
                f"websearch:{hash(query)}", timeout=5, namespace=self.namespace
            ):
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
                logger.debug(
                    f"Determined content type {content_type} for query: {query}"
                )

                # Store in cache
                await set_cache(
                    cache_key,
                    result,
                    content_type=content_type,
                    namespace=self.namespace,
                )

                # Log execution time
                execution_time = time.time() - start_time
                logger.debug(
                    f"Web search for '{query}' completed in {execution_time:.2f}s"
                )

                # Prefetch related queries if available
                await self._prefetch_related_queries(query, result)

                return result

        except Exception as e:
            logger.error(f"Error in CachedWebSearchTool._run: {e!s}")
            log_exception(e)
            # Return error information in the format expected by the agents SDK
            return {
                "status": "error",
                "error": {"message": str(e)},
                "search_results": [],
            }

    def _determine_content_type(
        self, query: str, result: dict[str, Any] | None = None
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
                    except Exception as parse_error:
                        logger.debug(
                            "Unable to parse domain from result link '%s': %s",
                            item.get("link"),
                            parse_error,
                        )

        # Use content type detection logic
        return determine_content_type(query=query, domains=domains or None)

    async def _prefetch_related_queries(self, query: str, result: Any) -> None:
        """Prefetch related queries based on search results.

        This helps with cache warming for likely follow-up searches.

        Args:
            query: The original search query
            result: The search result
        """
        try:
            if (
                not result
                or not isinstance(result, dict)
                or "search_results" not in result
            ):
                return

            # Extract suggested related questions if available
            related_queries = []

            # Check for related questions in search results
            for item in result.get("search_results", []):
                if "snippet" in item and "?" in item["snippet"]:
                    # Extract potential questions from snippets
                    import re

                    questions = re.findall(r"([^.!?]*\\?)", item["snippet"])
                    related_queries.extend(
                        q.strip() for q in questions if len(q.strip()) > 10
                    )

            # Limit to top 3 most relevant related queries
            related_queries = related_queries[:3]

            if related_queries:
                logger.debug(
                    f"Prefetching {len(related_queries)} related queries for '{query}'"
                )
                # Generate cache keys for all related queries
                prefetch_pattern = f"{self.namespace}:websearch:*"
                await prefetch_cache_keys(prefetch_pattern, namespace=self.namespace)
        except Exception as e:
            # Don't let prefetching errors affect the main flow
            logger.debug(f"Error prefetching related queries: {e!s}")


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

        query_hash = hashlib.md5(
            query.lower().strip().encode(), usedforsecurity=False
        ).hexdigest()

        # Invalidate all entries containing this hash
        pattern = f"*{query_hash}*"
        count = await invalidate_pattern(pattern, namespace=WEB_CACHE_NAMESPACE)

        logger.info(f"Invalidated {count} cache entries for query: {query}")
        return count
    except Exception as e:
        logger.error(f"Error invalidating web cache for query '{query}': {e!s}")
        return 0


async def batch_web_search(
    queries: list[str], skip_cache: bool = False
) -> list[dict[str, Any]]:
    """Perform multiple web searches in a batch.

    This function optimizes multiple searches by using batch cache operations
    and parallelizing uncached searches when possible.

    Args:
        queries: List of search queries
        skip_cache: Whether to skip the cache

    Returns:
        List of search results in the same order as the input queries
    """
    try:
        # Generate cache keys for all queries
        cache_keys = []
        for query in queries:
            cache_key = generate_cache_key("websearch", query, None)
            cache_keys.append(cache_key)

        if not skip_cache:
            # Try to get results from cache in a batch
            cached_results = await batch_cache_get(
                cache_keys, namespace=WEB_CACHE_NAMESPACE
            )
        else:
            # Skip cache for all queries
            cached_results = [None] * len(queries)

        # Track which queries need to be searched
        search_indices = []
        search_queries = []
        for i, result in enumerate(cached_results):
            if result is None:
                search_indices.append(i)
                search_queries.append(queries[i])

        # Perform searches for uncached queries
        search_results = []
        if search_queries:
            tool = CachedWebSearchTool(namespace=WEB_CACHE_NAMESPACE)

            # Execute searches (could be optimized with asyncio.gather)
            for query in search_queries:
                result = await tool._run(query, skip_cache=True)
                search_results.append(result)

        # Combine cached and new results
        final_results = list(cached_results)  # Make a copy
        for i, result in zip(search_indices, search_results, strict=False):
            final_results[i] = result

        return final_results
    except Exception as e:
        logger.error(f"Error in batch_web_search: {e!s}")
        log_exception(e)
        return [
            {"status": "error", "error": {"message": str(e)}, "search_results": []}
        ] * len(queries)


def web_cached(content_type: ContentType, ttl: int | None = None):
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
    "WEB_CACHE_NAMESPACE",
    "CachedWebSearchTool",
    "batch_web_search",
    "get_web_cache_stats",
    "invalidate_web_cache_for_query",
    "web_cached",
]
