"""
Comprehensive Query Performance Monitoring System for TripSage Database Operations.

This module provides real-time query performance monitoring, pattern detection,
alerting, and analytics for database operations with sub-millisecond precision.

Features:
- Query execution tracking with high precision timing
- Slow query detection with configurable thresholds
- N+1 query pattern detection
- Performance analytics and trending
- Real-time alerting and notifications
- Prometheus metrics integration
- Seamless DatabaseService integration
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from statistics import mean, median
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from tripsage_core.config import Settings, get_settings
from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    get_database_metrics,
)

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Database query operation types."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UPSERT = "UPSERT"
    VECTOR_SEARCH = "VECTOR_SEARCH"
    COUNT = "COUNT"
    TRANSACTION = "TRANSACTION"
    FUNCTION_CALL = "FUNCTION_CALL"
    RAW_SQL = "RAW_SQL"


class QueryStatus(Enum):
    """Query execution status."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Performance alert types."""

    SLOW_QUERY = "slow_query"
    N_PLUS_ONE = "n_plus_one"
    HIGH_ERROR_RATE = "high_error_rate"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONNECTION_POOL_EXHAUSTION = "connection_pool_exhaustion"
    QUERY_TIMEOUT = "query_timeout"
    MEMORY_PRESSURE = "memory_pressure"


# Configuration Models using Pydantic 2.x


class QueryMonitorConfig(BaseModel):
    """Configuration for query performance monitoring."""

    # Monitoring toggles
    enabled: bool = Field(default=True, description="Enable query monitoring")
    track_patterns: bool = Field(
        default=True, description="Enable N+1 pattern detection"
    )
    collect_stack_traces: bool = Field(
        default=True, description="Collect stack traces for slow queries"
    )

    # Timing thresholds (in seconds)
    slow_query_threshold: float = Field(
        default=1.0, description="Slow query threshold in seconds", gt=0
    )
    very_slow_query_threshold: float = Field(
        default=5.0, description="Very slow query threshold in seconds", gt=0
    )
    critical_query_threshold: float = Field(
        default=10.0, description="Critical query threshold in seconds", gt=0
    )

    # Pattern detection
    n_plus_one_threshold: int = Field(
        default=10, description="N+1 query detection threshold", gt=0
    )
    n_plus_one_time_window: float = Field(
        default=60.0, description="N+1 detection time window in seconds", gt=0
    )

    # Error rate monitoring
    error_rate_threshold: float = Field(
        default=0.05, description="Error rate threshold (5%)", ge=0, le=1
    )
    error_rate_window: float = Field(
        default=300.0, description="Error rate calculation window in seconds", gt=0
    )

    # Performance degradation detection
    degradation_threshold: float = Field(
        default=0.5,
        description="Performance degradation threshold (50% increase)",
        gt=0,
    )
    degradation_baseline_window: float = Field(
        default=3600.0,
        description="Baseline calculation window in seconds",
        gt=0,
    )

    # History and retention
    max_query_history: int = Field(
        default=10000, description="Maximum query history entries", gt=0
    )
    max_pattern_history: int = Field(
        default=1000, description="Maximum pattern history entries", gt=0
    )
    max_alert_history: int = Field(
        default=5000, description="Maximum alert history entries", gt=0
    )

    # Analytics
    analytics_window: float = Field(
        default=3600.0, description="Analytics calculation window in seconds", gt=0
    )
    trending_buckets: int = Field(
        default=24, description="Number of trending time buckets", gt=0
    )

    # Prometheus metrics
    export_prometheus: bool = Field(
        default=True, description="Export Prometheus metrics"
    )
    metrics_prefix: str = Field(
        default="tripsage_query", description="Prometheus metrics prefix"
    )

    @field_validator("very_slow_query_threshold")
    @classmethod
    def validate_very_slow_threshold(cls, v: float, info) -> float:
        """Ensure very slow threshold is greater than slow threshold."""
        if (
            "slow_query_threshold" in info.data
            and v <= info.data["slow_query_threshold"]
        ):
            raise ValueError("very_slow_query_threshold must be > slow_query_threshold")
        return v

    @field_validator("critical_query_threshold")
    @classmethod
    def validate_critical_threshold(cls, v: float, info) -> float:
        """Ensure critical threshold is greater than very slow threshold."""
        if (
            "very_slow_query_threshold" in info.data
            and v <= info.data["very_slow_query_threshold"]
        ):
            raise ValueError(
                "critical_query_threshold must be > very_slow_query_threshold"
            )
        return v


# Data Models


