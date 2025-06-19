"""
Performance Regression Detection Service for TripSage Core.

This module provides automated performance regression detection:
- Statistical analysis of query performance trends
- Automated baseline establishment and updating
- Real-time anomaly detection
- Performance degradation alerts
- Adaptive thresholds based on historical data
- Integration with monitoring and alerting systems
"""

import asyncio
import logging
import statistics
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RegressionSeverity(Enum):
    """Severity levels for performance regressions."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TrendDirection(Enum):
    """Performance trend directions."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


@dataclass
class PerformanceDataPoint:
    """Individual performance measurement."""

    timestamp: datetime
    value: float
    operation: str
    table: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_minutes(self) -> float:
        """Get age of data point in minutes."""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds() / 60


@dataclass
class StatisticalBaseline:
    """Statistical baseline for performance metrics."""

    metric_name: str
    mean: float
    median: float
    std_dev: float
    p50: float
    p95: float
    p99: float
    min_value: float
    max_value: float
    sample_count: int
    confidence_interval: tuple[float, float]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_anomaly(self, value: float, sensitivity: float = 2.0) -> tuple[bool, float]:
        """Check if value is an anomaly using statistical methods.

        Args:
            value: Value to check
            sensitivity: Number of standard deviations for anomaly threshold

        Returns:
            Tuple of (is_anomaly, z_score)
        """
        if self.std_dev == 0:
            return False, 0.0

        z_score = abs(value - self.mean) / self.std_dev
        is_anomaly = z_score > sensitivity

        return is_anomaly, z_score

    def is_regression(self, value: float, threshold_multiplier: float = 1.5) -> bool:
        """Check if value represents a performance regression."""
        # Consider regression if value exceeds P95 by threshold multiplier
        return value > (self.p95 * threshold_multiplier)

    def get_severity(self, value: float) -> RegressionSeverity:
        """Determine severity level for a performance regression."""
        if value > (self.p99 * 3.0):
            return RegressionSeverity.EMERGENCY
        elif value > (self.p99 * 2.0):
            return RegressionSeverity.CRITICAL
        elif value > (self.p95 * 2.0):
            return RegressionSeverity.WARNING
        else:
            return RegressionSeverity.INFO


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""

    metric_name: str
    direction: TrendDirection
    slope: float  # Rate of change
    correlation: float  # Strength of trend
    recent_mean: float
    historical_mean: float
    change_percent: float
    window_size: int
    analysis_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def is_significant(self) -> bool:
        """Check if trend is statistically significant."""
        return abs(self.correlation) > 0.7 and abs(self.change_percent) > 10.0


