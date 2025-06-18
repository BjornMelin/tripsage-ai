"""
Enhanced Database Service with Performance Monitoring and LIFO Connection Pooling.

This module provides a high-performance database service that integrates:
- LIFO connection pool behavior for better cache locality
- Enhanced Prometheus metrics and monitoring
- Performance regression detection
- Connection validation with pre-ping behavior
- Comprehensive observability and alerting
- Resource utilization tracking
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
)
from tripsage_core.monitoring.enhanced_database_metrics import (
    EnhancedDatabaseMetrics,
    get_enhanced_database_metrics,
)
from tripsage_core.monitoring.performance_regression_detector import (
    PerformanceRegressionDetector,
    get_regression_detector,
)
from tripsage_core.services.infrastructure.enhanced_database_pool_manager import (
    EnhancedDatabasePoolManager,
    get_enhanced_pool_manager,
)
from tripsage_core.services.infrastructure.replica_manager import (
    QueryType,
    ReplicaManager,
)

logger = logging.getLogger(__name__)


class EnhancedDatabaseService:
    """
    Enhanced database service with LIFO pooling and comprehensive monitoring.

    This service provides:
    - LIFO connection pool for optimal cache locality
    - Real-time performance monitoring and metrics
    - Performance regression detection and alerting
    - Connection health monitoring and validation
    - Comprehensive Prometheus metrics
    - Query latency percentiles (P50, P95, P99)
    - Resource utilization tracking
    - Automatic performance optimization
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        metrics_registry=None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        lifo_enabled: bool = True,
        enable_regression_detection: bool = True,
        regression_threshold: float = 1.5,
    ):
        """Initialize enhanced database service.

        Args:
            settings: Application settings
            metrics_registry: Prometheus metrics registry
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum number of additional connections
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Connection recycle time in seconds
            pool_pre_ping: Enable pre-ping validation
            lifo_enabled: Enable LIFO (Last In, First Out) behavior
            enable_regression_detection: Enable performance regression detection
            regression_threshold: Threshold for regression detection
        """
        self.settings = settings or get_settings()
        self.metrics_registry = metrics_registry
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.lifo_enabled = lifo_enabled
        self.enable_regression_detection = enable_regression_detection
        self.regression_threshold = regression_threshold

        # Service state
        self._connected = False
        self._pool_manager: Optional[EnhancedDatabasePoolManager] = None
        self._replica_manager: Optional[ReplicaManager] = None
        self._metrics: Optional[EnhancedDatabaseMetrics] = None
        self._regression_detector: Optional[PerformanceRegressionDetector] = None

        # Performance tracking
        self._query_count = 0
        self._error_count = 0
        self._start_time = time.time()

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to the database."""
        return self._connected and self._pool_manager is not None

    async def connect(self) -> None:
        """Initialize database service with enhanced monitoring."""
        if self._connected:
            return

        logger.info("Connecting enhanced database service with monitoring")

        try:
            # Initialize enhanced metrics
            self._metrics = get_enhanced_database_metrics(
                metrics_registry=self.metrics_registry,
                enable_regression_detection=self.enable_regression_detection,
                regression_threshold=self.regression_threshold,
            )

            # Initialize performance regression detector
            if self.enable_regression_detection:
                self._regression_detector = await get_regression_detector(
                    regression_threshold=self.regression_threshold,
                )

                # Add alert callback for logging
                self._regression_detector.add_alert_callback(
                    lambda alert: logger.warning(
                        f"Performance regression: {alert.message} "
                        f"(severity: {alert.severity.value})"
                    )
                )

            # Initialize enhanced pool manager
            self._pool_manager = await get_enhanced_pool_manager(
                settings=self.settings,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=self.pool_pre_ping,
                lifo_enabled=self.lifo_enabled,
                metrics_registry=self.metrics_registry,
            )

            # Test connection
            is_healthy = await self._pool_manager.health_check()
            if not is_healthy:
                raise CoreDatabaseError(
                    message="Pool manager health check failed",
                    code="POOL_HEALTH_CHECK_FAILED",
                )

            # Initialize replica manager if enabled
            if self.settings.enable_read_replicas:
                try:
                    self._replica_manager = ReplicaManager(self.settings)
                    await self._replica_manager.initialize()
                    logger.info("Read replica manager initialized")
                except Exception as replica_error:
                    logger.error(
                        f"Failed to initialize replica manager: {replica_error}"
                    )
                    # Continue without replica manager

            self._connected = True

            # Set build info in metrics
            if self._metrics:
                self._metrics.set_build_info(
                    version="2025.1.0",
                    commit="enhanced-performance",
                    build_date=datetime.now().isoformat(),
                    python_version="3.13+",
                )

            logger.info(
                f"Enhanced database service connected successfully "
                f"(pool_size={self.pool_size}, lifo={self.lifo_enabled}, "
                f"regression_detection={self.enable_regression_detection})"
            )

        except Exception as e:
            logger.error(f"Failed to connect enhanced database service: {e}")
            self._connected = False
            raise CoreDatabaseError(
                message=f"Failed to connect to database: {str(e)}",
                code="DATABASE_CONNECTION_FAILED",
                details={"error": str(e)},
            ) from e

    async def close(self) -> None:
        """Close database service and cleanup resources."""
        logger.info("Closing enhanced database service")

        # Close replica manager first
        if self._replica_manager:
            try:
                await self._replica_manager.close()
                self._replica_manager = None
                logger.info("Replica manager closed")
            except Exception as e:
                logger.error(f"Error closing replica manager: {e}")

        # Close regression detector
        if self._regression_detector:
            try:
                await self._regression_detector.stop()
                self._regression_detector = None
                logger.info("Regression detector stopped")
            except Exception as e:
                logger.error(f"Error stopping regression detector: {e}")

        # Close pool manager
        if self._pool_manager:
            try:
                await self._pool_manager.close()
                self._pool_manager = None
                logger.info("Pool manager closed")
            except Exception as e:
                logger.error(f"Error closing pool manager: {e}")

        self._connected = False
        logger.info("Enhanced database service closed")

    async def ensure_connected(self) -> None:
        """Ensure database connection is established."""
        if not self.is_connected:
            await self.connect()

    @asynccontextmanager
    async def _get_client_for_query(
        self,
        query_type: QueryType = QueryType.READ,
        user_region: Optional[str] = None,
    ):
        """Get the appropriate client for a query with monitoring."""
        # If replica manager is available and enabled, use it for read queries
        if self._replica_manager and query_type in [
            QueryType.READ,
            QueryType.ANALYTICS,
            QueryType.VECTOR_SEARCH,
        ]:
            try:
                async with self._replica_manager.acquire_connection(
                    query_type=query_type,
                    user_region=user_region,
                ) as (replica_id, client):
                    yield replica_id, client
                    return
            except Exception as e:
                logger.warning(
                    f"Failed to get replica client: {e}, falling back to primary"
                )

        # Use enhanced pool manager for primary connections
        await self.ensure_connected()

        if not self._pool_manager:
            raise CoreServiceError(
                message="Pool manager not initialized",
                code="POOL_MANAGER_NOT_INITIALIZED",
                service="EnhancedDatabaseService",
            )

        async with self._pool_manager.acquire_connection() as client:
            yield "primary", client

    async def _execute_with_monitoring(
        self,
        operation: str,
        table: str,
        query_func,
        user_region: Optional[str] = None,
    ):
        """Execute database operation with comprehensive monitoring."""
        start_time = time.perf_counter()
        query_type = self._get_query_type(operation)
        success = False
        error_message = None

        try:
            async with self._get_client_for_query(
                query_type=query_type,
                user_region=user_region,
            ) as (replica_id, client):
                result = await query_func(client)
                success = True
                return result

        except Exception as e:
            error_message = str(e)
            self._error_count += 1
            raise

        finally:
            duration = time.perf_counter() - start_time
            self._query_count += 1

            # Record metrics
            if self._metrics:
                self._metrics.record_query_duration(
                    duration=duration,
                    operation=operation,
                    table=table,
                    database="supabase",
                    pool_id="enhanced",
                    status="success" if success else "error",
                )

                # Update pool utilization metrics
                if self._pool_manager:
                    pool_metrics = self._pool_manager.get_metrics()
                    stats = pool_metrics["statistics"]

                    self._metrics.record_pool_utilization(
                        utilization_percent=stats["pool_utilization"],
                        active_connections=stats["active_connections"],
                        idle_connections=stats["idle_connections"],
                        total_connections=stats["total_connections"],
                        pool_id="enhanced",
                        database="supabase",
                    )

            # Record for regression detection
            if self._regression_detector and success:
                metric_name = f"{operation}_{table}_duration"
                self._regression_detector.record_performance(
                    metric_name=metric_name,
                    value=duration,
                    operation=operation,
                    table=table,
                    metadata={
                        "replica_id": replica_id
                        if "replica_id" in locals()
                        else "primary"
                    },
                )

            logger.debug(
                f"Query {operation} on {table}: {duration:.3f}s "
                f"({'success' if success else 'error'})"
            )

    def _get_query_type(self, operation: str) -> QueryType:
        """Map operation string to QueryType enum."""
        operation_upper = operation.upper()

        mapping = {
            "SELECT": QueryType.READ,
            "INSERT": QueryType.WRITE,
            "UPDATE": QueryType.WRITE,
            "DELETE": QueryType.WRITE,
            "UPSERT": QueryType.WRITE,
            "COUNT": QueryType.READ,
            "VECTOR_SEARCH": QueryType.VECTOR_SEARCH,
        }

        return mapping.get(operation_upper, QueryType.READ)

    # Core database operations with monitoring

    async def insert(
        self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Insert data into table with monitoring."""

        async def _insert_query(client: Client):
            result = await asyncio.to_thread(
                lambda: client.table(table).insert(data).execute()
            )
            return result.data

        try:
            return await self._execute_with_monitoring(
                operation="INSERT",
                table=table,
                query_func=_insert_query,
            )
        except Exception as e:
            logger.error(f"Database INSERT error for table '{table}': {e}")
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
        user_region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table with monitoring."""

        async def _select_query(client: Client):
            query = client.table(table).select(columns)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # Support for complex filters like {"gte": 18}
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

        try:
            return await self._execute_with_monitoring(
                operation="SELECT",
                table=table,
                query_func=_select_query,
                user_region=user_region,
            )
        except Exception as e:
            logger.error(f"Database SELECT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to select from table '{table}'",
                code="SELECT_FAILED",
                operation="SELECT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def update(
        self, table: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update data in table with monitoring."""

        async def _update_query(client: Client):
            query = client.table(table).update(data)

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data

        try:
            return await self._execute_with_monitoring(
                operation="UPDATE",
                table=table,
                query_func=_update_query,
            )
        except Exception as e:
            logger.error(f"Database UPDATE error for table '{table}': {e}")
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
    ) -> List[Dict[str, Any]]:
        """Upsert data in table with monitoring."""

        async def _upsert_query(client: Client):
            query = client.table(table).upsert(data)

            if on_conflict:
                query = query.on_conflict(on_conflict)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data

        try:
            return await self._execute_with_monitoring(
                operation="UPSERT",
                table=table,
                query_func=_upsert_query,
            )
        except Exception as e:
            logger.error(f"Database UPSERT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to upsert into table '{table}'",
                code="UPSERT_FAILED",
                operation="UPSERT",
                table=table,
                details={"error": str(e)},
            ) from e

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete data from table with monitoring."""

        async def _delete_query(client: Client):
            query = client.table(table).delete()

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data

        try:
            return await self._execute_with_monitoring(
                operation="DELETE",
                table=table,
                query_func=_delete_query,
            )
        except Exception as e:
            logger.error(f"Database DELETE error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to delete from table '{table}'",
                code="DELETE_FAILED",
                operation="DELETE",
                table=table,
                details={"error": str(e)},
            ) from e

    async def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in table with monitoring."""

        async def _count_query(client: Client):
            query = client.table(table).select("*", count="exact")

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.count

        try:
            return await self._execute_with_monitoring(
                operation="COUNT",
                table=table,
                query_func=_count_query,
            )
        except Exception as e:
            logger.error(f"Database COUNT error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to count records in table '{table}'",
                code="COUNT_FAILED",
                operation="COUNT",
                table=table,
                details={"error": str(e)},
            ) from e

    # Vector search operations with monitoring

    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search with monitoring."""

        async def _vector_search_query(client: Client):
            # Convert vector to string format for PostgreSQL
            vector_str = f"[{','.join(map(str, query_vector))}]"

            query = client.table(table).select(
                f"*, {vector_column} <-> '{vector_str}' as distance"
            )

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply similarity threshold
            if similarity_threshold:
                distance_threshold = (
                    1 - similarity_threshold
                )  # Convert similarity to distance
                query = query.lt(
                    f"{vector_column} <-> '{vector_str}'", distance_threshold
                )

            # Order by similarity and limit
            query = query.order(f"{vector_column} <-> '{vector_str}'").limit(limit)

            result = await asyncio.to_thread(lambda: query.execute())
            return result.data

        try:
            return await self._execute_with_monitoring(
                operation="VECTOR_SEARCH",
                table=table,
                query_func=_vector_search_query,
                user_region=user_region,
            )
        except Exception as e:
            logger.error(f"Database vector search error for table '{table}': {e}")
            raise CoreDatabaseError(
                message=f"Failed to perform vector search on table '{table}'",
                code="VECTOR_SEARCH_FAILED",
                operation="VECTOR_SEARCH",
                table=table,
                details={"error": str(e)},
            ) from e

    # Health and monitoring

    async def health_check(self) -> bool:
        """Check database connectivity with enhanced monitoring."""
        try:
            await self.ensure_connected()

            # Use pool manager's health check
            if self._pool_manager:
                return await self._pool_manager.health_check()

            return False
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        uptime = time.time() - self._start_time
        error_rate = self._error_count / max(self._query_count, 1)

        metrics = {
            "service": {
                "uptime_seconds": uptime,
                "total_queries": self._query_count,
                "error_count": self._error_count,
                "error_rate": error_rate,
                "connected": self._connected,
                "lifo_enabled": self.lifo_enabled,
                "regression_detection_enabled": self.enable_regression_detection,
            }
        }

        # Add pool metrics
        if self._pool_manager:
            metrics["pool"] = self._pool_manager.get_metrics()

        # Add regression detector metrics
        if self._regression_detector:
            metrics["regression_detection"] = (
                self._regression_detector.get_metrics_summary()
            )

        # Add enhanced metrics summary
        if self._metrics:
            metrics["enhanced_metrics"] = self._metrics.get_summary_stats()

        return metrics

    def get_recent_performance_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent performance regression alerts."""
        if not self._regression_detector:
            return []

        alerts = self._regression_detector.get_recent_alerts(limit=limit)

        return [
            {
                "metric_name": alert.metric_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "baseline_p95": alert.baseline_p95,
                "z_score": alert.z_score,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "recommendations": alert.recommendations,
            }
            for alert in alerts
        ]


# Global enhanced database service instance
_enhanced_database_service: Optional[EnhancedDatabaseService] = None


async def get_enhanced_database_service(**kwargs) -> EnhancedDatabaseService:
    """Get the global enhanced database service instance.

    Args:
        **kwargs: Arguments to pass to EnhancedDatabaseService constructor

    Returns:
        Connected EnhancedDatabaseService instance
    """
    global _enhanced_database_service

    if _enhanced_database_service is None:
        _enhanced_database_service = EnhancedDatabaseService(**kwargs)
        await _enhanced_database_service.connect()

    return _enhanced_database_service


async def close_enhanced_database_service() -> None:
    """Close the global enhanced database service instance."""
    global _enhanced_database_service

    if _enhanced_database_service:
        await _enhanced_database_service.close()
        _enhanced_database_service = None
