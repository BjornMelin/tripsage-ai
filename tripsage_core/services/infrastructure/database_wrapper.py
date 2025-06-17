"""
Database service wrapper with monitoring integration and feature flags.

This wrapper provides a transparent layer around the database service
with optional monitoring, metrics collection, and graceful degradation.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from tripsage_core.config import Settings, get_settings
from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    get_database_metrics,
)
from tripsage_core.services.infrastructure.database_monitor import (
    ConsolidatedDatabaseMonitor,
    MonitoringConfig,
    QueryType,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService

logger = logging.getLogger(__name__)


class DatabaseServiceWrapper:
    """
    Enhanced database service with monitoring and feature flag support.

    This wrapper provides:
    - Optional monitoring and metrics collection based on feature flags
    - Graceful degradation when monitoring components fail
    - Transparent pass-through to underlying database service
    - Automatic setup and teardown of monitoring components
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize database service wrapper.

        Args:
            settings: Application settings or None to use defaults
        """
        self.settings = settings or get_settings()

        # Core database service
        self.database_service = DatabaseService(settings=self.settings)

        # Optional monitoring components
        self.metrics: Optional[DatabaseMetrics] = None
        self.monitor: Optional[ConsolidatedDatabaseMonitor] = None

        # Initialize monitoring components based on feature flags
        self._initialize_monitoring()

    def _initialize_monitoring(self):
        """Initialize monitoring components based on feature flags."""
        try:
            # Initialize metrics if enabled
            if self.settings.enable_prometheus_metrics:
                self.metrics = get_database_metrics()
                logger.info("Database metrics collection enabled")
            else:
                logger.info("Database metrics collection disabled by feature flag")

            # Initialize monitor if enabled
            if self.settings.enable_database_monitoring:
                monitor_config = MonitoringConfig(
                    health_check_interval=self.settings.db_health_check_interval,
                    security_check_interval=self.settings.db_security_check_interval,
                    max_recovery_attempts=self.settings.db_max_recovery_attempts,
                    recovery_delay=self.settings.db_recovery_delay,
                )

                self.monitor = ConsolidatedDatabaseMonitor(
                    database_service=self.database_service,
                    config=monitor_config,
                    settings=self.settings,
                )

                logger.info("Database connection monitoring enabled")
            else:
                logger.info("Database connection monitoring disabled by feature flag")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring components: {e}")
            # Continue without monitoring if initialization fails
            self.metrics = None
            self.monitor = None

    @property
    def is_connected(self) -> bool:
        """Check if the service is connected to the database."""
        return self.database_service.is_connected

    @property
    def client(self):
        """Get Supabase client, raising error if not connected."""
        return self.database_service.client

    async def connect(self) -> None:
        """Initialize database connection with monitoring."""
        start_time = asyncio.get_event_loop().time()

        try:
            await self.database_service.connect()
            success = True

            # Start monitoring if available
            if self.monitor and self.settings.enable_database_monitoring:
                try:
                    await self.monitor.start_monitoring()
                except Exception as e:
                    logger.error(f"Failed to start database monitoring: {e}")

            # Start metrics server if enabled
            if (
                self.metrics
                and self.settings.enable_metrics_server
                and self.settings.enable_prometheus_metrics
            ):
                try:
                    self.metrics.start_metrics_server(self.settings.metrics_server_port)
                except Exception as e:
                    logger.error(f"Failed to start metrics server: {e}")

        except Exception:
            success = False

            # Record connection failure in monitor
            if self.monitor:
                self.monitor.record_connection_failure()

            raise
        finally:
            # Record connection attempt in metrics
            if self.metrics:
                duration = asyncio.get_event_loop().time() - start_time
                self.metrics.record_connection_attempt("supabase", success, duration)

    async def close(self) -> None:
        """Close database connection and monitoring."""
        # Stop monitoring first
        if self.monitor:
            try:
                await self.monitor.stop_monitoring()
            except Exception as e:
                logger.error(f"Error stopping database monitoring: {e}")

        # Close database connection
        await self.database_service.close()

    async def ensure_connected(self) -> None:
        """Ensure database connection is established."""
        await self.database_service.ensure_connected()

    # Core database operations with optional metrics

    async def insert(
        self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Insert data into table with metrics."""
        if self.metrics and self.settings.enable_prometheus_metrics:
            with self.metrics.time_query("supabase", "INSERT", table):
                return await self.database_service.insert(table, data)
        else:
            return await self.database_service.insert(table, data)

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table with metrics."""
        if self.metrics and self.settings.enable_prometheus_metrics:
            with self.metrics.time_query("supabase", "SELECT", table):
                return await self.database_service.select(
                    table, columns, filters, order_by, limit, offset
                )
        else:
            return await self.database_service.select(
                table, columns, filters, order_by, limit, offset
            )

    async def update(
        self, table: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update data in table with monitoring."""
        if self.monitor and self.monitor.config.query_monitoring_enabled:
            async with self.monitor.monitor_query(QueryType.UPDATE, table):
                return await self.database_service.update(table, data, filters)
        else:
            return await self.database_service.update(table, data, filters)

    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Upsert data in table with monitoring."""
        if self.monitor and self.monitor.config.query_monitoring_enabled:
            async with self.monitor.monitor_query(QueryType.UPSERT, table):
                return await self.database_service.upsert(table, data, on_conflict)
        else:
            return await self.database_service.upsert(table, data, on_conflict)

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete data from table with monitoring."""
        if self.monitor and self.monitor.config.query_monitoring_enabled:
            async with self.monitor.monitor_query(QueryType.DELETE, table):
                return await self.database_service.delete(table, filters)
        else:
            return await self.database_service.delete(table, filters)

    async def count(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in table with monitoring."""
        if self.monitor and self.monitor.config.query_monitoring_enabled:
            async with self.monitor.monitor_query(QueryType.COUNT, table):
                return await self.database_service.count(table, filters)
        else:
            return await self.database_service.count(table, filters)

    # Transaction support with monitoring
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions with monitoring."""
        if self.monitor and self.monitor.config.query_monitoring_enabled:
            async with self.monitor.monitor_query(QueryType.TRANSACTION, None):
                async with self.database_service.transaction() as tx:
                    yield tx
        else:
            async with self.database_service.transaction() as tx:
                yield tx

    # Pass-through methods (delegate to database service)

    async def create_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip record."""
        return await self.database_service.create_trip(trip_data)

    async def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Get trip by ID."""
        return await self.database_service.get_trip(trip_id)

    async def get_user_trips(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trips for a user."""
        return await self.database_service.get_user_trips(user_id)

    async def update_trip(
        self, trip_id: str, trip_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update trip record."""
        return await self.database_service.update_trip(trip_id, trip_data)

    async def delete_trip(self, trip_id: str) -> bool:
        """Delete trip record."""
        return await self.database_service.delete_trip(trip_id)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user record."""
        return await self.database_service.create_user(user_data)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return await self.database_service.get_user(user_id)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        return await self.database_service.get_user_by_email(email)

    async def update_user(
        self, user_id: str, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user record."""
        return await self.database_service.update_user(user_id, user_data)

    async def save_flight_search(self, search_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save flight search parameters."""
        return await self.database_service.save_flight_search(search_data)

    async def save_flight_option(self, option_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save flight option."""
        return await self.database_service.save_flight_option(option_data)

    async def get_user_flight_searches(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's flight searches."""
        return await self.database_service.get_user_flight_searches(user_id)

    async def save_accommodation_search(
        self, search_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save accommodation search parameters."""
        return await self.database_service.save_accommodation_search(search_data)

    async def save_accommodation_option(
        self, option_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save accommodation option."""
        return await self.database_service.save_accommodation_option(option_data)

    async def get_user_accommodation_searches(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """Get user's accommodation searches."""
        return await self.database_service.get_user_accommodation_searches(user_id)

    async def create_chat_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create chat session."""
        return await self.database_service.create_chat_session(session_data)

    async def save_chat_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save chat message."""
        return await self.database_service.save_chat_message(message_data)

    async def get_chat_history(
        self, session_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get chat history for session."""
        return await self.database_service.get_chat_history(session_id, limit)

    async def save_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save API key configuration."""
        return await self.database_service.save_api_key(key_data)

    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's API keys."""
        return await self.database_service.get_user_api_keys(user_id)

    async def get_api_key(
        self, user_id: str, service_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific API key for user and service."""
        return await self.database_service.get_api_key(user_id, service_name)

    async def delete_api_key(self, key_id: str, user_id: str) -> bool:
        """Delete API key by ID with user authorization."""
        return await self.database_service.delete_api_key(key_id, user_id)

    async def delete_api_key_by_service(self, user_id: str, service_name: str) -> bool:
        """Delete API key by service name."""
        return await self.database_service.delete_api_key_by_service(
            user_id, service_name
        )

    async def create_api_key(self, key_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new API key."""
        return await self.database_service.create_api_key(key_data)

    async def get_api_key_for_service(
        self, user_id: str, service: str
    ) -> Optional[Dict[str, Any]]:
        """Get API key for specific service."""
        return await self.database_service.get_api_key_for_service(user_id, service)

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get API key by ID with user authorization."""
        return await self.database_service.get_api_key_by_id(key_id, user_id)

    async def update_api_key_last_used(self, key_id: str) -> bool:
        """Update the last_used timestamp for an API key."""
        return await self.database_service.update_api_key_last_used(key_id)

    async def update_api_key_validation(
        self, key_id: str, is_valid: bool, validated_at
    ) -> bool:
        """Update API key validation status."""
        return await self.database_service.update_api_key_validation(
            key_id, is_valid, validated_at
        )

    async def update_api_key(
        self, key_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an API key with new data."""
        return await self.database_service.update_api_key(key_id, update_data)

    async def log_api_key_usage(self, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log API key usage for audit trail."""
        return await self.database_service.log_api_key_usage(usage_data)

    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        return await self.database_service.vector_search(
            table, vector_column, query_vector, limit, similarity_threshold, filters
        )

    async def vector_search_destinations(
        self,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search destinations using vector similarity."""
        return await self.database_service.vector_search_destinations(
            query_vector, limit, similarity_threshold
        )

    async def save_destination_embedding(
        self, destination_data: Dict[str, Any], embedding: List[float]
    ) -> Dict[str, Any]:
        """Save destination with embedding."""
        return await self.database_service.save_destination_embedding(
            destination_data, embedding
        )

    async def execute_sql(
        self, sql: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        return await self.database_service.execute_sql(sql, params)

    async def call_function(
        self, function_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Call Supabase database function."""
        return await self.database_service.call_function(function_name, params)

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        return await self.database_service.get_user_stats(user_id)

    async def get_popular_destinations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular destinations."""
        return await self.database_service.get_popular_destinations(limit)

    async def health_check(self) -> bool:
        """Check database connectivity."""
        return await self.database_service.health_check()

    async def get_table_info(self, table: str) -> Dict[str, Any]:
        """Get table schema information."""
        return await self.database_service.get_table_info(table)

    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return await self.database_service.get_database_stats()

    async def get_trip_by_id(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Get trip by ID."""
        return await self.database_service.get_trip_by_id(trip_id)

    async def search_trips(
        self, search_filters: Dict[str, Any], limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search trips with text and filters."""
        return await self.database_service.search_trips(search_filters, limit, offset)

    async def get_trip_collaborators(self, trip_id: str) -> List[Dict[str, Any]]:
        """Get trip collaborators."""
        return await self.database_service.get_trip_collaborators(trip_id)

    async def get_trip_related_counts(self, trip_id: str) -> Dict[str, int]:
        """Get counts of related trip data."""
        return await self.database_service.get_trip_related_counts(trip_id)

    async def add_trip_collaborator(
        self, collaborator_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add trip collaborator."""
        return await self.database_service.add_trip_collaborator(collaborator_data)

    async def get_trip_collaborator(
        self, trip_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific trip collaborator."""
        return await self.database_service.get_trip_collaborator(trip_id, user_id)

    # Monitoring access methods

    def get_monitoring_status(self) -> Optional[Dict[str, Any]]:
        """Get monitoring status if monitoring is enabled."""
        if self.monitor and self.settings.enable_database_monitoring:
            return self.monitor.get_monitoring_status()
        return None

    def get_current_health(self):
        """Get current health status if monitoring is enabled."""
        if self.monitor and self.settings.enable_database_monitoring:
            return self.monitor.get_current_health()
        return None

    def get_security_alerts(self, limit: Optional[int] = None):
        """Get security alerts if monitoring is enabled."""
        if self.monitor and self.settings.enable_security_monitoring:
            return self.monitor.get_security_alerts(limit)
        return []

    def get_metrics_summary(self) -> Optional[Dict[str, Any]]:
        """Get metrics summary if metrics are enabled."""
        if (
            self.monitor
            and self.monitor.metrics
            and self.settings.enable_prometheus_metrics
        ):
            return self.monitor.metrics.get_metrics_summary()
        return None

    async def manual_health_check(self):
        """Perform manual health check if monitoring is enabled."""
        if self.monitor and self.settings.enable_database_monitoring:
            return await self.monitor.manual_health_check()
        return None

    async def manual_security_check(self):
        """Perform manual security check if monitoring is enabled."""
        if self.monitor and self.settings.enable_security_monitoring:
            await self.monitor.manual_security_check()


# Global wrapper instance
_database_wrapper: Optional[DatabaseServiceWrapper] = None


async def get_database_wrapper() -> DatabaseServiceWrapper:
    """Get the global database wrapper instance.

    Returns:
        Connected DatabaseServiceWrapper instance
    """
    global _database_wrapper

    if _database_wrapper is None:
        _database_wrapper = DatabaseServiceWrapper()
        await _database_wrapper.connect()

    return _database_wrapper


async def close_database_wrapper() -> None:
    """Close the global database wrapper instance."""
    global _database_wrapper

    if _database_wrapper:
        await _database_wrapper.close()
        _database_wrapper = None
