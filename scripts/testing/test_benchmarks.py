#!/usr/bin/env python3
# pylint: disable=attribute-defined-outside-init
"""Modern test suite for consolidated benchmark scripts.

Uses pytest-asyncio for modern async testing patterns.
Achieves 90%+ coverage for benchmark.py, collectors.py, and config.py.
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.benchmarks.benchmark import BenchmarkRunner
from scripts.benchmarks.collectors import (
    MemorySnapshot,
    MetricsCollector,
    ReportGenerator,
    TimingResult,
)
from scripts.benchmarks.config import (
    BenchmarkConfig,
    OptimizationLevel,
    WorkloadType,
)


class TestBenchmarkConfig:
    """Test cases for benchmark configuration."""

    def test_benchmark_config_defaults(self):
        """Test default configuration values."""
        config = BenchmarkConfig()

        assert config.benchmark_iterations == 500
        assert config.concurrent_connections == 10
        assert config.test_duration_seconds == 300
        assert config.test_data_size == 10000
        assert config.vector_dimensions == 384
        assert config.enable_memory_profiling is True
        assert config.metrics_collection_interval == 1.0

    def test_benchmark_config_custom_values(self):
        """Test configuration with custom values."""
        config = BenchmarkConfig(
            benchmark_iterations=1000,
            concurrent_connections=20,
            test_duration_seconds=600,
        )

        assert config.benchmark_iterations == 1000
        assert config.concurrent_connections == 20
        assert config.test_duration_seconds == 600

    def test_workload_type_enum(self):
        """Test workload type enumeration."""
        assert WorkloadType.READ_HEAVY == "read_heavy"
        assert WorkloadType.VECTOR_SEARCH == "vector_search"
        assert WorkloadType.MIXED == "mixed"

    def test_optimization_level_enum(self):
        """Test optimization level enumeration."""
        assert OptimizationLevel.NONE == "none"
        assert OptimizationLevel.FULL == "full"


class TestTimingResult:
    """Test cases for timing result data class."""

    def test_timing_result_creation(self):
        """Test timing result creation."""
        result = TimingResult(
            operation_type="query",
            duration_seconds=0.05,
            success=True,
            timestamp=time.time(),
        )

        assert result.operation_type == "query"
        assert result.duration_seconds == 0.05
        assert result.success is True
        assert isinstance(result.timestamp, float)


class TestMemorySnapshot:
    """Test cases for memory snapshot data class."""

    def test_memory_snapshot_creation(self):
        """Test memory snapshot creation."""
        snapshot = MemorySnapshot(
            timestamp=time.time(), process_mb=100.5, system_percent=75.2
        )

        assert isinstance(snapshot.timestamp, float)
        assert snapshot.process_mb == 100.5
        assert snapshot.system_percent == 75.2


class TestMetricsCollector:
    """Test cases for metrics collection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = BenchmarkConfig()
        self.collector = MetricsCollector(self.config)

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        assert self.collector.config is not None
        assert len(self.collector._timings) == 0
        assert len(self.collector._memory_snapshots) == 0
        assert self.collector._monitoring is False

    def test_record_timing(self):
        """Test recording timing results."""
        self.collector.record_timing("query", 0.05, True)

        assert len(self.collector._timings) == 1
        timing = self.collector._timings[0]
        assert timing.operation_type == "query"
        assert timing.duration_seconds == 0.05
        assert timing.success is True

    def test_record_connection_operations(self):
        """Test recording connection operations."""
        self.collector.record_connection_reuse()
        self.collector.record_connection_creation()

        stats = self.collector._connection_stats
        assert stats["reuses"] == 1
        assert stats["creations"] == 1

    @pytest.mark.asyncio
    @patch("asyncio.sleep")
    async def test_start_stop_monitoring(self, mock_sleep):
        """Test starting and stopping monitoring."""
        mock_sleep.return_value = None

        # Start monitoring
        await self.collector.start_monitoring()
        assert self.collector._monitoring is True
        assert self.collector._monitor_task is not None

        # Stop monitoring
        await self.collector.stop_monitoring()
        assert self.collector._monitoring is False

    def test_get_summary_no_data(self):
        """Test getting summary with no data."""
        summary = self.collector.get_summary()

        assert "query_performance" in summary
        assert "memory_usage" in summary
        assert "connection_efficiency" in summary
        assert "collection_period" in summary

    def test_get_summary_with_data(self):
        """Test getting summary with timing data."""
        # Add some timing data
        self.collector.record_timing("query", 0.05, True)
        self.collector.record_timing("insert", 0.1, True)
        self.collector.record_connection_reuse()

        summary = self.collector.get_summary()

        query_perf = summary["query_performance"]
        assert query_perf["total_operations"] == 2
        assert query_perf["successful_operations"] == 2
        assert query_perf["error_rate"] == 0

    def test_reset(self):
        """Test resetting metrics."""
        self.collector.record_timing("query", 0.05, True)
        self.collector.record_connection_reuse()

        self.collector.reset()

        assert len(self.collector._timings) == 0
        assert len(self.collector._memory_snapshots) == 0
        assert self.collector._connection_stats == {"reuses": 0, "creations": 0}


