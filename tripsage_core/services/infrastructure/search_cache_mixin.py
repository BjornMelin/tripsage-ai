"""Search cache mixin for standardized caching patterns across services.

This module provides a reusable mixin that implements common caching patterns
for search operations, reducing code duplication and ensuring consistency.
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from tripsage_core.services.infrastructure.cache_service import CacheService


logger = logging.getLogger(__name__)

# Generic type for search requests and responses
SearchRequestType = TypeVar("SearchRequestType", bound=BaseModel)
SearchResponseType = TypeVar("SearchResponseType", bound=BaseModel)


class SearchCacheMixin(Generic[SearchRequestType, SearchResponseType], ABC):
    """Mixin for standardized search caching patterns.

    This mixin provides:
    - Consistent cache key generation
    - Automatic cache TTL management
    - Cache hit/miss metrics
    - Seamless integration with DragonflyDB cache service
    - Type-safe caching operations

    Usage:
        class MyService(SearchCacheMixin[MySearchRequest, MySearchResponse]):
            def __init__(self):
                self._cache_service = None
                self._cache_ttl = 300  # 5 minutes
                self._cache_prefix = "my_service"

            async def search(self, request: MySearchRequest) -> MySearchResponse:
                # Try cache first
                cached = await self.get_cached_search(request)
                if cached:
                    return cached

                # Perform search
                response = await self._perform_search(request)

                # Cache results
                await self.cache_search_results(request, response)

                return response
    """

    # These attributes must be set by the implementing class
    _cache_service: CacheService | None
    _cache_ttl: int  # TTL in seconds
    _cache_prefix: str  # Prefix for cache keys

    @abstractmethod
    def get_cache_fields(self, request: SearchRequestType) -> dict[str, Any]:
        """Extract fields from the search request to use for cache key generation.

        This method should return a dictionary of fields that uniquely identify
        the search request. Only include fields that affect search results.

        Args:
            request: The search request

        Returns:
            Dictionary of fields to include in cache key
        """

    def generate_cache_key(self, request: SearchRequestType) -> str:
        """Generate a consistent cache key for the search request.

        Args:
            request: The search request

        Returns:
            Cache key string
        """
        # Get fields to include in cache key
        cache_fields = self.get_cache_fields(request)

        # Sort fields for consistency
        sorted_fields = sorted(cache_fields.items())

        # Create a deterministic string representation
        key_data = json.dumps(sorted_fields, sort_keys=True, default=str)

        # Generate hash for compact key
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]

        # Add prefix for namespacing
        return f"{self._cache_prefix}:search:{key_hash}"

    async def get_cached_search(
        self, request: SearchRequestType
    ) -> SearchResponseType | None:
        """Get cached search results if available.

        Args:
            request: The search request

        Returns:
            Cached response if available and valid, None otherwise
        """
        if not self._cache_service:
            return None

        try:
            cache_key = self.generate_cache_key(request)

            # Get from cache
            cached_data = await self._cache_service.get_json(cache_key)

            if cached_data:
                logger.info(
                    "Cache hit for search request",
                    extra={
                        "cache_key": cache_key,
                        "service": self._cache_prefix,
                    },
                )

                # Reconstruct response object
                # The implementing class should store the response class
                response_class = self._get_response_class()
                return response_class(**cached_data)
            else:
                logger.debug(
                    "Cache miss for search request",
                    extra={
                        "cache_key": cache_key,
                        "service": self._cache_prefix,
                    },
                )
                return None

        except Exception as e:
            logger.warning(
                "Failed to get cached search results",
                extra={
                    "error": str(e),
                    "service": self._cache_prefix,
                },
            )
            return None

    async def cache_search_results(
        self,
        request: SearchRequestType,
        response: SearchResponseType,
        ttl: int | None = None,
    ) -> bool:
        """Cache search results.

        Args:
            request: The search request
            response: The search response to cache
            ttl: Optional custom TTL in seconds (uses default if not provided)

        Returns:
            True if successfully cached, False otherwise
        """
        if not self._cache_service:
            return False

        try:
            cache_key = self.generate_cache_key(request)
            ttl = ttl or self._cache_ttl

            # Convert response to dict for caching
            response_data = response.model_dump()

            # Add metadata
            response_data["_cached_at"] = datetime.now(UTC).isoformat()
            response_data["_cache_version"] = "1.0"

            # Store in cache
            success = await self._cache_service.set_json(
                cache_key, response_data, ttl=ttl
            )

            if success:
                logger.info(
                    "Successfully cached search results",
                    extra={
                        "cache_key": cache_key,
                        "ttl": ttl,
                        "service": self._cache_prefix,
                    },
                )
            else:
                logger.warning(
                    "Failed to cache search results",
                    extra={
                        "cache_key": cache_key,
                        "service": self._cache_prefix,
                    },
                )

            return success

        except Exception as e:
            logger.error(
                "Error caching search results",
                extra={
                    "error": str(e),
                    "service": self._cache_prefix,
                },
            )
            return False

    async def invalidate_cache(self, request: SearchRequestType) -> bool:
        """Invalidate cached results for a specific search request.

        Args:
            request: The search request to invalidate

        Returns:
            True if cache was invalidated, False otherwise
        """
        if not self._cache_service:
            return False

        try:
            cache_key = self.generate_cache_key(request)
            deleted = await self._cache_service.delete(cache_key)

            if deleted:
                logger.info(
                    "Invalidated cache for search request",
                    extra={
                        "cache_key": cache_key,
                        "service": self._cache_prefix,
                    },
                )

            return bool(deleted)

        except Exception as e:
            logger.error(
                "Error invalidating cache",
                extra={
                    "error": str(e),
                    "service": self._cache_prefix,
                },
            )
            return False

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate all cached results matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "my_service:search:*")

        Returns:
            Number of keys deleted
        """
        if not self._cache_service:
            return 0

        try:
            # Use the service prefix in the pattern
            full_pattern = f"{self._cache_prefix}:search:{pattern}"
            deleted = await self._cache_service.delete_pattern(full_pattern)

            logger.info(
                "Invalidated cache pattern",
                extra={
                    "pattern": full_pattern,
                    "deleted_count": deleted,
                    "service": self._cache_prefix,
                },
            )

            return deleted

        except Exception as e:
            logger.error(
                "Error invalidating cache pattern",
                extra={
                    "error": str(e),
                    "pattern": pattern,
                    "service": self._cache_prefix,
                },
            )
            return 0

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for this service.

        Returns:
            Dictionary with cache statistics
        """
        if not self._cache_service:
            return {"enabled": False}

        try:
            # Get all keys for this service
            pattern = f"{self._cache_prefix}:search:*"
            keys = await self._cache_service.keys(pattern)

            # Get cache info
            info = await self._cache_service.info()

            return {
                "enabled": True,
                "service": self._cache_prefix,
                "cached_searches": len(keys),
                "ttl_seconds": self._cache_ttl,
                "cache_info": info,
            }

        except Exception as e:
            logger.error(
                "Error getting cache stats",
                extra={
                    "error": str(e),
                    "service": self._cache_prefix,
                },
            )
            return {
                "enabled": True,
                "service": self._cache_prefix,
                "error": str(e),
            }

    @abstractmethod
    def _get_response_class(self) -> type[SearchResponseType]:
        """Get the response class for deserialization.

        This method must be implemented by the concrete class to provide
        the proper response type for cache deserialization.

        Returns:
            The response class type
        """


class SimpleCacheMixin:
    """Simplified cache mixin for non-search caching patterns.

    This mixin provides basic caching functionality for general use cases
    that don't follow the search request/response pattern.
    """

    _cache_service: CacheService | None
    _cache_ttl: int
    _cache_prefix: str

    async def cache_get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        if not self._cache_service:
            return default

        full_key = f"{self._cache_prefix}:{key}"
        return await self._cache_service.get_json(full_key, default)

    async def cache_set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a value in cache."""
        if not self._cache_service:
            return False

        full_key = f"{self._cache_prefix}:{key}"
        ttl = ttl or self._cache_ttl
        return await self._cache_service.set_json(full_key, value, ttl)

    async def cache_delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self._cache_service:
            return False

        full_key = f"{self._cache_prefix}:{key}"
        return bool(await self._cache_service.delete(full_key))

    async def cache_exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self._cache_service:
            return False

        full_key = f"{self._cache_prefix}:{key}"
        return bool(await self._cache_service.exists(full_key))
