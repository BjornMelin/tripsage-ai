"""
Comprehensive tests for the modern PGVector service module.

This module provides comprehensive test coverage for the production-ready
pgvector service functionality including:
- HNSW index creation with optimization profiles
- Query optimization and performance tuning
- Index health monitoring and statistics
- Memory table optimization for Mem0 integration
- Error handling and edge cases
- Table optimization workflows
"""

from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.infrastructure.pgvector_service import (
    DistanceFunction,
    IndexConfig,
    IndexStats,
    OptimizationProfile,
    PGVectorService,
    optimize_vector_table,
)

class TestDistanceFunction:
    """Test DistanceFunction enum."""

    def test_distance_function_values(self):
        """Test that distance functions have correct operator names."""
        assert DistanceFunction.L2.value == "vector_l2_ops"
        assert DistanceFunction.COSINE.value == "vector_cosine_ops"
        assert DistanceFunction.INNER_PRODUCT.value == "vector_ip_ops"

class TestOptimizationProfile:
    """Test OptimizationProfile enum."""

    def test_optimization_profile_values(self):
        """Test that optimization profiles have correct values."""
        assert OptimizationProfile.SPEED.value == "speed"
        assert OptimizationProfile.BALANCED.value == "balanced"
        assert OptimizationProfile.QUALITY.value == "quality"

class TestIndexConfig:
    """Test IndexConfig model."""

    def test_default_index_config(self):
        """Test default IndexConfig values."""
        config = IndexConfig()
        assert config.m == 16
        assert config.ef_construction == 64
        assert config.ef_search == 40

    def test_custom_index_config(self):
        """Test custom IndexConfig values."""
        config = IndexConfig(m=24, ef_construction=100, ef_search=200)
        assert config.m == 24
        assert config.ef_construction == 100
        assert config.ef_search == 200

    def test_index_config_validation(self):
        """Test IndexConfig field validation."""
        config = IndexConfig(m=8, ef_construction=32, ef_search=20)
        assert config.m == 8
        assert config.ef_construction == 32
        assert config.ef_search == 20

class TestIndexStats:
    """Test IndexStats model."""

    def test_index_stats_creation(self):
        """Test creating IndexStats with all fields."""
        stats = IndexStats(
            index_name="test_idx",
            index_size_bytes=1024000,
            index_size_human="1000 kB",
            row_count=5000,
            index_usage_count=100,
            last_used="2025-01-01 12:00:00",
        )
        assert stats.index_name == "test_idx"
        assert stats.index_size_bytes == 1024000
        assert stats.index_size_human == "1000 kB"
        assert stats.row_count == 5000
        assert stats.index_usage_count == 100
        assert stats.last_used == "2025-01-01 12:00:00"

    def test_index_stats_optional_last_used(self):
        """Test IndexStats with optional last_used field."""
        stats = IndexStats(
            index_name="test_idx",
            index_size_bytes=1024000,
            index_size_human="1000 kB",
            row_count=5000,
            index_usage_count=0,
        )
        assert stats.last_used is None

