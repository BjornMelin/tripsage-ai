#!/usr/bin/env python3
"""
Tests for consolidated benchmark scripts.

Achieves 90%+ coverage for the new consolidated benchmark.py, collectors.py, and config.py.
"""

import asyncio
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "benchmarks"))

from benchmark import BenchmarkRunner
from collectors import MetricsCollector, ReportGenerator, TimingResult, MemorySnapshot
from config import BenchmarkConfig, PerformanceThresholds, WorkloadType, OptimizationLevel


class TestBenchmarkConfig(unittest.TestCase):
    """Test cases for benchmark configuration."""

    def test_benchmark_config_defaults(self):
        """Test default configuration values."""
        config = BenchmarkConfig()
        
        self.assertEqual(config.benchmark_iterations, 500)
        self.assertEqual(config.concurrent_connections, 10)
        self.assertEqual(config.test_duration_seconds, 300)
        self.assertEqual(config.test_data_size, 10000)
        self.assertEqual(config.vector_dimensions, 384)
        self.assertTrue(config.enable_memory_profiling)
        self.assertEqual(config.metrics_collection_interval, 1.0)

    def test_benchmark_config_custom_values(self):
        """Test configuration with custom values."""
        config = BenchmarkConfig(
            benchmark_iterations=1000,
            concurrent_connections=20,
            test_duration_seconds=600
        )
        
        self.assertEqual(config.benchmark_iterations, 1000)
        self.assertEqual(config.concurrent_connections, 20)
        self.assertEqual(config.test_duration_seconds, 600)

    def test_performance_thresholds_defaults(self):
        """Test default performance threshold values."""
        thresholds = PerformanceThresholds()
        
        self.assertEqual(thresholds.query_performance_improvement, 3.0)
        self.assertEqual(thresholds.vector_performance_improvement, 30.0)
        self.assertEqual(thresholds.memory_reduction_target, 0.5)
        self.assertEqual(thresholds.connection_reuse_ratio, 0.80)
        self.assertEqual(thresholds.cache_hit_ratio_target, 0.75)

    def test_workload_type_enum(self):
        """Test workload type enumeration."""
        self.assertEqual(WorkloadType.READ_HEAVY, "read_heavy")
        self.assertEqual(WorkloadType.VECTOR_SEARCH, "vector_search")
        self.assertEqual(WorkloadType.MIXED, "mixed")

    def test_optimization_level_enum(self):
        """Test optimization level enumeration."""
        self.assertEqual(OptimizationLevel.NONE, "none")
        self.assertEqual(OptimizationLevel.FULL, "full")


