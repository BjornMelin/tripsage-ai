# pylint: disable=too-many-lines,too-many-instance-attributes,too-many-public-methods,no-name-in-module,too-many-statements
"""Supabase-only Database Service (FINAL-ONLY).

This module provides a single modern DatabaseService that uses the Supabase
Python client exclusively. All legacy SQLAlchemy engine and raw engine paths
have been removed to keep the implementation simple, maintainable, and safe.

Key features:
- Typed configuration via Pydantic (pool/monitoring/security/performance knobs)
- Supabase CRUD (select/insert/update/upsert/delete/count)
- Vector search using pgvector via PostgREST expression ordering
- RPC function invocation and raw SQL via a safe RPC wrapper (execute_sql)
- Lightweight monitoring (OTEL metrics) and basic rate limiting/circuit breaker
- Convenience helpers used by business services and wrappers
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from enum import Enum
from types import TracebackType
from typing import Any, Protocol, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from supabase import Client, create_client
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.observability.otel import get_meter, get_tracer
from tripsage_core.types import (
    FilterMapping,
    JSONObject,
    JSONObjectMapping,
    JSONObjectSequence,
    JSONValue,
)


logger = logging.getLogger(__name__)

DataT = TypeVar("DataT")


SupabasePayload = Mapping[str, object] | Sequence[Mapping[str, object]]


def _to_supabase_payload(
    data: JSONObject | JSONObjectSequence,
) -> SupabasePayload:
    """Convert internal JSON structures to supabase-compatible payloads."""

    def _convert(value: JSONValue) -> object:
        if isinstance(value, Mapping):
            mapping = cast(JSONObjectMapping, value)
            return {str(k): _convert(v) for k, v in mapping.items()}
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            seq = cast(Sequence[JSONValue], value)
            return [_convert(item) for item in seq]
        return value

    if isinstance(data, Sequence) and not isinstance(data, Mapping):
        payload_list: list[Mapping[str, object]] = []
        for item in data:
            mapping = cast(JSONObjectMapping, item)
            payload_list.append({str(k): _convert(v) for k, v in mapping.items()})
        return payload_list
    mapping = cast(JSONObjectMapping, data)
    return {str(k): _convert(v) for k, v in mapping.items()}


class SupabaseResponse(Protocol[DataT]):
    """Protocol representing the subset of Supabase responses we use."""

    data: DataT


class SupabaseCountResponse(Protocol):
    """Protocol for Supabase responses that expose a count attribute."""

    count: int | None


# -------------------
# OTEL metric helpers
# -------------------


class _MetricsCounter(Protocol):
    """Minimal counter protocol for OTEL metric stubs."""

    def add(self, amount: int, attributes: Mapping[str, str] | None = None) -> None:
        """Record a counter increment."""


class _MetricsHistogram(Protocol):
    """Minimal histogram protocol for OTEL metric stubs."""

    def record(
        self, amount: float, attributes: Mapping[str, str] | None = None
    ) -> None:
        """Record a histogram measurement."""


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
        enable_metrics: Enable OTEL metrics counters/histograms.
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
    def _v_burst(cls, v: int, info: ValidationInfo) -> int:
        """Validate the rate limit burst."""
        req = int(info.data.get("rate_limit_requests", 0))
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
    details: JSONObject
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None


# FINAL-ONLY: no legacy metric handle containers remain.


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
        # OTEL meters are set up in _initialize_metrics(); no legacy handles remain.
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
        self._h_query_duration: _MetricsHistogram | None = None
        self._c_query_total: _MetricsCounter | None = None
        self._c_slow_total: _MetricsCounter | None = None

        # Initialize OTEL meters when metrics are enabled
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
            try:
                if self._c_query_total is not None:
                    # Reuse query counter to record a synthetic 'connect' event
                    self._c_query_total.add(
                        1,
                        {
                            "operation": "CONNECT",
                            "table": "_",
                            "status": "success",
                        },
                    )
            except Exception:  # noqa: BLE001
                logger.debug("OTEL DB connect metric record failed", exc_info=True)
            self._connection_stats.uptime_seconds = 0
            self._connection_stats.connection_errors = 0
            logger.info("Database service connected in %.2fs.", time.time() - start)
        except Exception as e:
            self._connected = False
            try:
                if self._c_query_total is not None:
                    self._c_query_total.add(
                        1,
                        {
                            "operation": "CONNECT",
                            "table": "_",
                            "status": "error",
                        },
                    )
            except Exception:  # noqa: BLE001
                logger.debug("OTEL DB connect metric record failed", exc_info=True)
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
        # No explicit health gauge; rely on OTEL spans/metrics
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
        """Initialize OTEL metrics instruments for DB observability."""
        try:
            meter = get_meter(__name__)
            # Create instruments analogous to prior metrics set
            self._h_query_duration = meter.create_histogram(
                "db.query.duration", unit="s", description="DB query execution time"
            )
            self._c_query_total = meter.create_counter(
                "db.query.total", description="Total DB queries"
            )
            self._c_slow_total = meter.create_counter(
                "db.query.slow_total", description="Total slow DB queries"
            )
        except Exception:  # noqa: BLE001 - meter init is best-effort
            self._h_query_duration = None
            self._c_query_total = None
            self._c_slow_total = None
            logger.debug("OTEL meter init failed", exc_info=True)

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
        _span: object | None = None
        try:
            with span_ctx as span:  # type: ignore[assignment]
                _span = span
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
            try:
                attrs = {
                    "operation": query_type.value,
                    "table": (table or "unknown"),
                    "status": "success",
                }
                if self._h_query_duration is not None:
                    self._h_query_duration.record(duration, attrs)
                if self._c_query_total is not None:
                    self._c_query_total.add(1, attrs)
                if (
                    self._c_slow_total is not None
                    and duration > self.slow_query_threshold
                ):
                    self._c_slow_total.add(
                        1, {k: v for k, v in attrs.items() if k != "status"}
                    )
            except Exception:  # noqa: BLE001 - metrics must not affect queries
                logger.debug("OTEL DB metrics record failed", exc_info=True)
            self._connection_stats.queries_executed += 1
            self._record_circuit_breaker_success()
        except Exception:
            duration = time.time() - start_time
            with contextlib.suppress(Exception):  # pragma: no cover
                if _span is not None:
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
            try:
                attrs = {
                    "operation": query_type.value,
                    "table": (table or "unknown"),
                    "status": "error",
                }
                if self._h_query_duration is not None:
                    self._h_query_duration.record(duration, attrs)
                if self._c_query_total is not None:
                    self._c_query_total.add(1, attrs)
            except Exception:  # noqa: BLE001 - metrics must not affect queries
                logger.debug("OTEL DB metrics record failed", exc_info=True)
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
                try:
                    if self._c_query_total is not None:
                        self._c_query_total.add(
                            1,
                            {
                                "operation": "RATE_LIMIT",
                                "table": "_",
                                "status": "hit",
                                "user_id": user_id,
                            },
                        )
                except Exception:  # noqa: BLE001
                    logger.debug("OTEL rate-limit metric record failed", exc_info=True)
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
        data: JSONObject | JSONObjectSequence,
        user_id: str | None = None,
    ) -> list[JSONObject]:
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
                payload = _to_supabase_payload(data)
                # Cast payload to satisfy Supabase client's JSON type hints.
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(
                        lambda: self.client.table(table)
                        .insert(cast(Any, payload))
                        .execute()
                    ),
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
        filters: FilterMapping | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        user_id: str | None = None,
    ) -> list[JSONObject]:
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
                query: Any = self.client.table(table).select(columns)
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, Mapping):
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
                exec_callable = cast(Callable[[], object], query.execute)
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(exec_callable),
                )
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
        data: JSONObject,
        filters: JSONObjectMapping,
        user_id: str | None = None,
    ) -> list[JSONObject]:
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
                payload = _to_supabase_payload(data)
                query: Any = self.client.table(table).update(cast(Any, payload))
                for k, v in filters.items():
                    query = query.eq(k, v)
                exec_callable = cast(Callable[[], object], query.execute)
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(exec_callable),
                )
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
        data: JSONObject | JSONObjectSequence,
        on_conflict: str | None = None,
        user_id: str | None = None,
    ) -> list[JSONObject]:
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
                payload = _to_supabase_payload(data)
                query: Any = self.client.table(table).upsert(cast(Any, payload))
                if on_conflict and hasattr(query, "on_conflict"):
                    query = query.on_conflict(on_conflict)  # type: ignore[call-arg]  # pylint: disable=no-member
                exec_callable = cast(Callable[[], object], query.execute)
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(exec_callable),
                )
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
        self, table: str, filters: JSONObjectMapping, user_id: str | None = None
    ) -> list[JSONObject]:
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
                query: Any = self.client.table(table).delete()
                for k, v in filters.items():
                    query = query.eq(k, v)
                exec_callable = cast(Callable[[], object], query.execute)
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(exec_callable),
                )
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
        filters: FilterMapping | None = None,
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
                query: Any = self.client.table(table).select("*", count="exact")  # type: ignore[arg-type]
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, Mapping):
                            for op, operand in value.items():
                                query = getattr(query, op)(key, operand)
                        else:
                            query = query.eq(key, value)
                exec_callable = cast(Callable[[], object], query.execute)
                result = cast(
                    SupabaseCountResponse,
                    await asyncio.to_thread(exec_callable),
                )
                return int(result.count or 0)
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
        filters: JSONObject | None = None,
        user_id: str | None = None,
    ) -> list[JSONObject]:
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
                query: Any = self.client.table(table).select(
                    f"*, {vector_column} <-> '{vec}' as distance"
                )
                if filters:
                    for k, v in filters.items():
                        query = query.eq(k, v)
                if similarity_threshold is not None:
                    dist_thr = 1 - similarity_threshold
                    query = query.lt(f"{vector_column} <-> '{vec}'", dist_thr)
                query = query.order(f"{vector_column} <-> '{vec}'").limit(limit)
                exec_callable = cast(Callable[[], object], query.execute)
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(exec_callable),
                )
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
        self,
        sql: str,
        *params: JSONValue | JSONObjectMapping,
        user_id: str | None = None,
    ) -> list[JSONObject]:
        """Execute raw SQL through a trusted RPC wrapper.

        Args:
            sql: SQL text to execute. Use parameter placeholders handled by the RPC.
            *params: Parameter values. Can be a single dict or positional args.
            user_id: Optional user attribution.

        Returns:
            Result rows as a list of dictionaries.

        Raises:
            CoreDatabaseError: If the SQL execution fails.
        """
        # Handle params
        if len(params) == 1 and isinstance(params[0], Mapping):
            params_dict: JSONObject = {
                str(key): cast(JSONValue, value) for key, value in params[0].items()
            }
        else:
            params_dict = {
                str(i + 1): cast(JSONValue, param) for i, param in enumerate(params)
            }

        await self.ensure_connected()
        if self.enable_security:
            self._check_sql_injection(sql)
        async with self._monitor_query(QueryType.RAW_SQL, None, user_id):
            try:
                rpc_call = self.client.rpc(
                    "execute_sql", {"sql": sql, "params": params_dict}
                )
                exec_callable = cast(Callable[[], object], rpc_call.execute)
                result = cast(
                    SupabaseResponse[list[JSONObject]],
                    await asyncio.to_thread(exec_callable),
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
        params: JSONObject | None = None,
        user_id: str | None = None,
    ) -> JSONValue:
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
                rpc_call = self.client.rpc(function_name, params or {})
                exec_callable = cast(Callable[[], object], rpc_call.execute)
                result = cast(
                    SupabaseResponse[JSONValue],
                    await asyncio.to_thread(exec_callable),
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
            self.ops: list[Callable[[], Awaitable[list[JSONObject]]]] = []

        async def __aenter__(self) -> DatabaseService._Batch:
            """Enter the batch context and ensure connectivity."""
            await self.svc.ensure_connected()
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
            """Exit the batch context without committing extra state."""
            return False

        def insert(self, table: str, data: JSONObject | JSONObjectSequence):
            """Insert a record into a table."""
            self.ops.append(lambda: self.svc.insert(table, data, self.user_id))

        def update(self, table: str, data: JSONObject, filters: JSONObject):
            """Update a record in a table."""
            self.ops.append(lambda: self.svc.update(table, data, filters, self.user_id))

        def delete(self, table: str, filters: JSONObject):
            """Delete a record from a table."""
            self.ops.append(lambda: self.svc.delete(table, filters, self.user_id))

        async def execute(self) -> list[list[JSONObject]]:
            """Execute all recorded operations in order.

            Returns:
                List with each operation's result payload.
            """
            return [await operation() for operation in self.ops]

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
        self, trip_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
        """Create a new trip record."""
        result = await self.insert("trips", trip_data, user_id)
        return result[0] if result else {}

    async def get_trip_by_id(
        self, trip_id: str, user_id: str | None = None
    ) -> JSONObject | None:
        """Get trip by ID."""
        result = await self.select(
            "trips", "*", filters={"id": trip_id}, user_id=user_id
        )
        return result[0] if result else None

    async def get_user_trips(self, user_id: str) -> list[JSONObject]:
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
    ) -> JSONObject | None:
        """Get trip by ID."""
        result = await self.get_trip_by_id(trip_id, user_id)
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result

    async def update_trip(
        self, trip_id: str, trip_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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

    async def create_user(self, user_data: JSONObject) -> JSONObject:
        """Create a new user record."""
        result = await self.insert("users", user_data)
        return result[0] if result else {}

    async def get_user(self, user_id: str) -> JSONObject | None:
        """Get user by ID."""
        result = await self.select("users", "*", filters={"id": user_id})
        return result[0] if result else None

    async def get_user_by_email(self, email: str) -> JSONObject | None:
        """Get user by email."""
        result = await self.select("users", "*", filters={"email": email})
        return result[0] if result else None

    async def update_user(self, user_id: str, user_data: JSONObject) -> JSONObject:
        """Update user record."""
        result = await self.update("users", user_data, {"id": user_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"User {user_id} not found",
                details={"resource_id": user_id, "resource_type": "user"},
            )
        return result[0]

    async def save_flight_search(
        self, search_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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
        self, search_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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
        self, option_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
        """Persist a flight option candidate.

        Args:
            option_data: Flight option payload.
            user_id: Optional user attribution.

        Returns:
            The created record.
        """
        result = await self.insert("flight_options", option_data, user_id)
        return result[0] if result else {}

    async def get_user_flight_searches(self, user_id: str) -> list[JSONObject]:
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
        self, option_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
        """Persist an accommodation option candidate.

        Args:
            option_data: Option payload to store.
            user_id: Optional user attribution.

        Returns:
            The created record.
        """
        result = await self.insert("accommodation_options", option_data, user_id)
        return result[0] if result else {}

    async def get_user_accommodation_searches(self, user_id: str) -> list[JSONObject]:
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
        self, session_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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
        self, message_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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
        self, message_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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
    ) -> list[JSONObject]:
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
    ) -> list[JSONObject]:
        """List chat sessions for a user.

        Args:
            user_id: User identifier.
            limit: Maximum number of sessions.
            include_ended: Include sessions with ``ended_at`` set.

        Returns:
            List of session rows.
        """
        filters: JSONObject = {"user_id": user_id}
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
    ) -> JSONObject | None:
        """Fetch a chat session by id for a user."""
        rows = await self.select(
            "chat_sessions",
            "*",
            filters={"id": session_id, "user_id": user_id},
            limit=1,
            user_id=user_id,
        )
        return rows[0] if rows else None

    async def get_session_stats(self, session_id: str) -> JSONObject:
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
    ) -> list[JSONObject]:
        """List messages for a chat session ordered by creation time."""
        return await self.select(
            "chat_messages",
            "*",
            filters={"session_id": session_id},
            order_by="created_at",
            limit=limit or 100,
            offset=offset,
        )

    async def get_message_tool_calls(self, message_id: str) -> list[JSONObject]:
        """List tool calls attached to a message."""
        return await self.select(
            "chat_tool_calls", "*", filters={"message_id": message_id}
        )

    async def create_tool_call(self, tool_call_data: JSONObject) -> JSONObject:
        """Create a tool call row."""
        result = await self.insert("chat_tool_calls", tool_call_data)
        return result[0] if result else {}

    async def update_tool_call(
        self, tool_call_id: str, update_data: JSONObject
    ) -> JSONObject | None:
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

    async def get_user_api_keys(self, user_id: str) -> list[JSONObject]:
        """List API keys for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of API key rows.
        """
        return await self.select(
            "api_keys", "*", filters={"user_id": user_id}, user_id=user_id
        )

    async def get_api_key(self, user_id: str, service_name: str) -> JSONObject | None:
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
        self, key_data: JSONObject, user_id: str | None = None
    ) -> JSONObject:
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

    async def create_api_key(self, key_data: JSONObject) -> JSONObject:
        """Create a new API key row.

        Args:
            key_data: API key payload.

        Returns:
            Created API key row.
        """
        user_id = cast(str | None, key_data.get("user_id"))
        result = await self.insert("api_keys", key_data, user_id)
        return result[0] if result else {}

    async def get_api_key_by_id(self, key_id: str, user_id: str) -> JSONObject | None:
        """Fetch an API key by ID for a user.

        Args:
            key_id: Key identifier.
            user_id: User identifier.

        Returns:
            API key row or None.
        """
        result = await self.select(
            "api_keys",
            "*",
            filters={"id": key_id, "user_id": user_id},
            user_id=user_id,
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

    async def update_api_key(self, key_id: str, update_data: JSONObject) -> JSONObject:
        """Update arbitrary fields for a key.

        Args:
            key_id: Key identifier.
            update_data: Fields to update.

        Returns:
            Updated API key row or empty dict.
        """
        result = await self.update("api_keys", update_data, {"id": key_id})
        return result[0] if result else {}

    async def log_api_key_usage(self, usage_data: JSONObject) -> JSONObject:
        """Append an API key usage event.

        Args:
            usage_data: Usage payload to persist.

        Returns:
            Created usage row.
        """
        user_id = cast(str | None, usage_data.get("user_id"))
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
    ) -> list[JSONObject]:
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
        destination_data: JSONObject,
        embedding: list[float],
        user_id: str | None = None,
    ) -> JSONObject:
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

    async def get_trip_collaborators(self, trip_id: str) -> list[JSONObject]:
        """List collaborators for a trip.

        Args:
            trip_id: Trip identifier.

        Returns:
            List of collaborator rows.
        """
        return await self.select(
            "trip_collaborators", "*", filters={"trip_id": trip_id}
        )

    async def add_trip_collaborator(self, collaborator_data: JSONObject) -> JSONObject:
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
        user_id = cast(str | None, collaborator_data.get("added_by"))
        result = await self.upsert(
            "trip_collaborators",
            collaborator_data,
            on_conflict="trip_id,user_id",
            user_id=user_id,
        )
        return result[0] if result else {}

    async def get_trip_collaborator(
        self, trip_id: str, user_id: str
    ) -> JSONObject | None:
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
        search_filters: JSONObject,
        limit: int = 50,
        offset: int = 0,
        user_id: str | None = None,
    ) -> list[JSONObject]:
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
            user_filter = search_filters.get("user_id")
            if user_filter is not None:
                q = q.eq("user_id", user_filter)
            status_filter = search_filters.get("status")
            if status_filter is not None:
                q = q.eq("status", status_filter)
            visibility_filter = search_filters.get("visibility")
            if visibility_filter is not None:
                q = q.eq("visibility", visibility_filter)
            query_text = search_filters.get("query")
            if isinstance(query_text, str) and query_text:
                q = q.or_(f"name.ilike.%{query_text}%,destination.ilike.%{query_text}%")
            destinations = search_filters.get("destinations")
            if isinstance(destinations, Sequence) and not isinstance(
                destinations, (str, bytes, bytearray)
            ):
                ors = ",".join(
                    [f"destination.ilike.%{dest!s}%" for dest in destinations]
                )
                if ors:
                    q = q.or_(ors)
            tags = search_filters.get("tags")
            if isinstance(tags, Sequence) and not isinstance(
                tags, (str, bytes, bytearray)
            ):
                q = q.overlaps("notes", list(tags))  # type: ignore[call-arg]
            date_range = search_filters.get("date_range")
            if isinstance(date_range, Mapping):
                start_value = date_range.get("start_date")
                if isinstance(start_value, datetime):
                    q = q.gte("start_date", start_value.isoformat())
                elif isinstance(start_value, str):
                    q = q.gte("start_date", start_value)
                end_value = date_range.get("end_date")
                if isinstance(end_value, datetime):
                    q = q.lte("end_date", end_value.isoformat())
                elif isinstance(end_value, str):
                    q = q.lte("end_date", end_value)
            q = q.order("created_at").limit(limit).offset(offset)
        result = cast(
            SupabaseResponse[list[JSONObject]],
            await asyncio.to_thread(q.execute),
        )
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
    ) -> list[JSONObject]:
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

    async def get_user_stats(self, user_id: str) -> JSONObject:
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
            # Health tracked via spans/metrics elsewhere
            return True
        except Exception:
            logger.exception("Database health check failed")
            # Health tracked via spans/metrics elsewhere
            return False

    async def get_table_info(
        self, table: str, user_id: str | None = None
    ) -> JSONObject:
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

    async def get_database_stats(self) -> JSONObject:
        """Return service statistics and recent security/metrics summaries.

        Returns:
            Mapping of connection/query/security summaries.
        """
        stats: JSONObject = {
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
                try:
                    if self._c_query_total is not None:
                        self._c_query_total.add(
                            1,
                            {
                                "operation": "SECURITY",
                                "table": "_",
                                "status": "sql_injection_attempt",
                            },
                        )
                except Exception:  # noqa: BLE001
                    logger.debug("OTEL security metric record failed", exc_info=True)
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
    global _database_service  # pylint: disable=global-statement
    if _database_service is None:
        _database_service = DatabaseService()
        await _database_service.connect()
    return _database_service


async def close_database_service() -> None:
    """Close and clear the singleton DatabaseService instance."""
    global _database_service  # pylint: disable=global-statement
    if _database_service:
        await _database_service.close()
        _database_service = None