@dataclass
class QueryExecution:
    """Represents a single query execution with timing and metadata."""

    query_id: str
    query_type: QueryType
    table_name: Optional[str]
    query_hash: str
    query_text: Optional[str]
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: QueryStatus = QueryStatus.SUCCESS
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    row_count: Optional[int] = None
    connection_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    stack_trace: Optional[List[str]] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Calculate duration if end_time is set."""
        if self.end_time is not None and self.duration is None:
            self.duration = self.end_time - self.start_time

    @property
    def is_slow(self) -> bool:
        """Check if query execution is considered slow."""
        return self.duration is not None and self.duration > 1.0  # Default threshold

    @property
    def is_successful(self) -> bool:
        """Check if query execution was successful."""
        return self.status == QueryStatus.SUCCESS


@dataclass
class QueryPattern:
    """Represents a detected query pattern (e.g., N+1)."""

    pattern_id: str
    pattern_type: str
    query_hash: str
    table_name: str
    occurrence_count: int
    time_window: float
    first_occurrence: datetime
    last_occurrence: datetime
    severity: AlertSeverity
    sample_query: str
    affected_rows: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def frequency(self) -> float:
        """Calculate pattern frequency per second."""
        if self.time_window <= 0:
            return 0.0
        return self.occurrence_count / self.time_window


@dataclass
class PerformanceAlert:
    """Represents a performance monitoring alert."""

    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    query_id: Optional[str] = None
    table_name: Optional[str] = None
    duration: Optional[float] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance analytics metrics."""

    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    slow_queries: int = 0
    very_slow_queries: int = 0
    critical_queries: int = 0

    avg_duration: float = 0.0
    median_duration: float = 0.0
    p95_duration: float = 0.0
    p99_duration: float = 0.0

    error_rate: float = 0.0
    throughput: float = 0.0  # queries per second

    # Per-table statistics
    table_stats: Dict[str, Dict[str, Union[int, float]]] = field(default_factory=dict)

    # Per-operation statistics
    operation_stats: Dict[str, Dict[str, Union[int, float]]] = field(
        default_factory=dict
    )

    # Trend data
    trending_data: List[Dict[str, Union[datetime, float]]] = field(default_factory=list)


# Core Implementation Classes


