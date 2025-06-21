"""Integration tests for dashboard monitoring API endpoints.

This module provides comprehensive integration tests for the dashboard
monitoring and analytics functionality, including real-time features.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal


# Legacy compatibility models for testing
class AnomalyType:
    SPIKE = "spike"
    ERROR_RATE = "error_rate"


class UsageAlert:
    def __init__(
        self,
        alert_id,
        key_id,
        user_id,
        service,
        anomaly_type,
        severity,
        message,
        details=None,
    ):
        self.alert_id = alert_id
        self.key_id = key_id
        self.user_id = user_id
        self.service = service
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.message = message
        self.details = details or {}


class UsageDashboard:
    def __init__(
        self,
        total_requests,
        total_errors,
        overall_success_rate,
        active_keys,
        services_status,
        top_users,
        recent_alerts,
        usage_by_service,
        usage_trend,
    ):
        self.total_requests = total_requests
        self.total_errors = total_errors
        self.overall_success_rate = overall_success_rate
        self.active_keys = active_keys
        self.services_status = services_status
        self.top_users = top_users
        self.recent_alerts = recent_alerts
        self.usage_by_service = usage_by_service
        self.usage_trend = usage_trend


class ApiKeyMonitoringService:
    pass


class TestDashboardIntegration:
    """Integration tests for dashboard monitoring endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def authenticated_user(self):
        """Mock authenticated user principal."""
        return Principal(
            id="test_admin_123",
            type="user",
            email="admin@tripsage.com",
            auth_method="jwt",
            scopes=["dashboard:read", "dashboard:write"],
            metadata={"role": "admin"},
        )

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = True
        cache.ping.return_value = True
        cache.zadd.return_value = 1
        cache.zcount.return_value = 10
        cache.expire.return_value = True
        cache.hincrby.return_value = 1
        cache.keys.return_value = ["usage:stats:key1", "usage:stats:key2"]
        cache.info.return_value = {
            "used_memory_human": "64M",
            "connected_clients": "5",
            "total_commands_processed": "12345",
        }
        return cache

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        db = AsyncMock()
        db.execute_query.return_value = [{"health_check": 1}]
        return db

    @pytest.fixture
    def comprehensive_dashboard_data(self):
        """Comprehensive dashboard data for testing."""
        return UsageDashboard(
            total_requests=5000,
            total_errors=150,
            overall_success_rate=0.97,
            active_keys=15,
            services_status={
                "openai": "healthy",
                "weather": "healthy",
                "googlemaps": "degraded",
                "duffel": "unhealthy",
            },
            top_users=[
                {"user_id": "user_001", "request_count": 800},
                {"user_id": "user_002", "request_count": 650},
                {"user_id": "user_003", "request_count": 500},
                {"user_id": "agent_openai_key1", "request_count": 1200},
            ],
            recent_alerts=[
                UsageAlert(
                    alert_id="alert_001",
                    key_id="key_001",
                    user_id="user_001",
                    service="openai",
                    anomaly_type=AnomalyType.SPIKE,
                    severity="high",
                    message="Unusual spike in OpenAI API usage",
                    details={"spike_ratio": 4.5, "threshold": 3.0},
                ),
                UsageAlert(
                    alert_id="alert_002",
                    key_id="key_002",
                    user_id="user_002",
                    service="googlemaps",
                    anomaly_type=AnomalyType.ERROR_RATE,
                    severity="medium",
                    message="High error rate detected",
                    details={"error_rate": 0.15, "threshold": 0.1},
                ),
            ],
            usage_by_service={
                "openai": 2000,
                "weather": 1200,
                "googlemaps": 1000,
                "duffel": 800,
            },
            usage_trend=[
                {
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                    "requests": 180,
                    "errors": 8,
                    "success_rate": 0.955,
                },
                {
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                    "requests": 220,
                    "errors": 12,
                    "success_rate": 0.945,
                },
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "requests": 280,
                    "errors": 15,
                    "success_rate": 0.946,
                },
            ],
        )

    def test_dashboard_overview_comprehensive(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test comprehensive dashboard overview functionality."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.return_value = comprehensive_dashboard_data

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            response = client.get("/api/dashboard/overview")

            assert response.status_code == 200
            data = response.json()

            # Verify overview structure
            assert data["status"] == "healthy"  # >90% success rate
            assert data["total_requests_24h"] == 5000
            assert data["total_errors_24h"] == 150
            assert data["success_rate_24h"] == 0.97
            assert data["active_api_keys"] == 15
            assert data["active_users_24h"] == 4  # Top users count

            # Verify timestamp and environment
            assert "timestamp" in data
            assert "environment" in data
            assert "uptime_seconds" in data

    def test_services_status_comprehensive(self, client, authenticated_user, mock_cache_service):
        """Test comprehensive services status functionality."""
        # Mock external service health checks
        from tripsage_core.services.business.api_key_validator import (
            ServiceHealthCheck,
            ServiceHealthStatus,
            ServiceType,
        )

        mock_validator = AsyncMock()
        mock_validator.__aenter__.return_value = mock_validator
        mock_validator.__aexit__.return_value = None

        health_checks = {
            ServiceType.OPENAI: ServiceHealthCheck(
                service=ServiceType.OPENAI,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=120.0,
                message="OpenAI API is operational",
                details={"last_error": None, "response_time": "120ms"},
            ),
            ServiceType.WEATHER: ServiceHealthCheck(
                service=ServiceType.WEATHER,
                status=ServiceHealthStatus.DEGRADED,
                latency_ms=450.0,
                message="Weather API experiencing high latency",
                details={"last_error": "timeout", "response_time": "450ms"},
            ),
            ServiceType.GOOGLEMAPS: ServiceHealthCheck(
                service=ServiceType.GOOGLEMAPS,
                status=ServiceHealthStatus.UNHEALTHY,
                latency_ms=0.0,
                message="Google Maps API connection failed",
                details={
                    "last_error": "connection_refused",
                    "response_time": "timeout",
                },
            ),
        }

        mock_validator.check_all_services_health.return_value = health_checks

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_validator.ApiKeyValidator",
                return_value=mock_validator,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
        ):
            response = client.get("/api/dashboard/services")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 3

            # Check OpenAI service (healthy)
            openai_service = next(s for s in data if s["service"] == "openai")
            assert openai_service["status"] == "healthy"
            assert openai_service["latency_ms"] == 120.0
            assert openai_service["error_rate"] == 0.0
            assert openai_service["uptime_percentage"] == 100.0

            # Check Weather service (degraded)
            weather_service = next(s for s in data if s["service"] == "weather")
            assert weather_service["status"] == "degraded"
            assert weather_service["latency_ms"] == 450.0
            assert weather_service["error_rate"] == 0.1
            assert weather_service["uptime_percentage"] == 95.0

            # Check Google Maps service (unhealthy)
            gmaps_service = next(s for s in data if s["service"] == "googlemaps")
            assert gmaps_service["status"] == "unhealthy"
            assert gmaps_service["error_rate"] == 0.5
            assert gmaps_service["uptime_percentage"] == 80.0

    def test_usage_metrics_with_filters(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test usage metrics with various filters."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.return_value = comprehensive_dashboard_data
        mock_monitoring_service._generate_usage_trend.return_value = comprehensive_dashboard_data.usage_trend

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            # Test with time range filter
            response = client.get("/api/dashboard/metrics?time_range_hours=48")
            assert response.status_code == 200
            data = response.json()

            assert data["total_requests"] == 5000
            assert data["success_rate"] == 0.97
            assert "period_start" in data
            assert "period_end" in data

            # Verify latency metrics
            assert "avg_latency_ms" in data
            assert "p95_latency_ms" in data
            assert "p99_latency_ms" in data

            # Verify breakdown data
            assert "top_endpoints" in data
            assert "error_breakdown" in data
            assert len(data["top_endpoints"]) > 0

    def test_rate_limits_monitoring(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test rate limits monitoring functionality."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.return_value = comprehensive_dashboard_data

        # Mock rate limit data for multiple keys
        rate_limit_responses = {
            "key_001": {
                "requests_in_window": 75,
                "window_minutes": 60,
                "limit": 100,
                "remaining": 25,
                "reset_at": "2023-01-01T02:00:00Z",
            },
            "key_002": {
                "requests_in_window": 95,
                "window_minutes": 60,
                "limit": 100,
                "remaining": 5,
                "reset_at": "2023-01-01T02:00:00Z",
            },
        }

        async def mock_rate_limit_status(key_id, window_minutes=60):
            return rate_limit_responses.get(key_id, {"error": "Not found"})

        mock_monitoring_service.get_rate_limit_status.side_effect = mock_rate_limit_status
        mock_monitoring_service.recent_usage = {"key_001": [], "key_002": []}

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            response = client.get("/api/dashboard/rate-limits?limit=10")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 2

            # Check first key (75% usage)
            key1_data = next(item for item in data if item["key_id"] == "key_001")
            assert key1_data["current_usage"] == 75
            assert key1_data["limit"] == 100
            assert key1_data["remaining"] == 25
            assert key1_data["percentage_used"] == 75.0

            # Check second key (95% usage - approaching limit)
            key2_data = next(item for item in data if item["key_id"] == "key_002")
            assert key2_data["current_usage"] == 95
            assert key2_data["percentage_used"] == 95.0

    def test_alerts_management_workflow(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test complete alerts management workflow."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.return_value = comprehensive_dashboard_data

        # Set up active alerts
        mock_monitoring_service.active_alerts = {
            "alert_001": comprehensive_dashboard_data.recent_alerts[0],
            "alert_002": comprehensive_dashboard_data.recent_alerts[1],
        }

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            # 1. Get all alerts
            response = client.get("/api/dashboard/alerts")
            assert response.status_code == 200
            alerts = response.json()
            assert len(alerts) == 2

            # 2. Filter alerts by severity
            response = client.get("/api/dashboard/alerts?severity=high")
            assert response.status_code == 200
            high_alerts = response.json()
            assert len(high_alerts) == 1
            assert high_alerts[0]["severity"] == "high"

            # 3. Acknowledge an alert
            response = client.post("/api/dashboard/alerts/alert_001/acknowledge")
            assert response.status_code == 200
            ack_data = response.json()
            assert ack_data["success"] is True
            assert ack_data["alert_id"] == "alert_001"

            # 4. Dismiss an alert
            response = client.delete("/api/dashboard/alerts/alert_002")
            assert response.status_code == 200
            dismiss_data = response.json()
            assert dismiss_data["success"] is True
            assert dismiss_data["alert_id"] == "alert_002"

            # 5. Try to acknowledge non-existent alert
            response = client.post("/api/dashboard/alerts/nonexistent/acknowledge")
            assert response.status_code == 404

    def test_user_activity_analysis(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test user activity analysis functionality."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.return_value = comprehensive_dashboard_data

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            response = client.get("/api/dashboard/users/activity?time_range_hours=24&limit=5")

            assert response.status_code == 200
            data = response.json()

            assert len(data) == 4  # All top users

            # Check user activity structure
            user_activity = data[0]
            assert "user_id" in user_activity
            assert "user_type" in user_activity
            assert "request_count" in user_activity
            assert "error_count" in user_activity
            assert "success_rate" in user_activity
            assert "last_activity" in user_activity
            assert "services_used" in user_activity
            assert "avg_latency_ms" in user_activity

            # Verify user types are correctly identified
            agent_users = [u for u in data if u["user_type"] == "agent"]
            regular_users = [u for u in data if u["user_type"] == "user"]

            assert len(agent_users) == 1  # agent_openai_key1
            assert len(regular_users) == 3  # user_001, user_002, user_003

    def test_trend_analysis_multiple_metrics(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test trend analysis for multiple metrics."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service._generate_usage_trend.return_value = comprehensive_dashboard_data.usage_trend

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            # Test different metric types
            metrics = ["request_count", "error_rate", "latency", "active_users"]

            for metric in metrics:
                response = client.get(f"/api/dashboard/trends/{metric}?time_range_hours=24")
                assert response.status_code == 200

                data = response.json()
                assert len(data) == 3  # Three trend data points

                # Verify trend data structure
                trend_point = data[0]
                assert "timestamp" in trend_point
                assert "value" in trend_point
                assert "metadata" in trend_point

                # Verify values are appropriate for metric type
                if metric == "error_rate":
                    # Error rate should be between 0 and 1
                    assert 0 <= trend_point["value"] <= 1
                elif metric == "request_count":
                    # Request count should be positive
                    assert trend_point["value"] >= 0

    def test_analytics_summary_comprehensive(
        self,
        client,
        authenticated_user,
        comprehensive_dashboard_data,
        mock_cache_service,
        mock_db_service,
    ):
        """Test comprehensive analytics summary."""
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.return_value = comprehensive_dashboard_data
        mock_monitoring_service._generate_usage_trend.return_value = comprehensive_dashboard_data.usage_trend

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            response = client.get("/api/dashboard/analytics/summary?time_range_hours=72")

            assert response.status_code == 200
            data = response.json()

            # Verify summary structure
            assert "period" in data
            assert "performance" in data
            assert "services" in data
            assert "usage" in data
            assert "alerts" in data
            assert "trends" in data

            # Verify period information
            assert data["period"]["hours"] == 72
            assert "start" in data["period"]
            assert "end" in data["period"]

            # Verify performance metrics
            performance = data["performance"]
            assert performance["total_requests"] == 5000
            assert performance["total_errors"] == 150
            assert performance["success_rate"] == 0.97

            # Verify services breakdown
            services = data["services"]
            assert services["total_services"] == 4
            assert services["healthy_services"] == 2  # openai, weather
            assert services["degraded_services"] == 1  # googlemaps
            assert services["unhealthy_services"] == 1  # duffel

            # Verify usage information
            usage = data["usage"]
            assert usage["active_api_keys"] == 15
            assert usage["active_users"] == 4
            assert "usage_by_service" in usage

            # Verify alerts summary
            alerts = data["alerts"]
            assert alerts["total_alerts"] == 2
            assert alerts["high_alerts"] == 1
            assert alerts["unacknowledged_alerts"] == 2

    def test_dashboard_error_handling(self, client, authenticated_user, mock_cache_service, mock_db_service):
        """Test dashboard error handling scenarios."""
        # Test with service that throws exceptions
        mock_monitoring_service = AsyncMock(spec=ApiKeyMonitoringService)
        mock_monitoring_service.get_dashboard_data.side_effect = Exception("Service unavailable")

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=authenticated_user,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_monitoring_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
        ):
            # Test overview error handling
            response = client.get("/api/dashboard/overview")
            assert response.status_code == 500

            # Test metrics error handling
            response = client.get("/api/dashboard/metrics")
            assert response.status_code == 500

            # Test user activity error handling
            response = client.get("/api/dashboard/users/activity")
            assert response.status_code == 500
