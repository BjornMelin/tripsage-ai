# pylint: disable=too-many-lines,too-many-instance-attributes,too-many-public-methods,no-name-in-module,global-statement,import-error
"""Supabase-only Database Service (FINAL-ONLY).

This module provides a single modern DatabaseService that uses the Supabase
Python client exclusively. All legacy SQLAlchemy engine and raw engine paths
have been removed to keep the implementation simple, maintainable, and safe.

Key features:
- Typed configuration via Pydantic (pool/monitoring/security/performance knobs)
- Supabase CRUD (select/insert/update/upsert/delete/count)
- Vector search using pgvector via PostgREST expression ordering
- RPC function invocation and raw SQL via a safe RPC wrapper (execute_sql)
- Lightweight monitoring (Prometheus optional) and basic rate limiting/circuit breaker
- Convenience helpers used by business services and wrappers
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from supabase import Client, create_client

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.observability.otel import get_meter, get_tracer


logger = logging.getLogger(__name__)


# ---------------------------
# Configuration (Pydantic v2)
# ---------------------------


class DatabasePoolConfig(BaseModel):
    """Connection pool tuning parameters.

    Attributes:
        pool_size: Baseline number of persistent connections.
        max_overflow: Extra connections allowed above `pool_size`.
        pool_use_lifo: Whether to reuse most-recently-used connections first.
        pool_pre_ping: Enable connection validation before checkout.
        pool_recycle: Seconds after which connections are recycled.
        pool_timeout: Seconds to wait for an available connection.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    pool_size: int = Field(default=100, ge=1, le=1000)
    max_overflow: int = Field(default=500, ge=0, le=2000)
    pool_use_lifo: bool = Field(default=True)
    pool_pre_ping: bool = Field(default=True)
    pool_recycle: int = Field(default=3600, ge=300, le=86400)
    pool_timeout: float = Field(default=30.0, gt=0.0, le=300.0)

    @field_validator("pool_size")
    @classmethod
    def _v_size(cls, v: int) -> int:
        """Validate the pool size."""
        if v <= 0:
            raise ValueError("pool_size must be positive")
        return v

    @field_validator("pool_timeout")
    @classmethod
    def _v_timeout(cls, v: float) -> float:
        """Validate the pool timeout."""
        if v <= 0:
            raise ValueError("pool_timeout must be positive")
        return v


class DatabaseMonitoringConfig(BaseModel):
    """Monitoring and metrics configuration.

    Attributes:
        enable_monitoring: Enable internal monitoring hooks.
        enable_metrics: Enable Prometheus metrics counters/gauges.
        enable_query_tracking: Track per-query timings in memory.
        slow_query_threshold: Seconds considered a slow query.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    enable_monitoring: bool = True
    enable_metrics: bool = False
    enable_query_tracking: bool = True
    slow_query_threshold: float = Field(default=1.0, gt=0.0, le=60.0)


class DatabaseSecurityConfig(BaseModel):
    """Security and rate-limiting configuration.

    Attributes:
        enable_security: Enable security checks (e.g., SQL guardrail).
        enable_rate_limiting: Enable per-user in-process rate limiting.
        enable_audit_logging: Emit audit events for write operations.
        rate_limit_requests: Requests per minute threshold per user.
        rate_limit_burst: Allowed burst tokens per minute.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    enable_security: bool = True
    enable_rate_limiting: bool = True
    enable_audit_logging: bool = True
    rate_limit_requests: int = Field(default=1000, ge=1, le=100000)
    rate_limit_burst: int = Field(default=2000, ge=1, le=200000)

    @field_validator("rate_limit_burst")
    @classmethod
    def _v_burst(cls, v: int, info) -> int:  # type: ignore[no-any-unimported]
        """Validate the rate limit burst."""
        req = info.data.get("rate_limit_requests", 0)
        if v < req:
            raise ValueError("rate_limit_burst must be >= rate_limit_requests")
        return v


class DatabasePerformanceConfig(BaseModel):
    """Performance-related feature flags.

    Attributes:
        enable_read_replicas: Reserved for future read-replica routing.
        enable_circuit_breaker: Enable a simple circuit breaker guard.
        circuit_breaker_threshold: Consecutive failures to trip breaker.
        circuit_breaker_timeout: Seconds the breaker remains open.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    enable_read_replicas: bool = True
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = Field(default=5, ge=1, le=100)
    circuit_breaker_timeout: float = Field(default=60.0, gt=0.0, le=3600.0)


class DatabaseConfig(BaseModel):
    """Top-level database configuration grouping sub-configs.

    Attributes:
        pool: Pool configuration.
        monitoring: Monitoring and metrics configuration.
        security: Security and rate limiting configuration.
        performance: Performance feature flags.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    pool: DatabasePoolConfig = Field(default_factory=DatabasePoolConfig)
    monitoring: DatabaseMonitoringConfig = Field(
        default_factory=DatabaseMonitoringConfig
    )
    security: DatabaseSecurityConfig = Field(default_factory=DatabaseSecurityConfig)
    performance: DatabasePerformanceConfig = Field(
        default_factory=DatabasePerformanceConfig
    )

    @classmethod
    def create_default(cls) -> DatabaseConfig:
        """Create the default database configuration."""
        return cls()

    @classmethod
    def create_testing(cls) -> DatabaseConfig:
        """Create the testing database configuration."""
        return cls(
            pool=DatabasePoolConfig(
                pool_size=5,
                max_overflow=10,
                pool_use_lifo=False,
                pool_recycle=300,
                pool_timeout=10.0,
            ),
            monitoring=DatabaseMonitoringConfig(
                enable_monitoring=False,
                enable_metrics=False,
                enable_query_tracking=False,
                slow_query_threshold=5.0,
            ),
            security=DatabaseSecurityConfig(
                enable_security=False,
                enable_rate_limiting=False,
                enable_audit_logging=False,
                rate_limit_requests=100000,
                rate_limit_burst=200000,
            ),
            performance=DatabasePerformanceConfig(
                enable_read_replicas=False,
                enable_circuit_breaker=False,
                circuit_breaker_threshold=100,
                circuit_breaker_timeout=300.0,
            ),
        )


# ----------
# Monitoring
# ----------


