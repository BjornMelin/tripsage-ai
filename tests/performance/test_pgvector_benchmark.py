"""
Tests for PGVector performance benchmark suite.

This test module validates the benchmark framework functionality including:
- Configuration validation
- Benchmark execution
- Metrics collection and calculation
- Regression detection
- Report generation
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# Skip the entire module if benchmark dependencies aren't available
pytest.importorskip("scipy")
pytest.importorskip("matplotlib")

from scripts.benchmarks.pgvector_benchmark import (
    BenchmarkConfig,
    BenchmarkResults,
    IndexCreationMetrics,
    MemoryProfileMetrics,
    PGVectorBenchmark,
    QueryPerformanceMetrics,
    run_benchmark,
)
from scripts.benchmarks.regression_detector import (
    BaselineManager,
    RegressionAnalysisResult,
    RegressionDetector,
    RegressionThresholds,
)


class TestBenchmarkConfig:
    """Test benchmark configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BenchmarkConfig()

        assert config.vector_dimensions == 384
        assert config.small_dataset_size == 1000
        assert config.medium_dataset_size == 10000
        assert config.large_dataset_size == 50000
        assert config.warmup_queries == 50
        assert config.benchmark_queries == 200
        assert config.target_query_latency_ms == 10.0
        assert config.target_performance_improvement_x == 30.0

        # Check post_init sets defaults
        assert config.ef_search_values is not None
        assert 40 in config.ef_search_values
        assert 100 in config.ef_search_values

    def test_config_customization(self):
        """Test configuration customization."""
        config = BenchmarkConfig(
            vector_dimensions=512,
            small_dataset_size=500,
            ef_search_values=[50, 150],
            target_query_latency_ms=5.0,
        )

        assert config.vector_dimensions == 512
        assert config.small_dataset_size == 500
        assert config.ef_search_values == [50, 150]
        assert config.target_query_latency_ms == 5.0


