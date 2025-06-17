"""
Tests for ConsolidatedDatabaseMonitor.

This test module verifies the consolidated database monitoring functionality
that combines health, performance, and security monitoring.
"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.infrastructure.database_monitor import (
    ConsolidatedDatabaseMonitor,
    HealthStatus,
    MonitoringConfig,
    QueryStatus,
    QueryType,
    SecurityEvent,
)


@pytest.fixture
def mock_database_service():
    """Create mock database service."""
    service = AsyncMock()
    service.is_connected = True
    service.health_check = AsyncMock(return_value=True)
    service.select = AsyncMock(return_value=[{"id": 1}])
    service.connect = AsyncMock()
    service.close = AsyncMock()
    return service


@pytest.fixture
def monitoring_config():
    """Create test monitoring configuration."""
    return MonitoringConfig(
        health_check_interval=1.0,
        security_check_interval=2.0,
        slow_query_threshold=0.1,
        max_query_history=100,
        recovery_enabled=True,
        max_recovery_attempts=2,
        recovery_delay=0.1,
    )


@pytest.fixture
async def consolidated_monitor(mock_database_service, monitoring_config):
    """Create consolidated database monitor instance."""
    monitor = ConsolidatedDatabaseMonitor(
        database_service=mock_database_service,
        config=monitoring_config,
    )
    yield monitor
    # Cleanup
    if monitor._monitoring:
        await monitor.stop_monitoring()


class TestConsolidatedDatabaseMonitor:
    """Test cases for ConsolidatedDatabaseMonitor."""

    async def test_initialization(self, consolidated_monitor):
        """Test monitor initialization."""
        assert consolidated_monitor is not None
        assert not consolidated_monitor._monitoring
        assert consolidated_monitor.config.health_check_enabled
        assert consolidated_monitor.config.query_monitoring_enabled
        assert consolidated_monitor.config.security_monitoring_enabled

    async def test_health_check(self, consolidated_monitor):
        """Test health check functionality."""
        result = await consolidated_monitor._perform_health_check()

        assert result is not None
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time >= 0
        assert "passed" in result.message

    async def test_health_check_failure(
        self, consolidated_monitor, mock_database_service
    ):
        """Test health check when database is unhealthy."""
        mock_database_service.health_check.return_value = False

        result = await consolidated_monitor._perform_health_check()

        assert result.status == HealthStatus.CRITICAL
        assert "failed" in result.message

    async def test_query_tracking(self, consolidated_monitor):
        """Test query execution tracking."""
        # Start tracking a query
        query_id = await consolidated_monitor.track_query(QueryType.SELECT, "users")
        assert query_id != ""

        # Finish tracking
        execution = await consolidated_monitor.finish_query(
            query_id, QueryStatus.SUCCESS, None, 5
        )

        assert execution is not None
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.status == QueryStatus.SUCCESS
        assert execution.row_count == 5
        assert execution.duration is not None

    async def test_slow_query_detection(self, consolidated_monitor):
        """Test slow query detection."""
        query_id = await consolidated_monitor.track_query(QueryType.SELECT, "users")

        # Simulate slow query
        time.sleep(0.2)  # Exceeds threshold of 0.1s

        execution = await consolidated_monitor.finish_query(
            query_id, QueryStatus.SUCCESS
        )

        assert execution.is_slow(consolidated_monitor.config.slow_query_threshold)

    async def test_monitor_query_context_manager(self, consolidated_monitor):
        """Test query monitoring context manager."""
        async with consolidated_monitor.monitor_query(QueryType.INSERT, "trips"):
            # Simulate some work
            await asyncio.sleep(0.01)

        # Check that query was tracked
        history = consolidated_monitor.get_query_history()
        assert len(history) == 1
        assert history[0].query_type == QueryType.INSERT
        assert history[0].table_name == "trips"

    async def test_monitor_query_context_manager_with_error(self, consolidated_monitor):
        """Test query monitoring context manager when an error occurs."""
        with pytest.raises(ValueError):
            async with consolidated_monitor.monitor_query(QueryType.UPDATE, "users"):
                raise ValueError("Test error")

        # Check that error was tracked
        history = consolidated_monitor.get_query_history()
        assert len(history) == 1
        assert history[0].status == QueryStatus.ERROR
        assert history[0].error_message == "Test error"

    async def test_connection_failure_tracking(self, consolidated_monitor):
        """Test connection failure tracking."""
        initial_count = consolidated_monitor._failed_connection_count

        consolidated_monitor.record_connection_failure()

        assert consolidated_monitor._failed_connection_count == initial_count + 1

        consolidated_monitor.reset_connection_failures()

        assert consolidated_monitor._failed_connection_count == 0

    async def test_alert_callback(self, consolidated_monitor):
        """Test alert callback functionality."""
        alerts_received = []

        def alert_callback(alert):
            alerts_received.append(alert)

        consolidated_monitor.add_alert_callback(alert_callback)

        # Trigger an alert manually
        from tripsage_core.services.infrastructure.database_monitor import (  # noqa: E501
            SecurityAlert,
        )

        test_alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="warning",
            message="Test alert",
            details={"test": True},
        )

        await consolidated_monitor._trigger_alert(test_alert)

        assert len(alerts_received) == 1
        assert alerts_received[0].message == "Test alert"

    async def test_monitoring_status(self, consolidated_monitor):
        """Test monitoring status reporting."""
        status = consolidated_monitor.get_monitoring_status()

        assert "monitoring_active" in status
        assert "config" in status
        assert "statistics" in status
        assert status["config"]["health_check_enabled"]
        assert status["config"]["query_monitoring_enabled"]

    async def test_start_stop_monitoring(self, consolidated_monitor):
        """Test starting and stopping monitoring."""
        await consolidated_monitor.start_monitoring()
        assert consolidated_monitor._monitoring

        await consolidated_monitor.stop_monitoring()
        assert not consolidated_monitor._monitoring

    async def test_security_check(self, consolidated_monitor):
        """Test security monitoring."""
        # Add some query history to trigger checks
        for _i in range(15):
            query_id = await consolidated_monitor.track_query(QueryType.SELECT, "users")
            await consolidated_monitor.finish_query(
                query_id, QueryStatus.ERROR, "Test error"
            )

        await consolidated_monitor._perform_security_check()

        # Should have triggered a high error rate alert
        alerts = consolidated_monitor.get_security_alerts()
        assert len(alerts) > 0

        high_error_alerts = [
            alert
            for alert in alerts
            if alert.event_type == SecurityEvent.HIGH_ERROR_RATE
        ]
        assert len(high_error_alerts) > 0

    async def test_manual_operations(self, consolidated_monitor):
        """Test manual health and security checks."""
        health_result = await consolidated_monitor.manual_health_check()
        assert health_result is not None
        assert health_result.status == HealthStatus.HEALTHY

        await consolidated_monitor.manual_security_check()
        # Should complete without error

    async def test_query_history_limits(self, consolidated_monitor):
        """Test query history size limiting."""
        # Set a small history limit
        consolidated_monitor.config.max_query_history = 5

        # Add more queries than the limit
        for i in range(10):
            query_id = await consolidated_monitor.track_query(
                QueryType.SELECT, f"table_{i}"
            )
            await consolidated_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        history = consolidated_monitor.get_query_history()
        assert len(history) == 5  # Should be limited

    async def test_slow_queries_filter(self, consolidated_monitor):
        """Test filtering of slow queries."""
        # Add some fast and slow queries
        for i in range(3):
            query_id = await consolidated_monitor.track_query(QueryType.SELECT, "users")
            if i % 2 == 0:
                # Simulate slow query
                time.sleep(0.2)
            await consolidated_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        slow_queries = consolidated_monitor.get_slow_queries()
        assert len(slow_queries) >= 1  # At least one slow query

    async def test_disabled_monitoring(self, mock_database_service):
        """Test monitor with disabled components."""
        config = MonitoringConfig(
            health_check_enabled=False,
            query_monitoring_enabled=False,
            security_monitoring_enabled=False,
            metrics_enabled=False,
        )

        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=config,
        )

        # Query tracking should return empty string when disabled
        query_id = await monitor.track_query(QueryType.SELECT, "users")
        assert query_id == ""

        # Monitoring status should reflect disabled state
        status = monitor.get_monitoring_status()
        assert not status["config"]["health_check_enabled"]
        assert not status["config"]["query_monitoring_enabled"]
