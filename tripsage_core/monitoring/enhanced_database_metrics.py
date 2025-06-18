"""
Enhanced Database Metrics for TripSage Core.

This module provides comprehensive Prometheus metrics for database operations:
- Connection pool utilization and health
- Query latency percentiles (P50, P95, P99)
- Connection validation metrics
- Performance regression detection
- Resource utilization tracking
- Error rate monitoring
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Database metric types."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceBaseline:
    """Performance baseline for regression detection."""
    
    metric_name: str
    p50: float
    p95: float
    p99: float
    mean: float
    std_dev: float
    sample_count: int
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_regression(self, value: float, threshold_multiplier: float = 2.0) -> bool:
        """Check if value represents a performance regression."""
        if self.sample_count < 10:  # Need enough samples
            return False
        
        # Consider it a regression if value is significantly higher than P95
        return value > (self.p95 * threshold_multiplier)
    
    def update_baseline(self, values: List[float]):
        """Update baseline with new values."""
        if not values:
            return
        
        values.sort()
        n = len(values)
        
        self.p50 = values[int(n * 0.5)]
        self.p95 = values[int(n * 0.95)]
        self.p99 = values[int(n * 0.99)]
        self.mean = sum(values) / n
        
        # Calculate standard deviation
        variance = sum((x - self.mean) ** 2 for x in values) / n
        self.std_dev = variance ** 0.5
        
        self.sample_count = n
        self.last_updated = datetime.now(timezone.utc)


@dataclass
class PerformanceAlert:
    """Performance regression alert."""
    
    metric_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_p95: float
    threshold_multiplier: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


class EnhancedDatabaseMetrics:
    """
    Enhanced database metrics with comprehensive Prometheus integration.
    
    Features:
    - Connection pool metrics with utilization tracking
    - Query latency percentiles (P50, P95, P99)
    - Connection health and validation metrics
    - Performance regression detection
    - Resource utilization monitoring
    - Error rate tracking
    - Custom metric collection
    """
    
    def __init__(
        self,
        metrics_registry=None,
        baseline_window_size: int = 1000,
        regression_threshold: float = 2.0,
        enable_regression_detection: bool = True,
    ):
        """Initialize enhanced database metrics.
        
        Args:
            metrics_registry: Prometheus metrics registry
            baseline_window_size: Number of samples for baseline calculation
            regression_threshold: Multiplier for regression detection
            enable_regression_detection: Enable performance regression alerts
        """
        self.baseline_window_size = baseline_window_size
        self.regression_threshold = regression_threshold
        self.enable_regression_detection = enable_regression_detection
        
        # Metrics storage
        self._metric_samples: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=baseline_window_size)
        )
        self._baselines: Dict[str, PerformanceBaseline] = {}
        self._alerts: List[PerformanceAlert] = []
        
        # Prometheus metrics
        self.metrics = None
        if metrics_registry is not None:
            try:
                self.metrics = self._initialize_prometheus_metrics(metrics_registry)
                logger.info("Enhanced database metrics initialized with Prometheus")
            except ImportError:
                logger.warning("Prometheus client not available, enhanced metrics disabled")
        
        # Performance tracking
        self._start_time = time.time()
        self._total_queries = 0
        self._error_count = 0
    
    def _initialize_prometheus_metrics(self, registry):
        """Initialize comprehensive Prometheus metrics."""
        try:
            from prometheus_client import Counter, Gauge, Histogram, Summary, Info
            
            metrics = type("EnhancedMetrics", (), {})()
            
            # === CONNECTION POOL METRICS ===
            
            # Pool utilization and status
            metrics.pool_utilization_percent = Gauge(
                "tripsage_db_pool_utilization_percent",
                "Database connection pool utilization percentage",
                ["pool_id", "database"],
                registry=registry,
            )
            
            metrics.pool_connections = Gauge(
                "tripsage_db_pool_connections",
                "Database connection pool connections by status",
                ["pool_id", "database", "status"],
                registry=registry,
            )
            
            metrics.pool_connection_lifetime = Histogram(
                "tripsage_db_pool_connection_lifetime_seconds",
                "Connection lifetime in the pool",
                ["pool_id", "database"],
                registry=registry,
                buckets=(1, 5, 10, 30, 60, 300, 900, 1800, 3600, 7200),
            )
            
            # Connection operations
            metrics.pool_checkout_duration = Histogram(
                "tripsage_db_pool_checkout_duration_seconds",
                "Time to checkout connection from pool",
                ["pool_id", "database", "result"],
                registry=registry,
                buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
            )
            
            metrics.pool_operations = Counter(
                "tripsage_db_pool_operations_total",
                "Total pool operations by type and result",
                ["pool_id", "database", "operation", "result"],
                registry=registry,
            )
            
            # === QUERY PERFORMANCE METRICS ===
            
            # Query latency with detailed percentiles
            metrics.query_duration = Histogram(
                "tripsage_db_query_duration_seconds",
                "Database query execution time with percentiles",
                ["database", "operation", "table", "pool_id"],
                registry=registry,
                buckets=(
                    0.0001, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05,
                    0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0
                ),
            )
            
            # Query latency percentiles (custom tracking)
            metrics.query_latency_p50 = Gauge(
                "tripsage_db_query_latency_p50_seconds",
                "50th percentile query latency",
                ["database", "operation", "table"],
                registry=registry,
            )
            
            metrics.query_latency_p95 = Gauge(
                "tripsage_db_query_latency_p95_seconds", 
                "95th percentile query latency",
                ["database", "operation", "table"],
                registry=registry,
            )
            
            metrics.query_latency_p99 = Gauge(
                "tripsage_db_query_latency_p99_seconds",
                "99th percentile query latency", 
                ["database", "operation", "table"],
                registry=registry,
            )
            
            # Query volume and success rate
            metrics.queries_total = Counter(
                "tripsage_db_queries_total",
                "Total database queries executed",
                ["database", "operation", "table", "status"],
                registry=registry,
            )
            
            metrics.query_error_rate = Gauge(
                "tripsage_db_query_error_rate",
                "Query error rate (errors per total queries)",
                ["database", "operation", "table"],
                registry=registry,
            )
            
            # === CONNECTION HEALTH METRICS ===
            
            metrics.connection_validation_duration = Histogram(
                "tripsage_db_connection_validation_duration_seconds",
                "Connection validation time",
                ["pool_id", "database", "result"],
                registry=registry,
                buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            )
            
            metrics.connection_health_score = Gauge(
                "tripsage_db_connection_health_score",
                "Connection health score (0-1, 1 = healthy)",
                ["pool_id", "database", "connection_id"],
                registry=registry,
            )
            
            metrics.connection_errors = Counter(
                "tripsage_db_connection_errors_total",
                "Total connection errors by type",
                ["pool_id", "database", "error_type"],
                registry=registry,
            )
            
            # === PERFORMANCE REGRESSION METRICS ===
            
            metrics.performance_regression_alerts = Counter(
                "tripsage_db_performance_regression_alerts_total",
                "Performance regression alerts triggered",
                ["metric_name", "severity"],
                registry=registry,
            )
            
            metrics.baseline_deviation = Gauge(
                "tripsage_db_baseline_deviation_ratio",
                "Current performance vs baseline ratio (>1 = degradation)",
                ["metric_name"],
                registry=registry,
            )
            
            # === RESOURCE UTILIZATION METRICS ===
            
            metrics.memory_usage = Gauge(
                "tripsage_db_memory_usage_bytes",
                "Database-related memory usage",
                ["component"],
                registry=registry,
            )
            
            metrics.cpu_usage = Gauge(
                "tripsage_db_cpu_usage_percent",
                "Database-related CPU usage percentage",
                ["component"],
                registry=registry,
            )
            
            # === TRANSACTION METRICS ===
            
            metrics.transaction_duration = Histogram(
                "tripsage_db_transaction_duration_seconds",
                "Database transaction duration",
                ["database", "isolation_level"],
                registry=registry,
                buckets=(0.001, 0.01, 0.1, 1.0, 10.0, 60.0, 300.0),
            )
            
            metrics.transaction_rollbacks = Counter(
                "tripsage_db_transaction_rollbacks_total",
                "Total transaction rollbacks",
                ["database", "reason"],
                registry=registry,
            )
            
            # === CACHE METRICS (for connection caching) ===
            
            metrics.cache_hit_rate = Gauge(
                "tripsage_db_cache_hit_rate",
                "Database connection cache hit rate",
                ["cache_type"],
                registry=registry,
            )
            
            metrics.cache_size = Gauge(
                "tripsage_db_cache_size_bytes",
                "Database connection cache size",
                ["cache_type"],
                registry=registry,
            )
            
            # === INFO METRICS ===
            
            metrics.build_info = Info(
                "tripsage_db_build_info",
                "Database service build information",
                registry=registry,
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced Prometheus metrics: {e}")
            return None
    
    def record_query_duration(
        self,
        duration: float,
        operation: str,
        table: str = "unknown",
        database: str = "supabase",
        pool_id: str = "default",
        status: str = "success",
    ):
        """Record query execution duration with percentile tracking."""
        self._total_queries += 1
        
        if status != "success":
            self._error_count += 1
        
        # Record in Prometheus if available
        if self.metrics:
            self.metrics.query_duration.labels(
                database=database,
                operation=operation,
                table=table,
                pool_id=pool_id,
            ).observe(duration)
            
            self.metrics.queries_total.labels(
                database=database,
                operation=operation,
                table=table,
                status=status,
            ).inc()
        
        # Update percentile tracking
        metric_key = f"query_duration_{operation}_{table}"
        self._metric_samples[metric_key].append(duration)
        
        # Update percentiles if we have enough samples
        if len(self._metric_samples[metric_key]) >= 10:
            self._update_percentiles(metric_key, operation, table, database)
        
        # Check for performance regression
        if self.enable_regression_detection:
            self._check_performance_regression(metric_key, duration)
    
    def record_pool_utilization(
        self,
        utilization_percent: float,
        active_connections: int,
        idle_connections: int,
        total_connections: int,
        pool_id: str = "default",
        database: str = "supabase",
    ):
        """Record connection pool utilization metrics."""
        if not self.metrics:
            return
        
        self.metrics.pool_utilization_percent.labels(
            pool_id=pool_id,
            database=database,
        ).set(utilization_percent)
        
        self.metrics.pool_connections.labels(
            pool_id=pool_id,
            database=database,
            status="active",
        ).set(active_connections)
        
        self.metrics.pool_connections.labels(
            pool_id=pool_id,
            database=database,
            status="idle", 
        ).set(idle_connections)
        
        self.metrics.pool_connections.labels(
            pool_id=pool_id,
            database=database,
            status="total",
        ).set(total_connections)
    
    def record_connection_health(
        self,
        connection_id: str,
        health_score: float,
        validation_duration: Optional[float] = None,
        validation_result: str = "success",
        pool_id: str = "default",
        database: str = "supabase",
    ):
        """Record connection health metrics."""
        if not self.metrics:
            return
        
        self.metrics.connection_health_score.labels(
            pool_id=pool_id,
            database=database,
            connection_id=connection_id,
        ).set(health_score)
        
        if validation_duration is not None:
            self.metrics.connection_validation_duration.labels(
                pool_id=pool_id,
                database=database,
                result=validation_result,
            ).observe(validation_duration)
    
    def record_checkout_duration(
        self,
        duration: float,
        result: str = "success",
        pool_id: str = "default",
        database: str = "supabase",
    ):
        """Record connection checkout duration."""
        if not self.metrics:
            return
        
        self.metrics.pool_checkout_duration.labels(
            pool_id=pool_id,
            database=database,
            result=result,
        ).observe(duration)
        
        self.metrics.pool_operations.labels(
            pool_id=pool_id,
            database=database,
            operation="checkout",
            result=result,
        ).inc()
    
    def record_connection_error(
        self,
        error_type: str,
        pool_id: str = "default",
        database: str = "supabase",
    ):
        """Record connection error."""
        if not self.metrics:
            return
        
        self.metrics.connection_errors.labels(
            pool_id=pool_id,
            database=database,
            error_type=error_type,
        ).inc()
    
    def record_transaction_duration(
        self,
        duration: float,
        isolation_level: str = "read_committed",
        database: str = "supabase",
    ):
        """Record transaction duration."""
        if not self.metrics:
            return
        
        self.metrics.transaction_duration.labels(
            database=database,
            isolation_level=isolation_level,
        ).observe(duration)
    
    def record_transaction_rollback(
        self,
        reason: str,
        database: str = "supabase",
    ):
        """Record transaction rollback."""
        if not self.metrics:
            return
        
        self.metrics.transaction_rollbacks.labels(
            database=database,
            reason=reason,
        ).inc()
    
    def _update_percentiles(
        self,
        metric_key: str,
        operation: str,
        table: str,
        database: str,
    ):
        """Update percentile metrics."""
        if not self.metrics:
            return
        
        samples = list(self._metric_samples[metric_key])
        samples.sort()
        n = len(samples)
        
        if n == 0:
            return
        
        p50 = samples[int(n * 0.5)]
        p95 = samples[int(n * 0.95)] 
        p99 = samples[int(n * 0.99)]
        
        self.metrics.query_latency_p50.labels(
            database=database,
            operation=operation,
            table=table,
        ).set(p50)
        
        self.metrics.query_latency_p95.labels(
            database=database,
            operation=operation,
            table=table,
        ).set(p95)
        
        self.metrics.query_latency_p99.labels(
            database=database,
            operation=operation,
            table=table,
        ).set(p99)
        
        # Update baseline
        baseline = self._baselines.get(metric_key)
        if baseline is None:
            baseline = PerformanceBaseline(
                metric_name=metric_key,
                p50=p50,
                p95=p95,
                p99=p99,
                mean=sum(samples) / n,
                std_dev=0.0,
                sample_count=n,
            )
            self._baselines[metric_key] = baseline
        else:
            baseline.update_baseline(samples)
        
        # Update error rate
        if operation and table:
            error_rate = self._error_count / max(self._total_queries, 1)
            self.metrics.query_error_rate.labels(
                database=database,
                operation=operation,
                table=table,
            ).set(error_rate)
    
    def _check_performance_regression(self, metric_key: str, value: float):
        """Check for performance regression and trigger alerts."""
        baseline = self._baselines.get(metric_key)
        if baseline is None:
            return
        
        if baseline.is_regression(value, self.regression_threshold):
            severity = AlertSeverity.WARNING
            if value > (baseline.p99 * self.regression_threshold):
                severity = AlertSeverity.CRITICAL
            
            alert = PerformanceAlert(
                metric_name=metric_key,
                severity=severity,
                message=(
                    f"Performance regression detected: {metric_key} "
                    f"value {value:.3f}s exceeds baseline P95 {baseline.p95:.3f}s "
                    f"by {self.regression_threshold}x"
                ),
                current_value=value,
                baseline_p95=baseline.p95,
                threshold_multiplier=self.regression_threshold,
                details={
                    "baseline_p50": baseline.p50,
                    "baseline_p99": baseline.p99,
                    "baseline_mean": baseline.mean,
                    "sample_count": baseline.sample_count,
                },
            )
            
            self._alerts.append(alert)
            
            # Record alert in metrics
            if self.metrics:
                self.metrics.performance_regression_alerts.labels(
                    metric_name=metric_key,
                    severity=severity.value,
                ).inc()
                
                deviation_ratio = value / baseline.p95
                self.metrics.baseline_deviation.labels(
                    metric_name=metric_key,
                ).set(deviation_ratio)
            
            logger.warning(f"Performance regression alert: {alert.message}")
            
            # Keep only recent alerts
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]
    
    def get_recent_alerts(self, limit: int = 50) -> List[PerformanceAlert]:
        """Get recent performance alerts."""
        return self._alerts[-limit:] if self._alerts else []
    
    def get_baselines(self) -> Dict[str, PerformanceBaseline]:
        """Get current performance baselines."""
        return self._baselines.copy()
    
    def get_percentiles(self, metric_key: str) -> Optional[Tuple[float, float, float]]:
        """Get P50, P95, P99 for a metric."""
        if metric_key not in self._metric_samples:
            return None
        
        samples = list(self._metric_samples[metric_key])
        if len(samples) < 10:
            return None
        
        samples.sort()
        n = len(samples)
        
        return (
            samples[int(n * 0.5)],  # P50
            samples[int(n * 0.95)], # P95
            samples[int(n * 0.99)], # P99
        )
    
    def reset_baselines(self):
        """Reset all performance baselines (useful for testing)."""
        self._baselines.clear()
        self._metric_samples.clear()
        self._alerts.clear()
        logger.info("Performance baselines reset")
    
    def set_build_info(
        self,
        version: str,
        commit: str,
        build_date: str,
        python_version: str,
    ):
        """Set build information."""
        if not self.metrics:
            return
        
        self.metrics.build_info.info({
            "version": version,
            "commit": commit,
            "build_date": build_date,
            "python_version": python_version,
        })
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        uptime = time.time() - self._start_time
        error_rate = self._error_count / max(self._total_queries, 1)
        
        return {
            "uptime_seconds": uptime,
            "total_queries": self._total_queries,
            "error_count": self._error_count,
            "error_rate": error_rate,
            "active_baselines": len(self._baselines),
            "recent_alerts": len(self._alerts),
            "tracked_metrics": len(self._metric_samples),
            "regression_detection_enabled": self.enable_regression_detection,
            "regression_threshold": self.regression_threshold,
        }


# Global enhanced metrics instance
_enhanced_metrics: Optional[EnhancedDatabaseMetrics] = None


def get_enhanced_database_metrics(**kwargs) -> EnhancedDatabaseMetrics:
    """Get or create global enhanced database metrics instance."""
    global _enhanced_metrics
    
    if _enhanced_metrics is None:
        _enhanced_metrics = EnhancedDatabaseMetrics(**kwargs)
    
    return _enhanced_metrics


def reset_enhanced_database_metrics():
    """Reset global enhanced metrics instance (for testing)."""
    global _enhanced_metrics
    _enhanced_metrics = None