@dataclass
class RegressionAlert:
    """Performance regression alert."""

    metric_name: str
    severity: RegressionSeverity
    current_value: float
    baseline_p95: float
    z_score: float
    message: str
    trend: PerformanceTrend | None = None
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resolved: bool = False

    def acknowledge(self, user: str, note: str = ""):
        """Acknowledge the alert."""
        self.acknowledged = True
        self.metadata["acknowledged_by"] = user
        self.metadata["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
        if note:
            self.metadata["acknowledge_note"] = note

    def resolve(self, user: str, note: str = ""):
        """Resolve the alert."""
        self.resolved = True
        self.metadata["resolved_by"] = user
        self.metadata["resolved_at"] = datetime.now(timezone.utc).isoformat()
        if note:
            self.metadata["resolution_note"] = note


class PerformanceRegressionDetector:
    """
    Advanced performance regression detection system.

    Features:
    - Statistical baseline establishment and updating
    - Real-time anomaly detection using multiple algorithms
    - Trend analysis and forecasting
    - Adaptive thresholds based on historical patterns
    - Contextual alert generation with recommendations
    - Integration with monitoring and alerting systems
    """

    def __init__(
        self,
        baseline_window_hours: int = 24,
        trend_window_minutes: int = 60,
        sensitivity: float = 2.0,
        regression_threshold: float = 1.5,
        min_samples_for_baseline: int = 50,
        max_data_points: int = 10000,
        enable_trend_analysis: bool = True,
        enable_adaptive_thresholds: bool = True,
    ):
        """Initialize performance regression detector.

        Args:
            baseline_window_hours: Hours of data for baseline calculation
            trend_window_minutes: Minutes of data for trend analysis
            sensitivity: Standard deviations for anomaly detection
            regression_threshold: Multiplier for regression detection
            min_samples_for_baseline: Minimum samples needed for reliable baseline
            max_data_points: Maximum data points to keep in memory
            enable_trend_analysis: Enable trend analysis and forecasting
            enable_adaptive_thresholds: Enable adaptive threshold adjustment
        """
        self.baseline_window_hours = baseline_window_hours
        self.trend_window_minutes = trend_window_minutes
        self.sensitivity = sensitivity
        self.regression_threshold = regression_threshold
        self.min_samples_for_baseline = min_samples_for_baseline
        self.max_data_points = max_data_points
        self.enable_trend_analysis = enable_trend_analysis
        self.enable_adaptive_thresholds = enable_adaptive_thresholds

        # Data storage
        self._data_points: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_data_points)
        )
        self._baselines: dict[str, StatisticalBaseline] = {}
        self._trends: dict[str, PerformanceTrend] = {}
        self._alerts: deque = deque(maxlen=1000)

        # Alert callbacks
        self._alert_callbacks: list[Callable[[RegressionAlert], None]] = []

        # Background processing
        self._processing_task: asyncio.Task | None = None
        self._running = False

        logger.info("Performance regression detector initialized")

    async def start(self):
        """Start the regression detector background processing."""
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        logger.info("Performance regression detector started")

    async def stop(self):
        """Stop the regression detector."""
        if not self._running:
            return

        self._running = False

        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        logger.info("Performance regression detector stopped")

    def record_performance(
        self,
        metric_name: str,
        value: float,
        operation: str = "unknown",
        table: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ):
        """Record a performance measurement.

        Args:
            metric_name: Name of the performance metric
            value: Measured value
            operation: Database operation type
            table: Database table name
            metadata: Additional metadata
        """
        data_point = PerformanceDataPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            operation=operation,
            table=table,
            metadata=metadata or {},
        )

        self._data_points[metric_name].append(data_point)

        # Perform real-time analysis
        self._analyze_real_time(metric_name, data_point)

    def _analyze_real_time(self, metric_name: str, data_point: PerformanceDataPoint):
        """Perform real-time analysis on new data point."""
        baseline = self._baselines.get(metric_name)

        if baseline is None:
            # Try to create baseline if we have enough data
            self._update_baseline(metric_name)
            baseline = self._baselines.get(metric_name)

        if baseline is None:
            return  # Not enough data yet

        # Check for anomalies and regressions
        is_anomaly, z_score = baseline.is_anomaly(data_point.value, self.sensitivity)
        is_regression = baseline.is_regression(
            data_point.value, self.regression_threshold
        )

        if is_anomaly or is_regression:
            severity = baseline.get_severity(data_point.value)

            # Generate alert
            alert = RegressionAlert(
                metric_name=metric_name,
                severity=severity,
                current_value=data_point.value,
                baseline_p95=baseline.p95,
                z_score=z_score,
                message=self._generate_alert_message(
                    metric_name, data_point.value, baseline, is_anomaly, is_regression
                ),
                metadata={
                    "operation": data_point.operation,
                    "table": data_point.table,
                    "is_anomaly": is_anomaly,
                    "is_regression": is_regression,
                    "baseline_samples": baseline.sample_count,
                },
            )

            # Add trend analysis if enabled
            if self.enable_trend_analysis:
                trend = self._trends.get(metric_name)
                if trend and trend.is_significant:
                    alert.trend = trend

            # Add recommendations
            alert.recommendations = self._generate_recommendations(
                metric_name, data_point, baseline, alert.severity
            )

            self._trigger_alert(alert)

    async def _processing_loop(self):
        """Background processing loop for baseline updates and trend analysis."""
        while self._running:
            try:
                # Update baselines for all metrics
                for metric_name in list(self._data_points.keys()):
                    self._update_baseline(metric_name)

                    if self.enable_trend_analysis:
                        self._analyze_trend(metric_name)

                # Clean old data
                self._cleanup_old_data()

                # Sleep before next processing cycle
                await asyncio.sleep(60)  # Process every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in regression detector processing loop: {e}")
                await asyncio.sleep(10)

    def _update_baseline(self, metric_name: str):
        """Update statistical baseline for a metric."""
        data_points = list(self._data_points[metric_name])

        if len(data_points) < self.min_samples_for_baseline:
            return

        # Filter to baseline window
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            hours=self.baseline_window_hours
        )
        recent_points = [dp for dp in data_points if dp.timestamp >= cutoff_time]

        if len(recent_points) < self.min_samples_for_baseline:
            return

        values = [dp.value for dp in recent_points]
        values.sort()

        n = len(values)
        mean = statistics.mean(values)
        median = statistics.median(values)
        std_dev = statistics.stdev(values) if n > 1 else 0.0

        # Calculate percentiles
        p50 = values[int(n * 0.50)]
        p95 = values[int(n * 0.95)]
        p99 = values[int(n * 0.99)]

        # Calculate confidence interval (95%)
        if std_dev > 0:
            margin_error = 1.96 * (std_dev / (n**0.5))
            confidence_interval = (mean - margin_error, mean + margin_error)
        else:
            confidence_interval = (mean, mean)

        baseline = StatisticalBaseline(
            metric_name=metric_name,
            mean=mean,
            median=median,
            std_dev=std_dev,
            p50=p50,
            p95=p95,
            p99=p99,
            min_value=min(values),
            max_value=max(values),
            sample_count=n,
            confidence_interval=confidence_interval,
        )

        self._baselines[metric_name] = baseline
        logger.debug(f"Updated baseline for {metric_name}: P95={p95:.3f}, samples={n}")

    def _analyze_trend(self, metric_name: str):
        """Analyze performance trend for a metric."""
        data_points = list(self._data_points[metric_name])

        # Filter to trend window
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=self.trend_window_minutes
        )
        recent_points = [dp for dp in data_points if dp.timestamp >= cutoff_time]

        if len(recent_points) < 10:
            return

        # Prepare data for linear regression
        timestamps = [
            (dp.timestamp - recent_points[0].timestamp).total_seconds()
            for dp in recent_points
        ]
        values = [dp.value for dp in recent_points]

        # Calculate linear regression
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values, strict=False))
        sum_x2 = sum(x * x for x in timestamps)

        # Slope and correlation
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Calculate correlation coefficient
        mean_x = sum_x / n
        mean_y = sum_y / n

        numerator = sum(
            (x - mean_x) * (y - mean_y)
            for x, y in zip(timestamps, values, strict=False)
        )
        denom_x = sum((x - mean_x) ** 2 for x in timestamps)
        denom_y = sum((y - mean_y) ** 2 for y in values)

        if denom_x == 0 or denom_y == 0:
            correlation = 0.0
        else:
            correlation = numerator / ((denom_x * denom_y) ** 0.5)

        # Determine trend direction
        if abs(slope) < 0.001:
            direction = TrendDirection.STABLE
        elif slope > 0:
            if abs(correlation) > 0.5:
                direction = TrendDirection.DEGRADING
            else:
                direction = TrendDirection.VOLATILE
        else:
            if abs(correlation) > 0.5:
                direction = TrendDirection.IMPROVING
            else:
                direction = TrendDirection.VOLATILE

        # Calculate change percentage
        recent_mean = statistics.mean(values[-min(10, len(values)) :])

        # Historical mean from baseline
        baseline = self._baselines.get(metric_name)
        historical_mean = baseline.mean if baseline else recent_mean

        if historical_mean > 0:
            change_percent = ((recent_mean - historical_mean) / historical_mean) * 100
        else:
            change_percent = 0.0

        trend = PerformanceTrend(
            metric_name=metric_name,
            direction=direction,
            slope=slope,
            correlation=correlation,
            recent_mean=recent_mean,
            historical_mean=historical_mean,
            change_percent=change_percent,
            window_size=n,
        )

        self._trends[metric_name] = trend

        if trend.is_significant:
            logger.info(
                f"Significant trend detected for {metric_name}: "
                f"{direction.value}, change={change_percent:.1f}%"
            )

    def _generate_alert_message(
        self,
        metric_name: str,
        value: float,
        baseline: StatisticalBaseline,
        is_anomaly: bool,
        is_regression: bool,
    ) -> str:
        """Generate descriptive alert message."""
        parts = []

        if is_regression:
            parts.append("Performance regression detected")

        if is_anomaly:
            parts.append("Statistical anomaly detected")

        message = " and ".join(parts) if parts else "Performance issue detected"

        message += (
            f" for {metric_name}: current value {value:.3f}s "
            f"vs baseline P95 {baseline.p95:.3f}s "
            f"(+{((value / baseline.p95 - 1) * 100):.1f}%)"
        )

        return message

    def _generate_recommendations(
        self,
        metric_name: str,
        data_point: PerformanceDataPoint,
        baseline: StatisticalBaseline,
        severity: RegressionSeverity,
    ) -> list[str]:
        """Generate contextual recommendations for performance issues."""
        recommendations = []

        operation = data_point.operation
        table = data_point.table

        # Operation-specific recommendations
        if operation.upper() == "SELECT":
            recommendations.extend(
                [
                    f"Check if {table} table has proper indexes for the query",
                    "Consider adding LIMIT clauses to reduce result set size",
                    "Review query execution plan for inefficient operations",
                ]
            )
        elif operation.upper() == "INSERT":
            recommendations.extend(
                [
                    f"Check if {table} table has too many indexes slowing inserts",
                    "Consider batch inserts instead of individual operations",
                    "Review foreign key constraints and triggers",
                ]
            )
        elif operation.upper() == "UPDATE":
            recommendations.extend(
                [
                    f"Ensure WHERE clause in updates on {table} uses indexed columns",
                    "Check for lock contention on frequently updated rows",
                    "Consider optimistic locking for concurrent updates",
                ]
            )

        # Severity-specific recommendations
        if severity in [RegressionSeverity.CRITICAL, RegressionSeverity.EMERGENCY]:
            recommendations.extend(
                [
                    "Consider temporarily scaling up database resources",
                    "Check for active long-running transactions",
                    "Review connection pool settings and utilization",
                    "Monitor database CPU and memory usage",
                ]
            )

        # Trend-based recommendations
        trend = self._trends.get(metric_name)
        if trend and trend.direction == TrendDirection.DEGRADING:
            recommendations.extend(
                [
                    "Performance is trending worse - investigate root cause",
                    "Consider proactive optimization before issue escalates",
                    "Review recent schema or configuration changes",
                ]
            )

        # General recommendations
        recommendations.extend(
            [
                "Check database connection pool health and utilization",
                "Review recent application deployments for performance impact",
                "Monitor query patterns for changes in access patterns",
            ]
        )

        return recommendations[:5]  # Limit to top 5 recommendations

    def _trigger_alert(self, alert: RegressionAlert):
        """Trigger a performance regression alert."""
        self._alerts.append(alert)

        logger.warning(f"Performance alert ({alert.severity.value}): {alert.message}")

        # Call registered alert callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _cleanup_old_data(self):
        """Clean up old data points to manage memory usage."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            hours=self.baseline_window_hours * 2
        )

        for _metric_name, data_points in self._data_points.items():
            # Remove old data points
            while data_points and data_points[0].timestamp < cutoff_time:
                data_points.popleft()

    def add_alert_callback(self, callback: Callable[[RegressionAlert], None]):
        """Add alert callback function."""
        self._alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[RegressionAlert], None]):
        """Remove alert callback function."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    def get_baseline(self, metric_name: str) -> StatisticalBaseline | None:
        """Get baseline for a metric."""
        return self._baselines.get(metric_name)

    def get_trend(self, metric_name: str) -> PerformanceTrend | None:
        """Get trend analysis for a metric."""
        return self._trends.get(metric_name)

    def get_recent_alerts(
        self,
        limit: int = 50,
        severity: RegressionSeverity | None = None,
        unresolved_only: bool = False,
    ) -> list[RegressionAlert]:
        """Get recent performance alerts."""
        alerts = list(self._alerts)

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]

        return alerts[-limit:] if alerts else []

    def acknowledge_alert(self, alert_id: str, user: str, note: str = ""):
        """Acknowledge an alert by timestamp-based ID."""
        for alert in self._alerts:
            if alert.timestamp.isoformat() == alert_id:
                alert.acknowledge(user, note)
                return True
        return False

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of detector metrics."""
        total_alerts = len(self._alerts)
        critical_alerts = len(
            [a for a in self._alerts if a.severity == RegressionSeverity.CRITICAL]
        )
        unresolved_alerts = len([a for a in self._alerts if not a.resolved])

        return {
            "tracked_metrics": len(self._data_points),
            "active_baselines": len(self._baselines),
            "active_trends": len(self._trends),
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts,
            "unresolved_alerts": unresolved_alerts,
            "configuration": {
                "baseline_window_hours": self.baseline_window_hours,
                "trend_window_minutes": self.trend_window_minutes,
                "sensitivity": self.sensitivity,
                "regression_threshold": self.regression_threshold,
                "min_samples_for_baseline": self.min_samples_for_baseline,
                "trend_analysis_enabled": self.enable_trend_analysis,
                "adaptive_thresholds_enabled": self.enable_adaptive_thresholds,
            },
        }


# Global regression detector instance
_regression_detector: PerformanceRegressionDetector | None = None


async def get_regression_detector(**kwargs) -> PerformanceRegressionDetector:
    """Get or create global regression detector instance."""
    global _regression_detector

    if _regression_detector is None:
        _regression_detector = PerformanceRegressionDetector(**kwargs)
        await _regression_detector.start()

    return _regression_detector


async def close_regression_detector():
    """Close global regression detector instance."""
    global _regression_detector

    if _regression_detector:
        await _regression_detector.stop()
        _regression_detector = None
