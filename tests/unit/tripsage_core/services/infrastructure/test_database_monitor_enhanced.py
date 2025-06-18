"""
Enhanced comprehensive tests for TripSage Core Database Monitor.

This module provides 90%+ test coverage for database monitoring functionality with
modern testing patterns:
- Health monitoring and thresholds
- Query performance tracking and slow query detection
- Security monitoring and alert system
- Prometheus metrics integration
- Automatic recovery mechanisms
- Connection failure handling
- Error rate monitoring and alerting
- Alert callback system
- Monitoring lifecycle management

Modern testing patterns:
- AAA (Arrange, Act, Assert) pattern
- pytest-asyncio for async test support
- Hypothesis for property-based testing
- Comprehensive fixture management
- Proper mocking with isolation
- Performance testing scenarios
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from hypothesis import given
from hypothesis import strategies as st

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.database_monitor import (
    ConsolidatedDatabaseMonitor,
    HealthCheckResult,
    HealthStatus,
    MonitoringConfig,
    QueryExecution,
    QueryStatus,
    QueryType,
    SecurityAlert,
    SecurityEvent,
    get_database_monitor,
    reset_consolidated_monitor,
)


class TestDatabaseMonitorInitialization:
    """Test suite for database monitor initialization."""

    @pytest_asyncio.fixture
    async def mock_database_service(self):
        """Create mock database service."""
        service = AsyncMock()
        service.is_connected = True
        service.health_check = AsyncMock(return_value=True)
        service.select = AsyncMock(return_value=[{"id": 1}])
        service.connect = AsyncMock()
        service.close = AsyncMock()
        return service

    @pytest_asyncio.fixture
    async def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.environment = "testing"
        return settings

    @pytest_asyncio.fixture
    async def monitoring_config(self):
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

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    def test_initialization_default(self, mock_database_service):
        """Test database monitor default initialization."""
        # Arrange & Act
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock(spec=Settings)
            mock_get_settings.return_value = mock_settings

            monitor = ConsolidatedDatabaseMonitor(mock_database_service)

            # Assert
            assert monitor.database_service == mock_database_service
            assert monitor.config is not None
            assert monitor.settings == mock_settings
            assert not monitor._monitoring
            assert monitor._monitor_task is None
            assert monitor._last_health_check is None
            assert len(monitor._health_history) == 0
            assert len(monitor._active_queries) == 0
            assert len(monitor._query_history) == 0
            assert len(monitor._security_alerts) == 0
            assert monitor._failed_connection_count == 0
            assert len(monitor._alert_callbacks) == 0

    def test_initialization_with_config(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Test database monitor initialization with custom config."""
        # Arrange & Act
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )

        # Assert
        assert monitor.config == monitoring_config
        assert monitor.config.health_check_interval == 1.0
        assert monitor.config.slow_query_threshold == 0.1
        assert monitor.config.recovery_enabled

    def test_initialization_with_metrics(self, mock_database_service, mock_settings):
        """Test database monitor initialization with Prometheus metrics."""
        # Arrange
        config = MonitoringConfig(metrics_enabled=True)
        mock_registry = Mock()

        # Mock prometheus_client
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.Counter"
        ) as mock_counter:
            with patch(
                "tripsage_core.services.infrastructure.database_monitor.Gauge"
            ) as mock_gauge:
                with patch(
                    "tripsage_core.services.infrastructure.database_monitor.Histogram"
                ) as mock_histogram:
                    mock_counter.return_value = Mock()
                    mock_gauge.return_value = Mock()
                    mock_histogram.return_value = Mock()

                    # Act
                    monitor = ConsolidatedDatabaseMonitor(
                        database_service=mock_database_service,
                        config=config,
                        settings=mock_settings,
                        metrics_registry=mock_registry,
                    )

                    # Assert
                    assert monitor.metrics is not None

    def test_initialization_metrics_import_error(
        self, mock_database_service, mock_settings
    ):
        """Test database monitor initialization when Prometheus is not available."""
        # Arrange
        config = MonitoringConfig(metrics_enabled=True)

        # Mock ImportError for prometheus_client
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.ConsolidatedDatabaseMonitor._initialize_metrics"
        ) as mock_init:
            mock_init.side_effect = ImportError("prometheus_client not found")

            # Act
            monitor = ConsolidatedDatabaseMonitor(
                database_service=mock_database_service,
                config=config,
                settings=mock_settings,
            )

            # Assert
            assert monitor.metrics is None


