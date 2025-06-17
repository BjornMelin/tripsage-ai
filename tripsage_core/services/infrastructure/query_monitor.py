"""
Essential Query Performance Monitoring for TripSage Database Operations.

This module provides lightweight query performance monitoring focused on
essential metrics: query timing, error rates, and slow query detection.

Features:
- Query execution timing
- Slow query detection
- Error rate tracking
- Basic logging integration
- Simple metrics collection
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

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


class QueryMonitorConfig(BaseModel):
    """Configuration for essential query monitoring."""

    enabled: bool = Field(default=True, description="Enable query monitoring")
    slow_query_threshold: float = Field(
        default=1.0, description="Slow query threshold in seconds", gt=0
    )
    max_query_history: int = Field(
        default=1000, description="Maximum query history entries", gt=0
    )
    error_rate_threshold: float = Field(
        default=0.05, description="Error rate threshold (5%)", ge=0, le=1
    )
    export_metrics: bool = Field(
        default=True, description="Export metrics to monitoring system"
    )


@dataclass
class QueryExecution:
    """Essential query execution data."""

    query_id: str
    query_type: QueryType
    table_name: Optional[str]
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: QueryStatus = QueryStatus.SUCCESS
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Calculate duration if end_time is set."""
        if self.end_time is not None and self.duration is None:
            self.duration = self.end_time - self.start_time

    def is_slow(self, threshold: float = 1.0) -> bool:
        """Check if query execution is considered slow."""
        return self.duration is not None and self.duration > threshold

    @property
    def is_successful(self) -> bool:
        """Check if query execution was successful."""
        return self.status == QueryStatus.SUCCESS


@dataclass
class QueryMetrics:
    """Essential performance metrics."""

    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    slow_queries: int = 0
    avg_duration: float = 0.0
    error_rate: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class QueryTracker:
    """Essential query execution tracking."""

    def __init__(self, config: QueryMonitorConfig):
        self.config = config
        self._active_queries: Dict[str, QueryExecution] = {}
        self._query_history: List[QueryExecution] = []

    async def start_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
    ) -> str:
        """Start tracking a query execution."""
        if not self.config.enabled:
            return ""

        query_id = f"{int(time.time() * 1000000)}_{id(object())}"
        start_time = time.perf_counter()

        execution = QueryExecution(
            query_id=query_id,
            query_type=query_type,
            table_name=table_name,
            start_time=start_time,
        )

        self._active_queries[query_id] = execution
        logger.debug(f"Started tracking query {query_id}: {query_type.value}")
        return query_id

    async def finish_query(
        self,
        query_id: str,
        status: QueryStatus = QueryStatus.SUCCESS,
        error_message: Optional[str] = None,
        row_count: Optional[int] = None,
    ) -> Optional[QueryExecution]:
        """Finish tracking a query execution."""
        if not query_id:
            return None

        end_time = time.perf_counter()
        execution = self._active_queries.pop(query_id, None)

        if not execution:
            logger.warning(f"Query execution {query_id} not found")
            return None

        execution.end_time = end_time
        execution.duration = end_time - execution.start_time
        execution.status = status
        execution.error_message = error_message
        execution.row_count = row_count

        # Maintain history limit
        self._query_history.append(execution)
        if len(self._query_history) > self.config.max_query_history:
            self._query_history = self._query_history[-self.config.max_query_history :]

        logger.debug(
            f"Finished tracking query {query_id}: "
            f"duration={execution.duration:.3f}s, status={status.value}"
        )
        return execution

    def get_query_history(self, limit: Optional[int] = None) -> List[QueryExecution]:
        """Get query execution history."""
        history = self._query_history
        if limit:
            history = history[-limit:]
        return history

    def get_slow_queries(
        self, threshold: Optional[float] = None
    ) -> List[QueryExecution]:
        """Get slow query executions."""
        threshold = threshold or self.config.slow_query_threshold
        return [
            execution
            for execution in self._query_history
            if execution.duration and execution.duration >= threshold
        ]


