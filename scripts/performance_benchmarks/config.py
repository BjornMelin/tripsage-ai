"""
Configuration for performance benchmarking suite.

This module defines the configuration settings, thresholds, and parameters
for validating database performance optimizations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkType(str, Enum):
    """Types of performance benchmarks."""

    BASELINE = "baseline"  # Before optimization
    OPTIMIZED = "optimized"  # After optimization
    COMPARISON = "comparison"  # Side-by-side comparison


class OptimizationLevel(str, Enum):
    """Optimization levels to benchmark."""

    NONE = "none"  # No optimizations
    BASIC = "basic"  # Basic optimizations (indexes, connection pooling)
    ADVANCED = "advanced"  # Advanced optimizations (HNSW, compression)
    FULL = "full"  # All optimizations enabled


class WorkloadType(str, Enum):
    """Types of database workloads to benchmark."""

    READ_HEAVY = "read_heavy"  # 80% reads, 20% writes
    WRITE_HEAVY = "write_heavy"  # 20% reads, 80% writes
    BALANCED = "balanced"  # 50% reads, 50% writes
    VECTOR_SEARCH = "vector_search"  # Vector similarity searches
    ANALYTICS = "analytics"  # Complex analytical queries
    MIXED = "mixed"  # All operation types


@dataclass
class PerformanceThresholds:
    """Expected performance improvement thresholds."""

    # General query performance (claimed 3x improvement)
    query_performance_improvement: float = 3.0
    query_performance_tolerance: float = 0.5  # ±50% tolerance

    # pgvector performance (claimed 30x improvement)
    vector_performance_improvement: float = 30.0
    vector_performance_tolerance: float = 5.0  # ±5x tolerance

    # Memory usage (claimed 50% reduction)
    memory_reduction_target: float = 0.5
    memory_reduction_tolerance: float = 0.1  # ±10% tolerance

    # Connection pool efficiency thresholds
    connection_pool_efficiency: float = 0.85  # 85% pool utilization
    connection_reuse_ratio: float = 0.90  # 90% connection reuse

    # Cache hit ratio thresholds
    cache_hit_ratio_target: float = 0.80  # 80% cache hit ratio
    cache_response_time_max: float = 0.005  # 5ms max cache response

    # Throughput thresholds (queries per second)
    min_read_throughput: float = 1000.0
    min_write_throughput: float = 500.0
    min_vector_search_throughput: float = 100.0

    # Latency thresholds (milliseconds)
    max_read_latency_p95: float = 50.0
    max_write_latency_p95: float = 100.0
    max_vector_search_latency_p95: float = 200.0


class BenchmarkConfig(BaseModel):
    """Configuration for benchmark execution."""

    model_config = ConfigDict(from_attributes=True)

    # Test execution parameters
    warmup_iterations: int = Field(
        default=100, description="Warmup iterations before benchmarking"
    )
    benchmark_iterations: int = Field(
        default=1000, description="Number of benchmark iterations"
    )
    concurrent_connections: int = Field(
        default=10, description="Number of concurrent connections"
    )
    test_duration_seconds: int = Field(
        default=300, description="Maximum test duration in seconds"
    )

    # Data parameters
    test_data_size: int = Field(default=10000, description="Number of test records")
    vector_dimensions: int = Field(
        default=384, description="Vector embedding dimensions"
    )
    batch_size: int = Field(default=100, description="Batch size for bulk operations")

    # Performance monitoring
    metrics_collection_interval: float = Field(
        default=1.0, description="Metrics collection interval in seconds"
    )
    enable_detailed_metrics: bool = Field(
        default=True, description="Enable detailed performance metrics"
    )
    enable_memory_profiling: bool = Field(
        default=True, description="Enable memory usage profiling"
    )

    # Optimization settings
    optimization_levels: List[OptimizationLevel] = Field(
        default_factory=lambda: [OptimizationLevel.NONE, OptimizationLevel.FULL],
        description="Optimization levels to benchmark",
    )
    workload_types: List[WorkloadType] = Field(
        default_factory=lambda: [
            WorkloadType.READ_HEAVY,
            WorkloadType.VECTOR_SEARCH,
            WorkloadType.MIXED,
        ],
        description="Workload types to benchmark",
    )

    # Database configuration
    connection_pool_size: int = Field(default=20, description="Connection pool size")
    enable_read_replicas: bool = Field(
        default=True, description="Enable read replica testing"
    )
    enable_caching: bool = Field(default=True, description="Enable cache layer testing")

    # Vector search configuration
    vector_index_types: List[str] = Field(
        default_factory=lambda: ["none", "ivfflat", "hnsw"],
        description="Vector index types to benchmark",
    )
    hnsw_ef_search_values: List[int] = Field(
        default_factory=lambda: [40, 100, 200],
        description="HNSW ef_search values to benchmark",
    )

    # Geographic distribution simulation
    simulate_geographic_distribution: bool = Field(
        default=True, description="Simulate geographic distribution"
    )
    test_regions: List[str] = Field(
        default_factory=lambda: [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1",
        ],
        description="Regions to simulate for geographic routing",
    )

    # Reporting
    generate_html_report: bool = Field(
        default=True, description="Generate HTML performance report"
    )
    generate_csv_export: bool = Field(default=True, description="Export results to CSV")
    include_visualizations: bool = Field(
        default=True, description="Include performance charts"
    )

    # Thresholds
    performance_thresholds: PerformanceThresholds = Field(
        default_factory=PerformanceThresholds,
        description="Performance improvement thresholds",
    )


@dataclass
class BenchmarkScenario:
    """Definition of a benchmark scenario."""

    name: str
    description: str
    workload_type: WorkloadType
    optimization_level: OptimizationLevel
    duration_seconds: int
    concurrent_users: int
    operations_per_user: int
    data_size: int
    enable_monitoring: bool = True
    custom_config: Optional[Dict] = None


class DefaultScenarios:
    """Predefined benchmark scenarios for common use cases."""

    @staticmethod
    def get_baseline_scenarios() -> List[BenchmarkScenario]:
        """Get baseline benchmark scenarios (no optimizations)."""
        return [
            BenchmarkScenario(
                name="baseline_read_heavy",
                description="Baseline read-heavy workload without optimizations",
                workload_type=WorkloadType.READ_HEAVY,
                optimization_level=OptimizationLevel.NONE,
                duration_seconds=120,
                concurrent_users=10,
                operations_per_user=100,
                data_size=10000,
            ),
            BenchmarkScenario(
                name="baseline_vector_search",
                description="Baseline vector search without HNSW indexes",
                workload_type=WorkloadType.VECTOR_SEARCH,
                optimization_level=OptimizationLevel.NONE,
                duration_seconds=180,
                concurrent_users=5,
                operations_per_user=50,
                data_size=10000,
            ),
            BenchmarkScenario(
                name="baseline_mixed_workload",
                description="Baseline mixed workload without optimizations",
                workload_type=WorkloadType.MIXED,
                optimization_level=OptimizationLevel.NONE,
                duration_seconds=300,
                concurrent_users=10,
                operations_per_user=100,
                data_size=10000,
            ),
        ]

    @staticmethod
    def get_optimized_scenarios() -> List[BenchmarkScenario]:
        """Get optimized benchmark scenarios (full optimizations)."""
        return [
            BenchmarkScenario(
                name="optimized_read_heavy",
                description=(
                    "Optimized read-heavy workload with connection pooling and caching"
                ),
                workload_type=WorkloadType.READ_HEAVY,
                optimization_level=OptimizationLevel.FULL,
                duration_seconds=120,
                concurrent_users=10,
                operations_per_user=100,
                data_size=10000,
            ),
            BenchmarkScenario(
                name="optimized_vector_search",
                description=(
                    "Optimized vector search with HNSW indexes and halfvec compression"
                ),
                workload_type=WorkloadType.VECTOR_SEARCH,
                optimization_level=OptimizationLevel.FULL,
                duration_seconds=180,
                concurrent_users=5,
                operations_per_user=50,
                data_size=10000,
            ),
            BenchmarkScenario(
                name="optimized_mixed_workload",
                description="Optimized mixed workload with all optimizations enabled",
                workload_type=WorkloadType.MIXED,
                optimization_level=OptimizationLevel.FULL,
                duration_seconds=300,
                concurrent_users=10,
                operations_per_user=100,
                data_size=10000,
            ),
        ]

    @staticmethod
    def get_high_concurrency_scenarios() -> List[BenchmarkScenario]:
        """Get high-concurrency benchmark scenarios."""
        return [
            BenchmarkScenario(
                name="high_concurrency_reads",
                description="High-concurrency read workload with replica routing",
                workload_type=WorkloadType.READ_HEAVY,
                optimization_level=OptimizationLevel.FULL,
                duration_seconds=180,
                concurrent_users=50,
                operations_per_user=100,
                data_size=20000,
            ),
            BenchmarkScenario(
                name="high_concurrency_vector_search",
                description="High-concurrency vector search with optimized indexes",
                workload_type=WorkloadType.VECTOR_SEARCH,
                optimization_level=OptimizationLevel.FULL,
                duration_seconds=240,
                concurrent_users=25,
                operations_per_user=50,
                data_size=20000,
            ),
        ]

    @staticmethod
    def get_all_scenarios() -> List[BenchmarkScenario]:
        """Get all predefined benchmark scenarios."""
        scenarios = []
        scenarios.extend(DefaultScenarios.get_baseline_scenarios())
        scenarios.extend(DefaultScenarios.get_optimized_scenarios())
        scenarios.extend(DefaultScenarios.get_high_concurrency_scenarios())
        return scenarios


# Global configuration instance
DEFAULT_BENCHMARK_CONFIG = BenchmarkConfig()
DEFAULT_PERFORMANCE_THRESHOLDS = PerformanceThresholds()
