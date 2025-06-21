"""
Comprehensive tests for TripSage Core WebSocket Performance Monitor.

This module provides comprehensive test coverage for WebSocket performance monitoring functionality
including metrics collection, alert generation, threshold monitoring, aggregation,
circuit breaker tracking, and historical data management.
"""

import asyncio
import time
from collections import deque
from datetime import datetime
from unittest.mock import Mock

import pytest

from tripsage_core.services.infrastructure.websocket_performance_monitor import (
    AggregatedMetrics,
    PerformanceAlert,
    PerformanceSnapshot,
    PerformanceThresholds,
    WebSocketPerformanceMonitor,
)


class TestPerformanceModels:
    """Test suite for performance monitoring models."""

    def test_performance_snapshot_creation(self):
        """Test PerformanceSnapshot dataclass creation."""
        timestamp = time.time()
        snapshot = PerformanceSnapshot(
            timestamp=timestamp,
            connection_id="conn_123",
            latency_ms=150.5,
            queue_size=10,
            error_count=2,
            message_rate=5.0,
            memory_usage_mb=25.7,
            circuit_breaker_state="closed",
            backpressure_active=False,
        )

        assert snapshot.timestamp == timestamp
        assert snapshot.connection_id == "conn_123"
        assert snapshot.latency_ms == 150.5
        assert snapshot.queue_size == 10
        assert snapshot.error_count == 2
        assert snapshot.message_rate == 5.0
        assert snapshot.memory_usage_mb == 25.7
        assert snapshot.circuit_breaker_state == "closed"
        assert snapshot.backpressure_active is False

    def test_aggregated_metrics_creation(self):
        """Test AggregatedMetrics dataclass creation."""
        start_time = time.time()
        end_time = start_time + 60

        metrics = AggregatedMetrics(
            start_time=start_time,
            end_time=end_time,
            connection_count=5,
            avg_latency_ms=125.0,
            p95_latency_ms=200.0,
            p99_latency_ms=350.0,
            total_messages=1000,
            total_errors=5,
            avg_queue_size=15.5,
            max_queue_size=50,
            circuit_breaker_trips=2,
            backpressure_events=3,
        )

        assert metrics.start_time == start_time
        assert metrics.end_time == end_time
        assert metrics.connection_count == 5
        assert metrics.avg_latency_ms == 125.0
        assert metrics.p95_latency_ms == 200.0
        assert metrics.p99_latency_ms == 350.0
        assert metrics.total_messages == 1000
        assert metrics.total_errors == 5
        assert metrics.avg_queue_size == 15.5
        assert metrics.max_queue_size == 50
        assert metrics.circuit_breaker_trips == 2
        assert metrics.backpressure_events == 3

    def test_performance_alert_creation(self):
        """Test PerformanceAlert model creation."""
        alert = PerformanceAlert(
            type="latency",
            severity="high",
            connection_id="conn_123",
            message="High latency detected",
            threshold=1000.0,
            current_value=1500.0,
        )

        assert alert.type == "latency"
        assert alert.severity == "high"
        assert alert.connection_id == "conn_123"
        assert alert.message == "High latency detected"
        assert alert.threshold == 1000.0
        assert alert.current_value == 1500.0
        assert alert.resolved is False
        assert isinstance(alert.id, str)
        assert isinstance(alert.timestamp, datetime)

    def test_performance_alert_without_connection(self):
        """Test PerformanceAlert without connection ID."""
        alert = PerformanceAlert(
            type="system",
            severity="critical",
            message="System-wide issue",
            threshold=0.0,
            current_value=1.0,
        )

        assert alert.connection_id is None
        assert alert.type == "system"

    def test_performance_thresholds_defaults(self):
        """Test PerformanceThresholds default values."""
        thresholds = PerformanceThresholds()

        assert thresholds.latency_warning_ms == 1000.0
        assert thresholds.latency_critical_ms == 2000.0
        assert thresholds.queue_size_warning == 1000
        assert thresholds.queue_size_critical == 1500
        assert thresholds.error_rate_warning == 0.05
        assert thresholds.error_rate_critical == 0.10
        assert thresholds.message_rate_min == 0.1
        assert thresholds.backpressure_duration_warning == 30.0

    def test_performance_thresholds_custom(self):
        """Test PerformanceThresholds with custom values."""
        thresholds = PerformanceThresholds(
            latency_warning_ms=500.0,
            latency_critical_ms=1000.0,
            queue_size_warning=500,
            queue_size_critical=1000,
            error_rate_warning=0.02,
            error_rate_critical=0.05,
            message_rate_min=0.5,
            backpressure_duration_warning=15.0,
        )

        assert thresholds.latency_warning_ms == 500.0
        assert thresholds.latency_critical_ms == 1000.0
        assert thresholds.queue_size_warning == 500
        assert thresholds.queue_size_critical == 1000
        assert thresholds.error_rate_warning == 0.02
        assert thresholds.error_rate_critical == 0.05
        assert thresholds.message_rate_min == 0.5
        assert thresholds.backpressure_duration_warning == 15.0


