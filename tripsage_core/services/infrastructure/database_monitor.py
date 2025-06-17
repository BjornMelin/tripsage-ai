"""
Database Connection Monitor for TripSage Core.

Provides real-time monitoring of database connections, health checks,
security monitoring, and automatic recovery capabilities.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from tripsage_core.config import Settings, get_settings
from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    get_database_metrics,
)

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
    AUTHENTICATION_FAILURE = "auth_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    status: HealthStatus
    response_time: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class SecurityAlert:
    """Security alert information."""

    event_type: SecurityEvent
    severity: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class DatabaseConnectionMonitor:
    """
    Comprehensive database connection monitor with health checks,
    security monitoring, and automatic recovery capabilities.

    Features:
    - Real-time health monitoring
    - Connection pool monitoring
    - Security event detection
    - Automatic recovery attempts
    - Metrics collection
    - Alert notifications
    """

    def __init__(
        self,
        database_service,
        settings: Optional[Settings] = None,
        metrics: Optional[DatabaseMetrics] = None,
    ):
        """Initialize database connection monitor.

        Args:
            database_service: Database service instance to monitor
            settings: Application settings
            metrics: Metrics collector instance
        """
        self.database_service = database_service
        self.settings = settings or get_settings()
        self.metrics = metrics or get_database_metrics()

        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_check_interval = self.settings.db_health_check_interval
        self._security_check_interval = self.settings.db_security_check_interval

        # Health tracking
        self._last_health_check: Optional[HealthCheckResult] = None
        self._health_history: List[HealthCheckResult] = []
        self._max_health_history = 100

        # Security tracking
        self._security_alerts: List[SecurityAlert] = []
        self._max_security_history = 500
        self._failed_connection_count = 0
        self._last_connection_attempt = 0

        # Alert callbacks
        self._alert_callbacks: List[Callable[[SecurityAlert], None]] = []

        # Recovery settings
        self._max_recovery_attempts = self.settings.db_max_recovery_attempts
        self._recovery_delay = self.settings.db_recovery_delay

        logger.info("Database connection monitor initialized")

    async def start_monitoring(self):
        """Start continuous database monitoring."""
        if self._monitoring:
            logger.warning("Database monitoring already started")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Database monitoring started")

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

        logger.info("Database monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        last_health_check = 0
        last_security_check = 0

        while self._monitoring:
            try:
                current_time = time.time()

                # Health check
                if current_time - last_health_check >= self._health_check_interval:
                    await self._perform_health_check()
                    last_health_check = current_time

                # Security check
                if current_time - last_security_check >= self._security_check_interval:
                    await self._perform_security_check()
                    last_security_check = current_time

                # Sleep for a short interval
                await asyncio.sleep(5.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(10.0)  # Longer sleep on error

    async def _perform_health_check(self) -> HealthCheckResult:
        """Perform comprehensive health check."""
        start_time = time.time()

        try:
            # Basic connectivity check
            is_healthy = await self.database_service.health_check()
            response_time = time.time() - start_time

            if is_healthy:
                # Additional health checks
                details = await self._collect_health_details()

                status = self._determine_health_status(details)
                result = HealthCheckResult(
                    status=status,
                    response_time=response_time,
                    message=(
                        f"Database health check "
                        f"{'passed' if status == HealthStatus.HEALTHY else 'has concerns'}"  # noqa: E501
                    ),
                    details=details,
                )
            else:
                result = HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    response_time=response_time,
                    message="Database health check failed - connectivity issue",
                )

                # Trigger recovery if critical
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
            await self._handle_critical_health(result)

        # Update tracking
        self._last_health_check = result
        self._health_history.append(result)

        # Trim history
        if len(self._health_history) > self._max_health_history:
            self._health_history = self._health_history[-self._max_health_history :]

        # Update metrics
        self.metrics.record_health_check(
            "supabase",
            result.status == HealthStatus.HEALTHY,
        )

        logger.debug(f"Health check completed: {result.status.value}")
        return result

    async def _collect_health_details(self) -> Dict[str, Any]:
        """Collect detailed health information."""
        details = {}

        try:
            # Connection status
            details["connected"] = self.database_service.is_connected

            # Database stats (if available)
            if self.database_service.is_connected:
                try:
                    stats = await self.database_service.get_database_stats()
                    details["database_stats"] = stats
                except Exception as e:
                    details["stats_error"] = str(e)

            # Response time for simple query
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

    def _determine_health_status(self, details: Dict[str, Any]) -> HealthStatus:
        """Determine overall health status based on details."""
        if not details.get("connected", False):
            return HealthStatus.CRITICAL

        if "query_error" in details:
            return HealthStatus.CRITICAL

        # Check response time
        query_time = details.get("query_response_time", 0)
        if query_time > 5.0:  # 5 seconds threshold
            return HealthStatus.WARNING
        elif query_time > 10.0:  # 10 seconds threshold
            return HealthStatus.CRITICAL

        # Check database stats if available
        if "database_stats" in details:
            details["database_stats"]
            # Add additional checks based on stats

        return HealthStatus.HEALTHY

    async def _handle_critical_health(self, result: HealthCheckResult):
        """Handle critical health status."""
        logger.warning(f"Critical database health detected: {result.message}")

        # Create security alert
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

        # Attempt recovery
        if not self.database_service.is_connected:
            await self._attempt_recovery()

    async def _perform_security_check(self):
        """Perform security monitoring checks."""
        try:
            # Check for suspicious patterns
            await self._check_connection_patterns()
            await self._check_query_patterns()

            # Monitor for rate limiting
            await self._check_rate_limits()

        except Exception as e:
            logger.error(f"Security check error: {e}")

    async def _check_connection_patterns(self):
        """Check for suspicious connection patterns."""
        current_time = time.time()

        # Check for rapid connection failures
        if self._failed_connection_count > 5:  # threshold
            time_since_last = current_time - self._last_connection_attempt

            if time_since_last < 60:  # within 1 minute
                alert = SecurityAlert(
                    event_type=SecurityEvent.CONNECTION_FAILURE,
                    severity="warning",
                    message=(
                        f"Multiple connection failures detected: "
                        f"{self._failed_connection_count}"
                    ),
                    details={
                        "failed_count": self._failed_connection_count,
                        "time_window": time_since_last,
                    },
                )
                await self._trigger_alert(alert)

    async def _check_query_patterns(self):
        """Check for suspicious query patterns."""
        # This would typically analyze query logs
        # For now, we'll implement basic monitoring

        # Check metrics for error rates
        metrics_summary = self.metrics.get_metrics_summary()

        query_errors = metrics_summary.get("query_errors", {})
        total_errors = sum(query_errors.values()) if query_errors else 0

        if total_errors > 10:  # threshold
            alert = SecurityAlert(
                event_type=SecurityEvent.SUSPICIOUS_QUERY,
                severity="warning",
                message=f"High query error rate detected: {total_errors} errors",
                details={"error_count": total_errors, "errors": query_errors},
            )
            await self._trigger_alert(alert)

    async def _check_rate_limits(self):
        """Check for rate limit violations."""
        # Monitor query frequency
        metrics_summary = self.metrics.get_metrics_summary()

        query_total = metrics_summary.get("query_total", {})
        total_queries = sum(query_total.values()) if query_total else 0

        # Simple rate check (would be more sophisticated in production)
        if total_queries > 1000:  # threshold per monitoring interval
            alert = SecurityAlert(
                event_type=SecurityEvent.RATE_LIMIT_EXCEEDED,
                severity="warning",
                message=f"High query rate detected: {total_queries} queries",
                details={"query_count": total_queries},
            )
            await self._trigger_alert(alert)

    async def _attempt_recovery(self):
        """Attempt to recover database connection."""
        logger.info("Attempting database connection recovery")

        for attempt in range(self._max_recovery_attempts):
            try:
                logger.info(
                    f"Recovery attempt {attempt + 1}/{self._max_recovery_attempts}"
                )

                # Close existing connection
                await self.database_service.close()

                # Wait before retry
                await asyncio.sleep(self._recovery_delay)

                # Attempt to reconnect
                await self.database_service.connect()

                if self.database_service.is_connected:
                    logger.info("Database connection recovery successful")

                    # Record successful recovery
                    alert = SecurityAlert(
                        event_type=SecurityEvent.CONNECTION_FAILURE,
                        severity="info",
                        message=(
                            f"Database connection recovered after {attempt + 1} attempts"  # noqa: E501
                        ),
                        details={"recovery_attempts": attempt + 1},
                    )
                    await self._trigger_alert(alert)
                    return

            except Exception as e:
                logger.error(f"Recovery attempt {attempt + 1} failed: {e}")

                if attempt == self._max_recovery_attempts - 1:
                    # Final attempt failed
                    alert = SecurityAlert(
                        event_type=SecurityEvent.CONNECTION_FAILURE,
                        severity="critical",
                        message=(
                            f"Database connection recovery failed after "
                            f"{self._max_recovery_attempts} attempts"
                        ),
                        details={
                            "recovery_attempts": self._max_recovery_attempts,
                            "last_error": str(e),
                        },
                    )
                    await self._trigger_alert(alert)

    async def _trigger_alert(self, alert: SecurityAlert):
        """Trigger security alert."""
        # Add to history
        self._security_alerts.append(alert)

        # Trim history
        if len(self._security_alerts) > self._max_security_history:
            self._security_alerts = self._security_alerts[-self._max_security_history :]

        # Log alert
        logger.warning(f"Security alert: {alert.event_type.value} - {alert.message}")

        # Call registered callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def add_alert_callback(self, callback: Callable[[SecurityAlert], None]):
        """Add alert callback function.

        Args:
            callback: Function to call when alerts are triggered
        """
        self._alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[SecurityAlert], None]):
        """Remove alert callback function.

        Args:
            callback: Function to remove
        """
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    def record_connection_failure(self):
        """Record a connection failure for monitoring."""
        self._failed_connection_count += 1
        self._last_connection_attempt = time.time()

    def reset_connection_failures(self):
        """Reset connection failure tracking."""
        self._failed_connection_count = 0

    # Status and reporting methods

    def get_current_health(self) -> Optional[HealthCheckResult]:
        """Get current health status."""
        return self._last_health_check

    def get_health_history(
        self, limit: Optional[int] = None
    ) -> List[HealthCheckResult]:
        """Get health check history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of health check results
        """
        history = self._health_history
        if limit:
            history = history[-limit:]
        return history

    def get_security_alerts(self, limit: Optional[int] = None) -> List[SecurityAlert]:
        """Get security alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of security alerts
        """
        alerts = self._security_alerts
        if limit:
            alerts = alerts[-limit:]
        return alerts

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get overall monitoring status.

        Returns:
            Dictionary with monitoring information
        """
        return {
            "monitoring_active": self._monitoring,
            "health_check_interval": self._health_check_interval,
            "security_check_interval": self._security_check_interval,
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
            "health_history_count": len(self._health_history),
            "security_alerts_count": len(self._security_alerts),
            "failed_connection_count": self._failed_connection_count,
            "alert_callbacks_count": len(self._alert_callbacks),
        }

    async def manual_health_check(self) -> HealthCheckResult:
        """Perform manual health check.

        Returns:
            Health check result
        """
        return await self._perform_health_check()

    async def manual_security_check(self):
        """Perform manual security check."""
        await self._perform_security_check()

    def configure_monitoring(
        self,
        health_check_interval: Optional[float] = None,
        security_check_interval: Optional[float] = None,
        max_recovery_attempts: Optional[int] = None,
        recovery_delay: Optional[float] = None,
    ):
        """Configure monitoring settings.

        Args:
            health_check_interval: Health check interval in seconds
            security_check_interval: Security check interval in seconds
            max_recovery_attempts: Maximum recovery attempts
            recovery_delay: Delay between recovery attempts
        """
        if health_check_interval is not None:
            self._health_check_interval = health_check_interval

        if security_check_interval is not None:
            self._security_check_interval = security_check_interval

        if max_recovery_attempts is not None:
            self._max_recovery_attempts = max_recovery_attempts

        if recovery_delay is not None:
            self._recovery_delay = recovery_delay

        logger.info("Monitoring configuration updated")