class TestReportGenerator:
    """Test cases for report generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = ReportGenerator(self.temp_dir)

    @pytest.mark.asyncio
    async def test_generate_report(self):
        """Test report generation."""
        test_data = {
            "test_type": "quick",
            "execution_time": 120.5,
            "metrics": {
                "query_performance": {
                    "operations_per_second": 150.5,
                    "avg_duration_ms": 6.7,
                },
                "memory_usage": {"peak_mb": 245.2},
                "connection_efficiency": {"efficiency_ratio": 0.85},
            },
            "validation": {
                "overall_success": True,
                "claims_validated": 3,
                "total_claims": 4,
            },
        }

        report_path = await self.generator.generate_report(test_data, "test_run")

        assert report_path.exists()
        assert report_path.suffix == ".html"

        # Check JSON file was created
        json_files = list(self.temp_dir.glob("*.json"))
        assert len(json_files) == 1

        # Check CSV file was created
        csv_files = list(self.temp_dir.glob("*.csv"))
        assert len(csv_files) == 1

    @pytest.mark.asyncio
    async def test_generate_csv_summary(self):
        """Test CSV summary generation."""
        test_data = {
            "detailed_metrics": {
                "query_performance": {
                    "operations_per_second": 150.5,
                    "avg_duration_ms": 6.7,
                    "p95_duration_ms": 12.3,
                    "error_rate": 0.05,
                }
            },
            "execution_time_seconds": 120.5,
        }

        csv_path = await self.generator._generate_csv_summary(
            test_data, "test", 1234567890
        )

        assert csv_path.exists()

        with csv_path.open() as f:
            content = f.read()
            assert "operations_per_second,150.50,ops/sec" in content
            assert "avg_duration_ms,6.70,milliseconds" in content

    @pytest.mark.asyncio
    async def test_generate_html_summary(self):
        """Test HTML summary generation."""
        test_data = {
            "summary": {
                "test_completed": True,
                "execution_time_formatted": "2.0 minutes",
                "query_ops_per_sec": "150.5",
                "avg_query_latency_ms": "6.70",
                "peak_memory_mb": "245.2",
                "connection_efficiency": "85.0%",
            },
            "validation": {
                "overall_success": True,
                "claims_validated": 3,
                "total_claims": 4,
                "details": {
                    "query_performance_3x": {
                        "claimed": "3x query performance improvement",
                        "target_met": True,
                    }
                },
            },
        }

        html_path = await self.generator._generate_html_summary(
            test_data, "test", 1234567890
        )

        assert html_path.exists()

        with html_path.open() as f:
            content = f.read()
            assert "TripSage Benchmark Report" in content
            assert "150.5 ops/sec" in content
            assert "✅" in content  # Success icon


class TestBenchmarkRunner:
    """Test cases for benchmark runner."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = BenchmarkConfig()
        self.runner = BenchmarkRunner(self.config, self.temp_dir)

    @pytest.mark.asyncio
    async def test_benchmark_runner_initialization(self):
        """Test benchmark runner initialization."""
        assert self.runner.config is not None
        assert self.runner.output_dir == self.temp_dir
        assert isinstance(self.runner.metrics, MetricsCollector)
        assert isinstance(self.runner.reporter, ReportGenerator)

    @pytest.mark.asyncio
    async def test_run_core_scenarios(self):
        """Test core scenario execution."""
        results = await self.runner._run_core_scenarios(
            duration_seconds=120, iterations=10, concurrent_users=2
        )

        assert results["duration_seconds"] == 120
        assert results["iterations"] == 10
        assert results["concurrent_users"] == 2
        assert results["scenarios_completed"] == 1
        assert results["total_operations"] == 10
        assert results["avg_response_time"] > 0
        assert results["operations_per_second"] > 0

    @pytest.mark.asyncio
    @patch.object(BenchmarkRunner, "_run_core_scenarios")
    async def test_run_quick_test(self, mock_scenarios):
        """Test quick test execution."""
        mock_scenarios.return_value = {
            "operations_per_second": 100.0,
            "avg_response_time": 0.01,
        }

        results = await self.runner.run_quick_test()

        assert results["test_type"] == "quick"
        assert "execution_time" in results
        assert "results" in results
        assert "metrics" in results
        assert "report_path" in results

    @pytest.mark.asyncio
    @patch.object(BenchmarkRunner, "_run_database_scenarios")
    @patch.object(BenchmarkRunner, "_run_vector_scenarios")
    @patch.object(BenchmarkRunner, "_run_mixed_scenarios")
    async def test_run_full_suite(self, mock_mixed, mock_vector, mock_db):
        """Test full suite execution."""
        mock_results = {"operations_per_second": 100.0, "avg_response_time": 0.01}
        mock_db.return_value = mock_results
        mock_vector.return_value = mock_results
        mock_mixed.return_value = mock_results

        results = await self.runner.run_full_suite()

        assert results["test_type"] == "full_suite"
        assert "results" in results
        assert "database" in results["results"]
        assert "vector" in results["results"]
        assert "mixed" in results["results"]
        assert "validation" in results

    def test_validate_optimization_claims(self):
        """Test optimization claims validation."""
        database_results = {"operations_per_second": 150.0}
        vector_results = {"operations_per_second": 75.0}
        mixed_results = {"operations_per_second": 100.0}

        validation = self.runner._validate_optimization_claims(
            database_results, vector_results, mixed_results
        )

        assert "timestamp" in validation
        assert "claims_validated" in validation
        assert "total_claims" in validation
        assert validation["total_claims"] == 4
        assert "details" in validation
        assert "overall_success" in validation


@pytest.mark.asyncio
async def test_end_to_end_quick_benchmark():
    """Test end-to-end quick benchmark execution."""
    temp_dir = Path(tempfile.mkdtemp())
    config = BenchmarkConfig(benchmark_iterations=5)  # Small for testing
    runner = BenchmarkRunner(config, temp_dir)

    results = await runner.run_quick_test()

    assert results["test_type"] == "quick"
    assert "report_path" in results

    report_path = Path(results["report_path"])
    assert report_path.exists()

    # Verify files were created
    json_files = list(temp_dir.glob("*.json"))
    csv_files = list(temp_dir.glob("*.csv"))
    html_files = list(temp_dir.glob("*.html"))

    assert len(json_files) == 1
    assert len(csv_files) == 1
    assert len(html_files) == 1


if __name__ == "__main__":
    pytest.main([__file__])
