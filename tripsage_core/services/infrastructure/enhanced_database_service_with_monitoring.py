"""
Enhanced Database Service with Integrated Query Performance Monitoring.

This module extends the existing DatabaseService with comprehensive query monitoring,
pattern detection, and performance analytics capabilities. It provides seamless
integration with the QueryPerformanceMonitor system while maintaining full
backward compatibility with the existing API.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError,
)
from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    get_database_metrics,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.query_monitor import (
    QueryMonitorConfig,
    QueryPerformanceMonitor,
    QueryType,
    get_query_monitor,
)

logger = logging.getLogger(__name__)


class EnhancedDatabaseService(DatabaseService):
    """
    Enhanced database service with integrated query performance monitoring.

    This service extends the standard DatabaseService with:
    - Automatic query performance tracking
    - Real-time pattern detection (N+1 queries, etc.)
    - Performance analytics and alerting
    - Prometheus metrics integration
    - Seamless monitoring without API changes
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        monitor_config: Optional[QueryMonitorConfig] = None,
        metrics: Optional[DatabaseMetrics] = None,
        enable_monitoring: bool = True,
    ):
        """Initialize enhanced database service with monitoring.

        Args:
            settings: Application settings
            monitor_config: Query monitoring configuration
            metrics: Database metrics collector
            enable_monitoring: Enable query performance monitoring
        """
        # Initialize parent class
        super().__init__(settings)

        # Initialize monitoring components
        self._monitoring_enabled = enable_monitoring
        self._metrics = metrics or get_database_metrics()

        if self._monitoring_enabled:
            self._query_monitor = get_query_monitor(
                config=monitor_config,
                settings=self.settings,
                metrics=self._metrics,
            )
            self._setup_monitoring()
        else:
            self._query_monitor = None

        logger.info(
            f"Enhanced database service initialized "
            f"(monitoring: {'enabled' if self._monitoring_enabled else 'disabled'})"
        )

    def _setup_monitoring(self):
        """Set up query monitoring integration."""
        if not self._query_monitor:
            return

        # Add hooks for enhanced monitoring
        def pre_query_hook(
            query_type, table_name, query_text, user_id, session_id, tags
        ):
            """Pre-query hook for additional logging."""
            logger.debug(
                f"Starting {query_type.value} query on {table_name} for user {user_id}"
            )

        def post_query_hook(execution, patterns, alerts):
            """Post-query hook for processing results."""
            if execution.duration and execution.duration > 0.5:
                logger.info(
                    f"Query {execution.query_id} took {execution.duration:.3f}s "
                    f"({execution.query_type.value} on {execution.table_name})"
                )

            if patterns:
                logger.warning(
                    f"Detected {len(patterns)} performance patterns for query {execution.query_id}"
                )

            if alerts:
                logger.warning(
                    f"Generated {len(alerts)} performance alerts for query {execution.query_id}"
                )

        self._query_monitor.add_pre_query_hook(pre_query_hook)
        self._query_monitor.add_post_query_hook(post_query_hook)

    @property
    def query_monitor(self) -> Optional[QueryPerformanceMonitor]:
        """Get the query performance monitor instance."""
        return self._query_monitor

    @property
    def monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self._monitoring_enabled

    async def start_monitoring(self):
        """Start background query monitoring."""
        if self._query_monitor:
            await self._query_monitor.start_monitoring()
            logger.info("Query performance monitoring started")

    async def stop_monitoring(self):
        """Stop background query monitoring."""
        if self._query_monitor:
            await self._query_monitor.stop_monitoring()
            logger.info("Query performance monitoring stopped")

    async def connect(self) -> None:
        """Connect to database and start monitoring."""
        await super().connect()
        if self._monitoring_enabled:
            await self.start_monitoring()

    async def close(self) -> None:
        """Close database connection and stop monitoring."""
        if self._monitoring_enabled:
            await self.stop_monitoring()
        await super().close()

    # Enhanced Core Database Operations with Monitoring

    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Insert data with query monitoring.

        Args:
            table: Table name
            data: Data to insert
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            List of inserted records
        """
        if not self._monitoring_enabled:
            return await super().insert(table, data)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.INSERT,
            table_name=table,
            user_id=user_id,
            session_id=session_id,
            tags={
                "operation": "insert",
                "record_count": len(data) if isinstance(data, list) else 1,
            },
        ):
            return await super().insert(table, data)

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select data with query monitoring.

        Args:
            table: Table name
            columns: Columns to select
            filters: Filter conditions
            order_by: Order by column
            limit: Limit number of results
            offset: Offset for pagination
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            List of selected records
        """
        if not self._monitoring_enabled:
            return await super().select(
                table, columns, filters, order_by, limit, offset
            )

        # Create query text for pattern detection
        query_text = f"SELECT {columns} FROM {table}"
        if filters:
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, dict):
                    for op in value.keys():
                        filter_parts.append(f"{key} {op} ?")
                else:
                    filter_parts.append(f"{key} = ?")
            if filter_parts:
                query_text += " WHERE " + " AND ".join(filter_parts)

        if order_by:
            query_text += f" ORDER BY {order_by}"
        if limit:
            query_text += f" LIMIT {limit}"
        if offset:
            query_text += f" OFFSET {offset}"

        async with self._query_monitor.monitor_query(
            query_type=QueryType.SELECT,
            table_name=table,
            query_text=query_text,
            user_id=user_id,
            session_id=session_id,
            tags={
                "operation": "select",
                "columns": columns,
                "has_filters": bool(filters),
                "has_order": bool(order_by),
                "has_limit": bool(limit),
            },
        ):
            return await super().select(
                table, columns, filters, order_by, limit, offset
            )

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Update data with query monitoring.

        Args:
            table: Table name
            data: Data to update
            filters: Filter conditions
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            List of updated records
        """
        if not self._monitoring_enabled:
            return await super().update(table, data, filters)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.UPDATE,
            table_name=table,
            user_id=user_id,
            session_id=session_id,
            tags={
                "operation": "update",
                "update_fields": list(data.keys()),
                "filter_fields": list(filters.keys()),
            },
        ):
            return await super().update(table, data, filters)

    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Upsert data with query monitoring.

        Args:
            table: Table name
            data: Data to upsert
            on_conflict: Columns to handle conflict on
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            List of upserted records
        """
        if not self._monitoring_enabled:
            return await super().upsert(table, data, on_conflict)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.UPSERT,
            table_name=table,
            user_id=user_id,
            session_id=session_id,
            tags={
                "operation": "upsert",
                "record_count": len(data) if isinstance(data, list) else 1,
                "on_conflict": on_conflict,
            },
        ):
            return await super().upsert(table, data, on_conflict)

    async def delete(
        self,
        table: str,
        filters: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Delete data with query monitoring.

        Args:
            table: Table name
            filters: Filter conditions
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            List of deleted records
        """
        if not self._monitoring_enabled:
            return await super().delete(table, filters)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.DELETE,
            table_name=table,
            user_id=user_id,
            session_id=session_id,
            tags={"operation": "delete", "filter_fields": list(filters.keys())},
        ):
            return await super().delete(table, filters)

    async def count(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Count records with query monitoring.

        Args:
            table: Table name
            filters: Filter conditions
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            Number of records
        """
        if not self._monitoring_enabled:
            return await super().count(table, filters)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.COUNT,
            table_name=table,
            user_id=user_id,
            session_id=session_id,
            tags={"operation": "count", "has_filters": bool(filters)},
        ):
            return await super().count(table, filters)

    # Vector Operations with Monitoring

    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Vector search with query monitoring.

        Args:
            table: Table name
            vector_column: Vector column name
            query_vector: Query vector
            limit: Number of results
            similarity_threshold: Minimum similarity threshold
            filters: Additional filters
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            List of similar records with similarity scores
        """
        if not self._monitoring_enabled:
            return await super().vector_search(
                table, vector_column, query_vector, limit, similarity_threshold, filters
            )

        async with self._query_monitor.monitor_query(
            query_type=QueryType.VECTOR_SEARCH,
            table_name=table,
            user_id=user_id,
            session_id=session_id,
            tags={
                "operation": "vector_search",
                "vector_column": vector_column,
                "vector_dimension": len(query_vector),
                "limit": limit,
                "similarity_threshold": similarity_threshold,
                "has_filters": bool(filters),
            },
        ):
            return await super().vector_search(
                table, vector_column, query_vector, limit, similarity_threshold, filters
            )

    # Advanced Operations with Monitoring

    async def execute_sql(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute raw SQL with query monitoring.

        Args:
            sql: SQL query
            params: Query parameters
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            Query results
        """
        if not self._monitoring_enabled:
            return await super().execute_sql(sql, params)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.RAW_SQL,
            table_name="multiple",  # Raw SQL can affect multiple tables
            query_text=sql,
            user_id=user_id,
            session_id=session_id,
            tags={"operation": "raw_sql", "has_params": bool(params)},
        ):
            return await super().execute_sql(sql, params)

    async def call_function(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Any:
        """Call database function with query monitoring.

        Args:
            function_name: Database function name
            params: Function parameters
            user_id: User ID for monitoring
            session_id: Session ID for monitoring

        Returns:
            Function result
        """
        if not self._monitoring_enabled:
            return await super().call_function(function_name, params)

        async with self._query_monitor.monitor_query(
            query_type=QueryType.FUNCTION_CALL,
            table_name="function",
            query_text=function_name,
            user_id=user_id,
            session_id=session_id,
            tags={
                "operation": "function_call",
                "function_name": function_name,
                "has_params": bool(params),
            },
        ):
            return await super().call_function(function_name, params)

    # Transaction Support with Monitoring

    @asynccontextmanager
    async def transaction(
        self, user_id: Optional[str] = None, session_id: Optional[str] = None
    ):
        """Transaction context manager with monitoring.

        Args:
            user_id: User ID for monitoring
            session_id: Session ID for monitoring
        """
        if not self._monitoring_enabled:
            async with super().transaction() as tx:
                yield tx
            return

        async with self._query_monitor.monitor_query(
            query_type=QueryType.TRANSACTION,
            table_name="multiple",
            user_id=user_id,
            session_id=session_id,
            tags={"operation": "transaction"},
        ):
            async with super().transaction() as tx:
                yield tx

    # High-level Business Operations with Enhanced Monitoring

    async def create_trip(
        self, trip_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create trip with monitoring."""
        return await self.insert("trips", trip_data, user_id=user_id)

    async def get_trip(
        self, trip_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get trip with monitoring."""
        result = await self.select("trips", "*", {"id": trip_id}, user_id=user_id)
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]

    async def get_user_trips(
        self, user_id: str, session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user trips with monitoring."""
        return await self.select(
            "trips",
            "*",
            {"user_id": user_id},
            order_by="-created_at",
            user_id=user_id,
            session_id=session_id,
        )

    # Performance Monitoring API

    async def get_query_performance_metrics(self) -> Dict[str, Any]:
        """Get query performance metrics."""
        if not self._query_monitor:
            return {"error": "Query monitoring not enabled"}

        return {
            "monitoring_status": await self._query_monitor.get_monitoring_status(),
            "performance_metrics": await self._query_monitor.get_performance_metrics(),
            "slow_queries": len(await self._query_monitor.get_slow_queries(limit=100)),
            "detected_patterns": len(
                await self._query_monitor.get_query_patterns(limit=100)
            ),
            "recent_alerts": len(
                await self._query_monitor.get_performance_alerts(limit=100)
            ),
        }

    async def get_table_performance_report(self, table_name: str) -> Dict[str, Any]:
        """Get performance report for a specific table."""
        if not self._query_monitor:
            return {"error": "Query monitoring not enabled"}

        return await self._query_monitor.get_table_performance(table_name)

    async def get_user_query_report(self, user_id: str) -> Dict[str, Any]:
        """Get query performance report for a specific user."""
        if not self._query_monitor:
            return {"error": "Query monitoring not enabled"}

        return await self._query_monitor.get_user_query_stats(user_id)

    async def get_slow_queries_report(
        self, limit: int = 50, threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get slow queries report."""
        if not self._query_monitor:
            return []

        slow_queries = await self._query_monitor.get_slow_queries(
            limit=limit, threshold=threshold
        )

        return [
            {
                "query_id": query.query_id,
                "table_name": query.table_name,
                "query_type": query.query_type.value,
                "duration": query.duration,
                "timestamp": query.timestamp.isoformat(),
                "user_id": query.user_id,
                "query_text": query.query_text[:200]
                if query.query_text
                else None,  # Truncate for report
                "error_message": query.error_message,
            }
            for query in slow_queries
        ]

    async def get_performance_alerts_report(
        self, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get performance alerts report."""
        if not self._query_monitor:
            return []

        alerts = await self._query_monitor.get_performance_alerts(limit=limit)

        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "table_name": alert.table_name,
                "duration": alert.duration,
                "details": alert.details,
            }
            for alert in alerts
        ]

    # Configuration Management

    def update_monitoring_config(self, **config_updates):
        """Update monitoring configuration."""
        if self._query_monitor:
            self._query_monitor.update_config(**config_updates)
            logger.info(f"Updated monitoring configuration: {config_updates}")
        else:
            logger.warning("Cannot update config: monitoring not enabled")

    def add_performance_alert_callback(self, callback):
        """Add performance alert callback."""
        if self._query_monitor:
            self._query_monitor.add_alert_callback(callback)
        else:
            logger.warning("Cannot add alert callback: monitoring not enabled")


# Global Enhanced Database Service Instance

_enhanced_database_service: Optional[EnhancedDatabaseService] = None


async def get_enhanced_database_service(
    settings: Optional[Settings] = None,
    monitor_config: Optional[QueryMonitorConfig] = None,
    metrics: Optional[DatabaseMetrics] = None,
    enable_monitoring: bool = True,
) -> EnhancedDatabaseService:
    """Get or create global enhanced database service instance.

    Args:
        settings: Application settings
        monitor_config: Query monitoring configuration
        metrics: Database metrics collector
        enable_monitoring: Enable query performance monitoring

    Returns:
        Connected EnhancedDatabaseService instance
    """
    global _enhanced_database_service

    if _enhanced_database_service is None:
        _enhanced_database_service = EnhancedDatabaseService(
            settings=settings,
            monitor_config=monitor_config,
            metrics=metrics,
            enable_monitoring=enable_monitoring,
        )
        await _enhanced_database_service.connect()

    return _enhanced_database_service


async def close_enhanced_database_service() -> None:
    """Close the global enhanced database service instance."""
    global _enhanced_database_service

    if _enhanced_database_service:
        await _enhanced_database_service.close()
        _enhanced_database_service = None