class TestPGVectorBenchmark:
    """Test PGVector benchmark execution."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service for testing."""
        service = AsyncMock()
        service.connect = AsyncMock()
        service.disconnect = AsyncMock()
        service.execute_sql = AsyncMock()
        return service

    @pytest.fixture
    def mock_pgvector_service(self):
        """Mock pgvector service for testing."""
        service = AsyncMock()
        service.create_hnsw_index = AsyncMock(return_value="test_index")
        service.set_query_quality = AsyncMock()

        # Mock index stats
        mock_stats = MagicMock()
        mock_stats.index_size_bytes = 1024 * 1024  # 1MB
        mock_stats.index_size_human = "1.0 MB"
        service.get_index_stats = AsyncMock(return_value=mock_stats)

        return service

    @pytest.fixture
    def temp_output_dir(self):
        """Temporary output directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_benchmark_initialization(self, temp_output_dir):
        """Test benchmark initialization."""
        config = BenchmarkConfig(output_directory=temp_output_dir)
        benchmark = PGVectorBenchmark(config)

        assert benchmark.config.output_directory == temp_output_dir
        assert Path(temp_output_dir).exists()
        assert benchmark.baseline_index_metrics == []
        assert benchmark.optimized_index_metrics == []

    @pytest.mark.asyncio
    async def test_setup_and_cleanup(self, mock_db_service, temp_output_dir):
        """Test benchmark setup and cleanup."""
        config = BenchmarkConfig(output_directory=temp_output_dir)
        benchmark = PGVectorBenchmark(config)

        # Mock the services
        with patch(
            "scripts.performance.pgvector_benchmark.DatabaseService",
            return_value=mock_db_service,
        ):
            with patch(
                "scripts.performance.pgvector_benchmark.PGVectorService"
            ) as mock_pgvector:
                mock_pgvector.return_value = AsyncMock()

                await benchmark.setup()
                assert benchmark.db_service is not None
                assert benchmark.pgvector_service is not None

                await benchmark.cleanup()
                mock_db_service.disconnect.assert_called_once()

    def test_memory_recording(self, temp_output_dir):
        """Test memory usage recording."""
        config = BenchmarkConfig(
            output_directory=temp_output_dir, enable_memory_profiling=True
        )
        benchmark = PGVectorBenchmark(config)

        # Record memory usage
        benchmark._record_memory_usage("test_phase")

        assert len(benchmark.memory_profile) == 1
        metric = benchmark.memory_profile[0]
        assert metric.test_phase == "test_phase"
        assert metric.rss_memory_mb > 0
        assert isinstance(metric.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_create_test_table(self, mock_db_service, temp_output_dir):
        """Test test table creation."""
        config = BenchmarkConfig(output_directory=temp_output_dir)
        benchmark = PGVectorBenchmark(config)
        benchmark.db_service = mock_db_service

        await benchmark._create_test_table("test_table", 100)

        # Verify table creation SQL was called
        assert mock_db_service.execute_sql.call_count >= 2  # DROP + CREATE + INSERTs

        # Check that DROP and CREATE were called
        calls = mock_db_service.execute_sql.call_args_list
        drop_call = str(calls[0][0][0])
        create_call = str(calls[1][0][0])

        assert "DROP TABLE IF EXISTS test_table" in drop_call
        assert "CREATE TABLE test_table" in create_call
        assert "VECTOR(384)" in create_call

    @pytest.mark.asyncio
    async def test_index_creation_benchmark(
        self, mock_db_service, mock_pgvector_service, temp_output_dir
    ):
        """Test index creation benchmarking."""
        config = BenchmarkConfig(
            output_directory=temp_output_dir,
            small_dataset_size=10,  # Very small for testing
            medium_dataset_size=20,
            large_dataset_size=30,
        )
        benchmark = PGVectorBenchmark(config)
        benchmark.db_service = mock_db_service
        benchmark.pgvector_service = mock_pgvector_service

        # Mock table creation to avoid actual data generation
        benchmark._create_test_table = AsyncMock()

        await benchmark.benchmark_index_creation()

        # Should have created baselines and optimized metrics
        assert len(benchmark.baseline_index_metrics) >= 3  # One per dataset size
        assert len(benchmark.optimized_index_metrics) > 0

        # Check metrics structure
        baseline_metric = benchmark.baseline_index_metrics[0]
        assert isinstance(baseline_metric, IndexCreationMetrics)
        assert baseline_metric.data_size in [10, 20, 30]
        assert baseline_metric.vector_dimensions == 384

    @pytest.mark.asyncio
    async def test_query_performance_benchmark(
        self, mock_db_service, mock_pgvector_service, temp_output_dir
    ):
        """Test query performance benchmarking."""
        config = BenchmarkConfig(
            output_directory=temp_output_dir,
            benchmark_queries=5,  # Small number for testing
            warmup_queries=2,
            ef_search_values=[40, 100],
        )
        benchmark = PGVectorBenchmark(config)
        benchmark.db_service = mock_db_service
        benchmark.pgvector_service = mock_pgvector_service

        # Mock query execution
        mock_results = [
            {"id": 1, "content": "test", "distance": 0.1},
            {"id": 2, "content": "test2", "distance": 0.2},
        ]
        benchmark._execute_similarity_query = AsyncMock(return_value=mock_results)

        await benchmark.benchmark_query_performance()

        # Should have baseline and optimized metrics
        assert len(benchmark.baseline_query_metrics) >= 1
        assert len(benchmark.optimized_query_metrics) >= 2  # Different ef_search values

        # Check metrics structure
        query_metric = benchmark.optimized_query_metrics[0]
        assert isinstance(query_metric, QueryPerformanceMetrics)
        assert query_metric.query_count == 5
        assert query_metric.success_rate > 0

    @pytest.mark.asyncio
    async def test_similarity_query_execution(self, mock_db_service, temp_output_dir):
        """Test similarity query execution."""
        config = BenchmarkConfig(output_directory=temp_output_dir)
        benchmark = PGVectorBenchmark(config)
        benchmark.db_service = mock_db_service

        # Mock database response
        mock_results = [
            {"id": 1, "content": "test", "distance": 0.1},
            {"id": 2, "content": "test2", "distance": 0.2},
        ]
        mock_db_service.execute_sql.return_value = [
            MagicMock(**result) for result in mock_results
        ]

        # Create test query vector
        query_vector = np.random.random(384)

        results = await benchmark._execute_similarity_query("test_table", query_vector)

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["content"] == "test"

        # Verify SQL was called with correct parameters
        mock_db_service.execute_sql.assert_called_once()
        sql_call = mock_db_service.execute_sql.call_args[0]
        assert "ORDER BY distance" in sql_call[0]
        assert "LIMIT 10" in sql_call[0]

    def test_performance_improvement_calculation(self, temp_output_dir):
        """Test performance improvement calculations."""
        config = BenchmarkConfig(output_directory=temp_output_dir)
        benchmark = PGVectorBenchmark(config)

        # Add sample metrics
        benchmark.baseline_query_metrics = [
            QueryPerformanceMetrics(
                test_name="baseline",
                ef_search=40,
                query_count=100,
                avg_latency_ms=100.0,  # High baseline latency
                p95_latency_ms=150.0,
                p99_latency_ms=200.0,
                min_latency_ms=50.0,
                max_latency_ms=300.0,
                queries_per_second=10.0,  # Low baseline QPS
                memory_usage_mb=500.0,
                success_rate=1.0,
                errors=[],
            )
        ]

        benchmark.optimized_query_metrics = [
            QueryPerformanceMetrics(
                test_name="optimized",
                ef_search=100,
                query_count=100,
                avg_latency_ms=5.0,  # Much better latency
                p95_latency_ms=8.0,
                p99_latency_ms=12.0,
                min_latency_ms=2.0,
                max_latency_ms=15.0,
                queries_per_second=200.0,  # Much better QPS
                memory_usage_mb=350.0,  # Lower memory
                success_rate=1.0,
                errors=[],
            )
        ]

        # Add memory profile for memory reduction calculation
        benchmark.memory_profile = [
            MemoryProfileMetrics(
                test_phase="baseline_test",
                timestamp=datetime.now(timezone.utc),
                rss_memory_mb=500.0,
                vms_memory_mb=600.0,
                memory_percent=50.0,
                available_memory_mb=4000.0,
            ),
            MemoryProfileMetrics(
                test_phase="optimized_test",
                timestamp=datetime.now(timezone.utc),
                rss_memory_mb=350.0,  # 30% reduction
                vms_memory_mb=420.0,
                memory_percent=35.0,
                available_memory_mb=4000.0,
            ),
        ]

        improvements, memory_reduction = benchmark._calculate_performance_improvements()

        # Check query performance improvement (100ms -> 5ms = 20x improvement)
        assert improvements["query_latency_improvement"] == 20.0

        # Check throughput improvement (10 -> 200 = 20x improvement)
        assert improvements["throughput_improvement"] == 20.0

        # Check memory reduction (500 -> 350 = 30% reduction)
        assert abs(memory_reduction - 0.3) < 0.01  # 30% reduction

    def test_performance_validation(self, temp_output_dir):
        """Test performance target validation."""
        config = BenchmarkConfig(
            output_directory=temp_output_dir,
            target_query_latency_ms=10.0,
            target_performance_improvement_x=30.0,
            target_memory_reduction_pct=25.0,
        )
        benchmark = PGVectorBenchmark(config)

        # Add optimized metrics that meet targets
        benchmark.optimized_query_metrics = [
            QueryPerformanceMetrics(
                test_name="optimized",
                ef_search=100,
                query_count=100,
                avg_latency_ms=8.0,  # Under 10ms target
                p95_latency_ms=12.0,
                p99_latency_ms=15.0,
                min_latency_ms=5.0,
                max_latency_ms=20.0,
                queries_per_second=200.0,
                memory_usage_mb=350.0,
                success_rate=1.0,
                errors=[],
            )
        ]

        improvements = {"query_latency_improvement": 35.0}  # Exceeds 30x target
        memory_reduction = 0.30  # Exceeds 25% target

        validation_results, regression_detected = (
            benchmark._validate_performance_targets(improvements, memory_reduction)
        )

        assert validation_results["query_latency_target"]  # 8ms < 10ms
        assert validation_results["performance_improvement_target"]  # 35x > 30x
        assert validation_results["memory_reduction_target"]  # 30% > 25%
        assert not regression_detected  # No regression

    def test_system_info_collection(self, temp_output_dir):
        """Test system information collection."""
        config = BenchmarkConfig(output_directory=temp_output_dir)
        benchmark = PGVectorBenchmark(config)

        system_info = benchmark._get_system_info()

        assert "platform" in system_info
        assert "cpu_count" in system_info
        assert "memory_total_gb" in system_info
        assert "python_version" in system_info
        assert "timestamp" in system_info

        assert system_info["cpu_count"] > 0
        assert system_info["memory_total_gb"] > 0


class TestBaselineManager:
    """Test baseline management functionality."""

    @pytest.fixture
    def temp_baseline_dir(self):
        """Temporary baseline directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_baseline_initialization(self, temp_baseline_dir):
        """Test baseline manager initialization."""
        manager = BaselineManager(temp_baseline_dir)

        assert manager.baseline_dir == Path(temp_baseline_dir)
        assert manager.baseline_dir.exists()

    def test_save_and_load_baseline(self, temp_baseline_dir):
        """Test saving and loading baselines."""
        manager = BaselineManager(temp_baseline_dir)

        # Save a baseline
        performance_data = {
            "avg_latency_ms": 5.0,
            "p95_latency_ms": 8.0,
            "queries_per_second": 200.0,
            "memory_usage_mb": 350.0,
            "success_rate": 1.0,
        }

        manager.save_baseline("test_benchmark", performance_data, "v1.0")

        # Load the baseline
        baseline = manager.get_latest_baseline("test_benchmark")

        assert baseline is not None
        assert baseline.test_version == "v1.0"
        assert baseline.avg_latency_ms == 5.0
        assert baseline.queries_per_second == 200.0
        assert baseline.memory_usage_mb == 350.0

    def test_no_baseline_available(self, temp_baseline_dir):
        """Test behavior when no baseline is available."""
        manager = BaselineManager(temp_baseline_dir)

        baseline = manager.get_latest_baseline("nonexistent_test")

        assert baseline is None

    def test_multiple_baselines(self, temp_baseline_dir):
        """Test handling multiple baselines."""
        manager = BaselineManager(temp_baseline_dir)

        # Save multiple baselines
        for i in range(3):
            performance_data = {
                "avg_latency_ms": 5.0 + i,
                "queries_per_second": 200.0 + i * 10,
                "memory_usage_mb": 350.0,
                "success_rate": 1.0,
            }
            manager.save_baseline("test_benchmark", performance_data, f"v1.{i}")

        # Get latest baseline
        baseline = manager.get_latest_baseline("test_benchmark")

        assert baseline.test_version == "v1.2"  # Latest version
        assert baseline.avg_latency_ms == 7.0  # 5.0 + 2
        assert baseline.queries_per_second == 220.0  # 200.0 + 2*10


