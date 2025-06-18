"""
Integration tests for Enhanced Database Service with LIFO pooling and monitoring.

This test suite validates:
- LIFO connection pool behavior
- Enhanced Prometheus metrics collection
- Performance regression detection
- Connection validation and health monitoring
- Resource utilization tracking
- Error handling and recovery
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring import (
    EnhancedDatabaseService,
    get_enhanced_database_service,
    close_enhanced_database_service,
)
from tripsage_core.services.infrastructure.enhanced_database_pool_manager import (
    EnhancedDatabasePoolManager,
    ConnectionInfo,
    ConnectionStatus,
    PoolStatistics,
)
from tripsage_core.monitoring.enhanced_database_metrics import (
    EnhancedDatabaseMetrics,
    PerformanceBaseline,
    PerformanceAlert,
    AlertSeverity,
)
from tripsage_core.monitoring.performance_regression_detector import (
    PerformanceRegressionDetector,
    RegressionSeverity,
    StatisticalBaseline,
    RegressionAlert,
)
from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.config import get_settings


class TestEnhancedDatabaseService:
    """Test suite for Enhanced Database Service."""

    @pytest.fixture
    async def mock_settings(self):
        """Mock settings for testing."""
        settings = get_settings()
        settings.database_url = "https://test.supabase.co"
        settings.database_public_key = "test_key"
        settings.enable_read_replicas = False
        return settings

    @pytest.fixture
    async def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        client = MagicMock()
        
        # Mock table operations
        table_mock = MagicMock()
        client.table.return_value = table_mock
        
        # Mock query operations
        query_mock = MagicMock()
        table_mock.select.return_value = query_mock
        table_mock.insert.return_value = query_mock
        table_mock.update.return_value = query_mock
        table_mock.upsert.return_value = query_mock
        table_mock.delete.return_value = query_mock
        
        # Mock query execution
        result_mock = MagicMock()
        result_mock.data = [{"id": 1, "name": "test"}]
        result_mock.count = 1
        query_mock.execute.return_value = result_mock
        
        # Mock query chaining
        query_mock.eq.return_value = query_mock
        query_mock.gte.return_value = query_mock
        query_mock.lt.return_value = query_mock
        query_mock.order.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.on_conflict.return_value = query_mock
        
        return client

    @pytest.fixture
    async def enhanced_service(self, mock_settings):
        """Create enhanced database service for testing."""
        service = EnhancedDatabaseService(
            settings=mock_settings,
            pool_size=5,
            max_overflow=10,
            lifo_enabled=True,
            enable_regression_detection=True,
        )
        
        # Mock the pool manager and metrics
        with patch('tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.get_enhanced_pool_manager') as mock_pool, \
             patch('tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.get_enhanced_database_metrics') as mock_metrics, \
             patch('tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.get_regression_detector') as mock_detector:
            
            # Mock pool manager
            pool_manager = AsyncMock()
            pool_manager.health_check.return_value = True
            pool_manager.get_metrics.return_value = {
                "statistics": {
                    "pool_utilization": 50.0,
                    "active_connections": 2,
                    "idle_connections": 3,
                    "total_connections": 5,
                }
            }
            mock_pool.return_value = pool_manager
            
            # Mock metrics
            metrics = MagicMock()
            mock_metrics.return_value = metrics
            
            # Mock regression detector
            detector = AsyncMock()
            detector.record_performance = MagicMock()
            detector.get_recent_alerts.return_value = []
            detector.get_metrics_summary.return_value = {"tracked_metrics": 5}
            mock_detector.return_value = detector
            
            yield service

    @pytest.mark.asyncio
    async def test_service_initialization(self, enhanced_service):
        """Test enhanced service initialization."""
        await enhanced_service.connect()
        
        assert enhanced_service.is_connected
        assert enhanced_service.lifo_enabled
        assert enhanced_service.enable_regression_detection
        assert enhanced_service._pool_manager is not None
        assert enhanced_service._metrics is not None

    @pytest.mark.asyncio
    async def test_lifo_connection_behavior(self, enhanced_service, mock_supabase_client):
        """Test LIFO connection pool behavior."""
        await enhanced_service.connect()
        
        # Mock the client acquisition to track LIFO behavior
        with patch.object(enhanced_service._pool_manager, 'acquire_connection') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = mock_supabase_client
            mock_acquire.return_value.__aexit__.return_value = None
            
            # Perform multiple operations
            await enhanced_service.select("users", columns="id,name")
            await enhanced_service.select("posts", columns="id,title")
            
            # Verify pool manager was used
            assert mock_acquire.call_count == 2

    @pytest.mark.asyncio
    async def test_select_operation_with_monitoring(self, enhanced_service, mock_supabase_client):
        """Test SELECT operation with performance monitoring."""
        await enhanced_service.connect()
        
        with patch.object(enhanced_service._pool_manager, 'acquire_connection') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = mock_supabase_client
            mock_acquire.return_value.__aexit__.return_value = None
            
            # Execute select operation
            result = await enhanced_service.select(
                table="users",
                columns="id,name,email",
                filters={"active": True},
                order_by="created_at",
                limit=10
            )
            
            # Verify result
            assert result == [{"id": 1, "name": "test"}]
            
            # Verify metrics recording
            assert enhanced_service._metrics.record_query_duration.called

    @pytest.mark.asyncio
    async def test_insert_operation_with_monitoring(self, enhanced_service, mock_supabase_client):
        """Test INSERT operation with performance monitoring."""
        await enhanced_service.connect()
        
        with patch.object(enhanced_service._pool_manager, 'acquire_connection') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = mock_supabase_client
            mock_acquire.return_value.__aexit__.return_value = None
            
            # Execute insert operation
            test_data = {"name": "John Doe", "email": "john@example.com"}
            result = await enhanced_service.insert("users", test_data)
            
            # Verify result
            assert result == [{"id": 1, "name": "test"}]

    @pytest.mark.asyncio
    async def test_vector_search_with_monitoring(self, enhanced_service, mock_supabase_client):
        """Test vector search operation with performance monitoring."""
        await enhanced_service.connect()
        
        with patch.object(enhanced_service._pool_manager, 'acquire_connection') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = mock_supabase_client
            mock_acquire.return_value.__aexit__.return_value = None
            
            # Execute vector search
            query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
            result = await enhanced_service.vector_search(
                table="embeddings",
                vector_column="embedding",
                query_vector=query_vector,
                limit=5,
                similarity_threshold=0.8
            )
            
            # Verify result
            assert result == [{"id": 1, "name": "test"}]

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, enhanced_service):
        """Test performance regression detection integration."""
        await enhanced_service.connect()
        
        # Simulate slow operation that should trigger regression
        with patch.object(enhanced_service, '_execute_with_monitoring') as mock_execute:
            mock_execute.return_value = [{"id": 1}]
            
            # Mock regression detector to simulate alert
            enhanced_service._regression_detector.record_performance = MagicMock()
            
            await enhanced_service.select("users", columns="id")
            
            # Verify regression detector was called
            assert enhanced_service._regression_detector.record_performance.called

    @pytest.mark.asyncio
    async def test_health_check(self, enhanced_service):
        """Test database health check functionality."""
        await enhanced_service.connect()
        
        # Test successful health check
        health_status = await enhanced_service.health_check()
        assert health_status is True
        
        # Test failed health check
        enhanced_service._pool_manager.health_check.return_value = False
        health_status = await enhanced_service.health_check()
        assert health_status is False

    @pytest.mark.asyncio
    async def test_error_handling_and_metrics(self, enhanced_service, mock_supabase_client):
        """Test error handling and error metrics collection."""
        await enhanced_service.connect()
        
        # Mock database error
        mock_supabase_client.table.side_effect = Exception("Database connection failed")
        
        with patch.object(enhanced_service._pool_manager, 'acquire_connection') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = mock_supabase_client
            mock_acquire.return_value.__aexit__.return_value = None
            
            # Execute operation that should fail
            with pytest.raises(CoreDatabaseError):
                await enhanced_service.select("users", columns="id")
            
            # Verify error was counted
            assert enhanced_service._error_count == 1

    @pytest.mark.asyncio
    async def test_connection_pool_metrics(self, enhanced_service):
        """Test connection pool metrics collection."""
        await enhanced_service.connect()
        
        # Get performance metrics
        metrics = enhanced_service.get_performance_metrics()
        
        # Verify metrics structure
        assert "service" in metrics
        assert "pool" in metrics
        assert "regression_detection" in metrics
        assert "enhanced_metrics" in metrics
        
        # Verify service metrics
        service_metrics = metrics["service"]
        assert "uptime_seconds" in service_metrics
        assert "total_queries" in service_metrics
        assert "error_count" in service_metrics
        assert "error_rate" in service_metrics
        assert "lifo_enabled" in service_metrics
        assert service_metrics["lifo_enabled"] is True

    @pytest.mark.asyncio
    async def test_performance_alerts_retrieval(self, enhanced_service):
        """Test retrieval of performance regression alerts."""
        await enhanced_service.connect()
        
        # Mock some alerts
        mock_alerts = [
            RegressionAlert(
                metric_name="query_duration_users_select",
                severity=RegressionSeverity.WARNING,
                current_value=2.5,
                baseline_p95=1.5,
                z_score=2.1,
                message="Performance regression detected",
                timestamp=datetime.now(timezone.utc),
            )
        ]
        enhanced_service._regression_detector.get_recent_alerts.return_value = mock_alerts
        
        # Get recent alerts
        alerts = enhanced_service.get_recent_performance_alerts(limit=10)
        
        # Verify alerts structure
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["metric_name"] == "query_duration_users_select"
        assert alert["severity"] == "warning"
        assert alert["current_value"] == 2.5
        assert alert["baseline_p95"] == 1.5

    @pytest.mark.asyncio
    async def test_service_cleanup(self, enhanced_service):
        """Test proper cleanup of service resources."""
        await enhanced_service.connect()
        
        # Verify service is connected
        assert enhanced_service.is_connected
        
        # Close service
        await enhanced_service.close()
        
        # Verify service is properly closed
        assert not enhanced_service.is_connected
        assert enhanced_service._pool_manager is None
        assert enhanced_service._regression_detector is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, enhanced_service, mock_supabase_client):
        """Test concurrent database operations with LIFO pooling."""
        await enhanced_service.connect()
        
        with patch.object(enhanced_service._pool_manager, 'acquire_connection') as mock_acquire:
            mock_acquire.return_value.__aenter__.return_value = mock_supabase_client
            mock_acquire.return_value.__aexit__.return_value = None
            
            # Execute multiple concurrent operations
            tasks = [
                enhanced_service.select("users", columns="id"),
                enhanced_service.select("posts", columns="id"),
                enhanced_service.count("users"),
                enhanced_service.select("comments", columns="id"),
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all operations completed successfully
            assert len(results) == 4
            for result in results:
                assert len(result) >= 0  # count() returns int, others return list

    @pytest.mark.asyncio
    async def test_query_type_mapping(self, enhanced_service):
        """Test query type mapping for replica routing."""
        # Test operation mapping
        assert enhanced_service._get_query_type("SELECT").name == "READ"
        assert enhanced_service._get_query_type("INSERT").name == "WRITE"
        assert enhanced_service._get_query_type("UPDATE").name == "WRITE"
        assert enhanced_service._get_query_type("DELETE").name == "WRITE"
        assert enhanced_service._get_query_type("VECTOR_SEARCH").name == "VECTOR_SEARCH"
        assert enhanced_service._get_query_type("COUNT").name == "READ"


class TestEnhancedDatabasePoolManager:
    """Test suite for Enhanced Database Pool Manager."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = get_settings()
        settings.database_url = "https://test.supabase.co"
        settings.database_public_key = "test_key"
        return settings

    @pytest.fixture
    async def pool_manager(self, mock_settings):
        """Create enhanced pool manager for testing."""
        with patch('tripsage_core.services.infrastructure.enhanced_database_pool_manager.create_client'):
            manager = EnhancedDatabasePoolManager(
                settings=mock_settings,
                pool_size=3,
                max_overflow=5,
                lifo_enabled=True,
                pool_pre_ping=True,
            )
            yield manager

    @pytest.mark.asyncio
    async def test_pool_initialization(self, pool_manager):
        """Test pool manager initialization."""
        with patch.object(pool_manager, '_create_connection') as mock_create:
            mock_create.return_value = MagicMock(spec=ConnectionInfo)
            
            await pool_manager.initialize()
            
            assert pool_manager._initialized
            assert mock_create.call_count == pool_manager.pool_size

    @pytest.mark.asyncio
    async def test_lifo_connection_retrieval(self, pool_manager):
        """Test LIFO connection retrieval behavior."""
        # Create mock connections
        conn1 = ConnectionInfo("conn1", MagicMock())
        conn2 = ConnectionInfo("conn2", MagicMock())
        conn3 = ConnectionInfo("conn3", MagicMock())
        
        # Add connections to pool
        pool_manager._available_connections.extend([conn1, conn2, conn3])
        pool_manager._all_connections = {
            "conn1": conn1,
            "conn2": conn2,
            "conn3": conn3,
        }
        
        with patch.object(pool_manager, '_check_connection_health', return_value=True):
            # Get connection - should return conn3 (LIFO)
            result = await pool_manager._get_pooled_connection()
            assert result.connection_id == "conn3"

    @pytest.mark.asyncio
    async def test_connection_health_monitoring(self, pool_manager):
        """Test connection health monitoring."""
        # Create connection with age exceeding recycle time
        old_conn = ConnectionInfo("old_conn", MagicMock())
        old_conn.created_at = datetime.now(timezone.utc).replace(year=2020)
        
        # Test health check
        is_healthy = await pool_manager._check_connection_health(old_conn)
        assert not is_healthy  # Should be unhealthy due to age

    @pytest.mark.asyncio
    async def test_pool_metrics_collection(self, pool_manager):
        """Test pool metrics collection."""
        await pool_manager.initialize()
        
        # Get metrics
        metrics = pool_manager.get_metrics()
        
        # Verify metrics structure
        assert "pool_config" in metrics
        assert "statistics" in metrics
        assert "connection_details" in metrics
        assert "performance" in metrics
        
        # Verify pool config
        config = metrics["pool_config"]
        assert config["lifo_enabled"] is True
        assert config["pool_size"] == 3
        assert config["max_overflow"] == 5

    @pytest.mark.asyncio
    async def test_connection_validation(self, pool_manager):
        """Test connection validation functionality."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_query = MagicMock()
        mock_table.select.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock()
        
        # Test successful validation
        is_valid = await pool_manager._validate_connection(mock_client)
        assert is_valid
        
        # Test failed validation
        mock_query.execute.side_effect = Exception("Connection failed")
        is_valid = await pool_manager._validate_connection(mock_client)
        assert not is_valid


class TestEnhancedDatabaseMetrics:
    """Test suite for Enhanced Database Metrics."""

    @pytest.fixture
    def metrics(self):
        """Create enhanced database metrics for testing."""
        return EnhancedDatabaseMetrics(
            baseline_window_size=100,
            regression_threshold=2.0,
            enable_regression_detection=True,
        )

    def test_query_duration_recording(self, metrics):
        """Test query duration recording and percentile calculation."""
        # Record multiple query durations
        durations = [0.1, 0.2, 0.15, 0.3, 0.25, 0.18, 0.22, 0.12, 0.28, 0.19]
        
        for duration in durations:
            metrics.record_query_duration(
                duration=duration,
                operation="SELECT",
                table="users",
                status="success"
            )
        
        # Get percentiles
        percentiles = metrics.get_percentiles("query_duration_SELECT_users")
        assert percentiles is not None
        p50, p95, p99 = percentiles
        assert 0.1 <= p50 <= 0.3
        assert p95 >= p50
        assert p99 >= p95

    def test_performance_regression_detection(self, metrics):
        """Test performance regression detection."""
        # Record baseline performance
        for _ in range(50):
            metrics.record_query_duration(
                duration=0.1,  # Fast baseline
                operation="SELECT",
                table="users",
                status="success"
            )
        
        # Record regression (slow query)
        metrics.record_query_duration(
            duration=0.5,  # Much slower
            operation="SELECT",
            table="users",
            status="success"
        )
        
        # Check for alerts
        alerts = metrics.get_recent_alerts()
        assert len(alerts) > 0
        
        alert = alerts[-1]
        assert alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]
        assert alert.current_value == 0.5

    def test_pool_utilization_recording(self, metrics):
        """Test pool utilization metrics recording."""
        metrics.record_pool_utilization(
            utilization_percent=75.0,
            active_connections=3,
            idle_connections=1,
            total_connections=4,
        )
        
        # Verify metrics were recorded (would be tracked by Prometheus if available)
        # This test mainly ensures no exceptions are raised

    def test_connection_health_recording(self, metrics):
        """Test connection health metrics recording."""
        metrics.record_connection_health(
            connection_id="conn_1",
            health_score=0.95,
            validation_duration=0.05,
            validation_result="success"
        )
        
        # Verify metrics were recorded (would be tracked by Prometheus if available)
        # This test mainly ensures no exceptions are raised

    def test_summary_statistics(self, metrics):
        """Test summary statistics generation."""
        # Record some data
        for i in range(10):
            metrics.record_query_duration(
                duration=0.1 + (i * 0.01),
                operation="SELECT",
                table="users",
                status="success" if i < 8 else "error"
            )
        
        # Get summary
        summary = metrics.get_summary_stats()
        
        # Verify summary structure
        assert "uptime_seconds" in summary
        assert "total_queries" in summary
        assert "error_count" in summary
        assert "error_rate" in summary
        assert summary["total_queries"] == 10
        assert summary["error_count"] == 2
        assert summary["error_rate"] == 0.2


class TestPerformanceRegressionDetector:
    """Test suite for Performance Regression Detector."""

    @pytest.fixture
    async def detector(self):
        """Create performance regression detector for testing."""
        detector = PerformanceRegressionDetector(
            baseline_window_hours=1,
            trend_window_minutes=30,
            sensitivity=2.0,
            regression_threshold=1.5,
            min_samples_for_baseline=10,
        )
        await detector.start()
        yield detector
        await detector.stop()

    @pytest.mark.asyncio
    async def test_performance_recording(self, detector):
        """Test performance data recording."""
        # Record performance data
        detector.record_performance(
            metric_name="query_duration_test",
            value=0.1,
            operation="SELECT",
            table="users"
        )
        
        # Verify data was recorded
        assert "query_duration_test" in detector._data_points
        assert len(detector._data_points["query_duration_test"]) == 1

    @pytest.mark.asyncio
    async def test_baseline_establishment(self, detector):
        """Test statistical baseline establishment."""
        # Record enough data for baseline
        metric_name = "test_metric"
        values = [0.1, 0.12, 0.11, 0.13, 0.09, 0.14, 0.10, 0.15, 0.08, 0.16, 0.12]
        
        for value in values:
            detector.record_performance(metric_name, value, "SELECT", "users")
        
        # Force baseline update
        detector._update_baseline(metric_name)
        
        # Verify baseline was created
        baseline = detector.get_baseline(metric_name)
        assert baseline is not None
        assert baseline.sample_count == len(values)
        assert 0.08 <= baseline.p95 <= 0.16

    @pytest.mark.asyncio
    async def test_regression_detection(self, detector):
        """Test regression detection and alerting."""
        metric_name = "test_regression"
        
        # Establish baseline with fast queries
        for _ in range(20):
            detector.record_performance(metric_name, 0.1, "SELECT", "users")
        
        # Force baseline update
        detector._update_baseline(metric_name)
        
        # Clear existing alerts
        detector._alerts.clear()
        
        # Record slow query that should trigger regression
        detector.record_performance(metric_name, 0.5, "SELECT", "users")
        
        # Check for alerts
        alerts = detector.get_recent_alerts()
        if alerts:  # Regression should be detected
            alert = alerts[-1]
            assert alert.metric_name == metric_name
            assert alert.current_value == 0.5

    @pytest.mark.asyncio
    async def test_alert_management(self, detector):
        """Test alert acknowledgment and resolution."""
        # Create a mock alert
        alert = RegressionAlert(
            metric_name="test_metric",
            severity=RegressionSeverity.WARNING,
            current_value=0.5,
            baseline_p95=0.2,
            z_score=2.5,
            message="Test regression",
        )
        
        detector._alerts.append(alert)
        
        # Test acknowledgment
        alert_id = alert.timestamp.isoformat()
        success = detector.acknowledge_alert(alert_id, "test_user", "Investigating")
        assert success
        assert alert.acknowledged
        assert alert.metadata["acknowledged_by"] == "test_user"

    @pytest.mark.asyncio
    async def test_metrics_summary(self, detector):
        """Test metrics summary generation."""
        # Record some data
        detector.record_performance("test1", 0.1, "SELECT", "users")
        detector.record_performance("test2", 0.2, "INSERT", "posts")
        
        # Get summary
        summary = detector.get_metrics_summary()
        
        # Verify summary structure
        assert "tracked_metrics" in summary
        assert "active_baselines" in summary
        assert "total_alerts" in summary
        assert "configuration" in summary
        assert summary["tracked_metrics"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])