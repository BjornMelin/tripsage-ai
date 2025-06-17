"""
Comprehensive tests for the pgvector HNSW optimizer module.

Tests cover all optimization functionality including:
- HNSW parameter auto-tuning and validation
- halfvec compression and migration
- Parallel index building with progress monitoring
- Query optimization and performance analysis
- Integration with existing database service patterns
"""

import time
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.pgvector_optimizer import (
    DistanceFunction,
    HNSWParameters,
    IndexBuildProgress,
    OptimizationProfile,
    ParallelIndexConfig,
    PGVectorOptimizer,
    QueryOptimizationStats,
    VectorCompressionConfig,
    quick_optimize_table,
)


class TestHNSWParameters:
    """Test HNSW parameter validation and creation."""

    def test_valid_parameters(self):
        """Test creating HNSW parameters with valid values."""
        params = HNSWParameters(m=24, ef_construction=100, ef_search=150)
        assert params.m == 24
        assert params.ef_construction == 100
        assert params.ef_search == 150

    def test_default_parameters(self):
        """Test default parameter values."""
        params = HNSWParameters()
        assert params.m == 16
        assert params.ef_construction == 64
        assert params.ef_search == 40

    def test_invalid_m_parameter(self):
        """Test validation of m parameter range."""
        with pytest.raises(CoreValidationError) as exc_info:
            HNSWParameters(m=4)  # Below minimum
        assert "INVALID_HNSW_M_PARAMETER" in str(exc_info.value)

        with pytest.raises(CoreValidationError) as exc_info:
            HNSWParameters(m=50)  # Above maximum
        assert "INVALID_HNSW_M_PARAMETER" in str(exc_info.value)

    def test_invalid_ef_construction_parameter(self):
        """Test validation of ef_construction parameter range."""
        with pytest.raises(CoreValidationError) as exc_info:
            HNSWParameters(ef_construction=30)  # Below minimum
        assert "INVALID_HNSW_EF_CONSTRUCTION_PARAMETER" in str(exc_info.value)

        with pytest.raises(CoreValidationError) as exc_info:
            HNSWParameters(ef_construction=500)  # Above maximum
        assert "INVALID_HNSW_EF_CONSTRUCTION_PARAMETER" in str(exc_info.value)

    def test_invalid_ef_search_parameter(self):
        """Test validation of ef_search parameter range."""
        with pytest.raises(CoreValidationError) as exc_info:
            HNSWParameters(ef_search=5)  # Below minimum
        assert "INVALID_HNSW_EF_SEARCH_PARAMETER" in str(exc_info.value)

        with pytest.raises(CoreValidationError) as exc_info:
            HNSWParameters(ef_search=2000)  # Above maximum
        assert "INVALID_HNSW_EF_SEARCH_PARAMETER" in str(exc_info.value)


class TestVectorCompressionConfig:
    """Test vector compression configuration validation."""

    def test_valid_compression_config(self):
        """Test creating valid compression configuration."""
        config = VectorCompressionConfig(
            source_column="embedding",
            target_column="embedding_halfvec",
            dimensions=1536,
        )
        assert config.enable_compression is True
        assert config.source_column == "embedding"
        assert config.target_column == "embedding_halfvec"
        assert config.dimensions == 1536
        assert config.preserve_original is False

    def test_invalid_dimensions(self):
        """Test validation of vector dimensions."""
        with pytest.raises(ValidationError) as exc_info:
            VectorCompressionConfig(
                source_column="embedding",
                target_column="embedding_halfvec",
                dimensions=0,  # Invalid
            )
        assert "Dimensions must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            VectorCompressionConfig(
                source_column="embedding",
                target_column="embedding_halfvec",
                dimensions=5000,  # Above halfvec limit
            )
        assert "halfvec supports up to 4000 dimensions" in str(exc_info.value)


class TestParallelIndexConfig:
    """Test parallel index building configuration."""

    def test_valid_parallel_config(self):
        """Test creating valid parallel configuration."""
        config = ParallelIndexConfig(
            max_parallel_workers=8,
            maintenance_work_mem="2GB",
            enable_progress_monitoring=True,
        )
        assert config.max_parallel_workers == 8
        assert config.maintenance_work_mem == "2GB"
        assert config.enable_progress_monitoring is True

    def test_invalid_worker_count(self):
        """Test validation of parallel worker count."""
        with pytest.raises(ValidationError) as exc_info:
            ParallelIndexConfig(max_parallel_workers=0)
        assert "Must have at least 1 parallel worker" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ParallelIndexConfig(max_parallel_workers=100)
        assert "Maximum 64 parallel workers supported" in str(exc_info.value)