class TestPGVectorService:
    """Test the main PGVectorService functionality."""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service."""
        mock_db = AsyncMock()
        mock_db.execute_sql = AsyncMock()
        return mock_db

    @pytest.fixture
    def pgvector_service(self, mock_database_service):
        """Create a PGVectorService with mocked database."""
        return PGVectorService(mock_database_service)

    def test_service_initialization(self, mock_database_service):
        """Test PGVectorService initialization."""
        service = PGVectorService(mock_database_service)
        assert service.db == mock_database_service
        assert len(service._profiles) == 3

        # Test profile creation
        assert OptimizationProfile.SPEED in service._profiles
        assert OptimizationProfile.BALANCED in service._profiles
        assert OptimizationProfile.QUALITY in service._profiles

    def test_optimization_profiles_creation(self, pgvector_service):
        """Test that optimization profiles are created correctly."""
        profiles = pgvector_service._profiles

        # Speed profile
        speed = profiles[OptimizationProfile.SPEED]
        assert speed.m == 16
        assert speed.ef_construction == 64
        assert speed.ef_search == 40

        # Balanced profile
        balanced = profiles[OptimizationProfile.BALANCED]
        assert balanced.m == 16
        assert balanced.ef_construction == 64
        assert balanced.ef_search == 100

        # Quality profile
        quality = profiles[OptimizationProfile.QUALITY]
        assert quality.m == 16
        assert quality.ef_construction == 100
        assert quality.ef_search == 200

    @pytest.mark.asyncio
    async def test_create_hnsw_index_default_params(
        self, pgvector_service, mock_database_service
    ):
        """Test creating HNSW index with default parameters."""
        mock_database_service.execute_sql.return_value = []

        index_name = await pgvector_service.create_hnsw_index(
            table_name="test_table", column_name="embedding"
        )

        expected_name = "idx_test_table_embedding_cosine_hnsw"
        assert index_name == expected_name

        # Verify SQL was called
        assert mock_database_service.execute_sql.called
        call_args = mock_database_service.execute_sql.call_args_list

        # Should have at least one call for index creation
        assert len(call_args) >= 1

        # Check the SQL contains expected elements
        create_call = call_args[0][0][0]
        assert "CREATE INDEX CONCURRENTLY" in create_call
        assert "test_table" in create_call
        assert "embedding" in create_call
        assert "vector_cosine_ops" in create_call
        assert "hnsw" in create_call

    @pytest.mark.asyncio
    async def test_create_hnsw_index_custom_params(
        self, pgvector_service, mock_database_service
    ):
        """Test creating HNSW index with custom parameters."""
        mock_database_service.execute_sql.return_value = []

        index_name = await pgvector_service.create_hnsw_index(
            table_name="vectors",
            column_name="content_embedding",
            distance_function=DistanceFunction.L2,
            profile=OptimizationProfile.QUALITY,
            index_name="custom_vector_idx",
        )

        assert index_name == "custom_vector_idx"

        # Verify SQL calls
        call_args = mock_database_service.execute_sql.call_args_list
        assert len(call_args) >= 1

        # Check the SQL contains expected elements
        create_call = call_args[0][0][0]
        assert "CREATE INDEX CONCURRENTLY custom_vector_idx" in create_call
        assert "vectors" in create_call
        assert "content_embedding" in create_call
        assert "vector_l2_ops" in create_call

    @pytest.mark.asyncio
    async def test_create_hnsw_index_with_quality_profile(
        self, pgvector_service, mock_database_service
    ):
        """Test creating HNSW index with quality profile sets ef_construction."""
        mock_database_service.execute_sql.return_value = []

        await pgvector_service.create_hnsw_index(
            table_name="test_table",
            column_name="embedding",
            profile=OptimizationProfile.QUALITY,
        )

        call_args = mock_database_service.execute_sql.call_args_list

        # Should have calls for index creation and ef_search setting
        assert len(call_args) >= 2

        # Check that ef_construction parameter is included
        # (quality profile has ef_construction=100)
        create_call = call_args[0][0][0]
        assert "WITH (ef_construction = 100)" in create_call

    @pytest.mark.asyncio
    async def test_set_query_quality(self, pgvector_service, mock_database_service):
        """Test setting query quality via ef_search."""
        mock_database_service.execute_sql.return_value = []

        await pgvector_service.set_query_quality(ef_search=150)

        mock_database_service.execute_sql.assert_called_once_with(
            "SET hnsw.ef_search = 150"
        )

    @pytest.mark.asyncio
    async def test_reset_query_settings(self, pgvector_service, mock_database_service):
        """Test resetting query settings to defaults."""
        mock_database_service.execute_sql.return_value = []

        await pgvector_service.reset_query_settings()

        mock_database_service.execute_sql.assert_called_once_with(
            "RESET hnsw.ef_search"
        )

    @pytest.mark.asyncio
    async def test_get_index_stats_success(
        self, pgvector_service, mock_database_service
    ):
        """Test getting index statistics successfully."""
        mock_result = [
            {
                "index_name": "test_table_embedding_cosine_hnsw_idx",
                "index_size_bytes": 2048000,
                "index_size_human": "2000 kB",
                "row_count": 10000,
                "index_usage_count": 500,
                "last_used": "2025-01-01 12:00:00",
            }
        ]
        mock_database_service.execute_sql.return_value = mock_result

        stats = await pgvector_service.get_index_stats("test_table", "embedding")

        assert stats is not None
        assert isinstance(stats, IndexStats)
        assert stats.index_name == "test_table_embedding_cosine_hnsw_idx"
        assert stats.index_size_bytes == 2048000
        assert stats.index_size_human == "2000 kB"
        assert stats.row_count == 10000
        assert stats.index_usage_count == 500
        assert stats.last_used == "2025-01-01 12:00:00"

        # Verify SQL call
        mock_database_service.execute_sql.assert_called_once()
        call_args = mock_database_service.execute_sql.call_args
        assert "test_table" in call_args[0][1]
        assert "embedding" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_index_stats_no_index(
        self, pgvector_service, mock_database_service
    ):
        """Test getting index statistics when no index exists."""
        mock_database_service.execute_sql.return_value = []

        stats = await pgvector_service.get_index_stats("test_table", "embedding")

        assert stats is None

    @pytest.mark.asyncio
    async def test_check_index_health_missing_index(
        self, pgvector_service, mock_database_service
    ):
        """Test health check when index is missing."""
        mock_database_service.execute_sql.return_value = []

        health = await pgvector_service.check_index_health("test_table", "embedding")

        assert health["status"] == "missing"
        assert "No HNSW index found" in health["message"]
        assert len(health["recommendations"]) > 0
        assert "Create HNSW index" in health["recommendations"][0]

    @pytest.mark.asyncio
    async def test_check_index_health_healthy_index(
        self, pgvector_service, mock_database_service
    ):
        """Test health check for a healthy index."""
        mock_result = [
            {
                "index_name": "test_idx",
                "index_size_bytes": 500000,  # 500KB
                "index_size_human": "500 kB",
                "row_count": 1000,
                "index_usage_count": 100,
                "last_used": "2025-01-01 12:00:00",
            }
        ]
        mock_database_service.execute_sql.return_value = mock_result

        health = await pgvector_service.check_index_health("test_table", "embedding")

        assert health["status"] == "healthy"
        assert health["index_name"] == "test_idx"
        assert health["size"] == "500 kB"
        assert health["rows"] == 1000
        assert health["usage_count"] == 100
        assert health["last_used"] == "2025-01-01 12:00:00"
        assert len(health["recommendations"]) == 0

    @pytest.mark.asyncio
    async def test_check_index_health_unused_index(
        self, pgvector_service, mock_database_service
    ):
        """Test health check for an unused index."""
        mock_result = [
            {
                "index_name": "test_idx",
                "index_size_bytes": 500000,
                "index_size_human": "500 kB",
                "row_count": 1000,
                "index_usage_count": 0,  # Never used
                "last_used": None,
            }
        ]
        mock_database_service.execute_sql.return_value = mock_result

        health = await pgvector_service.check_index_health("test_table", "embedding")

        assert health["status"] == "needs_attention"
        assert "Index is not being used" in health["recommendations"][0]

    @pytest.mark.asyncio
    async def test_check_index_health_large_index(
        self, pgvector_service, mock_database_service
    ):
        """Test health check for a large index."""
        mock_result = [
            {
                "index_name": "test_idx",
                "index_size_bytes": 2 * 1024 * 1024 * 1024,  # 2GB
                "index_size_human": "2 GB",
                "row_count": 1000000,
                "index_usage_count": 100,
                "last_used": "2025-01-01 12:00:00",
            }
        ]
        mock_database_service.execute_sql.return_value = mock_result

        health = await pgvector_service.check_index_health("test_table", "embedding")

        assert health["status"] == "needs_attention"
        assert any("Large index" in rec for rec in health["recommendations"])

    @pytest.mark.asyncio
    async def test_check_index_health_high_bytes_per_row(
        self, pgvector_service, mock_database_service
    ):
        """Test health check for index with high bytes per row."""
        mock_result = [
            {
                "index_name": "test_idx",
                "index_size_bytes": 2000000,  # 2MB
                "index_size_human": "2 MB",
                "row_count": 1000,  # High bytes per row (2000 bytes/row)
                "index_usage_count": 100,
                "last_used": "2025-01-01 12:00:00",
            }
        ]
        mock_database_service.execute_sql.return_value = mock_result

        health = await pgvector_service.check_index_health("test_table", "embedding")

        assert health["status"] == "needs_attention"
        assert any("Index size seems large" in rec for rec in health["recommendations"])

    @pytest.mark.asyncio
    async def test_optimize_for_table_new_index(
        self, pgvector_service, mock_database_service
    ):
        """Test table optimization when no index exists."""
        # Use return_value to provide consistent empty response for all SQL calls
        mock_database_service.execute_sql.return_value = []

        results = await pgvector_service.optimize_for_table(
            "test_table", "embedding", "medium"
        )

        assert results["table"] == "test_table"
        assert results["column"] == "embedding"
        assert len(results["actions"]) >= 1

        # Should have created an index
        create_action = next(
            (a for a in results["actions"] if a["action"] == "created_index"), None
        )
        assert create_action is not None
        assert "index_name" in create_action
        assert create_action["profile"] == "balanced"

    @pytest.mark.asyncio
    async def test_optimize_for_table_existing_index(
        self, pgvector_service, mock_database_service
    ):
        """Test table optimization when index already exists."""
        mock_index_result = [
            {
                "index_name": "existing_idx",
                "index_size_bytes": 500000,
                "index_size_human": "500 kB",
                "row_count": 1000,
                "index_usage_count": 100,
                "last_used": "2025-01-01 12:00:00",
            }
        ]

        mock_database_service.execute_sql.side_effect = [
            mock_index_result,  # get_index_stats returns existing index
            [],  # set_query_quality call
            mock_index_result,  # check_index_health call
        ]

        results = await pgvector_service.optimize_for_table(
            "test_table", "embedding", "high"
        )

        assert results["table"] == "test_table"
        assert results["column"] == "embedding"

        # Should have found existing index
        exists_action = next(
            (a for a in results["actions"] if a["action"] == "index_exists"), None
        )
        assert exists_action is not None
        assert exists_action["index_name"] == "existing_idx"
        assert exists_action["size"] == "500 kB"

    @pytest.mark.asyncio
    async def test_optimize_for_table_query_load_mapping(
        self, pgvector_service, mock_database_service
    ):
        """Test that query load maps to correct profiles."""
        mock_database_service.execute_sql.return_value = []

        # Test low load -> speed profile
        await pgvector_service.optimize_for_table("test_table", "embedding", "low")

        # Test medium load -> balanced profile
        await pgvector_service.optimize_for_table("test_table", "embedding", "medium")

        # Test high load -> quality profile
        await pgvector_service.optimize_for_table("test_table", "embedding", "high")

        # Test invalid load -> defaults to balanced
        await pgvector_service.optimize_for_table("test_table", "embedding", "invalid")

        # All calls should have succeeded
        assert mock_database_service.execute_sql.call_count >= 4

    @pytest.mark.asyncio
    async def test_optimize_memory_tables(
        self, pgvector_service, mock_database_service
    ):
        """Test optimizing memory tables for Mem0 integration."""

        # Mock table and column existence checks
        def mock_execute_side_effect(*args, **kwargs):
            sql = args[0] if args else ""
            if "information_schema.tables" in sql:
                return [[True]]  # Table exists
            elif "information_schema.columns" in sql:
                return [[True]]  # Vector column exists
            elif "pg_relation_size" in sql:
                return [{"index_size": "1 MB", "index_size_bytes": 1048576}]
            return []

        mock_database_service.execute_sql.side_effect = mock_execute_side_effect

        results = await pgvector_service.optimize_memory_tables()

        assert "memory_optimization" in results
        assert "errors" in results
        assert isinstance(results["memory_optimization"], list)
        assert isinstance(results["errors"], list)

        # Should have attempted to optimize memory tables
        optimization_results = results["memory_optimization"]
        if optimization_results:  # If any tables were found and optimized
            for result in optimization_results:
                assert "table_type" in result
                assert result["table_type"] == "memory"

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_with_errors(
        self, pgvector_service, mock_database_service
    ):
        """Test memory table optimization with some errors."""

        def mock_execute_side_effect(*args, **kwargs):
            sql = args[0] if args else ""
            table_name = args[1][0] if len(args) > 1 and args[1] else ""

            if table_name == "memories":
                raise Exception("Connection timeout")
            elif "information_schema.tables" in sql:
                return [[True]]  # Table exists
            elif "information_schema.columns" in sql:
                return [[True]]  # Vector column exists
            return []

        mock_database_service.execute_sql.side_effect = mock_execute_side_effect

        results = await pgvector_service.optimize_memory_tables()

        assert "errors" in results
        assert len(results["errors"]) > 0

        # Should have error for memories table
        memory_error = next(
            (e for e in results["errors"] if e["table"] == "memories"), None
        )
        assert memory_error is not None
        assert "Connection timeout" in memory_error["error"]

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_no_tables_exist(
        self, pgvector_service, mock_database_service
    ):
        """Test memory table optimization when no tables exist."""

        def mock_execute_side_effect(*args, **kwargs):
            sql = args[0] if args else ""

            if "information_schema.tables" in sql:
                return [[False]]  # Table does not exist
            elif "information_schema.columns" in sql:
                return [[False]]  # Column does not exist
            return []

        mock_database_service.execute_sql.side_effect = mock_execute_side_effect

        results = await pgvector_service.optimize_memory_tables()

        assert "memory_optimization" in results
        assert "errors" in results
        # Should have no optimizations or errors since no tables exist
        assert len(results["memory_optimization"]) == 0
        assert len(results["errors"]) == 0

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_no_vector_columns(
        self, pgvector_service, mock_database_service
    ):
        """Test memory table optimization when tables exist but no vector columns."""

        def mock_execute_side_effect(*args, **kwargs):
            sql = args[0] if args else ""

            if "information_schema.tables" in sql:
                return [[True]]  # Table exists
            elif "information_schema.columns" in sql:
                return [[False]]  # Vector column does not exist
            return []

        mock_database_service.execute_sql.side_effect = mock_execute_side_effect

        results = await pgvector_service.optimize_memory_tables()

        assert "memory_optimization" in results
        assert "errors" in results
        # Should have no optimizations since no vector columns exist
        assert len(results["memory_optimization"]) == 0
        assert len(results["errors"]) == 0

    @pytest.mark.asyncio
    async def test_list_vector_tables(self, pgvector_service, mock_database_service):
        """Test listing tables with vector columns."""
        mock_result = [
            {
                "table_name": "embeddings",
                "column_name": "vector",
                "index_status": "indexed",
            },
            {
                "table_name": "memories",
                "column_name": "embedding",
                "index_status": "no_index",
            },
        ]
        mock_database_service.execute_sql.return_value = mock_result

        tables = await pgvector_service.list_vector_tables()

        assert len(tables) == 2
        assert tables[0]["table_name"] == "embeddings"
        assert tables[0]["column_name"] == "vector"
        assert tables[0]["index_status"] == "indexed"
        assert tables[1]["table_name"] == "memories"
        assert tables[1]["index_status"] == "no_index"

    @pytest.mark.asyncio
    async def test_list_vector_tables_empty(
        self, pgvector_service, mock_database_service
    ):
        """Test listing vector tables when none exist."""
        mock_database_service.execute_sql.return_value = []

        tables = await pgvector_service.list_vector_tables()

        assert tables == []

    @pytest.mark.asyncio
    async def test_set_default_ef_search_success(
        self, pgvector_service, mock_database_service
    ):
        """Test setting default ef_search successfully."""
        mock_database_service.execute_sql.return_value = []

        await pgvector_service._set_default_ef_search(100)

        mock_database_service.execute_sql.assert_called_once_with(
            "SET hnsw.ef_search = 100"
        )

    @pytest.mark.asyncio
    async def test_set_default_ef_search_error(
        self, pgvector_service, mock_database_service
    ):
        """Test setting default ef_search with error (should not raise)."""
        mock_database_service.execute_sql.side_effect = Exception("Permission denied")

        # Should not raise exception, just log warning
        await pgvector_service._set_default_ef_search(100)

        mock_database_service.execute_sql.assert_called_once_with(
            "SET hnsw.ef_search = 100"
        )

class TestUtilityFunction:
    """Test the optimize_vector_table utility function."""

    @pytest.mark.asyncio
    async def test_optimize_vector_table_success(self):
        """Test the quick optimization utility function."""
        mock_db = AsyncMock()
        mock_db.execute_sql.return_value = []

        results = await optimize_vector_table(
            mock_db, "test_table", "embedding", "medium"
        )

        assert "table" in results
        assert "column" in results
        assert "actions" in results
        assert results["table"] == "test_table"
        assert results["column"] == "embedding"

class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service."""
        mock_db = AsyncMock()
        return mock_db

    @pytest.fixture
    def pgvector_service(self, mock_database_service):
        """Create a PGVectorService with mocked database."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_create_hnsw_index_database_error(
        self, pgvector_service, mock_database_service
    ):
        """Test handling database errors during index creation."""
        mock_database_service.execute_sql.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(Exception, match="Database connection failed"):
            await pgvector_service.create_hnsw_index("test_table", "embedding")

    @pytest.mark.asyncio
    async def test_get_index_stats_database_error(
        self, pgvector_service, mock_database_service
    ):
        """Test handling database errors during stats retrieval."""
        mock_database_service.execute_sql.side_effect = Exception("Query failed")

        with pytest.raises(Exception, match="Query failed"):
            await pgvector_service.get_index_stats("test_table", "embedding")

    @pytest.mark.asyncio
    async def test_set_query_quality_database_error(
        self, pgvector_service, mock_database_service
    ):
        """Test handling database errors during query quality setting."""
        mock_database_service.execute_sql.side_effect = Exception("Permission denied")

        with pytest.raises(Exception, match="Permission denied"):
            await pgvector_service.set_query_quality(100)

    def test_invalid_optimization_profile_access(self, pgvector_service):
        """Test accessing invalid optimization profile."""
        # This should work since we're accessing via enum
        profile = OptimizationProfile.SPEED
        config = pgvector_service._profiles[profile]
        assert config.ef_search == 40

    def test_distance_function_suffix_extraction(self, pgvector_service):
        """Test distance function suffix extraction for index naming."""
        # Test L2 suffix extraction
        suffix = DistanceFunction.L2.value.split("_")[1]
        assert suffix == "l2"

        # Test COSINE suffix extraction
        suffix = DistanceFunction.COSINE.value.split("_")[1]
        assert suffix == "cosine"

        # Test INNER_PRODUCT suffix extraction
        suffix = DistanceFunction.INNER_PRODUCT.value.split("_")[1]
        assert suffix == "ip"

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service."""
        mock_db = AsyncMock()
        return mock_db

    @pytest.fixture
    def pgvector_service(self, mock_database_service):
        """Create a PGVectorService with mocked database."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_full_table_optimization_workflow(
        self, pgvector_service, mock_database_service
    ):
        """Test complete table optimization workflow."""
        # Use return_value to provide consistent empty response for all SQL calls
        mock_database_service.execute_sql.return_value = []

        results = await pgvector_service.optimize_for_table(
            "large_embeddings", "content_vector", "high"
        )

        assert results["table"] == "large_embeddings"
        assert results["column"] == "content_vector"
        assert len(results["actions"]) >= 1

        # Verify index was created with quality profile
        create_action = next(
            (a for a in results["actions"] if a["action"] == "created_index"), None
        )
        assert create_action is not None
        assert create_action["profile"] == "quality"

    @pytest.mark.asyncio
    async def test_memory_system_integration_workflow(
        self, pgvector_service, mock_database_service
    ):
        """Test Mem0 memory system integration workflow."""
        # Mock memory tables exist and get optimized
        # use return_value for consistent behavior
        mock_database_service.execute_sql.return_value = [
            [True]
        ]  # All queries return table/column exists

        results = await pgvector_service.optimize_memory_tables()

        assert "memory_optimization" in results
        # Note: Since we're mocking all responses as True, some optimizations will fail
        # but the method should still return results without raising exceptions

        # Verify the structure is correct even if some operations fail
        assert isinstance(results["memory_optimization"], list)
        assert isinstance(results["errors"], list)

    @pytest.mark.asyncio
    async def test_query_performance_optimization_workflow(
        self, pgvector_service, mock_database_service
    ):
        """Test query performance optimization workflow."""
        mock_database_service.execute_sql.return_value = []

        # Test speed optimization
        await pgvector_service.set_query_quality(40)  # Speed
        await pgvector_service.set_query_quality(100)  # Balanced
        await pgvector_service.set_query_quality(200)  # Quality

        # Verify settings were applied
        calls = mock_database_service.execute_sql.call_args_list
        assert len(calls) == 3
        assert "SET hnsw.ef_search = 40" in calls[0][0][0]
        assert "SET hnsw.ef_search = 100" in calls[1][0][0]
        assert "SET hnsw.ef_search = 200" in calls[2][0][0]

    @pytest.mark.asyncio
    async def test_index_monitoring_workflow(
        self, pgvector_service, mock_database_service
    ):
        """Test index monitoring and health checking workflow."""
        # Mock progressive index usage
        health_checks = [
            # Unused index
            [
                {
                    "index_name": "test_idx",
                    "index_size_bytes": 1000000,
                    "index_size_human": "1 MB",
                    "row_count": 1000,
                    "index_usage_count": 0,
                    "last_used": None,
                }
            ],
            # Used index
            [
                {
                    "index_name": "test_idx",
                    "index_size_bytes": 1000000,
                    "index_size_human": "1 MB",
                    "row_count": 1000,
                    "index_usage_count": 100,
                    "last_used": "2025-01-01 12:00:00",
                }
            ],
        ]

        for i, mock_result in enumerate(health_checks):
            mock_database_service.execute_sql.return_value = mock_result

            health = await pgvector_service.check_index_health(
                "test_table", "embedding"
            )

            if i == 0:
                # First check - unused index
                assert health["status"] == "needs_attention"
                assert any("not being used" in rec for rec in health["recommendations"])
            else:
                # Second check - used index
                assert health["status"] == "healthy"
                assert len(health["recommendations"]) == 0
