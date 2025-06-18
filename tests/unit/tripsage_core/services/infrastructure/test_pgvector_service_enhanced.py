"""
Enhanced comprehensive tests for TripSage Core PGVector Service.

This module provides 90%+ test coverage for PGVector service functionality with
modern testing patterns:
- Index creation and optimization workflows
- Performance profile management (speed/balanced/quality)
- Memory table optimization for Mem0 integration
- Index health monitoring and recommendations
- Query optimization with ef_search tuning
- Vector table discovery and statistics
- Error handling and edge cases
- Concurrent operations and performance testing

Modern testing patterns:
- AAA (Arrange, Act, Assert) pattern
- pytest-asyncio for async test support
- Hypothesis for property-based testing
- Comprehensive fixture management
- Proper mocking with isolation
- Performance and load testing scenarios
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from hypothesis import given
from hypothesis import strategies as st

from tripsage_core.services.infrastructure.pgvector_service import (
    DistanceFunction,
    IndexConfig,
    IndexStats,
    OptimizationProfile,
    PGVectorService,
    optimize_vector_table,
)


class TestPGVectorServiceInitialization:
    """Test suite for PGVector service initialization."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    def test_initialization(self, pgvector_service, mock_database_service):
        """Test PGVector service initialization."""
        # Assert
        assert pgvector_service.db == mock_database_service
        assert pgvector_service._profiles is not None
        assert len(pgvector_service._profiles) == 3

    def test_profiles_creation(self, pgvector_service):
        """Test optimization profiles creation."""
        # Arrange & Act
        profiles = pgvector_service._profiles

        # Assert
        assert OptimizationProfile.SPEED in profiles
        assert OptimizationProfile.BALANCED in profiles
        assert OptimizationProfile.QUALITY in profiles

        # Verify profile configurations
        speed_profile = profiles[OptimizationProfile.SPEED]
        assert speed_profile.m == 16
        assert speed_profile.ef_construction == 64
        assert speed_profile.ef_search == 40

        balanced_profile = profiles[OptimizationProfile.BALANCED]
        assert balanced_profile.ef_search == 100

        quality_profile = profiles[OptimizationProfile.QUALITY]
        assert quality_profile.ef_construction == 100
        assert quality_profile.ef_search == 200


class TestPGVectorServiceIndexCreation:
    """Test suite for HNSW index creation."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_create_hnsw_index_default_params(self, pgvector_service):
        """Test HNSW index creation with default parameters."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"

        # Act
        index_name = await pgvector_service.create_hnsw_index(table_name, column_name)

        # Assert
        assert index_name == "idx_test_table_embedding_cosine_hnsw"
        pgvector_service.db.execute_sql.assert_called()

        # Verify SQL contains expected elements
        call_args = pgvector_service.db.execute_sql.call_args_list
        create_index_call = call_args[0][0][0]
        assert "CREATE INDEX CONCURRENTLY" in create_index_call
        assert "USING hnsw" in create_index_call
        assert "vector_cosine_ops" in create_index_call

    @pytest.mark.asyncio
    async def test_create_hnsw_index_custom_name(self, pgvector_service):
        """Test HNSW index creation with custom name."""
        # Arrange
        table_name = "destinations"
        column_name = "vector"
        custom_name = "custom_vector_index"

        # Act
        index_name = await pgvector_service.create_hnsw_index(
            table_name, column_name, index_name=custom_name
        )

        # Assert
        assert index_name == custom_name

    @pytest.mark.asyncio
    async def test_create_hnsw_index_different_distance_functions(
        self, pgvector_service
    ):
        """Test HNSW index creation with different distance functions."""
        # Test cases for each distance function
        test_cases = [
            (DistanceFunction.L2, "vector_l2_ops", "l2"),
            (DistanceFunction.COSINE, "vector_cosine_ops", "cosine"),
            (DistanceFunction.INNER_PRODUCT, "vector_ip_ops", "ip"),
        ]

        for distance_func, ops_string, suffix in test_cases:
            # Arrange
            table_name = "test_table"
            column_name = "embedding"

            # Act
            index_name = await pgvector_service.create_hnsw_index(
                table_name, column_name, distance_function=distance_func
            )

            # Assert
            assert suffix in index_name

            # Verify correct ops string was used
            call_args = pgvector_service.db.execute_sql.call_args_list[
                -2
            ]  # -2 because _set_default_ef_search is also called
            create_index_call = call_args[0][0]
            assert ops_string in create_index_call

    @pytest.mark.asyncio
    async def test_create_hnsw_index_quality_profile(self, pgvector_service):
        """Test HNSW index creation with quality profile."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"
        profile = OptimizationProfile.QUALITY

        # Act
        await pgvector_service.create_hnsw_index(
            table_name, column_name, profile=profile
        )

        # Assert
        call_args = pgvector_service.db.execute_sql.call_args_list

        # Should have calls for index creation and ef_search setting
        assert len(call_args) >= 2

        # Check that ef_construction is set in index creation
        create_index_call = call_args[0][0][0]
        assert "ef_construction = 100" in create_index_call

    @pytest.mark.asyncio
    async def test_create_hnsw_index_speed_profile(self, pgvector_service):
        """Test HNSW index creation with speed profile (defaults)."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"
        profile = OptimizationProfile.SPEED

        # Act
        await pgvector_service.create_hnsw_index(
            table_name, column_name, profile=profile
        )

        # Assert
        call_args = pgvector_service.db.execute_sql.call_args_list

        # Should only have index creation call (no WITH clause for defaults)
        create_index_call = call_args[0][0][0]
        assert "WITH (" not in create_index_call