class TestIndexBuildProgress:
    """Test index build progress tracking."""

    def test_progress_creation(self):
        """Test creating progress tracker."""
        start_time = time.time()
        progress = IndexBuildProgress(
            index_name="test_idx",
            table_name="test_table",
            total_tuples=1000,
            tuples_done=250,
            progress_percent=25.0,
            phase="building",
            start_time=start_time,
        )
        assert progress.index_name == "test_idx"
        assert progress.progress_percent == 25.0
        assert progress.elapsed_time >= 0

    def test_progress_calculations(self):
        """Test progress calculation methods."""
        start_time = time.time() - 10  # 10 seconds ago
        estimated_completion = time.time() + 30  # 30 seconds from now

        progress = IndexBuildProgress(
            index_name="test_idx",
            table_name="test_table",
            total_tuples=1000,
            tuples_done=250,
            progress_percent=25.0,
            phase="building",
            start_time=start_time,
            estimated_completion=estimated_completion,
        )

        assert progress.elapsed_time >= 10
        assert progress.estimated_remaining is not None
        assert progress.estimated_remaining > 0


class TestQueryOptimizationStats:
    """Test query optimization statistics."""

    def test_stats_creation(self):
        """Test creating optimization statistics."""
        stats = QueryOptimizationStats(
            avg_query_time=15.5,
            index_hit_ratio=0.95,
            memory_usage_mb=128.0,
            cache_hit_ratio=0.85,
            total_queries=100,
            recall_score=0.98,
        )
        assert stats.avg_query_time == 15.5
        assert stats.index_hit_ratio == 0.95
        assert stats.recall_score == 0.98


