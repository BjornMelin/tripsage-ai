"""WebSocket Performance Monitoring Service.

This service provides comprehensive performance monitoring for
WebSocket connections including:
- Real-time metrics collection
- Connection health tracking
- Performance alert generation
- Historical data aggregation
- Circuit breaker monitoring
- Queue backpressure analytics
"""

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from .websocket_connection_service import WebSocketConnection


logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Point-in-time performance snapshot."""

    timestamp: float
    connection_id: str
    latency_ms: float
    queue_size: int
    error_count: int
    message_rate: float
    memory_usage_mb: float
    circuit_breaker_state: str
    backpressure_active: bool


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics over a time window."""

    start_time: float
    end_time: float
    connection_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_messages: int
    total_errors: int
    avg_queue_size: float
    max_queue_size: int
    circuit_breaker_trips: int
    backpressure_events: int


class PerformanceAlert(BaseModel):
    """Performance alert notification."""

    id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    type: str  # "latency", "queue_size", "error_rate", "circuit_breaker"
    severity: str  # "low", "medium", "high", "critical"
    connection_id: str | None = None
    message: str
    threshold: float
    current_value: float
    timestamp: datetime = Field(default_factory=datetime.now)
    resolved: bool = False


class PerformanceThresholds(BaseModel):
    """Configurable performance thresholds."""

    latency_warning_ms: float = 1000.0
    latency_critical_ms: float = 2000.0
    queue_size_warning: int = 1000
    queue_size_critical: int = 1500
    error_rate_warning: float = 0.05  # 5% error rate
    error_rate_critical: float = 0.10  # 10% error rate
    message_rate_min: float = 0.1  # messages per second
    backpressure_duration_warning: float = 30.0  # seconds