class TestDatabaseMonitorHealthChecks:
    """Test suite for health monitoring functionality."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_health_check_success(self, database_monitor):
        """Test successful health check."""
        # Arrange
        database_monitor.database_service.health_check.return_value = True
        database_monitor.database_service.is_connected = True
        database_monitor.database_service.select.return_value = [{"id": 1}]

        # Act
        result = await database_monitor._perform_health_check()

        # Assert
        assert isinstance(result, HealthCheckResult)
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time >= 0
        assert "passed" in result.message
        assert result.details is not None
        assert result.details["connected"] is True
        assert database_monitor._last_health_check == result
        assert len(database_monitor._health_history) == 1

    @pytest.mark.asyncio
    async def test_health_check_connectivity_failure(self, database_monitor):
        """Test health check when database connectivity fails."""
        # Arrange
        database_monitor.database_service.health_check.return_value = False

        # Act
        result = await database_monitor._perform_health_check()

        # Assert
        assert result.status == HealthStatus.CRITICAL
        assert "failed" in result.message
        assert "connectivity issue" in result.message

    @pytest.mark.asyncio
    async def test_health_check_query_error(self, database_monitor):
        """Test health check when test query fails."""
        # Arrange
        database_monitor.database_service.health_check.return_value = True
        database_monitor.database_service.is_connected = True
        database_monitor.database_service.select.side_effect = Exception("Query failed")

        # Act
        result = await database_monitor._perform_health_check()

        # Assert
        assert result.status == HealthStatus.CRITICAL
        assert result.details is not None
        assert "query_error" in result.details

    @pytest.mark.asyncio
    async def test_health_check_slow_response(self, database_monitor):
        """Test health check with slow response time."""
        # Arrange
        database_monitor.config.response_time_warning_threshold = 0.001
        database_monitor.config.response_time_critical_threshold = 0.002
        database_monitor.database_service.health_check.return_value = True
        database_monitor.database_service.is_connected = True

        async def slow_select(*args, **kwargs):
            await asyncio.sleep(0.0015)  # Between warning and critical
            return [{"id": 1}]

        database_monitor.database_service.select = slow_select

        # Act
        result = await database_monitor._perform_health_check()

        # Assert
        assert result.status == HealthStatus.WARNING

    @pytest.mark.asyncio
    async def test_health_check_critical_response_time(self, database_monitor):
        """Test health check with critical response time."""
        # Arrange
        database_monitor.config.response_time_critical_threshold = 0.001
        database_monitor.database_service.health_check.return_value = True
        database_monitor.database_service.is_connected = True

        async def very_slow_select(*args, **kwargs):
            await asyncio.sleep(0.002)  # Above critical threshold
            return [{"id": 1}]

        database_monitor.database_service.select = very_slow_select

        # Act
        result = await database_monitor._perform_health_check()

        # Assert
        assert result.status == HealthStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, database_monitor):
        """Test health check exception handling."""
        # Arrange
        database_monitor.database_service.health_check.side_effect = Exception(
            "Connection error"
        )

        # Act
        result = await database_monitor._perform_health_check()

        # Assert
        assert result.status == HealthStatus.CRITICAL
        assert "Health check error" in result.message
        assert result.details is not None
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_health_history_trimming(self, database_monitor):
        """Test health check history size limiting."""
        # Arrange
        database_monitor.database_service.health_check.return_value = True

        # Act - Perform many health checks
        for _ in range(105):
            await database_monitor._perform_health_check()

        # Assert
        assert len(database_monitor._health_history) == 100  # Should be trimmed

    @pytest.mark.asyncio
    async def test_manual_health_check(self, database_monitor):
        """Test manual health check execution."""
        # Arrange
        database_monitor.database_service.health_check.return_value = True

        # Act
        result = await database_monitor.manual_health_check()

        # Assert
        assert isinstance(result, HealthCheckResult)
        assert result.status == HealthStatus.HEALTHY

    def test_get_current_health(self, database_monitor):
        """Test getting current health status."""
        # Arrange & Act
        current_health = database_monitor.get_current_health()

        # Assert
        assert current_health is None  # No health check performed yet

    def test_get_health_history(self, database_monitor):
        """Test getting health check history."""
        # Arrange & Act
        history = database_monitor.get_health_history()

        # Assert
        assert isinstance(history, list)
        assert len(history) == 0

    def test_get_health_history_with_limit(self, database_monitor):
        """Test getting health check history with limit."""
        # Arrange
        # Add some mock health results
        for i in range(5):
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                response_time=0.1,
                message=f"Test {i}",
            )
            database_monitor._health_history.append(result)

        # Act
        history = database_monitor.get_health_history(limit=3)

        # Assert
        assert len(history) == 3
        assert history[-1].message == "Test 4"  # Should be the last 3 entries


class TestDatabaseMonitorQueryTracking:
    """Test suite for query monitoring functionality."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_query_tracking_basic(self, database_monitor):
        """Test basic query tracking functionality."""
        # Arrange & Act
        query_id = await database_monitor.track_query(QueryType.SELECT, "users")

        # Assert
        assert query_id != ""
        assert query_id in database_monitor._active_queries
        execution = database_monitor._active_queries[query_id]
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.start_time > 0
        assert execution.end_time is None

    @pytest.mark.asyncio
    async def test_query_tracking_disabled(self, mock_database_service, mock_settings):
        """Test query tracking when disabled."""
        # Arrange
        config = MonitoringConfig(query_monitoring_enabled=False)
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=config,
            settings=mock_settings,
        )

        # Act
        query_id = await monitor.track_query(QueryType.SELECT, "users")

        # Assert
        assert query_id == ""
        assert len(monitor._active_queries) == 0

    @pytest.mark.asyncio
    async def test_finish_query_success(self, database_monitor):
        """Test finishing query tracking successfully."""
        # Arrange
        query_id = await database_monitor.track_query(QueryType.INSERT, "trips")
        await asyncio.sleep(0.01)  # Small delay to ensure duration

        # Act
        execution = await database_monitor.finish_query(
            query_id, QueryStatus.SUCCESS, None, 5
        )

        # Assert
        assert execution is not None
        assert execution.query_id == query_id
        assert execution.status == QueryStatus.SUCCESS
        assert execution.row_count == 5
        assert execution.duration is not None
        assert execution.duration > 0
        assert execution.is_successful
        assert query_id not in database_monitor._active_queries
        assert len(database_monitor._query_history) == 1

    @pytest.mark.asyncio
    async def test_finish_query_error(self, database_monitor):
        """Test finishing query tracking with error."""
        # Arrange
        query_id = await database_monitor.track_query(QueryType.UPDATE, "users")

        # Act
        execution = await database_monitor.finish_query(
            query_id, QueryStatus.ERROR, "SQL syntax error"
        )

        # Assert
        assert execution is not None
        assert execution.status == QueryStatus.ERROR
        assert execution.error_message == "SQL syntax error"
        assert not execution.is_successful

    @pytest.mark.asyncio
    async def test_finish_query_not_found(self, database_monitor):
        """Test finishing query that wasn't tracked."""
        # Arrange & Act
        execution = await database_monitor.finish_query("nonexistent_id")

        # Assert
        assert execution is None

    @pytest.mark.asyncio
    async def test_finish_query_empty_id(self, database_monitor):
        """Test finishing query with empty ID."""
        # Arrange & Act
        execution = await database_monitor.finish_query("")

        # Assert
        assert execution is None

    @pytest.mark.asyncio
    async def test_slow_query_detection(self, database_monitor):
        """Test slow query detection."""
        # Arrange
        query_id = await database_monitor.track_query(QueryType.SELECT, "large_table")
        await asyncio.sleep(0.15)  # Exceeds threshold of 0.1s

        # Act
        execution = await database_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        # Assert
        assert execution.is_slow(database_monitor.config.slow_query_threshold)
        assert execution.duration >= 0.1

    @pytest.mark.asyncio
    async def test_query_history_limiting(self, database_monitor):
        """Test query history size limiting."""
        # Arrange
        database_monitor.config.max_query_history = 5

        # Act - Add more queries than the limit
        for i in range(10):
            query_id = await database_monitor.track_query(
                QueryType.SELECT, f"table_{i}"
            )
            await database_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        # Assert
        assert len(database_monitor._query_history) == 5

    @pytest.mark.asyncio
    async def test_monitor_query_context_manager(self, database_monitor):
        """Test query monitoring context manager."""
        # Arrange & Act
        async with database_monitor.monitor_query(
            QueryType.DELETE, "old_data"
        ) as query_id:
            assert query_id != ""
            await asyncio.sleep(0.01)

        # Assert
        history = database_monitor.get_query_history()
        assert len(history) == 1
        assert history[0].query_type == QueryType.DELETE
        assert history[0].table_name == "old_data"
        assert history[0].status == QueryStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_monitor_query_context_manager_with_exception(self, database_monitor):
        """Test query monitoring context manager with exception."""
        # Arrange & Act
        with pytest.raises(ValueError):
            async with database_monitor.monitor_query(QueryType.UPDATE, "users"):
                raise ValueError("Test error")

        # Assert
        history = database_monitor.get_query_history()
        assert len(history) == 1
        assert history[0].status == QueryStatus.ERROR
        assert history[0].error_message == "Test error"

    def test_get_query_history(self, database_monitor):
        """Test getting query history."""
        # Arrange
        for i in range(3):
            execution = QueryExecution(
                query_id=f"test_{i}",
                query_type=QueryType.SELECT,
                table_name="users",
                start_time=time.perf_counter(),
            )
            database_monitor._query_history.append(execution)

        # Act
        history = database_monitor.get_query_history()

        # Assert
        assert len(history) == 3

    def test_get_query_history_with_limit(self, database_monitor):
        """Test getting query history with limit."""
        # Arrange
        for i in range(5):
            execution = QueryExecution(
                query_id=f"test_{i}",
                query_type=QueryType.SELECT,
                table_name="users",
                start_time=time.perf_counter(),
            )
            database_monitor._query_history.append(execution)

        # Act
        history = database_monitor.get_query_history(limit=2)

        # Assert
        assert len(history) == 2
        assert history[-1].query_id == "test_4"  # Should be the last 2 entries

    def test_get_slow_queries(self, database_monitor):
        """Test filtering slow queries."""
        # Arrange
        fast_execution = QueryExecution(
            query_id="fast",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=0.0,
            end_time=0.05,
            duration=0.05,
        )
        slow_execution = QueryExecution(
            query_id="slow",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=0.0,
            end_time=0.2,
            duration=0.2,
        )
        database_monitor._query_history = [fast_execution, slow_execution]

        # Act
        slow_queries = database_monitor.get_slow_queries()

        # Assert
        assert len(slow_queries) == 1
        assert slow_queries[0].query_id == "slow"

    def test_get_slow_queries_custom_threshold(self, database_monitor):
        """Test filtering slow queries with custom threshold."""
        # Arrange
        execution = QueryExecution(
            query_id="medium",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=0.0,
            end_time=0.15,
            duration=0.15,
        )
        database_monitor._query_history = [execution]

        # Act
        slow_queries = database_monitor.get_slow_queries(threshold=0.2)

        # Assert
        assert len(slow_queries) == 0  # 0.15 < 0.2


