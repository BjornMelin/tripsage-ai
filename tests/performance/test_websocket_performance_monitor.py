"""
Tests for WebSocket performance monitoring.

This test suite validates the WebSocket performance monitoring infrastructure including:
- Metrics collection and aggregation
- Performance alert generation
- Historical data retention
- Real-time monitoring capabilities
"""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.services.infrastructure.websocket_connection_service import (
    ConnectionHealth,
    ConnectionState,
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_performance_monitor import (
    PerformanceAlert,
    PerformanceThresholds,
    WebSocketPerformanceMonitor,
)


@pytest.fixture
def performance_monitor():
    """Create a WebSocket performance monitor for testing."""
    thresholds = PerformanceThresholds(
        latency_warning_ms=100.0,
        latency_critical_ms=200.0,
        queue_size_warning=50,
        queue_size_critical=100,
        error_rate_warning=0.05,
        error_rate_critical=0.10,
    )
    
    monitor = WebSocketPerformanceMonitor(
        collection_interval=0.1,  # Fast for testing
        aggregation_interval=1.0,  # Fast for testing
        retention_hours=1,  # Short for testing
        thresholds=thresholds
    )
    
    return monitor


@pytest.fixture
def mock_websocket_connection():
    """Create a mock WebSocket connection for testing."""
    connection = MagicMock(spec=WebSocketConnection)
    connection.connection_id = "test_connection_1"
    connection.state = ConnectionState.CONNECTED
    connection.message_count = 100
    connection.error_count = 2
    connection.last_activity = time.time()
    
    # Mock circuit breaker
    connection.circuit_breaker = MagicMock()
    connection.circuit_breaker.state = MagicMock()
    connection.circuit_breaker.state.value = "CLOSED"
    
    return connection


@pytest.fixture
def mock_connection_health():
    """Create mock connection health metrics."""
    return ConnectionHealth(
        latency=50.0,
        message_rate=10.0,
        error_rate=0.02,
        reconnect_count=0,
        last_activity=datetime.now(),
        quality="excellent",
        queue_size=25,
        backpressure_active=False,
        dropped_messages=0
    )


@pytest.mark.performance
@pytest.mark.asyncio
class TestWebSocketPerformanceMonitor:
    """Test suite for WebSocket performance monitoring."""
    
    async def test_monitor_startup_and_shutdown(self, performance_monitor):
        """Test monitor starts and stops correctly."""
        assert not performance_monitor._running
        
        await performance_monitor.start()
        assert performance_monitor._running
        assert performance_monitor._monitor_task is not None
        assert performance_monitor._aggregation_task is not None
        assert performance_monitor._cleanup_task is not None
        
        await performance_monitor.stop()
        assert not performance_monitor._running
    
    def test_collect_connection_metrics(
        self, performance_monitor, mock_websocket_connection, mock_connection_health
    ):
        """Test metrics collection from WebSocket connections."""
        # Mock the get_health method
        mock_websocket_connection.get_health.return_value = mock_connection_health
        
        # Collect metrics
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify snapshot was created
        assert len(performance_monitor.snapshots) == 1
        snapshot = performance_monitor.snapshots[0]
        
        assert snapshot.connection_id == "test_connection_1"
        assert snapshot.latency_ms == 50.0
        assert snapshot.queue_size == 25
        assert snapshot.error_count == 2
        assert snapshot.circuit_breaker_state == "CLOSED"
        assert not snapshot.backpressure_active
        
        # Verify connection metrics were updated
        assert "test_connection_1" in performance_monitor.connection_metrics
        metrics = performance_monitor.connection_metrics["test_connection_1"]
        assert metrics["total_messages"] == 100
        assert metrics["total_errors"] == 2
        assert metrics["current_latency"] == 50.0
    
    def test_latency_alert_generation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test alert generation for high latency."""
        # Create high latency health metrics
        high_latency_health = ConnectionHealth(
            latency=150.0,  # Above warning threshold (100ms)
            message_rate=10.0,
            error_rate=0.02,
            reconnect_count=0,
            last_activity=datetime.now(),
            quality="poor",
            queue_size=25,
            backpressure_active=False,
            dropped_messages=0
        )
        
        mock_websocket_connection.get_health.return_value = high_latency_health
        
        # Collect metrics (should trigger alert)
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify alert was created
        assert len(performance_monitor.active_alerts) == 1
        alert_key = "latency_test_connection_1"
        assert alert_key in performance_monitor.active_alerts
        
        alert = performance_monitor.active_alerts[alert_key]
        assert alert.type == "latency"
        assert alert.severity == "medium"  # Warning level
        assert alert.current_value == 150.0
        assert alert.threshold == 100.0
    
    def test_critical_latency_alert_generation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test critical alert generation for very high latency."""
        # Create critical latency health metrics
        critical_latency_health = ConnectionHealth(
            latency=250.0,  # Above critical threshold (200ms)
            message_rate=10.0,
            error_rate=0.02,
            reconnect_count=0,
            last_activity=datetime.now(),
            quality="critical",
            queue_size=25,
            backpressure_active=False,
            dropped_messages=0
        )
        
        mock_websocket_connection.get_health.return_value = critical_latency_health
        
        # Collect metrics (should trigger critical alert)
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify critical alert was created
        assert len(performance_monitor.active_alerts) == 1
        alert_key = "latency_test_connection_1"
        alert = performance_monitor.active_alerts[alert_key]
        assert alert.severity == "critical"
        assert alert.current_value == 250.0
    
    def test_queue_size_alert_generation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test alert generation for high queue size."""
        # Create high queue size health metrics
        high_queue_health = ConnectionHealth(
            latency=50.0,
            message_rate=10.0,
            error_rate=0.02,
            reconnect_count=0,
            last_activity=datetime.now(),
            quality="good",
            queue_size=75,  # Above warning threshold (50)
            backpressure_active=False,
            dropped_messages=0
        )
        
        mock_websocket_connection.get_health.return_value = high_queue_health
        
        # Collect metrics (should trigger alert)
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify alert was created
        alert_key = "queue_size_test_connection_1"
        assert alert_key in performance_monitor.active_alerts
        
        alert = performance_monitor.active_alerts[alert_key]
        assert alert.type == "queue_size"
        assert alert.severity == "medium"
        assert alert.current_value == 75
    
    def test_error_rate_alert_generation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test alert generation for high error rate."""
        # Set up connection with high error rate
        mock_websocket_connection.message_count = 100
        mock_websocket_connection.error_count = 8  # 8% error rate (above 5% warning)
        
        normal_health = ConnectionHealth(
            latency=50.0,
            message_rate=10.0,
            error_rate=0.08,
            reconnect_count=0,
            last_activity=datetime.now(),
            quality="good",
            queue_size=25,
            backpressure_active=False,
            dropped_messages=0
        )
        
        mock_websocket_connection.get_health.return_value = normal_health
        
        # Collect metrics (should trigger error rate alert)
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify alert was created
        alert_key = "error_rate_test_connection_1"
        assert alert_key in performance_monitor.active_alerts
        
        alert = performance_monitor.active_alerts[alert_key]
        assert alert.type == "error_rate"
        assert alert.severity == "medium"
        assert alert.current_value == 0.08
    
    def test_circuit_breaker_alert_generation(
        self, performance_monitor, mock_websocket_connection, mock_connection_health
    ):
        """Test alert generation for circuit breaker events."""
        # Set circuit breaker to OPEN state
        mock_websocket_connection.circuit_breaker.state.value = "OPEN"
        mock_websocket_connection.get_health.return_value = mock_connection_health
        
        # Collect metrics (should trigger circuit breaker alert)
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify alert was created
        alert_key = "circuit_breaker_test_connection_1"
        assert alert_key in performance_monitor.active_alerts
        
        alert = performance_monitor.active_alerts[alert_key]
        assert alert.type == "circuit_breaker"
        assert alert.severity == "high"
        assert alert.current_value == 1
    
    def test_backpressure_alert_generation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test alert generation for prolonged backpressure."""
        # Create backpressure health metrics
        backpressure_health = ConnectionHealth(
            latency=50.0,
            message_rate=10.0,
            error_rate=0.02,
            reconnect_count=0,
            last_activity=datetime.now(),
            quality="good",
            queue_size=25,
            backpressure_active=True,
            dropped_messages=5
        )
        
        mock_websocket_connection.get_health.return_value = backpressure_health
        
        # Simulate backpressure events over time
        current_time = time.time()
        
        # Add some backpressure events in the past
        performance_monitor.backpressure_events["test_connection_1"] = [
            current_time - 40,  # 40 seconds ago (within warning threshold)
            current_time - 35,
            current_time - 30,
        ]
        
        # Collect metrics (should trigger backpressure alert)
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Verify alert was created
        alert_key = "backpressure_test_connection_1"
        assert alert_key in performance_monitor.active_alerts
        
        alert = performance_monitor.active_alerts[alert_key]
        assert alert.type == "backpressure"
        assert alert.severity == "medium"
    
    def test_alert_cooldown_mechanism(
        self, performance_monitor, mock_websocket_connection, mock_connection_health
    ):
        """Test that alerts have cooldown to prevent spam."""
        # Create high latency health
        high_latency_health = ConnectionHealth(
            latency=150.0,  # Above warning threshold
            message_rate=10.0,
            error_rate=0.02,
            reconnect_count=0,
            last_activity=datetime.now(),
            quality="poor",
            queue_size=25,
            backpressure_active=False,
            dropped_messages=0
        )
        
        mock_websocket_connection.get_health.return_value = high_latency_health
        
        # Collect metrics twice quickly
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        initial_alert_count = len(performance_monitor.active_alerts)
        
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        final_alert_count = len(performance_monitor.active_alerts)
        
        # Should only have one alert due to cooldown
        assert initial_alert_count == final_alert_count == 1
    
    async def test_metrics_aggregation(self, performance_monitor, mock_websocket_connection):
        """Test periodic metrics aggregation."""
        # Create multiple snapshots with different latencies
        latencies = [25.0, 50.0, 75.0, 100.0, 125.0]
        
        for latency in latencies:
            health = ConnectionHealth(
                latency=latency,
                message_rate=10.0,
                error_rate=0.02,
                reconnect_count=0,
                last_activity=datetime.now(),
                quality="good",
                queue_size=25,
                backpressure_active=False,
                dropped_messages=0
            )
            
            mock_websocket_connection.get_health.return_value = health
            performance_monitor.collect_connection_metrics(mock_websocket_connection)
            
            # Small delay to spread timestamps
            await asyncio.sleep(0.01)
        
        # Trigger aggregation
        await performance_monitor._aggregate_metrics()
        
        # Verify aggregated metrics were created
        assert len(performance_monitor.aggregated_metrics) == 1
        
        aggregated = performance_monitor.aggregated_metrics[0]
        assert aggregated.connection_count == 1
        assert aggregated.avg_latency_ms == 75.0  # Average of latencies
        assert aggregated.p95_latency_ms == 125.0  # 95th percentile
        assert aggregated.p99_latency_ms == 125.0  # 99th percentile (same as p95 for small dataset)
    
    def test_performance_summary(self, performance_monitor):
        """Test performance summary generation."""
        # Initially no data
        summary = performance_monitor.get_performance_summary()
        assert summary["status"] == "no_data"
        
        # Add some aggregated metrics
        from tripsage_core.services.infrastructure.websocket_performance_monitor import AggregatedMetrics
        
        current_time = time.time()
        metrics = AggregatedMetrics(
            start_time=current_time - 60,
            end_time=current_time,
            connection_count=5,
            avg_latency_ms=75.0,
            p95_latency_ms=120.0,
            p99_latency_ms=150.0,
            total_messages=500,
            total_errors=10,
            avg_queue_size=30.0,
            max_queue_size=80,
            circuit_breaker_trips=1,
            backpressure_events=2
        )
        
        performance_monitor.aggregated_metrics.append(metrics)
        
        # Get summary
        summary = performance_monitor.get_performance_summary()
        
        assert summary["connection_count"] == 5
        assert summary["avg_latency_ms"] == 75.0
        assert summary["p95_latency_ms"] == 120.0
        assert summary["total_messages"] == 500
        assert summary["total_errors"] == 10
        assert summary["circuit_breaker_trips"] == 1
        assert summary["backpressure_events"] == 2
        
        # Health score should be calculated (100 - penalties)
        assert 0 <= summary["health_score"] <= 100
        assert summary["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_connection_performance_details(
        self, performance_monitor, mock_websocket_connection, mock_connection_health
    ):
        """Test individual connection performance details."""
        # Collect some metrics
        mock_websocket_connection.get_health.return_value = mock_connection_health
        performance_monitor.collect_connection_metrics(mock_websocket_connection)
        
        # Get connection performance
        perf = performance_monitor.get_connection_performance("test_connection_1")
        
        assert perf["connection_id"] == "test_connection_1"
        assert perf["total_messages"] == 100
        assert perf["total_errors"] == 2
        assert perf["current_latency"] == 50.0
        assert perf["state"] == "connected"
        assert perf["circuit_breaker_state"] == "CLOSED"
        assert not perf["backpressure_active"]
        
        # Test non-existent connection
        unknown_perf = performance_monitor.get_connection_performance("unknown")
        assert "error" in unknown_perf
    
    def test_metrics_export(self, performance_monitor):
        """Test metrics export functionality."""
        # Add some test data
        from tripsage_core.services.infrastructure.websocket_performance_monitor import AggregatedMetrics
        
        current_time = time.time()
        metrics = AggregatedMetrics(
            start_time=current_time - 60,
            end_time=current_time,
            connection_count=3,
            avg_latency_ms=50.0,
            p95_latency_ms=80.0,
            p99_latency_ms=100.0,
            total_messages=300,
            total_errors=5,
            avg_queue_size=20.0,
            max_queue_size=40,
            circuit_breaker_trips=0,
            backpressure_events=1
        )
        
        performance_monitor.aggregated_metrics.append(metrics)
        
        # Export as JSON
        exported = performance_monitor.export_metrics("json")
        assert isinstance(exported, str)
        
        # Parse and verify structure
        import json
        data = json.loads(exported)
        
        assert "summary" in data
        assert "aggregated_metrics" in data
        assert "active_alerts" in data
        assert "connection_count" in data
        assert "export_timestamp" in data
        
        # Test unsupported format
        with pytest.raises(ValueError, match="Unsupported format"):
            performance_monitor.export_metrics("xml")
    
    async def test_data_cleanup(self, performance_monitor):
        """Test cleanup of old data."""
        # Add old data
        old_time = time.time() - 7200  # 2 hours ago
        
        # Add old snapshots and events
        performance_monitor.circuit_breaker_events["old_connection"] = [old_time]
        performance_monitor.backpressure_events["old_connection"] = [old_time]
        
        # Add old active alert
        old_alert = PerformanceAlert(
            type="latency",
            severity="medium",
            connection_id="old_connection",
            message="Old alert",
            threshold=100.0,
            current_value=150.0,
            timestamp=datetime.now() - timedelta(hours=2)
        )
        performance_monitor.active_alerts["old_alert"] = old_alert
        
        # Run cleanup
        await performance_monitor._cleanup_old_data()
        
        # Verify old data was cleaned up
        assert "old_connection" not in performance_monitor.circuit_breaker_events
        assert "old_connection" not in performance_monitor.backpressure_events
        assert "old_alert" not in performance_monitor.active_alerts
        assert old_alert.resolved
    
    @pytest.mark.slow
    async def test_full_monitoring_cycle(self, performance_monitor):
        """Test complete monitoring cycle with start/stop."""
        # Start monitoring
        await performance_monitor.start()
        
        # Let it run briefly
        await asyncio.sleep(0.2)
        
        # Verify background tasks are running
        assert performance_monitor._running
        assert not performance_monitor._monitor_task.done()
        assert not performance_monitor._aggregation_task.done()
        assert not performance_monitor._cleanup_task.done()
        
        # Stop monitoring
        await performance_monitor.stop()
        
        # Verify tasks are stopped
        assert not performance_monitor._running
        assert performance_monitor._monitor_task.done()
        assert performance_monitor._aggregation_task.done()
        assert performance_monitor._cleanup_task.done()


@pytest.mark.performance
def test_performance_thresholds_validation():
    """Test performance thresholds validation."""
    # Test default thresholds
    thresholds = PerformanceThresholds()
    assert thresholds.latency_warning_ms == 1000.0
    assert thresholds.latency_critical_ms == 2000.0
    
    # Test custom thresholds
    custom_thresholds = PerformanceThresholds(
        latency_warning_ms=50.0,
        latency_critical_ms=100.0,
        queue_size_warning=20,
        queue_size_critical=50
    )
    assert custom_thresholds.latency_warning_ms == 50.0
    assert custom_thresholds.queue_size_warning == 20


@pytest.mark.performance
def test_performance_alert_model():
    """Test performance alert data model."""
    alert = PerformanceAlert(
        type="latency",
        severity="critical",
        connection_id="test_conn",
        message="High latency detected",
        threshold=100.0,
        current_value=250.0
    )
    
    assert alert.type == "latency"
    assert alert.severity == "critical"
    assert alert.connection_id == "test_conn"
    assert alert.threshold == 100.0
    assert alert.current_value == 250.0
    assert not alert.resolved
    assert alert.id is not None  # UUID should be generated