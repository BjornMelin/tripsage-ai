"""Database metrics collection using Prometheus.

This module provides comprehensive database monitoring and metrics collection
using Prometheus client library, tracking connection health, performance,
and error rates for the TripSage database services.
"""

import logging
import time
from contextlib import contextmanager

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    start_http_server,
)


logger = logging.getLogger(__name__)


class DatabaseMetrics:
    """Prometheus metrics collector for database operations.

    Tracks comprehensive database performance and health metrics including:
    - Connection attempts, successes, and failures
    - Query execution times and error rates
    - Active connection counts
    - Table-level operation statistics
    - Health check results
    """

    def __init__(self, registry: CollectorRegistry | None = None):
        """Initialize database metrics collector.

        Args:
            registry: Optional Prometheus collector registry
        """
        self.registry = registry

        # Connection metrics
        self.connection_attempts = Counter(
            "tripsage_db_connection_attempts_total",
            "Total database connection attempts",
            ["service", "status"],
            registry=registry,
        )

        self.connection_duration = Histogram(
            "tripsage_db_connection_duration_seconds",
            "Database connection establishment time",
            ["service"],
            registry=registry,
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
        )

        self.active_connections = Gauge(
            "tripsage_db_connections_active",
            "Currently active database connections",
            ["service"],
            registry=registry,
        )

        # Query metrics
        self.query_duration = Histogram(
            "tripsage_db_query_duration_seconds",
            "Database query execution time",
            ["service", "operation", "table"],
            registry=registry,
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
        )

        self.query_total = Counter(
            "tripsage_db_queries_total",
            "Total database queries executed",
            ["service", "operation", "table", "status"],
            registry=registry,
        )

        self.query_errors = Counter(
            "tripsage_db_query_errors_total",
            "Total database query errors",
            ["service", "operation", "table", "error_type"],
            registry=registry,
        )

        # Health metrics
        self.health_status = Gauge(
            "tripsage_db_health_status",
            "Database health status (1=healthy, 0=unhealthy)",
            ["service"],
            registry=registry,
        )

        self.last_health_check = Gauge(
            "tripsage_db_last_health_check_timestamp",
            "Timestamp of last health check",
            ["service"],
            registry=registry,
        )

        # Performance metrics
        self.transaction_duration = Histogram(
            "tripsage_db_transaction_duration_seconds",
            "Database transaction execution time",
            ["service"],
            registry=registry,
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
        )

        self.pool_size = Gauge(
            "tripsage_db_connection_pool_size",
            "Database connection pool size",
            ["service"],
            registry=registry,
        )

        self.pool_available = Gauge(
            "tripsage_db_connection_pool_available",
            "Available connections in pool",
            ["service"],
            registry=registry,
        )

        # Database info
        self.database_info = Info(
            "tripsage_db_info",
            "Database information",
            ["service"],
            registry=registry,
        )

        logger.info("Database metrics collector initialized")

    def record_connection_attempt(self, service: str, success: bool, duration: float):
        """Record a database connection attempt.

        Args:
            service: Service name (e.g., 'supabase', 'postgres')
            success: Whether connection was successful
            duration: Connection establishment time in seconds
        """
        status = "success" if success else "error"
        self.connection_attempts.labels(service=service, status=status).inc()
        self.connection_duration.labels(service=service).observe(duration)

        logger.debug(
            f"Recorded connection attempt: service={service}, success={success}, "
            f"duration={duration:.3f}s"
        )

    def set_active_connections(self, service: str, count: int):
        """Set the number of active connections.

        Args:
            service: Service name
            count: Number of active connections
        """
        self.active_connections.labels(service=service).set(count)

    def record_query(
        self,
        service: str,
        operation: str,
        table: str,
        duration: float,
        success: bool,
        error_type: str | None = None,
    ):
        """Record a database query execution.

        Args:
            service: Service name
            operation: SQL operation (SELECT, INSERT, UPDATE, DELETE)
            table: Table name
            duration: Query execution time in seconds
            success: Whether query was successful
            error_type: Type of error if query failed
        """
        status = "success" if success else "error"

        self.query_duration.labels(
            service=service, operation=operation, table=table
        ).observe(duration)

        self.query_total.labels(
            service=service, operation=operation, table=table, status=status
        ).inc()

        if not success and error_type:
            self.query_errors.labels(
                service=service, operation=operation, table=table, error_type=error_type
            ).inc()

        logger.debug(
            f"Recorded query: service={service}, operation={operation}, "
            f"table={table}, duration={duration:.3f}s, success={success}"
        )

    @contextmanager
    def time_query(self, service: str, operation: str, table: str):
        """Context manager to time database queries.

        Args:
            service: Service name
            operation: SQL operation
            table: Table name

        Usage:
            with metrics.time_query("supabase", "SELECT", "users"):
                result = await db.select("users", "*")
        """
        start_time = time.time()
        success = False
        error_type = None

        try:
            yield
            success = True
        except Exception as e:
            error_type = type(e).__name__
            raise
        finally:
            duration = time.time() - start_time
            self.record_query(service, operation, table, duration, success, error_type)

    def record_health_check(self, service: str, healthy: bool):
        """Record health check result.

        Args:
            service: Service name
            healthy: Whether service is healthy
        """
        self.health_status.labels(service=service).set(1 if healthy else 0)
        self.last_health_check.labels(service=service).set(time.time())

        logger.debug(f"Recorded health check: service={service}, healthy={healthy}")

    def set_pool_metrics(self, service: str, size: int, available: int):
        """Set connection pool metrics.

        Args:
            service: Service name
            size: Total pool size
            available: Available connections
        """
        self.pool_size.labels(service=service).set(size)
        self.pool_available.labels(service=service).set(available)

    def set_database_info(
        self,
        service: str,
        version: str,
        host: str,
        database: str,
        **kwargs,
    ):
        """Set database information.

        Args:
            service: Service name
            version: Database version
            host: Database host
            database: Database name
            **kwargs: Additional info fields
        """
        info_dict = {
            "version": version,
            "host": host,
            "database": database,
            **kwargs,
        }
        self.database_info.labels(service=service).info(info_dict)

    @contextmanager
    def time_transaction(self, service: str):
        """Context manager to time database transactions.

        Args:
            service: Service name

        Usage:
            with metrics.time_transaction("supabase"):
                async with db.transaction() as tx:
                    # transaction operations
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.transaction_duration.labels(service=service).observe(duration)
            logger.debug(
                f"Recorded transaction: service={service}, duration={duration:.3f}s"
            )

    def get_metrics_summary(self) -> dict[str, any]:
        """Get a summary of current metrics.

        Returns:
            Dictionary with current metric values
        """
        return {
            "connection_attempts": self._get_counter_value(self.connection_attempts),
            "active_connections": self._get_gauge_value(self.active_connections),
            "query_total": self._get_counter_value(self.query_total),
            "query_errors": self._get_counter_value(self.query_errors),
            "health_status": self._get_gauge_value(self.health_status),
        }

    def _get_counter_value(self, counter: Counter) -> dict[str, float]:
        """Get counter values by labels."""
        try:
            return {
                str(sample.labels): sample.value
                for sample in counter.collect()[0].samples
            }
        except (IndexError, AttributeError):
            return {}

    def _get_gauge_value(self, gauge: Gauge) -> dict[str, float]:
        """Get gauge values by labels."""
        try:
            return {
                str(sample.labels): sample.value
                for sample in gauge.collect()[0].samples
            }
        except (IndexError, AttributeError):
            return {}

    def start_metrics_server(self, port: int = 8000):
        """Start Prometheus metrics HTTP server.

        Args:
            port: Port to serve metrics on
        """
        try:
            start_http_server(port, registry=self.registry)
            logger.info(f"Metrics server started on port {port}")
        except Exception as e:
            logger.exception(f"Failed to start metrics server")
            raise


# Global metrics instance
_database_metrics: DatabaseMetrics | None = None


def get_database_metrics() -> DatabaseMetrics:
    """Get or create global database metrics instance.

    Returns:
        DatabaseMetrics instance
    """
    global _database_metrics

    if _database_metrics is None:
        _database_metrics = DatabaseMetrics()

    return _database_metrics


def reset_database_metrics():
    """Reset global database metrics instance (for testing)."""
    global _database_metrics
    _database_metrics = None