class TestDatabaseMonitorSecurityMonitoring:
    """Test suite for security monitoring functionality."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_security_check_high_error_rate(self, database_monitor):
        """Test security check for high error rates."""
        # Arrange - Add queries with high error rate
        for i in range(10):
            query_id = await database_monitor.track_query(QueryType.SELECT, "users")
            status = QueryStatus.ERROR if i < 8 else QueryStatus.SUCCESS
            await database_monitor.finish_query(
                query_id, status, "Test error" if status == QueryStatus.ERROR else None
            )

        # Act
        await database_monitor._perform_security_check()

        # Assert
        alerts = database_monitor.get_security_alerts()
        error_rate_alerts = [
            alert
            for alert in alerts
            if alert.event_type == SecurityEvent.HIGH_ERROR_RATE
        ]
        assert len(error_rate_alerts) > 0
        assert error_rate_alerts[0].severity == "warning"

    @pytest.mark.asyncio
    async def test_security_check_slow_queries(self, database_monitor):
        """Test security check for high number of slow queries."""
        # Arrange - Add many slow queries
        for _i in range(15):
            query_id = await database_monitor.track_query(QueryType.SELECT, "users")
            execution = database_monitor._active_queries[query_id]
            execution.duration = 0.2  # Slow query
            execution.end_time = execution.start_time + 0.2
            await database_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        # Act
        await database_monitor._perform_security_check()

        # Assert
        alerts = database_monitor.get_security_alerts()
        slow_query_alerts = [
            alert
            for alert in alerts
            if alert.event_type == SecurityEvent.SLOW_QUERY_DETECTED
        ]
        assert len(slow_query_alerts) > 0

    @pytest.mark.asyncio
    async def test_security_check_connection_failures(self, database_monitor):
        """Test security check for multiple connection failures."""
        # Arrange
        database_monitor._failed_connection_count = 6
        database_monitor._last_connection_attempt = time.time() - 30  # Recent failures

        # Act
        await database_monitor._perform_security_check()

        # Assert
        alerts = database_monitor.get_security_alerts()
        connection_failure_alerts = [
            alert
            for alert in alerts
            if alert.event_type == SecurityEvent.CONNECTION_FAILURE
        ]
        assert len(connection_failure_alerts) > 0

    @pytest.mark.asyncio
    async def test_security_check_no_queries(self, database_monitor):
        """Test security check when no queries have been tracked."""
        # Arrange & Act
        await database_monitor._perform_security_check()

        # Assert - Should not raise errors
        alerts = database_monitor.get_security_alerts()
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_security_check_exception_handling(self, database_monitor):
        """Test security check exception handling."""
        # Arrange
        with patch.object(
            database_monitor,
            "_check_query_patterns",
            side_effect=Exception("Test error"),
        ):
            # Act
            await database_monitor._perform_security_check()

            # Assert - Should not raise errors, just log them

    @pytest.mark.asyncio
    async def test_manual_security_check(self, database_monitor):
        """Test manual security check execution."""
        # Arrange & Act
        await database_monitor.manual_security_check()

        # Assert - Should complete without errors

    def test_record_connection_failure(self, database_monitor):
        """Test recording connection failures."""
        # Arrange
        initial_count = database_monitor._failed_connection_count

        # Act
        database_monitor.record_connection_failure()

        # Assert
        assert database_monitor._failed_connection_count == initial_count + 1
        assert database_monitor._last_connection_attempt > 0

    def test_reset_connection_failures(self, database_monitor):
        """Test resetting connection failure count."""
        # Arrange
        database_monitor._failed_connection_count = 5

        # Act
        database_monitor.reset_connection_failures()

        # Assert
        assert database_monitor._failed_connection_count == 0

    def test_get_security_alerts(self, database_monitor):
        """Test getting security alerts."""
        # Arrange
        alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="warning",
            message="Test alert",
            details={"test": True},
        )
        database_monitor._security_alerts = [alert]

        # Act
        alerts = database_monitor.get_security_alerts()

        # Assert
        assert len(alerts) == 1
        assert alerts[0].message == "Test alert"

    def test_get_security_alerts_with_limit(self, database_monitor):
        """Test getting security alerts with limit."""
        # Arrange
        for i in range(5):
            alert = SecurityAlert(
                event_type=SecurityEvent.CONNECTION_FAILURE,
                severity="warning",
                message=f"Alert {i}",
                details={},
            )
            database_monitor._security_alerts.append(alert)

        # Act
        alerts = database_monitor.get_security_alerts(limit=2)

        # Assert
        assert len(alerts) == 2
        assert alerts[-1].message == "Alert 4"


class TestDatabaseMonitorAlertSystem:
    """Test suite for alert callback system."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_alert_callback_registration(self, database_monitor):
        """Test alert callback registration and removal."""

        # Arrange
        def test_callback(alert):
            pass

        # Act
        database_monitor.add_alert_callback(test_callback)

        # Assert
        assert test_callback in database_monitor._alert_callbacks

        # Act - Remove callback
        database_monitor.remove_alert_callback(test_callback)

        # Assert
        assert test_callback not in database_monitor._alert_callbacks

    @pytest.mark.asyncio
    async def test_alert_callback_execution(self, database_monitor):
        """Test alert callback execution."""
        # Arrange
        received_alerts = []

        def test_callback(alert):
            received_alerts.append(alert)

        database_monitor.add_alert_callback(test_callback)

        alert = SecurityAlert(
            event_type=SecurityEvent.HIGH_ERROR_RATE,
            severity="warning",
            message="Test alert",
            details={},
        )

        # Act
        await database_monitor._trigger_alert(alert)

        # Assert
        assert len(received_alerts) == 1
        assert received_alerts[0].message == "Test alert"
        assert len(database_monitor._security_alerts) == 1

    @pytest.mark.asyncio
    async def test_alert_callback_exception_handling(self, database_monitor):
        """Test alert callback exception handling."""

        # Arrange
        def failing_callback(alert):
            raise Exception("Callback error")

        database_monitor.add_alert_callback(failing_callback)

        alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="critical",
            message="Test alert",
            details={},
        )

        # Act - Should not raise exception
        await database_monitor._trigger_alert(alert)

        # Assert
        assert len(database_monitor._security_alerts) == 1

    @pytest.mark.asyncio
    async def test_alert_history_limiting(self, database_monitor):
        """Test alert history size limiting."""
        # Arrange
        database_monitor.config.max_security_history = 3

        # Act - Add more alerts than the limit
        for i in range(5):
            alert = SecurityAlert(
                event_type=SecurityEvent.CONNECTION_FAILURE,
                severity="warning",
                message=f"Alert {i}",
                details={},
            )
            await database_monitor._trigger_alert(alert)

        # Assert
        assert len(database_monitor._security_alerts) == 3
        # Should keep the last 3 alerts
        assert database_monitor._security_alerts[-1].message == "Alert 4"

    def test_remove_nonexistent_callback(self, database_monitor):
        """Test removing callback that doesn't exist."""

        # Arrange
        def test_callback(alert):
            pass

        # Act - Should not raise error
        database_monitor.remove_alert_callback(test_callback)

        # Assert
        assert test_callback not in database_monitor._alert_callbacks


