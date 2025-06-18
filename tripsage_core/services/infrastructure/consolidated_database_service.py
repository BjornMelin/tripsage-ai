"""
Consolidated Database Service for TripSage Core.

This module provides a unified, high-performance database service that leverages
Supabase platform features including Supavisor connection pooling, RLS security,
and built-in monitoring capabilities.

Key Features:
- Supavisor connection pooling (transaction and session modes)
- Row Level Security (RLS) integration
- Built-in monitoring and metrics
- Vector search operations (pgvector)
- Automatic retry logic and circuit breaker
- Query performance tracking
- Connection health monitoring
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, Field
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)

logger = logging.getLogger(__name__)


class ConnectionMode(Enum):
    """Database connection modes."""
    
    DIRECT = "direct"  # Direct connection (port 5432)
    SESSION = "session"  # Supavisor session mode (port 5432)
    TRANSACTION = "transaction"  # Supavisor transaction mode (port 6543)


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


class HealthStatus(Enum):
    """Database health status levels."""
    
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class QueryMetrics(BaseModel):
    """Query execution metrics."""
    
    query_type: QueryType
    table: Optional[str] = None
    duration_ms: float
    rows_affected: int = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionStats(BaseModel):
    """Connection statistics."""
    
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    connection_errors: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = 0
    queries_executed: int = 0
    avg_query_time_ms: float = 0


class ConsolidatedDatabaseService:
    """
    Unified database service leveraging Supabase platform features.
    
    This service provides:
    - Automatic connection mode selection based on use case
    - Supavisor connection pooling for optimal performance
    - Built-in monitoring and metrics collection
    - Query performance tracking and optimization
    - Automatic retry logic with circuit breaker
    - Vector search operations via pgvector
    - RLS-aware operations with proper role handling
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        default_mode: ConnectionMode = ConnectionMode.TRANSACTION,
        enable_monitoring: bool = True,
        enable_query_cache: bool = True,
        query_timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize consolidated database service.
        
        Args:
            settings: Application settings
            default_mode: Default connection mode
            enable_monitoring: Enable performance monitoring
            enable_query_cache: Enable query result caching
            query_timeout: Default query timeout in seconds
            max_retries: Maximum retry attempts for failed queries
            retry_delay: Delay between retry attempts
        """
        self.settings = settings or get_settings()
        self.default_mode = default_mode
        self.enable_monitoring = enable_monitoring
        self.enable_query_cache = enable_query_cache
        self.query_timeout = query_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Connection management
        self._clients: Dict[ConnectionMode, Optional[Client]] = {
            ConnectionMode.DIRECT: None,
            ConnectionMode.SESSION: None,
            ConnectionMode.TRANSACTION: None,
        }
        self._connected = False
        
        # Monitoring and metrics
        self._start_time = time.time()
        self._query_metrics: List[QueryMetrics] = []
        self._connection_stats = ConnectionStats()
        self._circuit_breaker_open = False
        self._last_error_time: Optional[float] = None
        
        # Query cache (simple in-memory cache)
        self._query_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl = 60.0  # 1 minute default TTL
    
    def _get_connection_url(self, mode: ConnectionMode) -> str:
        """Get connection URL for specified mode.
        
        Args:
            mode: Connection mode
            
        Returns:
            Supabase connection URL
        """
        base_url = self.settings.database_url
        
        if mode == ConnectionMode.DIRECT:
            # Direct connection uses standard URL
            return base_url
        
        # Parse URL to modify for Supavisor
        parsed = urlparse(base_url)
        
        # Extract project ref from hostname
        # Format: https://[project-ref].supabase.co
        hostname_parts = parsed.hostname.split('.')
        if len(hostname_parts) < 2:
            raise CoreDatabaseError(
                message="Invalid Supabase URL format",
                code="INVALID_URL",
                details={"url": base_url}
            )
        
        project_ref = hostname_parts[0]
        
        # Construct Supavisor URL
        # Format: postgres://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:[port]/postgres
        if mode == ConnectionMode.TRANSACTION:
            port = 6543
        else:  # SESSION mode
            port = 5432
        
        # Determine region from settings or default
        region = getattr(self.settings, 'supabase_region', 'us-east-1')
        
        pooler_host = f"aws-0-{region}.pooler.supabase.com"
        
        # Construct new URL with Supavisor host
        supavisor_url = urlunparse((
            parsed.scheme,
            f"{pooler_host}:{port}",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        return supavisor_url
    
    def _create_client_options(self, mode: ConnectionMode) -> ClientOptions:
        """Create client options for specified connection mode.
        
        Args:
            mode: Connection mode
            
        Returns:
            Configured client options
        """
        if mode == ConnectionMode.TRANSACTION:
            # Transaction mode: disable session features
            return ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=self.query_timeout,
            )
        else:
            # Direct/Session mode: enable session features
            return ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
                postgrest_client_timeout=self.query_timeout,
            )
    
    async def connect(self, mode: Optional[ConnectionMode] = None) -> None:
        """Initialize database connection.
        
        Args:
            mode: Connection mode to initialize (None for all modes)
        """
        modes_to_init = [mode] if mode else list(ConnectionMode)
        
        for conn_mode in modes_to_init:
            if self._clients[conn_mode] is not None:
                continue
            
            try:
                url = self._get_connection_url(conn_mode)
                api_key = self.settings.database_public_key.get_secret_value()
                options = self._create_client_options(conn_mode)
                
                # Create Supabase client
                client = create_client(url, api_key, options=options)
                
                # Test connection
                await asyncio.to_thread(
                    lambda: client.table("users").select("id").limit(1).execute()
                )
                
                self._clients[conn_mode] = client
                logger.info(f"Connected to database in {conn_mode.value} mode")
                
            except Exception as e:
                logger.error(f"Failed to connect in {conn_mode.value} mode: {e}")
                self._connection_stats.connection_errors += 1
                self._connection_stats.last_error = str(e)
                
                if mode:  # If specific mode requested, raise error
                    raise CoreDatabaseError(
                        message=f"Failed to connect in {conn_mode.value} mode",
                        code="CONNECTION_FAILED",
                        details={"mode": conn_mode.value, "error": str(e)}
                    ) from e
        
        self._connected = any(client is not None for client in self._clients.values())
        
        if not self._connected:
            raise CoreDatabaseError(
                message="Failed to establish any database connection",
                code="ALL_CONNECTIONS_FAILED"
            )
    
    async def close(self) -> None:
        """Close all database connections."""
        for mode, client in self._clients.items():
            if client:
                try:
                    # Supabase client cleanup
                    self._clients[mode] = None
                    logger.info(f"Closed {mode.value} connection")
                except Exception as e:
                    logger.error(f"Error closing {mode.value} connection: {e}")
        
        self._connected = False
    
    def _select_connection_mode(
        self,
        query_type: QueryType,
        preferred_mode: Optional[ConnectionMode] = None
    ) -> ConnectionMode:
        """Select optimal connection mode for query.
        
        Args:
            query_type: Type of query
            preferred_mode: User-preferred mode
            
        Returns:
            Selected connection mode
        """
        if preferred_mode:
            return preferred_mode
        
        # Use transaction mode for read queries in serverless environments
        if query_type in [QueryType.SELECT, QueryType.COUNT, QueryType.VECTOR_SEARCH]:
            return ConnectionMode.TRANSACTION
        
        # Use session mode for write operations
        if query_type in [QueryType.INSERT, QueryType.UPDATE, QueryType.DELETE, QueryType.UPSERT]:
            return ConnectionMode.SESSION
        
        # Use direct connection for complex operations
        if query_type in [QueryType.TRANSACTION, QueryType.RAW_SQL, QueryType.FUNCTION_CALL]:
            return ConnectionMode.DIRECT
        
        return self.default_mode
    
    async def _get_client(
        self,
        mode: ConnectionMode,
        ensure_connected: bool = True
    ) -> Client:
        """Get client for specified connection mode.
        
        Args:
            mode: Connection mode
            ensure_connected: Ensure connection is established
            
        Returns:
            Supabase client
        """
        if ensure_connected and self._clients[mode] is None:
            await self.connect(mode)
        
        client = self._clients[mode]
        if not client:
            raise CoreServiceError(
                message=f"No {mode.value} connection available",
                code="CONNECTION_NOT_AVAILABLE",
                service="ConsolidatedDatabaseService"
            )
        
        return client
    
    @asynccontextmanager
    async def _track_query(
        self,
        query_type: QueryType,
        table: Optional[str] = None
    ):
        """Context manager for query tracking.
        
        Args:
            query_type: Type of query
            table: Table name
        """
        start_time = time.time()
        metrics = QueryMetrics(query_type=query_type, table=table)
        
        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise
        finally:
            metrics.duration_ms = (time.time() - start_time) * 1000
            
            if self.enable_monitoring:
                self._query_metrics.append(metrics)
                self._connection_stats.queries_executed += 1
                
                # Update average query time
                total_time = sum(m.duration_ms for m in self._query_metrics)
                self._connection_stats.avg_query_time_ms = (
                    total_time / len(self._query_metrics)
                )
    
    async def _execute_with_retry(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute operation with retry logic.
        
        Args:
            operation: Operation to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Operation result
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Check circuit breaker
                if self._circuit_breaker_open:
                    if self._last_error_time and (
                        time.time() - self._last_error_time > 60
                    ):
                        # Reset circuit breaker after 1 minute
                        self._circuit_breaker_open = False
                    else:
                        raise CoreDatabaseError(
                            message="Circuit breaker is open",
                            code="CIRCUIT_BREAKER_OPEN"
                        )
                
                # Execute operation
                result = await operation(*args, **kwargs)
                
                # Reset error tracking on success
                self._last_error_time = None
                return result
                
            except Exception as e:
                last_error = e
                self._last_error_time = time.time()
                
                # Don't retry on certain errors
                if isinstance(e, (CoreResourceNotFoundError, ValueError)):
                    raise
                
                # Open circuit breaker after too many failures
                if attempt >= 2:
                    self._circuit_breaker_open = True
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    logger.warning(
                        f"Retry attempt {attempt + 1} after error: {e}"
                    )
        
        raise last_error
    
    # Core database operations
    
    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        mode: Optional[ConnectionMode] = None,
        use_cache: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Select data from table.
        
        Args:
            table: Table name
            columns: Columns to select
            filters: Filter conditions
            order_by: Order by column (prefix with - for DESC)
            limit: Limit number of results
            offset: Offset for pagination
            mode: Connection mode to use
            use_cache: Whether to use query cache
            
        Returns:
            List of selected records
        """
        # Check cache first
        if use_cache or (use_cache is None and self.enable_query_cache):
            cache_key = f"select:{table}:{columns}:{filters}:{order_by}:{limit}:{offset}"
            if cache_key in self._query_cache:
                result, timestamp = self._query_cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return result
        
        async def _select():
            conn_mode = self._select_connection_mode(QueryType.SELECT, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.SELECT, table) as metrics:
                query = client.table(table).select(columns)
                
                # Apply filters
                if filters:
                    for key, value in filters.items():
                        if isinstance(value, dict):
                            # Complex filters like {"gte": 18}
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
                metrics.rows_affected = len(result.data)
                
                # Cache result
                if use_cache or (use_cache is None and self.enable_query_cache):
                    self._query_cache[cache_key] = (result.data, time.time())
                
                return result.data
        
        return await self._execute_with_retry(_select)
    
    async def insert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        mode: Optional[ConnectionMode] = None,
    ) -> List[Dict[str, Any]]:
        """Insert data into table.
        
        Args:
            table: Table name
            data: Data to insert
            mode: Connection mode to use
            
        Returns:
            List of inserted records
        """
        async def _insert():
            conn_mode = self._select_connection_mode(QueryType.INSERT, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.INSERT, table) as metrics:
                result = await asyncio.to_thread(
                    lambda: client.table(table).insert(data).execute()
                )
                metrics.rows_affected = len(result.data)
                
                # Invalidate cache for this table
                if self.enable_query_cache:
                    self._invalidate_table_cache(table)
                
                return result.data
        
        return await self._execute_with_retry(_insert)
    
    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any],
        mode: Optional[ConnectionMode] = None,
    ) -> List[Dict[str, Any]]:
        """Update data in table.
        
        Args:
            table: Table name
            data: Data to update
            filters: Filter conditions
            mode: Connection mode to use
            
        Returns:
            List of updated records
        """
        async def _update():
            conn_mode = self._select_connection_mode(QueryType.UPDATE, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.UPDATE, table) as metrics:
                query = client.table(table).update(data)
                
                # Apply filters
                for key, value in filters.items():
                    query = query.eq(key, value)
                
                result = await asyncio.to_thread(lambda: query.execute())
                metrics.rows_affected = len(result.data)
                
                # Invalidate cache for this table
                if self.enable_query_cache:
                    self._invalidate_table_cache(table)
                
                return result.data
        
        return await self._execute_with_retry(_update)
    
    async def delete(
        self,
        table: str,
        filters: Dict[str, Any],
        mode: Optional[ConnectionMode] = None,
    ) -> List[Dict[str, Any]]:
        """Delete data from table.
        
        Args:
            table: Table name
            filters: Filter conditions
            mode: Connection mode to use
            
        Returns:
            List of deleted records
        """
        async def _delete():
            conn_mode = self._select_connection_mode(QueryType.DELETE, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.DELETE, table) as metrics:
                query = client.table(table).delete()
                
                # Apply filters
                for key, value in filters.items():
                    query = query.eq(key, value)
                
                result = await asyncio.to_thread(lambda: query.execute())
                metrics.rows_affected = len(result.data)
                
                # Invalidate cache for this table
                if self.enable_query_cache:
                    self._invalidate_table_cache(table)
                
                return result.data
        
        return await self._execute_with_retry(_delete)
    
    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None,
        mode: Optional[ConnectionMode] = None,
    ) -> List[Dict[str, Any]]:
        """Upsert data in table.
        
        Args:
            table: Table name
            data: Data to upsert
            on_conflict: Columns to handle conflict on
            mode: Connection mode to use
            
        Returns:
            List of upserted records
        """
        async def _upsert():
            conn_mode = self._select_connection_mode(QueryType.UPSERT, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.UPSERT, table) as metrics:
                query = client.table(table).upsert(data)
                
                if on_conflict:
                    query = query.on_conflict(on_conflict)
                
                result = await asyncio.to_thread(lambda: query.execute())
                metrics.rows_affected = len(result.data)
                
                # Invalidate cache for this table
                if self.enable_query_cache:
                    self._invalidate_table_cache(table)
                
                return result.data
        
        return await self._execute_with_retry(_upsert)
    
    async def count(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        mode: Optional[ConnectionMode] = None,
    ) -> int:
        """Count records in table.
        
        Args:
            table: Table name
            filters: Filter conditions
            mode: Connection mode to use
            
        Returns:
            Number of records
        """
        async def _count():
            conn_mode = self._select_connection_mode(QueryType.COUNT, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.COUNT, table):
                query = client.table(table).select("*", count="exact")
                
                # Apply filters
                if filters:
                    for key, value in filters.items():
                        query = query.eq(key, value)
                
                result = await asyncio.to_thread(lambda: query.execute())
                return result.count
        
        return await self._execute_with_retry(_count)
    
    # Vector operations
    
    async def vector_search(
        self,
        table: str,
        vector_column: str,
        query_vector: List[float],
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        mode: Optional[ConnectionMode] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search.
        
        Args:
            table: Table name
            vector_column: Vector column name
            query_vector: Query vector
            limit: Number of results
            similarity_threshold: Minimum similarity threshold
            filters: Additional filters
            mode: Connection mode to use
            
        Returns:
            List of similar records with similarity scores
        """
        async def _vector_search():
            conn_mode = self._select_connection_mode(QueryType.VECTOR_SEARCH, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.VECTOR_SEARCH, table) as metrics:
                # Convert vector to string format
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
                    distance_threshold = 1 - similarity_threshold
                    query = query.lt(
                        f"{vector_column} <-> '{vector_str}'", distance_threshold
                    )
                
                # Order by similarity and limit
                query = query.order(f"{vector_column} <-> '{vector_str}'").limit(limit)
                
                result = await asyncio.to_thread(lambda: query.execute())
                metrics.rows_affected = len(result.data)
                
                return result.data
        
        return await self._execute_with_retry(_vector_search)
    
    # Advanced operations
    
    async def call_function(
        self,
        function_name: str,
        params: Optional[Dict[str, Any]] = None,
        mode: Optional[ConnectionMode] = None,
    ) -> Any:
        """Call database function.
        
        Args:
            function_name: Function name
            params: Function parameters
            mode: Connection mode to use
            
        Returns:
            Function result
        """
        async def _call_function():
            conn_mode = self._select_connection_mode(QueryType.FUNCTION_CALL, mode)
            client = await self._get_client(conn_mode)
            
            async with self._track_query(QueryType.FUNCTION_CALL):
                result = await asyncio.to_thread(
                    lambda: client.rpc(function_name, params or {}).execute()
                )
                return result.data
        
        return await self._execute_with_retry(_call_function)
    
    # Monitoring and health
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connections.
        
        Returns:
            Health status for each connection mode
        """
        health_status = {}
        
        for mode in ConnectionMode:
            try:
                client = self._clients[mode]
                if not client:
                    health_status[mode.value] = {
                        "status": HealthStatus.UNKNOWN.value,
                        "message": "Not connected"
                    }
                    continue
                
                start_time = time.time()
                await asyncio.to_thread(
                    lambda: client.table("users").select("id").limit(1).execute()
                )
                response_time = (time.time() - start_time) * 1000
                
                health_status[mode.value] = {
                    "status": HealthStatus.HEALTHY.value,
                    "response_time_ms": response_time
                }
                
            except Exception as e:
                health_status[mode.value] = {
                    "status": HealthStatus.CRITICAL.value,
                    "error": str(e)
                }
        
        return health_status
    
    def get_connection_stats(self) -> ConnectionStats:
        """Get connection statistics.
        
        Returns:
            Current connection statistics
        """
        self._connection_stats.uptime_seconds = time.time() - self._start_time
        
        # Count active connections
        active = sum(1 for client in self._clients.values() if client is not None)
        self._connection_stats.active_connections = active
        self._connection_stats.total_connections = len(self._clients)
        
        return self._connection_stats
    
    def get_query_metrics(
        self,
        query_type: Optional[QueryType] = None,
        limit: int = 100
    ) -> List[QueryMetrics]:
        """Get query metrics.
        
        Args:
            query_type: Filter by query type
            limit: Maximum number of metrics to return
            
        Returns:
            List of query metrics
        """
        metrics = self._query_metrics
        
        if query_type:
            metrics = [m for m in metrics if m.query_type == query_type]
        
        # Return most recent metrics
        return metrics[-limit:]
    
    async def monitor_connections(self) -> Dict[str, Any]:
        """Monitor live database connections.
        
        Returns:
            Connection monitoring data
        """
        # This would typically query pg_stat_activity
        # For now, return basic stats
        return {
            "stats": self.get_connection_stats().dict(),
            "health": await self.health_check(),
            "circuit_breaker_open": self._circuit_breaker_open,
            "cache_size": len(self._query_cache),
        }
    
    def _invalidate_table_cache(self, table: str) -> None:
        """Invalidate cache entries for a table.
        
        Args:
            table: Table name
        """
        keys_to_remove = [
            key for key in self._query_cache
            if key.startswith(f"select:{table}:")
        ]
        
        for key in keys_to_remove:
            del self._query_cache[key]
    
    def clear_cache(self) -> None:
        """Clear all cached query results."""
        self._query_cache.clear()
    
    def set_cache_ttl(self, ttl: float) -> None:
        """Set cache TTL.
        
        Args:
            ttl: Cache TTL in seconds
        """
        self._cache_ttl = ttl
    
    # Business operations (maintaining compatibility)
    
    async def create_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip record."""
        result = await self.insert("trips", trip_data)
        return result[0] if result else {}
    
    async def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Get trip by ID."""
        result = await self.select("trips", "*", {"id": trip_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]
    
    async def get_user_trips(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trips for a user."""
        return await self.select(
            "trips", "*", {"user_id": user_id}, order_by="-created_at"
        )
    
    async def update_trip(
        self, trip_id: str, trip_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update trip record."""
        result = await self.update("trips", trip_data, {"id": trip_id})
        if not result:
            raise CoreResourceNotFoundError(
                message=f"Trip {trip_id} not found",
                details={"resource_id": trip_id, "resource_type": "trip"},
            )
        return result[0]
    
    async def delete_trip(self, trip_id: str) -> bool:
        """Delete trip record."""
        result = await self.delete("trips", {"id": trip_id})
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


# Global service instance
_database_service: Optional[ConsolidatedDatabaseService] = None


async def get_database_service() -> ConsolidatedDatabaseService:
    """Get the global database service instance.
    
    Returns:
        Connected database service instance
    """
    global _database_service
    
    if _database_service is None:
        _database_service = ConsolidatedDatabaseService()
        await _database_service.connect()
    
    return _database_service


async def close_database_service() -> None:
    """Close the global database service instance."""
    global _database_service
    
    if _database_service:
        await _database_service.close()
        _database_service = None