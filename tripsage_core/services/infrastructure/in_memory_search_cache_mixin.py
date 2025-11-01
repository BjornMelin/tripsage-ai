"""In-memory search cache mixin for services with local caching.

Provides reusable in-memory caching patterns for search operations.
"""

import hashlib
import logging
import time
from typing import Any


logger = logging.getLogger(__name__)


class InMemorySearchCacheMixin:
    """Mixin for in-memory search caching patterns.

    This mixin provides:
    - Consistent cache key generation
    - In-memory cache with TTL
    - Automatic cache cleanup
    - Type-safe caching operations

    Usage:
        class MyService(InMemorySearchCacheMixin):
            def __init__(self):
                self.cache_ttl = 300  # 5 minutes
                super().__init__(cache_ttl=self.cache_ttl)

            async def search(self, request):
                cache_key = self._generate_search_cache_key(request)
                cached = self._get_cached_search(cache_key)
                if cached:
                    return cached

                # Perform search
                results = await self._perform_search(request)

                # Cache results
                self._cache_search_results(cache_key, results)
                return results
    """

    def __init__(self, cache_ttl: int = 300):
        """Initialize the in-memory search cache mixin."""
        self._search_cache: dict[str, tuple[Any, float]] = {}
        self.cache_ttl: int = cache_ttl

    def _generate_search_cache_key(self, search_request: Any) -> str:
        """Generate cache key for search request.

        This is a generic implementation. Services can override for specific logic.
        """
        # Convert request to dict for hashing
        request_dict: dict[str, Any] | str
        if hasattr(search_request, "model_dump"):
            request_dict = search_request.model_dump()
        elif hasattr(search_request, "__dict__"):
            request_dict = search_request.__dict__
        else:
            request_dict = str(search_request)

        # Create deterministic string
        if isinstance(request_dict, dict):
            # Sort keys for consistency
            sorted_items: list[tuple[str, Any]] = sorted(
                [(str(k), v) for k, v in request_dict.items()]
            )
            key_data = str(sorted_items)
        else:
            key_data = str(request_dict)

        # Generate hash
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()[:16]

    def _get_cached_search(self, cache_key: str) -> Any | None:
        """Get cached search results if still valid."""
        if cache_key in self._search_cache:
            result, timestamp = self._search_cache[cache_key]

            if time.time() - timestamp < self.cache_ttl:
                logger.debug("Cache hit for search", extra={"cache_key": cache_key})
                return result

            # Expired, remove it
            del self._search_cache[cache_key]

        logger.debug("Cache miss for search", extra={"cache_key": cache_key})
        return None

    def _cache_search_results(self, cache_key: str, results: Any) -> None:
        """Cache search results."""
        self._search_cache[cache_key] = (results, time.time())

        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self._search_cache) > 1000:
            # Sort by timestamp and remove oldest 200
            oldest_keys = sorted(
                self._search_cache.keys(), key=lambda k: self._search_cache[k][1]
            )[:200]

            for key in oldest_keys:
                del self._search_cache[key]

            logger.debug(
                "Cleaned up search cache",
                extra={
                    "removed": len(oldest_keys),
                    "remaining": len(self._search_cache),
                },
            )
