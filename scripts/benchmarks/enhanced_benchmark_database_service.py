#!/usr/bin/env python3
"""Enhanced Performance Benchmark Script for Database Service.

Modern performance benchmarking with:
- Statistical analysis and confidence intervals
- Performance regression detection
- Memory usage monitoring
- Concurrent load testing
- Detailed metrics collection
- Export to multiple formats (JSON, CSV, HTML)
- Integration with monitoring systems

Uses modern Python 3.13 patterns and best practices.
"""

import asyncio
import csv
import json
import logging
import statistics
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import psutil
from pydantic import BaseModel, Field


try:
    from tripsage_core.config import get_settings
    from tripsage_core.services.infrastructure.database_service import DatabaseService
except ImportError as e:
    print(f"Warning: Could not import TripSage modules: {e}")
    print("Running in mock mode for demonstration.")

    class MockSettings:
        """Mock settings for demonstration purposes."""

        DATABASE_POOL_SIZE = 20
        DATABASE_MAX_OVERFLOW = 30
        DATABASE_POOL_TIMEOUT = 30
        ENABLE_QUERY_CACHE = True

    def get_settings():
        """Get mock settings for demonstration."""
        return MockSettings()

    class DatabaseService:
        """Mock database service for demonstration purposes."""

        def __init__(self, settings):
            """Initialize mock database service.

            Args:
                settings: Mock settings object
            """
            self.settings = settings

        async def connect(self):
            """Connect to mock database."""
            await asyncio.sleep(0.001)

        async def close(self):
            """Close mock database connection."""
            await asyncio.sleep(0.001)

        async def execute_sql(self, query, params=None):
            """Execute mock SQL query.

            Args:
                query: SQL query string
                params: Query parameters

            Returns:
                Mock query result
            """
            await asyncio.sleep(0.002)
            return [{"result": "mock"}]

        @asynccontextmanager
        async def transaction(self):
            """Mock database transaction context manager."""
            yield


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("benchmark.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkMetrics:
    """Comprehensive benchmark metrics."""

    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error_message: str | None = None
    memory_before_mb: float | None = None
    memory_after_mb: float | None = None
    memory_peak_mb: float | None = None
    cpu_percent: float | None = None
    connection_count: int | None = None
    query_complexity: str | None = None
    cache_hit: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkStatistics(BaseModel):
    """Statistical analysis of benchmark results."""

    operation_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float

    # Duration statistics (in milliseconds)
    mean_duration: float
    median_duration: float
    std_deviation: float
    min_duration: float
    max_duration: float
    p50_duration: float
    p95_duration: float
    p99_duration: float

    # Confidence intervals
    confidence_interval_95: tuple[float, float]

    # Memory statistics
    mean_memory_usage: float | None = None
    peak_memory_usage: float | None = None

    # Performance indicators
    operations_per_second: float
    is_regression: bool = False
    regression_threshold_ms: float | None = None


class PerformanceRegression(BaseModel):
    """Performance regression detection model."""

    operation_name: str
    current_p95: float
    baseline_p95: float | None
    threshold_ms: float
    is_regression: bool
    regression_percentage: float | None = None
    severity: str  # "low", "medium", "high", "critical"


class EnhancedDatabaseBenchmark:
    """Enhanced database benchmark with modern monitoring capabilities."""

    def __init__(
        self,
        iterations: int = 100,
        concurrent_users: int = 10,
        output_dir: str = "benchmark_results",
        baseline_file: str | None = None,
    ):
        self.iterations = iterations
        self.concurrent_users = concurrent_users
        self.output_dir = Path(output_dir)
        self.baseline_file = baseline_file

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        self.settings = get_settings()
        self.metrics: list[BenchmarkMetrics] = []
        self.statistics: dict[str, BenchmarkStatistics] = {}
        self.regressions: list[PerformanceRegression] = []

        # Performance thresholds (in milliseconds)
        self.performance_thresholds = {
            "connection_establishment": 500,
            "simple_select": 100,
            "parameterized_query": 150,
            "complex_join": 1000,
            "transaction": 300,
            "bulk_insert": 2000,
            "vector_search": 500,
            "concurrent_operations": 200,
        }

    @asynccontextmanager
    async def measure_performance(
        self, operation_name: str
    ) -> AsyncGenerator[BenchmarkMetrics]:
        """Context manager for measuring performance with detailed metrics."""
        # Get initial system metrics
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_before = process.cpu_percent()

        # Create metrics object
        metrics = BenchmarkMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            end_time=0,
            duration_ms=0,
            success=False,
            memory_before_mb=memory_before,
        )

        try:
            yield metrics
            metrics.success = True

        except Exception as exc:
            metrics.error_message = str(exc)
            logger.exception("Benchmark %s failed", operation_name)

        finally:
            # Calculate final metrics
            metrics.end_time = time.time()
            metrics.duration_ms = (metrics.end_time - metrics.start_time) * 1000

            # Get final system metrics
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            metrics.memory_after_mb = memory_after
            metrics.memory_peak_mb = max(memory_before, memory_after)
            metrics.cpu_percent = process.cpu_percent() - cpu_before

            # Store metrics
            self.metrics.append(metrics)

    async def run_all_benchmarks(self):
        """Run comprehensive benchmarks with modern monitoring."""
        logger.info(f"Starting enhanced benchmarks with {self.iterations} iterations")
        logger.info(f"Concurrent users: {self.concurrent_users}")
        logger.info(f"Output directory: {self.output_dir}")

        # Run benchmarks
        await self.benchmark_connection_performance()
        await self.benchmark_query_performance()
        await self.benchmark_transaction_performance()
        await self.benchmark_concurrent_performance()
        await self.benchmark_memory_usage()
        await self.benchmark_vector_operations()

        # Analyze results
        self.calculate_statistics()
        self.detect_regressions()

        # Generate reports
        await self.generate_comprehensive_report()

        logger.info("Enhanced benchmarks completed successfully")

    async def benchmark_connection_performance(self):
        """Benchmark connection establishment and management."""
        logger.info("Benchmarking connection performance...")

        for i in range(min(20, self.iterations)):
            async with self.measure_performance("connection_establishment") as metrics:
                service = DatabaseService(settings=self.settings)
                await service.connect()
                await service.close()
                metrics.metadata["iteration"] = i

    async def benchmark_query_performance(self):
        """Benchmark various query types with detailed analysis."""
        logger.info("Benchmarking query performance...")

        service = DatabaseService(settings=self.settings)
        await service.connect()

        try:
            # Simple SELECT
            for i in range(self.iterations):
                async with self.measure_performance("simple_select") as metrics:
                    result = await service.execute_sql("SELECT 1 as test_value")
                    metrics.metadata.update(
                        {"iteration": i, "result_count": len(result) if result else 0}
                    )

            # Parameterized query
            for i in range(self.iterations):
                async with self.measure_performance("parameterized_query") as metrics:
                    result = await service.execute_sql(
                        "SELECT $1::text as param_value", (f"param_{i}",)
                    )
                    metrics.metadata.update(
                        {
                            "iteration": i,
                            "parameter": f"param_{i}",
                            "result_count": len(result) if result else 0,
                        }
                    )

            # Complex JOIN
            for i in range(min(20, self.iterations)):
                async with self.measure_performance("complex_join") as metrics:
                    query = """
                    SELECT t.table_name, c.column_name, c.data_type
                    FROM information_schema.tables t
                    JOIN information_schema.columns c ON t.table_name = c.table_name
                    WHERE t.table_schema = 'information_schema'
                    LIMIT 10
                    """
                    result = await service.execute_sql(query)
                    metrics.metadata.update(
                        {
                            "iteration": i,
                            "query_complexity": "complex_join",
                            "result_count": len(result) if result else 0,
                        }
                    )

        finally:
            await service.close()

    async def benchmark_transaction_performance(self):
        """Benchmark transaction performance with rollback scenarios."""
        logger.info("Benchmarking transaction performance...")

        service = DatabaseService(settings=self.settings)
        await service.connect()

        try:
            # Simple transactions
            for i in range(min(30, self.iterations)):
                async with self.measure_performance("transaction") as metrics:
                    async with service.transaction():
                        await service.execute_sql("SELECT 1")
                        await service.execute_sql("SELECT 2")
                    metrics.metadata.update(
                        {"iteration": i, "transaction_type": "simple"}
                    )

            # Transaction with rollback
            for i in range(min(10, self.iterations)):
                async with self.measure_performance("transaction_rollback") as metrics:
                    try:
                        async with service.transaction():
                            await service.execute_sql("SELECT 1")
                            if i % 3 == 0:  # Simulate occasional rollback
                                raise Exception("Intentional rollback")
                    except Exception:  # noqa: BLE001
                        pass  # Expected for rollback test

                    metrics.metadata.update(
                        {
                            "iteration": i,
                            "transaction_type": "rollback",
                            "rolled_back": i % 3 == 0,
                        }
                    )

        finally:
            await service.close()

    async def benchmark_concurrent_performance(self):
        """Benchmark concurrent operations with load testing."""
        logger.info(
            f"Benchmarking concurrent performance with {self.concurrent_users} users..."
        )

        async def concurrent_user_simulation(user_id: int):
            """Simulate a single user's database operations."""
            service = DatabaseService(settings=self.settings)
            await service.connect()

            try:
                for operation_id in range(10):
                    async with self.measure_performance(
                        "concurrent_operations"
                    ) as metrics:
                        await service.execute_sql(
                            "SELECT $1::int as user_id, $2::int as operation_id",
                            (user_id, operation_id),
                        )
                        metrics.metadata.update(
                            {
                                "user_id": user_id,
                                "operation_id": operation_id,
                                "concurrent_users": self.concurrent_users,
                            }
                        )
            finally:
                await service.close()

        # Run concurrent users
        tasks = [
            concurrent_user_simulation(user_id)
            for user_id in range(self.concurrent_users)
        ]
        await asyncio.gather(*tasks)

    async def benchmark_memory_usage(self):
        """Benchmark memory usage patterns."""
        logger.info("Benchmarking memory usage...")

        service = DatabaseService(settings=self.settings)
        await service.connect()

        try:
            # Memory usage with large result sets
            for i in range(min(10, self.iterations)):
                async with self.measure_performance(
                    "memory_usage_large_results"
                ) as metrics:
                    result = await service.execute_sql("""
                        SELECT table_name, column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'information_schema'
                        LIMIT 100
                    """)

                    # Process results to simulate memory usage
                    processed = [str(row) for row in (result or [])]

                    metrics.metadata.update(
                        {
                            "iteration": i,
                            "result_count": len(result) if result else 0,
                            "processed_count": len(processed),
                        }
                    )

        finally:
            await service.close()

    async def benchmark_vector_operations(self):
        """Benchmark vector search operations if available."""
        logger.info("Benchmarking vector operations...")

        service = DatabaseService(settings=self.settings)
        await service.connect()

        try:
            # Check if pgvector is available
            try:
                await service.execute_sql(
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                )
                vector_available = True
            except Exception:  # noqa: BLE001
                vector_available = False
                logger.warning(
                    "pgvector extension not available, using mock operations"
                )

            for i in range(min(10, self.iterations)):
                async with self.measure_performance("vector_search") as metrics:
                    if vector_available:
                        # Real vector operations
                        vector1 = np.random.random(384).tolist()
                        vector2 = np.random.random(384).tolist()

                        result = await service.execute_sql(
                            "SELECT $1::vector <-> $2::vector as distance",
                            (vector1, vector2),
                        )
                    else:
                        # Mock vector operations
                        await asyncio.sleep(0.005)  # Simulate vector computation
                        result = [{"distance": 0.5}]

                    metrics.metadata.update(
                        {
                            "iteration": i,
                            "vector_available": vector_available,
                            "vector_dimension": 384,
                            "result_count": len(result) if result else 0,
                        }
                    )

        finally:
            await service.close()

    def calculate_statistics(self):
        """Calculate comprehensive statistics for all benchmarks."""
        logger.info("Calculating statistics...")

        # Group metrics by operation
        operations = {}
        for metric in self.metrics:
            if metric.operation_name not in operations:
                operations[metric.operation_name] = []
            operations[metric.operation_name].append(metric)

        # Calculate statistics for each operation
        for operation_name, metrics_list in operations.items():
            successful_metrics = [m for m in metrics_list if m.success]

            if not successful_metrics:
                continue

            durations = [m.duration_ms for m in successful_metrics]
            memory_usages = [
                m.memory_peak_mb for m in successful_metrics if m.memory_peak_mb
            ]

            # Calculate percentiles
            durations_sorted = sorted(durations)
            n = len(durations_sorted)

            p50 = durations_sorted[int(n * 0.5)] if n > 0 else 0
            p95 = durations_sorted[int(n * 0.95)] if n > 0 else 0
            p99 = durations_sorted[int(n * 0.99)] if n > 0 else 0

            # Calculate confidence interval (95%)
            mean_duration = statistics.mean(durations)
            std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
            margin_error = (
                1.96 * (std_dev / (len(durations) ** 0.5)) if len(durations) > 1 else 0
            )
            confidence_interval = (
                mean_duration - margin_error,
                mean_duration + margin_error,
            )

            # Calculate operations per second
            total_time_seconds = sum(durations) / 1000
            ops_per_second = (
                len(durations) / total_time_seconds if total_time_seconds > 0 else 0
            )

            # Create statistics object
            stats = BenchmarkStatistics(
                operation_name=operation_name,
                total_runs=len(metrics_list),
                successful_runs=len(successful_metrics),
                failed_runs=len(metrics_list) - len(successful_metrics),
                success_rate=(len(successful_metrics) / len(metrics_list)) * 100,
                mean_duration=mean_duration,
                median_duration=statistics.median(durations),
                std_deviation=std_dev,
                min_duration=min(durations),
                max_duration=max(durations),
                p50_duration=p50,
                p95_duration=p95,
                p99_duration=p99,
                confidence_interval_95=confidence_interval,
                mean_memory_usage=statistics.mean(memory_usages)
                if memory_usages
                else None,
                peak_memory_usage=max(memory_usages) if memory_usages else None,
                operations_per_second=ops_per_second,
            )

            self.statistics[operation_name] = stats

    def detect_regressions(self):
        """Detect performance regressions against baselines."""
        logger.info("Detecting performance regressions...")

        # Load baseline if available
        baseline_stats = {}
        if self.baseline_file and Path(self.baseline_file).exists():
            try:
                with Path(self.baseline_file).open() as f:
                    baseline_data = json.load(f)
                    baseline_stats = baseline_data.get("statistics", {})
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Could not load baseline file: {e}")

        # Check for regressions
        for operation_name, stats in self.statistics.items():
            threshold = self.performance_thresholds.get(operation_name, 1000)
            baseline_p95 = None

            if operation_name in baseline_stats:
                baseline_p95 = baseline_stats[operation_name].get("p95_duration")

            # Determine if this is a regression
            is_regression = stats.p95_duration > threshold
            regression_percentage = None
            severity = "low"

            if baseline_p95:
                regression_percentage = (
                    (stats.p95_duration - baseline_p95) / baseline_p95
                ) * 100
                is_regression = (
                    is_regression or regression_percentage > 20
                )  # 20% regression threshold

                if regression_percentage > 100:
                    severity = "critical"
                elif regression_percentage > 50:
                    severity = "high"
                elif regression_percentage > 20:
                    severity = "medium"

            if is_regression or stats.p95_duration > threshold:
                regression = PerformanceRegression(
                    operation_name=operation_name,
                    current_p95=stats.p95_duration,
                    baseline_p95=baseline_p95,
                    threshold_ms=threshold,
                    is_regression=is_regression,
                    regression_percentage=regression_percentage,
                    severity=severity,
                )
                self.regressions.append(regression)
                stats.is_regression = True
                stats.regression_threshold_ms = threshold

    async def generate_comprehensive_report(self):
        """Generate comprehensive benchmark reports in multiple formats."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Generate JSON report
        await self.generate_json_report(timestamp)

        # Generate CSV report
        await self.generate_csv_report(timestamp)

        # Generate HTML report
        await self.generate_html_report(timestamp)

        # Generate console report
        self.generate_console_report()

        # Save baseline for future comparisons
        await self.save_baseline(timestamp)

    async def generate_json_report(self, timestamp: str):
        """Generate detailed JSON report."""
        report_data = {
            "benchmark_info": {
                "timestamp": timestamp,
                "iterations": self.iterations,
                "concurrent_users": self.concurrent_users,
                "python_version": sys.version,
                "system_info": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": psutil.virtual_memory().total
                    / 1024
                    / 1024
                    / 1024,
                    "platform": sys.platform,
                },
            },
            "statistics": {
                name: asdict(stats) for name, stats in self.statistics.items()
            },
            "regressions": [asdict(reg) for reg in self.regressions],
            "raw_metrics": [asdict(metric) for metric in self.metrics],
            "performance_thresholds": self.performance_thresholds,
        }

        json_file = self.output_dir / f"benchmark_report_{timestamp}.json"
        with Path(json_file, "w").open() as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"JSON report saved to: {json_file}")

    async def generate_csv_report(self, timestamp: str):
        """Generate CSV report for data analysis."""
        csv_file = self.output_dir / f"benchmark_data_{timestamp}.csv"

        with Path(csv_file, "w", newline="").open() as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(
                [
                    "operation_name",
                    "duration_ms",
                    "success",
                    "memory_before_mb",
                    "memory_after_mb",
                    "memory_peak_mb",
                    "cpu_percent",
                    "timestamp",
                ]
            )

            # Write data
            for metric in self.metrics:
                writer.writerow(
                    [
                        metric.operation_name,
                        metric.duration_ms,
                        metric.success,
                        metric.memory_before_mb,
                        metric.memory_after_mb,
                        metric.memory_peak_mb,
                        metric.cpu_percent,
                        metric.start_time,
                    ]
                )

        logger.info(f"CSV report saved to: {csv_file}")

    async def generate_html_report(self, timestamp: str):
        """Generate HTML report with visualizations."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Database Benchmark Report - {timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{
                    color: #333;
                    border-bottom: 2px solid #ddd;
                    padding-bottom: 10px;
                }}
                .stats-table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                .stats-table th, .stats-table td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                .stats-table th {{ background-color: #f2f2f2; }}
                .regression {{ background-color: #ffebee; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Database Benchmark Report</h1>
                <p>Generated: {timestamp}</p>
                <p>Iterations: {self.iterations} |
                   Concurrent Users: {self.concurrent_users}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>Total Operations: {len(self.statistics)}</p>
                <p>Performance Regressions: {len(self.regressions)}</p>
                <p>Total Metrics Collected: {len(self.metrics)}</p>
            </div>

            <h2>Performance Statistics</h2>
            <table class="stats-table">
                <tr>
                    <th>Operation</th>
                    <th>Mean (ms)</th>
                    <th>P95 (ms)</th>
                    <th>P99 (ms)</th>
                    <th>Success Rate</th>
                    <th>Ops/Sec</th>
                    <th>Status</th>
                </tr>
        """

        for name, stats in self.statistics.items():
            status_class = "regression" if stats.is_regression else ""
            status_text = "⚠️ REGRESSION" if stats.is_regression else "✅ OK"

            html_content += f"""
                <tr class="{status_class}">
                    <td>{name}</td>
                    <td>{stats.mean_duration:.2f}</td>
                    <td>{stats.p95_duration:.2f}</td>
                    <td>{stats.p99_duration:.2f}</td>
                    <td>{stats.success_rate:.1f}%</td>
                    <td>{stats.operations_per_second:.2f}</td>
                    <td>{status_text}</td>
                </tr>
            """

        html_content += """
            </table>

            <h2>Performance Regressions</h2>
        """

        if self.regressions:
            html_content += '<table class="stats-table">'
            html_content += """
                <tr>
                    <th>Operation</th>
                    <th>Current P95 (ms)</th>
                    <th>Baseline P95 (ms)</th>
                    <th>Regression %</th>
                    <th>Severity</th>
                </tr>
            """

            for reg in self.regressions:
                html_content += f"""
                    <tr>
                        <td>{reg.operation_name}</td>
                        <td>{reg.current_p95:.2f}</td>
                        <td>{reg.baseline_p95:.2f if reg.baseline_p95 else 'N/A'}</td>
                        <td>{
                    (
                        f"{reg.regression_percentage:.1f}%"
                        if reg.regression_percentage
                        else "N/A"
                    )
                }</td>
                        <td>{reg.severity.upper()}</td>
                    </tr>
                """

            html_content += "</table>"
        else:
            html_content += (
                '<p class="success">No performance regressions detected! 🎉</p>'
            )

        html_content += """
        </body>
        </html>
        """

        html_file = self.output_dir / f"benchmark_report_{timestamp}.html"
        with Path(html_file, "w").open() as f:
            f.write(html_content)

        logger.info(f"HTML report saved to: {html_file}")

    def generate_console_report(self):
        """Generate console report with key metrics."""
        print("\n" + "=" * 80)
        print("DATABASE BENCHMARK RESULTS")
        print("=" * 80)

        # Summary
        total_operations = len(self.statistics)
        total_regressions = len(self.regressions)

        print("\nSUMMARY:")
        print(f"  Total Operations: {total_operations}")
        print(f"  Performance Regressions: {total_regressions}")
        print(f"  Total Metrics: {len(self.metrics)}")

        # Performance statistics table
        print("\nPERFORMANCE STATISTICS:")
        print("-" * 100)
        header = (
            f"{'Operation':<25} {'Mean(ms)':<10} {'P95(ms)':<10} "
            f"{'P99(ms)':<10} {'Success%':<10} {'Ops/Sec':<10} {'Status':<10}"
        )
        print(header)
        print("-" * 100)

        for name, stats in self.statistics.items():
            status = "REGRESSION" if stats.is_regression else "OK"
            print(
                f"{name:<25} {stats.mean_duration:<10.2f} {stats.p95_duration:<10.2f} "
                f"{stats.p99_duration:<10.2f} {stats.success_rate:<10.1f} "
                f"{stats.operations_per_second:<10.2f} {status:<10}"
            )

        # Regressions
        if self.regressions:
            print("\nPERFORMANCE REGRESSIONS:")
            print("-" * 80)
            for reg in self.regressions:
                print(
                    f"⚠️  {reg.operation_name}: {reg.current_p95:.2f}ms "
                    f"(threshold: {reg.threshold_ms}ms, severity: {reg.severity})"
                )
        else:
            print("\n✅ No performance regressions detected!")

        print("=" * 80)

    async def save_baseline(self, timestamp: str):
        """Save current results as baseline for future comparisons."""
        baseline_file = self.output_dir / f"baseline_{timestamp}.json"
        baseline_data = {
            "timestamp": timestamp,
            "statistics": {
                name: asdict(stats) for name, stats in self.statistics.items()
            },
            "performance_thresholds": self.performance_thresholds,
        }

        with Path(baseline_file, "w").open() as f:
            json.dump(baseline_data, f, indent=2, default=str)

        # Also save as latest baseline
        latest_baseline = self.output_dir / "baseline_latest.json"
        with Path(latest_baseline, "w").open() as f:
            json.dump(baseline_data, f, indent=2, default=str)

        logger.info(f"Baseline saved to: {baseline_file}")


async def main():
    """Main benchmark execution with enhanced CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Database Service Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python enhanced_benchmark_database_service.py --iterations 100 --concurrent 10
  python enhanced_benchmark_database_service.py --baseline baseline_latest.json
  python enhanced_benchmark_database_service.py --output-dir ./results --iterations 50
        """,
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per test (default: 100)",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=10,
        help="Number of concurrent users (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Output directory for results (default: benchmark_results)",
    )
    parser.add_argument(
        "--baseline", type=str, help="Baseline file for regression detection"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Create and run benchmark
    benchmark = EnhancedDatabaseBenchmark(
        iterations=args.iterations,
        concurrent_users=args.concurrent,
        output_dir=args.output_dir,
        baseline_file=args.baseline,
    )

    try:
        await benchmark.run_all_benchmarks()

        # Exit with error code if regressions detected
        if benchmark.regressions:
            critical_regressions = [
                r for r in benchmark.regressions if r.severity == "critical"
            ]
            if critical_regressions:
                logger.exception(
                    f"Critical performance regressions detected: "
                    f"{len(critical_regressions)}"
                )
                sys.exit(2)
            else:
                logger.warning(
                    f"Performance regressions detected: {len(benchmark.regressions)}"
                )
                sys.exit(1)

        logger.info("All benchmarks completed successfully with no regressions")

    except Exception:
        logger.exception("Benchmark failed")
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())
