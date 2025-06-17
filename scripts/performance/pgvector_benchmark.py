"""
PGVector Performance Benchmark Suite for TripSage.

This comprehensive benchmarking suite validates pgvector optimization performance
improvements and provides automated regression detection. Designed to validate:

- 30x pgvector query performance improvement
- <10ms query latency target
- 30% memory reduction
- Index creation performance across data sizes
- Reproducible baseline metrics for CI/CD integration

Key Features:
- Comprehensive index creation benchmarks
- Query latency tests with various ef_search values
- Memory usage profiling and tracking
- Automated regression detection
- Performance comparison reports
- CI/CD integration support
"""

import asyncio
import json
import logging
import os
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.pgvector_service import (
    DistanceFunction,
    OptimizationProfile,
    PGVectorService,
)

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Configuration for pgvector benchmarking."""

    # Test data configuration
    vector_dimensions: int = 384
    small_dataset_size: int = 1000
    medium_dataset_size: int = 10000
    large_dataset_size: int = 50000

    # Performance test configuration
    warmup_queries: int = 50
    benchmark_queries: int = 200
    concurrent_connections: int = 10
    query_timeout_seconds: int = 30

    # Index configuration
    ef_search_values: List[int] = None
    optimization_profiles: List[OptimizationProfile] = None
    distance_functions: List[DistanceFunction] = None

    # Memory profiling
    enable_memory_profiling: bool = True
    memory_sample_interval: float = 0.5  # seconds

    # Performance targets
    target_query_latency_ms: float = 10.0
    target_memory_reduction_pct: float = 30.0
    target_performance_improvement_x: float = 30.0

    # Output configuration
    output_directory: str = "./benchmark_results"
    generate_detailed_report: bool = True
    export_raw_data: bool = True

    def __post_init__(self):
        """Set default values for mutable fields."""
        if self.ef_search_values is None:
            self.ef_search_values = [40, 100, 200, 400]
        if self.optimization_profiles is None:
            self.optimization_profiles = [
                OptimizationProfile.SPEED,
                OptimizationProfile.BALANCED,
                OptimizationProfile.QUALITY,
            ]
        if self.distance_functions is None:
            self.distance_functions = [
                DistanceFunction.COSINE,
                DistanceFunction.L2,
                DistanceFunction.INNER_PRODUCT,
            ]


@dataclass
class IndexCreationMetrics:
    """Metrics for index creation performance."""

    table_name: str
    data_size: int
    vector_dimensions: int
    distance_function: str
    optimization_profile: str
    creation_time_seconds: float
    index_size_bytes: int
    index_size_human: str
    memory_usage_mb: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class QueryPerformanceMetrics:
    """Metrics for query performance."""

    test_name: str
    ef_search: int
    query_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    queries_per_second: float
    memory_usage_mb: float
    success_rate: float
    errors: List[str]


@dataclass
class MemoryProfileMetrics:
    """Memory usage profiling metrics."""

    test_phase: str
    timestamp: datetime
    rss_memory_mb: float
    vms_memory_mb: float
    memory_percent: float
    available_memory_mb: float


@dataclass
class BenchmarkResults:
    """Complete benchmark results."""

    config: BenchmarkConfig
    test_start_time: datetime
    test_end_time: datetime
    total_duration_seconds: float

    # Index creation results
    baseline_index_metrics: List[IndexCreationMetrics]
    optimized_index_metrics: List[IndexCreationMetrics]

    # Query performance results
    baseline_query_metrics: List[QueryPerformanceMetrics]
    optimized_query_metrics: List[QueryPerformanceMetrics]

    # Memory profiling results
    memory_profile: List[MemoryProfileMetrics]

    # Performance comparison
    performance_improvements: Dict[str, float]
    memory_reduction_achieved: float

    # Validation results
    validation_results: Dict[str, bool]
    regression_detected: bool

    # System information
    system_info: Dict[str, Any]


class PGVectorBenchmark:
    """Comprehensive pgvector performance benchmark suite."""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize benchmark suite.

        Args:
            config: Benchmark configuration, uses defaults if None
        """
        self.config = config or BenchmarkConfig()
        self.db_service: Optional[DatabaseService] = None
        self.pgvector_service: Optional[PGVectorService] = None
        self.process = psutil.Process()

        # Results storage
        self.baseline_index_metrics: List[IndexCreationMetrics] = []
        self.optimized_index_metrics: List[IndexCreationMetrics] = []
        self.baseline_query_metrics: List[QueryPerformanceMetrics] = []
        self.optimized_query_metrics: List[QueryPerformanceMetrics] = []
        self.memory_profile: List[MemoryProfileMetrics] = []

        # Setup output directory
        os.makedirs(self.config.output_directory, exist_ok=True)

        # Configure logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure benchmark logging."""
        log_file = os.path.join(self.config.output_directory, "benchmark.log")

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)

    async def setup(self) -> None:
        """Initialize database connections and services."""
        logger.info("Initializing benchmark environment...")

        # Initialize database service
        settings = get_settings()
        self.db_service = DatabaseService(settings)
        await self.db_service.connect()

        # Initialize pgvector service
        self.pgvector_service = PGVectorService(self.db_service)

        logger.info("Benchmark environment initialized successfully")

    async def cleanup(self) -> None:
        """Clean up resources and connections."""
        if self.db_service:
            await self.db_service.disconnect()
        logger.info("Benchmark cleanup completed")

    def _record_memory_usage(self, test_phase: str) -> None:
        """Record current memory usage."""
        if not self.config.enable_memory_profiling:
            return

        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            available_memory = psutil.virtual_memory().available / (1024 * 1024)

            metric = MemoryProfileMetrics(
                test_phase=test_phase,
                timestamp=datetime.now(timezone.utc),
                rss_memory_mb=memory_info.rss / (1024 * 1024),
                vms_memory_mb=memory_info.vms / (1024 * 1024),
                memory_percent=memory_percent,
                available_memory_mb=available_memory,
            )

            self.memory_profile.append(metric)

        except Exception as e:
            logger.warning(f"Failed to record memory usage: {e}")

    async def _create_test_table(self, table_name: str, size: int) -> None:
        """Create test table with vector data.

        Args:
            table_name: Name of test table
            size: Number of records to create
        """
        logger.info(f"Creating test table {table_name} with {size} records...")

        # Drop existing table
        await self.db_service.execute_sql(f"DROP TABLE IF EXISTS {table_name}")

        # Create table
        create_sql = f"""
            CREATE TABLE {table_name} (
                id BIGSERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                embedding VECTOR({self.config.vector_dimensions}),
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        await self.db_service.execute_sql(create_sql)

        # Generate and insert test data in batches
        batch_size = 1000
        for batch_start in range(0, size, batch_size):
            batch_end = min(batch_start + batch_size, size)
            batch_data = []

            for i in range(batch_start, batch_end):
                # Generate random normalized vector
                vector = np.random.normal(0, 1, self.config.vector_dimensions)
                vector = vector / np.linalg.norm(vector)

                batch_data.append(
                    {
                        "content": f"Test content item {i}",
                        "embedding": vector.tolist(),
                        "metadata": {"test_id": i, "batch": batch_start // batch_size},
                    }
                )

            # Insert batch

            # Convert to proper format for SQL
            sql_batch = []
            for item in batch_data:
                sql_batch.append(
                    (
                        item["content"],
                        str(item["embedding"]),
                        json.dumps(item["metadata"]),
                    )
                )

            await self.db_service.execute_sql(
                f"INSERT INTO {table_name} (content, embedding, metadata) VALUES "
                + ",".join(
                    [
                        f"('{item[0]}', '{item[1]}'::vector, '{item[2]}'::jsonb)"
                        for item in sql_batch
                    ]
                )
            )

        logger.info(f"Created test table {table_name} with {size} records")

    async def benchmark_index_creation(self) -> None:
        """Benchmark index creation performance across different data sizes."""
        logger.info("Starting index creation benchmarks...")

        test_sizes = [
            self.config.small_dataset_size,
            self.config.medium_dataset_size,
            self.config.large_dataset_size,
        ]

        for size in test_sizes:
            table_name = f"benchmark_test_{size}"

            # Create test data
            self._record_memory_usage(f"before_data_creation_{size}")
            await self._create_test_table(table_name, size)
            self._record_memory_usage(f"after_data_creation_{size}")

            # Test baseline (no index)
            await self._benchmark_index_creation_scenario(
                table_name=table_name,
                data_size=size,
                create_index=False,
                metrics_list=self.baseline_index_metrics,
            )

            # Test optimized (with index) for each configuration
            for profile in self.config.optimization_profiles:
                for distance_func in self.config.distance_functions:
                    await self._benchmark_index_creation_scenario(
                        table_name=table_name,
                        data_size=size,
                        create_index=True,
                        optimization_profile=profile,
                        distance_function=distance_func,
                        metrics_list=self.optimized_index_metrics,
                    )

        logger.info("Index creation benchmarks completed")

    async def _benchmark_index_creation_scenario(
        self,
        table_name: str,
        data_size: int,
        create_index: bool,
        metrics_list: List[IndexCreationMetrics],
        optimization_profile: OptimizationProfile = OptimizationProfile.BALANCED,
        distance_function: DistanceFunction = DistanceFunction.COSINE,
    ) -> None:
        """Benchmark a specific index creation scenario."""

        self._record_memory_usage(
            f"before_index_{table_name}_{optimization_profile.value}"
        )

        start_time = time.time()
        success = True
        error_message = None
        index_size_bytes = 0
        index_size_human = "N/A"

        try:
            if create_index:
                # Create HNSW index
                await self.pgvector_service.create_hnsw_index(
                    table_name=table_name,
                    column_name="embedding",
                    distance_function=distance_function,
                    profile=optimization_profile,
                )

                # Get index statistics
                stats = await self.pgvector_service.get_index_stats(
                    table_name, "embedding"
                )
                if stats:
                    index_size_bytes = stats.index_size_bytes
                    index_size_human = stats.index_size_human

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Index creation failed: {e}")

        creation_time = time.time() - start_time

        self._record_memory_usage(
            f"after_index_{table_name}_{optimization_profile.value}"
        )

        # Get current memory usage
        memory_info = self.process.memory_info()
        memory_usage_mb = memory_info.rss / (1024 * 1024)

        # Create metrics
        metrics = IndexCreationMetrics(
            table_name=table_name,
            data_size=data_size,
            vector_dimensions=self.config.vector_dimensions,
            distance_function=distance_function.value,
            optimization_profile=optimization_profile.value,
            creation_time_seconds=creation_time,
            index_size_bytes=index_size_bytes,
            index_size_human=index_size_human,
            memory_usage_mb=memory_usage_mb,
            success=success,
            error_message=error_message,
        )

        metrics_list.append(metrics)

        logger.info(
            f"Index creation benchmark - Table: {table_name}, "
            f"Profile: {optimization_profile.value}, Time: {creation_time:.2f}s, "
            f"Success: {success}"
        )

    async def benchmark_query_performance(self) -> None:
        """Benchmark query performance with different configurations."""
        logger.info("Starting query performance benchmarks...")

        # Use medium dataset for query benchmarks
        table_name = f"benchmark_test_{self.config.medium_dataset_size}"

        # Baseline queries (no index)
        await self._benchmark_query_scenario(
            table_name=table_name,
            test_name="baseline_no_index",
            ef_search=40,  # Default
            metrics_list=self.baseline_query_metrics,
        )

        # Create HNSW index for optimized tests
        await self.pgvector_service.create_hnsw_index(
            table_name=table_name,
            column_name="embedding",
            distance_function=DistanceFunction.COSINE,
            profile=OptimizationProfile.BALANCED,
        )

        # Optimized queries with different ef_search values
        for ef_search in self.config.ef_search_values:
            await self._benchmark_query_scenario(
                table_name=table_name,
                test_name=f"optimized_ef_search_{ef_search}",
                ef_search=ef_search,
                metrics_list=self.optimized_query_metrics,
            )

        logger.info("Query performance benchmarks completed")

    async def _benchmark_query_scenario(
        self,
        table_name: str,
        test_name: str,
        ef_search: int,
        metrics_list: List[QueryPerformanceMetrics],
    ) -> None:
        """Benchmark a specific query performance scenario."""

        logger.info(f"Running query benchmark: {test_name} (ef_search={ef_search})")

        # Set ef_search parameter
        await self.pgvector_service.set_query_quality(ef_search)

        self._record_memory_usage(f"before_queries_{test_name}")

        # Generate random query vectors
        query_vectors = []
        for _ in range(self.config.benchmark_queries):
            vector = np.random.normal(0, 1, self.config.vector_dimensions)
            vector = vector / np.linalg.norm(vector)
            query_vectors.append(vector)

        # Warmup queries
        for i in range(self.config.warmup_queries):
            try:
                query_vector = query_vectors[i % len(query_vectors)]
                await self._execute_similarity_query(table_name, query_vector)
            except Exception as e:
                logger.warning(f"Warmup query {i} failed: {e}")

        # Benchmark queries
        query_times = []
        errors = []
        successful_queries = 0

        start_time = time.time()

        for i, query_vector in enumerate(query_vectors):
            query_start = time.time()

            try:
                await self._execute_similarity_query(table_name, query_vector)
                query_time = (time.time() - query_start) * 1000  # Convert to ms
                query_times.append(query_time)
                successful_queries += 1

            except Exception as e:
                error_msg = f"Query {i} failed: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)

        total_time = time.time() - start_time

        self._record_memory_usage(f"after_queries_{test_name}")

        # Calculate metrics
        if query_times:
            avg_latency_ms = statistics.mean(query_times)
            p95_latency_ms = statistics.quantiles(query_times, n=20)[
                18
            ]  # 95th percentile
            p99_latency_ms = (
                statistics.quantiles(query_times, n=100)[98]
                if len(query_times) >= 100
                else max(query_times)
            )
            min_latency_ms = min(query_times)
            max_latency_ms = max(query_times)
            queries_per_second = (
                successful_queries / total_time if total_time > 0 else 0
            )
        else:
            avg_latency_ms = p95_latency_ms = p99_latency_ms = 0
            min_latency_ms = max_latency_ms = 0
            queries_per_second = 0

        success_rate = successful_queries / len(query_vectors) if query_vectors else 0

        # Get memory usage
        memory_info = self.process.memory_info()
        memory_usage_mb = memory_info.rss / (1024 * 1024)

        # Create metrics
        metrics = QueryPerformanceMetrics(
            test_name=test_name,
            ef_search=ef_search,
            query_count=len(query_vectors),
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            p99_latency_ms=p99_latency_ms,
            min_latency_ms=min_latency_ms,
            max_latency_ms=max_latency_ms,
            queries_per_second=queries_per_second,
            memory_usage_mb=memory_usage_mb,
            success_rate=success_rate,
            errors=errors[:10],  # Keep only first 10 errors
        )

        metrics_list.append(metrics)

        logger.info(
            f"Query benchmark completed - {test_name}: "
            f"Avg: {avg_latency_ms:.2f}ms, P95: {p95_latency_ms:.2f}ms, "
            f"QPS: {queries_per_second:.1f}, Success: {success_rate:.1%}"
        )

    async def _execute_similarity_query(
        self, table_name: str, query_vector: np.ndarray
    ) -> List[Dict]:
        """Execute a vector similarity query."""
        query_sql = f"""
            SELECT id, content, embedding <-> %s::vector AS distance
            FROM {table_name}
            ORDER BY distance
            LIMIT 10
        """

        result = await self.db_service.execute_sql(query_sql, (query_vector.tolist(),))
        return [dict(row) for row in result] if result else []

    def _calculate_performance_improvements(self) -> Tuple[Dict[str, float], float]:
        """Calculate performance improvements and memory reduction."""
        improvements = {}

        # Query performance improvement
        if self.baseline_query_metrics and self.optimized_query_metrics:
            baseline_avg = statistics.mean(
                [m.avg_latency_ms for m in self.baseline_query_metrics]
            )
            optimized_avg = statistics.mean(
                [m.avg_latency_ms for m in self.optimized_query_metrics]
            )

            if optimized_avg > 0:
                improvements["query_latency_improvement"] = baseline_avg / optimized_avg

            baseline_qps = statistics.mean(
                [m.queries_per_second for m in self.baseline_query_metrics]
            )
            optimized_qps = statistics.mean(
                [m.queries_per_second for m in self.optimized_query_metrics]
            )

            if baseline_qps > 0:
                improvements["throughput_improvement"] = optimized_qps / baseline_qps

        # Index creation time improvement
        if self.baseline_index_metrics and self.optimized_index_metrics:
            baseline_creation_time = (
                statistics.mean(
                    [
                        m.creation_time_seconds
                        for m in self.baseline_index_metrics
                        if m.success
                    ]
                )
                if self.baseline_index_metrics
                else 0
            )

            optimized_creation_time = (
                statistics.mean(
                    [
                        m.creation_time_seconds
                        for m in self.optimized_index_metrics
                        if m.success
                    ]
                )
                if self.optimized_index_metrics
                else 0
            )

            if optimized_creation_time > 0 and baseline_creation_time > 0:
                improvements["index_creation_improvement"] = (
                    baseline_creation_time / optimized_creation_time
                )

        # Memory reduction calculation
        memory_reduction = 0.0
        if self.memory_profile:
            baseline_memory = []
            optimized_memory = []

            for metric in self.memory_profile:
                if "baseline" in metric.test_phase:
                    baseline_memory.append(metric.rss_memory_mb)
                elif "optimized" in metric.test_phase:
                    optimized_memory.append(metric.rss_memory_mb)

            if baseline_memory and optimized_memory:
                avg_baseline = statistics.mean(baseline_memory)
                avg_optimized = statistics.mean(optimized_memory)

                if avg_baseline > 0:
                    memory_reduction = (avg_baseline - avg_optimized) / avg_baseline

        return improvements, memory_reduction

    def _validate_performance_targets(
        self, improvements: Dict[str, float], memory_reduction: float
    ) -> Tuple[Dict[str, bool], bool]:
        """Validate performance against targets."""
        validation_results = {}

        # Query latency target
        best_optimized_latency = min(
            [
                m.avg_latency_ms
                for m in self.optimized_query_metrics
                if m.avg_latency_ms > 0
            ],
            default=float("inf"),
        )

        validation_results["query_latency_target"] = (
            best_optimized_latency <= self.config.target_query_latency_ms
        )

        # Performance improvement target
        query_improvement = improvements.get("query_latency_improvement", 0)
        validation_results["performance_improvement_target"] = (
            query_improvement >= self.config.target_performance_improvement_x
        )

        # Memory reduction target
        validation_results["memory_reduction_target"] = memory_reduction >= (
            self.config.target_memory_reduction_pct / 100
        )

        # Overall validation
        regression_detected = not all(validation_results.values())

        return validation_results, regression_detected

    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information for the report."""
        return {
            "platform": os.uname().sysname,
            "platform_version": os.uname().release,
            "architecture": os.uname().machine,
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024 * 1024 * 1024),
            "python_version": os.sys.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def run_full_benchmark(self) -> BenchmarkResults:
        """Run the complete benchmark suite."""
        logger.info("Starting comprehensive pgvector benchmark suite...")

        test_start_time = datetime.now(timezone.utc)

        try:
            await self.setup()

            # Record initial memory state
            self._record_memory_usage("benchmark_start")

            # Run index creation benchmarks
            await self.benchmark_index_creation()

            # Run query performance benchmarks
            await self.benchmark_query_performance()

            # Record final memory state
            self._record_memory_usage("benchmark_end")

        finally:
            await self.cleanup()

        test_end_time = datetime.now(timezone.utc)
        total_duration = (test_end_time - test_start_time).total_seconds()

        # Calculate improvements and validate
        improvements, memory_reduction = self._calculate_performance_improvements()
        validation_results, regression_detected = self._validate_performance_targets(
            improvements, memory_reduction
        )

        # Compile results
        results = BenchmarkResults(
            config=self.config,
            test_start_time=test_start_time,
            test_end_time=test_end_time,
            total_duration_seconds=total_duration,
            baseline_index_metrics=self.baseline_index_metrics,
            optimized_index_metrics=self.optimized_index_metrics,
            baseline_query_metrics=self.baseline_query_metrics,
            optimized_query_metrics=self.optimized_query_metrics,
            memory_profile=self.memory_profile,
            performance_improvements=improvements,
            memory_reduction_achieved=memory_reduction,
            validation_results=validation_results,
            regression_detected=regression_detected,
            system_info=self._get_system_info(),
        )

        # Generate reports
        if self.config.generate_detailed_report:
            await self._generate_reports(results)

        logger.info(f"Benchmark suite completed in {total_duration:.2f} seconds")
        return results

    async def _generate_reports(self, results: BenchmarkResults) -> None:
        """Generate comprehensive benchmark reports."""
        logger.info("Generating benchmark reports...")

        # Export raw data as JSON
        if self.config.export_raw_data:
            raw_data_file = os.path.join(
                self.config.output_directory, "benchmark_raw_data.json"
            )
            with open(raw_data_file, "w") as f:
                # Convert dataclass to dict recursively
                def to_dict(obj):
                    if hasattr(obj, "__dict__"):
                        return {k: to_dict(v) for k, v in obj.__dict__.items()}
                    elif isinstance(obj, list):
                        return [to_dict(item) for item in obj]
                    elif isinstance(obj, datetime):
                        return obj.isoformat()
                    else:
                        return obj

                json.dump(to_dict(results), f, indent=2, default=str)

        # Generate summary report
        summary_file = os.path.join(
            self.config.output_directory, "benchmark_summary.md"
        )
        with open(summary_file, "w") as f:
            f.write(self._generate_summary_report(results))

        logger.info(f"Reports generated in {self.config.output_directory}")

    def _generate_summary_report(self, results: BenchmarkResults) -> str:
        """Generate a markdown summary report."""
        report = []

        report.append("# PGVector Performance Benchmark Report")
        report.append(
            f"**Generated:** {results.test_end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        report.append(f"**Duration:** {results.total_duration_seconds:.2f} seconds")
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append("")

        if results.validation_results.get("performance_improvement_target", False):
            report.append("✅ **Performance Target Met:** 30x improvement achieved")
        else:
            improvement = results.performance_improvements.get(
                "query_latency_improvement", 0
            )
            report.append(
                f"❌ **Performance Target Missed:** {improvement:.1f}x improvement (target: 30x)"
            )

        if results.validation_results.get("query_latency_target", False):
            report.append("✅ **Latency Target Met:** <10ms query latency achieved")
        else:
            best_latency = min(
                [m.avg_latency_ms for m in results.optimized_query_metrics], default=0
            )
            report.append(
                f"❌ **Latency Target Missed:** {best_latency:.2f}ms (target: <10ms)"
            )

        if results.validation_results.get("memory_reduction_target", False):
            report.append(
                f"✅ **Memory Target Met:** {results.memory_reduction_achieved:.1%} reduction achieved"
            )
        else:
            report.append(
                f"❌ **Memory Target Missed:** {results.memory_reduction_achieved:.1%} reduction (target: 30%)"
            )

        report.append("")

        # Performance Improvements
        report.append("## Performance Improvements")
        report.append("")

        for metric, value in results.performance_improvements.items():
            report.append(f"- **{metric.replace('_', ' ').title()}:** {value:.2f}x")

        report.append(
            f"- **Memory Reduction:** {results.memory_reduction_achieved:.1%}"
        )
        report.append("")

        # Index Creation Performance
        if results.optimized_index_metrics:
            report.append("## Index Creation Performance")
            report.append("")
            report.append(
                "| Data Size | Profile | Distance Function | Creation Time (s) | Index Size |"
            )
            report.append(
                "|-----------|---------|-------------------|------------------|------------|"
            )

            for metric in results.optimized_index_metrics:
                if metric.success:
                    report.append(
                        f"| {metric.data_size:,} | {metric.optimization_profile} | "
                        f"{metric.distance_function} | {metric.creation_time_seconds:.2f} | "
                        f"{metric.index_size_human} |"
                    )
            report.append("")

        # Query Performance Summary
        if results.optimized_query_metrics:
            report.append("## Query Performance Summary")
            report.append("")
            report.append(
                "| Test | ef_search | Avg Latency (ms) | P95 Latency (ms) | QPS |"
            )
            report.append(
                "|------|-----------|------------------|------------------|-----|"
            )

            for metric in results.optimized_query_metrics:
                report.append(
                    f"| {metric.test_name} | {metric.ef_search} | "
                    f"{metric.avg_latency_ms:.2f} | {metric.p95_latency_ms:.2f} | "
                    f"{metric.queries_per_second:.1f} |"
                )
            report.append("")

        # System Information
        report.append("## System Information")
        report.append("")
        for key, value in results.system_info.items():
            report.append(f"- **{key.replace('_', ' ').title()}:** {value}")

        report.append("")

        # Configuration
        report.append("## Test Configuration")
        report.append("")
        config_dict = asdict(results.config)
        for key, value in config_dict.items():
            if not key.startswith("_"):
                report.append(f"- **{key.replace('_', ' ').title()}:** {value}")

        return "\n".join(report)


# CLI and utility functions
async def run_benchmark(
    output_dir: str = "./benchmark_results",
    quick_test: bool = False,
    verbose: bool = False,
) -> BenchmarkResults:
    """Run pgvector benchmark with specified parameters.

    Args:
        output_dir: Directory for benchmark results
        quick_test: Run abbreviated test for development
        verbose: Enable verbose logging

    Returns:
        Complete benchmark results
    """
    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.INFO)

    # Create configuration
    config = BenchmarkConfig(output_directory=output_dir)

    if quick_test:
        # Reduce test parameters for quick testing
        config.small_dataset_size = 100
        config.medium_dataset_size = 1000
        config.large_dataset_size = 5000
        config.benchmark_queries = 50
        config.warmup_queries = 10
        config.ef_search_values = [40, 100]
        config.optimization_profiles = [OptimizationProfile.BALANCED]
        config.distance_functions = [DistanceFunction.COSINE]

    # Run benchmark
    benchmark = PGVectorBenchmark(config)
    return await benchmark.run_full_benchmark()


if __name__ == "__main__":
    import sys

    # Simple CLI interface
    quick_test = "--quick" in sys.argv
    verbose = "--verbose" in sys.argv

    output_dir = "./benchmark_results"
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]

    # Run the benchmark
    asyncio.run(
        run_benchmark(output_dir=output_dir, quick_test=quick_test, verbose=verbose)
    )
