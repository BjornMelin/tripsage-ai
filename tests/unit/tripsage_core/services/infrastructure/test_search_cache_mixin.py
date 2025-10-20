"""Tests for SearchCacheMixin and SimpleCacheMixin.

This module tests the caching mixin functionality to ensure consistent
caching behavior across services.
"""

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, Field

from tripsage_core.services.infrastructure.cache_service import CacheService
from tripsage_core.services.infrastructure.search_cache_mixin import (
    SearchCacheMixin,
    SimpleCacheMixin,
)


# Mock models for search functionality
class MockSearchRequest(BaseModel):
    """Mock search request model for testing."""

    query: str = Field(..., description="Search query")
    filters: dict[str, Any] | None = Field(default=None, description="Search filters")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=20, description="Page size")


class MockSearchResponse(BaseModel):
    """Mock search response model for testing."""

    results: list[dict[str, Any]] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total result count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


# Concrete implementation for testing
class MockSearchService(SearchCacheMixin[MockSearchRequest, MockSearchResponse]):
    """Mock service implementing SearchCacheMixin for testing."""

    def __init__(self, cache_service: CacheService | None = None):
        self._cache_service = cache_service
        self._cache_ttl = 300  # 5 minutes
        self._cache_prefix = "test_search"

    def get_cache_fields(self, request: MockSearchRequest) -> dict[str, Any]:
        """Extract cacheable fields from request."""
        fields = {
            "query": request.query,
            "page": request.page,
            "page_size": request.page_size,
        }
        if request.filters:
            fields["filters"] = json.dumps(request.filters, sort_keys=True)
        return fields

    def _get_response_class(self) -> type[MockSearchResponse]:
        """Get response class for deserialization."""
        return MockSearchResponse


class MockSimpleService(SimpleCacheMixin):
    """Test service implementing SimpleCacheMixin."""

    def __init__(self, cache_service: CacheService | None = None):
        self._cache_service = cache_service
        self._cache_ttl = 600  # 10 minutes
        self._cache_prefix = "test_simple"