class MetricsCollector:
    """Collects and calculates essential query metrics."""

    def __init__(self, config: QueryMonitorConfig):
        self.config = config

    def calculate_metrics(self, executions: List[QueryExecution]) -> QueryMetrics:
        """Calculate essential performance metrics."""
        if not executions:
            return QueryMetrics()

        metrics = QueryMetrics()
        durations = []

        for execution in executions:
            metrics.total_queries += 1

            if execution.is_successful:
                metrics.successful_queries += 1
            else:
                metrics.failed_queries += 1

            if execution.duration is not None:
                durations.append(execution.duration)
                if execution.is_slow(self.config.slow_query_threshold):
                    metrics.slow_queries += 1

        # Calculate averages
        if durations:
            metrics.avg_duration = sum(durations) / len(durations)

        if metrics.total_queries > 0:
            metrics.error_rate = metrics.failed_queries / metrics.total_queries

        return metrics


class QueryPerformanceMonitor:
    """
    Essential query performance monitoring system.

    Simplified monitoring focusing on core metrics:
    - Query execution timing
    - Slow query detection
    - Error rate tracking
    - Basic metrics collection
    """

    def __init__(
        self,
        config: Optional[QueryMonitorConfig] = None,
        settings: Optional[Settings] = None,
        metrics: Optional[DatabaseMetrics] = None,
    ):
        """Initialize query performance monitor."""
        self.config = config or QueryMonitorConfig()
        self.settings = settings or get_settings()
        self.metrics = metrics or get_database_metrics()

        # Core components
        self.tracker = QueryTracker(self.config)
        self.metrics_collector = MetricsCollector(self.config)

        logger.info("Essential query performance monitor initialized")

    async def track_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
    ) -> str:
        """Start tracking a query execution."""
        return await self.tracker.start_query(query_type, table_name)

    async def finish_query(
        self,
        query_id: str,
        status: QueryStatus = QueryStatus.SUCCESS,
        error_message: Optional[str] = None,
        row_count: Optional[int] = None,
    ) -> Optional[QueryExecution]:
        """Finish tracking a query execution."""
        execution = await self.tracker.finish_query(
            query_id, status, error_message, row_count
        )

        if execution and self.config.export_metrics:
            # Update monitoring metrics
            try:
                self.metrics.record_query(
                    service="supabase",
                    operation=execution.query_type.value,
                    table=execution.table_name or "unknown",
                    duration=execution.duration or 0.0,
                    success=execution.is_successful,
                    error_type=type(Exception).__name__
                    if execution.error_message
                    else None,
                )
            except Exception as e:
                logger.error(f"Failed to record metrics: {e}")

            # Log slow queries
            if execution.is_slow(self.config.slow_query_threshold):
                logger.warning(
                    f"Slow query detected: {execution.duration:.3f}s "
                    f"({execution.query_type.value} on {execution.table_name})"
                )

        return execution

    @asynccontextmanager
    async def monitor_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
    ):
        """Context manager for monitoring query execution."""
        query_id = await self.track_query(query_type, table_name)

        success = False
        error_message = None

        try:
            yield query_id
            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            await self.finish_query(
                query_id,
                QueryStatus.SUCCESS if success else QueryStatus.ERROR,
                error_message,
            )

    def get_performance_metrics(self) -> QueryMetrics:
        """Get current performance metrics."""
        executions = self.tracker.get_query_history()
        return self.metrics_collector.calculate_metrics(executions)

    def get_slow_queries(self, limit: int = 100) -> List[QueryExecution]:
        """Get slow query executions."""
        return self.tracker.get_slow_queries()[:limit]

    def get_monitoring_status(self) -> Dict[str, any]:
        """Get monitoring system status."""
        history = self.tracker.get_query_history()
        metrics = self.get_performance_metrics()

        return {
            "monitoring_enabled": self.config.enabled,
            "config": {
                "slow_query_threshold": self.config.slow_query_threshold,
                "error_rate_threshold": self.config.error_rate_threshold,
                "export_metrics": self.config.export_metrics,
            },
            "statistics": {
                "total_tracked_queries": len(history),
                "current_metrics": {
                    "total_queries": metrics.total_queries,
                    "error_rate": metrics.error_rate,
                    "avg_duration": metrics.avg_duration,
                    "slow_queries": metrics.slow_queries,
                },
            },
        }

    def update_config(self, **config_updates):
        """Update monitoring configuration."""
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
    """Get or create global query performance monitor instance."""
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