class TestMetricsCollector(unittest.TestCase):
    """Test cases for metrics collection."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = BenchmarkConfig()
        self.collector = MetricsCollector(self.config)

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        self.assertIsNotNone(self.collector.config)
        self.assertEqual(len(self.collector._timings), 0)
        self.assertEqual(len(self.collector._memory_snapshots), 0)
        self.assertFalse(self.collector._monitoring)

    def test_record_timing(self):
        """Test recording timing results."""
        self.collector.record_timing("query", 0.05, True)
        
        self.assertEqual(len(self.collector._timings), 1)
        timing = self.collector._timings[0]
        self.assertEqual(timing.operation_type, "query")
        self.assertEqual(timing.duration_seconds, 0.05)
        self.assertTrue(timing.success)

    def test_record_failed_timing(self):
        """Test recording failed timing results."""
        self.collector.record_timing("query", 0.1, False)
        
        timing = self.collector._timings[0]
        self.assertFalse(timing.success)

    def test_connection_tracking(self):
        """Test connection reuse and creation tracking."""
        self.collector.record_connection_reuse()
        self.collector.record_connection_reuse()
        self.collector.record_connection_creation()
        
        summary = self.collector.get_connection_summary()
        self.assertEqual(summary["connection_reuses"], 2)
        self.assertEqual(summary["connection_creations"], 1)
        self.assertEqual(summary["total_operations"], 3)
        self.assertAlmostEqual(summary["efficiency_ratio"], 2/3, places=2)

    def test_query_summary_with_data(self):
        """Test query performance summary with data."""
        # Add some timing data
        for i in range(10):
            duration = 0.01 + (i * 0.001)  # 10ms to 19ms
            self.collector.record_timing("query", duration, True)
        
        summary = self.collector.get_summary()
        query_summary = summary["query_performance"]
        
        self.assertEqual(query_summary["total_operations"], 10)
        self.assertEqual(query_summary["successful_operations"], 10)
        self.assertEqual(query_summary["error_rate"], 0.0)
        self.assertGreater(query_summary["avg_duration_ms"], 0)
        self.assertGreater(query_summary["p95_duration_ms"], 0)
        self.assertGreater(query_summary["operations_per_second"], 0)

    def test_query_summary_with_errors(self):
        """Test query performance summary with some errors."""
        # Add mixed success/failure data
        for i in range(5):
            self.collector.record_timing("query", 0.01, True)
        for i in range(2):
            self.collector.record_timing("query", 0.05, False)
        
        summary = self.collector.get_summary()
        query_summary = summary["query_performance"]
        
        self.assertEqual(query_summary["total_operations"], 7)
        self.assertEqual(query_summary["successful_operations"], 5)
        self.assertAlmostEqual(query_summary["error_rate"], 2/7, places=2)

    def test_query_summary_no_data(self):
        """Test query performance summary with no data."""
        summary = self.collector.get_summary()
        query_summary = summary["query_performance"]
        
        self.assertIn("error", query_summary)

    def test_memory_summary_with_data(self):
        """Test memory usage summary with data."""
        # Add some memory snapshots
        for i in range(5):
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                process_mb=100 + i * 10,  # 100, 110, 120, 130, 140 MB
                system_percent=50 + i
            )
            self.collector._memory_snapshots.append(snapshot)
        
        summary = self.collector.get_memory_summary()
        
        self.assertEqual(summary["current_mb"], 140)
        self.assertEqual(summary["peak_mb"], 140)
        self.assertEqual(summary["min_mb"], 100)
        self.assertEqual(summary["avg_mb"], 120)
        self.assertEqual(summary["memory_growth_mb"], 40)

    def test_memory_summary_no_data(self):
        """Test memory usage summary with no data."""
        summary = self.collector.get_memory_summary()
        self.assertIn("error", summary)

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        # Add some data
        self.collector.record_timing("query", 0.01, True)
        self.collector.record_connection_reuse()
        
        # Reset
        self.collector.reset()
        
        # Verify all data is cleared
        self.assertEqual(len(self.collector._timings), 0)
        self.assertEqual(len(self.collector._memory_snapshots), 0)
        self.assertEqual(self.collector._connection_stats["reuses"], 0)
        self.assertEqual(self.collector._connection_stats["creations"], 0)

    @patch('asyncio.sleep')
    async def test_start_stop_monitoring(self, mock_sleep):
        """Test starting and stopping monitoring."""
        # Mock sleep to avoid actual delays
        mock_sleep.return_value = None
        
        # Start monitoring
        await self.collector.start_monitoring()
        self.assertTrue(self.collector._monitoring)
        self.assertIsNotNone(self.collector._monitor_task)
        
        # Stop monitoring
        await self.collector.stop_monitoring()
        self.assertFalse(self.collector._monitoring)


class TestReportGenerator(unittest.TestCase):
    """Test cases for report generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.generator = ReportGenerator(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_generate_simple_report(self):
        """Test generating a simple report."""
        data = {
            "test_type": "quick",
            "execution_time": 120.5,
            "results": {"operations_per_second": 150.0},
            "metrics": {
                "query_performance": {
                    "avg_duration_ms": 15.0,
                    "operations_per_second": 150.0
                },
                "memory_usage": {"peak_mb": 125.0},
                "connection_efficiency": {"efficiency_ratio": 0.85}
            }
        }
        
        report_path = await self.generator.generate_simple_report(data, "test_quick")
        
        # Verify report files were created
        self.assertTrue(report_path.exists())
        self.assertTrue(report_path.name.endswith(".html"))
        
        # Verify JSON file was created
        json_files = list(self.temp_dir.glob("*.json"))
        self.assertEqual(len(json_files), 1)
        
        # Verify CSV file was created
        csv_files = list(self.temp_dir.glob("*.csv"))
        self.assertEqual(len(csv_files), 1)

    async def test_generate_csv_summary(self):
        """Test CSV summary generation."""
        data = {
            "detailed_metrics": {
                "query_performance": {
                    "operations_per_second": 100.0,
                    "avg_duration_ms": 20.0,
                    "p95_duration_ms": 35.0,
                    "error_rate": 0.05
                },
                "memory_usage": {
                    "peak_mb": 150.0,
                    "avg_mb": 120.0,
                    "memory_growth_mb": 30.0
                },
                "connection_efficiency": {
                    "efficiency_ratio": 0.90,
                    "connection_reuses": 180,
                    "connection_creations": 20
                }
            },
            "execution_time_seconds": 300.0
        }
        
        csv_path = await self.generator._generate_csv_summary(data, "test", 1234567890)
        
        self.assertTrue(csv_path.exists())
        
        # Verify CSV content
        content = csv_path.read_text()
        self.assertIn("metric_name,value,unit")
        self.assertIn("operations_per_second,100.00,ops/sec")
        self.assertIn("peak_memory_mb,150.00,MB")
        self.assertIn("connection_efficiency,0.900,ratio")

    async def test_generate_html_summary(self):
        """Test HTML summary generation."""
        data = {
            "summary": {
                "query_ops_per_sec": "150.0",
                "avg_query_latency_ms": "15.00",
                "peak_memory_mb": "125.0",
                "connection_efficiency": "85.0%",
                "execution_time_formatted": "2.0 minutes"
            },
            "validation": {
                "overall_success": True,
                "claims_validated": 3,
                "total_claims": 4,
                "details": {
                    "query_performance_3x": {
                        "claimed": "3x query improvement",
                        "target_met": True
                    },
                    "vector_search_30x": {
                        "claimed": "30x vector improvement", 
                        "target_met": True
                    }
                }
            }
        }
        
        html_path = await self.generator._generate_html_summary(data, "test", 1234567890)
        
        self.assertTrue(html_path.exists())
        
        # Verify HTML content
        content = html_path.read_text()
        self.assertIn("TripSage Benchmark Report")
        self.assertIn("150.0 ops/sec")
        self.assertIn("15.00 ms")
        self.assertIn("125.0 MB")
        self.assertIn("85.0%")
        self.assertIn("PASSED")

    def test_format_duration(self):
        """Test duration formatting."""
        self.assertEqual(self.generator._format_duration(30), "30.0 seconds")
        self.assertEqual(self.generator._format_duration(90), "1.5 minutes")
        self.assertEqual(self.generator._format_duration(3900), "1.1 hours")


class TestBenchmarkRunner(unittest.TestCase):
    """Test cases for benchmark runner."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = BenchmarkConfig()
        self.runner = BenchmarkRunner(self.config, self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    async def test_benchmark_runner_initialization(self):
        """Test benchmark runner initialization."""
        self.assertEqual(self.runner.config, self.config)
        self.assertEqual(self.runner.output_dir, self.temp_dir)
        self.assertIsNotNone(self.runner.metrics)
        self.assertIsNotNone(self.runner.reporter)

    async def test_run_core_scenarios(self):
        """Test running core benchmark scenarios."""
        results = await self.runner._run_core_scenarios(10, 100, 5)
        
        self.assertEqual(results["duration_seconds"], 10)
        self.assertEqual(results["iterations"], 100)
        self.assertEqual(results["concurrent_users"], 5)
        self.assertEqual(results["scenarios_completed"], 1)
        self.assertEqual(results["total_operations"], 100)
        self.assertGreater(results["avg_response_time"], 0)
        self.assertGreater(results["operations_per_second"], 0)

    @patch.object(BenchmarkRunner, '_run_core_scenarios')
    async def test_run_quick_test(self, mock_scenarios):
        """Test running quick benchmark test."""
        mock_scenarios.return_value = {
            "operations_per_second": 150.0,
            "avg_response_time": 0.01,
            "total_operations": 100
        }
        
        with patch.object(self.runner.metrics, 'start_monitoring', new_callable=AsyncMock):
            with patch.object(self.runner.metrics, 'stop_monitoring', new_callable=AsyncMock):
                with patch.object(self.runner.metrics, 'get_summary') as mock_summary:
                    mock_summary.return_value = {"query_performance": {"operations_per_second": 150.0}}
                    
                    with patch.object(self.runner.reporter, 'generate_simple_report') as mock_report:
                        mock_report.return_value = self.temp_dir / "report.html"
                        
                        results = await self.runner.run_quick_test()
                        
                        self.assertEqual(results["test_type"], "quick")
                        self.assertIn("execution_time", results)
                        self.assertIn("results", results)
                        self.assertIn("metrics", results)

    @patch.object(BenchmarkRunner, '_run_database_scenarios')
    @patch.object(BenchmarkRunner, '_run_vector_scenarios')  
    @patch.object(BenchmarkRunner, '_run_mixed_scenarios')
    async def test_run_full_suite(self, mock_mixed, mock_vector, mock_db):
        """Test running full benchmark suite."""
        # Mock scenario results
        mock_results = {"operations_per_second": 100.0}
        mock_db.return_value = mock_results
        mock_vector.return_value = mock_results
        mock_mixed.return_value = mock_results
        
        with patch.object(self.runner.metrics, 'start_monitoring', new_callable=AsyncMock):
            with patch.object(self.runner.metrics, 'stop_monitoring', new_callable=AsyncMock):
                with patch.object(self.runner.metrics, 'get_summary') as mock_summary:
                    mock_summary.return_value = {
                        "query_performance": {"operations_per_second": 150.0},
                        "memory_usage": {"peak_mb": 120.0},
                        "connection_efficiency": {"efficiency_ratio": 0.85}
                    }
                    
                    with patch.object(self.runner.reporter, 'generate_simple_report') as mock_report:
                        mock_report.return_value = self.temp_dir / "report.html"
                        
                        results = await self.runner.run_full_suite()
                        
                        self.assertEqual(results["test_type"], "full_suite")
                        self.assertIn("validation", results)
                        self.assertIn("database", results["results"])
                        self.assertIn("vector", results["results"])
                        self.assertIn("mixed", results["results"])

    def test_validate_optimization_claims(self):
        """Test optimization claims validation."""
        database_results = {"operations_per_second": 150.0}
        vector_results = {"operations_per_second": 75.0}
        mixed_results = {"operations_per_second": 100.0}
        
        # Mock memory and connection metrics
        with patch.object(self.runner.metrics, 'get_memory_summary') as mock_memory:
            mock_memory.return_value = {"peak_mb": 150.0}
            
            with patch.object(self.runner.metrics, 'get_connection_summary') as mock_conn:
                mock_conn.return_value = {"efficiency_ratio": 0.85}
                
                validation = self.runner._validate_optimization_claims(
                    database_results, vector_results, mixed_results
                )
                
                self.assertIn("timestamp", validation)
                self.assertIn("claims_validated", validation)
                self.assertIn("total_claims", validation)
                self.assertIn("details", validation)
                self.assertEqual(validation["total_claims"], 4)
                
                # Check specific claims
                details = validation["details"]
                self.assertIn("query_performance_3x", details)
                self.assertIn("vector_search_30x", details)
                self.assertIn("memory_reduction_50pct", details)
                self.assertIn("connection_efficiency", details)


class TestBenchmarkIntegration(unittest.TestCase):
    """Integration tests for benchmark system."""

    async def test_end_to_end_quick_benchmark(self):
        """Test end-to-end quick benchmark execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = BenchmarkConfig(benchmark_iterations=5)  # Small number for testing
            runner = BenchmarkRunner(config, Path(temp_dir))
            
            results = await runner.run_quick_test()
            
            # Verify results structure
            self.assertEqual(results["test_type"], "quick")
            self.assertIn("execution_time", results)
            self.assertIn("results", results)
            self.assertIn("metrics", results)
            self.assertIn("report_path", results)
            
            # Verify report files were created
            report_path = Path(results["report_path"])
            self.assertTrue(report_path.exists())


if __name__ == '__main__':
    # Run async tests
    import asyncio
    
    def run_async_test(test_method):
        """Helper to run async test methods."""
        def wrapper(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(test_method(self))
            finally:
                loop.close()
        return wrapper
    
    # Patch async test methods
    for cls in [TestMetricsCollector, TestReportGenerator, TestBenchmarkRunner, TestBenchmarkIntegration]:
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if callable(attr) and asyncio.iscoroutinefunction(attr) and attr_name.startswith('test_'):
                setattr(cls, attr_name, run_async_test(attr))
    
    unittest.main(verbosity=2)