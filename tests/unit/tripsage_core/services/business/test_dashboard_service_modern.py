"""
Modern comprehensive tests for Dashboard Service - 2025 Edition.

This module provides comprehensive test coverage for the DashboardService
using modern pytest patterns, async testing, and property-based testing.

Features tested:
- Real-time metrics aggregation
- Service analytics and health monitoring
- User activity tracking and analytics
- Alert management system
- Rate limiting status monitoring
- Cache integration and performance
- Error handling and resilience
- Comprehensive edge cases

Testing patterns used:
- Pytest fixtures with async support
- Property-based testing with Hypothesis
- Modern mocking with AsyncMock
- Performance benchmarking setup
- Comprehensive error scenario testing
- Real-time data simulation
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from hypothesis import given
from hypothesis import strategies as st

from tripsage_core.services.business.api_key_service import (
    ServiceHealthStatus,
    ServiceType,
)
from tripsage_core.services.business.dashboard_service import (
    AlertData,
    AlertSeverity,
    AlertType,
    ApiKeyValidator,
    DashboardData,
    DashboardService,
    RealTimeMetrics,
)


class TestDashboardServiceModern:
    """Modern comprehensive test suite for DashboardService."""

    @pytest_asyncio.fixture
    async def mock_cache_service(self) -> AsyncMock:
        """Create mock cache service with realistic behavior."""
        cache = AsyncMock()

        # Basic cache operations
        cache.get_json = AsyncMock(return_value=None)
        cache.set_json = AsyncMock(return_value=True)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        cache.ping = AsyncMock(return_value=True)
        cache.is_connected = True

        # Advanced cache operations for rate limiting
        cache.hincrby = AsyncMock(return_value=1)
        cache.expire = AsyncMock(return_value=True)
        cache.keys = AsyncMock(return_value=["rate_limit:key1", "rate_limit:key2"])

        # Performance simulation
        async def realistic_get_json(key: str) -> Dict[str, Any] | None:
            await asyncio.sleep(0.001)  # 1ms realistic cache latency
            # Mock different cache keys
            if "rate_limit:" in key:
                return {
                    "count": 45,
                    "limit": 100,
                    "reset_at": (
                        datetime.now(timezone.utc) + timedelta(hours=1)
                    ).isoformat(),
                }
            elif "dashboard:metrics:" in key:
                return None  # Force fresh computation
            return None

        cache.get_json.side_effect = realistic_get_json
        return cache

    @pytest_asyncio.fixture
    async def mock_database_service(self) -> AsyncMock:
        """Create mock database service with realistic behavior."""
        db = AsyncMock()

        # Mock common database operations
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        db.execute = AsyncMock(return_value=None)
        db.select = AsyncMock(return_value=[])

        # Performance simulation
        async def realistic_select(table: str, **kwargs) -> List[Dict[str, Any]]:
            await asyncio.sleep(0.005)  # 5ms realistic database latency

            if table == "api_key_usage_logs":
                # Generate realistic usage logs
                now = datetime.now(timezone.utc)
                return [
                    {
                        "timestamp": (now - timedelta(minutes=i)).isoformat(),
                        "user_id": f"user_{i % 3 + 1}",
                        "key_id": f"key_{i % 2 + 1}",
                        "service": "openai" if i % 2 == 0 else "weather",
                        "success": i % 10 != 0,  # 10% error rate
                        "latency_ms": 100 + (i % 100),
                    }
                    for i in range(100)  # 100 usage records
                ]
            return []

        db.select.side_effect = realistic_select
        return db

    @pytest_asyncio.fixture
    async def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.environment = "test"
        settings.cache_ttl = 300
        # 32+ chars for encryption
        settings.secret_key = "test-secret-key-for-encryption-testing-32-chars"
        return settings

    @pytest_asyncio.fixture
    async def dashboard_service(
        self, mock_cache_service, mock_database_service, mock_settings
    ) -> DashboardService:
        """Create DashboardService instance with mocked dependencies."""
        return DashboardService(
            cache_service=mock_cache_service,
            database_service=mock_database_service,
            settings=mock_settings,
        )

    @pytest_asyncio.fixture
    async def sample_usage_logs(self) -> List[Dict[str, Any]]:
        """Generate sample usage logs for testing."""
        now = datetime.now(timezone.utc)
        return [
            {
                "timestamp": (now - timedelta(minutes=i)).isoformat(),
                "user_id": f"user_{i % 5 + 1}",
                "key_id": f"key_{i % 3 + 1}",
                "service": ["openai", "weather", "googlemaps"][i % 3],
                "success": i % 20 != 0,  # 5% error rate
                "latency_ms": 50 + (i % 200),
            }
            for i in range(200)
        ]

    # Basic functionality tests

    async def test_dashboard_service_initialization(self, dashboard_service):
        """Test DashboardService initialization."""
        assert dashboard_service.cache is not None
        assert dashboard_service.db is not None
        assert dashboard_service.settings is not None
        assert dashboard_service.api_key_service is not None
        assert dashboard_service._active_alerts == {}
        assert dashboard_service._cache_prefix == "dashboard:metrics:"
        assert dashboard_service._cache_ttl == 300

    async def test_get_dashboard_data_success(
        self, dashboard_service, mock_database_service, sample_usage_logs
    ):
        """Test successful dashboard data retrieval."""
        # Mock the _query_usage_logs method directly to ensure sample data
        with patch.object(
            dashboard_service, "_query_usage_logs", return_value=sample_usage_logs
        ):
            # Mock health checks
            with patch.object(
                dashboard_service.api_key_service,
                "check_all_services_health",
                return_value={
                    ServiceType.OPENAI: MagicMock(
                        status=ServiceHealthStatus.HEALTHY,
                        latency_ms=120.0,
                        checked_at=datetime.now(timezone.utc),
                    ),
                    ServiceType.WEATHER: MagicMock(
                        status=ServiceHealthStatus.DEGRADED,
                        latency_ms=300.0,
                        checked_at=datetime.now(timezone.utc),
                    ),
                },
            ):
                dashboard_data = await dashboard_service.get_dashboard_data(
                    time_range_hours=24, top_users_limit=10
                )

        # Verify dashboard data structure
        assert isinstance(dashboard_data, DashboardData)
        assert isinstance(dashboard_data.metrics, RealTimeMetrics)
        assert isinstance(dashboard_data.services, list)
        assert isinstance(dashboard_data.top_users, list)
        assert isinstance(dashboard_data.recent_alerts, list)
        assert isinstance(dashboard_data.usage_trend, list)
        assert isinstance(dashboard_data.cache_stats, dict)

        # Verify metrics calculation based on sample_usage_logs (200, 5% error)
        assert dashboard_data.metrics.total_requests == 200
        assert dashboard_data.metrics.total_errors == 10  # 5% of 200
        assert dashboard_data.metrics.success_rate == 0.95
        assert dashboard_data.metrics.unique_users_count > 0
        assert dashboard_data.metrics.active_keys_count > 0

    async def test_get_dashboard_data_with_cache(
        self, dashboard_service, mock_cache_service
    ):
        """Test dashboard data retrieval with cache hit."""
        # Mock cached metrics
        cached_metrics = {
            "total_requests": 1000,
            "total_errors": 50,
            "success_rate": 0.95,
            "avg_latency_ms": 150.0,
            "p95_latency_ms": 300.0,
            "p99_latency_ms": 500.0,
            "active_keys_count": 5,
            "unique_users_count": 20,
            "requests_per_minute": 10.0,
            "period_start": datetime.now(timezone.utc).isoformat(),
            "period_end": datetime.now(timezone.utc).isoformat(),
        }

        mock_cache_service.get_json.return_value = cached_metrics

        # Mock health checks
        with patch.object(
            dashboard_service.api_key_service,
            "check_all_services_health",
            return_value={},
        ):
            dashboard_data = await dashboard_service.get_dashboard_data()

        # Verify cache was used
        assert dashboard_data.metrics.total_requests == 1000
        assert dashboard_data.metrics.success_rate == 0.95

    async def test_get_dashboard_data_error_fallback(
        self, dashboard_service, mock_database_service
    ):
        """Test dashboard data error handling with fallback."""
        # Mock database to raise exception
        mock_database_service.select.side_effect = Exception("Database error")

        dashboard_data = await dashboard_service.get_dashboard_data()

        # Verify fallback data is returned
        assert isinstance(dashboard_data, DashboardData)
        assert dashboard_data.metrics.total_requests > 0  # Default fallback values
        assert dashboard_data.services == []  # Empty services on error

    # Rate limiting tests

    async def test_get_rate_limit_status_with_cache(
        self, dashboard_service, mock_cache_service
    ):
        """Test rate limit status retrieval with cache data."""
        # Mock cache data
        cache_data = {
            "count": 75,
            "limit": 100,
            "reset_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        mock_cache_service.get_json.return_value = cache_data

        status = await dashboard_service.get_rate_limit_status("test_key_123")

        assert status["requests_in_window"] == 75
        assert status["limit"] == 100
        assert status["remaining"] == 25
        assert status["percentage_used"] == 75.0
        assert status["is_throttled"] is False

    async def test_get_rate_limit_status_no_cache(self, dashboard_service):
        """Test rate limit status with no cache service."""
        dashboard_service.cache = None

        status = await dashboard_service.get_rate_limit_status("test_key_123")

        # Should return default status
        assert "requests_in_window" in status
        assert "limit" in status
        assert "remaining" in status
        assert status["is_throttled"] is False

    async def test_get_rate_limit_status_throttled(
        self, dashboard_service, mock_cache_service
    ):
        """Test rate limit status when throttled."""
        # Mock cache data showing limit exceeded
        cache_data = {
            "count": 150,
            "limit": 100,
            "reset_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        mock_cache_service.get_json.return_value = cache_data

        status = await dashboard_service.get_rate_limit_status("throttled_key")

        assert status["requests_in_window"] == 150
        assert status["remaining"] == 0  # max(0, 100 - 150)
        assert status["percentage_used"] == 150.0
        assert status["is_throttled"] is True

    # Alert management tests

    async def test_create_alert(self, dashboard_service):
        """Test alert creation."""
        alert = await dashboard_service.create_alert(
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="High Error Rate Detected",
            message="Error rate exceeded threshold",
            service="openai",
            threshold_value=0.1,
            current_value=0.15,
        )

        assert isinstance(alert, AlertData)
        assert alert.alert_type == AlertType.HIGH_ERROR_RATE
        assert alert.severity == AlertSeverity.HIGH
        assert alert.title == "High Error Rate Detected"
        assert alert.service == "openai"
        assert not alert.acknowledged
        assert not alert.resolved

        # Verify alert is stored
        assert alert.alert_id in dashboard_service._active_alerts

    async def test_acknowledge_alert(self, dashboard_service):
        """Test alert acknowledgment."""
        # Create an alert first
        alert = await dashboard_service.create_alert(
            alert_type=AlertType.RATE_LIMIT_EXCEEDED,
            severity=AlertSeverity.MEDIUM,
            title="Rate Limit Alert",
            message="Rate limit exceeded",
        )

        # Acknowledge the alert
        success = await dashboard_service.acknowledge_alert(
            alert.alert_id, "admin_user"
        )

        assert success is True
        stored_alert = dashboard_service._active_alerts[alert.alert_id]
        assert stored_alert.acknowledged is True
        assert stored_alert.acknowledged_by == "admin_user"
        assert stored_alert.acknowledged_at is not None

    async def test_acknowledge_nonexistent_alert(self, dashboard_service):
        """Test acknowledging non-existent alert."""
        success = await dashboard_service.acknowledge_alert("nonexistent", "user")
        assert success is False

    async def test_resolve_alert(self, dashboard_service):
        """Test alert resolution."""
        # Create an alert first
        alert = await dashboard_service.create_alert(
            alert_type=AlertType.SYSTEM_OVERLOAD,
            severity=AlertSeverity.CRITICAL,
            title="System Overload",
            message="System under heavy load",
        )

        # Resolve the alert
        success = await dashboard_service.resolve_alert(alert.alert_id)

        assert success is True
        stored_alert = dashboard_service._active_alerts[alert.alert_id]
        assert stored_alert.resolved is True
        assert stored_alert.resolved_at is not None

    # Performance and edge case tests

    async def test_large_usage_logs_performance(
        self, dashboard_service, mock_database_service
    ):
        """Test performance with large amounts of usage data."""
        # Generate large dataset
        now = datetime.now(timezone.utc)
        large_usage_logs = [
            {
                "timestamp": (now - timedelta(minutes=i)).isoformat(),
                "user_id": f"user_{i % 50 + 1}",  # 50 different users
                "key_id": f"key_{i % 10 + 1}",  # 10 different keys
                "service": ["openai", "weather", "googlemaps", "flights"][i % 4],
                "success": i % 100 != 0,  # 1% error rate
                "latency_ms": 50 + (i % 500),
            }
            for i in range(10000)  # 10k records
        ]

        mock_database_service.select.return_value = large_usage_logs

        # Mock health checks
        with patch.object(
            dashboard_service.api_key_service,
            "check_all_services_health",
            return_value={},
        ):
            import time

            start_time = time.time()
            dashboard_data = await dashboard_service.get_dashboard_data(
                time_range_hours=24, top_users_limit=20
            )
            end_time = time.time()

        # Verify performance (should complete in reasonable time)
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Should complete within 1 second

        # Verify data quality with large dataset
        assert dashboard_data.metrics.total_requests == 10000
        assert dashboard_data.metrics.total_errors == 100  # 1% of 10k
        assert len(dashboard_data.top_users) <= 20

    async def test_concurrent_operations(self, dashboard_service):
        """Test concurrent dashboard operations."""
        # Create multiple operations concurrently
        tasks = [
            dashboard_service.get_dashboard_data(time_range_hours=1),
            dashboard_service.get_rate_limit_status("key1"),
            dashboard_service.get_rate_limit_status("key2"),
            dashboard_service.create_alert(
                AlertType.PERFORMANCE_DEGRADATION,
                AlertSeverity.LOW,
                "Test Alert 1",
                "Concurrent test alert 1",
            ),
            dashboard_service.create_alert(
                AlertType.API_KEY_EXPIRED,
                AlertSeverity.MEDIUM,
                "Test Alert 2",
                "Concurrent test alert 2",
            ),
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations completed
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)

        # Verify alerts were created
        assert len(dashboard_service._active_alerts) == 2

    async def test_memory_usage_with_alerts(self, dashboard_service):
        """Test memory usage doesn't grow unbounded with alerts."""
        # Create many alerts
        alert_ids = []
        for i in range(100):
            alert = await dashboard_service.create_alert(
                alert_type=AlertType.SECURITY_ANOMALY,
                severity=AlertSeverity.INFO,
                title=f"Test Alert {i}",
                message=f"Test alert message {i}",
            )
            alert_ids.append(alert.alert_id)

        assert len(dashboard_service._active_alerts) == 100

        # Resolve all alerts
        for alert_id in alert_ids:
            await dashboard_service.resolve_alert(alert_id)

        # Verify all alerts are marked as resolved
        for alert in dashboard_service._active_alerts.values():
            assert alert.resolved is True

    # Property-based testing

    @given(
        time_range_hours=st.integers(min_value=1, max_value=168),
        top_users_limit=st.integers(min_value=1, max_value=100),
    )
    async def test_get_dashboard_data_property_based(
        self, dashboard_service, time_range_hours, top_users_limit
    ):
        """Property-based test for dashboard data retrieval."""
        # Mock minimal dependencies
        with patch.object(
            dashboard_service.api_key_service,
            "check_all_services_health",
            return_value={},
        ):
            dashboard_data = await dashboard_service.get_dashboard_data(
                time_range_hours=time_range_hours, top_users_limit=top_users_limit
            )

        # Verify properties that should always hold
        assert isinstance(dashboard_data, DashboardData)
        assert dashboard_data.metrics.success_rate >= 0.0
        assert dashboard_data.metrics.success_rate <= 1.0
        assert dashboard_data.metrics.total_requests >= 0
        assert dashboard_data.metrics.total_errors >= 0
        assert (
            dashboard_data.metrics.total_errors <= dashboard_data.metrics.total_requests
        )
        assert len(dashboard_data.top_users) <= top_users_limit

    @given(
        alert_type=st.sampled_from(list(AlertType)),
        severity=st.sampled_from(list(AlertSeverity)),
        title=st.text(min_size=1, max_size=100),
        message=st.text(min_size=1, max_size=500),
    )
    async def test_create_alert_property_based(
        self, dashboard_service, alert_type, severity, title, message
    ):
        """Property-based test for alert creation."""
        alert = await dashboard_service.create_alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
        )

        # Verify properties that should always hold
        assert alert.alert_type == alert_type
        assert alert.severity == severity
        assert alert.title == title
        assert alert.message == message
        assert not alert.acknowledged
        assert not alert.resolved
        assert alert.created_at <= datetime.now(timezone.utc)
        assert alert.priority_score > 0

    # Error handling tests

    async def test_database_connection_failure(
        self, dashboard_service, mock_database_service
    ):
        """Test behavior when database connection fails."""
        mock_database_service.select.side_effect = ConnectionError(
            "Database unreachable"
        )

        # Should handle gracefully with fallback data
        dashboard_data = await dashboard_service.get_dashboard_data()

        assert isinstance(dashboard_data, DashboardData)
        assert dashboard_data.metrics.total_requests > 0  # Fallback values

    async def test_cache_connection_failure(
        self, dashboard_service, mock_cache_service
    ):
        """Test behavior when cache connection fails."""
        mock_cache_service.get_json.side_effect = ConnectionError("Cache unreachable")
        mock_cache_service.is_connected = False

        # Should handle gracefully without cache
        status = await dashboard_service.get_rate_limit_status("test_key")

        assert "requests_in_window" in status
        assert "limit" in status

    async def test_invalid_time_range(self, dashboard_service):
        """Test behavior with invalid time ranges."""
        # Test with zero time range
        dashboard_data = await dashboard_service.get_dashboard_data(time_range_hours=0)
        assert isinstance(dashboard_data, DashboardData)

        # Test with negative time range (should be handled gracefully)
        dashboard_data = await dashboard_service.get_dashboard_data(time_range_hours=-1)
        assert isinstance(dashboard_data, DashboardData)

    async def test_malformed_usage_logs(self, dashboard_service, mock_database_service):
        """Test handling of malformed usage log data."""
        # Mock malformed data
        malformed_logs = [
            {"incomplete": "data"},
            {"timestamp": "invalid-date", "user_id": None},
            {"success": "not-boolean", "latency_ms": "not-number"},
            # Some valid data mixed in
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": "user_1",
                "success": True,
                "latency_ms": 100,
            },
        ]

        mock_database_service.select.return_value = malformed_logs

        # Should handle gracefully
        with patch.object(
            dashboard_service.api_key_service,
            "check_all_services_health",
            return_value={},
        ):
            dashboard_data = await dashboard_service.get_dashboard_data()

        assert isinstance(dashboard_data, DashboardData)
        # Should process at least the valid records
        assert dashboard_data.metrics.total_requests >= 0

    # Integration tests

    async def test_full_dashboard_workflow(self, dashboard_service, sample_usage_logs):
        """Test complete dashboard workflow integration."""
        # 1. Get initial dashboard data
        with patch.object(
            dashboard_service, "_query_usage_logs", return_value=sample_usage_logs
        ):
            with patch.object(
                dashboard_service.api_key_service,
                "check_all_services_health",
                return_value={
                    ServiceType.OPENAI: MagicMock(
                        status=ServiceHealthStatus.HEALTHY,
                        latency_ms=120.0,
                        checked_at=datetime.now(timezone.utc),
                    ),
                },
            ):
                dashboard_data = await dashboard_service.get_dashboard_data()

        assert isinstance(dashboard_data, DashboardData)
        initial_requests = dashboard_data.metrics.total_requests

        # 2. Create some alerts based on the data
        if dashboard_data.metrics.error_rate > 0.05:  # >5% error rate
            alert = await dashboard_service.create_alert(
                alert_type=AlertType.HIGH_ERROR_RATE,
                severity=AlertSeverity.HIGH,
                title="High Error Rate Detected",
                message=f"Error rate is {dashboard_data.metrics.error_rate:.2%}",
            )
            assert alert.alert_id in dashboard_service._active_alerts

        # 3. Check rate limits for active keys
        for user in dashboard_data.top_users[:3]:  # Check top 3 users
            key_id = f"key_for_{user.user_id}"
            rate_status = await dashboard_service.get_rate_limit_status(key_id)
            assert isinstance(rate_status, dict)
            assert "percentage_used" in rate_status

        # 4. Get updated dashboard data
        with patch.object(
            dashboard_service, "_query_usage_logs", return_value=sample_usage_logs
        ):
            with patch.object(
                dashboard_service.api_key_service,
                "check_all_services_health",
                return_value={
                    ServiceType.OPENAI: MagicMock(
                        status=ServiceHealthStatus.HEALTHY,
                        latency_ms=120.0,
                        checked_at=datetime.now(timezone.utc),
                    ),
                },
            ):
                updated_data = await dashboard_service.get_dashboard_data()

        # Verify consistency
        assert updated_data.metrics.total_requests == initial_requests
        assert len(updated_data.recent_alerts) >= 0

    async def test_health_score_calculation(self, dashboard_service):
        """Test overall health score calculation."""
        # Mock services with different health statuses
        with patch.object(
            dashboard_service.api_key_service,
            "check_all_services_health",
            return_value={
                ServiceType.OPENAI: MagicMock(
                    status=ServiceHealthStatus.HEALTHY,
                    latency_ms=100.0,
                    checked_at=datetime.now(timezone.utc),
                ),
                ServiceType.WEATHER: MagicMock(
                    status=ServiceHealthStatus.DEGRADED,
                    latency_ms=400.0,
                    checked_at=datetime.now(timezone.utc),
                ),
                ServiceType.GOOGLEMAPS: MagicMock(
                    status=ServiceHealthStatus.UNHEALTHY,
                    latency_ms=1000.0,
                    checked_at=datetime.now(timezone.utc),
                ),
            },
        ):
            dashboard_data = await dashboard_service.get_dashboard_data()

        # Verify health score calculation
        health_score = dashboard_data.overall_health_score
        assert 0.0 <= health_score <= 100.0

        # Health score should reflect mixed service states
        # With 1 healthy, 1 degraded, 1 unhealthy, score should be moderate
        assert 30.0 <= health_score <= 80.0

    # Test utilities and helpers

    async def test_get_cache_statistics(self, dashboard_service, mock_cache_service):
        """Test cache statistics retrieval."""
        stats = await dashboard_service._get_cache_statistics()

        assert isinstance(stats, dict)
        assert "connected" in stats
        assert stats["connected"] is True  # Mock is connected

        # When cache is None
        dashboard_service.cache = None
        empty_stats = await dashboard_service._get_cache_statistics()
        assert empty_stats == {}

    async def test_query_usage_logs_filtering(
        self, dashboard_service, mock_database_service
    ):
        """Test usage logs querying with time filtering."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)

        await dashboard_service._query_usage_logs(start_time, end_time)

        # Verify database was called with correct parameters
        mock_database_service.select.assert_called_once()
        call_args = mock_database_service.select.call_args
        assert call_args[0][0] == "api_key_usage_logs"  # table name

        # Verify time filters were applied
        filters = call_args[1]["filters"]
        assert "timestamp__gte" in filters
        assert "timestamp__lte" in filters

    # Compatibility tests

    async def test_legacy_compatibility(self, dashboard_service):
        """Test compatibility with legacy dashboard data format."""
        with patch.object(
            dashboard_service.api_key_service,
            "check_all_services_health",
            return_value={},
        ):
            dashboard_data = await dashboard_service.get_dashboard_data()

        # Verify legacy fields are present
        assert hasattr(dashboard_data, "total_requests")
        assert hasattr(dashboard_data, "total_errors")
        assert hasattr(dashboard_data, "overall_success_rate")
        assert hasattr(dashboard_data, "active_keys")
        assert hasattr(dashboard_data, "top_users_legacy")
        assert hasattr(dashboard_data, "services_status")
        assert hasattr(dashboard_data, "usage_by_service")

    async def test_api_key_validator_compatibility(self):
        """Test ApiKeyValidator compatibility wrapper."""
        async with ApiKeyValidator() as validator:
            assert hasattr(validator, "api_key_service")
            assert hasattr(validator, "check_all_services_health")

            # Test the method exists and is callable
            health_checks = await validator.check_all_services_health()
            assert isinstance(health_checks, dict)
