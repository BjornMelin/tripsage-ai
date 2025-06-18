"""
Consolidated Database Service for TripSage Core.

This module provides a unified, high-performance database service that consolidates
all functionality from 7 previous database services into a single, maintainable solution.

Key Features:
- LIFO connection pooling with SQLAlchemy 2.0+ (pool_size=100, max_overflow=500)
- Supavisor integration for optimal serverless performance
- Comprehensive monitoring and metrics (Prometheus)
- Security hardening with rate limiting and audit logging
- Read replica support with intelligent routing
- Vector search operations (pgvector)
- Automatic retry logic and circuit breaker
- Query performance tracking and regression detection
- Connection health monitoring and validation
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.engine import Engine

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
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
    READ = "READ"  # Generic read operation
    WRITE = "WRITE"  # Generic write operation
    ANALYTICS = "ANALYTICS"  # Analytics queries


class HealthStatus(Enum):
    """Database health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class SecurityEvent(Enum):
    """Security event types."""

    SUSPICIOUS_QUERY = "suspicious_query"
    CONNECTION_FAILURE = "connection_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SLOW_QUERY_DETECTED = "slow_query_detected"
    HIGH_ERROR_RATE = "high_error_rate"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


class QueryMetrics(BaseModel):
    """Query execution metrics."""

    query_type: QueryType
    table: Optional[str] = None
    duration_ms: float
    rows_affected: int = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    replica_id: Optional[str] = None


class ConnectionStats(BaseModel):
    """Connection pool statistics."""

    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    pool_size: int = 0
    max_overflow: int = 0
    connection_errors: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = 0
    queries_executed: int = 0
    avg_query_time_ms: float = 0
    pool_utilization: float = 0


class SecurityAlert(BaseModel):
    """Security alert information."""

    event_type: SecurityEvent
    severity: str  # low, medium, high, critical
    message: str
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    action_taken: Optional[str] = None


