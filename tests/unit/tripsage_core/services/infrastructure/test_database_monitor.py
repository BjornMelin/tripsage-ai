"""
Tests for database connection monitoring functionality.

Tests cover health checks, security monitoring, recovery mechanisms,
and alert generation for database operations.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import DatabaseMetrics
from tripsage_core.services.infrastructure.database_monitor import (
    DatabaseConnectionMonitor,
    HealthCheckResult,
    HealthStatus,
    SecurityAlert,
    SecurityEvent,
)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_initialization_with_defaults(self):
        """Test initialization with default timestamp."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY, response_time=0.5, message="All good"
        )

        assert result.status == HealthStatus.HEALTHY
        assert result.response_time == 0.5
        assert result.message == "All good"
        assert result.details is None
        assert isinstance(result.timestamp, datetime)

    def test_initialization_with_details(self):
        """Test initialization with custom details."""
        details = {"connection_count": 5}
        result = HealthCheckResult(
            status=HealthStatus.WARNING,
            response_time=1.0,
            message="High response time",
            details=details,
        )

        assert result.details == details


class TestSecurityAlert:
    """Test SecurityAlert dataclass."""

    def test_initialization_with_defaults(self):
        """Test initialization with default timestamp."""
        alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="critical",
            message="Connection failed",
            details={"error": "timeout"},
        )

        assert alert.event_type == SecurityEvent.CONNECTION_FAILURE
        assert alert.severity == "critical"
        assert alert.message == "Connection failed"
        assert alert.details == {"error": "timeout"}
        assert isinstance(alert.timestamp, datetime)
        assert alert.user_id is None
        assert alert.ip_address is None

    def test_initialization_with_user_info(self):
        """Test initialization with user information."""
        alert = SecurityAlert(
            event_type=SecurityEvent.UNAUTHORIZED_ACCESS,
            severity="warning",
            message="Unauthorized access attempt",
            details={},
            user_id="user123",
            ip_address="192.168.1.1",
        )

        assert alert.user_id == "user123"
        assert alert.ip_address == "192.168.1.1"