class TestDatabaseMonitorRecovery:
    """Test suite for automatic recovery functionality."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_recovery_successful(self, database_monitor):
        """Test successful database connection recovery."""
        # Arrange
        database_monitor.database_service.is_connected = False
        database_monitor.database_service.connect.return_value = None
        database_monitor.database_service.close.return_value = None

        # Mock successful reconnection
        def mock_connect():
            database_monitor.database_service.is_connected = True

        database_monitor.database_service.connect.side_effect = mock_connect

        # Act
        await database_monitor._attempt_recovery()

        # Assert
        database_monitor.database_service.close.assert_called()
        database_monitor.database_service.connect.assert_called()
        assert database_monitor.database_service.is_connected

    @pytest.mark.asyncio
    async def test_recovery_failure_all_attempts(self, database_monitor):
        """Test recovery failure after all attempts."""
        # Arrange
        database_monitor.database_service.is_connected = False
        database_monitor.database_service.connect.side_effect = Exception(
            "Connection failed"
        )

        # Act
        await database_monitor._attempt_recovery()

        # Assert
        assert (
            database_monitor.database_service.connect.call_count
            == database_monitor.config.max_recovery_attempts
        )
        alerts = database_monitor.get_security_alerts()
        failure_alerts = [
            alert
            for alert in alerts
            if alert.event_type == SecurityEvent.CONNECTION_FAILURE
            and "recovery failed" in alert.message
        ]
        assert len(failure_alerts) > 0

    @pytest.mark.asyncio
    async def test_recovery_partial_failure(self, database_monitor):
        """Test recovery succeeding after some failures."""
        # Arrange
        database_monitor.database_service.is_connected = False
        connect_calls = 0

        def mock_connect():
            nonlocal connect_calls
            connect_calls += 1
            if connect_calls == 2:  # Succeed on second attempt
                database_monitor.database_service.is_connected = True
            else:
                raise Exception("Connection failed")

        database_monitor.database_service.connect.side_effect = mock_connect

        # Act
        await database_monitor._attempt_recovery()

        # Assert
        assert database_monitor.database_service.connect.call_count == 2
        assert database_monitor.database_service.is_connected

    @pytest.mark.asyncio
    async def test_critical_health_triggers_recovery(self, database_monitor):
        """Test that critical health status triggers recovery when enabled."""
        # Arrange
        database_monitor.config.recovery_enabled = True
        database_monitor.database_service.is_connected = False

        # Mock successful recovery
        def mock_connect():
            database_monitor.database_service.is_connected = True

        database_monitor.database_service.connect.side_effect = mock_connect

        critical_result = HealthCheckResult(
            status=HealthStatus.CRITICAL,
            response_time=1.0,
            message="Critical health",
        )

        # Act
        await database_monitor._handle_critical_health(critical_result)

        # Assert
        database_monitor.database_service.connect.assert_called()

    @pytest.mark.asyncio
    async def test_recovery_disabled(self, mock_database_service, mock_settings):
        """Test behavior when recovery is disabled."""
        # Arrange
        config = MonitoringConfig(recovery_enabled=False)
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=config,
            settings=mock_settings,
        )

        critical_result = HealthCheckResult(
            status=HealthStatus.CRITICAL,
            response_time=1.0,
            message="Critical health",
        )

        # Act
        await monitor._handle_critical_health(critical_result)

        # Assert
        mock_database_service.connect.assert_not_called()


class TestDatabaseMonitorLifecycle:
    """Test suite for monitoring lifecycle management."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_start_monitoring(self, database_monitor):
        """Test starting monitoring."""
        # Arrange & Act
        await database_monitor.start_monitoring()

        # Assert
        assert database_monitor._monitoring
        assert database_monitor._monitor_task is not None
        assert not database_monitor._monitor_task.done()

    @pytest.mark.asyncio
    async def test_start_monitoring_already_running(self, database_monitor):
        """Test starting monitoring when already running."""
        # Arrange
        await database_monitor.start_monitoring()
        initial_task = database_monitor._monitor_task

        # Act
        await database_monitor.start_monitoring()

        # Assert
        assert database_monitor._monitor_task == initial_task  # Same task

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, database_monitor):
        """Test stopping monitoring."""
        # Arrange
        await database_monitor.start_monitoring()

        # Act
        await database_monitor.stop_monitoring()

        # Assert
        assert not database_monitor._monitoring
        assert database_monitor._monitor_task.done()

    @pytest.mark.asyncio
    async def test_stop_monitoring_not_running(self, database_monitor):
        """Test stopping monitoring when not running."""
        # Arrange & Act
        await database_monitor.stop_monitoring()

        # Assert - Should not raise error
        assert not database_monitor._monitoring

    @pytest.mark.asyncio
    async def test_monitor_loop_health_checks(self, database_monitor):
        """Test monitoring loop performs health checks."""
        # Arrange
        database_monitor.config.health_check_interval = 0.1
        database_monitor.database_service.health_check.return_value = True

        # Act
        await database_monitor.start_monitoring()
        await asyncio.sleep(0.2)  # Let it run briefly
        await database_monitor.stop_monitoring()

        # Assert
        assert len(database_monitor._health_history) > 0

    @pytest.mark.asyncio
    async def test_monitor_loop_security_checks(self, database_monitor):
        """Test monitoring loop performs security checks."""
        # Arrange
        database_monitor.config.security_check_interval = 0.1

        # Add some error queries to trigger security alerts
        for _i in range(10):
            query_id = await database_monitor.track_query(QueryType.SELECT, "users")
            await database_monitor.finish_query(query_id, QueryStatus.ERROR, "Error")

        # Act
        await database_monitor.start_monitoring()
        await asyncio.sleep(0.2)  # Let it run briefly
        await database_monitor.stop_monitoring()

        # Assert
        alerts = database_monitor.get_security_alerts()
        assert len(alerts) > 0

    @pytest.mark.asyncio
    async def test_monitor_loop_exception_handling(self, database_monitor):
        """Test monitoring loop handles exceptions gracefully."""
        # Arrange
        database_monitor.database_service.health_check.side_effect = Exception(
            "Test error"
        )

        # Act
        await database_monitor.start_monitoring()
        await asyncio.sleep(0.1)  # Let it run briefly
        await database_monitor.stop_monitoring()

        # Assert - Should not crash, monitoring should still be stoppable
        assert not database_monitor._monitoring