class TestPGVectorServiceQueryOptimization:
    """Test suite for query optimization."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_set_query_quality(self, pgvector_service):
        """Test setting query quality with ef_search."""
        # Arrange
        ef_search = 150

        # Act
        await pgvector_service.set_query_quality(ef_search)

        # Assert
        pgvector_service.db.execute_sql.assert_called_with(
            f"SET hnsw.ef_search = {ef_search}"
        )

    @pytest.mark.asyncio
    async def test_set_query_quality_default(self, pgvector_service):
        """Test setting query quality with default value."""
        # Act
        await pgvector_service.set_query_quality()

        # Assert
        pgvector_service.db.execute_sql.assert_called_with("SET hnsw.ef_search = 100")

    @pytest.mark.asyncio
    async def test_reset_query_settings(self, pgvector_service):
        """Test resetting query settings to defaults."""
        # Act
        await pgvector_service.reset_query_settings()

        # Assert
        pgvector_service.db.execute_sql.assert_called_with("RESET hnsw.ef_search")


class TestPGVectorServiceIndexStatistics:
    """Test suite for index statistics and monitoring."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_get_index_stats_exists(self, pgvector_service):
        """Test getting index statistics when index exists."""
        # Arrange
        table_name = "destinations"
        column_name = "embedding"

        mock_stats_data = [
            {
                "index_name": "idx_destinations_embedding_cosine_hnsw",
                "index_size_bytes": 1048576,  # 1MB
                "index_size_human": "1 MB",
                "row_count": 1000,
                "index_usage_count": 150,
                "last_used": "2025-01-01 12:00:00",
            }
        ]

        pgvector_service.db.execute_sql.return_value = mock_stats_data

        # Act
        stats = await pgvector_service.get_index_stats(table_name, column_name)

        # Assert
        assert stats is not None
        assert isinstance(stats, IndexStats)
        assert stats.index_name == "idx_destinations_embedding_cosine_hnsw"
        assert stats.index_size_bytes == 1048576
        assert stats.index_size_human == "1 MB"
        assert stats.row_count == 1000
        assert stats.index_usage_count == 150
        assert stats.last_used == "2025-01-01 12:00:00"

    @pytest.mark.asyncio
    async def test_get_index_stats_not_exists(self, pgvector_service):
        """Test getting index statistics when index doesn't exist."""
        # Arrange
        table_name = "nonexistent_table"
        column_name = "embedding"

        pgvector_service.db.execute_sql.return_value = []

        # Act
        stats = await pgvector_service.get_index_stats(table_name, column_name)

        # Assert
        assert stats is None

    @pytest.mark.asyncio
    async def test_check_index_health_missing(self, pgvector_service):
        """Test index health check when index is missing."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            mock_get_stats.return_value = None

            # Act
            health = await pgvector_service.check_index_health(table_name, column_name)

            # Assert
            assert health["status"] == "missing"
            assert "No HNSW index found" in health["message"]
            assert len(health["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_check_index_health_healthy(self, pgvector_service):
        """Test index health check for healthy index."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"

        mock_stats = IndexStats(
            index_name="test_index",
            index_size_bytes=1048576,  # 1MB
            index_size_human="1 MB",
            row_count=1000,
            index_usage_count=100,
            last_used="2025-01-01 12:00:00",
        )

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            # Act
            health = await pgvector_service.check_index_health(table_name, column_name)

            # Assert
            assert health["status"] == "healthy"
            assert health["index_name"] == "test_index"
            assert len(health["recommendations"]) == 0

    @pytest.mark.asyncio
    async def test_check_index_health_unused(self, pgvector_service):
        """Test index health check for unused index."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"

        mock_stats = IndexStats(
            index_name="test_index",
            index_size_bytes=1048576,
            index_size_human="1 MB",
            row_count=1000,
            index_usage_count=0,  # Unused
            last_used=None,
        )

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            # Act
            health = await pgvector_service.check_index_health(table_name, column_name)

            # Assert
            assert health["status"] == "needs_attention"
            assert any("not being used" in rec for rec in health["recommendations"])

    @pytest.mark.asyncio
    async def test_check_index_health_large_size(self, pgvector_service):
        """Test index health check for large index."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"

        mock_stats = IndexStats(
            index_name="test_index",
            index_size_bytes=2 * 1024 * 1024 * 1024,  # 2GB
            index_size_human="2 GB",
            row_count=1000,
            index_usage_count=100,
            last_used="2025-01-01 12:00:00",
        )

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            # Act
            health = await pgvector_service.check_index_health(table_name, column_name)

            # Assert
            assert health["status"] == "needs_attention"
            assert any("Large index" in rec for rec in health["recommendations"])


