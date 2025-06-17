"""
Performance Metrics Collection and Analysis.

This module provides comprehensive performance metrics collection for validating
database optimization improvements including query performance, memory usage,
connection efficiency, and vector search performance.
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Dict, List, Optional

import numpy as np
import psutil

from .config import BenchmarkConfig

logger = logging.getLogger(__name__)


@dataclass
class TimingMetrics:
    """Timing metrics for performance operations."""

    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    operation_type: str = ""
    success: bool = True
    error_message: Optional[str] = None

    def __post_init__(self):
        """Calculate duration if end_time is set."""
        if self.end_time is not None and self.duration is None:
            self.duration = self.end_time - self.start_time

    def finish(self, success: bool = True, error_message: Optional[str] = None):
        """Mark the timing as finished."""
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message


@dataclass
class MemoryMetrics:
    """Memory usage metrics."""

    timestamp: float
    process_memory_mb: float
    system_memory_mb: float
    system_memory_percent: float
    peak_memory_mb: Optional[float] = None

    @classmethod
    def current(cls) -> "MemoryMetrics":
        """Get current memory metrics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        virtual_memory = psutil.virtual_memory()

        return cls(
            timestamp=time.perf_counter(),
            process_memory_mb=memory_info.rss / 1024 / 1024,
            system_memory_mb=virtual_memory.total / 1024 / 1024,
            system_memory_percent=virtual_memory.percent,
        )


@dataclass
class ConnectionMetrics:
    """Connection pool and database connection metrics."""

    timestamp: float
    active_connections: int
    idle_connections: int
    total_connections: int
    pool_utilization: float
    connection_wait_time: float = 0.0
    connection_reuse_count: int = 0
    connection_creation_count: int = 0

    @property
    def efficiency_ratio(self) -> float:
        """Calculate connection efficiency (reuse vs creation)."""
        total_ops = self.connection_reuse_count + self.connection_creation_count
        if total_ops == 0:
            return 0.0
        return self.connection_reuse_count / total_ops


@dataclass
class VectorSearchMetrics:
    """Vector search specific performance metrics."""

    timestamp: float
    query_time: float
    index_type: str
    ef_search: Optional[int] = None
    recall_score: Optional[float] = None
    results_count: int = 0
    memory_usage_mb: float = 0.0
    index_size_mb: float = 0.0

    @property
    def queries_per_second(self) -> float:
        """Calculate queries per second."""
        if self.query_time <= 0:
            return 0.0
        return 1.0 / self.query_time


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    timestamp: float
    hit_count: int = 0
    miss_count: int = 0
    hit_ratio: float = 0.0
    avg_hit_time: float = 0.0
    avg_miss_time: float = 0.0
    cache_size_mb: float = 0.0
    eviction_count: int = 0

    def __post_init__(self):
        """Calculate hit ratio."""
        total = self.hit_count + self.miss_count
        if total > 0:
            self.hit_ratio = self.hit_count / total


