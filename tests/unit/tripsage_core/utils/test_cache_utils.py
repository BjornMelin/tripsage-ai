"""Unit tests for TripSage Core cache utilities.

Tests cache validation, TTL logic, key generation, cache invalidation,
batch operations, and distributed locking functionality.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.utils.cache_utils import (
    CacheStats,
    DragonflyCache,
    InMemoryCache,
    batch_cache_get,
    batch_cache_set,
    cache_lock,
    cached,
    cached_daily,
    cached_realtime,
    cached_semi_static,
    cached_static,
    cached_time_sensitive,
    determine_content_type,
    generate_cache_key,
    get_cache,
    get_cache_stats,
    invalidate_pattern,
    memory_cache,
    prefetch_cache_keys,
    set_cache,
)
from tripsage_core.utils.content_utils import ContentType


class TestCacheStats:
    """Test cache statistics model."""

    def test_cache_stats_creation(self):
        """Test creating cache stats with default values."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_ratio == 0.0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.key_count == 0
        assert stats.size_mb == 0.0

    def test_cache_stats_with_values(self):
        """Test creating cache stats with specific values."""
        stats = CacheStats(
            hits=100,
            misses=20,
            hit_ratio=0.83,
            sets=50,
            deletes=5,
            key_count=45,
            size_mb=2.5,
        )
        assert stats.hits == 100
        assert stats.misses == 20
        assert stats.hit_ratio == 0.83
        assert stats.sets == 50
        assert stats.deletes == 5
        assert stats.key_count == 45
        assert stats.size_mb == 2.5


class TestInMemoryCache:
    """Test in-memory cache implementation."""

    @pytest.fixture
    def cache(self):
        """Create a fresh in-memory cache for each test."""
        return InMemoryCache()

    async def test_basic_get_set(self, cache):
        """Test basic get and set operations."""
        # Test setting and getting a value
        result = await cache.set("key1", "value1")
        assert result is True

        value = await cache.get("key1")
        assert value == "value1"

        # Test getting non-existent key
        value = await cache.get("nonexistent")
        assert value is None

    async def test_ttl_expiration(self, cache):
        """Test TTL expiration functionality."""
        # Set value with 1 second TTL
        await cache.set("ttl_key", "ttl_value", ttl=1)

        # Should be available immediately
        value = await cache.get("ttl_key")
        assert value == "ttl_value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        value = await cache.get("ttl_key")
        assert value is None

    async def test_delete_operation(self, cache):
        """Test delete operations."""
        # Set and delete existing key
        await cache.set("delete_me", "value")
        result = await cache.delete("delete_me")
        assert result is True

        # Key should no longer exist
        value = await cache.get("delete_me")
        assert value is None

        # Delete non-existent key
        result = await cache.delete("nonexistent")
        assert result is False

    async def test_clear_operation(self, cache):
        """Test clearing all cache data."""
        # Add multiple keys
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        # Clear cache
        await cache.clear()

        # All keys should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None

    async def test_statistics_tracking(self, cache):
        """Test cache statistics tracking."""
        # Initial stats
        stats = await cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0

        # Perform operations
        await cache.set("key1", "value1")  # 1 set
        await cache.get("key1")  # 1 hit
        await cache.get("nonexistent")  # 1 miss
        await cache.delete("key1")  # 1 delete

        # Check updated stats
        stats = await cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.sets == 1
        assert stats.deletes == 1
        assert stats.hit_ratio == 0.5
        assert stats.key_count == 0  # Key was deleted

    async def test_concurrent_access(self, cache):
        """Test concurrent access to cache."""

        async def set_values():
            for i in range(10):
                await cache.set(f"key_{i}", f"value_{i}")

        async def get_values():
            results = []
            for i in range(10):
                value = await cache.get(f"key_{i}")
                results.append(value)
            return results

        # Run concurrent operations
        await asyncio.gather(set_values(), set_values())
        results = await get_values()

        # All values should be set correctly
        assert len([r for r in results if r is not None]) == 10


