"""
Comprehensive tests for DatabaseCacheMixin.

This module provides comprehensive test coverage for the database cache integration
mixin, including read-through caching, write-through with invalidation, bulk operations,
vector search caching, and cache management features.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.infrastructure.cache_service import QueryResultCache
from tripsage_core.services.infrastructure.database_cache_mixin import (
    DatabaseCacheMixin,
)


class MockDatabaseService(DatabaseCacheMixin):
    """Mock database service for testing the mixin."""

    def __init__(self):
        super().__init__()
        self.select_called = []
        self.insert_called = []
        self.update_called = []
        self.delete_called = []
        self.upsert_called = []
        self.vector_search_called = []

    async def select(
        self, table, columns="*", filters=None, order_by=None, limit=None, offset=None
    ):
        self.select_called.append(
            {
                "table": table,
                "columns": columns,
                "filters": filters,
                "order_by": order_by,
                "limit": limit,
                "offset": offset,
            }
        )
        # Return mock data based on table
        if table == "users":
            return [{"id": 1, "name": "User 1"}, {"id": 2, "name": "User 2"}]
        elif table == "trips":
            return [{"id": 1, "destination": "Paris"}]
        return []

    async def insert(self, table, data):
        self.insert_called.append({"table": table, "data": data})
        return (
            [{"id": 1, **data}]
            if isinstance(data, dict)
            else [{"id": i, **item} for i, item in enumerate(data, 1)]
        )

    async def update(self, table, data, filters):
        self.update_called.append({"table": table, "data": data, "filters": filters})
        return [{"id": 1, **data}]

    async def delete(self, table, filters):
        self.delete_called.append({"table": table, "filters": filters})
        return [{"id": 1, "deleted": True}]

    async def upsert(self, table, data, on_conflict=None):
        self.upsert_called.append(
            {"table": table, "data": data, "on_conflict": on_conflict}
        )
        return (
            [{"id": 1, **data}]
            if isinstance(data, dict)
            else [{"id": i, **item} for i, item in enumerate(data, 1)]
        )

    async def vector_search(
        self,
        table,
        vector_column,
        query_vector,
        limit=10,
        similarity_threshold=None,
        filters=None,
    ):
        self.vector_search_called.append(
            {
                "table": table,
                "vector_column": vector_column,
                "query_vector": query_vector,
                "limit": limit,
                "similarity_threshold": similarity_threshold,
                "filters": filters,
            }
        )
        return [{"id": 1, "similarity": 0.95}, {"id": 2, "similarity": 0.85}]


class TestDatabaseCacheMixin:
    """Comprehensive test suite for DatabaseCacheMixin."""

    @pytest.fixture
    def mock_query_cache(self):
        """Create a mock query result cache."""
        cache = AsyncMock(spec=QueryResultCache)
        cache.get_query_result = AsyncMock(return_value=None)
        cache.cache_query_result = AsyncMock(return_value=True)
        cache.invalidate_table_cache = AsyncMock(return_value=3)
        cache.get_vector_search_result = AsyncMock(return_value=None)
        cache.cache_vector_search_result = AsyncMock(return_value=True)
        cache.get_cache_stats = AsyncMock(
            return_value={
                "l1_cache_size": 10,
                "hit_ratio": 0.75,
                "total_hits": 30,
                "total_misses": 10,
            }
        )
        cache.optimize_cache = AsyncMock(
            return_value={
                "l1_evictions": 5,
                "pattern_cleanups": 2,
                "recommendations": ["Test recommendation"],
            }
        )
        return cache

    @pytest.fixture
    def db_service(self, mock_query_cache):
        """Create a mock database service with cache mixin."""
        service = MockDatabaseService()
        service._query_cache = mock_query_cache
        return service

    # Table Name Extraction Tests

    def test_extract_table_from_operation_direct(self, db_service):
        """Test table name extraction with direct table name."""
        table = db_service._extract_table_from_operation("users", "some operation")
        assert table == "users"

    def test_extract_table_from_operation_select(self, db_service):
        """Test table name extraction from SELECT statement."""
        operation = "SELECT * FROM users WHERE active = true"
        table = db_service._extract_table_from_operation(None, operation)
        assert table == "users"

    def test_extract_table_from_operation_insert(self, db_service):
        """Test table name extraction from INSERT statement."""
        operation = "INSERT INTO trips (destination) VALUES ('Paris')"
        table = db_service._extract_table_from_operation(None, operation)
        assert table == "trips"

    def test_extract_table_from_operation_update(self, db_service):
        """Test table name extraction from UPDATE statement."""
        operation = "UPDATE users SET active = false WHERE id = 1"
        table = db_service._extract_table_from_operation(None, operation)
        assert table == "users"

    def test_extract_table_from_operation_delete(self, db_service):
        """Test table name extraction from DELETE statement."""
        operation = "DELETE FROM sessions WHERE expired = true"
        table = db_service._extract_table_from_operation(None, operation)
        assert table == "sessions"

    def test_extract_table_from_operation_no_match(self, db_service):
        """Test table name extraction with no matching pattern."""
        operation = "SOME UNKNOWN OPERATION"
        table = db_service._extract_table_from_operation(None, operation)
        assert table is None

    # Read-Through Caching Tests

    @pytest.mark.asyncio
    async def test_select_with_cache_hit(self, db_service, mock_query_cache):
        """Test select with cache hit."""
        cached_data = [{"id": 1, "name": "Cached User"}]
        mock_query_cache.get_query_result.return_value = cached_data

        result = await db_service.select_with_cache("users")

        assert result == cached_data
        # Original select should not be called
        assert len(db_service.select_called) == 0
        mock_query_cache.get_query_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_with_cache_miss(self, db_service, mock_query_cache):
        """Test select with cache miss."""
        mock_query_cache.get_query_result.return_value = None

        result = await db_service.select_with_cache("users")

        # Should get data from database
        assert len(result) == 2
        assert result[0]["name"] == "User 1"
        # Original select should be called
        assert len(db_service.select_called) == 1
        # Result should be cached
        mock_query_cache.cache_query_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_with_cache_skip_cache(self, db_service, mock_query_cache):
        """Test select with cache skip."""
        result = await db_service.select_with_cache("users", skip_cache=True)

        # Should get data directly from database
        assert len(result) == 2
        # Cache should not be checked
        mock_query_cache.get_query_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_select_with_cache_disabled(self, db_service, mock_query_cache):
        """Test select with cache disabled."""
        db_service._cache_enabled = False

        result = await db_service.select_with_cache("users")

        # Should go directly to database
        assert len(result) == 2
        mock_query_cache.get_query_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_select_with_cache_custom_ttl(self, db_service, mock_query_cache):
        """Test select with custom cache TTL."""
        mock_query_cache.get_query_result.return_value = None
        custom_ttl = 1800

        await db_service.select_with_cache("users", cache_ttl=custom_ttl)

        # Verify custom TTL was passed to cache
        call_args = mock_query_cache.cache_query_result.call_args
        assert call_args[1]["ttl"] == custom_ttl

    @pytest.mark.asyncio
    async def test_select_with_cache_complex_query(self, db_service, mock_query_cache):
        """Test select with complex query parameters."""
        mock_query_cache.get_query_result.return_value = None

        await db_service.select_with_cache(
            "users",
            columns="id,name,email",
            filters={"active": True, "age": {"gte": 18}},
            order_by="-created_at",
            limit=50,
            offset=10,
        )

        # Verify query parameters were passed correctly
        select_call = db_service.select_called[0]
        assert select_call["columns"] == "id,name,email"
        assert select_call["filters"] == {"active": True, "age": {"gte": 18}}
        assert select_call["order_by"] == "-created_at"
        assert select_call["limit"] == 50
        assert select_call["offset"] == 10

    # Write-Through with Invalidation Tests

    @pytest.mark.asyncio
    async def test_insert_with_cache_invalidation(self, db_service, mock_query_cache):
        """Test insert with automatic cache invalidation."""
        test_data = {"name": "New User", "email": "user@example.com"}

        result = await db_service.insert_with_cache_invalidation("users", test_data)

        assert len(result) == 1
        assert result[0]["name"] == "New User"
        # Cache should be invalidated
        mock_query_cache.invalidate_table_cache.assert_called_once_with("users")

    @pytest.mark.asyncio
    async def test_insert_with_cache_invalidation_disabled(
        self, db_service, mock_query_cache
    ):
        """Test insert with cache invalidation disabled."""
        db_service._invalidation_enabled = False
        test_data = {"name": "New User"}

        await db_service.insert_with_cache_invalidation("users", test_data)

        # Cache should not be invalidated
        mock_query_cache.invalidate_table_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_with_cache_invalidation(self, db_service, mock_query_cache):
        """Test update with automatic cache invalidation."""
        test_data = {"name": "Updated User"}
        filters = {"id": 1}

        result = await db_service.update_with_cache_invalidation(
            "users", test_data, filters
        )

        assert len(result) == 1
        assert result[0]["name"] == "Updated User"
        mock_query_cache.invalidate_table_cache.assert_called_once_with("users")

    @pytest.mark.asyncio
    async def test_upsert_with_cache_invalidation(self, db_service, mock_query_cache):
        """Test upsert with automatic cache invalidation."""
        test_data = {"id": 1, "name": "Upserted User"}

        result = await db_service.upsert_with_cache_invalidation(
            "users", test_data, on_conflict="id"
        )

        assert len(result) == 1
        mock_query_cache.invalidate_table_cache.assert_called_once_with("users")

    @pytest.mark.asyncio
    async def test_delete_with_cache_invalidation(self, db_service, mock_query_cache):
        """Test delete with automatic cache invalidation."""
        filters = {"id": 1}

        result = await db_service.delete_with_cache_invalidation("users", filters)

        assert len(result) == 1
        mock_query_cache.invalidate_table_cache.assert_called_once_with("users")

    @pytest.mark.asyncio
    async def test_invalidation_no_result(self, db_service, mock_query_cache):
        """Test that invalidation doesn't occur when no records are affected."""
        # Mock empty result
        db_service.insert_called = []

        async def mock_insert(table, data):
            return []  # No records inserted

        db_service.insert = mock_insert

        await db_service.insert_with_cache_invalidation("users", {"name": "Test"})

        # Cache should not be invalidated for empty results
        mock_query_cache.invalidate_table_cache.assert_not_called()

    # Vector Search Caching Tests

    @pytest.mark.asyncio
    async def test_vector_search_with_cache_hit(self, db_service, mock_query_cache):
        """Test vector search with cache hit."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        cached_result = [{"id": 1, "similarity": 0.95}]
        mock_query_cache.get_vector_search_result.return_value = cached_result

        result = await db_service.vector_search_with_cache(
            "destinations", "embedding", query_vector, limit=5, similarity_threshold=0.8
        )

        assert result == cached_result
        # Original vector search should not be called
        assert len(db_service.vector_search_called) == 0

    @pytest.mark.asyncio
    async def test_vector_search_with_cache_miss(self, db_service, mock_query_cache):
        """Test vector search with cache miss."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_query_cache.get_vector_search_result.return_value = None

        result = await db_service.vector_search_with_cache(
            "destinations", "embedding", query_vector, limit=5, similarity_threshold=0.8
        )

        # Should get data from database
        assert len(result) == 2
        # Original vector search should be called
        assert len(db_service.vector_search_called) == 1
        # Result should be cached
        mock_query_cache.cache_vector_search_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_with_cache_skip(self, db_service, mock_query_cache):
        """Test vector search with cache skip."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        result = await db_service.vector_search_with_cache(
            "destinations", "embedding", query_vector, skip_cache=True
        )

        # Should go directly to database
        assert len(result) == 2
        mock_query_cache.get_vector_search_result.assert_not_called()

    # Bulk Operations Tests

    @pytest.mark.asyncio
    async def test_bulk_insert_with_cache_invalidation(
        self, db_service, mock_query_cache
    ):
        """Test bulk insert operations with cache invalidation."""
        operations = [
            {"table": "users", "data": {"name": "User 1"}},
            {"table": "users", "data": {"name": "User 2"}},
            {"table": "trips", "data": {"destination": "Paris"}},
        ]

        results = await db_service.bulk_insert_with_cache_invalidation(operations)

        assert "users" in results
        assert "trips" in results
        # Should invalidate cache for both tables
        assert mock_query_cache.invalidate_table_cache.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_insert_same_table(self, db_service, mock_query_cache):
        """Test bulk insert with multiple operations on same table."""
        operations = [
            {"table": "users", "data": {"name": "User 1"}},
            {"table": "users", "data": {"name": "User 2"}},
        ]

        await db_service.bulk_insert_with_cache_invalidation(operations)

        # Should group operations by table
        assert len(db_service.insert_called) == 1
        insert_call = db_service.insert_called[0]
        assert len(insert_call["data"]) == 2  # Both records in one call

    # Cache Warming Tests

    @pytest.mark.asyncio
    async def test_warm_frequently_accessed_cache_default(
        self, db_service, mock_query_cache
    ):
        """Test cache warming with default queries."""
        mock_query_cache.get_query_result.return_value = None  # Cache miss

        results = await db_service.warm_frequently_accessed_cache()

        # Should warm cache for multiple tables
        assert len(results) > 0
        assert "users" in results
        assert "trips" in results
        assert "destinations" in results

    @pytest.mark.asyncio
    async def test_warm_frequently_accessed_cache_custom(
        self, db_service, mock_query_cache
    ):
        """Test cache warming with custom queries."""
        mock_query_cache.get_query_result.return_value = None

        custom_queries = {
            "users": [{"columns": "id,name", "limit": 10}],
            "trips": [{"columns": "*", "filters": {"active": True}}],
        }

        results = await db_service.warm_frequently_accessed_cache(custom_queries)

        assert results["users"] == 1
        assert results["trips"] == 1

    @pytest.mark.asyncio
    async def test_warm_cache_already_cached(self, db_service, mock_query_cache):
        """Test cache warming when data is already cached."""
        mock_query_cache.get_query_result.return_value = [{"cached": True}]

        results = await db_service.warm_frequently_accessed_cache(
            {"users": [{"columns": "*", "limit": 10}]}
        )

        # Should not warm already cached data
        assert results["users"] == 0

    @pytest.mark.asyncio
    async def test_warm_cache_disabled(self, db_service, mock_query_cache):
        """Test cache warming when cache is disabled."""
        db_service._cache_enabled = False

        results = await db_service.warm_frequently_accessed_cache()

        assert results == {}

    # Cache Statistics and Monitoring Tests

    @pytest.mark.asyncio
    async def test_get_cache_statistics_enabled(self, db_service, mock_query_cache):
        """Test cache statistics retrieval when cache is enabled."""
        stats = await db_service.get_cache_statistics()

        assert stats["cache_enabled"] is True
        assert stats["invalidation_enabled"] is True
        assert "hit_ratio" in stats
        assert "l1_cache_size" in stats
        assert stats["service_type"] == "database_cache_mixin"

    @pytest.mark.asyncio
    async def test_get_cache_statistics_disabled(self, db_service, mock_query_cache):
        """Test cache statistics when cache is disabled."""
        db_service._cache_enabled = False

        stats = await db_service.get_cache_statistics()

        assert stats["cache_enabled"] is False

    @pytest.mark.asyncio
    async def test_optimize_database_cache_enabled(self, db_service, mock_query_cache):
        """Test database cache optimization."""
        mock_query_cache.get_cache_stats.return_value = {
            "hit_ratio": 0.3,  # Low hit ratio
            "l1_memory_mb": 150.0,  # High memory usage
        }

        optimization = await db_service.optimize_database_cache()

        recommendations = optimization["recommendations"]
        assert any("hit ratio" in rec for rec in recommendations)
        assert any("memory usage" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_optimize_database_cache_disabled(self, db_service, mock_query_cache):
        """Test database cache optimization when disabled."""
        db_service._cache_enabled = False

        optimization = await db_service.optimize_database_cache()

        assert optimization["cache_enabled"] is False

    # Cache Control Tests

    def test_enable_disable_cache(self, db_service):
        """Test enabling and disabling cache."""
        # Test disable
        db_service.disable_cache()
        assert not db_service._cache_enabled

        # Test enable
        db_service.enable_cache()
        assert db_service._cache_enabled

    def test_enable_disable_invalidation(self, db_service):
        """Test enabling and disabling cache invalidation."""
        # Test disable
        db_service.disable_invalidation()
        assert not db_service._invalidation_enabled

        # Test enable
        db_service.enable_invalidation()
        assert db_service._invalidation_enabled

    @pytest.mark.asyncio
    async def test_manual_cache_invalidation(self, db_service, mock_query_cache):
        """Test manual cache invalidation."""
        tables = ["users", "trips", "destinations"]
        mock_query_cache.invalidate_table_cache.return_value = 5

        results = await db_service.manual_cache_invalidation(tables)

        assert len(results) == 3
        assert all(count == 5 for count in results.values())
        assert mock_query_cache.invalidate_table_cache.call_count == 3

    @pytest.mark.asyncio
    async def test_manual_cache_invalidation_disabled(
        self, db_service, mock_query_cache
    ):
        """Test manual cache invalidation when cache is disabled."""
        db_service._cache_enabled = False

        results = await db_service.manual_cache_invalidation(["users"])

        assert results == {}
        mock_query_cache.invalidate_table_cache.assert_not_called()

    # Integration Tests

    @pytest.mark.asyncio
    async def test_full_workflow_cache_hit(self, db_service, mock_query_cache):
        """Test full workflow with cache hit scenario."""
        # First query - cache miss
        mock_query_cache.get_query_result.return_value = None
        result1 = await db_service.select_with_cache("users")
        assert len(result1) == 2

        # Second query - cache hit
        mock_query_cache.get_query_result.return_value = result1
        result2 = await db_service.select_with_cache("users")
        assert result2 == result1

        # Insert - should invalidate cache
        await db_service.insert_with_cache_invalidation("users", {"name": "New User"})
        mock_query_cache.invalidate_table_cache.assert_called_with("users")

    @pytest.mark.asyncio
    async def test_full_workflow_vector_search(self, db_service, mock_query_cache):
        """Test full workflow with vector search caching."""
        query_vector = [0.1, 0.2, 0.3]

        # First search - cache miss
        mock_query_cache.get_vector_search_result.return_value = None
        result1 = await db_service.vector_search_with_cache(
            "destinations", "embedding", query_vector
        )
        assert len(result1) == 2

        # Second search - cache hit
        mock_query_cache.get_vector_search_result.return_value = result1
        result2 = await db_service.vector_search_with_cache(
            "destinations", "embedding", query_vector
        )
        assert result2 == result1

    @pytest.mark.asyncio
    async def test_error_handling_cache_errors(self, db_service, mock_query_cache):
        """Test error handling when cache operations fail."""
        # Mock cache errors
        mock_query_cache.get_query_result.side_effect = Exception("Cache error")
        mock_query_cache.invalidate_table_cache.side_effect = Exception(
            "Invalidation error"
        )

        # Should still work with database fallback
        result = await db_service.select_with_cache("users")
        assert len(result) == 2

        # Invalidation errors should be handled gracefully
        await db_service.insert_with_cache_invalidation("users", {"name": "Test"})
        # Should not raise exception

    # Performance and Concurrency Tests

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, db_service, mock_query_cache):
        """Test concurrent cache operations."""
        mock_query_cache.get_query_result.return_value = None

        # Execute multiple queries concurrently
        tasks = [
            db_service.select_with_cache("users"),
            db_service.select_with_cache("trips"),
            db_service.select_with_cache("destinations"),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(isinstance(result, list) for result in results)

    @pytest.mark.asyncio
    async def test_concurrent_invalidation(self, db_service, mock_query_cache):
        """Test concurrent cache invalidation operations."""
        # Execute multiple invalidations concurrently
        tasks = [
            db_service.insert_with_cache_invalidation("users", {"name": f"User {i}"})
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        # Should have multiple invalidation calls
        assert mock_query_cache.invalidate_table_cache.call_count == 5
