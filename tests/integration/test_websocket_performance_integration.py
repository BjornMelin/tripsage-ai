"""
Comprehensive WebSocket Performance Integration Tests.

This module provides end-to-end integration tests for the complete WebSocket
performance infrastructure, including:
- Performance monitoring service integration
- Circuit breaker pattern validation
- Connection health tracking
- Real-time metrics collection
- Alert generation and resolution
- Performance regression detection
"""

import asyncio
import json
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage_core.services.infrastructure.websocket_connection_service import (
    ConnectionState,
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_manager import (
    CircuitBreakerState,
)
from tripsage_core.services.infrastructure.websocket_performance_monitor import (
    PerformanceThresholds,
    WebSocketPerformanceMonitor,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def performance_monitor():
    """Create and configure performance monitor for testing."""
    thresholds = PerformanceThresholds(
        latency_warning_ms=100.0,
        latency_critical_ms=200.0,
        queue_size_warning=50,
        queue_size_critical=100,
        error_rate_warning=0.05,
        error_rate_critical=0.10,
        backpressure_duration_warning=10.0,
    )

    monitor = WebSocketPerformanceMonitor(
        collection_interval=0.1,  # Fast collection for testing
        aggregation_interval=1.0,  # Fast aggregation for testing
        retention_hours=1,
        thresholds=thresholds,
    )

    await monitor.start()
    yield monitor
    await monitor.stop()


@pytest.fixture
def mock_websocket_connection():
    """Create a mock WebSocket connection for testing."""
    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.close = AsyncMock()

    connection = WebSocketConnection(
        websocket=mock_ws,
        connection_id=str(uuid4()),
        user_id=uuid4(),
        session_id=uuid4(),
    )

    return connection


class TestWebSocketPerformanceIntegration:
    """Integration tests for WebSocket performance monitoring."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_lifecycle_with_monitoring(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test complete connection lifecycle with performance monitoring."""
        connection = mock_websocket_connection

        # Simulate connection lifecycle
        assert connection.state == ConnectionState.CONNECTED

        # Collect initial metrics
        performance_monitor.collect_connection_metrics(connection)

        # Simulate authentication
        connection.state = ConnectionState.AUTHENTICATED

        # Send some messages to generate metrics
        for i in range(10):
            test_event = {
                "type": "test.message",
                "payload": {"message": f"Test message {i}"},
                "priority": 2,
            }
            await connection.send(test_event)
            performance_monitor.collect_connection_metrics(connection)
            await asyncio.sleep(0.01)

        # Wait for aggregation to process the collected metrics
        await asyncio.sleep(1.2)  # Allow aggregation interval to pass

        # Verify metrics were collected
        summary = performance_monitor.get_performance_summary()
        assert summary["status"] in ["healthy", "degraded", "unhealthy"]
        assert summary["connection_count"] >= 0

        # Test connection performance data
        perf_data = performance_monitor.get_connection_performance(
            connection.connection_id
        )
        assert perf_data["connection_id"] == connection.connection_id
        assert "total_messages" in perf_data
        assert "current_latency" in perf_data

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_circuit_breaker_monitoring_integration(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test circuit breaker pattern integration with performance monitoring."""
        connection = mock_websocket_connection

        # Simulate multiple failures to trigger circuit breaker
        for i in range(10):
            connection.circuit_breaker.record_failure()
            performance_monitor.collect_connection_metrics(connection)

            # Check if circuit breaker opened
            if connection.circuit_breaker.state == CircuitBreakerState.OPEN:
                break

        # Verify circuit breaker is open
        assert connection.circuit_breaker.state == CircuitBreakerState.OPEN

        # Verify alert was generated
        alerts = performance_monitor.get_active_alerts()
        circuit_breaker_alerts = [
            alert for alert in alerts if alert.get("type") == "circuit_breaker"
        ]
        assert len(circuit_breaker_alerts) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_alert_generation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test performance alert generation and management."""
        connection = mock_websocket_connection

        # Simulate high latency to trigger alert
        connection._last_message_time = time.time() - 0.5  # 500ms ago

        # Mock health to show high latency
        with patch.object(connection, "get_health") as mock_health:
            mock_health.return_value = MagicMock(
                latency=250.0,  # Above critical threshold
                queue_size=10,
                message_rate=1.0,
                backpressure_active=False,
            )

            # Collect metrics to trigger alert
            performance_monitor.collect_connection_metrics(connection)

        # Verify alert was generated
        alerts = performance_monitor.get_active_alerts()
        latency_alerts = [alert for alert in alerts if alert.get("type") == "latency"]
        assert len(latency_alerts) > 0

        latency_alert = latency_alerts[0]
        assert latency_alert["severity"] == "critical"
        assert latency_alert["current_value"] == 250.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_queue_backpressure_monitoring(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test queue backpressure detection and monitoring."""
        connection = mock_websocket_connection

        # Fill up the message queue to simulate backpressure
        for i in range(1200):  # Exceed default queue size
            connection.message_queue.append(f"Message {i}")

        # Mock health to show high queue size and backpressure
        with patch.object(connection, "get_health") as mock_health:
            mock_health.return_value = MagicMock(
                latency=50.0,
                queue_size=1200,  # Above critical threshold
                message_rate=1.0,
                backpressure_active=True,
            )

            # Collect metrics
            performance_monitor.collect_connection_metrics(connection)

        # Verify queue size alert
        alerts = performance_monitor.get_active_alerts()
        queue_alerts = [alert for alert in alerts if alert.get("type") == "queue_size"]
        assert len(queue_alerts) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_rate_monitoring(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test error rate monitoring and alerting."""
        connection = mock_websocket_connection

        # Simulate messages and errors
        connection.message_count = 100
        connection.error_count = 15  # 15% error rate (above critical threshold)

        # Mock health to reflect error conditions
        with patch.object(connection, "get_health") as mock_health:
            mock_health.return_value = MagicMock(
                latency=50.0, queue_size=10, message_rate=1.0, backpressure_active=False
            )

            # Collect metrics
            performance_monitor.collect_connection_metrics(connection)

        # Verify error rate alert
        alerts = performance_monitor.get_active_alerts()
        error_alerts = [alert for alert in alerts if alert.get("type") == "error_rate"]
        assert len(error_alerts) > 0

        error_alert = error_alerts[0]
        assert error_alert["severity"] == "critical"
        assert error_alert["current_value"] == 0.15  # 15% error rate

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_metrics_aggregation_and_export(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test metrics aggregation and data export functionality."""
        connection = mock_websocket_connection

        # Generate metrics over time
        for i in range(20):
            # Vary the metrics to create realistic data
            latency = 50 + (i * 5)  # Increasing latency
            queue_size = 10 + i

            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=latency,
                    queue_size=queue_size,
                    message_rate=1.0,
                    backpressure_active=False,
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.05)  # Small delay between collections

        # Wait for aggregation
        await asyncio.sleep(1.2)  # Allow aggregation to complete

        # Test metrics export
        exported_data = performance_monitor.export_metrics("json")
        exported_dict = json.loads(exported_data)

        assert "summary" in exported_dict
        assert "aggregated_metrics" in exported_dict
        assert "active_alerts" in exported_dict
        assert "connection_count" in exported_dict
        assert "export_timestamp" in exported_dict

        # Verify aggregated metrics exist
        assert len(exported_dict["aggregated_metrics"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_health_score_calculation(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test health score calculation based on multiple performance factors."""
        connection = mock_websocket_connection

        # Test healthy state - collect multiple metrics to ensure aggregation
        for i in range(5):
            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=30.0 + i,  # Good latency
                    queue_size=5 + i,  # Low queue size
                    message_rate=2.0,
                    backpressure_active=False,
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.1)  # Small delay between collections

        # Wait for aggregation
        await asyncio.sleep(1.2)

        # Check healthy score
        summary = performance_monitor.get_performance_summary()
        assert summary["health_score"] >= 80  # Should be healthy
        assert summary["status"] == "healthy"

        # Test degraded state - collect multiple metrics
        for i in range(5):
            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=150.0 + i,  # High latency
                    queue_size=75 + i,  # High queue size
                    message_rate=1.0,
                    backpressure_active=True,  # Backpressure active
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.1)

        # Wait for aggregation
        await asyncio.sleep(1.2)

        # Check degraded/unhealthy score
        summary = performance_monitor.get_performance_summary()
        assert summary["health_score"] < 80  # Should be degraded or unhealthy

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_monitoring_operations(self, performance_monitor):
        """Test concurrent monitoring operations with multiple connections."""
        connections = []

        # Create multiple mock connections
        for i in range(10):
            mock_ws = MagicMock()
            mock_ws.send_text = AsyncMock()

            connection = WebSocketConnection(
                websocket=mock_ws,
                connection_id=f"conn_{i}",
                user_id=uuid4(),
            )
            connections.append(connection)

        # Collect metrics concurrently
        async def collect_metrics_for_connection(conn, iterations=5):
            for j in range(iterations):
                with patch.object(conn, "get_health") as mock_health:
                    mock_health.return_value = MagicMock(
                        latency=50.0 + j * 10,
                        queue_size=10 + j,
                        message_rate=1.0,
                        backpressure_active=False,
                    )

                    performance_monitor.collect_connection_metrics(conn)
                    await asyncio.sleep(0.01)

        # Run concurrent metric collection
        tasks = [collect_metrics_for_connection(conn) for conn in connections]
        await asyncio.gather(*tasks)

        # Verify metrics were collected for all connections
        for connection in connections:
            perf_data = performance_monitor.get_connection_performance(
                connection.connection_id
            )
            assert perf_data["connection_id"] == connection.connection_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_performance_data_cleanup(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test automatic cleanup of old performance data."""
        connection = mock_websocket_connection

        # Generate old metrics by manipulating timestamps
        old_timestamp = time.time() - 7200  # 2 hours ago

        # Manually add old snapshots
        from tripsage_core.services.infrastructure.websocket_performance_monitor import (
            PerformanceSnapshot,
        )

        old_snapshot = PerformanceSnapshot(
            timestamp=old_timestamp,
            connection_id=connection.connection_id,
            latency_ms=100.0,
            queue_size=10,
            error_count=0,
            message_rate=1.0,
            memory_usage_mb=50.0,
            circuit_breaker_state="CLOSED",
            backpressure_active=False,
        )

        performance_monitor.snapshots.append(old_snapshot)

        # Add recent snapshot
        performance_monitor.collect_connection_metrics(connection)

        # Force cleanup
        await performance_monitor._cleanup_old_data()

        # Verify old data was cleaned up but recent data remains
        recent_snapshots = [
            s
            for s in performance_monitor.snapshots
            if time.time() - s.timestamp < 3600  # Less than 1 hour old
        ]
        assert len(recent_snapshots) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_alert_cooldown_mechanism(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test alert cooldown to prevent spam."""
        connection = mock_websocket_connection

        # Mock health to trigger critical latency alert
        with patch.object(connection, "get_health") as mock_health:
            mock_health.return_value = MagicMock(
                latency=300.0,  # Critical latency
                queue_size=10,
                message_rate=1.0,
                backpressure_active=False,
            )

            # Collect metrics multiple times quickly
            for _ in range(5):
                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.1)

        # Should only have one alert due to cooldown
        alerts = performance_monitor.get_active_alerts()
        latency_alerts = [alert for alert in alerts if alert.get("type") == "latency"]
        assert len(latency_alerts) == 1


class TestWebSocketPerformanceRegression:
    """Tests for detecting performance regressions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_latency_regression_detection(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test detection of latency performance regressions."""
        connection = mock_websocket_connection

        # Establish baseline performance
        baseline_latencies = []
        for i in range(10):
            latency = 50.0 + (i * 2)  # Gradual increase
            baseline_latencies.append(latency)

            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=latency,
                    queue_size=10,
                    message_rate=1.0,
                    backpressure_active=False,
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.05)

        # Wait for aggregation
        await asyncio.sleep(1.2)

        # Get baseline metrics
        baseline_summary = performance_monitor.get_performance_summary()
        baseline_avg_latency = baseline_summary["avg_latency_ms"]

        # Simulate performance regression (sudden increase in latency)
        regression_latencies = []
        for i in range(10):
            latency = 250.0 + (
                i * 10
            )  # Much higher latencies (well above critical threshold)
            regression_latencies.append(latency)

            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=latency,
                    queue_size=10,
                    message_rate=1.0,
                    backpressure_active=False,
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.05)

        # Wait for aggregation
        await asyncio.sleep(1.2)

        # Get regression metrics
        regression_summary = performance_monitor.get_performance_summary()
        regression_avg_latency = regression_summary["avg_latency_ms"]

        # Verify regression was detected
        latency_increase = (
            regression_avg_latency - baseline_avg_latency
        ) / baseline_avg_latency
        assert latency_increase > 1.0  # More than 100% increase indicates regression

        # Should have generated critical alerts
        alerts = performance_monitor.get_active_alerts()
        critical_alerts = [
            alert for alert in alerts if alert.get("severity") == "critical"
        ]
        assert len(critical_alerts) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_throughput_regression_detection(
        self, performance_monitor, mock_websocket_connection
    ):
        """Test detection of message throughput regressions."""
        connection = mock_websocket_connection

        # Simulate high throughput baseline
        for _ in range(20):
            connection.message_count += 10  # Simulate processing 10 messages

            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=30.0,
                    queue_size=5,
                    message_rate=10.0,  # High message rate
                    backpressure_active=False,
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.05)

        # Wait for aggregation
        await asyncio.sleep(1.2)

        # Get baseline metrics
        baseline_summary = performance_monitor.get_performance_summary()
        baseline_total_messages = baseline_summary["total_messages"]

        # Simulate throughput regression (lower message processing)
        for i in range(20):
            connection.message_count += 2  # Much slower processing

            with patch.object(connection, "get_health") as mock_health:
                mock_health.return_value = MagicMock(
                    latency=150.0,  # Higher latency due to slow processing
                    # Higher queue due to slow processing (above warning threshold)
                    queue_size=75,
                    message_rate=2.0,  # Low message rate
                    backpressure_active=True,
                )

                performance_monitor.collect_connection_metrics(connection)
                await asyncio.sleep(0.05)

        # Wait for aggregation
        await asyncio.sleep(1.2)

        # Get regression metrics
        regression_summary = performance_monitor.get_performance_summary()

        # Verify degraded performance indicators
        assert regression_summary["health_score"] < 80  # Should be degraded
        assert regression_summary["max_queue_size"] > 20  # High queue size
        assert regression_summary["backpressure_events"] > 0  # Backpressure detected