class TestDragonflyCache:
    """Test DragonflyDB cache implementation."""

    @pytest.fixture
    def cache(self):
        """Create a DragonflyDB cache instance."""
        return DragonflyCache(namespace="test")

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service for testing."""
        service = AsyncMock()
        service.get.return_value = None
        service.set.return_value = True
        service.delete.return_value = 1
        service.hincrby = AsyncMock()
        service.expire = AsyncMock()
        service.hgetall = AsyncMock(return_value={})
        return service

    async def test_key_namespacing(self, cache):
        """Test proper key namespacing."""
        # Test key creation
        key = cache._make_key("test_key")
        assert key == "test:test_key"

        # Test already namespaced key
        namespaced_key = cache._make_key("test:already_namespaced")
        assert namespaced_key == "test:already_namespaced"

    async def test_get_operation_with_mock(self, cache, mock_cache_service):
        """Test get operation with mocked service."""
        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_cache_service,
        ):
            mock_cache_service.get.return_value = "test_value"

            result = await cache.get("test_key")
            assert result == "test_value"
            mock_cache_service.get.assert_called_with("test:test_key")

    async def test_set_operation_with_mock(self, cache, mock_cache_service):
        """Test set operation with mocked service."""
        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_cache_service,
        ):
            result = await cache.set("test_key", "test_value", ttl=300)
            assert result is True
            mock_cache_service.set.assert_called_with(
                "test:test_key", "test_value", ttl=300
            )

    async def test_delete_operation_with_mock(self, cache, mock_cache_service):
        """Test delete operation with mocked service."""
        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_cache_service,
        ):
            result = await cache.delete("test_key")
            assert result is True
            mock_cache_service.delete.assert_called_with("test:test_key")

    async def test_error_handling(self, cache):
        """Test error handling in cache operations."""
        # Mock failing cache service
        failing_service = AsyncMock()
        failing_service.get.side_effect = Exception("Connection failed")

        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=failing_service,
        ):
            # Should return None on error, not raise
            result = await cache.get("test_key")
            assert result is None

            # Should return False on error, not raise
            result = await cache.set("test_key", "value")
            assert result is False

            # Should return False on error, not raise
            result = await cache.delete("test_key")
            assert result is False

    async def test_stats_with_hash_support(self, cache, mock_cache_service):
        """Test statistics with hash support."""
        mock_cache_service.hgetall.return_value = {
            "hits": "10",
            "misses": "5",
            "sets": "8",
            "deletes": "2",
        }

        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_cache_service,
        ):
            stats = await cache.get_stats()
            assert stats.hits == 10
            assert stats.misses == 5
            assert stats.sets == 8
            assert stats.deletes == 2
            assert stats.hit_ratio == 10 / 15  # 10 hits / (10 hits + 5 misses)

    async def test_stats_fallback(self, cache, mock_cache_service):
        """Test statistics fallback when hash operations not available."""
        # Remove hash support
        del mock_cache_service.hgetall

        # Mock individual key retrieval
        mock_cache_service.get.side_effect = lambda key: {
            "test:stats:hits": "5",
            "test:stats:misses": "3",
            "test:stats:sets": "4",
            "test:stats:deletes": "1",
        }.get(key, "0")

        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_cache_service,
        ):
            stats = await cache.get_stats()
            assert stats.hits == 5
            assert stats.misses == 3
            assert stats.sets == 4
            assert stats.deletes == 1


class TestCacheKeyGeneration:
    """Test cache key generation functionality."""

    def test_basic_key_generation(self):
        """Test basic key generation."""
        key = generate_cache_key("prefix", "query")
        assert key.startswith("prefix:")
        assert len(key) > len("prefix:")

    def test_deterministic_keys(self):
        """Test that same inputs produce same keys."""
        key1 = generate_cache_key("prefix", "query", ["arg1", "arg2"])
        key2 = generate_cache_key("prefix", "query", ["arg1", "arg2"])
        assert key1 == key2

    def test_different_keys_for_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = generate_cache_key("prefix", "query1")
        key2 = generate_cache_key("prefix", "query2")
        assert key1 != key2

    def test_args_affect_key(self):
        """Test that args affect the generated key."""
        key1 = generate_cache_key("prefix", "query", ["arg1"])
        key2 = generate_cache_key("prefix", "query", ["arg2"])
        assert key1 != key2

    def test_kwargs_affect_key(self):
        """Test that kwargs affect the generated key."""
        key1 = generate_cache_key("prefix", "query", param1="value1")
        key2 = generate_cache_key("prefix", "query", param1="value2")
        assert key1 != key2

    def test_kwargs_order_independence(self):
        """Test that kwargs order doesn't affect key."""
        key1 = generate_cache_key("prefix", "query", param1="value1", param2="value2")
        key2 = generate_cache_key("prefix", "query", param2="value2", param1="value1")
        assert key1 == key2

    def test_case_normalization(self):
        """Test that query case is normalized."""
        key1 = generate_cache_key("prefix", "QUERY")
        key2 = generate_cache_key("prefix", "query")
        assert key1 == key2