class TestSearchCacheMixin:
    """Test SearchCacheMixin functionality."""

    @pytest.fixture
    def mock_cache_service(self):
        """Create mock cache service."""
        return AsyncMock(spec=CacheService)

    @pytest.fixture
    def test_service(self, mock_cache_service):
        """Create test service with mocked cache."""
        return MockSearchService(cache_service=mock_cache_service)

    @pytest.fixture
    def test_request(self):
        """Create test search request."""
        return MockSearchRequest(
            query="test query",
            filters={"category": "books", "price_max": 50},
            page=1,
            page_size=20,
        )

    @pytest.fixture
    def test_response(self):
        """Create test search response."""
        return MockSearchResponse(
            results=[
                {"id": 1, "title": "Test Item 1"},
                {"id": 2, "title": "Test Item 2"},
            ],
            total_count=2,
            page=1,
            page_size=20,
        )

    def test_generate_cache_key(self, test_service, test_request):
        """Test cache key generation."""
        key = test_service.generate_cache_key(test_request)

        # Key should have correct format
        assert key.startswith("test_search:search:")
        assert len(key) == len("test_search:search:") + 16  # 16 char hash

        # Same request should generate same key
        key2 = test_service.generate_cache_key(test_request)
        assert key == key2

        # Different request should generate different key
        different_request = MockSearchRequest(query="different query")
        different_key = test_service.generate_cache_key(different_request)
        assert key != different_key

    def test_get_cache_fields(self, test_service, test_request):
        """Test cache field extraction."""
        fields = test_service.get_cache_fields(test_request)

        assert fields["query"] == "test query"
        assert fields["page"] == 1
        assert fields["page_size"] == 20
        assert "filters" in fields
        assert json.loads(fields["filters"]) == {"category": "books", "price_max": 50}

    async def test_get_cached_search_hit(
        self, test_service, test_request, test_response, mock_cache_service
    ):
        """Test getting cached search results (cache hit)."""
        # Setup mock to return cached data
        cached_data = test_response.model_dump()
        cached_data["_cached_at"] = datetime.now().isoformat()
        mock_cache_service.get_json.return_value = cached_data

        # Get cached result
        result = await test_service.get_cached_search(test_request)

        # Verify result
        assert result is not None
        assert isinstance(result, MockSearchResponse)
        assert result.total_count == test_response.total_count
        assert len(result.results) == len(test_response.results)

        # Verify cache was called with correct key
        cache_key = test_service.generate_cache_key(test_request)
        mock_cache_service.get_json.assert_called_once_with(cache_key)

    async def test_get_cached_search_miss(
        self, test_service, test_request, mock_cache_service
    ):
        """Test getting cached search results (cache miss)."""
        # Setup mock to return None
        mock_cache_service.get_json.return_value = None

        # Get cached result
        result = await test_service.get_cached_search(test_request)

        # Verify result
        assert result is None

        # Verify cache was called
        mock_cache_service.get_json.assert_called_once()

    async def test_get_cached_search_no_cache_service(self, test_request):
        """Test getting cached search with no cache service."""
        service = MockSearchService(cache_service=None)
        result = await service.get_cached_search(test_request)
        assert result is None

    async def test_cache_search_results(
        self, test_service, test_request, test_response, mock_cache_service
    ):
        """Test caching search results."""
        # Setup mock
        mock_cache_service.set_json.return_value = True

        # Cache results
        success = await test_service.cache_search_results(test_request, test_response)

        # Verify success
        assert success is True

        # Verify cache was called correctly
        cache_key = test_service.generate_cache_key(test_request)
        mock_cache_service.set_json.assert_called_once()
        call_args = mock_cache_service.set_json.call_args

        assert call_args[0][0] == cache_key
        assert call_args[0][1]["total_count"] == test_response.total_count
        assert "_cached_at" in call_args[0][1]
        assert "_cache_version" in call_args[0][1]
        assert call_args[1]["ttl"] == 300

    async def test_cache_search_results_custom_ttl(
        self, test_service, test_request, test_response, mock_cache_service
    ):
        """Test caching with custom TTL."""
        mock_cache_service.set_json.return_value = True

        # Cache with custom TTL
        success = await test_service.cache_search_results(
            test_request, test_response, ttl=600
        )

        # Verify TTL was used
        assert success is True
        call_args = mock_cache_service.set_json.call_args
        assert call_args[1]["ttl"] == 600

    async def test_cache_search_results_failure(
        self, test_service, test_request, test_response, mock_cache_service
    ):
        """Test caching failure handling."""
        # Setup mock to fail
        mock_cache_service.set_json.side_effect = Exception("Cache error")

        # Cache results
        success = await test_service.cache_search_results(test_request, test_response)

        # Should return False on error
        assert success is False

    async def test_invalidate_cache(
        self, test_service, test_request, mock_cache_service
    ):
        """Test cache invalidation."""
        # Setup mock
        mock_cache_service.delete.return_value = 1

        # Invalidate cache
        success = await test_service.invalidate_cache(test_request)

        # Verify success
        assert success is True

        # Verify cache was called
        cache_key = test_service.generate_cache_key(test_request)
        mock_cache_service.delete.assert_called_once_with(cache_key)

    async def test_invalidate_cache_pattern(self, test_service, mock_cache_service):
        """Test pattern-based cache invalidation."""
        # Setup mock
        mock_cache_service.delete_pattern.return_value = 5

        # Invalidate pattern
        deleted = await test_service.invalidate_cache_pattern("*")

        # Verify result
        assert deleted == 5

        # Verify cache was called with full pattern
        mock_cache_service.delete_pattern.assert_called_once_with(
            "test_search:search:*"
        )

    async def test_get_cache_stats(self, test_service, mock_cache_service):
        """Test getting cache statistics."""
        # Setup mocks
        mock_cache_service.keys.return_value = ["key1", "key2", "key3"]
        mock_cache_service.info.return_value = {"used_memory": "1MB"}

        # Get stats
        stats = await test_service.get_cache_stats()

        # Verify stats
        assert stats["enabled"] is True
        assert stats["service"] == "test_search"
        assert stats["cached_searches"] == 3
        assert stats["ttl_seconds"] == 300
        assert stats["cache_info"]["used_memory"] == "1MB"

        # Verify cache calls
        mock_cache_service.keys.assert_called_once_with("test_search:search:*")
        mock_cache_service.info.assert_called_once()