class PerformanceMetricsCollector:
    """
    Comprehensive performance metrics collector for database optimization validation.

    Collects and analyzes:
    - Query execution timing and throughput
    - Memory usage and optimization
    - Connection pool efficiency
    - Vector search performance
    - Cache effectiveness
    - Geographic routing performance
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize the metrics collector.

        Args:
            config: Benchmark configuration or None for defaults
        """
        self.config = config or BenchmarkConfig()
        self.thresholds = self.config.performance_thresholds

        # Metrics storage
        self._timing_metrics: List[TimingMetrics] = []
        self._memory_metrics: List[MemoryMetrics] = []
        self._connection_metrics: List[ConnectionMetrics] = []
        self._vector_metrics: List[VectorSearchMetrics] = []
        self._cache_metrics: List[CacheMetrics] = []

        # Real-time tracking
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._active_timings: Dict[str, TimingMetrics] = {}

        # Performance windows for trending
        self._performance_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )

        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._start_time = time.perf_counter()

        logger.info("Performance metrics collector initialized")

    async def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._start_time = time.perf_counter()

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop continuous performance monitoring."""
        self._monitoring_active = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Continuous monitoring loop."""
        try:
            while self._monitoring_active:
                # Collect system metrics
                if self.config.enable_memory_profiling:
                    memory_metrics = MemoryMetrics.current()
                    self._memory_metrics.append(memory_metrics)

                # Update performance windows
                self._update_performance_windows()

                # Sleep for the configured interval
                await asyncio.sleep(self.config.metrics_collection_interval)

        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

    def _update_performance_windows(self) -> None:
        """Update rolling performance windows for trending analysis."""
        current_time = time.perf_counter()

        # Calculate current throughput for different operation types
        for operation_type, count in self._operation_counts.items():
            self._performance_windows[f"{operation_type}_throughput"].append(
                (current_time, count)
            )

        # Calculate current error rates
        for operation_type, error_count in self._error_counts.items():
            total_count = self._operation_counts.get(operation_type, 0)
            error_rate = error_count / max(total_count, 1)
            self._performance_windows[f"{operation_type}_error_rate"].append(
                (current_time, error_rate)
            )

    def start_timing(self, operation_id: str, operation_type: str) -> str:
        """Start timing an operation.

        Args:
            operation_id: Unique identifier for this operation
            operation_type: Type of operation being timed

        Returns:
            Timing ID for finishing the operation
        """
        timing = TimingMetrics(
            start_time=time.perf_counter(), operation_type=operation_type
        )
        self._active_timings[operation_id] = timing
        return operation_id

    def finish_timing(
        self,
        operation_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[TimingMetrics]:
        """Finish timing an operation.

        Args:
            operation_id: Operation ID from start_timing
            success: Whether the operation succeeded
            error_message: Error message if operation failed
            additional_data: Additional timing data

        Returns:
            Completed timing metrics or None if operation_id not found
        """
        if operation_id not in self._active_timings:
            logger.warning(f"No active timing found for operation {operation_id}")
            return None

        timing = self._active_timings.pop(operation_id)
        timing.finish(success, error_message)

        # Update counters
        self._operation_counts[timing.operation_type] += 1
        if not success:
            self._error_counts[timing.operation_type] += 1

        # Store timing
        self._timing_metrics.append(timing)

        return timing

    def record_connection_metrics(self, metrics: ConnectionMetrics) -> None:
        """Record connection pool metrics."""
        self._connection_metrics.append(metrics)

    def record_vector_search_metrics(self, metrics: VectorSearchMetrics) -> None:
        """Record vector search performance metrics."""
        self._vector_metrics.append(metrics)

    def record_cache_metrics(self, metrics: CacheMetrics) -> None:
        """Record cache performance metrics."""
        self._cache_metrics.append(metrics)

    def get_query_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive query performance summary."""
        if not self._timing_metrics:
            return {"error": "No timing metrics available"}

        # Filter successful operations
        successful_timings = [
            t for t in self._timing_metrics if t.success and t.duration is not None
        ]

        if not successful_timings:
            return {"error": "No successful operations recorded"}

        durations = [t.duration for t in successful_timings]

        # Calculate percentiles using numpy
        durations_array = np.array(durations)

        summary = {
            "total_operations": len(self._timing_metrics),
            "successful_operations": len(successful_timings),
            "error_rate": 1 - (len(successful_timings) / len(self._timing_metrics)),
            "duration_stats": {
                "mean": float(np.mean(durations_array)),
                "median": float(np.median(durations_array)),
                "std_dev": float(np.std(durations_array)),
                "min": float(np.min(durations_array)),
                "max": float(np.max(durations_array)),
                "p95": float(np.percentile(durations_array, 95)),
                "p99": float(np.percentile(durations_array, 99)),
            },
            "throughput": {
                "operations_per_second": len(successful_timings)
                / (time.perf_counter() - self._start_time),
                "total_duration": time.perf_counter() - self._start_time,
            },
        }

        # Per-operation type breakdown
        operation_types = {}
        for operation_type in set(t.operation_type for t in successful_timings):
            type_timings = [
                t for t in successful_timings if t.operation_type == operation_type
            ]
            type_durations = np.array([t.duration for t in type_timings])

            operation_types[operation_type] = {
                "count": len(type_timings),
                "mean_duration": float(np.mean(type_durations)),
                "p95_duration": float(np.percentile(type_durations, 95)),
                "ops_per_second": len(type_timings)
                / (time.perf_counter() - self._start_time),
            }

        summary["by_operation_type"] = operation_types
        return summary

    def get_memory_performance_summary(self) -> Dict[str, Any]:
        """Get memory usage performance summary."""
        if not self._memory_metrics:
            return {"error": "No memory metrics available"}

        process_memory = [m.process_memory_mb for m in self._memory_metrics]
        process_memory_array = np.array(process_memory)

        return {
            "process_memory_mb": {
                "current": process_memory[-1],
                "peak": float(np.max(process_memory_array)),
                "average": float(np.mean(process_memory_array)),
                "min": float(np.min(process_memory_array)),
            },
            "memory_efficiency": {
                "peak_to_average_ratio": float(
                    np.max(process_memory_array) / np.mean(process_memory_array)
                ),
                "memory_growth": process_memory[-1] - process_memory[0]
                if len(process_memory) > 1
                else 0,
            },
            "system_memory": {
                "total_mb": self._memory_metrics[-1].system_memory_mb,
                "current_usage_percent": self._memory_metrics[-1].system_memory_percent,
            },
        }

    def get_connection_performance_summary(self) -> Dict[str, Any]:
        """Get connection pool performance summary."""
        if not self._connection_metrics:
            return {"error": "No connection metrics available"}

        recent_metrics = self._connection_metrics[-10:]  # Last 10 samples

        utilizations = [m.pool_utilization for m in recent_metrics]
        wait_times = [m.connection_wait_time for m in recent_metrics]
        efficiency_ratios = [m.efficiency_ratio for m in recent_metrics]

        return {
            "pool_utilization": {
                "current": recent_metrics[-1].pool_utilization,
                "average": mean(utilizations),
                "max": max(utilizations),
            },
            "connection_efficiency": {
                "current_efficiency_ratio": recent_metrics[-1].efficiency_ratio,
                "average_efficiency_ratio": mean(efficiency_ratios),
                "total_reuses": sum(m.connection_reuse_count for m in recent_metrics),
                "total_creations": sum(
                    m.connection_creation_count for m in recent_metrics
                ),
            },
            "wait_times": {
                "current_wait_time": recent_metrics[-1].connection_wait_time,
                "average_wait_time": mean(wait_times),
                "max_wait_time": max(wait_times),
            },
            "connections": {
                "active": recent_metrics[-1].active_connections,
                "idle": recent_metrics[-1].idle_connections,
                "total": recent_metrics[-1].total_connections,
            },
        }

    def get_vector_search_performance_summary(self) -> Dict[str, Any]:
        """Get vector search performance summary."""
        if not self._vector_metrics:
            return {"error": "No vector search metrics available"}

        query_times = [m.query_time for m in self._vector_metrics]
        query_times_array = np.array(query_times)

        # Group by index type
        by_index_type = {}
        for index_type in set(m.index_type for m in self._vector_metrics):
            type_metrics = [
                m for m in self._vector_metrics if m.index_type == index_type
            ]
            type_times = np.array([m.query_time for m in type_metrics])

            by_index_type[index_type] = {
                "count": len(type_metrics),
                "mean_query_time": float(np.mean(type_times)),
                "p95_query_time": float(np.percentile(type_times, 95)),
                "queries_per_second": float(
                    np.mean([m.queries_per_second for m in type_metrics])
                ),
                "average_recall": float(
                    np.mean(
                        [
                            m.recall_score
                            for m in type_metrics
                            if m.recall_score is not None
                        ]
                    )
                )
                if any(m.recall_score for m in type_metrics)
                else None,
            }

        return {
            "overall": {
                "total_searches": len(self._vector_metrics),
                "mean_query_time": float(np.mean(query_times_array)),
                "p95_query_time": float(np.percentile(query_times_array, 95)),
                "average_qps": float(
                    np.mean([m.queries_per_second for m in self._vector_metrics])
                ),
            },
            "by_index_type": by_index_type,
            "memory_usage": {
                "average_mb": float(
                    np.mean([m.memory_usage_mb for m in self._vector_metrics])
                ),
                "peak_mb": float(
                    np.max([m.memory_usage_mb for m in self._vector_metrics])
                ),
            },
        }

    def get_cache_performance_summary(self) -> Dict[str, Any]:
        """Get cache performance summary."""
        if not self._cache_metrics:
            return {"error": "No cache metrics available"}

        recent_metrics = self._cache_metrics[-10:]  # Last 10 samples

        hit_ratios = [m.hit_ratio for m in recent_metrics]
        hit_times = [m.avg_hit_time for m in recent_metrics if m.avg_hit_time > 0]
        miss_times = [m.avg_miss_time for m in recent_metrics if m.avg_miss_time > 0]

        return {
            "hit_ratio": {
                "current": recent_metrics[-1].hit_ratio,
                "average": mean(hit_ratios),
                "target": self.thresholds.cache_hit_ratio_target,
                "meets_target": mean(hit_ratios)
                >= self.thresholds.cache_hit_ratio_target,
            },
            "response_times": {
                "average_hit_time": mean(hit_times) if hit_times else 0,
                "average_miss_time": mean(miss_times) if miss_times else 0,
                "target_response_time": self.thresholds.cache_response_time_max,
            },
            "cache_efficiency": {
                "total_hits": sum(m.hit_count for m in recent_metrics),
                "total_misses": sum(m.miss_count for m in recent_metrics),
                "eviction_count": sum(m.eviction_count for m in recent_metrics),
                "cache_size_mb": recent_metrics[-1].cache_size_mb,
            },
        }

    def validate_performance_improvements(
        self, baseline_metrics: Optional["PerformanceMetricsCollector"] = None
    ) -> Dict[str, Any]:
        """Validate performance improvements against thresholds and baseline.

        Args:
            baseline_metrics: Baseline metrics collector for comparison

        Returns:
            Validation results with improvement ratios and threshold compliance
        """
        validation_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validation_passed": True,
            "improvements": {},
            "threshold_compliance": {},
            "recommendations": [],
        }

        # Get current performance summaries
        query_summary = self.get_query_performance_summary()
        self.get_memory_performance_summary()
        vector_summary = self.get_vector_search_performance_summary()
        cache_summary = self.get_cache_performance_summary()
        connection_summary = self.get_connection_performance_summary()

        # Validate query performance improvements
        if baseline_metrics:
            baseline_query = baseline_metrics.get_query_performance_summary()

            if "duration_stats" in query_summary and "duration_stats" in baseline_query:
                current_p95 = query_summary["duration_stats"]["p95"]
                baseline_p95 = baseline_query["duration_stats"]["p95"]
                improvement_ratio = (
                    baseline_p95 / current_p95 if current_p95 > 0 else float("inf")
                )

                validation_results["improvements"]["query_performance"] = {
                    "improvement_ratio": improvement_ratio,
                    "target_improvement": self.thresholds.query_performance_improvement,
                    "meets_target": improvement_ratio
                    >= self.thresholds.query_performance_improvement
                    - self.thresholds.query_performance_tolerance,
                    "current_p95_ms": current_p95 * 1000,
                    "baseline_p95_ms": baseline_p95 * 1000,
                }

                if (
                    improvement_ratio
                    < self.thresholds.query_performance_improvement
                    - self.thresholds.query_performance_tolerance
                ):
                    validation_results["validation_passed"] = False
                    validation_results["recommendations"].append(
                        f"Query performance improvement ({improvement_ratio:.1f}x) "
                        f"is below target ({self.thresholds.query_performance_improvement}x)"
                    )

        # Validate vector search improvements
        if baseline_metrics and "overall" in vector_summary:
            baseline_vector = baseline_metrics.get_vector_search_performance_summary()

            if "overall" in baseline_vector:
                current_qps = vector_summary["overall"]["average_qps"]
                baseline_qps = baseline_vector["overall"]["average_qps"]
                vector_improvement = (
                    current_qps / baseline_qps if baseline_qps > 0 else float("inf")
                )

                validation_results["improvements"]["vector_search"] = {
                    "improvement_ratio": vector_improvement,
                    "target_improvement": (
                        self.thresholds.vector_performance_improvement
                    ),
                    "meets_target": vector_improvement
                    >= self.thresholds.vector_performance_improvement
                    - self.thresholds.vector_performance_tolerance,
                    "current_qps": current_qps,
                    "baseline_qps": baseline_qps,
                }

                if (
                    vector_improvement
                    < self.thresholds.vector_performance_improvement
                    - self.thresholds.vector_performance_tolerance
                ):
                    validation_results["validation_passed"] = False
                    validation_results["recommendations"].append(
                        f"Vector search improvement ({vector_improvement:.1f}x) "
                        f"is below target ({self.thresholds.vector_performance_improvement}x)"
                    )

        # Validate cache performance
        if "hit_ratio" in cache_summary:
            cache_hit_ratio = cache_summary["hit_ratio"]["average"]
            cache_meets_target = (
                cache_hit_ratio >= self.thresholds.cache_hit_ratio_target
            )

            validation_results["threshold_compliance"]["cache_hit_ratio"] = {
                "current": cache_hit_ratio,
                "target": self.thresholds.cache_hit_ratio_target,
                "meets_target": cache_meets_target,
            }

            if not cache_meets_target:
                validation_results["validation_passed"] = False
                validation_results["recommendations"].append(
                    f"Cache hit ratio ({cache_hit_ratio:.1%}) is below target "
                    f"({self.thresholds.cache_hit_ratio_target:.1%})"
                )

        # Validate connection pool efficiency
        if "connection_efficiency" in connection_summary:
            efficiency_ratio = connection_summary["connection_efficiency"][
                "average_efficiency_ratio"
            ]
            efficiency_meets_target = (
                efficiency_ratio >= self.thresholds.connection_reuse_ratio
            )

            validation_results["threshold_compliance"]["connection_efficiency"] = {
                "current": efficiency_ratio,
                "target": self.thresholds.connection_reuse_ratio,
                "meets_target": efficiency_meets_target,
            }

            if not efficiency_meets_target:
                validation_results["validation_passed"] = False
                validation_results["recommendations"].append(
                    f"Connection efficiency ({efficiency_ratio:.1%}) is below target "
                    f"({self.thresholds.connection_reuse_ratio:.1%})"
                )

        return validation_results

    def get_comprehensive_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all collected metrics."""
        return {
            "collection_period": {
                "start_time": self._start_time,
                "duration_seconds": time.perf_counter() - self._start_time,
                "metrics_count": {
                    "timing": len(self._timing_metrics),
                    "memory": len(self._memory_metrics),
                    "connection": len(self._connection_metrics),
                    "vector_search": len(self._vector_metrics),
                    "cache": len(self._cache_metrics),
                },
            },
            "query_performance": self.get_query_performance_summary(),
            "memory_performance": self.get_memory_performance_summary(),
            "connection_performance": self.get_connection_performance_summary(),
            "vector_search_performance": self.get_vector_search_performance_summary(),
            "cache_performance": self.get_cache_performance_summary(),
        }

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self._timing_metrics.clear()
        self._memory_metrics.clear()
        self._connection_metrics.clear()
        self._vector_metrics.clear()
        self._cache_metrics.clear()
        self._operation_counts.clear()
        self._error_counts.clear()
        self._active_timings.clear()
        self._performance_windows.clear()
        self._start_time = time.perf_counter()

        logger.info("Performance metrics reset")
