"""
Integration tests for database monitoring system.

Tests the complete monitoring stack including metrics collection,
health monitoring, security alerts, and database service integration.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    reset_database_metrics,
)
from tripsage_core.services.infrastructure.database_monitor import (
    ConsolidatedDatabaseMonitor,
    HealthStatus,
    SecurityEvent,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.database_wrapper import (
    DatabaseServiceWrapper,
)


class TestDatabaseMonitoringIntegration:
    """Integration tests for the complete monitoring system."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset global metrics state
        reset_database_metrics()

        # Create test settings
        self.settings = Settings(
            enable_database_monitoring=True,
            enable_prometheus_metrics=True,
            enable_security_monitoring=True,
            db_health_check_interval=0.1,  # Fast for testing
            db_security_check_interval=0.2,
        )

        # Mock database service
        self.mock_db_service = Mock(spec=DatabaseService)
        self.mock_db_service.is_connected = True
        self.mock_db_service.health_check = AsyncMock(return_value=True)
        self.mock_db_service.get_database_stats = AsyncMock(
            return_value={"connections": 5, "tables": ["users", "trips"]}
        )
        self.mock_db_service.select = AsyncMock(return_value=[{"id": "test"}])
        self.mock_db_service.connect = AsyncMock()
        self.mock_db_service.close = AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_monitoring_flow(self):
        """Test complete monitoring flow from start to finish."""
        # Create monitoring components
        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Start monitoring
        await monitor.start_monitoring()

        try:
            # Wait for a few monitoring cycles
            await asyncio.sleep(0.5)

            # Verify health checks occurred
            assert monitor.get_current_health() is not None
            assert monitor.get_current_health().status == HealthStatus.HEALTHY

            # Verify metrics were recorded
            summary = metrics.get_metrics_summary()
            assert len(summary["health_status"]) > 0

            # Get monitoring status
            status = monitor.get_monitoring_status()
            assert status["monitoring_active"] is True
            assert status["health_history_count"] > 0

        finally:
            # Stop monitoring
            await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_monitoring_with_database_failures(self):
        """Test monitoring behavior with database failures."""
        # Set up failing database service
        self.mock_db_service.health_check = AsyncMock(return_value=False)
        self.mock_db_service.is_connected = False

        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Collect alerts
        alerts = []

        def alert_callback(alert):
            alerts.append(alert)

        monitor.add_alert_callback(alert_callback)

        # Start monitoring
        await monitor.start_monitoring()

        try:
            # Wait for monitoring cycles
            await asyncio.sleep(0.5)

            # Also do a manual health check to ensure it works
            manual_health = await monitor.manual_health_check()
            assert manual_health is not None
            assert manual_health.status == HealthStatus.CRITICAL

            # Verify health check shows critical status
            current_health = monitor.get_current_health()
            assert current_health is not None
            assert current_health.status == HealthStatus.CRITICAL

            # Verify alerts were triggered
            assert len(alerts) > 0
            assert any(
                alert.event_type == SecurityEvent.CONNECTION_FAILURE for alert in alerts
            )

            # Verify metrics recorded unhealthy status
            summary = metrics.get_metrics_summary()
            health_metrics = summary["health_status"]
            # Should have unhealthy (0.0) status recorded
            assert any(value == 0.0 for value in health_metrics.values())

        finally:
            await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_wrapper_integration_with_monitoring(self):
        """Test database wrapper integration with monitoring."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ) as mock_db_class:
            mock_db_class.return_value = self.mock_db_service

            # Create wrapper with monitoring enabled
            wrapper = DatabaseServiceWrapper(self.settings)

            # Connect (should start monitoring)
            await wrapper.connect()

            try:
                # Perform database operations
                await wrapper.select("users", "*")
                await wrapper.insert("users", {"name": "test"})
                await wrapper.update("users", {"name": "updated"}, {"id": "123"})
                await wrapper.delete("users", {"id": "123"})

                # Wait for monitoring to collect data
                await asyncio.sleep(0.3)

                # Check monitoring status
                monitoring_status = wrapper.get_monitoring_status()
                assert monitoring_status is not None
                assert monitoring_status["monitoring_active"] is True

                # Check metrics
                metrics_summary = wrapper.get_metrics_summary()
                assert metrics_summary is not None
                assert len(metrics_summary["query_total"]) > 0

                # Check health
                health = wrapper.get_current_health()
                assert health is not None

            finally:
                await wrapper.close()

    @pytest.mark.asyncio
    async def test_wrapper_without_monitoring(self):
        """Test database wrapper without monitoring enabled."""
        settings_no_monitoring = Settings(
            enable_database_monitoring=False,
            enable_prometheus_metrics=False,
        )

        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ) as mock_db_class:
            mock_db_class.return_value = self.mock_db_service

            # Create wrapper with monitoring disabled
            wrapper = DatabaseServiceWrapper(settings_no_monitoring)

            await wrapper.connect()

            try:
                # Perform database operations
                await wrapper.select("users", "*")
                await wrapper.insert("users", {"name": "test"})

                # Check that monitoring methods return None
                assert wrapper.get_monitoring_status() is None
                assert wrapper.get_metrics_summary() is None
                assert wrapper.get_current_health() is None

            finally:
                await wrapper.close()

    @pytest.mark.asyncio
    async def test_recovery_mechanism(self):
        """Test automatic recovery mechanism."""
        # Start with disconnected database
        self.mock_db_service.is_connected = False
        self.mock_db_service.health_check = AsyncMock(return_value=False)

        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Mock recovery success on second attempt
        connect_calls = 0

        async def mock_connect():
            nonlocal connect_calls
            connect_calls += 1
            if connect_calls >= 2:
                self.mock_db_service.is_connected = True
                self.mock_db_service.health_check = AsyncMock(return_value=True)

        self.mock_db_service.connect.side_effect = mock_connect

        # Collect alerts to verify recovery
        alerts = []
        monitor.add_alert_callback(alerts.append)

        # Start monitoring
        await monitor.start_monitoring()

        try:
            # Trigger manual health check to force recovery attempt
            await monitor.manual_health_check()

            # Wait for recovery to happen
            await asyncio.sleep(0.5)

            # Should have recovery-related alerts
            recovery_alerts = [a for a in alerts if "recovered" in a.message]
            assert len(recovery_alerts) > 0

        finally:
            await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_security_monitoring_integration(self):
        """Test security monitoring with high error rates."""
        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Simulate high error rate
        for _i in range(15):  # Above threshold of 10
            metrics.record_query(
                "supabase", "SELECT", "users", 0.1, False, "TimeoutError"
            )

        alerts = []
        monitor.add_alert_callback(alerts.append)

        # Start monitoring
        await monitor.start_monitoring()

        try:
            # Wait for security check
            await asyncio.sleep(0.3)

            # Should trigger suspicious query alert
            security_alerts = [
                a for a in alerts if a.event_type == SecurityEvent.SUSPICIOUS_QUERY
            ]
            assert len(security_alerts) > 0

        finally:
            await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_metrics_collection_accuracy(self):
        """Test accuracy of metrics collection."""
        metrics = DatabaseMetrics()

        # Record various operations
        metrics.record_connection_attempt("supabase", True, 0.5)
        metrics.record_connection_attempt("supabase", False, 1.0)

        metrics.set_active_connections("supabase", 10)

        # Record successful queries
        for _i in range(5):
            metrics.record_query("supabase", "SELECT", "users", 0.1, True)

        # Record failed queries
        for _i in range(3):
            metrics.record_query(
                "supabase", "INSERT", "users", 0.05, False, "ValidationError"
            )

        # Record health checks
        metrics.record_health_check("supabase", True)
        metrics.record_health_check("supabase", False)

        # Verify metrics
        summary = metrics.get_metrics_summary()

        # Check connection attempts
        connection_attempts = summary["connection_attempts"]
        assert len(connection_attempts) == 2  # success and error

        # Check active connections
        active_connections = summary["active_connections"]
        supabase_active = next(
            (v for k, v in active_connections.items() if "supabase" in k), None
        )
        assert supabase_active == 10

        # Check query totals
        query_totals = summary["query_total"]
        assert len(query_totals) > 0

        # Check query errors
        query_errors = summary["query_errors"]
        assert len(query_errors) > 0

        # Check health status (should be last recorded - False = 0.0)
        health_status = summary["health_status"]
        supabase_health = next(
            (v for k, v in health_status.items() if "supabase" in k), None
        )
        assert supabase_health == 0.0

    @pytest.mark.asyncio
    async def test_concurrent_monitoring_operations(self):
        """Test monitoring under concurrent operations."""
        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Start monitoring
        await monitor.start_monitoring()

        try:
            # Simulate concurrent database operations
            async def worker(worker_id):
                for _i in range(10):
                    with metrics.time_query("supabase", "SELECT", f"table_{worker_id}"):
                        await asyncio.sleep(0.01)

                    metrics.record_query(
                        "supabase", "INSERT", f"table_{worker_id}", 0.01, True
                    )

            # Run multiple workers concurrently
            tasks = [worker(i) for i in range(5)]
            await asyncio.gather(*tasks)

            # Wait for monitoring to process
            await asyncio.sleep(0.2)

            # Verify metrics were collected from all workers
            summary = metrics.get_metrics_summary()
            query_totals = summary["query_total"]

            # Should have metrics from multiple tables
            table_metrics = [k for k in query_totals.keys() if "table_" in k]
            assert len(table_metrics) > 0

        finally:
            await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_monitoring_configuration_changes(self):
        """Test changing monitoring configuration at runtime."""
        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Start with default intervals

        # Start monitoring
        await monitor.start_monitoring()

        try:
            # Change configuration
            new_health_interval = 0.05
            new_security_interval = 0.1

            monitor.configure_monitoring(
                health_check_interval=new_health_interval,
                security_check_interval=new_security_interval,
                max_recovery_attempts=5,
                recovery_delay=2.0,
            )

            # Verify configuration was updated
            assert monitor._health_check_interval == new_health_interval
            assert monitor._security_check_interval == new_security_interval
            assert monitor._max_recovery_attempts == 5
            assert monitor._recovery_delay == 2.0

            # Wait for operations with new intervals
            await asyncio.sleep(0.3)

            # Verify monitoring still works
            status = monitor.get_monitoring_status()
            assert status["monitoring_active"] is True
            assert status["health_check_interval"] == new_health_interval

        finally:
            await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_alert_callback_functionality(self):
        """Test alert callback system."""
        metrics = DatabaseMetrics()
        monitor = ConsolidatedDatabaseMonitor(
            database_service=self.mock_db_service,
            settings=self.settings,
            metrics=metrics,
        )

        # Set up multiple callbacks
        callback1_alerts = []
        callback2_alerts = []

        def callback1(alert):
            callback1_alerts.append(alert)

        def callback2(alert):
            callback2_alerts.append(alert)

        monitor.add_alert_callback(callback1)
        monitor.add_alert_callback(callback2)

        # Trigger a manual alert
        from tripsage_core.services.infrastructure.database_monitor import SecurityAlert

        test_alert = SecurityAlert(
            event_type=SecurityEvent.CONNECTION_FAILURE,
            severity="warning",
            message="Test alert",
            details={},
        )

        await monitor._trigger_alert(test_alert)

        # Verify both callbacks received the alert
        assert len(callback1_alerts) == 1
        assert len(callback2_alerts) == 1
        assert callback1_alerts[0] == test_alert
        assert callback2_alerts[0] == test_alert

        # Remove one callback
        monitor.remove_alert_callback(callback1)

        # Trigger another alert
        test_alert2 = SecurityAlert(
            event_type=SecurityEvent.RATE_LIMIT_EXCEEDED,
            severity="info",
            message="Another test",
            details={},
        )

        await monitor._trigger_alert(test_alert2)

        # Only callback2 should receive the second alert
        assert len(callback1_alerts) == 1  # Still 1
        assert len(callback2_alerts) == 2  # Now 2

    def test_metrics_server_integration(self):
        """Test Prometheus metrics server integration."""
        metrics = DatabaseMetrics()

        # Record some metrics
        metrics.record_connection_attempt("supabase", True, 0.5)
        metrics.set_active_connections("supabase", 5)
        metrics.record_query("supabase", "SELECT", "users", 0.1, True)

        # Test metrics server startup (mocked)
        with patch(
            "tripsage_core.monitoring.database_metrics.start_http_server"
        ) as mock_start_server:
            metrics.start_metrics_server(8001)
            mock_start_server.assert_called_once_with(8001, registry=metrics.registry)

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when monitoring components fail."""
        # Create wrapper with failing monitoring initialization
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_class,
        ):
            mock_get_metrics.side_effect = Exception("Metrics initialization failed")
            mock_db_class.return_value = self.mock_db_service

            # Should create wrapper without monitoring
            wrapper = DatabaseServiceWrapper(self.settings)

            # Should still work for database operations
            await wrapper.connect()

            try:
                result = await wrapper.select("users", "*")
                assert result == [{"id": "test"}]

                # Monitoring methods should return None
                assert wrapper.get_monitoring_status() is None
                assert wrapper.get_metrics_summary() is None

            finally:
                await wrapper.close()