class TestSimpleCacheMixin:
    """Test SimpleCacheMixin functionality."""

    @pytest.fixture
    def mock_cache_service(self):
        """Create mock cache service."""
        return AsyncMock(spec=CacheService)

    @pytest.fixture
    def test_service(self, mock_cache_service):
        """Create test service with mocked cache."""
        return MockSimpleService(cache_service=mock_cache_service)

    async def test_cache_get(self, test_service, mock_cache_service):
        """Test getting value from cache."""
        # Setup mock
        mock_cache_service.get_json.return_value = {"data": "test"}

        # Get from cache
        result = await test_service.cache_get("test_key")

        # Verify result
        assert result == {"data": "test"}

        # Verify cache was called
        mock_cache_service.get_json.assert_called_once_with(
            "test_simple:test_key", None
        )

    async def test_cache_get_with_default(self, test_service, mock_cache_service):
        """Test getting value with default."""
        # Setup mock to return None
        mock_cache_service.get_json.return_value = None

        # Get from cache with default
        result = await test_service.cache_get("test_key", default="default_value")

        # Should return None (from cache service)
        assert result is None

        # Verify cache was called with default
        mock_cache_service.get_json.assert_called_once_with(
            "test_simple:test_key", "default_value"
        )

    async def test_cache_set(self, test_service, mock_cache_service):
        """Test setting value in cache."""
        # Setup mock
        mock_cache_service.set_json.return_value = True

        # Set in cache
        success = await test_service.cache_set("test_key", {"data": "test"})

        # Verify success
        assert success is True

        # Verify cache was called
        mock_cache_service.set_json.assert_called_once_with(
            "test_simple:test_key",
            {"data": "test"},
            600,  # Default TTL
        )

    async def test_cache_set_custom_ttl(self, test_service, mock_cache_service):
        """Test setting value with custom TTL."""
        mock_cache_service.set_json.return_value = True

        # Set with custom TTL
        success = await test_service.cache_set("test_key", "value", ttl=1200)

        # Verify TTL was used
        assert success is True
        call_args = mock_cache_service.set_json.call_args
        assert call_args[0][2] == 1200

    async def test_cache_delete(self, test_service, mock_cache_service):
        """Test deleting from cache."""
        # Setup mock
        mock_cache_service.delete.return_value = 1

        # Delete from cache
        success = await test_service.cache_delete("test_key")

        # Verify success
        assert success is True

        # Verify cache was called
        mock_cache_service.delete.assert_called_once_with("test_simple:test_key")

    async def test_cache_exists(self, test_service, mock_cache_service):
        """Test checking key existence."""
        # Setup mock
        mock_cache_service.exists.return_value = 1

        # Check existence
        exists = await test_service.cache_exists("test_key")

        # Verify result
        assert exists is True

        # Verify cache was called
        mock_cache_service.exists.assert_called_once_with("test_simple:test_key")

    async def test_no_cache_service(self):
        """Test operations with no cache service."""
        service = MockSimpleService(cache_service=None)

        # All operations should handle gracefully
        assert await service.cache_get("key") is None
        assert await service.cache_set("key", "value") is False
        assert await service.cache_delete("key") is False
        assert await service.cache_exists("key") is False


class TestIntegration:
    """Test integration scenarios."""

    async def test_complete_cache_flow(self):
        """Test complete cache flow with real-like scenario."""
        # Create mock cache service
        cache_service = AsyncMock(spec=CacheService)
        cache_storage = {}  # Simulate cache storage

        # Mock cache operations
        async def mock_get_json(key, default=None):
            return cache_storage.get(key, default)

        async def mock_set_json(key, value, ttl):
            cache_storage[key] = value
            return True

        async def mock_delete(key):
            if key in cache_storage:
                del cache_storage[key]
                return 1
            return 0

        cache_service.get_json.side_effect = mock_get_json
        cache_service.set_json.side_effect = mock_set_json
        cache_service.delete.side_effect = mock_delete

        # Create service
        service = MockSearchService(cache_service=cache_service)

        # Create request and response
        request = MockSearchRequest(query="python books", page=1)
        response = MockSearchResponse(
            results=[{"id": 1, "title": "Learning Python"}],
            total_count=1,
            page=1,
            page_size=20,
        )

        # First search - cache miss
        cached = await service.get_cached_search(request)
        assert cached is None

        # Cache the results
        success = await service.cache_search_results(request, response)
        assert success is True

        # Second search - cache hit
        cached = await service.get_cached_search(request)
        assert cached is not None
        assert cached.total_count == response.total_count
        assert cached.results == response.results

        # Invalidate cache
        invalidated = await service.invalidate_cache(request)
        assert invalidated is True

        # Third search - cache miss again
        cached = await service.get_cached_search(request)
        assert cached is None