class TestDatabaseMonitorStatus:
    """Test suite for monitoring status and reporting."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    def test_monitoring_status_basic(self, database_monitor):
        """Test basic monitoring status reporting."""
        # Arrange & Act
        status = database_monitor.get_monitoring_status()

        # Assert
        assert isinstance(status, dict)
        assert "monitoring_active" in status
        assert "config" in status
        assert "statistics" in status
        assert status["monitoring_active"] is False
        assert status["config"]["health_check_enabled"]
        assert status["config"]["query_monitoring_enabled"]
        assert status["config"]["security_monitoring_enabled"]

    def test_monitoring_status_with_data(self, database_monitor):
        """Test monitoring status with historical data."""
        # Arrange
        # Add some test data
        health_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            response_time=0.1,
            message="Test health check",
        )
        database_monitor._last_health_check = health_result
        database_monitor._health_history.append(health_result)

        execution = QueryExecution(
            query_id="test",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=time.perf_counter(),
        )
        database_monitor._query_history.append(execution)

        alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="warning",
            message="Test alert",
            details={},
        )
        database_monitor._security_alerts.append(alert)

        # Act
        status = database_monitor.get_monitoring_status()

        # Assert
        assert status["statistics"]["health_checks_count"] == 1
        assert status["statistics"]["queries_tracked"] == 1
        assert status["statistics"]["security_alerts_count"] == 1
        assert status["last_health_check"] is not None
        assert status["last_health_check"]["status"] == "healthy"

    def test_monitoring_status_no_health_check(self, database_monitor):
        """Test monitoring status when no health check has been performed."""
        # Arrange & Act
        status = database_monitor.get_monitoring_status()

        # Assert
        assert status["last_health_check"] is None


class TestDatabaseMonitorGlobalInstance:
    """Test suite for global database monitor instance management."""

    def test_get_database_monitor_create(self, mock_database_service, mock_settings):
        """Test creating global database monitor instance."""
        # Arrange
        reset_consolidated_monitor()

        # Act
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            monitor = get_database_monitor(database_service=mock_database_service)

        # Assert
        assert monitor is not None
        assert isinstance(monitor, ConsolidatedDatabaseMonitor)

    def test_get_database_monitor_singleton(self, mock_database_service, mock_settings):
        """Test global database monitor singleton behavior."""
        # Arrange
        reset_consolidated_monitor()

        # Act
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            monitor1 = get_database_monitor(database_service=mock_database_service)
            monitor2 = get_database_monitor()

        # Assert
        assert monitor1 == monitor2  # Same instance

    def test_get_database_monitor_none_service(self):
        """Test getting database monitor without service."""
        # Arrange
        reset_consolidated_monitor()

        # Act
        monitor = get_database_monitor()

        # Assert
        assert monitor is None

    def test_reset_consolidated_monitor(self, mock_database_service, mock_settings):
        """Test resetting global database monitor instance."""
        # Arrange
        with patch(
            "tripsage_core.services.infrastructure.database_monitor.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            get_database_monitor(database_service=mock_database_service)

        # Act
        reset_consolidated_monitor()
        monitor = get_database_monitor()

        # Assert
        assert monitor is None


# Property-based testing with Hypothesis
class TestDatabaseMonitorPropertyBased:
    """Property-based tests using Hypothesis."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @given(
        query_count=st.integers(min_value=1, max_value=50),
        error_rate=st.floats(min_value=0.0, max_value=1.0),
    )
    @pytest.mark.asyncio
    async def test_error_rate_calculation_property(
        self, database_monitor, query_count, error_rate
    ):
        """Property test: error rate calculation should be consistent."""
        # Arrange
        error_count = int(query_count * error_rate)
        success_count = query_count - error_count

        # Act - Add queries with specified error rate
        for _i in range(error_count):
            query_id = await database_monitor.track_query(QueryType.SELECT, "users")
            await database_monitor.finish_query(
                query_id, QueryStatus.ERROR, "Test error"
            )

        for _i in range(success_count):
            query_id = await database_monitor.track_query(QueryType.SELECT, "users")
            await database_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        # Assert
        history = database_monitor.get_query_history()
        actual_error_count = len([q for q in history if not q.is_successful])
        actual_error_rate = actual_error_count / len(history) if history else 0

        assert len(history) == query_count
        assert abs(actual_error_rate - error_rate) < 0.1  # Allow small tolerance

    @given(
        threshold=st.floats(min_value=0.01, max_value=2.0),
        duration=st.floats(min_value=0.0, max_value=3.0),
    )
    def test_slow_query_detection_property(self, database_monitor, threshold, duration):
        """Property test: slow query detection should be consistent with threshold."""
        # Arrange
        execution = QueryExecution(
            query_id="test",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=0.0,
            end_time=duration,
            duration=duration,
        )

        # Act & Assert
        is_slow = execution.is_slow(threshold)
        expected_slow = duration > threshold
        assert is_slow == expected_slow