class QueryExecutionTracker:
    """Tracks individual query executions with high precision timing."""

    def __init__(self, config: QueryMonitorConfig):
        self.config = config
        self._active_queries: Dict[str, QueryExecution] = {}
        self._query_history: deque = deque(maxlen=config.max_query_history)
        self._lock = asyncio.Lock()

    async def start_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start tracking a query execution.

        Args:
            query_type: Type of database operation
            table_name: Target table name
            query_text: SQL query text (optional)
            user_id: User ID executing the query
            session_id: Session ID
            tags: Additional metadata tags

        Returns:
            Unique query execution ID
        """
        query_id = f"{int(time.time() * 1000000)}_{id(object())}"
        start_time = time.perf_counter()

        # Generate query hash for pattern detection
        query_hash = self._generate_query_hash(query_type, table_name, query_text)

        # Collect stack trace if enabled
        stack_trace = None
        if self.config.collect_stack_traces:
            import traceback

            stack_trace = traceback.format_stack()[:-1]  # Exclude current frame

        execution = QueryExecution(
            query_id=query_id,
            query_type=query_type,
            table_name=table_name,
            query_hash=query_hash,
            query_text=query_text,
            start_time=start_time,
            user_id=user_id,
            session_id=session_id,
            stack_trace=stack_trace,
            tags=tags or {},
        )

        async with self._lock:
            self._active_queries[query_id] = execution

        logger.debug(f"Started tracking query {query_id}: {query_type.value}")
        return query_id

    async def finish_query(
        self,
        query_id: str,
        status: QueryStatus = QueryStatus.SUCCESS,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        row_count: Optional[int] = None,
    ) -> Optional[QueryExecution]:
        """Finish tracking a query execution.

        Args:
            query_id: Query execution ID
            status: Final execution status
            error_message: Error message if failed
            error_type: Error type classification
            row_count: Number of rows affected/returned

        Returns:
            Completed QueryExecution or None if not found
        """
        end_time = time.perf_counter()

        async with self._lock:
            execution = self._active_queries.pop(query_id, None)
            if not execution:
                logger.warning(
                    f"Query execution {query_id} not found in active queries"
                )
                return None

            # Update execution details
            execution.end_time = end_time
            execution.duration = end_time - execution.start_time
            execution.status = status
            execution.error_message = error_message
            execution.error_type = error_type
            execution.row_count = row_count

            # Add to history
            self._query_history.append(execution)

        logger.debug(
            f"Finished tracking query {query_id}: "
            f"duration={execution.duration:.3f}s, status={status.value}"
        )
        return execution

    def _generate_query_hash(
        self,
        query_type: QueryType,
        table_name: Optional[str],
        query_text: Optional[str],
    ) -> str:
        """Generate a hash for query pattern detection."""
        # Create normalized query signature
        signature_parts = [query_type.value]

        if table_name:
            signature_parts.append(table_name)

        if query_text:
            # Normalize query text by removing literals and whitespace
            normalized_query = self._normalize_query_text(query_text)
            signature_parts.append(normalized_query)

        signature = "|".join(signature_parts)
        return hashlib.md5(signature.encode()).hexdigest()

    def _normalize_query_text(self, query_text: str) -> str:
        """Normalize query text for pattern detection."""
        import re

        # Convert to lowercase
        normalized = query_text.lower().strip()

        # Replace string literals with placeholder
        normalized = re.sub(r"'[^']*'", "'?'", normalized)

        # Replace numeric literals with placeholder
        normalized = re.sub(r"\b\d+\b", "?", normalized)

        # Replace UUID patterns with placeholder
        normalized = re.sub(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            "?",
            normalized,
        )

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized

    async def get_active_queries(self) -> List[QueryExecution]:
        """Get currently active query executions."""
        async with self._lock:
            return list(self._active_queries.values())

    async def get_query_history(
        self, limit: Optional[int] = None
    ) -> List[QueryExecution]:
        """Get query execution history."""
        async with self._lock:
            history = list(self._query_history)
            if limit:
                history = history[-limit:]
            return history

    async def get_slow_queries(
        self, threshold: Optional[float] = None
    ) -> List[QueryExecution]:
        """Get slow query executions."""
        threshold = threshold or self.config.slow_query_threshold

        async with self._lock:
            return [
                execution
                for execution in self._query_history
                if execution.duration and execution.duration >= threshold
            ]


class QueryPatternDetector:
    """Detects N+1 queries and other performance patterns."""

    def __init__(self, config: QueryMonitorConfig):
        self.config = config
        self._pattern_history: deque = deque(maxlen=config.max_pattern_history)
        self._query_frequency: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._lock = asyncio.Lock()

    async def analyze_query(self, execution: QueryExecution) -> List[QueryPattern]:
        """Analyze a query execution for patterns.

        Args:
            execution: Completed query execution

        Returns:
            List of detected patterns
        """
        if not self.config.track_patterns or not execution.is_successful:
            return []

        patterns = []

        # Check for N+1 pattern
        n_plus_one = await self._detect_n_plus_one(execution)
        if n_plus_one:
            patterns.append(n_plus_one)

        # Check for repetitive queries
        repetitive = await self._detect_repetitive_queries(execution)
        if repetitive:
            patterns.append(repetitive)

        return patterns

    async def _detect_n_plus_one(
        self, execution: QueryExecution
    ) -> Optional[QueryPattern]:
        """Detect N+1 query patterns."""
        if execution.query_type != QueryType.SELECT:
            return None

        async with self._lock:
            # Track query frequency
            current_time = time.time()
            query_times = self._query_frequency[execution.query_hash]
            query_times.append(current_time)

            # Clean old entries outside time window
            cutoff_time = current_time - self.config.n_plus_one_time_window
            while query_times and query_times[0] < cutoff_time:
                query_times.popleft()

            # Check if frequency exceeds threshold
            if len(query_times) >= self.config.n_plus_one_threshold:
                pattern_id = f"n_plus_one_{execution.query_hash}_{int(current_time)}"

                pattern = QueryPattern(
                    pattern_id=pattern_id,
                    pattern_type="n_plus_one",
                    query_hash=execution.query_hash,
                    table_name=execution.table_name or "unknown",
                    occurrence_count=len(query_times),
                    time_window=self.config.n_plus_one_time_window,
                    first_occurrence=datetime.fromtimestamp(
                        query_times[0], timezone.utc
                    ),
                    last_occurrence=execution.timestamp,
                    severity=AlertSeverity.WARNING,
                    sample_query=execution.query_text
                    or f"{execution.query_type.value} on {execution.table_name}",
                    context={
                        "user_id": execution.user_id,
                        "session_id": execution.session_id,
                        "frequency_per_second": len(query_times)
                        / self.config.n_plus_one_time_window,
                    },
                )

                self._pattern_history.append(pattern)
                logger.warning(
                    f"N+1 pattern detected: {len(query_times)} similar queries "
                    f"in {self.config.n_plus_one_time_window}s window"
                )
                return pattern

        return None

    async def _detect_repetitive_queries(
        self, execution: QueryExecution
    ) -> Optional[QueryPattern]:
        """Detect repetitive query patterns."""
        # Implementation for detecting repetitive queries
        # This could be enhanced with more sophisticated analysis
        return None

    async def get_detected_patterns(
        self, limit: Optional[int] = None
    ) -> List[QueryPattern]:
        """Get detected query patterns."""
        async with self._lock:
            patterns = list(self._pattern_history)
            if limit:
                patterns = patterns[-limit:]
            return patterns


class PerformanceAnalytics:
    """Calculates performance metrics and trends."""

    def __init__(self, config: QueryMonitorConfig):
        self.config = config
        self._metrics_cache: Dict[str, PerformanceMetrics] = {}
        self._trending_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=config.trending_buckets)
        )
        self._lock = asyncio.Lock()

    async def calculate_metrics(
        self, executions: List[QueryExecution], window_start: Optional[datetime] = None
    ) -> PerformanceMetrics:
        """Calculate performance metrics for given executions.

        Args:
            executions: List of query executions to analyze
            window_start: Start of analysis window

        Returns:
            Calculated performance metrics
        """
        if not executions:
            return PerformanceMetrics()

        # Filter executions by time window if specified
        if window_start:
            executions = [ex for ex in executions if ex.timestamp >= window_start]

        metrics = PerformanceMetrics()
        durations = []

        # Calculate basic metrics
        metrics.total_queries = len(executions)
        metrics.successful_queries = sum(1 for ex in executions if ex.is_successful)
        metrics.failed_queries = metrics.total_queries - metrics.successful_queries

        # Calculate duration-based metrics
        for execution in executions:
            if execution.duration is not None:
                durations.append(execution.duration)

                if execution.duration >= self.config.critical_query_threshold:
                    metrics.critical_queries += 1
                elif execution.duration >= self.config.very_slow_query_threshold:
                    metrics.very_slow_queries += 1
                elif execution.duration >= self.config.slow_query_threshold:
                    metrics.slow_queries += 1

        # Calculate duration statistics
        if durations:
            metrics.avg_duration = mean(durations)
            metrics.median_duration = median(durations)

            sorted_durations = sorted(durations)
            n = len(sorted_durations)
            metrics.p95_duration = sorted_durations[int(n * 0.95)] if n > 0 else 0.0
            metrics.p99_duration = sorted_durations[int(n * 0.99)] if n > 0 else 0.0

        # Calculate error rate
        if metrics.total_queries > 0:
            metrics.error_rate = metrics.failed_queries / metrics.total_queries

        # Calculate throughput (queries per second)
        if executions:
            time_span = (
                executions[-1].timestamp - executions[0].timestamp
            ).total_seconds()
            if time_span > 0:
                metrics.throughput = metrics.total_queries / time_span

        # Calculate per-table statistics
        await self._calculate_table_stats(executions, metrics)

        # Calculate per-operation statistics
        await self._calculate_operation_stats(executions, metrics)

        return metrics

    async def _calculate_table_stats(
        self, executions: List[QueryExecution], metrics: PerformanceMetrics
    ):
        """Calculate per-table performance statistics."""
        table_data: Dict[str, List[float]] = defaultdict(list)
        table_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "errors": 0}
        )

        for execution in executions:
            table = execution.table_name or "unknown"
            table_counts[table]["total"] += 1

            if not execution.is_successful:
                table_counts[table]["errors"] += 1

            if execution.duration is not None:
                table_data[table].append(execution.duration)

        for table, durations in table_data.items():
            counts = table_counts[table]
            stats = {
                "query_count": counts["total"],
                "error_count": counts["errors"],
                "avg_duration": mean(durations) if durations else 0.0,
                "max_duration": max(durations) if durations else 0.0,
                "error_rate": counts["errors"] / counts["total"]
                if counts["total"] > 0
                else 0.0,
            }
            metrics.table_stats[table] = stats

    async def _calculate_operation_stats(
        self, executions: List[QueryExecution], metrics: PerformanceMetrics
    ):
        """Calculate per-operation performance statistics."""
        operation_data: Dict[str, List[float]] = defaultdict(list)
        operation_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total": 0, "errors": 0}
        )

        for execution in executions:
            operation = execution.query_type.value
            operation_counts[operation]["total"] += 1

            if not execution.is_successful:
                operation_counts[operation]["errors"] += 1

            if execution.duration is not None:
                operation_data[operation].append(execution.duration)

        for operation, durations in operation_data.items():
            counts = operation_counts[operation]
            stats = {
                "query_count": counts["total"],
                "error_count": counts["errors"],
                "avg_duration": mean(durations) if durations else 0.0,
                "max_duration": max(durations) if durations else 0.0,
                "error_rate": counts["errors"] / counts["total"]
                if counts["total"] > 0
                else 0.0,
            }
            metrics.operation_stats[operation] = stats

    async def update_trending_data(self, metrics: PerformanceMetrics):
        """Update trending performance data."""
        async with self._lock:
            current_time = datetime.now(timezone.utc)

            trend_point = {
                "timestamp": current_time,
                "avg_duration": metrics.avg_duration,
                "throughput": metrics.throughput,
                "error_rate": metrics.error_rate,
                "slow_query_rate": metrics.slow_queries / max(metrics.total_queries, 1),
            }

            self._trending_data["overall"].append(trend_point)
            metrics.trending_data = list(self._trending_data["overall"])

    async def detect_performance_degradation(
        self,
        current_metrics: PerformanceMetrics,
        baseline_window: Optional[float] = None,
    ) -> bool:
        """Detect performance degradation compared to baseline.

        Args:
            current_metrics: Current performance metrics
            baseline_window: Baseline calculation window in seconds

        Returns:
            True if performance degradation is detected
        """
        baseline_window = baseline_window or self.config.degradation_baseline_window

        async with self._lock:
            trending_data = list(self._trending_data["overall"])

            if len(trending_data) < 2:
                return False

            # Calculate baseline from older data
            cutoff_time = datetime.now(timezone.utc).timestamp() - baseline_window
            baseline_data = [
                point
                for point in trending_data
                if point["timestamp"].timestamp() < cutoff_time
            ]

            if not baseline_data:
                return False

            baseline_avg_duration = mean(
                point["avg_duration"] for point in baseline_data
            )
            baseline_error_rate = mean(point["error_rate"] for point in baseline_data)

            # Check for degradation
            duration_increase = (
                current_metrics.avg_duration - baseline_avg_duration
            ) / max(baseline_avg_duration, 0.001)

            error_rate_increase = current_metrics.error_rate - baseline_error_rate

            return (
                duration_increase > self.config.degradation_threshold
                or error_rate_increase > self.config.error_rate_threshold
            )


class AlertingSystem:
    """Handles performance alerts and notifications."""

    def __init__(self, config: QueryMonitorConfig):
        self.config = config
        self._alert_history: deque = deque(maxlen=config.max_alert_history)
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        self._lock = asyncio.Lock()

    async def check_and_alert(
        self,
        execution: QueryExecution,
        patterns: List[QueryPattern],
        metrics: PerformanceMetrics,
    ) -> List[PerformanceAlert]:
        """Check for alert conditions and generate alerts.

        Args:
            execution: Query execution to check
            patterns: Detected query patterns
            metrics: Current performance metrics

        Returns:
            List of generated alerts
        """
        alerts = []

        # Check slow query alerts
        slow_alert = await self._check_slow_query_alert(execution)
        if slow_alert:
            alerts.append(slow_alert)

        # Check pattern alerts
        for pattern in patterns:
            pattern_alert = await self._check_pattern_alert(pattern)
            if pattern_alert:
                alerts.append(pattern_alert)

        # Check error rate alerts
        error_rate_alert = await self._check_error_rate_alert(metrics)
        if error_rate_alert:
            alerts.append(error_rate_alert)

        # Process all generated alerts
        for alert in alerts:
            await self._process_alert(alert)

        return alerts

    async def _check_slow_query_alert(
        self, execution: QueryExecution
    ) -> Optional[PerformanceAlert]:
        """Check for slow query alerts."""
        if not execution.duration:
            return None

        severity = None
        if execution.duration >= self.config.critical_query_threshold:
            severity = AlertSeverity.CRITICAL
        elif execution.duration >= self.config.very_slow_query_threshold:
            severity = AlertSeverity.ERROR
        elif execution.duration >= self.config.slow_query_threshold:
            severity = AlertSeverity.WARNING

        if severity:
            alert_id = f"slow_query_{execution.query_id}"
            message = (
                f"Slow query detected: {execution.duration:.3f}s "
                f"({execution.query_type.value} on {execution.table_name})"
            )

            details = {
                "query_id": execution.query_id,
                "query_type": execution.query_type.value,
                "table_name": execution.table_name,
                "duration": execution.duration,
                "user_id": execution.user_id,
                "session_id": execution.session_id,
                "query_text": execution.query_text,
                "stack_trace": execution.stack_trace
                if self.config.collect_stack_traces
                else None,
            }

            return PerformanceAlert(
                alert_id=alert_id,
                alert_type=AlertType.SLOW_QUERY,
                severity=severity,
                message=message,
                details=details,
                query_id=execution.query_id,
                table_name=execution.table_name,
                duration=execution.duration,
            )

        return None

    async def _check_pattern_alert(
        self, pattern: QueryPattern
    ) -> Optional[PerformanceAlert]:
        """Check for pattern-based alerts."""
        if pattern.pattern_type == "n_plus_one":
            alert_id = f"n_plus_one_{pattern.pattern_id}"
            message = (
                f"N+1 query pattern detected: {pattern.occurrence_count} similar "
                f"queries in {pattern.time_window}s on table {pattern.table_name}"
            )

            details = {
                "pattern_id": pattern.pattern_id,
                "pattern_type": pattern.pattern_type,
                "occurrence_count": pattern.occurrence_count,
                "frequency": pattern.frequency,
                "table_name": pattern.table_name,
                "sample_query": pattern.sample_query,
                "context": pattern.context,
            }

            return PerformanceAlert(
                alert_id=alert_id,
                alert_type=AlertType.N_PLUS_ONE,
                severity=pattern.severity,
                message=message,
                details=details,
                table_name=pattern.table_name,
            )

        return None

    async def _check_error_rate_alert(
        self, metrics: PerformanceMetrics
    ) -> Optional[PerformanceAlert]:
        """Check for high error rate alerts."""
        if metrics.error_rate > self.config.error_rate_threshold:
            alert_id = f"high_error_rate_{int(time.time())}"
            message = f"High error rate detected: {metrics.error_rate:.1%}"

            details = {
                "error_rate": metrics.error_rate,
                "failed_queries": metrics.failed_queries,
                "total_queries": metrics.total_queries,
                "threshold": self.config.error_rate_threshold,
            }

            return PerformanceAlert(
                alert_id=alert_id,
                alert_type=AlertType.HIGH_ERROR_RATE,
                severity=AlertSeverity.ERROR,
                message=message,
                details=details,
            )

        return None

    async def _process_alert(self, alert: PerformanceAlert):
        """Process and store an alert."""
        async with self._lock:
            self._alert_history.append(alert)

        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.INFO)

        logger.log(log_level, f"Performance alert: {alert.message}")

        # Call registered callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add alert callback function."""
        self._alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Remove alert callback function."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    async def get_alerts(
        self,
        limit: Optional[int] = None,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
    ) -> List[PerformanceAlert]:
        """Get performance alerts with optional filtering."""
        async with self._lock:
            alerts = list(self._alert_history)

            # Apply filters
            if severity:
                alerts = [alert for alert in alerts if alert.severity == severity]
            if alert_type:
                alerts = [alert for alert in alerts if alert.alert_type == alert_type]

            # Apply limit
            if limit:
                alerts = alerts[-limit:]

            return alerts