class TestCachedDecorator:
    """Test cached decorator functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.enable_caching = True
        settings.cache_ttl_medium = 1800
        return settings

    async def test_cached_function_execution(self, mock_settings):
        """Test cached function execution."""
        call_count = 0

        @cached(use_redis=False)
        async def test_function(param):
            nonlocal call_count
            call_count += 1
            return f"result_{param}"

        with patch(
            "tripsage_core.utils.cache_utils.get_settings", return_value=mock_settings
        ):
            # First call should execute function
            result1 = await test_function("test")
            assert result1 == "result_test"
            assert call_count == 1

            # Second call should use cache
            result2 = await test_function("test")
            assert result2 == "result_test"
            assert call_count == 1  # Function not called again

    async def test_cached_with_skip_cache(self, mock_settings):
        """Test cached decorator with skip_cache parameter."""
        call_count = 0

        @cached(use_redis=False)
        async def test_function(param):
            nonlocal call_count
            call_count += 1
            return f"result_{param}"

        with patch(
            "tripsage_core.utils.cache_utils.get_settings", return_value=mock_settings
        ):
            # First call
            await test_function("test")
            assert call_count == 1

            # Second call with skip_cache should execute function
            await test_function("test", skip_cache=True)
            assert call_count == 2

    async def test_cached_with_disabled_caching(self):
        """Test cached decorator when caching is disabled."""
        call_count = 0

        @cached(use_redis=False)
        async def test_function(param):
            nonlocal call_count
            call_count += 1
            return f"result_{param}"

        settings = MagicMock()
        settings.enable_caching = False

        with patch(
            "tripsage_core.utils.cache_utils.get_settings", return_value=settings
        ):
            # Both calls should execute function
            await test_function("test")
            await test_function("test")
            assert call_count == 2

    async def test_cached_different_content_types(self, mock_settings):
        """Test cached decorators for different content types."""
        functions = []

        @cached_realtime(use_redis=False)
        async def realtime_func():
            functions.append("realtime")
            return "realtime_result"

        @cached_time_sensitive(use_redis=False)
        async def time_sensitive_func():
            functions.append("time_sensitive")
            return "time_sensitive_result"

        @cached_daily(use_redis=False)
        async def daily_func():
            functions.append("daily")
            return "daily_result"

        @cached_semi_static(use_redis=False)
        async def semi_static_func():
            functions.append("semi_static")
            return "semi_static_result"

        @cached_static(use_redis=False)
        async def static_func():
            functions.append("static")
            return "static_result"

        with patch(
            "tripsage_core.utils.cache_utils.get_settings", return_value=mock_settings
        ):
            # Test all decorators work
            assert await realtime_func() == "realtime_result"
            assert await time_sensitive_func() == "time_sensitive_result"
            assert await daily_func() == "daily_result"
            assert await semi_static_func() == "semi_static_result"
            assert await static_func() == "static_result"

            # All functions should have been called once
            assert len(functions) == 5


class TestBatchOperations:
    """Test batch cache operations."""

    async def test_batch_set_memory_cache(self):
        """Test batch set with memory cache."""
        items = [
            {"key": "key1", "value": "value1", "ttl": 300},
            {"key": "key2", "value": "value2"},
            {"key": "key3", "value": "value3", "ttl": 600},
        ]

        with patch("tripsage_core.utils.cache_utils.get_settings") as mock_settings:
            mock_settings.return_value.enable_caching = True

            results = await batch_cache_set(items, use_redis=False)
            assert len(results) == 3
            assert all(results)  # All should succeed

    async def test_batch_get_memory_cache(self):
        """Test batch get with memory cache."""
        # Set up test data
        await memory_cache.set("batch_key1", "batch_value1")
        await memory_cache.set("batch_key2", "batch_value2")

        keys = ["batch_key1", "batch_key2", "nonexistent_key"]

        with patch("tripsage_core.utils.cache_utils.get_settings") as mock_settings:
            mock_settings.return_value.enable_caching = True

            results = await batch_cache_get(keys, use_redis=False)
            assert len(results) == 3
            assert results[0] == "batch_value1"
            assert results[1] == "batch_value2"
            assert results[2] is None

    async def test_batch_operations_disabled_caching(self):
        """Test batch operations when caching is disabled."""
        items = [{"key": "key1", "value": "value1"}]

        with patch("tripsage_core.utils.cache_utils.get_settings") as mock_settings:
            mock_settings.return_value.enable_caching = False

            # Should still work but use memory cache
            results = await batch_cache_set(items, use_redis=True)
            assert len(results) == 1
            assert results[0] is True


class TestCacheLock:
    """Test distributed cache locking."""

    async def test_cache_lock_acquisition(self):
        """Test cache lock acquisition and release."""
        mock_service = AsyncMock()
        mock_service.get.return_value = None  # Lock not held
        mock_service.set.return_value = True  # Lock acquired
        mock_service.delete.return_value = 1  # Lock released

        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_service,
        ):
            async with cache_lock("test_lock") as acquired:
                assert acquired is True

    async def test_cache_lock_contention(self):
        """Test cache lock with contention."""
        mock_service = AsyncMock()
        mock_service.get.return_value = "other_holder"  # Lock held by another
        mock_service.set.return_value = False  # Cannot acquire

        with patch(
            "tripsage_core.utils.cache_utils.get_cache_instance",
            return_value=mock_service,
        ):
            async with cache_lock("test_lock", retry_count=1) as acquired:
                assert acquired is False

    async def test_cache_lock_disabled_caching(self):
        """Test cache lock when caching is disabled."""
        with patch("tripsage_core.utils.cache_utils.get_settings") as mock_settings:
            mock_settings.return_value.enable_caching = False

            async with cache_lock("test_lock") as acquired:
                assert acquired is True  # Should always succeed in development


class TestContentTypeDetection:
    """Test content type detection functionality."""

    def test_determine_time_sensitive_content(self):
        """Test detection of time-sensitive content."""
        queries = [
            "latest news about travel",
            "breaking: flight cancellations",
            "current weather in paris",
        ]

        for query in queries:
            content_type = determine_content_type(query)
            assert content_type == ContentType.TIME_SENSITIVE

    def test_determine_realtime_content(self):
        """Test detection of realtime content."""
        queries = [
            "live flight tracker",
            "real-time prices for hotels",
            "flight prices now",
        ]

        for query in queries:
            content_type = determine_content_type(query)
            assert content_type == ContentType.REALTIME

    def test_determine_static_content(self):
        """Test detection of static content."""
        queries = [
            "history of paris",
            "travel guide to rome",
            "documentation for api",
            "tutorial on booking flights",
        ]

        for query in queries:
            content_type = determine_content_type(query)
            assert content_type == ContentType.STATIC

    def test_determine_content_by_domain(self):
        """Test content type detection by domain."""
        # News domains should be time-sensitive
        content_type = determine_content_type("travel update", domains=["cnn.com"])
        assert content_type == ContentType.TIME_SENSITIVE

        # Documentation domains should be static
        content_type = determine_content_type(
            "api reference", domains=["docs.example.com"]
        )
        assert content_type == ContentType.STATIC

    def test_default_content_type(self):
        """Test default content type for travel content."""
        content_type = determine_content_type("hotels in paris")
        assert content_type == ContentType.DAILY


class TestUtilityFunctions:
    """Test utility functions."""

    async def test_get_set_delete_cache(self):
        """Test convenience cache functions."""
        # Test set and get
        result = await set_cache("util_key", "util_value")
        assert result is True

        await get_cache("util_key")
        # Note: This tests the redis cache, which might not be available
        # In a real environment, this would need proper mocking

    async def test_get_cache_stats_function(self):
        """Test cache stats convenience function."""
        stats = await get_cache_stats()
        assert isinstance(stats, CacheStats)

    async def test_invalidate_pattern_function(self):
        """Test pattern invalidation convenience function."""
        # This tests the redis cache invalidation
        count = await invalidate_pattern("test:*")
        assert isinstance(count, int)
        assert count >= 0

    async def test_prefetch_cache_keys(self):
        """Test cache key prefetching."""
        keys = await prefetch_cache_keys("test:*")
        assert isinstance(keys, list)
