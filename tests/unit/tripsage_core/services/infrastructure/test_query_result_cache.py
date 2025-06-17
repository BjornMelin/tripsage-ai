"""
Comprehensive tests for QueryResultCache.

This module provides comprehensive test coverage for the intelligent query result
caching functionality including fingerprinting, multi-level caching, compression,
TTL management, cache invalidation, and vector search caching.
"""

import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from tripsage_core.services.infrastructure.cache_service import (
    CacheService,
    QueryResultCache,
)


class TestQueryResultCache:
    """Comprehensive test suite for QueryResultCache."""

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        service = AsyncMock(spec=CacheService)
        service.ensure_connected = AsyncMock()
        service.get_json = AsyncMock(return_value=None)
        service.set_json = AsyncMock(return_value=True)
        service.delete = AsyncMock(return_value=1)
        return service

    @pytest.fixture
    def query_cache(self, mock_cache_service):
        """Create QueryResultCache instance with mocked dependencies."""
        return QueryResultCache(mock_cache_service, namespace="test_cache")

    # Query Fingerprinting Tests

    def test_generate_query_fingerprint_basic(self, query_cache):
        """Test basic query fingerprint generation."""
        query = "SELECT * FROM users"
        fingerprint = query_cache._generate_query_fingerprint(query)

        assert fingerprint.startswith("test_cache:query:")
        assert len(fingerprint.split(":")[-1]) == 16  # 16-char hash

        # Same query should produce same fingerprint
        fingerprint2 = query_cache._generate_query_fingerprint(query)
        assert fingerprint == fingerprint2

    def test_generate_query_fingerprint_with_params(self, query_cache):
        """Test query fingerprint with parameters."""
        query = "SELECT * FROM users WHERE age > ?"
        params = {"age": 18, "active": True}

        fingerprint1 = query_cache._generate_query_fingerprint(query, params)
        fingerprint2 = query_cache._generate_query_fingerprint(query, params)

        assert fingerprint1 == fingerprint2

        # Different params should produce different fingerprint
        params2 = {"age": 21, "active": True}
        fingerprint3 = query_cache._generate_query_fingerprint(query, params2)
        assert fingerprint1 != fingerprint3

    def test_generate_query_fingerprint_with_table(self, query_cache):
        """Test query fingerprint with table parameter."""
        query = "SELECT * FROM table"
        table = "users"

        fingerprint1 = query_cache._generate_query_fingerprint(query, table=table)
        fingerprint2 = query_cache._generate_query_fingerprint(query, table="trips")

        assert fingerprint1 != fingerprint2

    def test_generate_query_fingerprint_normalization(self, query_cache):
        """Test query normalization in fingerprinting."""
        query1 = "SELECT   *   FROM   users"
        query2 = "select * from users"
        query3 = "SELECT * FROM USERS"

        fingerprint1 = query_cache._generate_query_fingerprint(query1)
        fingerprint2 = query_cache._generate_query_fingerprint(query2)
        fingerprint3 = query_cache._generate_query_fingerprint(query3)

        assert fingerprint1 == fingerprint2 == fingerprint3

    # Intelligent TTL Tests

    def test_determine_intelligent_ttl_realtime(self, query_cache):
        """Test TTL determination for real-time queries."""
        query = "SELECT price FROM stocks WHERE symbol = 'AAPL'"
        ttl = query_cache._determine_intelligent_ttl(query)
        assert ttl == 60  # 1 minute for real-time data

    def test_determine_intelligent_ttl_time_sensitive(self, query_cache):
        """Test TTL determination for time-sensitive queries."""
        query = "SELECT * FROM news WHERE date = today"
        ttl = query_cache._determine_intelligent_ttl(query)
        assert ttl == 300  # 5 minutes for time-sensitive data

    def test_determine_intelligent_ttl_historical(self, query_cache):
        """Test TTL determination for historical queries."""
        query = "SELECT * FROM history WHERE year = 2020"
        ttl = query_cache._determine_intelligent_ttl(query)
        assert ttl == 86400  # 24 hours for historical data

    def test_determine_intelligent_ttl_aggregate(self, query_cache):
        """Test TTL determination for aggregate queries."""
        query = "SELECT COUNT(*) FROM users GROUP BY country"
        ttl = query_cache._determine_intelligent_ttl(query)
        assert ttl == 7200  # 2 hours for aggregates

    def test_determine_intelligent_ttl_large_result(self, query_cache):
        """Test TTL determination for large result sets."""
        query = "SELECT * FROM large_table"
        ttl = query_cache._determine_intelligent_ttl(query, result_size=2000000)
        assert ttl <= 1800  # Max 30 minutes for large results

    def test_determine_intelligent_ttl_table_specific(self, query_cache):
        """Test TTL determination with table-specific rules."""
        query = "SELECT * FROM table"

        # User data - short TTL
        ttl1 = query_cache._determine_intelligent_ttl(query, table="users")
        assert ttl1 <= 600  # Max 10 minutes

        # Reference data - long TTL
        ttl2 = query_cache._determine_intelligent_ttl(query, table="destinations")
        assert ttl2 >= 3600  # Min 1 hour

    # Compression Tests

    def test_should_compress_small_data(self, query_cache):
        """Test compression decision for small data."""
        small_data = {"id": 1, "name": "test"}
        assert not query_cache._should_compress(small_data)

    def test_should_compress_large_data(self, query_cache):
        """Test compression decision for large data."""
        large_data = {"data": "x" * 20000}  # 20KB of data
        assert query_cache._should_compress(large_data)

    def test_compress_decompress_data(self, query_cache):
        """Test data compression and decompression."""
        original_data = {
            "users": [{"id": i, "name": f"User {i}"} for i in range(100)],
            "metadata": {"count": 100, "generated_at": "2024-01-01T00:00:00Z"},
        }

        # Compress
        compressed = query_cache._compress_data(original_data)
        assert isinstance(compressed, bytes)
        assert len(compressed) < len(json.dumps(original_data))

        # Decompress
        decompressed = query_cache._decompress_data(compressed)
        assert decompressed == original_data

    def test_compress_decompress_invalid_data(self, query_cache):
        """Test compression with invalid data."""
        # Non-serializable data
        assert not query_cache._should_compress(object())

    # L1 Cache Management Tests

    def test_evict_l1_lru_under_limit(self, query_cache):
        """Test L1 LRU eviction when under limit."""
        # Add some items
        query_cache._l1_cache["key1"] = {"data": "value1"}
        query_cache._l1_access_times["key1"] = time.time()

        # Should not evict when under limit
        initial_size = len(query_cache._l1_cache)
        query_cache._evict_l1_lru()
        assert len(query_cache._l1_cache) == initial_size

    def test_evict_l1_lru_over_limit(self, query_cache):
        """Test L1 LRU eviction when over limit."""
        # Set small limit for testing
        query_cache._l1_max_size = 2

        # Add items with different access times
        current_time = time.time()
        query_cache._l1_cache["key1"] = {"data": "value1"}
        query_cache._l1_access_times["key1"] = current_time - 100

        query_cache._l1_cache["key2"] = {"data": "value2"}
        query_cache._l1_access_times["key2"] = current_time - 50

        query_cache._l1_cache["key3"] = {"data": "value3"}  # This exceeds limit
        query_cache._l1_access_times["key3"] = current_time

        # Should evict LRU item (key1)
        query_cache._evict_l1_lru()
        assert "key1" not in query_cache._l1_cache
        assert "key1" not in query_cache._l1_access_times
        assert "key2" in query_cache._l1_cache
        assert "key3" in query_cache._l1_cache

    # Access Pattern Learning Tests

    def test_update_access_pattern_new_key(self, query_cache):
        """Test access pattern tracking for new key."""
        cache_key = "test:key"

        # First access (miss)
        query_cache._update_access_pattern(cache_key, hit=False)

        pattern = query_cache._access_patterns[cache_key]
        assert pattern["hits"] == 0
        assert pattern["misses"] == 1
        assert pattern["last_access"] > 0

    def test_update_access_pattern_existing_key(self, query_cache):
        """Test access pattern tracking for existing key."""
        cache_key = "test:key"

        # Initialize pattern
        query_cache._access_patterns[cache_key] = {
            "hits": 5,
            "misses": 2,
            "last_access": time.time() - 1000,
            "access_frequency": 0.0,
        }

        # Update with hit
        query_cache._update_access_pattern(cache_key, hit=True)

        pattern = query_cache._access_patterns[cache_key]
        assert pattern["hits"] == 6
        assert pattern["misses"] == 2

    def test_update_access_pattern_frequency_calculation(self, query_cache):
        """Test access frequency calculation."""
        cache_key = "test:key"

        # Set up initial access
        old_time = time.time() - 3600  # 1 hour ago
        query_cache._access_patterns[cache_key] = {
            "hits": 0,
            "misses": 0,
            "last_access": old_time,
            "access_frequency": 0.0,
        }

        # Update access
        query_cache._update_access_pattern(cache_key, hit=True)

        pattern = query_cache._access_patterns[cache_key]
        # Frequency should be approximately 1 access per hour
        assert pattern["access_frequency"] > 0

    # Query Result Caching Tests

    @pytest.mark.asyncio
    async def test_get_query_result_l1_hit(self, query_cache, mock_cache_service):
        """Test query result retrieval from L1 cache."""
        # Set up L1 cache hit
        cache_key = "test_cache:query:abc123"
        test_data = {"id": 1, "name": "test"}

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            query_cache._l1_cache[cache_key] = {
                "data": test_data,
                "compressed": False,
                "expires_at": time.time() + 1000,
            }

            result = await query_cache.get_query_result("SELECT * FROM test")

            assert result == test_data
            # Should not call L2 cache
            mock_cache_service.get_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_query_result_l1_expired(self, query_cache, mock_cache_service):
        """Test query result retrieval with expired L1 cache."""
        cache_key = "test_cache:query:abc123"
        test_data = {"id": 1, "name": "test"}

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            # Set up expired L1 cache entry
            query_cache._l1_cache[cache_key] = {
                "data": test_data,
                "compressed": False,
                "expires_at": time.time() - 100,  # Expired
            }

            result = await query_cache.get_query_result("SELECT * FROM test")

            assert result is None
            # Expired entry should be removed
            assert cache_key not in query_cache._l1_cache
            # Should try L2 cache
            mock_cache_service.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_query_result_l2_hit(self, query_cache, mock_cache_service):
        """Test query result retrieval from L2 cache."""
        cache_key = "test_cache:query:abc123"
        test_data = {"id": 1, "name": "test"}

        # Set up L2 cache hit
        mock_cache_service.get_json.return_value = {
            "data": test_data,
            "compressed": False,
            "cached_at": time.time(),
            "query_hash": "abc123",
            "table": "test",
        }

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            result = await query_cache.get_query_result("SELECT * FROM test")

            assert result == test_data
            # Should restore to L1 cache
            assert cache_key in query_cache._l1_cache

    @pytest.mark.asyncio
    async def test_get_query_result_compressed_data(
        self, query_cache, mock_cache_service
    ):
        """Test query result retrieval with compressed data."""
        cache_key = "test_cache:query:abc123"
        test_data = {"large_data": "x" * 1000}

        # Compress the data
        compressed_data = query_cache._compress_data(test_data)

        # Set up L2 cache hit with compressed data
        mock_cache_service.get_json.return_value = {
            "data": compressed_data,
            "compressed": True,
            "cached_at": time.time(),
            "query_hash": "abc123",
            "table": "test",
        }

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            result = await query_cache.get_query_result("SELECT * FROM test")

            assert result == test_data

    @pytest.mark.asyncio
    async def test_get_query_result_miss(self, query_cache, mock_cache_service):
        """Test query result cache miss."""
        cache_key = "test_cache:query:abc123"

        # No cache hit
        mock_cache_service.get_json.return_value = None

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            result = await query_cache.get_query_result("SELECT * FROM test")

            assert result is None

    # Query Result Storage Tests

    @pytest.mark.asyncio
    async def test_cache_query_result_success(self, query_cache, mock_cache_service):
        """Test successful query result caching."""
        cache_key = "test_cache:query:abc123"
        test_data = {"id": 1, "name": "test"}

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            success = await query_cache.cache_query_result(
                "SELECT * FROM test", test_data, table="test"
            )

            assert success
            # Should store in L1 cache
            assert cache_key in query_cache._l1_cache
            # Should store in L2 cache
            mock_cache_service.set_json.assert_called()

    @pytest.mark.asyncio
    async def test_cache_query_result_with_compression(
        self, query_cache, mock_cache_service
    ):
        """Test query result caching with compression."""
        cache_key = "test_cache:query:abc123"
        large_data = {"data": "x" * 20000}  # Large data that should be compressed

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            success = await query_cache.cache_query_result(
                "SELECT * FROM test", large_data, table="test"
            )

            assert success
            # Check that compression was used
            l1_item = query_cache._l1_cache[cache_key]
            assert l1_item["compressed"] is True

    @pytest.mark.asyncio
    async def test_cache_query_result_none_data(self, query_cache, mock_cache_service):
        """Test caching None result."""
        success = await query_cache.cache_query_result(
            "SELECT * FROM test", None, table="test"
        )

        assert not success
        mock_cache_service.set_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_query_result_with_custom_ttl(
        self, query_cache, mock_cache_service
    ):
        """Test query result caching with custom TTL."""
        cache_key = "test_cache:query:abc123"
        test_data = {"id": 1, "name": "test"}
        custom_ttl = 1200

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            success = await query_cache.cache_query_result(
                "SELECT * FROM test", test_data, table="test", ttl=custom_ttl
            )

            assert success
            # Verify custom TTL was used - check the first call (cache data)
            first_call = mock_cache_service.set_json.call_args_list[0]
            assert first_call[1]["ttl"] == custom_ttl

    # Cache Invalidation Tests

    @pytest.mark.asyncio
    async def test_invalidate_table_cache_success(
        self, query_cache, mock_cache_service
    ):
        """Test successful table cache invalidation."""
        table = "users"
        dependent_keys = ["cache:key1", "cache:key2", "cache:key3"]

        # Set up dependency mapping
        mock_cache_service.get_json.return_value = dependent_keys
        mock_cache_service.delete.return_value = len(dependent_keys)

        # Set up L1 cache entries
        for key in dependent_keys:
            query_cache._l1_cache[key] = {"data": "test"}
            query_cache._l1_access_times[key] = time.time()

        invalidated = await query_cache.invalidate_table_cache(table)

        assert invalidated == len(dependent_keys)
        # L1 cache should be cleared
        for key in dependent_keys:
            assert key not in query_cache._l1_cache
            assert key not in query_cache._l1_access_times

    @pytest.mark.asyncio
    async def test_invalidate_table_cache_no_dependencies(
        self, query_cache, mock_cache_service
    ):
        """Test table cache invalidation with no dependencies."""
        table = "users"

        # No dependencies
        mock_cache_service.get_json.return_value = []

        invalidated = await query_cache.invalidate_table_cache(table)

        assert invalidated == 0
        mock_cache_service.delete.assert_not_called()

    # Vector Search Caching Tests

    @pytest.mark.asyncio
    async def test_cache_vector_search_result(self, query_cache, mock_cache_service):
        """Test vector search result caching."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = [{"id": 1, "similarity": 0.95}]

        success = await query_cache.cache_vector_search_result(
            query_vector, result, similarity_threshold=0.8, limit=5
        )

        assert success
        mock_cache_service.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vector_search_result_hit(self, query_cache, mock_cache_service):
        """Test vector search result cache hit."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected_result = [{"id": 1, "similarity": 0.95}]

        # Set up cache hit
        mock_cache_service.get_json.return_value = {
            "results": expected_result,
            "query_vector_hash": "abc123",
            "similarity_threshold": 0.8,
            "limit": 5,
            "cached_at": time.time(),
        }

        result = await query_cache.get_vector_search_result(
            query_vector, similarity_threshold=0.8, limit=5
        )

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_vector_search_result_miss(self, query_cache, mock_cache_service):
        """Test vector search result cache miss."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        # No cache hit
        mock_cache_service.get_json.return_value = None

        result = await query_cache.get_vector_search_result(
            query_vector, similarity_threshold=0.8, limit=5
        )

        assert result is None

    # Cache Warming Tests

    @pytest.mark.asyncio
    async def test_warm_cache(self, query_cache, mock_cache_service):
        """Test cache warming functionality."""
        queries = [
            ("SELECT * FROM users", {"active": True}, "users"),
            ("SELECT * FROM trips", None, "trips"),
        ]

        # Mock execute function
        async def mock_execute(query, params):
            if "users" in query:
                return [{"id": 1, "name": "User 1"}]
            elif "trips" in query:
                return [{"id": 1, "destination": "Paris"}]
            return None

        # No existing cache
        mock_cache_service.get_json.return_value = None

        with patch.object(query_cache, "get_query_result", return_value=None):
            warmed = await query_cache.warm_cache(queries, mock_execute)

            assert warmed == 2
            # Should have cached both queries + dependency tracking (4 total calls)
            assert mock_cache_service.set_json.call_count == 4

    @pytest.mark.asyncio
    async def test_warm_cache_already_cached(self, query_cache, mock_cache_service):
        """Test cache warming with already cached queries."""
        queries = [
            ("SELECT * FROM users", {"active": True}, "users"),
        ]

        async def mock_execute(query, params):
            return [{"id": 1, "name": "User 1"}]

        # Already cached
        with patch.object(
            query_cache, "get_query_result", return_value=[{"cached": True}]
        ):
            warmed = await query_cache.warm_cache(queries, mock_execute)

            assert warmed == 0  # Nothing warmed because already cached

    # Cache Statistics Tests

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, query_cache):
        """Test cache statistics retrieval."""
        # Set up some access patterns and L1 cache
        query_cache._access_patterns = {
            "key1": {
                "hits": 10,
                "misses": 2,
                "last_access": time.time(),
                "access_frequency": 5.0,
            },
            "key2": {
                "hits": 5,
                "misses": 5,
                "last_access": time.time(),
                "access_frequency": 2.0,
            },
        }

        query_cache._l1_cache = {
            "key1": {"data": {"small": "data"}},
            "key2": {"data": {"another": "entry"}},
        }

        stats = await query_cache.get_cache_stats()

        assert stats["l1_cache_size"] == 2
        assert stats["total_hits"] == 15
        assert stats["total_misses"] == 7
        assert stats["hit_ratio"] == round(15 / 22, 3)
        assert len(stats["frequent_queries"]) <= 5

    # Cache Optimization Tests

    @pytest.mark.asyncio
    async def test_optimize_cache(self, query_cache):
        """Test cache optimization functionality."""
        current_time = time.time()

        # Set up old access patterns
        query_cache._access_patterns = {
            "old_key": {"last_access": current_time - 90000},  # > 24 hours
            "recent_key": {"last_access": current_time - 1000},  # Recent
        }

        # Set up old L1 cache entries
        query_cache._l1_cache = {
            "old_l1_key": {"data": "test"},
        }
        query_cache._l1_access_times = {
            "old_l1_key": current_time - 2000,  # > 30 minutes
        }

        optimizations = await query_cache.optimize_cache()

        assert optimizations["pattern_cleanups"] == 1
        assert optimizations["l1_evictions"] == 1
        assert "old_key" not in query_cache._access_patterns
        assert "old_l1_key" not in query_cache._l1_cache

    @pytest.mark.asyncio
    async def test_optimize_cache_recommendations(self, query_cache):
        """Test cache optimization recommendations."""
        # Set up high L1 cache usage
        query_cache._l1_max_size = 10
        for i in range(9):  # 90% of capacity
            query_cache._l1_cache[f"key{i}"] = {"data": "test"}

        # Set up low hit ratio patterns
        query_cache._access_patterns = {
            "low_hit_key": {"hits": 2, "misses": 10, "last_access": time.time()},
        }

        optimizations = await query_cache.optimize_cache()

        recommendations = optimizations["recommendations"]
        assert any("increasing L1 cache size" in rec for rec in recommendations)
        assert any("low-hit-ratio queries" in rec for rec in recommendations)

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_get_query_result_l2_error(self, query_cache, mock_cache_service):
        """Test error handling in L2 cache retrieval."""
        cache_key = "test_cache:query:abc123"

        # L2 cache error
        mock_cache_service.get_json.side_effect = Exception("L2 cache error")

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            result = await query_cache.get_query_result("SELECT * FROM test")

            # Should handle error gracefully and return None
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_query_result_l2_error(self, query_cache, mock_cache_service):
        """Test error handling in L2 cache storage."""
        cache_key = "test_cache:query:abc123"
        test_data = {"id": 1, "name": "test"}

        # L2 cache storage error
        mock_cache_service.set_json.side_effect = Exception("L2 cache error")

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            success = await query_cache.cache_query_result(
                "SELECT * FROM test", test_data, table="test"
            )

            # Should handle error gracefully and return False
            assert not success

    @pytest.mark.asyncio
    async def test_invalidate_table_cache_error(self, query_cache, mock_cache_service):
        """Test error handling in table cache invalidation."""
        table = "users"

        # Error in getting dependencies
        mock_cache_service.get_json.side_effect = Exception("Cache error")

        invalidated = await query_cache.invalidate_table_cache(table)

        # Should handle error gracefully and return 0
        assert invalidated == 0

    # Edge Cases

    @pytest.mark.asyncio
    async def test_cache_empty_result(self, query_cache, mock_cache_service):
        """Test caching empty query results."""
        cache_key = "test_cache:query:abc123"
        empty_result = []

        with patch.object(
            query_cache, "_generate_query_fingerprint", return_value=cache_key
        ):
            success = await query_cache.cache_query_result(
                "SELECT * FROM empty_table", empty_result, table="test"
            )

            assert success
            # Empty results should still be cached + dependency tracking
            assert mock_cache_service.set_json.call_count == 2

    @pytest.mark.asyncio
    async def test_vector_search_empty_vector(self, query_cache, mock_cache_service):
        """Test vector search caching with empty vector."""
        empty_vector = []
        result = [{"id": 1}]

        success = await query_cache.cache_vector_search_result(empty_vector, result)

        assert success
        mock_cache_service.set_json.assert_called_once()

    def test_compression_with_unicode_data(self, query_cache):
        """Test compression with unicode and special characters."""
        unicode_data = {
            "message": "Hello 世界! 🌍",
            "emoji": "🎉🎊🎈",
            "accents": "café, naïve, résumé",
            "symbols": "αβγδε mathematical symbols",
        }

        # Should handle unicode properly
        compressed = query_cache._compress_data(unicode_data)
        decompressed = query_cache._decompress_data(compressed)

        assert decompressed == unicode_data

    def test_fingerprint_with_special_characters(self, query_cache):
        """Test fingerprinting with special characters in queries."""
        query_with_special = (
            "SELECT * FROM table WHERE name LIKE '%special chars: αβγ 🌍%'"
        )

        # Should handle special characters without errors
        fingerprint = query_cache._generate_query_fingerprint(query_with_special)
        assert fingerprint.startswith("test_cache:query:")
        assert len(fingerprint.split(":")[-1]) == 16