class TestRegressionDetector:
    """Test regression detection functionality."""

    @pytest.fixture
    def temp_baseline_dir(self):
        """Temporary baseline directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def baseline_manager(self, temp_baseline_dir):
        """Baseline manager with test data."""
        manager = BaselineManager(temp_baseline_dir)

        # Add a baseline
        performance_data = {
            "avg_latency_ms": 10.0,
            "p95_latency_ms": 15.0,
            "queries_per_second": 100.0,
            "memory_usage_mb": 500.0,
            "success_rate": 1.0,
        }
        manager.save_baseline("test_benchmark", performance_data, "baseline")

        return manager

    def test_regression_detector_initialization(self, baseline_manager):
        """Test regression detector initialization."""
        detector = RegressionDetector(baseline_manager)

        assert detector.baseline_manager is baseline_manager
        assert isinstance(detector.thresholds, RegressionThresholds)

    def test_no_regression_detection(self, baseline_manager):
        """Test detection when no regression exists."""
        detector = RegressionDetector(baseline_manager)

        # Current results similar to baseline
        current_results = {
            "avg_latency_ms": 9.5,  # Slightly better
            "p95_latency_ms": 14.0,
            "queries_per_second": 105.0,  # Slightly better
            "memory_usage_mb": 480.0,  # Slightly better
            "success_rate": 1.0,
        }

        analysis = detector.analyze_performance("test_benchmark", current_results)

        assert isinstance(analysis, RegressionAnalysisResult)
        assert not analysis.overall_regression
        assert not analysis.latency_regression
        assert not analysis.throughput_regression
        assert not analysis.memory_regression
        assert analysis.severity == "none"

    def test_latency_regression_detection(self, baseline_manager):
        """Test detection of latency regression."""
        detector = RegressionDetector(baseline_manager)

        # Current results with significantly worse latency
        current_results = {
            "avg_latency_ms": 25.0,  # 150% increase (exceeds 20% threshold)
            "p95_latency_ms": 35.0,
            "queries_per_second": 100.0,  # Same throughput
            "memory_usage_mb": 500.0,  # Same memory
            "success_rate": 1.0,
        }

        analysis = detector.analyze_performance("test_benchmark", current_results)

        assert analysis.overall_regression
        assert analysis.latency_regression
        assert not analysis.throughput_regression
        assert not analysis.memory_regression
        assert analysis.latency_change_pct > 20.0  # Significant increase
        assert analysis.severity in ["medium", "high", "critical"]

    def test_throughput_regression_detection(self, baseline_manager):
        """Test detection of throughput regression."""
        detector = RegressionDetector(baseline_manager)

        # Current results with significantly worse throughput
        current_results = {
            "avg_latency_ms": 10.0,  # Same latency
            "p95_latency_ms": 15.0,
            "queries_per_second": 70.0,  # 30% decrease (exceeds 15% threshold)
            "memory_usage_mb": 500.0,  # Same memory
            "success_rate": 1.0,
        }

        analysis = detector.analyze_performance("test_benchmark", current_results)

        assert analysis.overall_regression
        assert not analysis.latency_regression
        assert analysis.throughput_regression
        assert not analysis.memory_regression
        assert analysis.throughput_change_pct < -15.0  # Significant decrease

    def test_memory_regression_detection(self, baseline_manager):
        """Test detection of memory regression."""
        detector = RegressionDetector(baseline_manager)

        # Current results with significantly higher memory usage
        current_results = {
            "avg_latency_ms": 10.0,  # Same latency
            "p95_latency_ms": 15.0,
            "queries_per_second": 100.0,  # Same throughput
            "memory_usage_mb": 650.0,  # 30% increase (exceeds 25% threshold)
            "success_rate": 1.0,
        }

        analysis = detector.analyze_performance("test_benchmark", current_results)

        assert analysis.overall_regression
        assert not analysis.latency_regression
        assert not analysis.throughput_regression
        assert analysis.memory_regression
        assert analysis.memory_change_pct > 25.0  # Significant increase

    def test_critical_regression_detection(self, baseline_manager):
        """Test detection of critical regression."""
        detector = RegressionDetector(baseline_manager)

        # Current results with critical degradation
        current_results = {
            "avg_latency_ms": 25.0,  # 150% increase - critical
            "p95_latency_ms": 40.0,
            "queries_per_second": 40.0,  # 60% decrease - critical
            "memory_usage_mb": 1200.0,  # 140% increase - critical
            "success_rate": 0.8,  # Some failures
        }

        analysis = detector.analyze_performance("test_benchmark", current_results)

        assert analysis.overall_regression
        assert analysis.severity == "critical"
        assert len(analysis.recommendations) > 0
        assert any("CRITICAL" in rec for rec in analysis.recommendations)

    def test_no_baseline_handling(self, temp_baseline_dir):
        """Test handling when no baseline exists."""
        manager = BaselineManager(temp_baseline_dir)
        detector = RegressionDetector(manager)

        current_results = {
            "avg_latency_ms": 10.0,
            "queries_per_second": 100.0,
            "memory_usage_mb": 500.0,
            "success_rate": 1.0,
        }

        analysis = detector.analyze_performance("new_test", current_results)

        assert not analysis.overall_regression
        assert "No baseline available" in analysis.recommendations[0]


@pytest.mark.asyncio
async def test_run_benchmark_integration():
    """Integration test for run_benchmark function."""

    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the database connections
        with patch(
            "scripts.performance.pgvector_benchmark.DatabaseService"
        ) as mock_db_class:
            with patch(
                "scripts.performance.pgvector_benchmark.PGVectorService"
            ) as mock_pgv_class:
                # Setup mocks
                mock_db = AsyncMock()
                mock_db.connect = AsyncMock()
                mock_db.disconnect = AsyncMock()
                mock_db.execute_sql = AsyncMock(return_value=[])
                mock_db_class.return_value = mock_db

                mock_pgv = AsyncMock()
                mock_pgv.create_hnsw_index = AsyncMock(return_value="test_index")
                mock_pgv.set_query_quality = AsyncMock()
                mock_pgv.get_index_stats = AsyncMock(return_value=None)
                mock_pgv_class.return_value = mock_pgv

                # Run quick benchmark
                results = await run_benchmark(
                    output_dir=temp_dir, quick_test=True, verbose=False
                )

                assert isinstance(results, BenchmarkResults)
                assert results.config is not None
                assert results.test_start_time is not None
                assert results.test_end_time is not None
                assert results.total_duration_seconds > 0

                # Check that output files were created
                output_path = Path(temp_dir)
                assert (output_path / "benchmark_raw_data.json").exists()
                assert (output_path / "benchmark_summary.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
