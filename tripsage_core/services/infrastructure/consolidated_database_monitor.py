"""
Consolidated Database Monitoring for TripSage Core.

This module consolidates all database monitoring functionality into a single,
maintainable module that provides:
- Database connection monitoring with health checks
- Query performance monitoring and slow query detection
- Security monitoring and alert system
- Prometheus metrics integration
- Automatic recovery capabilities

Replaces:
- database_monitor.py (connection monitoring)
- query_monitor.py (performance monitoring)
- key_monitoring_service.py (security monitoring - partial)
- database_metrics.py (metrics collection)
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage_core.config import Settings, get_settings

logger = logging.getLogger(__name__)


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


class QueryStatus(Enum):
    """Query execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    status: HealthStatus
    response_time: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SecurityAlert:
    """Security alert information."""
    event_type: SecurityEvent
    severity: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    ip_address: Optional[str] = None


@dataclass
class QueryExecution:
    """Query execution tracking data."""
    query_id: str
    query_type: QueryType
    table_name: Optional[str]
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: QueryStatus = QueryStatus.SUCCESS
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Calculate duration if end_time is set."""
        if self.end_time is not None and self.duration is None:
            self.duration = self.end_time - self.start_time

    def is_slow(self, threshold: float = 1.0) -> bool:
        """Check if query execution is considered slow."""
        return self.duration is not None and self.duration > threshold

    @property
    def is_successful(self) -> bool:
        """Check if query execution was successful."""
        return self.status == QueryStatus.SUCCESS


class MonitoringConfig(BaseModel):
    """Configuration for consolidated database monitoring."""
    
    # Health monitoring
    health_check_enabled: bool = Field(default=True)
    health_check_interval: float = Field(default=30.0, gt=0)
    response_time_warning_threshold: float = Field(default=5.0, gt=0)
    response_time_critical_threshold: float = Field(default=10.0, gt=0)
    
    # Query monitoring
    query_monitoring_enabled: bool = Field(default=True)
    slow_query_threshold: float = Field(default=1.0, gt=0)
    max_query_history: int = Field(default=1000, gt=0)
    error_rate_threshold: float = Field(default=0.05, ge=0, le=1)
    
    # Security monitoring
    security_monitoring_enabled: bool = Field(default=True)
    security_check_interval: float = Field(default=60.0, gt=0)
    max_security_history: int = Field(default=500, gt=0)
    
    # Recovery settings
    recovery_enabled: bool = Field(default=True)
    max_recovery_attempts: int = Field(default=3, gt=0)
    recovery_delay: float = Field(default=5.0, gt=0)
    
    # Metrics
    metrics_enabled: bool = Field(default=True)
    metrics_export_interval: float = Field(default=10.0, gt=0)


class ConsolidatedDatabaseMonitor:
    """
    Consolidated database monitoring system that provides comprehensive
    monitoring capabilities in a single, maintainable module.
    
    Features:
    - Database connection monitoring with health checks
    - Query performance monitoring and slow query detection
    - Security monitoring and alert system
    - Prometheus metrics integration
    - Automatic recovery capabilities
    """
    
    def __init__(
        self,
        database_service,
        config: Optional[MonitoringConfig] = None,
        settings: Optional[Settings] = None,
        metrics_registry=None,
    ):
        """Initialize consolidated database monitor.
        
        Args:
            database_service: Database service instance to monitor
            config: Monitoring configuration
            settings: Application settings
            metrics_registry: Prometheus metrics registry
        """
        self.database_service = database_service
        self.config = config or MonitoringConfig()
        self.settings = settings or get_settings()
        
        # Initialize metrics if enabled
        self.metrics = None
        if self.config.metrics_enabled:
            try:
                from prometheus_client import Counter, Gauge, Histogram
                self.metrics = self._initialize_metrics(metrics_registry)
            except ImportError:
                logger.warning("Prometheus client not available, metrics disabled")
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Health tracking
        self._last_health_check: Optional[HealthCheckResult] = None
        self._health_history: List[HealthCheckResult] = []
        
        # Query tracking
        self._active_queries: Dict[str, QueryExecution] = {}
        self._query_history: List[QueryExecution] = []
        
        # Security tracking
        self._security_alerts: List[SecurityAlert] = []
        self._failed_connection_count = 0
        self._last_connection_attempt = 0
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[SecurityAlert], None]] = []
        
        logger.info("Consolidated database monitor initialized")
    
    def _initialize_metrics(self, registry):
        """Initialize Prometheus metrics."""
        try:
            from prometheus_client import Counter, Gauge, Histogram
            
            metrics = type('Metrics', (), {})()
            
            # Connection metrics
            metrics.connection_attempts = Counter(
                "tripsage_db_connection_attempts_total",
                "Total database connection attempts",
                ["service", "status"],
                registry=registry,
            )
            
            metrics.active_connections = Gauge(
                "tripsage_db_connections_active",
                "Currently active database connections",
                ["service"],
                registry=registry,
            )
            
            # Query metrics
            metrics.query_duration = Histogram(
                "tripsage_db_query_duration_seconds",
                "Database query execution time",
                ["service", "operation", "table"],
                registry=registry,
                buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
            )
            
            metrics.query_total = Counter(
                "tripsage_db_queries_total",
                "Total database queries executed",
                ["service", "operation", "table", "status"],
                registry=registry,
            )
            
            # Health metrics
            metrics.health_status = Gauge(
                "tripsage_db_health_status",
                "Database health status (1=healthy, 0=unhealthy)",
                ["service"],
                registry=registry,
            )
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus metrics: {e}")
            return None
    
    async def start_monitoring(self):
        """Start comprehensive database monitoring."""
        if self._monitoring:
            logger.warning("Database monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Consolidated database monitoring started")
    
    async def stop_monitoring(self):
        """Stop database monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Consolidated database monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        last_health_check = 0
        last_security_check = 0
        
        while self._monitoring:
            try:
                current_time = time.time()
                
                # Health check
                if (self.config.health_check_enabled and 
                    current_time - last_health_check >= self.config.health_check_interval):
                    await self._perform_health_check()
                    last_health_check = current_time
                
                # Security check
                if (self.config.security_monitoring_enabled and 
                    current_time - last_security_check >= self.config.security_check_interval):
                    await self._perform_security_check()
                    last_security_check = current_time
                
                # Sleep for monitoring interval
                await asyncio.sleep(5.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10.0)
    
    async def _perform_health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check."""
        start_time = time.time()
        
        try:
            # Basic connectivity check
            is_healthy = await self.database_service.health_check()
            response_time = time.time() - start_time
            
            if is_healthy:
                details = await self._collect_health_details()
                status = self._determine_health_status(details, response_time)
                
                result = HealthCheckResult(
                    status=status,
                    response_time=response_time,
                    message=f"Database health check {'passed' if status == HealthStatus.HEALTHY else 'has concerns'}",
                    details=details,
                )
            else:
                result = HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    response_time=response_time,
                    message="Database health check failed - connectivity issue",
                )
                
                if self.config.recovery_enabled:
                    await self._handle_critical_health(result)
        
        except Exception as e:
            response_time = time.time() - start_time
            result = HealthCheckResult(
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Health check error: {str(e)}",
                details={"error": str(e)},
            )
            
            logger.error(f"Health check failed: {e}")
            if self.config.recovery_enabled:
                await self._handle_critical_health(result)
        
        # Update tracking
        self._last_health_check = result
        self._health_history.append(result)
        
        # Trim history
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-100:]
        
        # Update metrics
        if self.metrics:
            self.metrics.health_status.labels(service="supabase").set(
                1 if result.status == HealthStatus.HEALTHY else 0
            )
        
        logger.debug(f"Health check completed: {result.status.value}")
        return result
    
    async def _collect_health_details(self) -> Dict[str, Any]:
        """Collect detailed health information."""
        details = {}
        
        try:
            details["connected"] = self.database_service.is_connected
            
            if self.database_service.is_connected:
                # Test simple query
                start_time = time.time()
                try:
                    await self.database_service.select("users", "id", limit=1)
                    details["query_response_time"] = time.time() - start_time
                except Exception as e:
                    details["query_error"] = str(e)
                    details["query_response_time"] = time.time() - start_time
        
        except Exception as e:
            details["collection_error"] = str(e)
        
        return details
    
    def _determine_health_status(self, details: Dict[str, Any], response_time: float) -> HealthStatus:
        """Determine overall health status."""
        if not details.get("connected", False):
            return HealthStatus.CRITICAL
        
        if "query_error" in details:
            return HealthStatus.CRITICAL
        
        # Check response time thresholds
        if response_time > self.config.response_time_critical_threshold:
            return HealthStatus.CRITICAL
        elif response_time > self.config.response_time_warning_threshold:
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def _handle_critical_health(self, result: HealthCheckResult):
        """Handle critical health status."""
        logger.warning(f"Critical database health detected: {result.message}")
        
        alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="critical",
            message=f"Database health critical: {result.message}",
            details={
                "health_result": {
                    "status": result.status.value,
                    "response_time": result.response_time,
                    "details": result.details,
                }
            },
        )
        
        await self._trigger_alert(alert)
        
        # Attempt recovery if not connected
        if not self.database_service.is_connected:
            await self._attempt_recovery()
    
    async def _perform_security_check(self):
        """Perform security monitoring checks."""
        try:
            await self._check_query_patterns()
            await self._check_error_rates()
            await self._check_connection_patterns()
        except Exception as e:
            logger.error(f"Security check error: {e}")
    
    async def _check_query_patterns(self):
        """Check for suspicious query patterns."""
        # Check for high number of slow queries
        recent_queries = self._query_history[-100:] if self._query_history else []
        slow_queries = [q for q in recent_queries if q.is_slow(self.config.slow_query_threshold)]
        
        if len(slow_queries) > 10:
            alert = SecurityAlert(
                event_type=SecurityEvent.SLOW_QUERY_DETECTED,
                severity="warning",
                message=f"High number of slow queries detected: {len(slow_queries)}",
                details={"slow_query_count": len(slow_queries), "threshold": self.config.slow_query_threshold},
            )
            await self._trigger_alert(alert)
    
    async def _check_error_rates(self):
        """Check for high error rates."""
        recent_queries = self._query_history[-100:] if self._query_history else []
        if not recent_queries:
            return
        
        error_count = len([q for q in recent_queries if not q.is_successful])
        error_rate = error_count / len(recent_queries)
        
        if error_rate > self.config.error_rate_threshold:
            alert = SecurityAlert(
                event_type=SecurityEvent.HIGH_ERROR_RATE,
                severity="warning",
                message=f"High error rate detected: {error_rate:.2%}",
                details={"error_rate": error_rate, "threshold": self.config.error_rate_threshold},
            )
            await self._trigger_alert(alert)
    
    async def _check_connection_patterns(self):
        """Check for suspicious connection patterns."""
        current_time = time.time()
        
        if self._failed_connection_count > 5:
            time_since_last = current_time - self._last_connection_attempt
            
            if time_since_last < 60:
                alert = SecurityAlert(
                    event_type=SecurityEvent.CONNECTION_FAILURE,
                    severity="warning",
                    message=f"Multiple connection failures detected: {self._failed_connection_count}",
                    details={
                        "failed_count": self._failed_connection_count,
                        "time_window": time_since_last,
                    },
                )
                await self._trigger_alert(alert)
    
    async def _attempt_recovery(self):
        """Attempt to recover database connection."""
        logger.info("Attempting database connection recovery")
        
        for attempt in range(self.config.max_recovery_attempts):
            try:
                logger.info(f"Recovery attempt {attempt + 1}/{self.config.max_recovery_attempts}")
                
                await self.database_service.close()
                await asyncio.sleep(self.config.recovery_delay)
                await self.database_service.connect()
                
                if self.database_service.is_connected:
                    logger.info("Database connection recovery successful")
                    
                    alert = SecurityAlert(
                        event_type=SecurityEvent.CONNECTION_FAILURE,
                        severity="info",
                        message=f"Database connection recovered after {attempt + 1} attempts",
                        details={"recovery_attempts": attempt + 1},
                    )
                    await self._trigger_alert(alert)
                    return
            
            except Exception as e:
                logger.error(f"Recovery attempt {attempt + 1} failed: {e}")
                
                if attempt == self.config.max_recovery_attempts - 1:
                    alert = SecurityAlert(
                        event_type=SecurityEvent.CONNECTION_FAILURE,
                        severity="critical",
                        message=f"Database connection recovery failed after {self.config.max_recovery_attempts} attempts",
                        details={
                            "recovery_attempts": self.config.max_recovery_attempts,
                            "last_error": str(e),
                        },
                    )
                    await self._trigger_alert(alert)
    
    async def _trigger_alert(self, alert: SecurityAlert):
        """Trigger security alert."""
        # Add to history
        self._security_alerts.append(alert)
        
        # Trim history
        if len(self._security_alerts) > self.config.max_security_history:
            self._security_alerts = self._security_alerts[-self.config.max_security_history:]
        
        # Log alert
        logger.warning(f"Security alert: {alert.event_type.value} - {alert.message}")
        
        # Call registered callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    # Query monitoring methods
    
    async def track_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
    ) -> str:
        """Start tracking a query execution."""
        if not self.config.query_monitoring_enabled:
            return ""
        
        query_id = f"{int(time.time() * 1000000)}_{id(object())}"
        start_time = time.perf_counter()
        
        execution = QueryExecution(
            query_id=query_id,
            query_type=query_type,
            table_name=table_name,
            start_time=start_time,
        )
        
        self._active_queries[query_id] = execution
        logger.debug(f"Started tracking query {query_id}: {query_type.value}")
        return query_id
    
    async def finish_query(
        self,
        query_id: str,
        status: QueryStatus = QueryStatus.SUCCESS,
        error_message: Optional[str] = None,
        row_count: Optional[int] = None,
    ) -> Optional[QueryExecution]:
        """Finish tracking a query execution."""
        if not query_id:
            return None
        
        end_time = time.perf_counter()
        execution = self._active_queries.pop(query_id, None)
        
        if not execution:
            logger.warning(f"Query execution {query_id} not found")
            return None
        
        execution.end_time = end_time
        execution.duration = end_time - execution.start_time
        execution.status = status
        execution.error_message = error_message
        execution.row_count = row_count
        
        # Maintain history limit
        self._query_history.append(execution)
        if len(self._query_history) > self.config.max_query_history:
            self._query_history = self._query_history[-self.config.max_query_history:]
        
        # Update metrics
        if self.metrics:
            self.metrics.query_duration.labels(
                service="supabase",
                operation=execution.query_type.value,
                table=execution.table_name or "unknown"
            ).observe(execution.duration or 0.0)
            
            self.metrics.query_total.labels(
                service="supabase",
                operation=execution.query_type.value,
                table=execution.table_name or "unknown",
                status=status.value
            ).inc()
        
        # Check for slow queries and alert
        if execution.is_slow(self.config.slow_query_threshold):
            logger.warning(
                f"Slow query detected: {execution.duration:.3f}s "
                f"({execution.query_type.value} on {execution.table_name})"
            )
        
        logger.debug(
            f"Finished tracking query {query_id}: "
            f"duration={execution.duration:.3f}s, status={status.value}"
        )
        return execution
    
    @asynccontextmanager
    async def monitor_query(
        self,
        query_type: QueryType,
        table_name: Optional[str] = None,
    ):
        """Context manager for monitoring query execution."""
        query_id = await self.track_query(query_type, table_name)
        
        success = False
        error_message = None
        
        try:
            yield query_id
            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            await self.finish_query(
                query_id,
                QueryStatus.SUCCESS if success else QueryStatus.ERROR,
                error_message,
            )
    
    # Public interface methods
    
    def add_alert_callback(self, callback: Callable[[SecurityAlert], None]):
        """Add alert callback function."""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[SecurityAlert], None]):
        """Remove alert callback function."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def record_connection_failure(self):
        """Record a connection failure for monitoring."""
        self._failed_connection_count += 1
        self._last_connection_attempt = time.time()
    
    def reset_connection_failures(self):
        """Reset connection failure tracking."""
        self._failed_connection_count = 0
    
    def get_current_health(self) -> Optional[HealthCheckResult]:
        """Get current health status."""
        return self._last_health_check
    
    def get_health_history(self, limit: Optional[int] = None) -> List[HealthCheckResult]:
        """Get health check history."""
        history = self._health_history
        if limit:
            history = history[-limit:]
        return history
    
    def get_security_alerts(self, limit: Optional[int] = None) -> List[SecurityAlert]:
        """Get security alerts."""
        alerts = self._security_alerts
        if limit:
            alerts = alerts[-limit:]
        return alerts
    
    def get_query_history(self, limit: Optional[int] = None) -> List[QueryExecution]:
        """Get query execution history."""
        history = self._query_history
        if limit:
            history = history[-limit:]
        return history
    
    def get_slow_queries(self, threshold: Optional[float] = None) -> List[QueryExecution]:
        """Get slow query executions."""
        threshold = threshold or self.config.slow_query_threshold
        return [
            execution for execution in self._query_history
            if execution.duration and execution.duration >= threshold
        ]
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        return {
            "monitoring_active": self._monitoring,
            "config": {
                "health_check_enabled": self.config.health_check_enabled,
                "health_check_interval": self.config.health_check_interval,
                "query_monitoring_enabled": self.config.query_monitoring_enabled,
                "slow_query_threshold": self.config.slow_query_threshold,
                "security_monitoring_enabled": self.config.security_monitoring_enabled,
                "metrics_enabled": self.config.metrics_enabled,
            },
            "statistics": {
                "health_checks_count": len(self._health_history),
                "queries_tracked": len(self._query_history),
                "security_alerts_count": len(self._security_alerts),
                "failed_connections": self._failed_connection_count,
                "alert_callbacks": len(self._alert_callbacks),
            },
            "last_health_check": (
                {
                    "status": self._last_health_check.status.value,
                    "response_time": self._last_health_check.response_time,
                    "message": self._last_health_check.message,
                    "timestamp": self._last_health_check.timestamp.isoformat(),
                }
                if self._last_health_check
                else None
            ),
        }
    
    async def manual_health_check(self) -> HealthCheckResult:
        """Perform manual health check."""
        return await self._perform_health_check()
    
    async def manual_security_check(self):
        """Perform manual security check."""
        await self._perform_security_check()


# Global consolidated monitor instance
_consolidated_monitor: Optional[ConsolidatedDatabaseMonitor] = None


def get_consolidated_database_monitor(
    database_service=None,
    config: Optional[MonitoringConfig] = None,
    settings: Optional[Settings] = None,
    metrics_registry=None,
) -> ConsolidatedDatabaseMonitor:
    """Get or create global consolidated database monitor instance."""
    global _consolidated_monitor
    
    if _consolidated_monitor is None and database_service is not None:
        _consolidated_monitor = ConsolidatedDatabaseMonitor(
            database_service=database_service,
            config=config,
            settings=settings,
            metrics_registry=metrics_registry,
        )
    
    return _consolidated_monitor


def reset_consolidated_monitor():
    """Reset global consolidated monitor instance (for testing)."""
    global _consolidated_monitor
    _consolidated_monitor = None