# Main Query Performance Monitor Class


class QueryPerformanceMonitor:
    """
    Main query performance monitoring system with comprehensive tracking,
    analytics, pattern detection, and alerting capabilities.

    Features:
    - Sub-millisecond precision query timing
    - N+1 query pattern detection
    - Real-time performance analytics
    - Configurable alerting system
    - Prometheus metrics integration
    - Decorator-based monitoring
    - Context manager support
    - Background analytics aggregation
    """

    def __init__(
        self,
        config: Optional[QueryMonitorConfig] = None,
        settings: Optional[Settings] = None,
        metrics: Optional[DatabaseMetrics] = None,
    ):
        """Initialize query performance monitor.

        Args:
            config: Query monitoring configuration
            settings: Application settings
            metrics: Database metrics collector
        """
        self.config = config or QueryMonitorConfig()
        self.settings = settings or get_settings()
        self.metrics = metrics or get_database_metrics()

        # Core components
        self.tracker = QueryExecutionTracker(self.config)
        self.pattern_detector = QueryPatternDetector(self.config)
        self.analytics = PerformanceAnalytics(self.config)
        self.alerting = AlertingSystem(self.config)

        # Background tasks
        self._monitoring = False
        self._analytics_task: Optional[asyncio.Task] = None
        self._analytics_interval = 60.0  # 1 minute

        # Integration hooks
        self._pre_query_hooks: List[Callable] = []
        self._post_query_hooks: List[Callable] = []

        logger.info("Query performance monitor initialized")

    async def start_monitoring(self):
        """Start background monitoring and analytics."""
        if self._monitoring:
            logger.warning("Query monitoring already started")
            return

        self._monitoring = True
        self._analytics_task = asyncio.create_task(self._analytics_loop())
        logger.info("Query performance monitoring started")

    async def stop_monitoring(self):
        """Stop background monitoring."""
        if not self._monitoring:
            return

        self._monitoring = False

        if self._analytics_task and not self._analytics_task.done():
            self._analytics_task.cancel()
            try:
                await self._analytics_task
            except asyncio.CancelledError:
                pass

        logger.info("Query performance monitoring stopped")

    async def _analytics_loop(self):
        """Background analytics calculation loop."""
        while self._monitoring:
            try:
                await self._calculate_and_update_analytics()
                await asyncio.sleep(self._analytics_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analytics loop error: {e}")
                await asyncio.sleep(30.0)  # Longer sleep on error

    async def _calculate_and_update_analytics(self):
        """Calculate and update performance analytics."""
        try:
            # Get recent query history
            executions = await self.tracker.get_query_history(limit=10000)

            if not executions:
                return

            # Calculate metrics for the analytics window
            window_start = datetime.now(timezone.utc) - timedelta(
                seconds=self.config.analytics_window
            )
            metrics = await self.analytics.calculate_metrics(executions, window_start)

            # Update trending data
            await self.analytics.update_trending_data(metrics)

            # Check for performance degradation
            degradation_detected = await self.analytics.detect_performance_degradation(
                metrics
            )
            if degradation_detected:
                alert = PerformanceAlert(
                    alert_id=f"degradation_{int(time.time())}",
                    alert_type=AlertType.PERFORMANCE_DEGRADATION,
                    severity=AlertSeverity.WARNING,
                    message="Performance degradation detected",
                    details={
                        "avg_duration": metrics.avg_duration,
                        "error_rate": metrics.error_rate,
                        "throughput": metrics.throughput,
                    },
                )
                await self.alerting._process_alert(alert)

            logger.debug(f"Analytics updated: {metrics.total_queries} queries analyzed")

        except Exception as e:
            logger.error(f"Failed to calculate analytics: {e}")

    # Query Monitoring Methods

    async def track_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start tracking a query execution.

        Args:
            query_type: Type of database operation
            table_name: Target table name
            query_text: SQL query text
            user_id: User executing the query
            session_id: Session ID
            tags: Additional metadata

        Returns:
            Query execution ID for finishing tracking
        """
        if not self.config.enabled:
            return ""

        # Call pre-query hooks
        for hook in self._pre_query_hooks:
            try:
                hook(query_type, table_name, query_text, user_id, session_id, tags)
            except Exception as e:
                logger.error(f"Pre-query hook error: {e}")

        return await self.tracker.start_query(
            query_type=query_type,
            table_name=table_name,
            query_text=query_text,
            user_id=user_id,
            session_id=session_id,
            tags=tags,
        )

    async def finish_query(
        self,
        query_id: str,
        status: QueryStatus = QueryStatus.SUCCESS,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        row_count: Optional[int] = None,
    ) -> Optional[QueryExecution]:
        """Finish tracking a query execution.

        Args:
            query_id: Query execution ID
            status: Final execution status
            error_message: Error message if failed
            error_type: Error type classification
            row_count: Number of rows affected

        Returns:
            Completed QueryExecution
        """
        if not self.config.enabled or not query_id:
            return None

        execution = await self.tracker.finish_query(
            query_id=query_id,
            status=status,
            error_message=error_message,
            error_type=error_type,
            row_count=row_count,
        )

        if execution:
            # Update Prometheus metrics
            if self.config.export_prometheus:
                await self._update_prometheus_metrics(execution)

            # Analyze patterns
            patterns = await self.pattern_detector.analyze_query(execution)

            # Get current metrics for alerting
            recent_executions = await self.tracker.get_query_history(limit=1000)
            current_metrics = await self.analytics.calculate_metrics(recent_executions)

            # Check for alerts
            alerts = await self.alerting.check_and_alert(
                execution, patterns, current_metrics
            )

            # Call post-query hooks
            for hook in self._post_query_hooks:
                try:
                    hook(execution, patterns, alerts)
                except Exception as e:
                    logger.error(f"Post-query hook error: {e}")

        return execution

    async def _update_prometheus_metrics(self, execution: QueryExecution):
        """Update Prometheus metrics for query execution."""
        try:
            self.metrics.record_query(
                service="supabase",
                operation=execution.query_type.value,
                table=execution.table_name or "unknown",
                duration=execution.duration or 0.0,
                success=execution.is_successful,
                error_type=execution.error_type,
            )
        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")

    # Context Manager Support

    @asynccontextmanager
    async def monitor_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for monitoring query execution.

        Usage:
            async with monitor.monitor_query(QueryType.SELECT, "users") as query_id:
                result = await db.select("users", "*")

        Args:
            query_type: Type of database operation
            table_name: Target table name
            query_text: SQL query text
            user_id: User executing the query
            session_id: Session ID
            tags: Additional metadata

        Yields:
            Query execution ID
        """
        query_id = await self.track_query(
            query_type=query_type,
            table_name=table_name,
            query_text=query_text,
            user_id=user_id,
            session_id=session_id,
            tags=tags,
        )

        success = False
        error_message = None
        error_type = None

        try:
            yield query_id
            success = True
        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__
            raise
        finally:
            await self.finish_query(
                query_id=query_id,
                status=QueryStatus.SUCCESS if success else QueryStatus.ERROR,
                error_message=error_message,
                error_type=error_type,
            )

    # Decorator Support

    def monitor_query_method(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
        extract_table_from_args: Optional[Callable] = None,
        extract_user_from_args: Optional[Callable] = None,
    ):
        """Decorator for monitoring database method calls.

        Args:
            query_type: Type of database operation
            table_name: Static table name or None to extract from args
            extract_table_from_args: Function to extract table name from method args
            extract_user_from_args: Function to extract user ID from method args

        Usage:
            @monitor.monitor_query_method(QueryType.SELECT, "users")
            async def get_user(self, user_id: str):
                return await self.select("users", "*", {"id": user_id})
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract context from arguments
                dynamic_table = table_name
                if extract_table_from_args:
                    try:
                        dynamic_table = extract_table_from_args(*args, **kwargs)
                    except Exception:
                        pass

                user_id = None
                if extract_user_from_args:
                    try:
                        user_id = extract_user_from_args(*args, **kwargs)
                    except Exception:
                        pass

                async with self.monitor_query(
                    query_type=query_type,
                    table_name=dynamic_table,
                    query_text=func.__name__,
                    user_id=user_id,
                    tags={"method": func.__name__},
                ):
                    return await func(*args, **kwargs)

            return wrapper

        return decorator

    # Hook Management

    def add_pre_query_hook(self, hook: Callable):
        """Add pre-query execution hook."""
        self._pre_query_hooks.append(hook)

    def add_post_query_hook(self, hook: Callable):
        """Add post-query execution hook."""
        self._post_query_hooks.append(hook)

    def remove_pre_query_hook(self, hook: Callable):
        """Remove pre-query execution hook."""
        if hook in self._pre_query_hooks:
            self._pre_query_hooks.remove(hook)

    def remove_post_query_hook(self, hook: Callable):
        """Remove post-query execution hook."""
        if hook in self._post_query_hooks:
            self._post_query_hooks.remove(hook)

    # Alert Management

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add alert callback function."""
        self.alerting.add_alert_callback(callback)

    def remove_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Remove alert callback function."""
        self.alerting.remove_alert_callback(callback)

    # Query and Analytics Methods

    async def get_slow_queries(
        self,
        limit: int = 100,
        threshold: Optional[float] = None,
    ) -> List[QueryExecution]:
        """Get slow query executions."""
        return await self.tracker.get_slow_queries(threshold=threshold)

    async def get_query_patterns(self, limit: int = 100) -> List[QueryPattern]:
        """Get detected query patterns."""
        return await self.pattern_detector.get_detected_patterns(limit=limit)

    async def get_performance_alerts(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
    ) -> List[PerformanceAlert]:
        """Get performance alerts."""
        return await self.alerting.get_alerts(
            limit=limit, severity=severity, alert_type=alert_type
        )

    async def get_performance_metrics(
        self, window_hours: float = 1.0
    ) -> PerformanceMetrics:
        """Get current performance metrics."""
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        executions = await self.tracker.get_query_history()
        return await self.analytics.calculate_metrics(executions, window_start)

    async def get_table_performance(self, table_name: str) -> Dict[str, Any]:
        """Get performance metrics for a specific table."""
        executions = await self.tracker.get_query_history()
        table_executions = [ex for ex in executions if ex.table_name == table_name]

        if not table_executions:
            return {"error": f"No data found for table {table_name}"}

        metrics = await self.analytics.calculate_metrics(table_executions)
        return {
            "table_name": table_name,
            "total_queries": metrics.total_queries,
            "avg_duration": metrics.avg_duration,
            "error_rate": metrics.error_rate,
            "slow_queries": metrics.slow_queries,
            "last_query": table_executions[-1].timestamp.isoformat(),
        }

    async def get_user_query_stats(self, user_id: str) -> Dict[str, Any]:
        """Get query statistics for a specific user."""
        executions = await self.tracker.get_query_history()
        user_executions = [ex for ex in executions if ex.user_id == user_id]

        if not user_executions:
            return {"error": f"No queries found for user {user_id}"}

        metrics = await self.analytics.calculate_metrics(user_executions)
        return {
            "user_id": user_id,
            "total_queries": metrics.total_queries,
            "avg_duration": metrics.avg_duration,
            "error_rate": metrics.error_rate,
            "slow_queries": metrics.slow_queries,
            "query_types": list(set(ex.query_type.value for ex in user_executions)),
        }

    # Monitoring Status and Control

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status."""
        active_queries = await self.tracker.get_active_queries()
        recent_executions = await self.tracker.get_query_history(limit=1000)
        recent_patterns = await self.pattern_detector.get_detected_patterns(limit=100)
        recent_alerts = await self.alerting.get_alerts(limit=100)

        return {
            "monitoring_enabled": self.config.enabled,
            "monitoring_active": self._monitoring,
            "config": {
                "slow_query_threshold": self.config.slow_query_threshold,
                "n_plus_one_threshold": self.config.n_plus_one_threshold,
                "error_rate_threshold": self.config.error_rate_threshold,
                "track_patterns": self.config.track_patterns,
                "export_prometheus": self.config.export_prometheus,
            },
            "statistics": {
                "active_queries": len(active_queries),
                "total_tracked_queries": len(recent_executions),
                "detected_patterns": len(recent_patterns),
                "total_alerts": len(recent_alerts),
                "pre_query_hooks": len(self._pre_query_hooks),
                "post_query_hooks": len(self._post_query_hooks),
            },
        }

    def update_config(self, **config_updates):
        """Update monitoring configuration.

        Args:
            **config_updates: Configuration fields to update
        """
        for key, value in config_updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config {key} = {value}")
            else:
                logger.warning(f"Unknown config key: {key}")


# Global Query Monitor Instance


_query_monitor: Optional[QueryPerformanceMonitor] = None


def get_query_monitor(
    config: Optional[QueryMonitorConfig] = None,
    settings: Optional[Settings] = None,
    metrics: Optional[DatabaseMetrics] = None,
) -> QueryPerformanceMonitor:
    """Get or create global query performance monitor instance.

    Args:
        config: Query monitoring configuration
        settings: Application settings
        metrics: Database metrics collector

    Returns:
        QueryPerformanceMonitor instance
    """
    global _query_monitor

    if _query_monitor is None:
        _query_monitor = QueryPerformanceMonitor(
            config=config, settings=settings, metrics=metrics
        )

    return _query_monitor


def reset_query_monitor():
    """Reset global query monitor instance (for testing)."""
    global _query_monitor
    _query_monitor = None


# Utility Functions


def create_table_extractor(table_arg_index: int = 0) -> Callable:
    """Create function to extract table name from method arguments.

    Args:
        table_arg_index: Index of table name argument

    Returns:
        Function that extracts table name from args
    """

    def extractor(*args, **kwargs):
        if len(args) > table_arg_index + 1:  # +1 for self
            return args[table_arg_index + 1]
        return None

    return extractor


def create_user_extractor(user_arg_name: str = "user_id") -> Callable:
    """Create function to extract user ID from method arguments.

    Args:
        user_arg_name: Name of user ID argument

    Returns:
        Function that extracts user ID from kwargs
    """

    def extractor(*args, **kwargs):
        return kwargs.get(user_arg_name)

    return extractor
