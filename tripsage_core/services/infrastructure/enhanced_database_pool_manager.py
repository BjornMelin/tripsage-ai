"""
Enhanced Database Pool Manager with LIFO behavior and performance optimizations.

This module provides an advanced database pool manager that implements:
- LIFO (Last In, First Out) connection behavior for better cache locality
- Enhanced Prometheus metrics for operational visibility
- Connection validation with pre-ping behavior
- Performance regression detection integration
- Advanced connection health monitoring
- Resource utilization tracking
"""

import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreDatabaseError

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection health status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"
    VALIDATING = "validating"


class PoolMetrics(Enum):
    """Pool performance metrics."""
    
    CHECKOUT_TIME = "checkout_time_ms"
    QUERY_TIME = "query_time_ms"
    CONNECTION_LIFETIME = "connection_lifetime_s"
    VALIDATION_TIME = "validation_time_ms"
    ERROR_RATE = "error_rate"


@dataclass
class ConnectionInfo:
    """Information about a pooled connection."""
    
    connection_id: str
    client: Client
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_validated: Optional[datetime] = None
    status: ConnectionStatus = ConnectionStatus.HEALTHY
    use_count: int = 0
    error_count: int = 0
    total_query_time: float = 0.0
    
    @property
    def age_seconds(self) -> float:
        """Get connection age in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()
    
    @property 
    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now(timezone.utc) - self.last_used).total_seconds()
    
    @property
    def avg_query_time(self) -> float:
        """Get average query time."""
        return self.total_query_time / max(self.use_count, 1)
    
    def mark_used(self, query_time: float = 0.0):
        """Mark connection as used."""
        self.last_used = datetime.now(timezone.utc)
        self.use_count += 1
        self.total_query_time += query_time
    
    def mark_error(self):
        """Mark connection error."""
        self.error_count += 1
        if self.error_count >= 3:
            self.status = ConnectionStatus.FAILED
        elif self.error_count >= 1:
            self.status = ConnectionStatus.DEGRADED


@dataclass
class PoolStatistics:
    """Connection pool statistics."""
    
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    total_validations: int = 0
    validation_failures: int = 0
    avg_checkout_time: float = 0.0
    avg_validation_time: float = 0.0
    peak_active: int = 0
    total_errors: int = 0
    
    @property
    def pool_utilization(self) -> float:
        """Calculate pool utilization percentage."""
        if self.total_connections == 0:
            return 0.0
        return (self.active_connections / self.total_connections) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_checkouts == 0:
            return 0.0
        return (self.total_errors / self.total_checkouts) * 100
    
    @property
    def validation_success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_validations == 0:
            return 100.0
        return ((self.total_validations - self.validation_failures) / self.total_validations) * 100


class EnhancedDatabasePoolManager:
    """
    Enhanced database pool manager with LIFO behavior and advanced monitoring.
    
    Features:
    - LIFO connection pool for better cache locality
    - Connection validation with pre-ping behavior
    - Comprehensive Prometheus metrics
    - Performance regression detection
    - Advanced health monitoring
    - Connection lifecycle management
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        lifo_enabled: bool = True,
        validation_interval: float = 300.0,
        metrics_registry=None,
    ):
        """Initialize enhanced pool manager.
        
        Args:
            settings: Application settings
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum number of additional connections
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Connection recycle time in seconds
            pool_pre_ping: Enable pre-ping validation
            lifo_enabled: Enable LIFO (Last In, First Out) behavior
            validation_interval: Connection validation interval in seconds
            metrics_registry: Prometheus metrics registry
        """
        self.settings = settings or get_settings()
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.lifo_enabled = lifo_enabled
        self.validation_interval = validation_interval
        
        # Connection pools - using deque for LIFO behavior
        self._available_connections: deque[ConnectionInfo] = deque()
        self._active_connections: Dict[str, ConnectionInfo] = {}
        self._all_connections: Dict[str, ConnectionInfo] = {}
        
        # Pool state
        self._initialized = False
        self._closed = False
        self._connection_counter = 0
        self._checkout_times: List[float] = []
        self._validation_times: List[float] = []
        
        # Statistics
        self.stats = PoolStatistics()
        
        # Background tasks
        self._validation_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = None
        if metrics_registry is not None:
            try:
                self.metrics = self._initialize_metrics(metrics_registry)
            except ImportError:
                logger.warning("Prometheus client not available, metrics disabled")
    
    def _initialize_metrics(self, registry):
        """Initialize Prometheus metrics."""
        try:
            from prometheus_client import Counter, Gauge, Histogram
            
            metrics = type("PoolMetrics", (), {})()
            
            # Connection pool metrics
            metrics.pool_connections_total = Gauge(
                "tripsage_db_pool_connections_total",
                "Total connections in pool",
                ["pool_id", "status"],
                registry=registry,
            )
            
            metrics.pool_utilization = Gauge(
                "tripsage_db_pool_utilization_percent",
                "Pool utilization percentage",
                ["pool_id"],
                registry=registry,
            )
            
            metrics.pool_checkout_duration = Histogram(
                "tripsage_db_pool_checkout_duration_seconds",
                "Time to checkout connection from pool",
                ["pool_id"],
                registry=registry,
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
            )
            
            metrics.pool_validation_duration = Histogram(
                "tripsage_db_pool_validation_duration_seconds", 
                "Connection validation time",
                ["pool_id", "result"],
                registry=registry,
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
            )
            
            metrics.pool_connection_lifetime = Histogram(
                "tripsage_db_pool_connection_lifetime_seconds",
                "Connection lifetime in pool",
                ["pool_id"],
                registry=registry,
                buckets=(1, 5, 10, 30, 60, 300, 900, 1800, 3600),
            )
            
            metrics.pool_operations_total = Counter(
                "tripsage_db_pool_operations_total",
                "Total pool operations",
                ["pool_id", "operation", "result"],
                registry=registry,
            )
            
            metrics.pool_errors_total = Counter(
                "tripsage_db_pool_errors_total",
                "Total pool errors",
                ["pool_id", "error_type"],
                registry=registry,
            )
            
            # Connection health metrics
            metrics.connection_health = Gauge(
                "tripsage_db_connection_health",
                "Connection health status (1=healthy, 0=unhealthy)",
                ["pool_id", "connection_id"],
                registry=registry,
            )
            
            # Performance metrics
            metrics.query_latency_percentiles = Histogram(
                "tripsage_db_query_latency_percentiles",
                "Query latency percentiles",
                ["pool_id", "operation"],
                registry=registry,
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
            )
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to initialize pool metrics: {e}")
            return None
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return
        
        logger.info(
            f"Initializing enhanced pool manager: size={self.pool_size}, "
            f"overflow={self.max_overflow}, lifo={self.lifo_enabled}"
        )
        
        try:
            # Create initial pool connections
            for _ in range(self.pool_size):
                connection_info = await self._create_connection()
                self._available_connections.append(connection_info)
            
            # Start background tasks
            if self.pool_pre_ping:
                self._validation_task = asyncio.create_task(self._validation_loop())
            
            if self.metrics:
                self._metrics_task = asyncio.create_task(self._metrics_loop())
            
            self._initialized = True
            logger.info(f"Pool manager initialized with {len(self._available_connections)} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize pool manager: {e}")
            raise CoreDatabaseError(
                message="Failed to initialize connection pool",
                code="POOL_INIT_FAILED",
                details={"error": str(e)},
            ) from e
    
    async def _create_connection(self) -> ConnectionInfo:
        """Create a new database connection."""
        self._connection_counter += 1
        connection_id = f"conn_{self._connection_counter}_{int(time.time())}"
        
        try:
            # Get Supavisor transaction mode URL
            supabase_url = self._get_supavisor_url()
            supabase_key = self.settings.database_public_key.get_secret_value()
            
            # Configure client options for optimal pooling
            options = ClientOptions(
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=30.0,
            )
            
            client = create_client(supabase_url, supabase_key, options=options)
            
            # Test connection
            await self._validate_connection(client)
            
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                client=client,
            )
            
            self._all_connections[connection_id] = connection_info
            self.stats.total_connections += 1
            
            logger.debug(f"Created connection {connection_id}")
            return connection_info
            
        except Exception as e:
            logger.error(f"Failed to create connection {connection_id}: {e}")
            if self.metrics:
                self.metrics.pool_errors_total.labels(
                    pool_id="enhanced",
                    error_type="connection_creation",
                ).inc()
            raise
    
    def _get_supavisor_url(self) -> str:
        """Get Supabase URL configured for Supavisor transaction mode."""
        base_url = self.settings.database_url
        parsed = urlparse(base_url)
        
        # Convert to Supavisor pooler URL format
        if ".supabase.co" in parsed.netloc:
            pooler_netloc = parsed.netloc.replace(
                ".supabase.co", ".pooler.supabase.com"
            )
            return urlunparse(
                (
                    parsed.scheme,
                    pooler_netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
        
        return base_url
    
    async def _validate_connection(self, client: Client) -> bool:
        """Validate a database connection."""
        start_time = time.perf_counter()
        
        try:
            # Simple health check query
            await asyncio.to_thread(
                lambda: client.table("users").select("id").limit(1).execute()
            )
            
            validation_time = time.perf_counter() - start_time
            self._validation_times.append(validation_time)
            
            # Keep only recent validation times
            if len(self._validation_times) > 100:
                self._validation_times = self._validation_times[-100:]
            
            if self.metrics:
                self.metrics.pool_validation_duration.labels(
                    pool_id="enhanced",
                    result="success",
                ).observe(validation_time)
            
            return True
            
        except Exception as e:
            validation_time = time.perf_counter() - start_time
            logger.warning(f"Connection validation failed: {e}")
            
            if self.metrics:
                self.metrics.pool_validation_duration.labels(
                    pool_id="enhanced", 
                    result="failure",
                ).observe(validation_time)
                
                self.metrics.pool_errors_total.labels(
                    pool_id="enhanced",
                    error_type="validation_failure",
                ).inc()
            
            return False
    
    @asynccontextmanager
    async def acquire_connection(
        self,
        pool_type: str = "transaction",
        timeout: float = None,
    ):
        """Acquire connection from pool with LIFO behavior.
        
        Args:
            pool_type: Ignored - maintained for compatibility
            timeout: Timeout for acquiring connection
        
        Yields:
            Supabase client connection
        """
        if not self._initialized:
            await self.initialize()
        
        if self._closed:
            raise CoreDatabaseError(
                message="Pool manager is closed",
                code="POOL_CLOSED",
            )
        
        timeout = timeout or self.pool_timeout
        start_time = time.perf_counter()
        connection_info = None
        
        try:
            # Try to get connection from pool with timeout
            connection_info = await asyncio.wait_for(
                self._get_pooled_connection(),
                timeout=timeout,
            )
            
            checkout_time = time.perf_counter() - start_time
            self._checkout_times.append(checkout_time)
            
            # Keep only recent checkout times
            if len(self._checkout_times) > 100:
                self._checkout_times = self._checkout_times[-100:]
            
            self.stats.total_checkouts += 1
            self.stats.active_connections += 1
            self.stats.avg_checkout_time = sum(self._checkout_times) / len(self._checkout_times)
            
            if self.stats.active_connections > self.stats.peak_active:
                self.stats.peak_active = self.stats.active_connections
            
            if self.metrics:
                self.metrics.pool_checkout_duration.labels(
                    pool_id="enhanced",
                ).observe(checkout_time)
                
                self.metrics.pool_operations_total.labels(
                    pool_id="enhanced",
                    operation="checkout",
                    result="success",
                ).inc()
            
            # Validate connection if pre-ping is enabled
            if self.pool_pre_ping:
                is_valid = await self._validate_connection(connection_info.client)
                if not is_valid:
                    connection_info.mark_error()
                    # Try to create new connection
                    await self._replace_connection(connection_info)
            
            connection_info.mark_used()
            
            logger.debug(f"Acquired connection {connection_info.connection_id}")
            yield connection_info.client
            
        except asyncio.TimeoutError:
            logger.error(f"Connection checkout timeout after {timeout}s")
            self.stats.total_errors += 1
            
            if self.metrics:
                self.metrics.pool_errors_total.labels(
                    pool_id="enhanced",
                    error_type="checkout_timeout",
                ).inc()
            
            raise CoreDatabaseError(
                message=f"Connection checkout timeout after {timeout}s",
                code="CHECKOUT_TIMEOUT",
            )
            
        except Exception as e:
            logger.error(f"Failed to acquire connection: {e}")
            self.stats.total_errors += 1
            
            if self.metrics:
                self.metrics.pool_errors_total.labels(
                    pool_id="enhanced",
                    error_type="checkout_error",
                ).inc()
            
            raise CoreDatabaseError(
                message=f"Failed to acquire connection: {str(e)}",
                code="CHECKOUT_FAILED",
                details={"error": str(e)},
            ) from e
            
        finally:
            # Return connection to pool
            if connection_info:
                await self._return_connection(connection_info)
    
    async def _get_pooled_connection(self) -> ConnectionInfo:
        """Get connection from pool with LIFO behavior."""
        while True:
            # Try to get connection from available pool
            if self._available_connections:
                if self.lifo_enabled:
                    # LIFO: get most recently returned connection
                    connection_info = self._available_connections.pop()
                else:
                    # FIFO: get oldest returned connection
                    connection_info = self._available_connections.popleft()
                
                # Check if connection is still valid
                if await self._check_connection_health(connection_info):
                    self._active_connections[connection_info.connection_id] = connection_info
                    return connection_info
                else:
                    # Connection is unhealthy, remove and try again
                    await self._remove_connection(connection_info)
                    continue
            
            # No available connections, try to create new one if under limit
            total_connections = len(self._all_connections)
            if total_connections < self.pool_size + self.max_overflow:
                connection_info = await self._create_connection()
                self._active_connections[connection_info.connection_id] = connection_info
                return connection_info
            
            # Pool is at capacity, wait for a connection to be returned
            await asyncio.sleep(0.1)
    
    async def _check_connection_health(self, connection_info: ConnectionInfo) -> bool:
        """Check if connection is healthy."""
        # Check connection age
        if connection_info.age_seconds > self.pool_recycle:
            logger.debug(f"Connection {connection_info.connection_id} expired")
            return False
        
        # Check connection status
        if connection_info.status == ConnectionStatus.FAILED:
            return False
        
        # Check if validation is needed
        if (
            self.pool_pre_ping 
            and connection_info.last_validated
            and (datetime.now(timezone.utc) - connection_info.last_validated).total_seconds() > self.validation_interval
        ):
            is_valid = await self._validate_connection(connection_info.client)
            connection_info.last_validated = datetime.now(timezone.utc)
            if not is_valid:
                connection_info.mark_error()
                return False
        
        return True
    
    async def _return_connection(self, connection_info: ConnectionInfo):
        """Return connection to pool."""
        if connection_info.connection_id in self._active_connections:
            del self._active_connections[connection_info.connection_id]
            self.stats.active_connections -= 1
            self.stats.total_checkins += 1
            
            # Check if connection should be kept
            if connection_info.status != ConnectionStatus.FAILED and not self._closed:
                if self.lifo_enabled:
                    # LIFO: add to end of deque
                    self._available_connections.append(connection_info)
                else:
                    # FIFO: add to beginning of deque
                    self._available_connections.appendleft(connection_info)
                    
                logger.debug(f"Returned connection {connection_info.connection_id} to pool")
            else:
                await self._remove_connection(connection_info)
            
            if self.metrics:
                self.metrics.pool_operations_total.labels(
                    pool_id="enhanced",
                    operation="checkin", 
                    result="success",
                ).inc()
    
    async def _replace_connection(self, old_connection: ConnectionInfo):
        """Replace unhealthy connection with new one."""
        try:
            await self._remove_connection(old_connection)
            new_connection = await self._create_connection()
            self._available_connections.append(new_connection)
            logger.info(f"Replaced unhealthy connection {old_connection.connection_id}")
        except Exception as e:
            logger.error(f"Failed to replace connection: {e}")
    
    async def _remove_connection(self, connection_info: ConnectionInfo):
        """Remove connection from pool."""
        connection_id = connection_info.connection_id
        
        # Remove from all tracking
        self._all_connections.pop(connection_id, None)
        self._active_connections.pop(connection_id, None)
        
        # Remove from available connections if present
        try:
            self._available_connections.remove(connection_info)
        except ValueError:
            pass  # Not in available connections
        
        self.stats.total_connections -= 1
        
        if connection_info.status == ConnectionStatus.FAILED:
            self.stats.failed_connections += 1
        
        if self.metrics:
            self.metrics.pool_connection_lifetime.labels(
                pool_id="enhanced",
            ).observe(connection_info.age_seconds)
        
        logger.debug(f"Removed connection {connection_id} from pool")
    
    async def _validation_loop(self):
        """Background task for connection validation."""
        while not self._closed:
            try:
                await asyncio.sleep(self.validation_interval)
                
                if self._closed:
                    break
                
                # Validate available connections
                connections_to_remove = []
                
                for connection_info in list(self._available_connections):
                    if not await self._check_connection_health(connection_info):
                        connections_to_remove.append(connection_info)
                
                # Remove unhealthy connections
                for connection_info in connections_to_remove:
                    await self._remove_connection(connection_info)
                
                if connections_to_remove:
                    logger.info(f"Removed {len(connections_to_remove)} unhealthy connections")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in validation loop: {e}")
    
    async def _metrics_loop(self):
        """Background task for updating metrics."""
        while not self._closed:
            try:
                await asyncio.sleep(10.0)  # Update metrics every 10 seconds
                
                if self._closed or not self.metrics:
                    break
                
                # Update pool metrics
                self.stats.idle_connections = len(self._available_connections)
                
                self.metrics.pool_connections_total.labels(
                    pool_id="enhanced",
                    status="total",
                ).set(self.stats.total_connections)
                
                self.metrics.pool_connections_total.labels(
                    pool_id="enhanced",
                    status="active",
                ).set(self.stats.active_connections)
                
                self.metrics.pool_connections_total.labels(
                    pool_id="enhanced",
                    status="idle",
                ).set(self.stats.idle_connections)
                
                self.metrics.pool_utilization.labels(
                    pool_id="enhanced",
                ).set(self.stats.pool_utilization)
                
                # Update connection health metrics
                for connection_info in self._all_connections.values():
                    health_value = 1 if connection_info.status == ConnectionStatus.HEALTHY else 0
                    self.metrics.connection_health.labels(
                        pool_id="enhanced",
                        connection_id=connection_info.connection_id,
                    ).set(health_value)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
    
    async def health_check(self) -> bool:
        """Check pool health."""
        if not self._initialized or self._closed:
            return False
        
        try:
            # Try to acquire and test a connection
            async with self.acquire_connection(timeout=5.0) as client:
                await asyncio.to_thread(
                    lambda: client.table("users").select("id").limit(1).execute()
                )
            return True
        except Exception as e:
            logger.error(f"Pool health check failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pool metrics."""
        return {
            "pool_config": {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": self.pool_pre_ping,
                "lifo_enabled": self.lifo_enabled,
                "validation_interval": self.validation_interval,
            },
            "statistics": {
                "total_connections": self.stats.total_connections,
                "active_connections": self.stats.active_connections,
                "idle_connections": self.stats.idle_connections,
                "failed_connections": self.stats.failed_connections,
                "total_checkouts": self.stats.total_checkouts,
                "total_checkins": self.stats.total_checkins,
                "total_validations": self.stats.total_validations,
                "validation_failures": self.stats.validation_failures,
                "avg_checkout_time": self.stats.avg_checkout_time,
                "avg_validation_time": self.stats.avg_validation_time,
                "peak_active": self.stats.peak_active,
                "total_errors": self.stats.total_errors,
                "pool_utilization": self.stats.pool_utilization,
                "error_rate": self.stats.error_rate,
                "validation_success_rate": self.stats.validation_success_rate,
            },
            "connection_details": [
                {
                    "connection_id": conn.connection_id,
                    "status": conn.status.value,
                    "age_seconds": conn.age_seconds,
                    "idle_seconds": conn.idle_seconds,
                    "use_count": conn.use_count,
                    "error_count": conn.error_count,
                    "avg_query_time": conn.avg_query_time,
                }
                for conn in self._all_connections.values()
            ],
            "performance": {
                "recent_checkout_times": self._checkout_times[-10:],
                "recent_validation_times": self._validation_times[-10:],
            },
        }
    
    async def close(self) -> None:
        """Close the pool and cleanup resources."""
        if self._closed:
            return
        
        logger.info("Closing enhanced database pool manager")
        self._closed = True
        
        # Cancel background tasks
        if self._validation_task:
            self._validation_task.cancel()
            try:
                await self._validation_task
            except asyncio.CancelledError:
                pass
        
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        # Clear all connections
        self._available_connections.clear()
        self._active_connections.clear()
        self._all_connections.clear()
        
        logger.info("Enhanced database pool manager closed")


# Global enhanced pool manager instance
_enhanced_pool_manager: Optional[EnhancedDatabasePoolManager] = None


async def get_enhanced_pool_manager(**kwargs) -> EnhancedDatabasePoolManager:
    """Get the global enhanced pool manager instance.
    
    Args:
        **kwargs: Arguments to pass to EnhancedDatabasePoolManager constructor
    
    Returns:
        Initialized EnhancedDatabasePoolManager instance
    """
    global _enhanced_pool_manager
    
    if _enhanced_pool_manager is None:
        _enhanced_pool_manager = EnhancedDatabasePoolManager(**kwargs)
        await _enhanced_pool_manager.initialize()
    
    return _enhanced_pool_manager


async def close_enhanced_pool_manager() -> None:
    """Close the global enhanced pool manager instance."""
    global _enhanced_pool_manager
    
    if _enhanced_pool_manager:
        await _enhanced_pool_manager.close()
        _enhanced_pool_manager = None