class QueryType(Enum):
    """Logical database operation categories used for metrics."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UPSERT = "UPSERT"
    VECTOR_SEARCH = "VECTOR_SEARCH"
    COUNT = "COUNT"
    FUNCTION = "FUNCTION"
    RAW_SQL = "RAW_SQL"


class SecurityEvent(Enum):
    """Types of security events recorded by the service."""

    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class QueryMetrics(BaseModel):
    """Per-query runtime metrics sample.

    Attributes:
        query_type: Logical operation type.
        table: Target table if applicable.
        duration_ms: Elapsed time in milliseconds.
        success: Whether the operation completed without error.
        error: Error summary when `success` is False.
        timestamp: UTC timestamp of completion.
        user_id: Optional user attribution for rate limits/auditing.
    """

    query_type: QueryType
    table: str | None = None
    duration_ms: float
    success: bool = True
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None


class ConnectionStats(BaseModel):
    """Lightweight connection/capacity statistics.

    Attributes:
        active_connections: Number of in-use connections.
        idle_connections: Number of idle connections.
        total_connections: Total connections tracked (if applicable).
        pool_size: Configured base pool size.
        max_overflow: Configured overflow capacity.
        connection_errors: Total connection-related errors observed.
        last_error: Most recent error message if any.
        uptime_seconds: Service uptime in seconds.
        queries_executed: Total executed queries since start.
        avg_query_time_ms: Rolling average time across successful queries.
        pool_utilization: Percent utilization of the (pool_size + overflow).
    """

    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    pool_size: int = 0
    max_overflow: int = 0
    connection_errors: int = 0
    last_error: str | None = None
    uptime_seconds: float = 0
    queries_executed: int = 0
    avg_query_time_ms: float = 0
    pool_utilization: float = 0


class SecurityAlert(BaseModel):
    """Security alert record for diagnostics and auditing.

    Attributes:
        event_type: Type of security event.
        severity: Severity label (e.g., low/medium/high/critical).
        message: Human-readable description.
        details: Structured details for troubleshooting.
        timestamp: UTC timestamp of the event.
        user_id: Optional user ID involved in the event.
    """

    event_type: SecurityEvent
    severity: str
    message: str
    details: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None


@dataclass
class Metrics:
    """Prometheus metric handles used by the service.

    Attributes:
        connection_attempts: Counter for connection attempts by status.
        query_duration: Histogram for query durations.
        query_count: Counter for total queries by status.
        slow_queries: Counter for slow queries detected.
        health_status: Gauge for component health (1 healthy / 0 unhealthy).
        security_events: Counter for security events by type/severity.
        rate_limit_hits: Counter for per-user rate limit hits.
    """

    connection_attempts: Any
    query_duration: Any
    query_count: Any
    slow_queries: Any
    health_status: Any
    security_events: Any
    rate_limit_hits: Any


# ----------------
# Database service
# ----------------


class DatabaseService:
    """Supabase-backed database service.

    This service centralizes all database access using the Supabase Python
    client (PostgREST + RPC). It provides typed, async CRUD helpers, vector
    search utilities, RPC execution, and minimal monitoring/guardrails.

    Attributes:
        settings: Resolved application settings.
        _config: Database configuration used by the service.
        _supabase_client: Underlying Supabase sync client (wrapped via to_thread).
        _connected: Whether `connect()` completed successfully.
        _start_time: Service start time in seconds.
        _query_metrics: In-memory rolling query metrics.
        _security_alerts: Captured security alerts.
        _connection_stats: Lightweight connection statistics.
        _metrics: Optional Prometheus metrics container.
    """

    def __init__(
        self, settings: Settings | None = None, config: DatabaseConfig | None = None
    ):
        """Initialize the DatabaseService."""
        self.settings = settings or get_settings()
        self._config = config or DatabaseConfig.create_default()

        # Expose select config values
        self.pool_size = self._config.pool.pool_size
        self.max_overflow = self._config.pool.max_overflow
        self.pool_timeout = self._config.pool.pool_timeout
        self.slow_query_threshold = self._config.monitoring.slow_query_threshold
        self.enable_query_tracking = self._config.monitoring.enable_query_tracking
        self.enable_security = self._config.security.enable_security
        self.enable_rate_limiting = self._config.security.enable_rate_limiting
        self.enable_audit_logging = self._config.security.enable_audit_logging
        self.enable_circuit_breaker = self._config.performance.enable_circuit_breaker
        self.circuit_breaker_threshold = (
            self._config.performance.circuit_breaker_threshold
        )
        self.circuit_breaker_timeout = self._config.performance.circuit_breaker_timeout

        # State
        self._supabase_client: Client | None = None
        self._connected = False
        self._start_time = time.time()
        self._query_metrics: deque[QueryMetrics] = deque(maxlen=1000)
        self._security_alerts: list[SecurityAlert] = []
        self._connection_stats = ConnectionStats(
            pool_size=self.pool_size, max_overflow=self.max_overflow
        )

        self._metrics: Metrics | None = None
        if self._config.monitoring.enable_metrics:
            self._initialize_metrics()

        # OpenTelemetry tracer and meter
        self._otel_tracer = get_tracer("tripsage_core.db")
        self._otel_meter = get_meter("tripsage_core.db")

        # Circuit breaker
        self._cb_failures = 0
        self._cb_last_failure = 0.0
        self._cb_open = False

        # Simple per-minute rate limiter counter
        self._rate_window: dict[str, tuple[int, float]] = {}

    # ---- connection ----

    @property
    def is_connected(self) -> bool:
        """Check if the database service is connected."""
        return self._connected and self._supabase_client is not None

    @property
    def client(self) -> Client:
        """Get the Supabase client."""
        if not self.is_connected:
            raise CoreServiceError(
                message="Database service not connected. Call connect() first.",
                code="DATABASE_NOT_CONNECTED",
                service="DatabaseService",
            )
        assert self._supabase_client is not None
        return self._supabase_client

    async def connect(self) -> None:
        """Establish the Supabase client connection.

        Ensures the client is created and a lightweight connectivity check
        succeeds. Safe to call multiple times.

        Raises:
            CoreDatabaseError: If initialization or connectivity checks fail.
        """
        if self._connected:
            return
        start = time.time()
        try:
            await self._initialize_supabase_client()
            await self._test_connections()
            self._connected = True
            if self._metrics:
                self._metrics.connection_attempts.labels(status="success").inc()
                self._metrics.health_status.labels(component="connection").set(1)
            self._connection_stats.uptime_seconds = 0
            self._connection_stats.connection_errors = 0
            logger.info("Database service connected in %.2fs.", time.time() - start)
        except Exception as e:
            self._connected = False
            if self._metrics:
                self._metrics.connection_attempts.labels(status="failure").inc()
                self._metrics.health_status.labels(component="connection").set(0)
            self._connection_stats.connection_errors += 1
            self._connection_stats.last_error = str(e)
            logger.exception("Failed to connect to database")
            raise CoreDatabaseError(
                message=f"Failed to connect to database: {e!s}",
                code="DATABASE_CONNECTION_FAILED",
                details={"error": str(e)},
            ) from e

    async def close(self) -> None:
        """Close the Supabase client and reset internal state."""
        self._supabase_client = None
        self._connected = False
        if self._metrics:
            self._metrics.health_status.labels(component="connection").set(0)
        logger.info("Database service closed")

    async def ensure_connected(self) -> None:
        """Connect on-demand if not already connected."""
        if not self.is_connected:
            await self.connect()

    async def _initialize_supabase_client(self) -> None:
        try:
            supabase_url = self.settings.database_url
            supabase_key = self.settings.database_public_key.get_secret_value()
            if not supabase_url or not supabase_url.startswith("https://"):
                raise CoreDatabaseError(
                    message=f"Invalid Supabase URL format: {supabase_url}",
                    code="INVALID_DATABASE_URL",
                )
            if not supabase_key or len(supabase_key) < 20:
                raise CoreDatabaseError(
                    message="Invalid Supabase API key", code="INVALID_DATABASE_KEY"
                )
            self._supabase_client = create_client(supabase_url, supabase_key)
        except Exception:
            logger.exception("Failed to initialize Supabase client")
            raise

    async def _test_connections(self) -> None:
        async with asyncio.TaskGroup() as tg:
            supabase_task = tg.create_task(
                asyncio.to_thread(
                    lambda: self.client.table("users").select("id").limit(1).execute()
                ),
                name="supabase_connection_test",
            )
        try:
            await supabase_task
        except Exception as e:
            raise CoreDatabaseError(
                message=f"Supabase connection test failed: {e!s}",
                code="SUPABASE_CONNECTION_TEST_FAILED",
            ) from e

    # ---- metrics ----

    def _initialize_metrics(self) -> None:
        try:
            from prometheus_client import Counter, Gauge, Histogram

            self._metrics = Metrics(
                connection_attempts=Counter(
                    "tripsage_db_connection_attempts_total",
                    "Total database connection attempts",
                    ["status"],
                ),
                query_duration=Histogram(
                    "tripsage_db_query_duration_seconds",
                    "Database query execution time",
                    ["operation", "table", "status"],
                    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
                ),
                query_count=Counter(
                    "tripsage_db_queries_total",
                    "Total database queries executed",
                    ["operation", "table", "status"],
                ),
                slow_queries=Counter(
                    "tripsage_db_slow_queries_total",
                    "Total slow queries detected",
                    ["operation", "table"],
                ),
                health_status=Gauge(
                    "tripsage_db_health_status",
                    "Database health status (1=healthy, 0=unhealthy)",
                    ["component"],
                ),
                security_events=Counter(
                    "tripsage_db_security_events_total",
                    "Total security events detected",
                    ["event_type", "severity"],
                ),
                rate_limit_hits=Counter(
                    "tripsage_db_rate_limit_hits_total",
                    "Total rate limit hits",
                    ["user_id"],
                ),
            )
        except (ImportError, ValueError, RuntimeError, TypeError):
            logger.warning("Prometheus metrics unavailable; metrics disabled")
            self._metrics = None

    @asynccontextmanager
    async def _monitor_query(
        self,
        query_type: QueryType,
        table: str | None = None,
        user_id: str | None = None,
    ):
        start_time = time.time()
        self._check_circuit_breaker()
        await self._check_rate_limit(user_id)
        span_ctx = contextlib.nullcontext()
        if self._otel_tracer:
            with contextlib.suppress(Exception):  # pragma: no cover
                span_ctx = self._otel_tracer.start_as_current_span(
                    name=f"db.{query_type.value.lower()}",
                    attributes={
                        "db.system": "postgresql",
                        "db.provider": "supabase",
                        "db.operation": query_type.value,
                        "db.table": table or "unknown",
                        "enduser.id": user_id or "anonymous",
                    },
                )
        try:
            with span_ctx as _span:  # type: ignore[assignment]
                yield
            duration = time.time() - start_time
            if _span is not None:
                with contextlib.suppress(Exception):  # pragma: no cover
                    _span.set_attribute("db.duration_sec", duration)
            if self.enable_query_tracking:
                self._query_metrics.append(
                    QueryMetrics(
                        query_type=query_type,
                        table=table,
                        duration_ms=duration * 1000,
                        success=True,
                        user_id=user_id,
                    )
                )
            if self._metrics:
                self._metrics.query_duration.labels(
                    operation=query_type.value,
                    table=table or "unknown",
                    status="success",
                ).observe(duration)
                self._metrics.query_count.labels(
                    operation=query_type.value,
                    table=table or "unknown",
                    status="success",
                ).inc()
                if duration > self.slow_query_threshold:
                    self._metrics.slow_queries.labels(
                        operation=query_type.value, table=table or "unknown"
                    ).inc()
            self._connection_stats.queries_executed += 1
            self._record_circuit_breaker_success()
        except Exception:
            duration = time.time() - start_time
            with contextlib.suppress(Exception):  # pragma: no cover
                if "_span" in locals() and _span is not None:
                    _span.set_attribute("db.duration_sec", duration)
                    _span.record_exception(Exception("query_failed"))
            if self.enable_query_tracking:
                self._query_metrics.append(
                    QueryMetrics(
                        query_type=query_type,
                        table=table,
                        duration_ms=duration * 1000,
                        success=False,
                    )
                )
            if self._metrics:
                self._metrics.query_duration.labels(
                    operation=query_type.value, table=table or "unknown", status="error"
                ).observe(duration)
                self._metrics.query_count.labels(
                    operation=query_type.value, table=table or "unknown", status="error"
                ).inc()
            self._record_circuit_breaker_failure()
            raise
        finally:
            pass

    # ---- circuit breaker & rate limiting ----

    def _check_circuit_breaker(self) -> None:
        """Check the circuit breaker."""
        if not self.enable_circuit_breaker:
            return
        if (
            self._cb_open
            and (time.time() - self._cb_last_failure) <= self.circuit_breaker_timeout
        ):
            raise CoreServiceError(
                message="Circuit breaker open",
                code="CIRCUIT_BREAKER_OPEN",
                service="DatabaseService",
            )
        if (
            self._cb_open
            and (time.time() - self._cb_last_failure) > self.circuit_breaker_timeout
        ):
            self._cb_open = False
            self._cb_failures = 0

    def _record_circuit_breaker_success(self) -> None:
        """Record the circuit breaker success."""
        if self._cb_failures:
            self._cb_failures = 0

    def _record_circuit_breaker_failure(self) -> None:
        """Record the circuit breaker failure."""
        self._cb_failures += 1
        self._cb_last_failure = time.time()
        if self._cb_failures >= self.circuit_breaker_threshold:
            self._cb_open = True

    async def _check_rate_limit(self, user_id: str | None) -> None:
        """Check the rate limit."""
        if not self.enable_rate_limiting or not user_id:
            return
        now = time.time()
        window_start = now - 60
        if user_id in self._rate_window:
            count, win = self._rate_window[user_id]
            if win < window_start:
                self._rate_window[user_id] = (1, now)
                return
            if count >= self._config.security.rate_limit_requests:
                if self._metrics:
                    self._metrics.rate_limit_hits.labels(user_id=user_id).inc()
                raise CoreServiceError(
                    message="Rate limit exceeded",
                    code="RATE_LIMIT_EXCEEDED",
                    service="DatabaseService",
                )
            self._rate_window[user_id] = (count + 1, win)
        else:
            self._rate_window[user_id] = (1, now)

    # ---- CRUD ----

    async def insert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Insert records into a table.

        Args:
            table: Target table name.
            data: Single row or list of row dictionaries to insert.
            user_id: Optional user performing the action (for auditing/limits).

        Returns:
            Inserted rows as a list of dictionaries.

        Raises:
            CoreDatabaseError: If insertion fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.INSERT, table, user_id):
            try:
                result: Any = await asyncio.to_thread(
                    lambda: self.client.table(table).insert(data).execute()
                )
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id, "INSERT", table, len(result.data) if result.data else 0
                    )
                return result.data
            except Exception as e:
                logger.exception("INSERT error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed to insert into '{table}'",
                    code="INSERT_FAILED",
                    operation="INSERT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def select(
        self,
        table: str,
        columns: str = "*",
        *,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Select rows from a table with optional filtering and pagination.

        Args:
            table: Target table name.
            columns: Column selection string (e.g., "*", "id,name").
            filters: Mapping of equality or operator mappings (e.g.,
                {"id": 1} or {"created_at": {"gte": "..."}}).
            order_by: Column name to order by; prefix with '-' for DESC.
            limit: Optional limit of rows.
            offset: Optional offset for pagination.
            user_id: Optional user attribution.

        Returns:
            Selected rows as a list of dictionaries.

        Raises:
            CoreDatabaseError: If selection fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.SELECT, table, user_id):
            try:
                query = self.client.table(table).select(columns)
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, dict):
                            for op, val in value.items():
                                query = getattr(query, op)(key, val)
                        else:
                            query = query.eq(key, value)
                if order_by:
                    if order_by.startswith("-"):
                        query = query.order(order_by[1:], desc=True)
                    else:
                        query = query.order(order_by)
                if limit is not None:
                    query = query.limit(limit)
                if offset is not None:
                    query = query.offset(offset)
                result: Any = await asyncio.to_thread(query.execute)
                return result.data
            except Exception as e:
                logger.exception("SELECT error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed to select from '{table}'",
                    code="SELECT_FAILED",
                    operation="SELECT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any],
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Update rows in a table.

        Args:
            table: Target table name.
            data: Partial row dictionary with fields to update.
            filters: Equality filters identifying rows to update.
            user_id: Optional user attribution.

        Returns:
            Updated rows as a list of dictionaries.

        Raises:
            CoreDatabaseError: If update fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.UPDATE, table, user_id):
            try:
                query = self.client.table(table).update(data)
                for k, v in filters.items():
                    query = query.eq(k, v)
                result: Any = await asyncio.to_thread(query.execute)
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id, "UPDATE", table, len(result.data) if result.data else 0
                    )
                return result.data
            except Exception as e:
                logger.exception("UPDATE error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed to update '{table}'",
                    code="UPDATE_FAILED",
                    operation="UPDATE",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def upsert(
        self,
        table: str,
        data: dict[str, Any] | list[dict[str, Any]],
        on_conflict: str | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Insert-or-update rows in a table.

        Args:
            table: Target table name.
            data: Single row or list of row dictionaries.
            on_conflict: Column(s) used to resolve conflicts (e.g., "id").
            user_id: Optional user attribution.

        Returns:
            Upserted rows as a list of dictionaries.

        Raises:
            CoreDatabaseError: If upsert fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.UPSERT, table, user_id):
            try:
                query = self.client.table(table).upsert(data)
                if on_conflict and hasattr(query, "on_conflict"):
                    query = query.on_conflict(on_conflict)  # type: ignore[call-arg]  # pylint: disable=no-member
                result: Any = await asyncio.to_thread(query.execute)
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id, "UPSERT", table, len(result.data) if result.data else 0
                    )
                return result.data
            except Exception as e:
                logger.exception("UPSERT error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed to upsert into '{table}'",
                    code="UPSERT_FAILED",
                    operation="UPSERT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def delete(
        self, table: str, filters: dict[str, Any], user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Delete rows from a table.

        Args:
            table: Target table name.
            filters: Equality filters identifying rows to delete.
            user_id: Optional user attribution.

        Returns:
            Deleted rows returned by PostgREST.

        Raises:
            CoreDatabaseError: If deletion fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.DELETE, table, user_id):
            try:
                query = self.client.table(table).delete()
                for k, v in filters.items():
                    query = query.eq(k, v)
                result: Any = await asyncio.to_thread(query.execute)
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id, "DELETE", table, len(result.data) if result.data else 0
                    )
                return result.data
            except Exception as e:
                logger.exception("DELETE error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed to delete from '{table}'",
                    code="DELETE_FAILED",
                    operation="DELETE",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def count(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> int:
        """Count rows matching optional filters.

        Args:
            table: Target table name.
            filters: Equality filters to apply before counting.
            user_id: Optional user attribution.

        Returns:
            Exact number of rows matching the filter.

        Raises:
            CoreDatabaseError: If count fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.COUNT, table, user_id):
            try:
                query = self.client.table(table).select("*", count="exact")  # type: ignore[arg-type]
                if filters:
                    for k, v in filters.items():
                        query = query.eq(k, v)
                result: Any = await asyncio.to_thread(query.execute)
                return int(getattr(result, "count", 0) or 0)
            except Exception as e:
                logger.exception("COUNT error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed to count records in '{table}'",
                    code="COUNT_FAILED",
                    operation="COUNT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    # ---- Vector search ----

    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: list[float],
        *,
        limit: int = 10,
        similarity_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform a vector similarity search using pgvector ordering.

        Args:
            table: Target table name containing the vector column.
            vector_column: Name of the vector column (pgvector type).
            query_vector: Query embedding vector.
            limit: Maximum number of results to return.
            similarity_threshold: Optional similarity threshold in [0, 1].
            filters: Optional equality filters to apply.
            user_id: Optional user attribution.

        Returns:
            Ranked rows with a computed ``distance`` field.

        Raises:
            CoreDatabaseError: If the vector search fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.VECTOR_SEARCH, table, user_id):
            try:
                vec = f"[{','.join(map(str, query_vector))}]"
                query = self.client.table(table).select(
                    f"*, {vector_column} <-> '{vec}' as distance"
                )
                if filters:
                    for k, v in filters.items():
                        query = query.eq(k, v)
                if similarity_threshold is not None:
                    dist_thr = 1 - similarity_threshold
                    query = query.lt(f"{vector_column} <-> '{vec}'", dist_thr)
                query = query.order(f"{vector_column} <-> '{vec}'").limit(limit)
                result: Any = await asyncio.to_thread(query.execute)
                return result.data
            except Exception as e:
                logger.exception("Vector search error for table '%s'", table)
                raise CoreDatabaseError(
                    message=f"Failed vector search on '{table}'",
                    code="VECTOR_SEARCH_FAILED",
                    operation="VECTOR_SEARCH",
                    table=table,
                    details={"error": str(e)},
                ) from e

    # ---- RPC / SQL ----

    async def execute_sql(
        self, sql: str, params: dict[str, Any] | None = None, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL through a trusted RPC wrapper.

        Args:
            sql: SQL text to execute. Use parameter placeholders handled by the RPC.
            params: Parameter mapping supplied to the RPC wrapper.
            user_id: Optional user attribution.

        Returns:
            Result rows as a list of dictionaries.

        Raises:
            CoreDatabaseError: If the SQL execution fails.
        """
        await self.ensure_connected()
        if self.enable_security:
            self._check_sql_injection(sql)
        async with self._monitor_query(QueryType.RAW_SQL, None, user_id):
            try:
                result: Any = await asyncio.to_thread(
                    self.client.rpc(
                        "execute_sql", {"sql": sql, "params": params or {}}
                    ).execute
                )
                return result.data
            except Exception as e:
                logger.exception("SQL execution error")
                raise CoreDatabaseError(
                    message="Failed to execute SQL",
                    code="SQL_EXECUTION_FAILED",
                    operation="EXECUTE_SQL",
                    details={"error": str(e), "sql": sql},
                ) from e

    async def call_function(
        self,
        function_name: str,
        params: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> Any:
        """Invoke a Postgres function via Supabase RPC.

        Args:
            function_name: Name of the function to invoke.
            params: Optional mapping of parameters.
            user_id: Optional user attribution.

        Returns:
            Function return payload as provided by Supabase.

        Raises:
            CoreDatabaseError: If the RPC call fails.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.FUNCTION, function_name, user_id):
            try:
                result: Any = await asyncio.to_thread(
                    self.client.rpc(function_name, params or {}).execute
                )
                return result.data
            except Exception as e:
                logger.exception("Function call error for '%s'", function_name)
                raise CoreDatabaseError(
                    message=f"Failed to call function '{function_name}'",
                    code="FUNCTION_CALL_FAILED",
                    operation="CALL_FUNCTION",
                    details={"error": str(e)},
                ) from e

    # ---- Convenience helpers used by wrappers/services ----
    class _Batch:
        """Non-atomic batched operations executor.

        Batches CRUD operations and executes them sequentially when
        ``execute()`` is called. This does NOT provide transactional
        atomicity—use a database RPC if atomic semantics are required.

        Attributes:
            svc: Parent DatabaseService.
            user_id: Optional user attribution for auditing.
            ops: Recorded operations to execute in order.
        """

        def __init__(self, svc: DatabaseService, user_id: str | None):
            self.svc = svc
            self.user_id = user_id
            self.ops: list[tuple[str, tuple]] = []

        async def __aenter__(self) -> DatabaseService._Batch:
            """Enter the batch context and ensure connectivity."""
            await self.svc.ensure_connected()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Exit the batch context without committing extra state."""
            return False

        def insert(self, table: str, data: dict[str, Any] | list[dict[str, Any]]):
            """Insert a record into a table."""
            self.ops.append(("insert", (table, data)))

        def update(self, table: str, data: dict[str, Any], filters: dict[str, Any]):
            """Update a record in a table."""
            self.ops.append(("update", (table, data, filters)))

        def delete(self, table: str, filters: dict[str, Any]):
            """Delete a record from a table."""
            self.ops.append(("delete", (table, filters)))

        async def execute(self) -> list[Any]:
            """Execute all recorded operations in order.

            Returns:
                List with each operation's result payload.
            """
            out: list[Any] = []
            for op, args in self.ops:
                if op == "insert":
                    out.append(await self.svc.insert(args[0], args[1], self.user_id))
                elif op == "update":
                    out.append(
                        await self.svc.update(args[0], args[1], args[2], self.user_id)
                    )
                elif op == "delete":
                    out.append(await self.svc.delete(args[0], args[1], self.user_id))
            return out

    def transaction(self, user_id: str | None = None) -> DatabaseService._Batch:
        """Create a new non-atomic batch context.

        Args:
            user_id: Optional user attribution for auditing.

        Returns:
            A batched context manager supporting ``insert``, ``update``,
            ``delete`` and ``execute``.
        """
        return DatabaseService._Batch(self, user_id)

    async def create_trip(
        self, trip_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Create a new trip record."""
        result = await self.insert("trips", trip_data, user_id)
        return result[0] if result else {}

    async def get_trip_by_id(
        self, trip_id: str, user_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get trip by ID."""
        result = await self.select(
            "trips", "*", filters={"id": trip_id}, user_id=user_id
        )
        return result[0] if result else None

    async def get_user_trips(self, user_id: str) -> list[dict[str, Any]]:
        """Get all trips for a user."""
        return await self.select(
            "trips",
            "*",
            filters={"user_id": user_id},
            order_by="-created_at",
            user_id=user_id,
        )

    async def get_trip(
        self, trip_id: str, user_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get trip by ID."""
        result = await self.get_trip_by_id(trip_id, user_id)
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result

    async def update_trip(
        self, trip_id: str, trip_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Update trip record."""
        result = await self.update("trips", trip_data, {"id": trip_id}, user_id)
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]

    async def delete_trip(self, trip_id: str, user_id: str | None = None) -> bool:
        """Delete trip record."""
        result = await self.delete("trips", {"id": trip_id}, user_id)
        return len(result) > 0

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new user record."""
        result = await self.insert("users", user_data)
        return result[0] if result else {}

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get user by ID."""
        result = await self.select("users", "*", filters={"id": user_id})
        return result[0] if result else None

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email."""
        result = await self.select("users", "*", filters={"email": email})
        return result[0] if result else None

    async def update_user(
        self, user_id: str, user_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update user record."""
        result = await self.update("users", user_data, {"id": user_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"User {user_id} not found",
                details={"resource_id": user_id, "resource_type": "user"},
            )
        return result[0]

    async def save_flight_search(
        self, search_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Persist a flight search request.

        Args:
            search_data: Search parameters to store.
            user_id: Optional user attribution.

        Returns:
            The created record.
        """
        result = await self.insert("flight_searches", search_data, user_id)
        return result[0] if result else {}

    async def save_accommodation_search(
        self, search_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Persist an accommodation search request.

        Args:
            search_data: Search parameters to store.
            user_id: Optional user attribution.

        Returns:
            The created record.
        """
        result = await self.insert("accommodation_searches", search_data, user_id)
        return result[0] if result else {}

    async def save_flight_option(
        self, option_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Persist a flight option candidate.

        Args:
            option_data: Flight option payload.
            user_id: Optional user attribution.

        Returns:
            The created record.
        """
        result = await self.insert("flight_options", option_data, user_id)
        return result[0] if result else {}

    async def get_user_flight_searches(self, user_id: str) -> list[dict[str, Any]]:
        """List flight searches created by a user.

        Args:
            user_id: User identifier.

        Returns:
            List of search rows.
        """
        return await self.select(
            "flight_searches",
            "*",
            filters={"user_id": user_id},
            order_by="-created_at",
            user_id=user_id,
        )

    async def save_accommodation_option(
        self, option_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Persist an accommodation option candidate.

        Args:
            option_data: Option payload to store.
            user_id: Optional user attribution.

        Returns:
            The created record.
        """
        result = await self.insert("accommodation_options", option_data, user_id)
        return result[0] if result else {}

    async def get_user_accommodation_searches(
        self, user_id: str
    ) -> list[dict[str, Any]]:
        """List accommodation searches created by a user.

        Args:
            user_id: User identifier.

        Returns:
            List of search rows.
        """
        return await self.select(
            "accommodation_searches",
            "*",
            filters={"user_id": user_id},
            order_by="-created_at",
            user_id=user_id,
        )

    async def create_chat_session(
        self, session_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Create a chat session row.

        Args:
            session_data: Session payload.
            user_id: Optional user attribution.

        Returns:
            The created session.
        """
        result = await self.insert("chat_sessions", session_data, user_id)
        return result[0] if result else {}

    async def create_chat_message(
        self, message_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Create a chat message row.

        Args:
            message_data: Message payload.
            user_id: Optional user attribution.

        Returns:
            The created message.
        """
        result = await self.insert("chat_messages", message_data, user_id)
        return result[0] if result else {}

    async def update_session_timestamp(self, session_id: str) -> bool:
        """Update ``updated_at`` timestamp for a chat session.

        Args:
            session_id: Chat session identifier.

        Returns:
            True if any row was updated.
        """
        now = datetime.now(UTC).isoformat()
        result = await self.update(
            "chat_sessions", {"updated_at": now}, {"id": session_id}
        )
        return len(result) > 0

    async def save_chat_message(
        self, message_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Store a chat message.

        Args:
            message_data: Message payload.
            user_id: Optional user attribution.

        Returns:
            The created message.
        """
        result = await self.insert("chat_messages", message_data, user_id)
        return result[0] if result else {}

    async def get_chat_history(
        self, session_id: str, limit: int = 50, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch chat messages for a session.

        Args:
            session_id: Chat session identifier.
            limit: Max messages to return.
            user_id: Optional user attribution.

        Returns:
            List of chat messages.
        """
        return await self.select(
            "chat_messages",
            "*",
            filters={"session_id": session_id},
            order_by="created_at",
            limit=limit,
            user_id=user_id,
        )

    # --- Additional chat helpers used by ChatService ---

    async def get_user_chat_sessions(
        self, user_id: str, limit: int = 10, include_ended: bool = False
    ) -> list[dict[str, Any]]:
        """List chat sessions for a user.

        Args:
            user_id: User identifier.
            limit: Maximum number of sessions.
            include_ended: Include sessions with ``ended_at`` set.

        Returns:
            List of session rows.
        """
        filters: dict[str, Any] = {"user_id": user_id}
        if not include_ended:
            filters["ended_at"] = {"is_": "null"}
        return await self.select(
            "chat_sessions",
            "*",
            filters=filters,
            order_by="-updated_at",
            limit=limit,
            user_id=user_id,
        )

    async def get_chat_session(
        self, session_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Fetch a chat session by id for a user."""
        rows = await self.select(
            "chat_sessions",
            "*",
            filters={"id": session_id, "user_id": user_id},
            limit=1,
            user_id=user_id,
        )
        return rows[0] if rows else None

    async def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """Return message count and last message timestamp for a session."""
        count = await self.count("chat_messages", {"session_id": session_id})
        last_rows = await self.select(
            "chat_messages",
            "created_at",
            filters={"session_id": session_id},
            order_by="-created_at",
            limit=1,
        )
        last_message_at = last_rows[0]["created_at"] if last_rows else None
        return {"message_count": count, "last_message_at": last_message_at}

    async def get_session_messages(
        self, session_id: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List messages for a chat session ordered by creation time."""
        return await self.select(
            "chat_messages",
            "*",
            filters={"session_id": session_id},
            order_by="created_at",
            limit=limit or 100,
            offset=offset,
        )

    async def get_message_tool_calls(self, message_id: str) -> list[dict[str, Any]]:
        """List tool calls attached to a message."""
        return await self.select(
            "chat_tool_calls", "*", filters={"message_id": message_id}
        )

    async def create_tool_call(self, tool_call_data: dict[str, Any]) -> dict[str, Any]:
        """Create a tool call row."""
        result = await self.insert("chat_tool_calls", tool_call_data)
        return result[0] if result else {}

    async def update_tool_call(
        self, tool_call_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update a tool call by id and return the updated row if any."""
        rows = await self.update(
            "chat_tool_calls", update_data, filters={"id": tool_call_id}
        )
        return rows[0] if rows else None

    async def end_chat_session(self, session_id: str) -> bool:
        """Mark a chat session as ended."""
        now = datetime.now(UTC).isoformat()
        rows = await self.update(
            "chat_sessions", {"ended_at": now, "updated_at": now}, {"id": session_id}
        )
        return len(rows) > 0

    async def get_user_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        """List API keys for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of API key rows.
        """
        return await self.select(
            "api_keys", "*", filters={"user_id": user_id}, user_id=user_id
        )

    async def get_api_key(
        self, user_id: str, service_name: str
    ) -> dict[str, Any] | None:
        """Fetch a user's API key for a service.

        Args:
            user_id: User identifier.
            service_name: Logical service name.

        Returns:
            API key row or None.
        """
        result = await self.select(
            "api_keys",
            "*",
            filters={"user_id": user_id, "service_name": service_name},
            user_id=user_id,
        )
        return result[0] if result else None

    async def save_api_key(
        self, key_data: dict[str, Any], user_id: str | None = None
    ) -> dict[str, Any]:
        """Create or update an API key using upsert.

        Args:
            key_data: API key payload.
            user_id: Optional user attribution.

        Returns:
            Saved API key row.
        """
        result = await self.upsert(
            "api_keys", key_data, on_conflict="user_id,service_name", user_id=user_id
        )
        return result[0] if result else {}

    async def create_api_key(self, key_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new API key row.

        Args:
            key_data: API key payload.

        Returns:
            Created API key row.
        """
        user_id = key_data.get("user_id")
        result = await self.insert("api_keys", key_data, user_id)
        return result[0] if result else {}

    async def get_api_key_for_service(
        self, user_id: str, service: str
    ) -> dict[str, Any] | None:
        """Alias for :meth:`get_api_key` for backward compatibility.

        Args:
            user_id: User identifier.
            service: Service name.

        Returns:
            API key row or None.
        """
        return await self.get_api_key(user_id, service)

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Fetch an API key by ID for a user.

        Args:
            key_id: Key identifier.
            user_id: User identifier.

        Returns:
            API key row or None.
        """
        result = await self.select(
            "api_keys", "*", filters={"id": key_id, "user_id": user_id}, user_id=user_id
        )
        return result[0] if result else None

    async def update_api_key_last_used(self, key_id: str) -> bool:
        """Update the ``last_used`` and ``updated_at`` timestamps for a key.

        Args:
            key_id: Key identifier.

        Returns:
            True if any row was updated.
        """
        now = datetime.now(UTC).isoformat()
        result = await self.update(
            "api_keys", {"last_used": now, "updated_at": now}, {"id": key_id}
        )
        return len(result) > 0

    async def update_api_key_validation(
        self, key_id: str, is_valid: bool, validated_at: datetime
    ) -> bool:
        """Record a key validation result and timestamp.

        Args:
            key_id: Key identifier.
            is_valid: Validation status.
            validated_at: Validation timestamp in UTC.

        Returns:
            True if any row was updated.
        """
        now = datetime.now(UTC).isoformat()
        result = await self.update(
            "api_keys",
            {
                "is_valid": is_valid,
                "last_validated": validated_at.isoformat(),
                "updated_at": now,
            },
            {"id": key_id},
        )
        return len(result) > 0

    async def update_api_key(
        self, key_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update arbitrary fields for a key.

        Args:
            key_id: Key identifier.
            update_data: Fields to update.

        Returns:
            Updated API key row or empty dict.
        """
        result = await self.update("api_keys", update_data, {"id": key_id})
        return result[0] if result else {}

    async def log_api_key_usage(self, usage_data: dict[str, Any]) -> dict[str, Any]:
        """Append an API key usage event.

        Args:
            usage_data: Usage payload to persist.

        Returns:
            Created usage row.
        """
        user_id = usage_data.get("user_id")
        result = await self.insert("api_key_usage_logs", usage_data, user_id)
        return result[0] if result else {}

    async def delete_api_key(self, key_id: str, user_id: str) -> bool:
        """Delete a key by ID for the given user.

        Args:
            key_id: Key identifier.
            user_id: User identifier.

        Returns:
            True if any row was deleted.
        """
        result = await self.delete(
            "api_keys", {"id": key_id, "user_id": user_id}, user_id
        )
        return len(result) > 0

    async def vector_search_destinations(
        self,
        query_vector: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience wrapper for destination vector search.

        Args:
            query_vector: Embedding to search with.
            limit: Max rows to return.
            similarity_threshold: Optional similarity threshold in [0, 1].
            user_id: Optional user attribution.

        Returns:
            Ranked destination rows including ``distance``.
        """
        return await self.vector_search(
            "destinations",
            "embedding",
            query_vector,
            limit=limit,
            similarity_threshold=similarity_threshold,
            user_id=user_id,
        )

    async def save_destination_embedding(
        self,
        destination_data: dict[str, Any],
        embedding: list[float],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Upsert a destination row with an embedding.

        Args:
            destination_data: Destination payload.
            embedding: Embedding vector to store.
            user_id: Optional user attribution.

        Returns:
            Saved destination row.
        """
        destination_data["embedding"] = embedding
        result = await self.upsert(
            "destinations", destination_data, on_conflict="id", user_id=user_id
        )
        return result[0] if result else {}

    async def get_trip_collaborators(self, trip_id: str) -> list[dict[str, Any]]:
        """List collaborators for a trip.

        Args:
            trip_id: Trip identifier.

        Returns:
            List of collaborator rows.
        """
        return await self.select(
            "trip_collaborators", "*", filters={"trip_id": trip_id}
        )

    async def add_trip_collaborator(
        self, collaborator_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Add or update a trip collaborator.

        Args:
            collaborator_data: Collaborator payload; must include
                ``trip_id``, ``user_id``, ``permission_level``, ``added_by``.

        Returns:
            Saved collaboration row.

        Raises:
            CoreDatabaseError: If a required field is missing or upsert fails.
        """
        required = ["trip_id", "user_id", "permission_level", "added_by"]
        for f in required:
            if f not in collaborator_data:
                raise CoreDatabaseError(
                    message=f"Missing required field: {f}",
                    code="MISSING_REQUIRED_FIELD",
                    operation="ADD_TRIP_COLLABORATOR",
                    details={"missing_field": f},
                )
        user_id = collaborator_data.get("added_by")
        result = await self.upsert(
            "trip_collaborators",
            collaborator_data,
            on_conflict="trip_id,user_id",
            user_id=user_id,
        )
        return result[0] if result else {}

    async def get_trip_collaborator(
        self, trip_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Fetch a specific collaborator for a trip and user.

        Args:
            trip_id: Trip identifier.
            user_id: Collaborator user identifier.

        Returns:
            Collaborator row or None.
        """
        result = await self.select(
            "trip_collaborators",
            "*",
            filters={"trip_id": trip_id, "user_id": user_id},
            user_id=user_id,
        )
        return result[0] if result else None

    async def get_trip_related_counts(self, trip_id: str) -> dict[str, int]:
        """Compute related entity counts for a trip.

        Args:
            trip_id: Trip identifier.

        Returns:
            Mapping of count names to values (flights, accommodations, messages).
        """
        flights = await self.count("flights", {"trip_id": trip_id})
        accommodations = await self.count("accommodations", {"trip_id": trip_id})
        messages = await self.count("chat_messages", {"trip_id": trip_id})
        return {
            "flights": flights,
            "accommodations": accommodations,
            "messages": messages,
        }

    async def search_trips(
        self,
        search_filters: dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search trips using filters and simple text matching.

        Args:
            search_filters: Filter mapping (user_id, status, visibility, query,
                destinations, tags, date_range).
            limit: Page size.
            offset: Page offset.
            user_id: Optional user attribution.

        Returns:
            List of trips matching the criteria.
        """
        await self.ensure_connected()
        async with self._monitor_query(QueryType.SELECT, "trips", user_id):
            q = self.client.table("trips").select("*")
            if "user_id" in search_filters:
                q = q.eq("user_id", search_filters["user_id"])
            if "status" in search_filters:
                q = q.eq("status", search_filters["status"])
            if "visibility" in search_filters:
                q = q.eq("visibility", search_filters["visibility"])
            if search_filters.get("query"):
                text = search_filters["query"]
                q = q.or_(f"name.ilike.%{text}%,destination.ilike.%{text}%")
            if search_filters.get("destinations"):
                ors = ",".join(
                    [f"destination.ilike.%{d}%" for d in search_filters["destinations"]]
                )
                if ors:
                    q = q.or_(ors)
            if search_filters.get("tags"):
                q = q.overlaps("notes", search_filters["tags"])  # type: ignore[call-arg]
            if "date_range" in search_filters:
                dr = search_filters["date_range"]
                if "start_date" in dr:
                    q = q.gte("start_date", dr["start_date"].isoformat())
                if "end_date" in dr:
                    q = q.lte("end_date", dr["end_date"].isoformat())
            q = q.order("created_at").limit(limit).offset(offset)
        result: Any = await asyncio.to_thread(q.execute)
        return result.data

    async def delete_api_key_by_service(self, user_id: str, service_name: str) -> bool:
        """Delete an API key by service for a user.

        Args:
            user_id: User identifier.
            service_name: Logical service name.

        Returns:
            True if a row was deleted.
        """
        result = await self.delete(
            "api_keys", {"user_id": user_id, "service_name": service_name}, user_id
        )
        return len(result) > 0

    async def get_popular_destinations(
        self, limit: int = 10, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return the most frequently used destinations from trips.

        Args:
            limit: Maximum number of destinations to return.
            user_id: Optional user attribution.

        Returns:
            Aggregated rows with destination and search_count.
        """
        return await self.execute_sql(
            """
            SELECT destination, COUNT(*) AS search_count
            FROM trips
            WHERE destination IS NOT NULL
            GROUP BY destination
            ORDER BY search_count DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
            user_id,
        )

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        """Collect high-level usage statistics for a user.

        Args:
            user_id: User identifier.

        Returns:
            Mapping of counters (trips, searches, total_searches).
        """
        trip_count = await self.count("trips", {"user_id": user_id}, user_id)
        flight_searches = await self.count(
            "flight_searches", {"user_id": user_id}, user_id
        )
        accommodation_searches = await self.count(
            "accommodation_searches", {"user_id": user_id}, user_id
        )
        return {
            "trip_count": trip_count,
            "flight_searches": flight_searches,
            "accommodation_searches": accommodation_searches,
            "total_searches": flight_searches + accommodation_searches,
        }

    # ---- Health / schema / stats ----

    async def health_check(self) -> bool:
        """Verify database connectivity.

        Returns:
            True when a very small probe query succeeds; False otherwise.
        """
        try:
            await self.ensure_connected()
            await asyncio.to_thread(
                self.client.table("users").select("id").limit(1).execute
            )
            if self._metrics:
                self._metrics.health_status.labels(component="overall").set(1)
            return True
        except Exception:
            logger.exception("Database health check failed")
            if self._metrics:
                self._metrics.health_status.labels(component="overall").set(0)
            return False

    async def get_table_info(
        self, table: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Fetch basic column metadata from information_schema.

        Args:
            table: Table name.
            user_id: Optional user attribution.

        Returns:
            Dict with ``columns`` list.
        """
        try:
            cols = await self.execute_sql(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %(table_name)s
                ORDER BY ordinal_position
                """,
                {"table_name": table},
                user_id,
            )
            return {"columns": cols}
        except Exception as e:
            logger.exception("Failed to get table info for '%s'", table)
            raise CoreDatabaseError(
                message=f"Failed to get schema for '{table}'",
                code="TABLE_INFO_FAILED",
                table=table,
                details={"error": str(e)},
            ) from e

    async def get_database_stats(self) -> dict[str, Any]:
        """Return service statistics and recent security/metrics summaries.

        Returns:
            Mapping of connection/query/security summaries.
        """
        stats: dict[str, Any] = {
            "connection_stats": self._connection_stats.model_dump(),
            "uptime_seconds": time.time() - self._start_time,
        }
        if self.enable_query_tracking and self._query_metrics:
            successful = [m for m in self._query_metrics if m.success]
            failed = [m for m in self._query_metrics if not m.success]
            stats["query_stats"] = {
                "total_queries": len(self._query_metrics),
                "successful_queries": len(successful),
                "failed_queries": len(failed),
                "avg_query_time_ms": (
                    sum(m.duration_ms for m in successful) / len(successful)
                )
                if successful
                else 0.0,
            }
        if self.enable_security and self._security_alerts:
            stats["security_stats"] = {
                "total_alerts": len(self._security_alerts),
                "recent_alerts": [a.model_dump() for a in self._security_alerts[-10:]],
            }
        return stats

    # ---- Helpers ----

    def _check_sql_injection(self, sql: str) -> None:
        # Heuristic guardrail; prefer parameterization and RPC in practice
        suspicious = [
            "--",
            "/*",
            "*/",
            "drop table",
            "truncate",
            "delete from",
            "union select",
            "or 1=1",
            "or '1'='1'",
        ]
        low = sql.lower()
        for pat in suspicious:
            if pat in low:
                alert = SecurityAlert(
                    event_type=SecurityEvent.SQL_INJECTION_ATTEMPT,
                    severity="critical",
                    message="Potential SQL injection attempt detected",
                    details={"pattern": pat, "sql_snippet": sql[:100]},
                )
                self._security_alerts.append(alert)
                if self._metrics:
                    self._metrics.security_events.labels(
                        event_type="sql_injection_attempt", severity="critical"
                    ).inc()
                raise CoreServiceError(
                    message="Potential SQL injection detected",
                    code="SQL_INJECTION_DETECTED",
                    service="DatabaseService",
                )

    def _log_audit_event(
        self, user_id: str | None, action: str, table: str, records_affected: int
    ) -> None:
        if not self.enable_audit_logging:
            return
        logger.info(
            "AUDIT: user=%s, action=%s, table=%s, records=%s, ts=%s",
            user_id,
            action,
            table,
            records_affected,
            datetime.now(UTC).isoformat(),
        )

    def clear_metrics(self) -> None:
        """Clear in-memory metrics and security alerts for this instance."""
        self._query_metrics.clear()
        self._security_alerts.clear()
        logger.info("Metrics and alerts cleared")


# -----------------
# Global entrypoints
# -----------------

_database_service: DatabaseService | None = None


async def get_database_service() -> DatabaseService:
    """Get a connected singleton DatabaseService instance.

    Returns:
        A connected DatabaseService.
    """
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
        await _database_service.connect()
    return _database_service


async def close_database_service() -> None:
    """Close and clear the singleton DatabaseService instance."""
    global _database_service
    if _database_service:
        await _database_service.close()
        _database_service = None