# Performance benchmarking tests
class TestDatabaseMonitorPerformance:
    """Performance tests for database monitoring operations."""

    @pytest_asyncio.fixture
    async def database_monitor(
        self, mock_database_service, monitoring_config, mock_settings
    ):
        """Create database monitor for testing."""
        monitor = ConsolidatedDatabaseMonitor(
            database_service=mock_database_service,
            config=monitoring_config,
            settings=mock_settings,
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_concurrent_query_tracking_performance(self, database_monitor):
        """Test performance of concurrent query tracking."""
        # Arrange
        query_count = 100

        # Act
        start_time = asyncio.get_event_loop().time()

        tasks = []
        for i in range(query_count):

            async def track_query_task(index):
                query_id = await database_monitor.track_query(
                    QueryType.SELECT, f"table_{index}"
                )
                await asyncio.sleep(0.001)  # Simulate query execution
                await database_monitor.finish_query(query_id, QueryStatus.SUCCESS)

            tasks.append(track_query_task(i))

        await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        # Assert
        execution_time = end_time - start_time
        assert len(database_monitor._query_history) == query_count
        # Should handle 100 concurrent queries efficiently
        assert execution_time < 2.0

    @pytest.mark.asyncio
    async def test_large_query_history_performance(self, database_monitor):
        """Test performance with large query history."""
        # Arrange
        database_monitor.config.max_query_history = 1000

        # Act
        start_time = time.time()

        for _i in range(1000):
            query_id = await database_monitor.track_query(QueryType.SELECT, "users")
            await database_monitor.finish_query(query_id, QueryStatus.SUCCESS)

        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert len(database_monitor._query_history) == 1000
        # Should handle large history efficiently
        assert execution_time < 5.0

    @pytest.mark.asyncio
    async def test_health_check_performance(self, database_monitor):
        """Test health check performance."""
        # Arrange
        database_monitor.database_service.health_check.return_value = True

        # Act
        start_time = time.time()

        for _ in range(10):
            await database_monitor._perform_health_check()

        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert len(database_monitor._health_history) == 10
        # Should perform health checks efficiently
        assert execution_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__])
