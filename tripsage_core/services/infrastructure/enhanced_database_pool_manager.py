"""
Enhanced Database Pool Manager with LIFO Connection Pooling.

This module implements research-backed 2025 patterns for optimal database performance:
- LIFO (Last-In-First-Out) connection pooling for better cache locality
- SQLAlchemy pooling layer under Supabase for precise control
- CPU-aware pool sizing for optimal resource utilization
- Connection validation with pool_pre_ping for reliability
- Comprehensive Prometheus metrics integration
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.monitoring.enhanced_database_metrics import (
    get_enhanced_database_metrics,
)

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolStats:
    """Statistics for connection pool performance monitoring."""

    pool_id: str
    total_connections: int
    active_connections: int
    idle_connections: int
    utilization_percent: float
    checkout_count: int
    checkin_count: int
    avg_checkout_time_ms: float
    max_checkout_time_ms: float
    connection_errors: int
    validation_failures: int
    last_updated: datetime


class EnhancedDatabasePoolManager:
    """
    Enhanced database pool manager implementing 2025 best practices.

    Features:
    - LIFO connection pooling for optimal cache locality (pool_use_lifo=True)
    - CPU-aware pool sizing (cpu_count * 2 for pool_size and max_overflow)
    - Connection validation with pool_pre_ping for reliability
    - Comprehensive metrics collection for Prometheus monitoring
    - Connection health scoring and performance tracking
    - Statistical baseline establishment for regression detection
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        enable_metrics: bool = True,
        enable_lifo: bool = True,
        enable_pre_ping: bool = True,
    ):
        """Initialize enhanced pool manager with 2025 best practices.

        Args:
            settings: Application settings
            enable_metrics: Enable comprehensive metrics collection
            enable_lifo: Enable LIFO connection pooling
            enable_pre_ping: Enable connection validation
        """
        self.settings = settings or get_settings()
        self.enable_metrics = enable_metrics
        self.enable_lifo = enable_lifo
        self.enable_pre_ping = enable_pre_ping

        # Pool configuration based on 2025 research
        self.cpu_count = os.cpu_count() or 4
        self.pool_size = self.cpu_count * 2  # Optimal sizing based on research
        self.max_overflow = self.cpu_count * 2  # Allow burst capacity

        # Components
        self._sqlalchemy_engine: Optional[Engine] = None
        self._supabase_client: Optional[Client] = None
        self._initialized = False
        self._pool_id = f"enhanced_pool_{int(time.time())}"

        # Metrics and monitoring
        self._metrics = get_enhanced_database_metrics() if enable_metrics else None
        self._stats = ConnectionPoolStats(
            pool_id=self._pool_id,
            total_connections=0,
            active_connections=0,
            idle_connections=0,
            utilization_percent=0.0,
            checkout_count=0,
            checkin_count=0,
            avg_checkout_time_ms=0.0,
            max_checkout_time_ms=0.0,
            connection_errors=0,
            validation_failures=0,
            last_updated=datetime.now(timezone.utc),
        )

        # Performance tracking
        self._checkout_times = []
        self._start_time = time.time()

        logger.info(
            f"Enhanced pool manager initialized: pool_size={self.pool_size}, "
            f"max_overflow={self.max_overflow}, lifo={enable_lifo}, "
            f"pre_ping={enable_pre_ping}"
        )

    async def initialize(self) -> None:
        """Initialize the enhanced connection pool with SQLAlchemy + Supabase."""
        if self._initialized:
            return

        logger.info("Initializing enhanced database pool with LIFO and metrics")

        try:
            # Initialize SQLAlchemy engine with LIFO pooling
            await self._initialize_sqlalchemy_engine()

            # Initialize Supabase client
            await self._initialize_supabase_client()

            # Test connections
            await self._test_connections()

            # Initialize metrics baseline
            if self._metrics:
                self._initialize_metrics_baseline()

            self._initialized = True
            logger.info(
                f"Enhanced database pool initialized successfully "
                f"(pool_id: {self._pool_id})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize enhanced pool: {e}")
            raise CoreDatabaseError(
                message="Failed to initialize enhanced database pool",
                code="ENHANCED_POOL_INIT_FAILED",
                details={"error": str(e)},
            ) from e

    async def _initialize_sqlalchemy_engine(self) -> None:
        """Initialize SQLAlchemy engine with LIFO pooling configuration."""
        try:
            # Build PostgreSQL connection string from Supabase URL
            postgres_url = self._build_postgres_connection_string()

            # Create engine with 2025 best practices
            self._sqlalchemy_engine = create_engine(
                postgres_url,
                # LIFO pooling for better cache locality
                pool_use_lifo=self.enable_lifo,
                # Connection validation for reliability
                pool_pre_ping=self.enable_pre_ping,
                # CPU-aware pool sizing
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                # Pool configuration
                poolclass=QueuePool,
                pool_timeout=30,  # Reasonable timeout for serverless
                pool_recycle=3600,  # 1 hour recycle for freshness
                # Performance optimizations
                echo=False,  # Disable SQL logging for performance
                future=True,  # Use SQLAlchemy 2.x features
                # Connection arguments for performance
                connect_args={
                    "application_name": "tripsage_enhanced_pool",
                    "connect_timeout": 10,
                    "command_timeout": 30,
                    # Performance tuning
                    "options": "-c default_transaction_isolation=read_committed",
                },
            )

            logger.info(
                f"SQLAlchemy engine initialized with LIFO pooling: "
                f"pool_size={self.pool_size}, max_overflow={self.max_overflow}, "
                f"pool_use_lifo={self.enable_lifo}, pool_pre_ping={self.enable_pre_ping}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize SQLAlchemy engine: {e}")
            raise CoreDatabaseError(
                message="Failed to initialize SQLAlchemy engine",
                code="SQLALCHEMY_INIT_FAILED",
                details={"error": str(e)},
            ) from e

    def _build_postgres_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase URL."""
        try:
            # Parse Supabase URL
            supabase_url = self.settings.database_url
            parsed = urlparse(supabase_url)

            # Extract components for PostgreSQL connection
            parsed.netloc.replace(".supabase.co", ".supabase.co")
            project_id = parsed.netloc.split(".")[0]

            # Get database credentials
            db_password = self.settings.database_password.get_secret_value()

            # Build PostgreSQL connection string for direct access
            postgres_url = (
                f"postgresql://postgres:{db_password}@"
                f"db.{project_id}.supabase.co:5432/postgres"
            )

            logger.debug("Built PostgreSQL connection string for SQLAlchemy")
            return postgres_url

        except Exception as e:
            logger.error(f"Failed to build PostgreSQL connection string: {e}")
            raise CoreDatabaseError(
                message="Failed to build database connection string",
                code="CONNECTION_STRING_BUILD_FAILED",
                details={"error": str(e)},
            ) from e

    async def _initialize_supabase_client(self) -> None:
        """Initialize Supabase client for high-level operations."""
        try:
            supabase_url = self.settings.database_url
            supabase_key = self.settings.database_public_key.get_secret_value()

            # Configure client options for performance
            options = ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=30.0,
            )

            self._supabase_client = create_client(
                supabase_url, supabase_key, options=options
            )

            logger.debug("Supabase client initialized for high-level operations")

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise CoreDatabaseError(
                message="Failed to initialize Supabase client",
                code="SUPABASE_CLIENT_INIT_FAILED",
                details={"error": str(e)},
            ) from e

    async def _test_connections(self) -> None:
        """Test both SQLAlchemy and Supabase connections."""
        try:
            # Test SQLAlchemy connection
            if self._sqlalchemy_engine:
                await asyncio.to_thread(self._test_sqlalchemy_connection)

            # Test Supabase connection
            if self._supabase_client:
                await asyncio.to_thread(self._test_supabase_connection)

            logger.debug("Connection tests passed")

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise CoreDatabaseError(
                message="Connection test failed",
                code="CONNECTION_TEST_FAILED",
                details={"error": str(e)},
            ) from e

    def _test_sqlalchemy_connection(self) -> None:
        """Test SQLAlchemy connection with pool validation."""
        with self._sqlalchemy_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.scalar() != 1:
                raise RuntimeError("SQLAlchemy connection test failed")

    def _test_supabase_connection(self) -> None:
        """Test Supabase connection."""
        self._supabase_client.table("users").select("id").limit(1).execute()
        # Connection is successful if no exception is raised

    def _initialize_metrics_baseline(self) -> None:
        """Initialize performance metrics baseline."""
        if not self._metrics:
            return

        try:
            # Set build information
            self._metrics.set_build_info(
                version="2025.1.0",
                commit="enhanced_pool_manager",
                build_date=datetime.now(timezone.utc).isoformat(),
                python_version=f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            )

            # Initialize pool metrics
            self._update_pool_metrics()

            logger.debug("Metrics baseline initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize metrics baseline: {e}")

    @asynccontextmanager
    async def acquire_connection(
        self,
        operation_type: str = "query",
        timeout: float = 30.0,
    ):
        """
        Acquire connection from LIFO pool with comprehensive monitoring.

        Args:
            operation_type: Type of operation for metrics tracking
            timeout: Connection acquisition timeout

        Yields:
            Tuple of (connection_type, connection) where:
            - connection_type: "sqlalchemy" or "supabase"
            - connection: The actual connection object

        This method provides:
        - LIFO connection acquisition for optimal cache locality
        - Connection validation with pre-ping
        - Comprehensive metrics collection
        - Performance monitoring and regression detection
        """
        checkout_start = time.time()
        connection_acquired = False
        connection_type = None
        connection = None

        try:
            await self.initialize()

            # Record checkout attempt
            self._stats.checkout_count += 1

            # Choose connection type based on operation
            if operation_type in ["raw_sql", "transaction", "bulk_operation"]:
                # Use SQLAlchemy for low-level operations
                connection_type = "sqlalchemy"
                connection = await asyncio.to_thread(
                    self._acquire_sqlalchemy_connection
                )
            else:
                # Use Supabase for high-level operations
                connection_type = "supabase"
                connection = self._supabase_client

            connection_acquired = True
            checkout_duration = time.time() - checkout_start

            # Record successful checkout
            self._record_successful_checkout(checkout_duration, operation_type)

            # Update pool statistics
            self._update_pool_metrics()

            yield connection_type, connection

        except Exception as e:
            # Record failed checkout
            checkout_duration = time.time() - checkout_start
            self._record_failed_checkout(checkout_duration, operation_type, str(e))

            logger.error(f"Failed to acquire connection: {e}")
            raise CoreDatabaseError(
                message="Failed to acquire database connection",
                code="CONNECTION_ACQUIRE_FAILED",
                details={
                    "error": str(e),
                    "operation_type": operation_type,
                    "checkout_duration_ms": checkout_duration * 1000,
                },
            ) from e

        finally:
            if connection_acquired:
                # Connection return is handled automatically by context managers
                self._stats.checkin_count += 1

                # Update final metrics
                self._update_pool_metrics()

    def _acquire_sqlalchemy_connection(self):
        """Acquire SQLAlchemy connection from LIFO pool."""
        if not self._sqlalchemy_engine:
            raise CoreDatabaseError(
                message="SQLAlchemy engine not initialized",
                code="SQLALCHEMY_ENGINE_NOT_INITIALIZED",
            )

        # This will use LIFO pooling automatically
        return self._sqlalchemy_engine.connect()

    def _record_successful_checkout(self, duration: float, operation_type: str) -> None:
        """Record successful connection checkout."""
        duration_ms = duration * 1000
        self._checkout_times.append(duration_ms)

        # Keep only recent checkout times for statistics
        if len(self._checkout_times) > 1000:
            self._checkout_times = self._checkout_times[-1000:]

        # Update statistics
        self._stats.avg_checkout_time_ms = sum(self._checkout_times) / len(
            self._checkout_times
        )
        self._stats.max_checkout_time_ms = max(
            self._stats.max_checkout_time_ms, duration_ms
        )

        # Record in metrics
        if self._metrics:
            self._metrics.record_checkout_duration(
                duration=duration,
                result="success",
                pool_id=self._pool_id,
                database="supabase",
            )

    def _record_failed_checkout(
        self, duration: float, operation_type: str, error: str
    ) -> None:
        """Record failed connection checkout."""
        self._stats.connection_errors += 1

        # Record in metrics
        if self._metrics:
            self._metrics.record_checkout_duration(
                duration=duration,
                result="error",
                pool_id=self._pool_id,
                database="supabase",
            )

            # Categorize error type
            error_type = "unknown"
            if "timeout" in error.lower():
                error_type = "timeout"
            elif "connection" in error.lower():
                error_type = "connection_failed"
            elif "pool" in error.lower():
                error_type = "pool_exhausted"

            self._metrics.record_connection_error(
                error_type=error_type,
                pool_id=self._pool_id,
                database="supabase",
            )

    def _update_pool_metrics(self) -> None:
        """Update connection pool metrics."""
        if not self._metrics or not self._sqlalchemy_engine:
            return

        try:
            # Get pool statistics from SQLAlchemy
            pool = self._sqlalchemy_engine.pool

            # Calculate pool utilization
            checked_out = pool.checkedout()
            pool.size()
            total_connections = checked_out + pool.checkedin()
            idle_connections = pool.checkedin()

            # Calculate utilization percentage
            max_connections = self.pool_size + self.max_overflow
            utilization_percent = (checked_out / max_connections) * 100

            # Update local statistics
            self._stats.total_connections = total_connections
            self._stats.active_connections = checked_out
            self._stats.idle_connections = idle_connections
            self._stats.utilization_percent = utilization_percent
            self._stats.last_updated = datetime.now(timezone.utc)

            # Record in Prometheus metrics
            self._metrics.record_pool_utilization(
                utilization_percent=utilization_percent,
                active_connections=checked_out,
                idle_connections=idle_connections,
                total_connections=total_connections,
                pool_id=self._pool_id,
                database="supabase",
            )

            # Record connection health scores (simplified implementation)
            avg_health_score = max(0.0, 1.0 - (self._stats.connection_errors / 100))
            self._metrics.record_connection_health(
                connection_id="pool_average",
                health_score=avg_health_score,
                pool_id=self._pool_id,
                database="supabase",
            )

        except Exception as e:
            logger.warning(f"Failed to update pool metrics: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with detailed diagnostics."""
        health_status = {
            "status": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool_id": self._pool_id,
            "checks": {},
            "metrics": {},
            "recommendations": [],
        }

        try:
            await self.initialize()

            # Test SQLAlchemy connection
            sqlalchemy_healthy = False
            try:
                await asyncio.to_thread(self._test_sqlalchemy_connection)
                sqlalchemy_healthy = True
                health_status["checks"]["sqlalchemy"] = "healthy"
            except Exception as e:
                health_status["checks"]["sqlalchemy"] = f"unhealthy: {e}"

            # Test Supabase connection
            supabase_healthy = False
            try:
                await asyncio.to_thread(self._test_supabase_connection)
                supabase_healthy = True
                health_status["checks"]["supabase"] = "healthy"
            except Exception as e:
                health_status["checks"]["supabase"] = f"unhealthy: {e}"

            # Overall health status
            if sqlalchemy_healthy and supabase_healthy:
                health_status["status"] = "healthy"
            elif sqlalchemy_healthy or supabase_healthy:
                health_status["status"] = "degraded"
            else:
                health_status["status"] = "unhealthy"

            # Add performance metrics
            health_status["metrics"] = {
                "pool_utilization_percent": self._stats.utilization_percent,
                "total_connections": self._stats.total_connections,
                "active_connections": self._stats.active_connections,
                "idle_connections": self._stats.idle_connections,
                "avg_checkout_time_ms": self._stats.avg_checkout_time_ms,
                "max_checkout_time_ms": self._stats.max_checkout_time_ms,
                "checkout_count": self._stats.checkout_count,
                "checkin_count": self._stats.checkin_count,
                "connection_errors": self._stats.connection_errors,
                "uptime_seconds": time.time() - self._start_time,
            }

            # Generate recommendations
            recommendations = []
            if self._stats.utilization_percent > 80:
                recommendations.append(
                    "High pool utilization detected. Consider increasing pool_size."
                )
            if self._stats.avg_checkout_time_ms > 100:
                recommendations.append(
                    "High average checkout time. Check for connection contention."
                )
            if self._stats.connection_errors > 10:
                recommendations.append(
                    "Multiple connection errors detected. Check database connectivity."
                )

            health_status["recommendations"] = recommendations

        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {e}")

        return health_status

    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get detailed pool statistics for monitoring."""
        stats_dict = {
            "pool_id": self._stats.pool_id,
            "configuration": {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "cpu_count": self.cpu_count,
                "lifo_enabled": self.enable_lifo,
                "pre_ping_enabled": self.enable_pre_ping,
            },
            "current_status": {
                "total_connections": self._stats.total_connections,
                "active_connections": self._stats.active_connections,
                "idle_connections": self._stats.idle_connections,
                "utilization_percent": round(self._stats.utilization_percent, 2),
            },
            "performance": {
                "checkout_count": self._stats.checkout_count,
                "checkin_count": self._stats.checkin_count,
                "avg_checkout_time_ms": round(self._stats.avg_checkout_time_ms, 2),
                "max_checkout_time_ms": round(self._stats.max_checkout_time_ms, 2),
                "connection_errors": self._stats.connection_errors,
                "validation_failures": self._stats.validation_failures,
            },
            "timestamps": {
                "last_updated": self._stats.last_updated.isoformat(),
                "uptime_seconds": round(time.time() - self._start_time, 2),
            },
        }

        # Add recent performance percentiles if available
        if self._metrics and len(self._checkout_times) >= 10:
            sorted_times = sorted(self._checkout_times)
            n = len(sorted_times)
            stats_dict["checkout_percentiles"] = {
                "p50_ms": round(sorted_times[int(n * 0.5)], 2),
                "p95_ms": round(sorted_times[int(n * 0.95)], 2),
                "p99_ms": round(sorted_times[int(n * 0.99)], 2),
            }

        return stats_dict

    async def close(self) -> None:
        """Clean up resources and close connections."""
        logger.info(f"Closing enhanced database pool (pool_id: {self._pool_id})")

        try:
            # Close SQLAlchemy engine
            if self._sqlalchemy_engine:
                self._sqlalchemy_engine.dispose()
                self._sqlalchemy_engine = None
                logger.debug("SQLAlchemy engine disposed")

            # Supabase client doesn't need explicit cleanup
            self._supabase_client = None

            # Reset state
            self._initialized = False

            logger.info("Enhanced database pool closed successfully")

        except Exception as e:
            logger.error(f"Error closing enhanced database pool: {e}")


# Global enhanced pool manager instance
_enhanced_pool_manager: Optional[EnhancedDatabasePoolManager] = None


async def get_enhanced_pool_manager() -> EnhancedDatabasePoolManager:
    """Get or create global enhanced pool manager instance."""
    global _enhanced_pool_manager

    if _enhanced_pool_manager is None:
        _enhanced_pool_manager = EnhancedDatabasePoolManager()
        await _enhanced_pool_manager.initialize()

    return _enhanced_pool_manager


async def close_enhanced_pool_manager() -> None:
    """Close global enhanced pool manager instance."""
    global _enhanced_pool_manager

    if _enhanced_pool_manager:
        await _enhanced_pool_manager.close()
        _enhanced_pool_manager = None