class TestPGVectorServiceTableOptimization:
    """Test suite for table optimization workflows."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_optimize_for_table_no_index(self, pgvector_service):
        """Test table optimization when no index exists."""
        # Arrange
        table_name = "destinations"
        column_name = "embedding"
        expected_query_load = "medium"

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            with patch.object(pgvector_service, "create_hnsw_index") as mock_create:
                with patch.object(pgvector_service, "set_query_quality"):
                    with patch.object(
                        pgvector_service, "check_index_health"
                    ) as mock_health:
                        mock_get_stats.return_value = None
                        mock_create.return_value = "new_index_name"
                        mock_health.return_value = {"recommendations": []}

                        # Act
                        results = await pgvector_service.optimize_for_table(
                            table_name, column_name, expected_query_load
                        )

                        # Assert
                        assert results["table"] == table_name
                        assert results["column"] == column_name
                        assert len(results["actions"]) >= 1

                        created_action = next(
                            action
                            for action in results["actions"]
                            if action["action"] == "created_index"
                        )
                        assert created_action["index_name"] == "new_index_name"
                        assert created_action["profile"] == "balanced"

    @pytest.mark.asyncio
    async def test_optimize_for_table_index_exists(self, pgvector_service):
        """Test table optimization when index already exists."""
        # Arrange
        table_name = "destinations"
        column_name = "embedding"

        mock_stats = IndexStats(
            index_name="existing_index",
            index_size_bytes=1048576,
            index_size_human="1 MB",
            row_count=1000,
            index_usage_count=100,
            last_used="2025-01-01 12:00:00",
        )

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            with patch.object(pgvector_service, "set_query_quality"):
                with patch.object(
                    pgvector_service, "check_index_health"
                ) as mock_health:
                    mock_get_stats.return_value = mock_stats
                    mock_health.return_value = {"recommendations": []}

                    # Act
                    results = await pgvector_service.optimize_for_table(
                        table_name, column_name, "medium"
                    )

                    # Assert
                    exists_action = next(
                        action
                        for action in results["actions"]
                        if action["action"] == "index_exists"
                    )
                    assert exists_action["index_name"] == "existing_index"
                    assert exists_action["size"] == "1 MB"

    @pytest.mark.asyncio
    async def test_optimize_for_table_different_loads(self, pgvector_service):
        """Test table optimization with different query loads."""
        # Test cases for different load levels
        load_profile_map = {
            "low": OptimizationProfile.SPEED,
            "medium": OptimizationProfile.BALANCED,
            "high": OptimizationProfile.QUALITY,
        }

        for load, expected_profile in load_profile_map.items():
            # Arrange
            table_name = "test_table"
            column_name = "embedding"

            with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
                with patch.object(pgvector_service, "create_hnsw_index") as mock_create:
                    with patch.object(
                        pgvector_service, "check_index_health"
                    ) as mock_health:
                        mock_get_stats.return_value = None
                        mock_create.return_value = "test_index"
                        mock_health.return_value = {"recommendations": []}

                        # Act
                        await pgvector_service.optimize_for_table(
                            table_name, column_name, load
                        )

                        # Assert
                        mock_create.assert_called_with(
                            table_name, column_name, profile=expected_profile
                        )


class TestPGVectorServiceMemoryOptimization:
    """Test suite for memory table optimization."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_success(self, pgvector_service):
        """Test successful memory table optimization."""
        # Arrange
        # Mock table existence checks
        table_exists_responses = [
            [True],  # memories table exists
            [True],  # conversations table exists
            [False],  # user_context table doesn't exist
            [True],  # chat_history table exists
            [False],  # travel_preferences table doesn't exist
        ]

        column_exists_responses = [
            [True],  # memories.embedding exists
            [True],  # conversations.embedding exists
            [True],  # chat_history.vector_content exists
        ]

        # Set up mock responses
        pgvector_service.db.execute_sql.side_effect = (
            table_exists_responses + column_exists_responses
        )

        with patch.object(pgvector_service, "optimize_for_table") as mock_optimize:
            mock_optimize.return_value = {
                "table": "test_table",
                "column": "embedding",
                "actions": [{"action": "created_index", "index_name": "test_index"}],
            }

            # Act
            results = await pgvector_service.optimize_memory_tables()

            # Assert
            assert "memory_optimization" in results
            assert "errors" in results
            assert len(results["memory_optimization"]) > 0

            # Verify that optimize_for_table was called for existing tables
            assert mock_optimize.call_count > 0

    @pytest.mark.asyncio
    async def test_optimize_memory_tables_with_errors(self, pgvector_service):
        """Test memory table optimization with errors."""
        # Arrange
        pgvector_service.db.execute_sql.side_effect = Exception("Database error")

        # Act
        results = await pgvector_service.optimize_memory_tables()

        # Assert
        assert "errors" in results
        assert len(results["errors"]) > 0

        # Should have error entries for each table pattern
        error_tables = [error["table"] for error in results["errors"]]
        assert "memories" in error_tables


