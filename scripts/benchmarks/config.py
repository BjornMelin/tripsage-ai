"""Simple configuration for TripSage performance benchmarking.

Focused on core optimization claims:
- 3x general query performance improvement
- 30x pgvector performance improvement
- 50% memory reduction
- Connection pool efficiency
"""

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class WorkloadType(str, Enum):
    """Types of database workloads to benchmark."""

    READ_HEAVY = "read_heavy"
    VECTOR_SEARCH = "vector_search"
    MIXED = "mixed"


class OptimizationLevel(str, Enum):
    """Optimization levels to benchmark."""

    NONE = "none"  # Baseline without optimizations
    FULL = "full"  # All optimizations enabled


@dataclass
class PerformanceThresholds:
    """Performance improvement thresholds for validation."""

    # Core optimization claims
    query_performance_improvement: float = 3.0  # Claimed 3x improvement
    vector_performance_improvement: float = 30.0  # Claimed 30x improvement
    memory_reduction_target: float = 0.5  # Claimed 50% reduction

    # Efficiency targets
    connection_reuse_ratio: float = 0.80  # 80% connection reuse
    cache_hit_ratio_target: float = 0.75  # 75% cache hit ratio

    # Performance tolerances (for validation)
    query_performance_tolerance: float = 0.5  # ±50% tolerance
    vector_performance_tolerance: float = 5.0  # ±5x tolerance
    memory_reduction_tolerance: float = 0.1  # ±10% tolerance


class BenchmarkConfig(BaseModel):
    """Simple benchmark configuration focused on core metrics."""

    model_config = ConfigDict(from_attributes=True)

    # Test execution
    benchmark_iterations: int = Field(
        default=500, description="Number of benchmark iterations"
    )
    concurrent_connections: int = Field(
        default=10, description="Concurrent connections"
    )
    test_duration_seconds: int = Field(
        default=300, description="Max test duration in seconds"
    )

    # Data parameters
    test_data_size: int = Field(default=10000, description="Number of test records")
    vector_dimensions: int = Field(
        default=384, description="Vector embedding dimensions"
    )

    # Monitoring
    enable_memory_profiling: bool = Field(
        default=True, description="Enable memory profiling"
    )
    metrics_collection_interval: float = Field(
        default=1.0, description="Metrics interval in seconds"
    )

    # Testing scope
    workload_types: list[WorkloadType] = Field(
        default_factory=lambda: [
            WorkloadType.READ_HEAVY,
            WorkloadType.VECTOR_SEARCH,
            WorkloadType.MIXED,
        ],
        description="Workload types to test",
    )
    optimization_levels: list[OptimizationLevel] = Field(
        default_factory=lambda: [OptimizationLevel.NONE, OptimizationLevel.FULL],
        description="Optimization levels to compare",
    )

    # Reporting
    generate_html_report: bool = Field(default=True, description="Generate HTML report")
    generate_csv_export: bool = Field(default=True, description="Export CSV results")

    # Performance thresholds
    performance_thresholds: PerformanceThresholds = Field(
        default_factory=PerformanceThresholds,
        description="Performance validation thresholds",
    )


# Default configuration instance
DEFAULT_BENCHMARK_CONFIG = BenchmarkConfig()
DEFAULT_PERFORMANCE_THRESHOLDS = PerformanceThresholds()