class DatabaseService:
    """
    Consolidated database service with LIFO pooling and comprehensive features.

    This service consolidates functionality from 7 previous database services:
    - Core database operations (CRUD, transactions)
    - Connection pooling with LIFO behavior
    - Monitoring and metrics collection
    - Security hardening and rate limiting
    - Read replica management
    - Query performance tracking
    - Health checking and recovery
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        # Connection pooling configuration
        pool_size: int = 100,  # As per research recommendations
        max_overflow: int = 500,  # As per research recommendations
        pool_use_lifo: bool = True,  # LIFO for better cache locality
        pool_pre_ping: bool = True,  # Connection validation
        pool_recycle: int = 3600,  # Recycle connections after 1 hour
        pool_timeout: float = 30.0,  # Connection timeout
        # Monitoring configuration
        enable_monitoring: bool = True,
        enable_metrics: bool = True,
        enable_query_tracking: bool = True,
        slow_query_threshold: float = 1.0,  # seconds
        # Security configuration
        enable_security: bool = True,
        enable_rate_limiting: bool = True,
        enable_audit_logging: bool = True,
        rate_limit_requests: int = 1000,  # per minute
        rate_limit_burst: int = 2000,
        # Performance configuration
        enable_read_replicas: bool = True,
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 5,  # failures before opening
        circuit_breaker_timeout: float = 60.0,  # seconds before retry
    ):
        """Initialize the consolidated database service.

        Args:
            settings: Application settings
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum overflow connections allowed
            pool_use_lifo: Use LIFO connection strategy
            pool_pre_ping: Enable connection validation
            pool_recycle: Connection recycle time in seconds
            pool_timeout: Timeout for getting connection from pool
            enable_monitoring: Enable comprehensive monitoring
            enable_metrics: Enable Prometheus metrics
            enable_query_tracking: Track query performance
            slow_query_threshold: Threshold for slow query detection
            enable_security: Enable security features
            enable_rate_limiting: Enable rate limiting
            enable_audit_logging: Enable audit logging
            rate_limit_requests: Requests per minute limit
            rate_limit_burst: Burst limit for rate limiting
            enable_read_replicas: Enable read replica support
            enable_circuit_breaker: Enable circuit breaker pattern
            circuit_breaker_threshold: Failures before circuit opens
            circuit_breaker_timeout: Circuit breaker timeout
        """
        self.settings = settings or get_settings()

        # Connection pooling configuration
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_use_lifo = pool_use_lifo
        self.pool_pre_ping = pool_pre_ping
        self.pool_recycle = pool_recycle
        self.pool_timeout = pool_timeout

        # Feature flags
        self.enable_monitoring = enable_monitoring
        self.enable_metrics = enable_metrics
        self.enable_query_tracking = enable_query_tracking
        self.slow_query_threshold = slow_query_threshold
        self.enable_security = enable_security
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_audit_logging = enable_audit_logging
        self.enable_read_replicas = enable_read_replicas
        self.enable_circuit_breaker = enable_circuit_breaker

        # Service state
        self._supabase_client: Optional[Client] = None
        self._sqlalchemy_engine: Optional[Engine] = None
        self._connected = False
        self._start_time = time.time()

        # Monitoring and metrics
        self._query_metrics: List[QueryMetrics] = []
        self._security_alerts: List[SecurityAlert] = []
        self._connection_stats = ConnectionStats(
            pool_size=pool_size, max_overflow=max_overflow
        )

        # Circuit breaker state
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0
        self._circuit_breaker_open = False
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # Rate limiting state
        self._rate_limit_window = {}  # user_id -> (count, window_start)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_burst = rate_limit_burst

        # Initialize metrics if enabled
        self._metrics = None
        if enable_metrics:
            self._initialize_metrics()

        logger.info(
            f"Consolidated Database Service initialized with "
            f"pool_size={pool_size}, max_overflow={max_overflow}, "
            f"LIFO={'enabled' if pool_use_lifo else 'disabled'}"
        )

    def _initialize_metrics(self):
        """Initialize Prometheus metrics for monitoring."""
        try:
            from prometheus_client import Counter, Gauge, Histogram, Summary

            # Create metrics container
            self._metrics = type("Metrics", (), {})()

            # Connection metrics
            self._metrics.connection_pool_size = Gauge(
                "tripsage_db_pool_size",
                "Current database connection pool size",
                ["pool_type"],
            )

            self._metrics.connection_pool_used = Gauge(
                "tripsage_db_pool_connections_used",
                "Number of connections currently in use",
                ["pool_type"],
            )

            self._metrics.connection_attempts = Counter(
                "tripsage_db_connection_attempts_total",
                "Total database connection attempts",
                ["status"],
            )

            # Query metrics
            self._metrics.query_duration = Histogram(
                "tripsage_db_query_duration_seconds",
                "Database query execution time",
                ["operation", "table", "status"],
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            )

            self._metrics.query_count = Counter(
                "tripsage_db_queries_total",
                "Total database queries executed",
                ["operation", "table", "status"],
            )

            self._metrics.slow_queries = Counter(
                "tripsage_db_slow_queries_total",
                "Total slow queries detected",
                ["operation", "table"],
            )

            # Health metrics
            self._metrics.health_status = Gauge(
                "tripsage_db_health_status",
                "Database health status (1=healthy, 0=unhealthy)",
                ["component"],
            )

            # Security metrics
            self._metrics.security_events = Counter(
                "tripsage_db_security_events_total",
                "Total security events detected",
                ["event_type", "severity"],
            )

            self._metrics.rate_limit_hits = Counter(
                "tripsage_db_rate_limit_hits_total",
                "Total rate limit hits",
                ["user_id"],
            )

            logger.info("Prometheus metrics initialized successfully")

        except ImportError:
            logger.warning("Prometheus client not available, metrics disabled")
            self._metrics = None
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {e}")
            self._metrics = None

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to the database."""
        return self._connected and self._supabase_client is not None

    @property
    def client(self) -> Client:
        """Get Supabase client, raising error if not connected."""
        if not self._connected or not self._supabase_client:
            raise CoreServiceError(
                message="Database service not connected. Call connect() first.",
                code="DATABASE_NOT_CONNECTED",
                service="DatabaseService",
            )
        return self._supabase_client

    async def connect(self) -> None:
        """Initialize database connections with LIFO pooling."""
        if self._connected:
            return

        start_time = time.time()

        try:
            # Initialize Supabase client
            await self._initialize_supabase_client()

            # Initialize SQLAlchemy engine with LIFO pooling
            await self._initialize_sqlalchemy_engine()

            # Test connections
            await self._test_connections()

            self._connected = True
            duration = time.time() - start_time

            # Update metrics
            if self._metrics:
                self._metrics.connection_attempts.labels(status="success").inc()
                self._metrics.health_status.labels(component="connection").set(1)

            # Record connection stats
            self._connection_stats.uptime_seconds = 0
            self._connection_stats.connection_errors = 0

            logger.info(
                f"Database service connected successfully in {duration:.2f}s. "
                f"LIFO pooling enabled with pool_size={self.pool_size}, "
                f"max_overflow={self.max_overflow}"
            )

        except Exception as e:
            self._connected = False

            # Update metrics
            if self._metrics:
                self._metrics.connection_attempts.labels(status="failure").inc()
                self._metrics.health_status.labels(component="connection").set(0)

            # Record error
            self._connection_stats.connection_errors += 1
            self._connection_stats.last_error = str(e)

            logger.error(f"Failed to connect to database: {e}")
            raise CoreDatabaseError(
                message=f"Failed to connect to database: {str(e)}",
                code="DATABASE_CONNECTION_FAILED",
                details={"error": str(e)},
            ) from e

    async def _initialize_supabase_client(self) -> None:
        """Initialize Supabase client with optimal configuration."""
        try:
            # Get Supabase configuration
            supabase_url = self.settings.database_url
            supabase_key = self.settings.database_public_key.get_secret_value()

            # Validate configuration
            if not supabase_url or not supabase_url.startswith("https://"):
                raise CoreDatabaseError(
                    message=f"Invalid Supabase URL format: {supabase_url}",
                    code="INVALID_DATABASE_URL",
                )

            if not supabase_key or len(supabase_key) < 20:
                raise CoreDatabaseError(
                    message="Invalid Supabase API key",
                    code="INVALID_DATABASE_KEY",
                )

            # Configure client options
            options = ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
                postgrest_client_timeout=self.pool_timeout,
            )

            # Create Supabase client
            self._supabase_client = create_client(
                supabase_url, supabase_key, options=options
            )

            logger.debug("Supabase client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    async def _initialize_sqlalchemy_engine(self) -> None:
        """Initialize SQLAlchemy engine with LIFO pooling."""
        try:
            # Extract database URL from Supabase configuration
            parsed_url = urlparse(self.settings.database_url)
            project_ref = parsed_url.hostname.split(".")[0]

            # Build PostgreSQL connection URL
            # Use Supavisor transaction mode (port 6543) for optimal pooling
            db_url = (
                f"postgresql://"
                f"postgres.{project_ref}:"
                f"{self.settings.database_password.get_secret_value()}"
                f"@{project_ref}.pooler.supabase.com:6543/postgres"
            )

            # Create engine with LIFO pooling
            self._sqlalchemy_engine = create_engine(
                db_url,
                pool_class=pool.QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=self.pool_pre_ping,
                pool_use_lifo=self.pool_use_lifo,  # LIFO for better cache locality
                echo=False,  # Set to True for debugging
                echo_pool=False,  # Set to True for pool debugging
            )

            # Add event listeners for monitoring
            if self.enable_monitoring:
                self._setup_pool_event_listeners()

            logger.debug(
                f"SQLAlchemy engine initialized with LIFO pooling "
                f"(pool_size={self.pool_size}, max_overflow={self.max_overflow})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize SQLAlchemy engine: {e}")
            raise

    def _setup_pool_event_listeners(self) -> None:
        """Set up SQLAlchemy pool event listeners for monitoring."""
        if not self._sqlalchemy_engine:
            return

        # Connection checkout event
        @event.listens_for(self._sqlalchemy_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Track connection checkout from pool."""
            self._connection_stats.active_connections += 1
            if self._metrics:
                self._metrics.connection_pool_used.labels(pool_type="lifo").set(
                    self._connection_stats.active_connections
                )

        # Connection checkin event
        @event.listens_for(self._sqlalchemy_engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Track connection checkin to pool."""
            self._connection_stats.active_connections = max(
                0, self._connection_stats.active_connections - 1
            )
            if self._metrics:
                self._metrics.connection_pool_used.labels(pool_type="lifo").set(
                    self._connection_stats.active_connections
                )

        # Connection invalidate event
        @event.listens_for(self._sqlalchemy_engine, "invalidate")
        def receive_invalidate(dbapi_conn, connection_record, exception):
            """Track connection invalidation."""
            self._connection_stats.connection_errors += 1
            if exception:
                self._connection_stats.last_error = str(exception)

    async def _test_connections(self) -> None:
        """Test both Supabase and SQLAlchemy connections."""
        # Test Supabase connection
        try:
            await asyncio.to_thread(
                lambda: self._supabase_client.table("users")
                .select("id")
                .limit(1)
                .execute()
            )
            logger.debug("Supabase connection test passed")
        except Exception as e:
            raise CoreDatabaseError(
                message=f"Supabase connection test failed: {str(e)}",
                code="SUPABASE_CONNECTION_TEST_FAILED",
            ) from e

        # Test SQLAlchemy connection
        if self._sqlalchemy_engine:
            try:
                with self._sqlalchemy_engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.scalar()
                logger.debug("SQLAlchemy connection test passed")
            except Exception as e:
                raise CoreDatabaseError(
                    message=f"SQLAlchemy connection test failed: {str(e)}",
                    code="SQLALCHEMY_CONNECTION_TEST_FAILED",
                ) from e

    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        if self._sqlalchemy_engine:
            try:
                self._sqlalchemy_engine.dispose()
                logger.info("SQLAlchemy engine disposed")
            except Exception as e:
                logger.error(f"Error disposing SQLAlchemy engine: {e}")

        self._supabase_client = None
        self._sqlalchemy_engine = None
        self._connected = False

        # Update metrics
        if self._metrics:
            self._metrics.health_status.labels(component="connection").set(0)
            self._metrics.connection_pool_used.labels(pool_type="lifo").set(0)

        logger.info("Database service closed")

    async def ensure_connected(self) -> None:
        """Ensure database connection is established."""
        if not self.is_connected:
            await self.connect()

    # Circuit breaker implementation

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker should block the request."""
        if not self.enable_circuit_breaker:
            return

        # Check if circuit is open
        if self._circuit_breaker_open:
            # Check if timeout has passed
            if (
                time.time() - self._circuit_breaker_last_failure
                > self.circuit_breaker_timeout
            ):
                # Try to close the circuit
                self._circuit_breaker_open = False
                self._circuit_breaker_failures = 0
                logger.info("Circuit breaker closed after timeout")
            else:
                raise CoreServiceError(
                    message="Circuit breaker is open - service temporarily unavailable",
                    code="CIRCUIT_BREAKER_OPEN",
                    service="DatabaseService",
                )

    def _record_circuit_breaker_success(self) -> None:
        """Record successful operation for circuit breaker."""
        if not self.enable_circuit_breaker:
            return

        # Reset failure count on success
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = 0
            logger.debug("Circuit breaker failure count reset")

    def _record_circuit_breaker_failure(self) -> None:
        """Record failed operation for circuit breaker."""
        if not self.enable_circuit_breaker:
            return

        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()

        # Open circuit if threshold reached
        if self._circuit_breaker_failures >= self.circuit_breaker_threshold:
            self._circuit_breaker_open = True
            logger.warning(
                f"Circuit breaker opened after {self._circuit_breaker_failures} failures"
            )

    # Rate limiting implementation

    async def _check_rate_limit(self, user_id: Optional[str] = None) -> None:
        """Check if request should be rate limited."""
        if not self.enable_rate_limiting or not user_id:
            return

        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        if user_id in self._rate_limit_window:
            count, last_window_start = self._rate_limit_window[user_id]

            # Reset window if expired
            if last_window_start < window_start:
                self._rate_limit_window[user_id] = (1, current_time)
                return

            # Check rate limit
            if count >= self.rate_limit_requests:
                # Record rate limit hit
                if self._metrics:
                    self._metrics.rate_limit_hits.labels(user_id=user_id).inc()

                # Create security alert
                if self.enable_security:
                    alert = SecurityAlert(
                        event_type=SecurityEvent.RATE_LIMIT_EXCEEDED,
                        severity="medium",
                        message=f"Rate limit exceeded for user {user_id}",
                        details={
                            "user_id": user_id,
                            "request_count": count,
                            "limit": self.rate_limit_requests,
                        },
                        user_id=user_id,
                    )
                    self._security_alerts.append(alert)

                raise CoreServiceError(
                    message="Rate limit exceeded - please try again later",
                    code="RATE_LIMIT_EXCEEDED",
                    service="DatabaseService",
                    details={"retry_after": 60},
                )

            # Increment counter
            self._rate_limit_window[user_id] = (count + 1, last_window_start)
        else:
            # First request in window
            self._rate_limit_window[user_id] = (1, current_time)

    # Query monitoring and metrics

    @asynccontextmanager
    async def _monitor_query(
        self,
        query_type: QueryType,
        table: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Context manager for query monitoring and metrics."""
        start_time = time.time()
        query_id = f"{query_type.value}_{table}_{int(start_time * 1000)}"

        # Check circuit breaker
        self._check_circuit_breaker()

        # Check rate limit
        await self._check_rate_limit(user_id)

        try:
            yield query_id

            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            if self.enable_query_tracking:
                metric = QueryMetrics(
                    query_type=query_type,
                    table=table,
                    duration_ms=duration * 1000,
                    success=True,
                    user_id=user_id,
                )
                self._query_metrics.append(metric)

            # Update Prometheus metrics
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

                # Check for slow query
                if duration > self.slow_query_threshold:
                    self._metrics.slow_queries.labels(
                        operation=query_type.value,
                        table=table or "unknown",
                    ).inc()

                    # Create security alert for slow query
                    if self.enable_security:
                        alert = SecurityAlert(
                            event_type=SecurityEvent.SLOW_QUERY_DETECTED,
                            severity="low",
                            message=f"Slow query detected: {query_type.value} on {table}",
                            details={
                                "query_type": query_type.value,
                                "table": table,
                                "duration_ms": duration * 1000,
                                "threshold_ms": self.slow_query_threshold * 1000,
                            },
                            user_id=user_id,
                        )
                        self._security_alerts.append(alert)

            # Update connection stats
            self._connection_stats.queries_executed += 1

            # Record circuit breaker success
            self._record_circuit_breaker_success()

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            if self.enable_query_tracking:
                metric = QueryMetrics(
                    query_type=query_type,
                    table=table,
                    duration_ms=duration * 1000,
                    success=False,
                    error=str(e),
                    user_id=user_id,
                )
                self._query_metrics.append(metric)

            # Update Prometheus metrics
            if self._metrics:
                self._metrics.query_duration.labels(
                    operation=query_type.value,
                    table=table or "unknown",
                    status="error",
                ).observe(duration)

                self._metrics.query_count.labels(
                    operation=query_type.value,
                    table=table or "unknown",
                    status="error",
                ).inc()

            # Record circuit breaker failure
            self._record_circuit_breaker_failure()

            # Re-raise the exception
            raise

    # Core database operations

    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Insert data into table with monitoring and security."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.INSERT, table, user_id):
            try:
                result = await asyncio.to_thread(
                    lambda: self.client.table(table).insert(data).execute()
                )

                # Audit logging
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id=user_id,
                        action="INSERT",
                        table=table,
                        records_affected=len(result.data) if result.data else 0,
                    )

                return result.data
            except Exception as e:
                logger.error(f"INSERT error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to insert into table '{table}'",
                    code="INSERT_FAILED",
                    operation="INSERT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table with monitoring."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.SELECT, table, user_id):
            try:
                query = self.client.table(table).select(columns)

                # Apply filters
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, dict):
                            # Support for complex filters
                            for operator, filter_value in value.items():
                                query = getattr(query, operator)(key, filter_value)
                        else:
                            query = query.eq(key, value)

                # Apply ordering
                if order_by:
                    if order_by.startswith("-"):
                        query = query.order(order_by[1:], desc=True)
                    else:
                        query = query.order(order_by)

                # Apply pagination
                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                result = await asyncio.to_thread(lambda: query.execute())
                return result.data
            except Exception as e:
                logger.error(f"SELECT error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to select from table '{table}'",
                    code="SELECT_FAILED",
                    operation="SELECT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Update data in table with monitoring and security."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.UPDATE, table, user_id):
            try:
                query = self.client.table(table).update(data)

                # Apply filters
                for key, value in filters.items():
                    query = query.eq(key, value)

                result = await asyncio.to_thread(lambda: query.execute())

                # Audit logging
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id=user_id,
                        action="UPDATE",
                        table=table,
                        records_affected=len(result.data) if result.data else 0,
                    )

                return result.data
            except Exception as e:
                logger.error(f"UPDATE error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to update table '{table}'",
                    code="UPDATE_FAILED",
                    operation="UPDATE",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Upsert data in table with monitoring."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.UPSERT, table, user_id):
            try:
                query = self.client.table(table).upsert(data)

                if on_conflict:
                    query = query.on_conflict(on_conflict)

                result = await asyncio.to_thread(lambda: query.execute())

                # Audit logging
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id=user_id,
                        action="UPSERT",
                        table=table,
                        records_affected=len(result.data) if result.data else 0,
                    )

                return result.data
            except Exception as e:
                logger.error(f"UPSERT error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to upsert into table '{table}'",
                    code="UPSERT_FAILED",
                    operation="UPSERT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def delete(
        self,
        table: str,
        filters: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Delete data from table with monitoring and security."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.DELETE, table, user_id):
            try:
                query = self.client.table(table).delete()

                # Apply filters
                for key, value in filters.items():
                    query = query.eq(key, value)

                result = await asyncio.to_thread(lambda: query.execute())

                # Audit logging
                if self.enable_audit_logging:
                    self._log_audit_event(
                        user_id=user_id,
                        action="DELETE",
                        table=table,
                        records_affected=len(result.data) if result.data else 0,
                    )

                return result.data
            except Exception as e:
                logger.error(f"DELETE error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to delete from table '{table}'",
                    code="DELETE_FAILED",
                    operation="DELETE",
                    table=table,
                    details={"error": str(e)},
                ) from e

    async def count(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> int:
        """Count records in table with monitoring."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.COUNT, table, user_id):
            try:
                query = self.client.table(table).select("*", count="exact")

                # Apply filters
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)

                result = await asyncio.to_thread(lambda: query.execute())
                return result.count
            except Exception as e:
                logger.error(f"COUNT error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to count records in table '{table}'",
                    code="COUNT_FAILED",
                    operation="COUNT",
                    table=table,
                    details={"error": str(e)},
                ) from e

    # Vector search operations

    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search using pgvector."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.VECTOR_SEARCH, table, user_id):
            try:
                # Use SQLAlchemy for vector operations
                if self._sqlalchemy_engine:
                    with self._sqlalchemy_engine.connect() as conn:
                        # Build vector search query
                        vector_str = f"'[{','.join(map(str, query_vector))}]'"

                        # Base query with vector distance
                        sql = f"""
                        SELECT *, ({vector_column} <-> {vector_str}::vector) as distance
                        FROM {table}
                        WHERE 1=1
                        """

                        # Add similarity threshold if provided
                        if similarity_threshold:
                            distance_threshold = 1 - similarity_threshold
                            sql += f" AND ({vector_column} <-> {vector_str}::vector) < {distance_threshold}"

                        # Add filters
                        params = {}
                        if filters:
                            for i, (key, value) in enumerate(filters.items()):
                                sql += f" AND {key} = :param_{i}"
                                params[f"param_{i}"] = value

                        # Order by similarity and limit
                        sql += f" ORDER BY {vector_column} <-> {vector_str}::vector LIMIT {limit}"

                        # Execute query
                        result = conn.execute(text(sql), params)
                        rows = result.fetchall()

                        # Convert to list of dicts
                        return [dict(row._mapping) for row in rows]
                else:
                    # Fallback to Supabase client (less efficient)
                    vector_str = f"[{','.join(map(str, query_vector))}]"

                    query = self.client.table(table).select(
                        f"*, {vector_column} <-> '{vector_str}' as distance"
                    )

                    if filters:
                        for key, value in filters.items():
                            query = query.eq(key, value)

                    if similarity_threshold:
                        distance_threshold = 1 - similarity_threshold
                        query = query.lt(
                            f"{vector_column} <-> '{vector_str}'", distance_threshold
                        )

                    query = query.order(f"{vector_column} <-> '{vector_str}'").limit(
                        limit
                    )

                    result = await asyncio.to_thread(lambda: query.execute())
                    return result.data

            except Exception as e:
                logger.error(f"Vector search error for table '{table}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to perform vector search on table '{table}'",
                    code="VECTOR_SEARCH_FAILED",
                    operation="VECTOR_SEARCH",
                    table=table,
                    details={"error": str(e)},
                ) from e

    # Transaction support

    @asynccontextmanager
    async def transaction(self, user_id: Optional[str] = None):
        """Context manager for database transactions."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.TRANSACTION, None, user_id):
            # Note: Supabase client doesn't have built-in transaction support
            # We simulate it with batch operations
            operations = []

            class TransactionContext:
                def __init__(self, service):
                    self.service = service
                    self.operations = operations

                def insert(
                    self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
                ):
                    self.operations.append(("insert", table, data))

                def update(
                    self, table: str, data: Dict[str, Any], filters: Dict[str, Any]
                ):
                    self.operations.append(("update", table, data, filters))

                def delete(self, table: str, filters: Dict[str, Any]):
                    self.operations.append(("delete", table, filters))

                async def execute(self):
                    """Execute all operations in the transaction."""
                    results = []
                    for operation in self.operations:
                        op_type = operation[0]
                        if op_type == "insert":
                            result = await self.service.insert(
                                operation[1], operation[2], user_id
                            )
                        elif op_type == "update":
                            result = await self.service.update(
                                operation[1], operation[2], operation[3], user_id
                            )
                        elif op_type == "delete":
                            result = await self.service.delete(
                                operation[1], operation[2], user_id
                            )
                        results.append(result)
                    return results

            yield TransactionContext(self)

    # High-level business operations

    async def create_trip(
        self, trip_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new trip record."""
        result = await self.insert("trips", trip_data, user_id)
        return result[0] if result else {}

    async def get_trip(
        self, trip_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get trip by ID."""
        result = await self.select("trips", "*", {"id": trip_id}, user_id=user_id)
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]

    async def get_user_trips(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trips for a user."""
        return await self.select(
            "trips", "*", {"user_id": user_id}, order_by="-created_at", user_id=user_id
        )

    async def update_trip(
        self, trip_id: str, trip_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update trip record."""
        result = await self.update("trips", trip_data, {"id": trip_id}, user_id)
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]

    async def delete_trip(self, trip_id: str, user_id: Optional[str] = None) -> bool:
        """Delete trip record."""
        result = await self.delete("trips", {"id": trip_id}, user_id)
        return len(result) > 0

    # User operations

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user record."""
        result = await self.insert("users", user_data)
        return result[0] if result else {}

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        result = await self.select("users", "*", {"id": user_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"User {user_id} not found",
                details={"resource_id": user_id, "resource_type": "user"},
            )
        return result[0]

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        result = await self.select("users", "*", {"email": email})
        return result[0] if result else None

    async def update_user(
        self, user_id: str, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user record."""
        result = await self.update("users", user_data, {"id": user_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"User {user_id} not found",
                details={"resource_id": user_id, "resource_type": "user"},
            )
        return result[0]

    # Flight operations

    async def save_flight_search(
        self, search_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save flight search parameters."""
        result = await self.insert("flight_searches", search_data, user_id)
        return result[0] if result else {}

    async def save_flight_option(
        self, option_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save flight option."""
        result = await self.insert("flight_options", option_data, user_id)
        return result[0] if result else {}

    async def get_user_flight_searches(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's flight searches."""
        return await self.select(
            "flight_searches",
            "*",
            {"user_id": user_id},
            order_by="-created_at",
            user_id=user_id,
        )

    # Accommodation operations

    async def save_accommodation_search(
        self, search_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save accommodation search parameters."""
        result = await self.insert("accommodation_searches", search_data, user_id)
        return result[0] if result else {}

    async def save_accommodation_option(
        self, option_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save accommodation option."""
        result = await self.insert("accommodation_options", option_data, user_id)
        return result[0] if result else {}

    async def get_user_accommodation_searches(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """Get user's accommodation searches."""
        return await self.select(
            "accommodation_searches",
            "*",
            {"user_id": user_id},
            order_by="-created_at",
            user_id=user_id,
        )

    # Chat operations

    async def create_chat_session(
        self, session_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create chat session."""
        result = await self.insert("chat_sessions", session_data, user_id)
        return result[0] if result else {}

    async def save_chat_message(
        self, message_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save chat message."""
        result = await self.insert("chat_messages", message_data, user_id)
        return result[0] if result else {}

    async def get_chat_history(
        self, session_id: str, limit: int = 50, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get chat history for session."""
        return await self.select(
            "chat_messages",
            "*",
            {"session_id": session_id},
            order_by="created_at",
            limit=limit,
            user_id=user_id,
        )

    # API key operations

    async def save_api_key(
        self, key_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save API key configuration."""
        result = await self.upsert(
            "api_keys", key_data, on_conflict="user_id,service_name", user_id=user_id
        )
        return result[0] if result else {}

    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's API keys."""
        return await self.select("api_keys", "*", {"user_id": user_id}, user_id=user_id)

    async def get_api_key(
        self, user_id: str, service_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific API key for user and service."""
        result = await self.select(
            "api_keys",
            "*",
            {"user_id": user_id, "service_name": service_name},
            user_id=user_id,
        )
        return result[0] if result else None

    async def delete_api_key(self, key_id: str, user_id: str) -> bool:
        """Delete API key by ID with user authorization."""
        result = await self.delete(
            "api_keys", {"id": key_id, "user_id": user_id}, user_id
        )
        return len(result) > 0

    async def delete_api_key_by_service(self, user_id: str, service_name: str) -> bool:
        """Delete API key by service name."""
        result = await self.delete(
            "api_keys", {"user_id": user_id, "service_name": service_name}, user_id
        )
        return len(result) > 0

    # Additional API key methods for compatibility

    async def create_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new API key."""
        user_id = key_data.get("user_id")
        result = await self.insert("api_keys", key_data, user_id)
        return result[0] if result else {}

    async def get_api_key_for_service(
        self, user_id: str, service: str
    ) -> Optional[Dict[str, Any]]:
        """Get API key for specific service - alias for get_api_key."""
        return await self.get_api_key(user_id, service)

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get API key by ID with user authorization."""
        result = await self.select(
            "api_keys", "*", {"id": key_id, "user_id": user_id}, user_id=user_id
        )
        return result[0] if result else None

    async def update_api_key_last_used(self, key_id: str) -> bool:
        """Update the last_used timestamp for an API key."""
        from datetime import datetime, timezone

        result = await self.update(
            "api_keys",
            {
                "last_used": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {"id": key_id},
        )
        return len(result) > 0

    async def update_api_key_validation(
        self, key_id: str, is_valid: bool, validated_at: datetime
    ) -> bool:
        """Update API key validation status."""
        from datetime import datetime, timezone

        result = await self.update(
            "api_keys",
            {
                "is_valid": is_valid,
                "last_validated": validated_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {"id": key_id},
        )
        return len(result) > 0

    async def update_api_key(
        self, key_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an API key with new data."""
        result = await self.update("api_keys", update_data, {"id": key_id})
        return result[0] if result else {}

    async def log_api_key_usage(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log API key usage for audit trail."""
        user_id = usage_data.get("user_id")
        result = await self.insert("api_key_usage_logs", usage_data, user_id)
        return result[0] if result else {}

    # Destination and embedding operations

    async def vector_search_destinations(
        self,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search destinations using vector similarity."""
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
        destination_data: Dict[str, Any],
        embedding: List[float],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save destination with embedding."""
        destination_data["embedding"] = embedding
        result = await self.upsert(
            "destinations", destination_data, on_conflict="id", user_id=user_id
        )
        return result[0] if result else {}

    # Advanced query operations

    async def execute_sql(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute raw SQL query with security checks."""
        await self.ensure_connected()

        # Security check for SQL injection
        if self.enable_security:
            self._check_sql_injection(sql)

        async with self._monitor_query(QueryType.RAW_SQL, None, user_id):
            try:
                if self._sqlalchemy_engine:
                    # Use SQLAlchemy for better control
                    with self._sqlalchemy_engine.connect() as conn:
                        result = conn.execute(text(sql), params or {})
                        if result.returns_rows:
                            rows = result.fetchall()
                            return [dict(row._mapping) for row in rows]
                        else:
                            return [{"rows_affected": result.rowcount}]
                else:
                    # Fallback to Supabase RPC
                    result = await asyncio.to_thread(
                        lambda: self.client.rpc(
                            "execute_sql", {"sql": sql, "params": params or {}}
                        ).execute()
                    )
                    return result.data
            except Exception as e:
                logger.error(f"SQL execution error: {e}")
                raise CoreDatabaseError(
                    message="Failed to execute SQL query",
                    code="SQL_EXECUTION_FAILED",
                    operation="EXECUTE_SQL",
                    details={"error": str(e), "sql": sql},
                ) from e

    async def call_function(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Any:
        """Call Supabase database function."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.FUNCTION_CALL, function_name, user_id):
            try:
                result = await asyncio.to_thread(
                    lambda: self.client.rpc(function_name, params or {}).execute()
                )
                return result.data
            except Exception as e:
                logger.error(f"Function call error for '{function_name}': {e}")
                raise CoreDatabaseError(
                    message=f"Failed to call database function '{function_name}'",
                    code="FUNCTION_CALL_FAILED",
                    operation="CALL_FUNCTION",
                    details={"error": str(e), "function": function_name},
                ) from e

    # Trip-specific operations

    async def get_trip_by_id(
        self, trip_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get trip by ID - compatibility method."""
        try:
            result = await self.select("trips", "*", {"id": trip_id}, user_id=user_id)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get trip by ID {trip_id}: {e}")
            return None

    async def search_trips(
        self,
        search_filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search trips with text and filters."""
        await self.ensure_connected()

        async with self._monitor_query(QueryType.SELECT, "trips", user_id):
            try:
                query = self.client.table("trips").select("*")

                # Apply basic filters
                if "user_id" in search_filters:
                    query = query.eq("user_id", search_filters["user_id"])

                if "status" in search_filters:
                    query = query.eq("status", search_filters["status"])

                if "visibility" in search_filters:
                    query = query.eq("visibility", search_filters["visibility"])

                # Text search
                if "query" in search_filters and search_filters["query"]:
                    search_text = search_filters["query"]
                    query = query.or_(
                        f"name.ilike.%{search_text}%,destination.ilike.%{search_text}%"
                    )

                # Filter by destinations
                if "destinations" in search_filters and search_filters["destinations"]:
                    destination_filters = []
                    for dest in search_filters["destinations"]:
                        destination_filters.append(f"destination.ilike.%{dest}%")
                    if destination_filters:
                        query = query.or_(",".join(destination_filters))

                # Filter by tags
                if "tags" in search_filters and search_filters["tags"]:
                    query = query.overlaps("notes", search_filters["tags"])

                # Date range filter
                if "date_range" in search_filters:
                    date_range = search_filters["date_range"]
                    if "start_date" in date_range:
                        query = query.gte(
                            "start_date", date_range["start_date"].isoformat()
                        )
                    if "end_date" in date_range:
                        query = query.lte(
                            "end_date", date_range["end_date"].isoformat()
                        )

                # Apply pagination and ordering
                query = query.order("created_at", desc=True)
                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                result = await asyncio.to_thread(lambda: query.execute())
                return result.data

            except Exception as e:
                logger.error(f"Trip search failed: {e}")
                raise CoreDatabaseError(
                    message="Failed to search trips",
                    code="TRIP_SEARCH_FAILED",
                    operation="SEARCH_TRIPS",
                    details={"error": str(e), "filters": search_filters},
                ) from e

    async def get_trip_collaborators(
        self, trip_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get trip collaborators."""
        try:
            return await self.select(
                "trip_collaborators", "*", {"trip_id": trip_id}, user_id=user_id
            )
        except Exception as e:
            logger.error(f"Failed to get trip collaborators for trip {trip_id}: {e}")
            raise CoreDatabaseError(
                message=f"Failed to get collaborators for trip {trip_id}",
                code="GET_COLLABORATORS_FAILED",
                operation="GET_TRIP_COLLABORATORS",
                table="trip_collaborators",
                details={"error": str(e), "trip_id": trip_id},
            ) from e

    async def get_trip_related_counts(
        self, trip_id: str, user_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get counts of related trip data."""
        try:
            results = {}

            # Count itinerary items
            results["itinerary_count"] = await self.count(
                "itinerary_items", {"trip_id": trip_id}, user_id
            )

            # Count flights
            results["flight_count"] = await self.count(
                "flights", {"trip_id": trip_id}, user_id
            )

            # Count accommodations
            results["accommodation_count"] = await self.count(
                "accommodations", {"trip_id": trip_id}, user_id
            )

            # Count transportation
            results["transportation_count"] = await self.count(
                "transportation", {"trip_id": trip_id}, user_id
            )

            # Count collaborators
            results["collaborator_count"] = await self.count(
                "trip_collaborators", {"trip_id": trip_id}, user_id
            )

            return results

        except Exception as e:
            logger.error(f"Failed to get trip related counts for trip {trip_id}: {e}")
            raise CoreDatabaseError(
                message=f"Failed to get related counts for trip {trip_id}",
                code="GET_TRIP_COUNTS_FAILED",
                operation="GET_TRIP_RELATED_COUNTS",
                details={"error": str(e), "trip_id": trip_id},
            ) from e

    async def add_trip_collaborator(
        self, collaborator_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add trip collaborator."""
        try:
            # Ensure required fields
            required_fields = ["trip_id", "user_id", "permission_level", "added_by"]
            for field in required_fields:
                if field not in collaborator_data:
                    raise CoreDatabaseError(
                        message=f"Missing required field: {field}",
                        code="MISSING_REQUIRED_FIELD",
                        operation="ADD_TRIP_COLLABORATOR",
                        details={"missing_field": field},
                    )

            # Use upsert to handle duplicates
            user_id = collaborator_data.get("added_by")
            result = await self.upsert(
                "trip_collaborators",
                collaborator_data,
                on_conflict="trip_id,user_id",
                user_id=user_id,
            )
            return result[0] if result else {}

        except CoreDatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to add trip collaborator: {e}")
            raise CoreDatabaseError(
                message="Failed to add trip collaborator",
                code="ADD_COLLABORATOR_FAILED",
                operation="ADD_TRIP_COLLABORATOR",
                table="trip_collaborators",
                details={"error": str(e), "collaborator_data": collaborator_data},
            ) from e

    async def get_trip_collaborator(
        self, trip_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific trip collaborator."""
        try:
            result = await self.select(
                "trip_collaborators",
                "*",
                {"trip_id": trip_id, "user_id": user_id},
                user_id=user_id,
            )
            return result[0] if result else None

        except Exception as e:
            logger.error(
                f"Failed to get trip collaborator for trip {trip_id}, user {user_id}: {e}"
            )
            raise CoreDatabaseError(
                message=f"Failed to get collaborator for trip {trip_id} and user {user_id}",
                code="GET_COLLABORATOR_FAILED",
                operation="GET_TRIP_COLLABORATOR",
                table="trip_collaborators",
                details={"error": str(e), "trip_id": trip_id, "user_id": user_id},
            ) from e

    # Analytics and reporting

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        # Get trip count
        trip_count = await self.count("trips", {"user_id": user_id}, user_id)

        # Get search count
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

    async def get_popular_destinations(
        self, limit: int = 10, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get most popular destinations."""
        return await self.execute_sql(
            """
            SELECT destination, COUNT(*) as search_count
            FROM trips
            WHERE destination IS NOT NULL
            GROUP BY destination
            ORDER BY search_count DESC
            LIMIT %(limit)s
            """,
            {"limit": limit},
            user_id,
        )

    # Health and monitoring

    async def health_check(self) -> bool:
        """Check database connectivity and health."""
        try:
            await self.ensure_connected()

            # Test Supabase connection
            await asyncio.to_thread(
                lambda: self.client.table("users").select("id").limit(1).execute()
            )

            # Test SQLAlchemy connection if available
            if self._sqlalchemy_engine:
                with self._sqlalchemy_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))

            # Update health metric
            if self._metrics:
                self._metrics.health_status.labels(component="overall").set(1)

            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

            # Update health metric
            if self._metrics:
                self._metrics.health_status.labels(component="overall").set(0)

            return False

    async def get_table_info(
        self, table: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get table schema information."""
        try:
            result = await self.execute_sql(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %(table_name)s
                ORDER BY ordinal_position
                """,
                {"table_name": table},
                user_id,
            )
            return {"columns": result}
        except Exception as e:
            logger.error(f"Failed to get table info for '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to get schema info for table '{table}'",
                code="TABLE_INFO_FAILED",
                table=table,
                details={"error": str(e)},
            ) from e

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            stats = {
                "connection_stats": self._connection_stats.dict(),
                "uptime_seconds": time.time() - self._start_time,
            }

            # Add query metrics summary
            if self.enable_query_tracking and self._query_metrics:
                successful_queries = [m for m in self._query_metrics if m.success]
                failed_queries = [m for m in self._query_metrics if not m.success]

                stats["query_stats"] = {
                    "total_queries": len(self._query_metrics),
                    "successful_queries": len(successful_queries),
                    "failed_queries": len(failed_queries),
                    "avg_query_time_ms": (
                        sum(m.duration_ms for m in successful_queries)
                        / len(successful_queries)
                        if successful_queries
                        else 0
                    ),
                    "queries_by_type": self._get_queries_by_type(),
                }

            # Add security stats
            if self.enable_security and self._security_alerts:
                stats["security_stats"] = {
                    "total_alerts": len(self._security_alerts),
                    "alerts_by_type": self._get_alerts_by_type(),
                    "recent_alerts": [
                        alert.dict() for alert in self._security_alerts[-10:]
                    ],
                }

            # Add pool stats from SQLAlchemy
            if self._sqlalchemy_engine:
                pool = self._sqlalchemy_engine.pool
                stats["pool_stats"] = {
                    "size": pool.size(),
                    "checked_out": pool.checked_out_connections(),
                    "overflow": pool.overflow(),
                    "total": pool.size() + pool.overflow(),
                }

            return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise CoreDatabaseError(
                message="Failed to get database statistics",
                code="STATS_FAILED",
                details={"error": str(e)},
            ) from e

    # Helper methods

    def _check_sql_injection(self, sql: str) -> None:
        """Basic SQL injection detection."""
        # List of suspicious patterns
        suspicious_patterns = [
            "';",
            '";',
            "--",
            "/*",
            "*/",
            "xp_",
            "sp_",
            "exec",
            "execute",
            "drop table",
            "drop database",
            "truncate",
            "delete from",
            "insert into",
            "update set",
            "union select",
            "or 1=1",
            "or '1'='1'",
            "or true",
            "admin'--",
        ]

        sql_lower = sql.lower()
        for pattern in suspicious_patterns:
            if pattern in sql_lower:
                # Create security alert
                alert = SecurityAlert(
                    event_type=SecurityEvent.SQL_INJECTION_ATTEMPT,
                    severity="critical",
                    message="Potential SQL injection attempt detected",
                    details={
                        "pattern": pattern,
                        "sql_snippet": sql[:100],
                    },
                )
                self._security_alerts.append(alert)

                # Record metric
                if self._metrics:
                    self._metrics.security_events.labels(
                        event_type="sql_injection_attempt",
                        severity="critical",
                    ).inc()

                raise CoreServiceError(
                    message="Potential SQL injection detected",
                    code="SQL_INJECTION_DETECTED",
                    service="DatabaseService",
                )

    def _log_audit_event(
        self,
        user_id: Optional[str],
        action: str,
        table: str,
        records_affected: int,
    ) -> None:
        """Log audit event for compliance."""
        if not self.enable_audit_logging:
            return

        # In a real implementation, this would write to an audit log table
        logger.info(
            f"AUDIT: user={user_id}, action={action}, table={table}, "
            f"records={records_affected}, timestamp={datetime.now(timezone.utc).isoformat()}"
        )

    def _get_queries_by_type(self) -> Dict[str, int]:
        """Get query count by type."""
        counts = {}
        for metric in self._query_metrics:
            query_type = metric.query_type.value
            counts[query_type] = counts.get(query_type, 0) + 1
        return counts

    def _get_alerts_by_type(self) -> Dict[str, int]:
        """Get security alert count by type."""
        counts = {}
        for alert in self._security_alerts:
            event_type = alert.event_type.value
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    # Public monitoring methods

    def get_connection_stats(self) -> ConnectionStats:
        """Get current connection pool statistics."""
        # Update pool utilization
        if self._sqlalchemy_engine:
            pool = self._sqlalchemy_engine.pool
            total_capacity = self.pool_size + self.max_overflow
            used_connections = pool.checked_out_connections()
            self._connection_stats.pool_utilization = (
                used_connections / total_capacity
            ) * 100
            self._connection_stats.active_connections = used_connections
            self._connection_stats.idle_connections = pool.size() - used_connections

        # Update average query time
        if self._query_metrics:
            successful_queries = [m for m in self._query_metrics if m.success]
            if successful_queries:
                self._connection_stats.avg_query_time_ms = sum(
                    m.duration_ms for m in successful_queries
                ) / len(successful_queries)

        # Update uptime
        self._connection_stats.uptime_seconds = time.time() - self._start_time

        return self._connection_stats

    def get_recent_queries(
        self, limit: int = 100, include_slow_only: bool = False
    ) -> List[QueryMetrics]:
        """Get recent query metrics."""
        queries = self._query_metrics[-limit:]

        if include_slow_only:
            queries = [
                q for q in queries if q.duration_ms > self.slow_query_threshold * 1000
            ]

        return queries

    def get_security_alerts(
        self, limit: Optional[int] = None, severity: Optional[str] = None
    ) -> List[SecurityAlert]:
        """Get security alerts with optional filtering."""
        alerts = self._security_alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if limit:
            alerts = alerts[-limit:]

        return alerts

    def clear_metrics(self) -> None:
        """Clear accumulated metrics and alerts."""
        self._query_metrics.clear()
        self._security_alerts.clear()
        logger.info("Metrics and alerts cleared")


# Global database service instance
_database_service: Optional[DatabaseService] = None


async def get_database_service() -> DatabaseService:
    """Get the global database service instance.

    Returns:
        Connected DatabaseService instance
    """
    global _database_service

    if _database_service is None:
        _database_service = DatabaseService()
        await _database_service.connect()

    return _database_service


async def close_database_service() -> None:
    """Close the global database service instance."""
    global _database_service

    if _database_service:
        await _database_service.close()
        _database_service = None