class TestPGVectorOptimizer:
    """Test the main pgvector optimizer functionality."""

    @pytest.fixture
    def mock_database_service(self):
        """Create a mock database service."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.is_connected = True
        return mock_db

    @pytest.fixture
    def optimizer(self, mock_database_service):
        """Create a pgvector optimizer with mocked dependencies."""
        return PGVectorOptimizer(database_service=mock_database_service)

    def test_optimizer_initialization(self, mock_database_service):
        """Test optimizer initialization."""
        optimizer = PGVectorOptimizer(database_service=mock_database_service)
        assert optimizer.db == mock_database_service
        assert len(optimizer._optimization_profiles) == 5

    def test_optimization_profiles(self, optimizer):
        """Test predefined optimization profiles."""
        speed_profile = optimizer.get_optimization_profile(OptimizationProfile.SPEED)
        assert speed_profile.m == 16
        assert speed_profile.ef_construction == 64

        accuracy_profile = optimizer.get_optimization_profile(
            OptimizationProfile.ACCURACY
        )
        assert accuracy_profile.m == 32
        assert accuracy_profile.ef_construction == 200

    @pytest.mark.asyncio
    async def test_auto_tune_parameters_no_database(self):
        """Test auto-tuning without database service."""
        optimizer = PGVectorOptimizer(database_service=None)

        with pytest.raises(CoreServiceError) as exc_info:
            await optimizer.auto_tune_parameters("test_table", "embedding")
        assert "DATABASE_SERVICE_NOT_INITIALIZED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auto_tune_parameters_success(self, optimizer, mock_database_service):
        """Test successful parameter auto-tuning."""
        # Mock data analysis results
        mock_database_service.execute_sql.side_effect = [
            [{"dimensions": 1536}],  # Dimensions query
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],  # Distance stats
        ]
        mock_database_service.count.return_value = 50000  # Vector count

        params = await optimizer.auto_tune_parameters("test_table", "embedding")

        assert isinstance(params, HNSWParameters)
        assert 5 <= params.m <= 48
        assert 32 <= params.ef_construction <= 400
        assert 10 <= params.ef_search <= 1000

    @pytest.mark.asyncio
    async def test_auto_tune_parameters_high_recall(
        self, optimizer, mock_database_service
    ):
        """Test auto-tuning with high recall target."""
        # Mock data analysis results
        mock_database_service.execute_sql.side_effect = [
            [{"dimensions": 384}],  # Lower dimensions
            [
                {
                    "avg_distance": 0.5,
                    "distance_variance": 0.1,
                    "min_distance": 0.05,
                    "max_distance": 1.0,
                }
            ],
        ]
        mock_database_service.count.return_value = 10000

        params = await optimizer.auto_tune_parameters(
            "test_table", "embedding", target_recall=0.98
        )

        # High recall should result in higher ef_construction and ef_search
        assert params.ef_construction >= 64
        assert params.ef_search >= 100

    @pytest.mark.asyncio
    async def test_create_optimized_hnsw_index_success(
        self, optimizer, mock_database_service
    ):
        """Test successful HNSW index creation."""
        mock_database_service.execute_sql.return_value = []

        index_name = await optimizer.create_optimized_hnsw_index(
            table_name="test_table",
            vector_column="embedding",
            parameters=HNSWParameters(m=24, ef_construction=100, ef_search=150),
        )

        assert index_name == "test_table_embedding_l2_hnsw_idx"

        # Verify SQL calls were made
        assert mock_database_service.execute_sql.called
        calls = mock_database_service.execute_sql.call_args_list

        # Should have called configuration and index creation
        assert len(calls) >= 2

    @pytest.mark.asyncio
    async def test_create_hnsw_index_with_profile(
        self, optimizer, mock_database_service
    ):
        """Test creating HNSW index with optimization profile."""
        mock_database_service.execute_sql.return_value = []

        index_name = await optimizer.create_optimized_hnsw_index(
            table_name="test_table",
            vector_column="embedding",
            profile=OptimizationProfile.ACCURACY,
            distance_function=DistanceFunction.COSINE,
        )

        assert index_name == "test_table_embedding_cosine_hnsw_idx"

    @pytest.mark.asyncio
    async def test_create_hnsw_index_auto_tune(self, optimizer, mock_database_service):
        """Test creating HNSW index with auto-tuned parameters."""
        # Mock auto-tuning
        mock_database_service.execute_sql.side_effect = [
            [{"dimensions": 1536}],  # Auto-tune dimensions
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],  # Auto-tune stats
            [],  # Configuration calls
            [],
            [],
            [],
            [],  # Index creation
        ]
        mock_database_service.count.return_value = 50000

        index_name = await optimizer.create_optimized_hnsw_index(
            table_name="test_table",
            vector_column="embedding",
        )

        assert index_name == "test_table_embedding_l2_hnsw_idx"

    @pytest.mark.asyncio
    async def test_create_halfvec_compressed_column_success(
        self, optimizer, mock_database_service
    ):
        """Test successful halfvec compression."""
        mock_database_service.execute_sql.side_effect = [
            [],  # Add column
            [],  # Convert data
            [{"halfvec_size": 3076, "original_size_estimate": 6148}],  # Verification
        ]

        config = VectorCompressionConfig(
            source_column="embedding",
            target_column="embedding_halfvec",
            dimensions=1536,
        )

        result = await optimizer.create_halfvec_compressed_column(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_create_halfvec_in_place_conversion(
        self, optimizer, mock_database_service
    ):
        """Test in-place halfvec conversion."""
        mock_database_service.execute_sql.side_effect = [
            [],  # Add temp column
            [],  # Convert data
            [],  # Drop original
            [],  # Rename temp
            [{"halfvec_size": 3076, "original_size_estimate": 6148}],  # Verification
        ]

        config = VectorCompressionConfig(
            source_column="embedding",
            target_column="embedding",  # Same column = in-place
            dimensions=1536,
        )

        result = await optimizer.create_halfvec_compressed_column(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_optimize_query_performance(self, optimizer, mock_database_service):
        """Test query performance optimization."""
        # Mock EXPLAIN output
        mock_explain_result = [
            {
                "QUERY PLAN": [
                    {
                        "Execution Time": 15.5,
                        "Planning Time": 2.3,
                        "Shared Hit Blocks": 100,
                        "Shared Read Blocks": 20,
                    }
                ]
            }
        ]
        mock_database_service.execute_sql.side_effect = [
            [],  # Set ef_search
            mock_explain_result,  # EXPLAIN query
        ]

        stats = await optimizer.optimize_query_performance(
            table_name="test_table",
            vector_column="embedding",
            query_vector=[0.1] * 1536,
            ef_search=200,
        )

        assert isinstance(stats, QueryOptimizationStats)
        assert stats.avg_query_time == 17.8  # execution + planning
        assert stats.index_hit_ratio >= 0.0
        assert stats.memory_usage_mb >= 0.0

    @pytest.mark.asyncio
    async def test_get_optimization_recommendations(
        self, optimizer, mock_database_service
    ):
        """Test generating optimization recommendations."""
        # Mock current index analysis
        mock_database_service.execute_sql.side_effect = [
            [],  # Index analysis
            [{"dimensions": 1536}],  # Data analysis - dimensions
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],  # Data analysis - stats
        ]
        mock_database_service.count.return_value = 100000

        recommendations = await optimizer.get_optimization_recommendations(
            "test_table", "embedding"
        )

        assert "table" in recommendations
        assert "column" in recommendations
        assert "suggestions" in recommendations
        assert recommendations["table"] == "test_table"
        assert recommendations["column"] == "embedding"
        assert isinstance(recommendations["suggestions"], list)

    @pytest.mark.asyncio
    async def test_benchmark_configurations(self, optimizer, mock_database_service):
        """Test benchmarking different HNSW configurations."""
        # Use AsyncMock with infinite responses to avoid StopIteration
        mock_database_service.execute_sql.return_value = []

        # Mock specific responses for size queries
        def side_effect_func(*args, **kwargs):
            sql = args[0] if args else ""
            if "pg_relation_size" in sql:
                # Return size information
                return [{"index_size": "10 MB", "index_size_bytes": 10485760}]
            return []

        mock_database_service.execute_sql.side_effect = side_effect_func

        configurations = [
            HNSWParameters(m=16, ef_construction=64, ef_search=40),
        ]

        test_queries = [
            [0.1] * 1536,
        ]

        results = await optimizer.benchmark_configurations(
            "test_table", "embedding", test_queries, configurations
        )

        assert len(results) == 1
        result = results[0]
        assert "configuration" in result
        assert "avg_query_time_ms" in result
        assert "queries_per_second" in result
        assert "index_size" in result
        assert result["configuration"]["m"] == 16

    def test_distance_function_operators(self, optimizer):
        """Test distance function operator mapping."""
        assert optimizer._get_distance_operator(DistanceFunction.L2) == "<->"
        assert optimizer._get_distance_operator(DistanceFunction.COSINE) == "<=>"
        assert optimizer._get_distance_operator(DistanceFunction.IP) == "<#>"

    def test_vector_type_mapping(self, optimizer):
        """Test vector type mapping for distance functions."""
        assert optimizer._get_vector_type(DistanceFunction.L2) == "vector"
        assert optimizer._get_vector_type(DistanceFunction.HALFVEC_L2) == "halfvec"
        assert optimizer._get_vector_type(DistanceFunction.HALFVEC_COSINE) == "halfvec"

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, optimizer, mock_database_service):
        """Test resource cleanup."""
        mock_database_service.execute_sql.return_value = []

        await optimizer.cleanup_resources()

        # Verify cleanup SQL calls
        calls = mock_database_service.execute_sql.call_args_list
        assert len(calls) >= 3  # At least 3 RESET calls


class TestUtilityFunctions:
    """Test utility functions for common optimization tasks."""

    @pytest.mark.asyncio
    async def test_quick_optimize_table_success(self):
        """Test quick table optimization with all features."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.is_connected = True

        # Mock data analysis
        mock_db.execute_sql.side_effect = [
            # Auto-tune parameters
            [{"dimensions": 1536}],
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],
            # Index creation
            [],  # Configure parallel
            [],  # Set workers
            [],  # Set memory
            [],  # Set checkpoint
            [],  # Set maintenance workers
            [],  # Create index
            [],  # Set ef_search
            # Compression
            [],  # Add halfvec column
            [],  # Convert data
            [{"halfvec_size": 3076, "original_size_estimate": 6148}],  # Verification
            # Recommendations
            [],  # Index analysis
            [{"dimensions": 1536}],  # Data analysis
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],
            # Cleanup
            [],  # Reset ef_search
            [],  # Reset workers
            [],  # Reset memory
        ]
        mock_db.count.side_effect = [50000, 50000]  # Vector counts

        results = await quick_optimize_table(
            table_name="test_table",
            vector_column="embedding",
            profile=OptimizationProfile.BALANCED,
            enable_compression=True,
            database_service=mock_db,
        )

        assert results["table"] == "test_table"
        assert results["column"] == "embedding"
        assert len(results["optimizations"]) >= 1
        assert "additional_recommendations" in results

    @pytest.mark.asyncio
    async def test_quick_optimize_table_no_compression(self):
        """Test quick optimization without compression."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.is_connected = True

        # Mock minimal calls for index creation only
        mock_db.execute_sql.side_effect = [
            # Auto-tune
            [{"dimensions": 1536}],
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],
            # Index creation
            [],  # Configure parallel
            [],  # Set workers
            [],  # Set memory
            [],  # Set checkpoint
            [],  # Set maintenance workers
            [],  # Create index
            [],  # Set ef_search
            # Recommendations
            [],  # Index analysis
            [{"dimensions": 1536}],  # Data analysis
            [
                {
                    "avg_distance": 0.8,
                    "distance_variance": 0.2,
                    "min_distance": 0.1,
                    "max_distance": 1.5,
                }
            ],
            # Cleanup
            [],  # Reset ef_search
            [],  # Reset workers
            [],  # Reset memory
        ]
        mock_db.count.side_effect = [50000, 50000]

        results = await quick_optimize_table(
            table_name="test_table",
            vector_column="embedding",
            enable_compression=False,
            database_service=mock_db,
        )

        assert len(results["optimizations"]) == 1  # Only index creation
        assert results["optimizations"][0]["type"] == "hnsw_index"


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_database_error_propagation(self):
        """Test that database errors are properly propagated."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.execute_sql.side_effect = Exception("Database connection failed")

        optimizer = PGVectorOptimizer(database_service=mock_db)

        with pytest.raises(CoreDatabaseError) as exc_info:
            await optimizer.auto_tune_parameters("test_table", "embedding")

        assert "HNSW_AUTO_TUNE_FAILED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_index_creation_failure(self):
        """Test handling of index creation failures."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.execute_sql.side_effect = Exception("Index creation failed")

        optimizer = PGVectorOptimizer(database_service=mock_db)

        with pytest.raises(CoreDatabaseError) as exc_info:
            await optimizer.create_optimized_hnsw_index(
                "test_table", "embedding", parameters=HNSWParameters()
            )

        assert "HNSW_INDEX_CREATION_FAILED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_compression_failure(self):
        """Test handling of compression failures."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.execute_sql.side_effect = Exception("Column creation failed")

        optimizer = PGVectorOptimizer(database_service=mock_db)

        config = VectorCompressionConfig(
            source_column="embedding",
            target_column="embedding_halfvec",
            dimensions=1536,
        )

        with pytest.raises(CoreDatabaseError) as exc_info:
            await optimizer.create_halfvec_compressed_column(config)

        assert "HALFVEC_COMPRESSION_FAILED" in str(exc_info.value)