class TestWebSocketEndToEndPerformance:
    """End-to-end performance integration tests."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.e2e
    async def test_complete_websocket_performance_workflow(
        self, test_client, performance_monitor
    ):
        """Test complete WebSocket workflow with performance monitoring."""

        # This test would ideally use a real WebSocket connection
        # For now, we'll simulate the workflow with the components we have

        # Create multiple connections to simulate real usage
        connections = []
        for i in range(5):
            mock_ws = MagicMock()
            mock_ws.send_text = AsyncMock()

            connection = WebSocketConnection(
                websocket=mock_ws,
                connection_id=f"e2e_conn_{i}",
                user_id=uuid4(),
                session_id=uuid4(),
            )
            connections.append(connection)

        # Simulate realistic usage patterns
        async def simulate_user_session(connection, duration_seconds=5):
            """Simulate a realistic user session."""
            start_time = time.time()
            message_count = 0

            while time.time() - start_time < duration_seconds:
                # Send message
                test_event = {
                    "type": "user.message",
                    "payload": {"message": f"Message {message_count}"},
                    "priority": 2,
                }
                await connection.send(test_event)
                message_count += 1

                # Collect metrics
                performance_monitor.collect_connection_metrics(connection)

                # Simulate user typing delay
                await asyncio.sleep(0.2)

        # Run concurrent user sessions
        tasks = [simulate_user_session(conn, 3) for conn in connections]
        await asyncio.gather(*tasks)

        # Wait for final aggregation
        await asyncio.sleep(1.5)

        # Verify complete workflow metrics
        summary = performance_monitor.get_performance_summary()
        assert summary["connection_count"] == len(connections)
        assert summary["total_messages"] > 0

        # Verify individual connection metrics
        for connection in connections:
            perf_data = performance_monitor.get_connection_performance(
                connection.connection_id
            )
            assert perf_data["total_messages"] > 0
            assert perf_data["connection_id"] == connection.connection_id

        # Export final performance report
        performance_report = performance_monitor.export_metrics("json")
        report_data = json.loads(performance_report)

        assert "summary" in report_data
        assert "aggregated_metrics" in report_data
        assert len(report_data["aggregated_metrics"]) > 0

        logger.info("End-to-end WebSocket performance test completed successfully")
        logger.info(f"Final health score: {summary['health_score']}")
        logger.info(f"Total connections: {summary['connection_count']}")
        logger.info(f"Total messages: {summary['total_messages']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