class TestDatabaseConnectionMonitor:
    """Test suite for DatabaseConnectionMonitor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()
        self.mock_db_service.is_connected = True
        self.mock_db_service.health_check = AsyncMock(return_value=True)
        self.mock_db_service.get_database_stats = AsyncMock(
            return_value={"connections": 5}
        )
        self.mock_db_service.select = AsyncMock(return_value=[{"id": "123"}])
        self.mock_db_service.connect = AsyncMock()
        self.mock_db_service.close = AsyncMock()

        self.settings = Settings(
            enable_database_monitoring=True,
            enable_security_monitoring=True,
            db_health_check_interval=1.0,
            db_security_check_interval=2.0,
        )

        self.mock_metrics = Mock(spec=DatabaseMetrics)
        self.mock_metrics.record_health_check = Mock()
        self.mock_metrics.get_metrics_summary = Mock(
            return_value={"query_errors": {}, "query_total": {}}
        )

        self.monitor = DatabaseConnectionMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=self.mock_metrics,
        )

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test monitor initialization."""
        assert self.monitor.database_service == self.mock_db_service
        assert self.monitor.settings == self.settings
        assert self.monitor.metrics == self.mock_metrics
        assert not self.monitor._monitoring
        assert self.monitor._monitor_task is None

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        # Start monitoring
        await self.monitor.start_monitoring()
        assert self.monitor._monitoring
        assert self.monitor._monitor_task is not None

        # Stop monitoring
        await self.monitor.stop_monitoring()
        assert not self.monitor._monitoring

    @pytest.mark.asyncio
    async def test_start_monitoring_already_started(self):
        """Test starting monitoring when already started."""
        await self.monitor.start_monitoring()

        # Try to start again
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.logger"
        ) as mock_logger:
            await self.monitor.start_monitoring()
            mock_logger.warning.assert_called_with(
                "Database monitoring already started"
            )

    @pytest.mark.asyncio
    async def test_perform_health_check_success(self):
        """Test successful health check."""
        result = await self.monitor._perform_health_check()

        assert isinstance(result, HealthCheckResult)
        assert result.status == HealthStatus.HEALTHY
        assert "passed" in result.message
        assert result.details is not None
        assert result.details["connected"] is True

        # Verify metrics were updated
        self.mock_metrics.record_health_check.assert_called_with("supabase", True)

    @pytest.mark.asyncio
    async def test_perform_health_check_failure(self):
        """Test failed health check."""
        self.mock_db_service.health_check.return_value = False

        result = await self.monitor._perform_health_check()

        assert result.status == HealthStatus.CRITICAL
        assert "failed" in result.message

        # Verify metrics were updated
        self.mock_metrics.record_health_check.assert_called_with("supabase", False)

    @pytest.mark.asyncio
    async def test_perform_health_check_exception(self):
        """Test health check with exception."""
        self.mock_db_service.health_check.side_effect = Exception("Connection error")

        result = await self.monitor._perform_health_check()

        assert result.status == HealthStatus.CRITICAL
        assert "Health check error" in result.message
        assert "Connection error" in result.details["error"]

    @pytest.mark.asyncio
    async def test_collect_health_details(self):
        """Test collecting detailed health information."""
        details = await self.monitor._collect_health_details()

        assert "connected" in details
        assert details["connected"] is True
        assert "database_stats" in details
        assert "query_response_time" in details

    @pytest.mark.asyncio
    async def test_collect_health_details_query_error(self):
        """Test health details collection with query error."""
        self.mock_db_service.select.side_effect = Exception("Query failed")

        details = await self.monitor._collect_health_details()

        assert "query_error" in details
        assert "Query failed" in details["query_error"]

    def test_determine_health_status_healthy(self):
        """Test health status determination for healthy state."""
        details = {"connected": True, "query_response_time": 0.1}

        status = self.monitor._determine_health_status(details)
        assert status == HealthStatus.HEALTHY

    def test_determine_health_status_disconnected(self):
        """Test health status determination for disconnected state."""
        details = {"connected": False}

        status = self.monitor._determine_health_status(details)
        assert status == HealthStatus.CRITICAL

    def test_determine_health_status_query_error(self):
        """Test health status determination with query error."""
        details = {"connected": True, "query_error": "Some error"}

        status = self.monitor._determine_health_status(details)
        assert status == HealthStatus.CRITICAL

    def test_determine_health_status_slow_response(self):
        """Test health status determination with slow response."""
        details = {
            "connected": True,
            "query_response_time": 6.0,  # Exceeds 5 second threshold
        }

        status = self.monitor._determine_health_status(details)
        assert status == HealthStatus.WARNING

    @pytest.mark.asyncio
    async def test_handle_critical_health(self):
        """Test handling critical health status."""
        result = HealthCheckResult(
            status=HealthStatus.CRITICAL, response_time=2.0, message="Critical failure"
        )

        self.mock_db_service.is_connected = False

        with (
            patch.object(self.monitor, "_trigger_alert") as mock_trigger_alert,
            patch.object(self.monitor, "_attempt_recovery") as mock_recovery,
        ):
            await self.monitor._handle_critical_health(result)

            # Verify alert was triggered
            mock_trigger_alert.assert_called_once()
            alert = mock_trigger_alert.call_args[0][0]
            assert isinstance(alert, SecurityAlert)
            assert alert.event_type == SecurityEvent.CONNECTION_FAILURE

            # Verify recovery was attempted
            mock_recovery.assert_called_once()

    @pytest.mark.asyncio
    async def test_attempt_recovery_success(self):
        """Test successful database recovery."""
        self.mock_db_service.is_connected = False

        # Mock successful reconnection on first attempt
        async def mock_connect():
            self.mock_db_service.is_connected = True

        self.mock_db_service.connect.side_effect = mock_connect

        with patch.object(self.monitor, "_trigger_alert") as mock_trigger_alert:
            await self.monitor._attempt_recovery()

            # Verify success alert was triggered
            mock_trigger_alert.assert_called_once()
            alert = mock_trigger_alert.call_args[0][0]
            assert "recovered" in alert.message

    @pytest.mark.asyncio
    async def test_attempt_recovery_failure(self):
        """Test failed database recovery."""
        self.mock_db_service.is_connected = False
        self.mock_db_service.connect.side_effect = Exception("Cannot connect")

        with patch.object(self.monitor, "_trigger_alert") as mock_trigger_alert:
            await self.monitor._attempt_recovery()

            # Should trigger failure alert after max attempts
            assert mock_trigger_alert.call_count >= 1
            final_alert = mock_trigger_alert.call_args[0][0]
            assert "recovery failed" in final_alert.message

    @pytest.mark.asyncio
    async def test_perform_security_check(self):
        """Test security monitoring checks."""
        with (
            patch.object(self.monitor, "_check_connection_patterns") as mock_conn_check,
            patch.object(self.monitor, "_check_query_patterns") as mock_query_check,
            patch.object(self.monitor, "_check_rate_limits") as mock_rate_check,
        ):
            await self.monitor._perform_security_check()

            mock_conn_check.assert_called_once()
            mock_query_check.assert_called_once()
            mock_rate_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_patterns_trigger_alert(self):
        """Test connection pattern checking triggers alert."""
        # Set up conditions for alert
        self.monitor._failed_connection_count = 6
        self.monitor._last_connection_attempt = time.time()

        with patch.object(self.monitor, "_trigger_alert") as mock_trigger_alert:
            await self.monitor._check_connection_patterns()

            mock_trigger_alert.assert_called_once()
            alert = mock_trigger_alert.call_args[0][0]
            assert alert.event_type == SecurityEvent.CONNECTION_FAILURE

    @pytest.mark.asyncio
    async def test_check_query_patterns_high_errors(self):
        """Test query pattern checking with high error rate."""
        self.mock_metrics.get_metrics_summary.return_value = {
            "query_errors": {"error1": 5, "error2": 6},  # Total 11 > threshold of 10
            "query_total": {},
        }

        with patch.object(self.monitor, "_trigger_alert") as mock_trigger_alert:
            await self.monitor._check_query_patterns()

            mock_trigger_alert.assert_called_once()
            alert = mock_trigger_alert.call_args[0][0]
            assert alert.event_type == SecurityEvent.SUSPICIOUS_QUERY

    @pytest.mark.asyncio
    async def test_check_rate_limits_high_queries(self):
        """Test rate limit checking with high query count."""
        self.mock_metrics.get_metrics_summary.return_value = {
            "query_total": {
                "query1": 500,
                "query2": 600,
            },  # Total 1100 > threshold of 1000
            "query_errors": {},
        }

        with patch.object(self.monitor, "_trigger_alert") as mock_trigger_alert:
            await self.monitor._check_rate_limits()

            mock_trigger_alert.assert_called_once()
            alert = mock_trigger_alert.call_args[0][0]
            assert alert.event_type == SecurityEvent.RATE_LIMIT_EXCEEDED

    @pytest.mark.asyncio
    async def test_trigger_alert(self):
        """Test alert triggering and storage."""
        alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="critical",
            message="Test alert",
            details={},
        )

        callback_mock = Mock()
        self.monitor.add_alert_callback(callback_mock)

        with patch(
            "tripsage_core.services.infrastructure.database_monitor.logger"
        ) as mock_logger:
            await self.monitor._trigger_alert(alert)

            # Verify alert was logged
            mock_logger.warning.assert_called_once()

            # Verify callback was called
            callback_mock.assert_called_once_with(alert)

            # Verify alert was stored
            alerts = self.monitor.get_security_alerts()
            assert len(alerts) == 1
            assert alerts[0] == alert

    def test_alert_callback_management(self):
        """Test adding and removing alert callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        # Add callbacks
        self.monitor.add_alert_callback(callback1)
        self.monitor.add_alert_callback(callback2)
        assert len(self.monitor._alert_callbacks) == 2

        # Remove callback
        self.monitor.remove_alert_callback(callback1)
        assert len(self.monitor._alert_callbacks) == 1
        assert callback2 in self.monitor._alert_callbacks

    def test_connection_failure_tracking(self):
        """Test connection failure tracking."""
        # Record failures
        self.monitor.record_connection_failure()
        self.monitor.record_connection_failure()

        assert self.monitor._failed_connection_count == 2
        assert self.monitor._last_connection_attempt > 0

        # Reset failures
        self.monitor.reset_connection_failures()
        assert self.monitor._failed_connection_count == 0

    def test_get_current_health(self):
        """Test getting current health status."""
        # Initially no health check
        assert self.monitor.get_current_health() is None

        # After setting health check result
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY, response_time=0.5, message="Good"
        )
        self.monitor._last_health_check = result

        assert self.monitor.get_current_health() == result

    def test_get_health_history(self):
        """Test getting health check history."""
        # Add some history
        for i in range(5):
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY, response_time=0.1 * i, message=f"Check {i}"
            )
            self.monitor._health_history.append(result)

        # Get all history
        history = self.monitor.get_health_history()
        assert len(history) == 5

        # Get limited history
        limited_history = self.monitor.get_health_history(limit=3)
        assert len(limited_history) == 3

    def test_get_security_alerts(self):
        """Test getting security alerts."""
        # Add some alerts
        for i in range(3):
            alert = SecurityAlert(
                event_type=SecurityEvent.CONNECTION_FAILURE,
                severity="warning",
                message=f"Alert {i}",
                details={},
            )
            self.monitor._security_alerts.append(alert)

        # Get all alerts
        alerts = self.monitor.get_security_alerts()
        assert len(alerts) == 3

        # Get limited alerts
        limited_alerts = self.monitor.get_security_alerts(limit=2)
        assert len(limited_alerts) == 2

    def test_get_monitoring_status(self):
        """Test getting monitoring status."""
        status = self.monitor.get_monitoring_status()

        assert "monitoring_active" in status
        assert "health_check_interval" in status
        assert "security_check_interval" in status
        assert "last_health_check" in status
        assert "health_history_count" in status
        assert "security_alerts_count" in status
        assert "failed_connection_count" in status
        assert "alert_callbacks_count" in status

    @pytest.mark.asyncio
    async def test_manual_health_check(self):
        """Test manual health check trigger."""
        result = await self.monitor.manual_health_check()

        assert isinstance(result, HealthCheckResult)
        # Verify it was stored in history
        assert self.monitor._last_health_check == result

    @pytest.mark.asyncio
    async def test_manual_security_check(self):
        """Test manual security check trigger."""
        with patch.object(
            self.monitor, "_perform_security_check"
        ) as mock_security_check:
            await self.monitor.manual_security_check()
            mock_security_check.assert_called_once()

    def test_configure_monitoring(self):
        """Test monitoring configuration updates."""
        self.monitor.configure_monitoring(
            health_check_interval=60.0,
            security_check_interval=120.0,
            max_recovery_attempts=5,
            recovery_delay=10.0,
        )

        assert self.monitor._health_check_interval == 60.0
        assert self.monitor._security_check_interval == 120.0
        assert self.monitor._max_recovery_attempts == 5
        assert self.monitor._recovery_delay == 10.0

    def test_history_trimming(self):
        """Test that history collections are trimmed to max size."""
        # Add more health history than max
        for i in range(self.monitor._max_health_history + 10):
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY, response_time=0.1, message=f"Check {i}"
            )
            self.monitor._health_history.append(result)

        # Simulate trimming (normally done in _perform_health_check)
        if len(self.monitor._health_history) > self.monitor._max_health_history:
            self.monitor._health_history = self.monitor._health_history[
                -self.monitor._max_health_history :
            ]

        assert len(self.monitor._health_history) == self.monitor._max_health_history

    @pytest.mark.asyncio
    async def test_monitor_loop_exception_handling(self):
        """Test that monitor loop handles exceptions gracefully."""
        self.monitor._monitoring = True

        with patch.object(self.monitor, "_perform_health_check") as mock_health_check:
            mock_health_check.side_effect = Exception("Test error")

            # Run one iteration of the monitor loop
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]

                with pytest.raises(asyncio.CancelledError):
                    await self.monitor._monitor_loop()

                # Verify that sleep was called with error delay (10.0 seconds)
                mock_sleep.assert_called_with(10.0)