class TestWebSocketPerformanceMonitor:
    """Test suite for WebSocketPerformanceMonitor."""

    @pytest.fixture
    def performance_monitor(self):
        """Create WebSocketPerformanceMonitor instance."""
        return WebSocketPerformanceMonitor(collection_interval=0.1, aggregation_interval=1.0, retention_hours=1)

    @pytest.fixture
    def custom_performance_monitor(self):
        """Create WebSocketPerformanceMonitor with custom thresholds."""
        thresholds = PerformanceThresholds(
            latency_warning_ms=500.0,
            latency_critical_ms=1000.0,
            queue_size_warning=50,
            queue_size_critical=100,
        )
        return WebSocketPerformanceMonitor(
            collection_interval=0.1,
            aggregation_interval=1.0,
            retention_hours=1,
            thresholds=thresholds,
        )

    @pytest.fixture
    def mock_connection(self):
        """Create mock WebSocket connection."""
        connection = Mock()
        connection.connection_id = "test_connection_123"
        connection.message_count = 100
        connection.error_count = 5
        connection.state = Mock()
        connection.state.value = "connected"

        # Mock circuit breaker
        connection.circuit_breaker = Mock()
        connection.circuit_breaker.state = Mock()
        connection.circuit_breaker.state.value = "closed"

        # Mock health
        health = Mock()
        health.latency = 150.0
        health.queue_size = 20
        health.message_rate = 10.0
        health.backpressure_active = False
        connection.get_health.return_value = health

        return connection

    @pytest.fixture
    def mock_unhealthy_connection(self):
        """Create mock unhealthy WebSocket connection."""
        connection = Mock()
        connection.connection_id = "unhealthy_connection_456"
        connection.message_count = 50
        connection.error_count = 10
        connection.state = Mock()
        connection.state.value = "connected"

        # Mock circuit breaker in open state
        connection.circuit_breaker = Mock()
        connection.circuit_breaker.state = Mock()
        connection.circuit_breaker.state.value = "open"

        # Mock unhealthy health
        health = Mock()
        health.latency = 2500.0  # Above critical threshold
        health.queue_size = 2000  # Above critical threshold
        health.message_rate = 2.0
        health.backpressure_active = True
        connection.get_health.return_value = health

        return connection

    def test_monitor_initialization(self, performance_monitor):
        """Test performance monitor initialization."""
        assert performance_monitor.collection_interval == 0.1
        assert performance_monitor.aggregation_interval == 1.0
        assert performance_monitor.retention_hours == 1
        assert isinstance(performance_monitor.thresholds, PerformanceThresholds)
        assert isinstance(performance_monitor.snapshots, deque)
        assert isinstance(performance_monitor.aggregated_metrics, deque)
        assert isinstance(performance_monitor.active_alerts, dict)
        assert isinstance(performance_monitor.alert_history, deque)
        assert performance_monitor._running is False

    def test_monitor_custom_thresholds(self, custom_performance_monitor):
        """Test performance monitor with custom thresholds."""
        assert custom_performance_monitor.thresholds.latency_warning_ms == 500.0
        assert custom_performance_monitor.thresholds.latency_critical_ms == 1000.0
        assert custom_performance_monitor.thresholds.queue_size_warning == 50
        assert custom_performance_monitor.thresholds.queue_size_critical == 100

    @pytest.mark.asyncio
    async def test_start_stop_monitor(self, performance_monitor):
        """Test starting and stopping the performance monitor."""
        # Test start
        await performance_monitor.start()
        assert performance_monitor._running is True
        assert performance_monitor._monitor_task is not None
        assert performance_monitor._aggregation_task is not None
        assert performance_monitor._cleanup_task is not None

        # Test start idempotency
        await performance_monitor.start()
        assert performance_monitor._running is True

        # Test stop
        await performance_monitor.stop()
        assert performance_monitor._running is False

    def test_collect_connection_metrics_healthy(self, performance_monitor, mock_connection):
        """Test collecting metrics from healthy connection."""
        initial_snapshot_count = len(performance_monitor.snapshots)

        performance_monitor.collect_connection_metrics(mock_connection)

        # Check snapshot was added
        assert len(performance_monitor.snapshots) == initial_snapshot_count + 1

        # Check snapshot details
        snapshot = performance_monitor.snapshots[-1]
        assert snapshot.connection_id == "test_connection_123"
        assert snapshot.latency_ms == 150.0
        assert snapshot.queue_size == 20
        assert snapshot.error_count == 5
        assert snapshot.message_rate == 10.0
        assert snapshot.circuit_breaker_state == "closed"
        assert snapshot.backpressure_active is False

        # Check connection metrics were updated
        conn_metrics = performance_monitor.connection_metrics["test_connection_123"]
        assert conn_metrics["total_messages"] == 100
        assert conn_metrics["total_errors"] == 5
        assert conn_metrics["current_latency"] == 150.0
        assert conn_metrics["current_queue_size"] == 20
        assert conn_metrics["state"] == "connected"

    def test_collect_connection_metrics_unhealthy(self, custom_performance_monitor, mock_unhealthy_connection):
        """Test collecting metrics from unhealthy connection."""
        initial_alert_count = len(custom_performance_monitor.active_alerts)

        custom_performance_monitor.collect_connection_metrics(mock_unhealthy_connection)

        # Check snapshot was added
        assert len(custom_performance_monitor.snapshots) > 0

        # Check snapshot details
        snapshot = custom_performance_monitor.snapshots[-1]
        assert snapshot.connection_id == "unhealthy_connection_456"
        assert snapshot.latency_ms == 2500.0
        assert snapshot.queue_size == 2000
        assert snapshot.circuit_breaker_state == "open"
        assert snapshot.backpressure_active is True

        # Check alerts were generated
        assert len(custom_performance_monitor.active_alerts) > initial_alert_count

        # Check circuit breaker event was tracked
        assert "unhealthy_connection_456" in custom_performance_monitor.circuit_breaker_events

        # Check backpressure event was tracked
        assert "unhealthy_connection_456" in custom_performance_monitor.backpressure_events

    def test_collect_connection_metrics_error_handling(self, performance_monitor):
        """Test error handling during metrics collection."""
        # Create connection that raises exception during health check
        bad_connection = Mock()
        bad_connection.connection_id = "bad_connection"
        bad_connection.get_health.side_effect = Exception("Health check failed")

        # Should not raise exception
        performance_monitor.collect_connection_metrics(bad_connection)

        # No snapshot should be added
        assert len(performance_monitor.snapshots) == 0

    def test_latency_alert_generation(self, custom_performance_monitor, mock_connection):
        """Test latency alert generation."""
        # Set latency above warning threshold
        mock_connection.get_health.return_value.latency = 750.0

        custom_performance_monitor.collect_connection_metrics(mock_connection)

        # Check medium severity alert was generated
        latency_alerts = [
            alert
            for alert in custom_performance_monitor.active_alerts.values()
            if alert.type == "latency" and alert.severity == "medium"
        ]
        assert len(latency_alerts) > 0
        assert latency_alerts[0].current_value == 750.0
        assert latency_alerts[0].threshold == 500.0

    def test_critical_latency_alert_generation(self, custom_performance_monitor, mock_connection):
        """Test critical latency alert generation."""
        # Set latency above critical threshold
        mock_connection.get_health.return_value.latency = 1500.0

        custom_performance_monitor.collect_connection_metrics(mock_connection)

        # Check critical severity alert was generated
        latency_alerts = [
            alert
            for alert in custom_performance_monitor.active_alerts.values()
            if alert.type == "latency" and alert.severity == "critical"
        ]
        assert len(latency_alerts) > 0
        assert latency_alerts[0].current_value == 1500.0
        assert latency_alerts[0].threshold == 1000.0

    def test_queue_size_alert_generation(self, custom_performance_monitor, mock_connection):
        """Test queue size alert generation."""
        # Set queue size above warning threshold
        mock_connection.get_health.return_value.queue_size = 75

        custom_performance_monitor.collect_connection_metrics(mock_connection)

        # Check medium severity alert was generated
        queue_alerts = [
            alert
            for alert in custom_performance_monitor.active_alerts.values()
            if alert.type == "queue_size" and alert.severity == "medium"
        ]
        assert len(queue_alerts) > 0
        assert queue_alerts[0].current_value == 75
        assert queue_alerts[0].threshold == 50

    def test_error_rate_alert_generation(self, custom_performance_monitor, mock_connection):
        """Test error rate alert generation."""
        # Set high error count
        mock_connection.message_count = 100
        mock_connection.error_count = 8  # 8% error rate, above 5% warning

        custom_performance_monitor.collect_connection_metrics(mock_connection)

        # Check error rate alert was generated
        error_alerts = [
            alert for alert in custom_performance_monitor.active_alerts.values() if alert.type == "error_rate"
        ]
        assert len(error_alerts) > 0
        assert error_alerts[0].current_value == 0.08
        assert error_alerts[0].threshold == 0.05

    def test_circuit_breaker_alert_generation(self, performance_monitor, mock_connection):
        """Test circuit breaker alert generation."""
        # Set circuit breaker to open state
        mock_connection.circuit_breaker.state.value = "open"

        performance_monitor.collect_connection_metrics(mock_connection)

        # Check circuit breaker alert was generated
        cb_alerts = [alert for alert in performance_monitor.active_alerts.values() if alert.type == "circuit_breaker"]
        assert len(cb_alerts) > 0
        assert cb_alerts[0].severity == "high"
        assert cb_alerts[0].message == "Circuit breaker opened"

    def test_backpressure_duration_alert(self, performance_monitor, mock_connection):
        """Test backpressure duration alert generation."""
        # Simulate prolonged backpressure
        mock_connection.get_health.return_value.backpressure_active = True
        connection_id = mock_connection.connection_id

        # Add old backpressure event
        old_time = time.time() - 45.0  # 45 seconds ago
        performance_monitor.backpressure_events[connection_id].append(old_time)

        performance_monitor.collect_connection_metrics(mock_connection)

        # Check backpressure alert was generated
        bp_alerts = [alert for alert in performance_monitor.active_alerts.values() if alert.type == "backpressure"]
        assert len(bp_alerts) > 0
        assert bp_alerts[0].severity == "medium"
        assert "Prolonged backpressure" in bp_alerts[0].message

    def test_get_connection_performance(self, performance_monitor, mock_connection):
        """Test getting performance data for specific connection."""
        # Collect some metrics first
        performance_monitor.collect_connection_metrics(mock_connection)

        metrics = performance_monitor.get_connection_performance("test_connection_123")

        assert "connection_id" in metrics
        assert metrics["total_messages"] == 100
        assert metrics["total_errors"] == 5
        assert metrics["current_latency"] == 150.0
        assert metrics["state"] == "connected"

    def test_get_connection_performance_nonexistent(self, performance_monitor):
        """Test getting performance data for nonexistent connection."""
        metrics = performance_monitor.get_connection_performance("nonexistent")
        assert "error" in metrics
        assert metrics["error"] == "Connection not found"

    def test_get_performance_summary(self, performance_monitor, mock_connection):
        """Test getting performance summary."""
        # Initially should return no data
        summary = performance_monitor.get_performance_summary()
        assert summary["status"] == "no_data"

        # Add some aggregated metrics by triggering aggregation
        for _i in range(10):
            performance_monitor.collect_connection_metrics(mock_connection)

        # Manually trigger aggregation
        await_func = performance_monitor._aggregate_metrics()
        if hasattr(await_func, "__await__"):
            import asyncio

            asyncio.create_task(await_func)

        # Should still show no data until aggregation runs
        summary = performance_monitor.get_performance_summary()
        assert isinstance(summary, dict)

    def test_get_active_alerts(self, performance_monitor, mock_unhealthy_connection):
        """Test getting active alerts."""
        # Generate some alerts
        performance_monitor.collect_connection_metrics(mock_unhealthy_connection)

        alerts = performance_monitor.get_active_alerts()

        assert isinstance(alerts, list)
        assert len(alerts) > 0
        assert all(isinstance(alert, dict) for alert in alerts)

        # Check that alerts have expected fields
        if alerts:
            alert = alerts[0]
            assert "type" in alert
            assert "severity" in alert
            assert "message" in alert

    def test_export_metrics(self, performance_monitor, mock_connection):
        """Test exporting metrics."""
        # Collect some metrics
        performance_monitor.collect_connection_metrics(mock_connection)

        exported = performance_monitor.export_metrics()

        assert isinstance(exported, str)  # Returns JSON string

        # Parse JSON to verify structure
        import json

        data = json.loads(exported)
        assert "summary" in data
        assert "aggregated_metrics" in data
        assert "active_alerts" in data
        assert "connection_count" in data

    def test_snapshot_deque_max_length(self, performance_monitor, mock_connection):
        """Test snapshot deque respects max length."""
        # Fill up the deque beyond its max length
        original_maxlen = performance_monitor.snapshots.maxlen

        for _ in range(original_maxlen + 10):
            performance_monitor.collect_connection_metrics(mock_connection)

        # Should not exceed max length
        assert len(performance_monitor.snapshots) == original_maxlen

    def test_metrics_data_structure_consistency(self, performance_monitor, mock_connection):
        """Test that metrics data structures remain consistent."""
        # Collect metrics multiple times
        for i in range(10):
            mock_connection.connection_id = f"conn_{i}"
            performance_monitor.collect_connection_metrics(mock_connection)

        # Check data consistency
        assert len(performance_monitor.connection_metrics) <= 10
        assert all(isinstance(metrics, dict) for metrics in performance_monitor.connection_metrics.values())
        assert all(isinstance(snapshot, PerformanceSnapshot) for snapshot in performance_monitor.snapshots)

    def test_performance_under_load(self, performance_monitor):
        """Test performance monitor behavior under high load."""
        mock_connections = []

        # Create multiple mock connections
        for i in range(100):
            conn = Mock()
            conn.connection_id = f"load_test_conn_{i}"
            conn.message_count = i * 10
            conn.error_count = i % 5
            conn.state = Mock()
            conn.state.value = "connected"
            conn.circuit_breaker = Mock()
            conn.circuit_breaker.state = Mock()
            conn.circuit_breaker.state.value = "closed"

            health = Mock()
            health.latency = 100.0 + (i % 50)
            health.queue_size = i % 20
            health.message_rate = 5.0
            health.backpressure_active = False
            conn.get_health.return_value = health

            mock_connections.append(conn)

        # Collect metrics from all connections
        start_time = time.time()
        for conn in mock_connections:
            performance_monitor.collect_connection_metrics(conn)
        end_time = time.time()

        # Should complete reasonably quickly
        assert end_time - start_time < 1.0  # Less than 1 second

        # Check that data was collected
        assert len(performance_monitor.snapshots) == 100
        assert len(performance_monitor.connection_metrics) == 100