class TestIntegration:
    """Integration tests with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_memory_optimization_workflow(self):
        """Test complete memory optimization workflow."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.is_connected = True

        # Simulate a large dataset that would benefit from optimization
        mock_db.count.return_value = 1000000  # 1M vectors
        mock_db.execute_sql.side_effect = [
            [{"dimensions": 1536}],  # Large dimensions
            [
                {
                    "avg_distance": 1.2,
                    "distance_variance": 0.8,
                    "min_distance": 0.1,
                    "max_distance": 2.0,
                }
            ],  # High variance
        ]

        optimizer = PGVectorOptimizer(database_service=mock_db)

        # Auto-tune should recommend higher parameters for large, high-variance dataset
        params = await optimizer.auto_tune_parameters("large_table", "embedding")

        # For large dataset with high variance, expect higher parameters
        assert params.m >= 20  # Higher m for large datasets
        assert params.ef_construction >= 120  # Higher ef_construction for accuracy
        assert params.ef_search >= 100  # Higher ef_search for quality

    @pytest.mark.asyncio
    async def test_small_dataset_optimization(self):
        """Test optimization for small datasets."""
        mock_db = AsyncMock(spec=DatabaseService)
        mock_db.is_connected = True

        # Small dataset
        mock_db.count.return_value = 5000
        mock_db.execute_sql.side_effect = [
            [{"dimensions": 384}],  # Smaller dimensions
            [
                {
                    "avg_distance": 0.6,
                    "distance_variance": 0.1,
                    "min_distance": 0.05,
                    "max_distance": 1.0,
                }
            ],  # Low variance
        ]

        optimizer = PGVectorOptimizer(database_service=mock_db)
        params = await optimizer.auto_tune_parameters("small_table", "embedding")

        # For small dataset, expect more conservative parameters
        assert params.ef_construction >= 64  # Minimum for small datasets
        assert params.ef_search >= 40  # Reasonable for small datasets