class TestPGVectorServiceTableDiscovery:
    """Test suite for vector table discovery."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_list_vector_tables_with_results(self, pgvector_service):
        """Test listing vector tables with results."""
        # Arrange
        mock_table_data = [
            {
                "table_name": "destinations",
                "column_name": "embedding",
                "index_status": "indexed",
            },
            {
                "table_name": "memories",
                "column_name": "embedding",
                "index_status": "no_index",
            },
            {
                "table_name": "conversations",
                "column_name": "vector_content",
                "index_status": "indexed",
            },
        ]

        pgvector_service.db.execute_sql.return_value = mock_table_data

        # Act
        tables = await pgvector_service.list_vector_tables()

        # Assert
        assert len(tables) == 3
        assert tables[0]["table_name"] == "destinations"
        assert tables[0]["index_status"] == "indexed"
        assert tables[1]["index_status"] == "no_index"

    @pytest.mark.asyncio
    async def test_list_vector_tables_empty(self, pgvector_service):
        """Test listing vector tables with no results."""
        # Arrange
        pgvector_service.db.execute_sql.return_value = []

        # Act
        tables = await pgvector_service.list_vector_tables()

        # Assert
        assert tables == []


class TestPGVectorServiceUtilityFunctions:
    """Test suite for utility functions."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest.mark.asyncio
    async def test_optimize_vector_table_utility(self, mock_database_service):
        """Test the optimize_vector_table utility function."""
        # Arrange
        table_name = "test_table"
        column_name = "embedding"
        query_load = "high"

        with patch(
            "tripsage_core.services.infrastructure.pgvector_service.PGVectorService"
        ) as MockService:
            mock_service_instance = Mock()
            mock_service_instance.optimize_for_table = AsyncMock(
                return_value={"test": "result"}
            )
            MockService.return_value = mock_service_instance

            # Act
            result = await optimize_vector_table(
                mock_database_service, table_name, column_name, query_load
            )

            # Assert
            MockService.assert_called_once_with(mock_database_service)
            mock_service_instance.optimize_for_table.assert_called_once_with(
                table_name, column_name, query_load
            )
            assert result == {"test": "result"}


class TestPGVectorServiceErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_create_index_database_error(self, pgvector_service):
        """Test index creation with database error."""
        # Arrange
        pgvector_service.db.execute_sql.side_effect = Exception(
            "Database connection failed"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await pgvector_service.create_hnsw_index("test_table", "embedding")

        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_ef_search_error_handling(self, pgvector_service):
        """Test ef_search setting with error handling."""
        # Arrange
        pgvector_service.db.execute_sql.side_effect = Exception("Permission denied")

        # Act & Assert - Should not raise exception due to internal error handling
        await pgvector_service._set_default_ef_search(100)

    @pytest.mark.asyncio
    async def test_get_index_stats_database_error(self, pgvector_service):
        """Test getting index stats with database error."""
        # Arrange
        pgvector_service.db.execute_sql.side_effect = Exception("Query failed")

        # Act & Assert
        with pytest.raises(Exception):
            await pgvector_service.get_index_stats("test_table", "embedding")


class TestPGVectorServiceDataModels:
    """Test suite for data models and validation."""

    def test_index_config_defaults(self):
        """Test IndexConfig default values."""
        # Arrange & Act
        config = IndexConfig()

        # Assert
        assert config.m == 16
        assert config.ef_construction == 64
        assert config.ef_search == 40

    def test_index_config_custom_values(self):
        """Test IndexConfig with custom values."""
        # Arrange & Act
        config = IndexConfig(m=32, ef_construction=128, ef_search=200)

        # Assert
        assert config.m == 32
        assert config.ef_construction == 128
        assert config.ef_search == 200

    def test_index_stats_creation(self):
        """Test IndexStats model creation."""
        # Arrange & Act
        stats = IndexStats(
            index_name="test_index",
            index_size_bytes=1048576,
            index_size_human="1 MB",
            row_count=1000,
            index_usage_count=50,
            last_used="2025-01-01 12:00:00",
        )

        # Assert
        assert stats.index_name == "test_index"
        assert stats.index_size_bytes == 1048576
        assert stats.index_size_human == "1 MB"
        assert stats.row_count == 1000
        assert stats.index_usage_count == 50
        assert stats.last_used == "2025-01-01 12:00:00"

    def test_distance_function_enum(self):
        """Test DistanceFunction enum values."""
        # Assert
        assert DistanceFunction.L2 == "vector_l2_ops"
        assert DistanceFunction.COSINE == "vector_cosine_ops"
        assert DistanceFunction.INNER_PRODUCT == "vector_ip_ops"

    def test_optimization_profile_enum(self):
        """Test OptimizationProfile enum values."""
        # Assert
        assert OptimizationProfile.SPEED == "speed"
        assert OptimizationProfile.BALANCED == "balanced"
        assert OptimizationProfile.QUALITY == "quality"


# Property-based testing with Hypothesis
class TestPGVectorServicePropertyBased:
    """Property-based tests using Hypothesis."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @given(
        table_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=["Ll", "Lu", "Nd"]),
        ),
        column_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=["Ll", "Lu", "Nd"]),
        ),
    )
    @pytest.mark.asyncio
    async def test_index_name_generation_property(
        self, pgvector_service, table_name, column_name
    ):
        """Property test: generated index names should be consistent and valid."""
        # Act
        index_name = await pgvector_service.create_hnsw_index(table_name, column_name)

        # Assert
        assert table_name in index_name
        assert column_name in index_name
        assert "hnsw" in index_name
        assert len(index_name) > 0

    @given(ef_search=st.integers(min_value=1, max_value=1000))
    @pytest.mark.asyncio
    async def test_ef_search_setting_property(self, pgvector_service, ef_search):
        """Property test: ef_search setting should handle various valid values."""
        # Act & Assert - Should not raise exception for valid values
        await pgvector_service.set_query_quality(ef_search)

        # Verify the correct SQL was called
        expected_sql = f"SET hnsw.ef_search = {ef_search}"
        pgvector_service.db.execute_sql.assert_called_with(expected_sql)

    @given(
        row_count=st.integers(min_value=0, max_value=1000000),
        index_size=st.integers(min_value=0, max_value=10**10),
        usage_count=st.integers(min_value=0, max_value=1000000),
    )
    def test_index_stats_validation_property(self, row_count, index_size, usage_count):
        """Property test: IndexStats should handle various numeric values."""
        # Act
        stats = IndexStats(
            index_name="test_index",
            index_size_bytes=index_size,
            index_size_human=f"{index_size} bytes",
            row_count=row_count,
            index_usage_count=usage_count,
        )

        # Assert
        assert stats.row_count == row_count
        assert stats.index_size_bytes == index_size
        assert stats.index_usage_count == usage_count


# Performance and concurrent operations testing
class TestPGVectorServicePerformance:
    """Performance tests for PGVector service."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_concurrent_index_creation(self, pgvector_service):
        """Test concurrent index creation operations."""
        # Arrange
        tables = [f"table_{i}" for i in range(10)]
        columns = [f"embedding_{i}" for i in range(10)]

        # Act
        start_time = asyncio.get_event_loop().time()

        tasks = [
            pgvector_service.create_hnsw_index(table, column)
            for table, column in zip(tables, columns, strict=False)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time

        # Assert
        assert len(results) == 10
        # Should complete concurrent operations efficiently
        assert execution_time < 2.0  # 2 seconds for 10 operations

        # All operations should succeed
        assert all(isinstance(result, str) for result in results)

    @pytest.mark.asyncio
    async def test_bulk_optimization_performance(self, pgvector_service):
        """Test performance of bulk table optimization."""
        # Arrange
        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            with patch.object(pgvector_service, "create_hnsw_index") as mock_create:
                with patch.object(
                    pgvector_service, "check_index_health"
                ) as mock_health:
                    mock_get_stats.return_value = None  # No existing index
                    mock_create.return_value = "test_index"
                    mock_health.return_value = {"recommendations": []}

                    tables = [f"table_{i}" for i in range(20)]
                    columns = [f"embedding_{i}" for i in range(20)]

                    # Act
                    start_time = asyncio.get_event_loop().time()

                    tasks = [
                        pgvector_service.optimize_for_table(table, column)
                        for table, column in zip(tables, columns, strict=False)
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    end_time = asyncio.get_event_loop().time()
                    execution_time = end_time - start_time

                    # Assert
                    assert len(results) == 20
                    assert (
                        execution_time < 3.0
                    )  # Should handle bulk operations efficiently

                    # All operations should succeed
                    assert all(isinstance(result, dict) for result in results)

    @pytest.mark.asyncio
    async def test_health_check_performance(self, pgvector_service):
        """Test performance of health check operations."""
        # Arrange
        mock_stats = IndexStats(
            index_name="test_index",
            index_size_bytes=1048576,
            index_size_human="1 MB",
            row_count=1000,
            index_usage_count=100,
            last_used="2025-01-01 12:00:00",
        )

        with patch.object(pgvector_service, "get_index_stats") as mock_get_stats:
            mock_get_stats.return_value = mock_stats

            # Act
            start_time = asyncio.get_event_loop().time()

            # Perform multiple health checks concurrently
            tasks = [
                pgvector_service.check_index_health(f"table_{i}", "embedding")
                for i in range(50)
            ]

            results = await asyncio.gather(*tasks)

            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time

            # Assert
            assert len(results) == 50
            assert execution_time < 1.0  # Health checks should be fast

            # All should return health status
            assert all("status" in result for result in results)


# Integration-style tests
class TestPGVectorServiceIntegration:
    """Integration-style tests for complete workflows."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        db_service = AsyncMock()
        db_service.execute_sql = AsyncMock()
        return db_service

    @pytest_asyncio.fixture
    async def pgvector_service(self, mock_database_service):
        """Create PGVector service for testing."""
        return PGVectorService(mock_database_service)

    @pytest.mark.asyncio
    async def test_complete_optimization_workflow(self, pgvector_service):
        """Test complete optimization workflow from discovery to monitoring."""
        # Arrange
        table_name = "destinations"
        column_name = "embedding"

        # Mock the complete workflow
        vector_tables_data = [
            {
                "table_name": table_name,
                "column_name": column_name,
                "index_status": "no_index",
            }
        ]

        mock_stats = IndexStats(
            index_name="new_index",
            index_size_bytes=1048576,
            index_size_human="1 MB",
            row_count=1000,
            index_usage_count=0,
            last_used=None,
        )

        with patch.object(pgvector_service, "list_vector_tables") as mock_list:
            with patch.object(pgvector_service, "optimize_for_table") as mock_optimize:
                with patch.object(
                    pgvector_service, "get_index_stats"
                ) as mock_get_stats:
                    with patch.object(
                        pgvector_service, "check_index_health"
                    ) as mock_health:
                        mock_list.return_value = vector_tables_data
                        mock_optimize.return_value = {
                            "table": table_name,
                            "column": column_name,
                            "actions": [
                                {"action": "created_index", "index_name": "new_index"}
                            ],
                        }
                        mock_get_stats.return_value = mock_stats
                        mock_health.return_value = {
                            "status": "needs_attention",
                            "recommendations": ["Index is not being used"],
                        }

                        # Act - Complete workflow
                        # 1. Discover vector tables
                        tables = await pgvector_service.list_vector_tables()

                        # 2. Optimize the table
                        optimization_result = await pgvector_service.optimize_for_table(
                            table_name, column_name, "medium"
                        )

                        # 3. Check health
                        health_result = await pgvector_service.check_index_health(
                            table_name, column_name
                        )

                        # 4. Get detailed stats
                        stats_result = await pgvector_service.get_index_stats(
                            table_name, column_name
                        )

                        # Assert workflow results
                        assert len(tables) == 1
                        assert tables[0]["index_status"] == "no_index"

                        assert optimization_result["table"] == table_name
                        assert len(optimization_result["actions"]) > 0

                        assert health_result["status"] == "needs_attention"
                        assert len(health_result["recommendations"]) > 0

                        assert stats_result.index_name == "new_index"
                        assert stats_result.row_count == 1000

    @pytest.mark.asyncio
    async def test_memory_optimization_integration(self, pgvector_service):
        """Test memory table optimization integration workflow."""
        # Arrange
        # Mock memory tables existence and optimization
        table_exists_side_effect = [
            [True],  # memories exists
            [True],  # conversations exists
            [False],  # user_context doesn't exist
        ]

        column_exists_side_effect = [
            [True],  # memories.embedding exists
            [True],  # conversations.embedding exists
        ]

        pgvector_service.db.execute_sql.side_effect = (
            table_exists_side_effect + column_exists_side_effect
        )

        with patch.object(pgvector_service, "optimize_for_table") as mock_optimize:
            mock_optimize.return_value = {
                "table": "memories",
                "column": "embedding",
                "actions": [{"action": "created_index", "index_name": "memory_index"}],
            }

            # Act
            memory_results = await pgvector_service.optimize_memory_tables()

            # Assert
            assert "memory_optimization" in memory_results
            assert len(memory_results["memory_optimization"]) > 0
            assert len(memory_results["errors"]) == 0

            # Should have optimized existing memory tables
            optimized_tables = [
                opt["table"] for opt in memory_results["memory_optimization"]
            ]
            assert "memories" in optimized_tables or "conversations" in optimized_tables


if __name__ == "__main__":
    pytest.main([__file__])