@pytest.mark.integration
class TestWebSocketPerformanceMonitorIntegration:
    """Integration tests for WebSocketPerformanceMonitor."""

    @pytest.mark.asyncio
    async def test_monitor_lifecycle_integration(self):
        """Test complete monitor lifecycle."""
        monitor = WebSocketPerformanceMonitor(collection_interval=0.05, aggregation_interval=0.1, retention_hours=1)

        try:
            # Start monitoring
            await monitor.start()
            assert monitor._running is True

            # Let it run briefly
            await asyncio.sleep(0.2)

            # Stop monitoring
            await monitor.stop()
            assert monitor._running is False

        except Exception as e:
            # Clean up on error
            await monitor.stop()
            raise e

    @pytest.mark.asyncio
    async def test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection."""
        monitor = WebSocketPerformanceMonitor()

        # Create multiple mock connections
        connections = []
        for i in range(10):
            conn = Mock()
            conn.connection_id = f"concurrent_conn_{i}"
            conn.message_count = 100
            conn.error_count = 5
            conn.state = Mock()
            conn.state.value = "connected"
            conn.circuit_breaker = Mock()
            conn.circuit_breaker.state = Mock()
            conn.circuit_breaker.state.value = "closed"

            health = Mock()
            health.latency = 150.0
            health.queue_size = 20
            health.message_rate = 10.0
            health.backpressure_active = False
            conn.get_health.return_value = health

            connections.append(conn)

        # Collect metrics concurrently
        tasks = []
        for conn in connections:
            task = asyncio.create_task(asyncio.to_thread(monitor.collect_connection_metrics, conn))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Verify all metrics were collected
        assert len(monitor.snapshots) == 10
        assert len(monitor.connection_metrics) == 10

    @pytest.mark.asyncio
    async def test_alert_lifecycle_integration(self):
        """Test complete alert lifecycle."""
        monitor = WebSocketPerformanceMonitor(thresholds=PerformanceThresholds(latency_warning_ms=100.0))

        # Create connection that will trigger alert
        conn = Mock()
        conn.connection_id = "alert_test_conn"
        conn.message_count = 100
        conn.error_count = 5
        conn.state = Mock()
        conn.state.value = "connected"
        conn.circuit_breaker = Mock()
        conn.circuit_breaker.state = Mock()
        conn.circuit_breaker.state.value = "closed"

        health = Mock()
        health.latency = 200.0  # Above warning threshold
        health.queue_size = 20
        health.message_rate = 10.0
        health.backpressure_active = False
        conn.get_health.return_value = health

        # Collect metrics to trigger alert
        monitor.collect_connection_metrics(conn)

        # Verify alert was created
        active_alerts = monitor.get_active_alerts()
        assert len(active_alerts) > 0

        # Check alert structure (returned as dict, not object)
        alert = active_alerts[0]
        assert "id" in alert
        assert "type" in alert
        assert alert["type"] == "latency"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