class WebSocketPerformanceMonitor:
    """Comprehensive WebSocket performance monitoring service."""

    def __init__(
        self,
        collection_interval: float = 1.0,
        aggregation_interval: float = 60.0,
        retention_hours: int = 24,
        thresholds: PerformanceThresholds | None = None,
    ):
        """Initialize WebSocket performance monitor."""
        self.collection_interval = collection_interval
        self.aggregation_interval = aggregation_interval
        self.retention_hours = retention_hours
        self.thresholds = thresholds or PerformanceThresholds()

        # Metrics storage
        self.snapshots: deque[PerformanceSnapshot] = deque(maxlen=10000)
        self.aggregated_metrics: deque[AggregatedMetrics] = deque(maxlen=1000)
        self.active_alerts: dict[str, PerformanceAlert] = {}
        self.alert_history: deque[PerformanceAlert] = deque(maxlen=1000)

        # Connection tracking
        self.connection_metrics: dict[str, dict[str, Any]] = defaultdict(dict)
        self.circuit_breaker_events: dict[str, list[float]] = defaultdict(list)
        self.backpressure_events: dict[str, list[float]] = defaultdict(list)

        # Background tasks
        self._monitor_task: asyncio.Task | None = None
        self._aggregation_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start performance monitoring."""
        if self._running:
            return

        self._running = True

        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("WebSocket performance monitoring started")

    async def stop(self) -> None:
        """Stop performance monitoring."""
        self._running = False

        # Cancel tasks
        for task in [self._monitor_task, self._aggregation_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        logger.info("WebSocket performance monitoring stopped")

    def collect_connection_metrics(self, connection: WebSocketConnection) -> None:
        """Collect metrics from a WebSocket connection."""
        try:
            health = connection.get_health()

            # Create performance snapshot
            snapshot = PerformanceSnapshot(
                timestamp=time.time(),
                connection_id=connection.connection_id,
                latency_ms=health.latency,
                queue_size=health.queue_size,
                error_count=connection.error_count,
                message_rate=health.message_rate,
                memory_usage_mb=0.0,  # Would need process monitoring for real memory
                circuit_breaker_state=connection.circuit_breaker.state.value,
                backpressure_active=health.backpressure_active,
            )

            self.snapshots.append(snapshot)

            # Update connection-specific metrics
            self.connection_metrics[connection.connection_id] = {
                "last_update": time.time(),
                "total_messages": connection.message_count,
                "total_errors": connection.error_count,
                "current_latency": health.latency,
                "current_queue_size": health.queue_size,
                "state": connection.state.value,
                "circuit_breaker_state": connection.circuit_breaker.state.value,
                "backpressure_active": health.backpressure_active,
            }

            # Track circuit breaker events
            if connection.circuit_breaker.state.value == "open":
                self.circuit_breaker_events[connection.connection_id].append(
                    time.time()
                )

            # Track backpressure events
            if health.backpressure_active:
                self.backpressure_events[connection.connection_id].append(time.time())

            # Check for alerts
            self._check_performance_alerts(connection, health)

        except Exception:
            logger.exception(
                "Failed to collect metrics for connection %s", connection.connection_id
            )

    def _check_performance_alerts(
        self, connection: WebSocketConnection, health
    ) -> None:
        """Check performance thresholds and generate alerts."""
        current_time = time.time()

        # Check latency alerts
        if health.latency > self.thresholds.latency_critical_ms:
            self._create_alert(
                alert_type="latency",
                severity="critical",
                connection_id=connection.connection_id,
                message=f"Critical latency: {health.latency:.1f}ms",
                threshold=self.thresholds.latency_critical_ms,
                current_value=health.latency,
            )
        elif health.latency > self.thresholds.latency_warning_ms:
            self._create_alert(
                alert_type="latency",
                severity="medium",
                connection_id=connection.connection_id,
                message=f"High latency: {health.latency:.1f}ms",
                threshold=self.thresholds.latency_warning_ms,
                current_value=health.latency,
            )

        # Check queue size alerts
        if health.queue_size > self.thresholds.queue_size_critical:
            self._create_alert(
                alert_type="queue_size",
                severity="critical",
                connection_id=connection.connection_id,
                message=f"Critical queue size: {health.queue_size}",
                threshold=self.thresholds.queue_size_critical,
                current_value=health.queue_size,
            )
        elif health.queue_size > self.thresholds.queue_size_warning:
            self._create_alert(
                alert_type="queue_size",
                severity="medium",
                connection_id=connection.connection_id,
                message=f"High queue size: {health.queue_size}",
                threshold=self.thresholds.queue_size_warning,
                current_value=health.queue_size,
            )

        # Check error rate alerts
        if connection.message_count > 0:
            error_rate = connection.error_count / connection.message_count
            if error_rate > self.thresholds.error_rate_critical:
                self._create_alert(
                    alert_type="error_rate",
                    severity="critical",
                    connection_id=connection.connection_id,
                    message=f"Critical error rate: {error_rate:.1%}",
                    threshold=self.thresholds.error_rate_critical,
                    current_value=error_rate,
                )
            elif error_rate > self.thresholds.error_rate_warning:
                self._create_alert(
                    alert_type="error_rate",
                    severity="medium",
                    connection_id=connection.connection_id,
                    message=f"High error rate: {error_rate:.1%}",
                    threshold=self.thresholds.error_rate_warning,
                    current_value=error_rate,
                )

        # Check circuit breaker alerts
        if connection.circuit_breaker.state.value == "open":
            self._create_alert(
                alert_type="circuit_breaker",
                severity="high",
                connection_id=connection.connection_id,
                message="Circuit breaker opened",
                threshold=0,
                current_value=1,
            )

        # Check backpressure duration alerts
        if health.backpressure_active:
            events = self.backpressure_events[connection.connection_id]
            # Check if we have events older than the warning threshold
            old_events = [
                t
                for t in events
                if current_time - t > self.thresholds.backpressure_duration_warning
            ]
            if len(old_events) > 0:
                oldest_event = min(old_events)
                duration = current_time - oldest_event
                self._create_alert(
                    alert_type="backpressure",
                    severity="medium",
                    connection_id=connection.connection_id,
                    message=f"Prolonged backpressure: {duration:.1f}s",
                    threshold=self.thresholds.backpressure_duration_warning,
                    current_value=duration,
                )

    def _create_alert(
        self,
        alert_type: str,
        severity: str,
        connection_id: str,
        message: str,
        threshold: float,
        current_value: float,
    ) -> None:
        """Create or update a performance alert."""
        alert_key = f"{alert_type}_{connection_id}"

        # Check if alert already exists and is recent
        if alert_key in self.active_alerts:
            existing_alert = self.active_alerts[alert_key]
            time_since_alert = (
                datetime.now() - existing_alert.timestamp
            ).total_seconds()

            # Only create new alert if enough time has passed (avoid spam)
            if time_since_alert < 60:  # 1 minute cooldown
                return

        # Create new alert
        alert = PerformanceAlert(
            type=alert_type,
            severity=severity,
            connection_id=connection_id,
            message=message,
            threshold=threshold,
            current_value=current_value,
        )

        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)

        logger.warning(
            "Performance alert: %s (connection: %s)", alert.message, connection_id
        )

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # This would be called with actual connections from the manager
                # For now, just sleep to maintain the loop structure
                await asyncio.sleep(self.collection_interval)

            except Exception:
                logger.exception("Error in performance monitor loop")
                await asyncio.sleep(self.collection_interval)

    async def _aggregation_loop(self) -> None:
        """Aggregate metrics periodically."""
        while self._running:
            try:
                await asyncio.sleep(self.aggregation_interval)
                await self._aggregate_metrics()

            except Exception:
                logger.exception("Error in aggregation loop")
                await asyncio.sleep(self.aggregation_interval)

    async def _cleanup_loop(self) -> None:
        """Clean up old data periodically."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                await self._cleanup_old_data()

            except Exception:
                logger.exception("Error in cleanup loop")
                await asyncio.sleep(3600)

    async def _aggregate_metrics(self) -> None:
        """Aggregate recent snapshots into summary metrics."""
        if not self.snapshots:
            return

        current_time = time.time()
        window_start = current_time - self.aggregation_interval

        # Filter snapshots within the aggregation window
        window_snapshots = [s for s in self.snapshots if s.timestamp >= window_start]

        if not window_snapshots:
            return

        # Calculate aggregated metrics
        latencies = [s.latency_ms for s in window_snapshots]
        queue_sizes = [s.queue_size for s in window_snapshots]

        # Sort for percentile calculations
        latencies.sort()
        n = len(latencies)

        p95_latency = latencies[int(n * 0.95)] if n > 0 else 0
        p99_latency = latencies[int(n * 0.99)] if n > 0 else 0

        # Count circuit breaker trips and backpressure events in window
        cb_trips = sum(1 for s in window_snapshots if s.circuit_breaker_state == "OPEN")
        bp_events = sum(1 for s in window_snapshots if s.backpressure_active)

        aggregated = AggregatedMetrics(
            start_time=window_start,
            end_time=current_time,
            connection_count=len({s.connection_id for s in window_snapshots}),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            total_messages=int(sum(s.message_rate for s in window_snapshots)),
            total_errors=sum(s.error_count for s in window_snapshots),
            avg_queue_size=sum(queue_sizes) / len(queue_sizes) if queue_sizes else 0,
            max_queue_size=max(queue_sizes) if queue_sizes else 0,
            circuit_breaker_trips=cb_trips,
            backpressure_events=bp_events,
        )

        self.aggregated_metrics.append(aggregated)

        logger.info(
            "Aggregated metrics: %s connections, avg latency "
            "%.1fms, p95 latency %.1fms",
            aggregated.connection_count,
            aggregated.avg_latency_ms,
            aggregated.p95_latency_ms,
        )

    async def _cleanup_old_data(self) -> None:
        """Clean up old metrics and alerts."""
        current_time = time.time()
        retention_seconds = self.retention_hours * 3600
        cutoff_time = current_time - retention_seconds

        # Clean up old snapshots (already handled by deque maxlen, but we can filter)
        old_snapshot_count = len(self.snapshots)
        self.snapshots = deque(
            (s for s in self.snapshots if s.timestamp >= cutoff_time),
            maxlen=self.snapshots.maxlen,
        )

        # Clean up old aggregated metrics
        old_aggregated_count = len(self.aggregated_metrics)
        self.aggregated_metrics = deque(
            (m for m in self.aggregated_metrics if m.end_time >= cutoff_time),
            maxlen=self.aggregated_metrics.maxlen,
        )

        # Clean up old circuit breaker events
        for connection_id in list(self.circuit_breaker_events.keys()):
            events = self.circuit_breaker_events[connection_id]
            self.circuit_breaker_events[connection_id] = [
                t for t in events if current_time - t < retention_seconds
            ]
            if not self.circuit_breaker_events[connection_id]:
                del self.circuit_breaker_events[connection_id]

        # Clean up old backpressure events
        for connection_id in list(self.backpressure_events.keys()):
            events = self.backpressure_events[connection_id]
            self.backpressure_events[connection_id] = [
                t for t in events if current_time - t < retention_seconds
            ]
            if not self.backpressure_events[connection_id]:
                del self.backpressure_events[connection_id]

        # Resolve old active alerts
        cutoff_alert_time = datetime.now() - timedelta(hours=1)
        for alert_key in list(self.active_alerts.keys()):
            alert = self.active_alerts[alert_key]
            if alert.timestamp < cutoff_alert_time:
                alert.resolved = True
                del self.active_alerts[alert_key]

        logger.info(
            "Cleaned up old metrics: snapshots %s -> %s, aggregated %s -> %s",
            old_snapshot_count,
            len(self.snapshots),
            old_aggregated_count,
            len(self.aggregated_metrics),
        )

    def get_performance_summary(self) -> dict[str, Any]:
        """Get current performance summary."""
        if not self.aggregated_metrics:
            return {"status": "no_data", "message": "No performance data available yet"}

        latest = self.aggregated_metrics[-1]

        # Calculate overall health score (0-100)
        health_score = 100

        # Penalize high latency
        if latest.avg_latency_ms > self.thresholds.latency_critical_ms:
            health_score -= 30
        elif latest.avg_latency_ms > self.thresholds.latency_warning_ms:
            health_score -= 15

        # Penalize circuit breaker trips
        if latest.circuit_breaker_trips > 0:
            health_score -= min(20, latest.circuit_breaker_trips * 5)

        # Penalize backpressure events
        if latest.backpressure_events > 0:
            health_score -= min(15, latest.backpressure_events * 3)

        # Penalize high queue sizes
        if latest.max_queue_size > self.thresholds.queue_size_critical:
            health_score -= 20
        elif latest.max_queue_size > self.thresholds.queue_size_warning:
            health_score -= 10

        health_score = max(0, health_score)

        return {
            "health_score": health_score,
            "status": "healthy"
            if health_score >= 80
            else "degraded"
            if health_score >= 60
            else "unhealthy",
            "connection_count": latest.connection_count,
            "avg_latency_ms": latest.avg_latency_ms,
            "p95_latency_ms": latest.p95_latency_ms,
            "p99_latency_ms": latest.p99_latency_ms,
            "total_messages": latest.total_messages,
            "total_errors": latest.total_errors,
            "avg_queue_size": latest.avg_queue_size,
            "max_queue_size": latest.max_queue_size,
            "circuit_breaker_trips": latest.circuit_breaker_trips,
            "backpressure_events": latest.backpressure_events,
            "active_alerts": len(self.active_alerts),
            "timestamp": latest.end_time,
        }

    def get_connection_performance(self, connection_id: str) -> dict[str, Any]:
        """Get performance data for a specific connection."""
        if connection_id not in self.connection_metrics:
            return {"error": "Connection not found"}

        metrics = self.connection_metrics[connection_id]

        # Get recent snapshots for this connection
        recent_snapshots = [
            s
            for s in self.snapshots
            if s.connection_id == connection_id
            and time.time() - s.timestamp < 300  # Last 5 minutes
        ]

        if recent_snapshots:
            latencies = [s.latency_ms for s in recent_snapshots]

            latencies.sort()
            n = len(latencies)

            p95_latency = latencies[int(n * 0.95)] if n > 0 else 0
        else:
            p95_latency = 0

        # Get circuit breaker event count (last hour)
        current_time = time.time()
        cb_events = len(
            [
                t
                for t in self.circuit_breaker_events.get(connection_id, [])
                if current_time - t < 3600
            ]
        )

        # Get backpressure event count (last hour)
        bp_events = len(
            [
                t
                for t in self.backpressure_events.get(connection_id, [])
                if current_time - t < 3600
            ]
        )

        return {
            "connection_id": connection_id,
            "last_update": metrics.get("last_update", 0),
            "total_messages": metrics.get("total_messages", 0),
            "total_errors": metrics.get("total_errors", 0),
            "current_latency": metrics.get("current_latency", 0),
            "p95_latency_5min": p95_latency,
            "current_queue_size": metrics.get("current_queue_size", 0),
            "state": metrics.get("state", "unknown"),
            "circuit_breaker_state": metrics.get("circuit_breaker_state", "unknown"),
            "backpressure_active": metrics.get("backpressure_active", False),
            "circuit_breaker_events_1h": cb_events,
            "backpressure_events_1h": bp_events,
            "recent_snapshots_count": len(recent_snapshots),
        }

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all active performance alerts."""
        return [alert.model_dump() for alert in self.active_alerts.values()]

    def export_metrics(self, format_type: str = "json") -> str:
        """Export performance metrics in specified format."""
        data = {
            "summary": self.get_performance_summary(),
            "aggregated_metrics": [asdict(m) for m in self.aggregated_metrics],
            "active_alerts": self.get_active_alerts(),
            "connection_count": len(self.connection_metrics),
            "export_timestamp": time.time(),
        }

        if format_type == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
