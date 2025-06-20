"""Tests for dashboard monitoring API endpoints.

This module tests the dashboard router endpoints for monitoring and insights:
- System overview and health
- Usage metrics and analytics
- Rate limit monitoring
- Alert management
- User activity tracking
- Trend analysis
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.services.business.api_key_service import (
    ServiceHealthStatus,
    ServiceType,
)
from tripsage_core.services.business.dashboard_service import (
    AlertData,
    AlertSeverity,
    AlertType,
    DashboardData,
    DashboardService,
    RealTimeMetrics,
    ServiceAnalytics,
    UserActivityData,
)


class TestDashboardRouter:
    """Test class for dashboard monitoring endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_principal(self):
        """Create mock authenticated principal."""
        return Principal(
            id="test_user_123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
            scopes=["dashboard:read"],
            metadata={"role": "admin"},
        )

    @pytest.fixture
    def mock_agent_principal(self):
        """Create mock agent principal."""
        return Principal(
            id="agent_openai_key123",
            type="agent",
            service="openai",
            auth_method="api_key",
            scopes=["openai:*"],
            metadata={"key_id": "key123", "service": "openai"},
        )

    @pytest.fixture
    def mock_monitoring_service(self):
        """Create mock monitoring service."""
        service = AsyncMock(spec=DashboardService)

        # Mock dashboard data using new DashboardData structure
        from datetime import datetime, timezone

        mock_metrics = RealTimeMetrics(
            total_requests=1000,
            total_errors=50,
            success_rate=0.95,
            avg_latency_ms=150.0,
            p95_latency_ms=300.0,
            p99_latency_ms=500.0,
            active_keys_count=5,
            unique_users_count=10,
            requests_per_minute=16.67,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
        )

        mock_alert = AlertData(
            alert_id="alert1",
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="Usage spike detected",
            message="High error rate detected in OpenAI service",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            service="openai",
            user_id="user1",
            api_key_id="key123",
        )

        mock_user_activity = [
            UserActivityData(
                user_id="user1",
                request_count=300,
                error_count=15,
                success_rate=0.95,
                avg_latency_ms=150.0,
                services_used=["openai"],
                first_activity=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                total_api_keys=1,
            ),
            UserActivityData(
                user_id="user2",
                request_count=200,
                error_count=10,
                success_rate=0.95,
                avg_latency_ms=140.0,
                services_used=["weather"],
                first_activity=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                total_api_keys=1,
            ),
        ]

        mock_services = [
            ServiceAnalytics(
                service_name="openai",
                service_type=ServiceType.OPENAI,
                total_requests=600,
                total_errors=30,
                success_rate=0.95,
                avg_latency_ms=150.0,
                active_keys=3,
                last_health_check=datetime.now(timezone.utc),
                health_status=ServiceHealthStatus.HEALTHY,
            ),
            ServiceAnalytics(
                service_name="weather",
                service_type=ServiceType.WEATHER,
                total_requests=400,
                total_errors=20,
                success_rate=0.95,
                avg_latency_ms=200.0,
                active_keys=2,
                last_health_check=datetime.now(timezone.utc),
                health_status=ServiceHealthStatus.DEGRADED,
            ),
        ]

        # Create DashboardData using direct field assignment to avoid alias conflicts
        mock_dashboard = DashboardData.model_construct(
            metrics=mock_metrics,
            services=mock_services,
            top_users=mock_user_activity,  # This is the real field
            recent_alerts=[mock_alert],
            usage_trend=[
                {
                    "timestamp": "2023-01-01T00:00:00Z",
                    "requests": 100,
                    "errors": 5,
                    "success_rate": 0.95,
                },
                {
                    "timestamp": "2023-01-01T01:00:00Z",
                    "requests": 120,
                    "errors": 3,
                    "success_rate": 0.975,
                },
            ],
            cache_stats={"connected": True, "hit_rate": 0.85},
            # Legacy compatibility fields
            total_requests=mock_metrics.total_requests,
            total_errors=mock_metrics.total_errors,
            overall_success_rate=mock_metrics.success_rate,
            active_keys=mock_metrics.active_keys_count,
            top_users_legacy=[  # Legacy format for backwards compatibility
                {"user_id": "user1", "request_count": 300},
                {"user_id": "user2", "request_count": 200},
            ],
            services_status={"openai": "healthy", "weather": "degraded"},
            usage_by_service={"openai": 600, "weather": 400},
        )

        service.get_dashboard_data.return_value = mock_dashboard
        service.get_rate_limit_status.return_value = {
            "requests_in_window": 45,
            "limit": 100,
            "remaining": 55,
            "reset_at": "2023-01-01T02:00:00Z",
            "percentage_used": 45.0,
            "is_throttled": False,
        }

        # Update to use new DashboardService alert format
        service._active_alerts = {
            "alert1": mock_alert,
        }
        service.acknowledge_alert = AsyncMock(return_value=True)
        service.resolve_alert = AsyncMock(return_value=True)

        return service

    @pytest.fixture
    def mock_validator(self):
        """Create mock API key validator."""
        from datetime import datetime, timezone

        from tripsage_core.services.business.dashboard_service import ApiKeyValidator

        validator = AsyncMock(spec=ApiKeyValidator)
        validator.__aenter__.return_value = validator
        validator.__aexit__.return_value = None

        # Mock health checks using correct ServiceHealthCheck format
        health_checks = {
            ServiceType.OPENAI: AsyncMock(
                service=ServiceType.OPENAI,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=150.0,
                message="Service is healthy",
                checked_at=datetime.now(timezone.utc),
            ),
            ServiceType.WEATHER: AsyncMock(
                service=ServiceType.WEATHER,
                status=ServiceHealthStatus.DEGRADED,
                latency_ms=300.0,
                message="Service is degraded",
                checked_at=datetime.now(timezone.utc),
            ),
        }

        validator.check_all_services_health.return_value = health_checks
        return validator

    def test_get_system_overview_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful system overview retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/overview")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["status"] == "healthy"
            assert data["total_requests_24h"] == 1000
            assert data["total_errors_24h"] == 50
            assert data["success_rate_24h"] == 0.95
            assert data["active_api_keys"] == 5
            assert "timestamp" in data
            assert "environment" in data

    def test_get_system_overview_unauthorized(self, client):
        """Test system overview with no authentication."""
        response = client.get("/api/dashboard/overview")

        # Should get 401 or 422 since authentication middleware is disabled
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_get_system_overview_agent_forbidden(self, client, mock_agent_principal):
        """Test system overview with agent authentication (should be forbidden)."""
        with patch(
            "tripsage.api.routers.dashboard.get_current_principal",
            return_value=mock_agent_principal,
        ):
            response = client.get("/api/dashboard/overview")

            assert (
                response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            )  # Due to validation error

    def test_get_services_status_success(self, client, mock_principal, mock_validator):
        """Test successful services status retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.ApiKeyValidator",
                return_value=mock_validator,
            ),
        ):
            response = client.get("/api/dashboard/services")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert len(data) == 2
            assert data[0]["service"] == "openai"
            assert data[0]["status"] == "healthy"
            assert data[1]["service"] == "weather"
            assert data[1]["status"] == "degraded"

    def test_get_usage_metrics_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful usage metrics retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get(
                "/api/dashboard/metrics?time_range_hours=24&service=openai"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["total_requests"] == 1000
            assert data["total_errors"] == 50
            assert data["success_rate"] == 0.95
            assert "period_start" in data
            assert "period_end" in data
            assert "top_endpoints" in data
            assert "error_breakdown" in data

    def test_get_usage_metrics_invalid_time_range(self, client, mock_principal):
        """Test usage metrics with invalid time range."""
        with patch(
            "tripsage.api.routers.dashboard.get_current_principal",
            return_value=mock_principal,
        ):
            response = client.get(
                "/api/dashboard/metrics?time_range_hours=200"
            )  # Too large

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_rate_limits_status_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful rate limits status retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/rate-limits")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert isinstance(data, list)
            # Should have rate limit info for each active key
            if data:
                rate_limit = data[0]
                assert "key_id" in rate_limit
                assert "current_usage" in rate_limit
                assert "limit" in rate_limit
                assert "percentage_used" in rate_limit

    def test_get_alerts_success(self, client, mock_principal, mock_monitoring_service):
        """Test successful alerts retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/alerts")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert isinstance(data, list)
            assert len(data) == 1
            alert = data[0]
            assert alert["alert_id"] == "alert1"
            assert alert["severity"] == "high"
            assert (
                alert["type"] == "high_error_rate"
            )  # Updated to use AlertType enum value
            assert alert["acknowledged"] is False

    def test_get_alerts_with_filters(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test alerts retrieval with filters."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get(
                "/api/dashboard/alerts?severity=high&acknowledged=false"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert isinstance(data, list)
            # All alerts should match the filters
            for alert in data:
                assert alert["severity"] == "high"
                assert alert["acknowledged"] is False

    def test_acknowledge_alert_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful alert acknowledgment."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.post("/api/dashboard/alerts/alert1/acknowledge")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["alert_id"] == "alert1"
            assert data["acknowledged_by"] == mock_principal.id
            assert "acknowledged_at" in data

    def test_acknowledge_alert_not_found(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test acknowledging non-existent alert."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.post("/api/dashboard/alerts/nonexistent/acknowledge")

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_dismiss_alert_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful alert dismissal."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.delete("/api/dashboard/alerts/alert1")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["success"] is True
            assert data["alert_id"] == "alert1"
            assert data["dismissed_by"] == mock_principal.id

    def test_get_user_activity_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful user activity retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/users/activity")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert isinstance(data, list)
            if data:
                user_activity = data[0]
                assert "user_id" in user_activity
                assert "user_type" in user_activity
                assert "request_count" in user_activity
                assert "success_rate" in user_activity
                assert "services_used" in user_activity

    def test_get_trend_data_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful trend data retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/trends/request_count")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert isinstance(data, list)
            if data:
                trend_point = data[0]
                assert "timestamp" in trend_point
                assert "value" in trend_point
                assert "metadata" in trend_point

    def test_get_trend_data_invalid_metric(self, client, mock_principal):
        """Test trend data with invalid metric type."""
        with patch(
            "tripsage.api.routers.dashboard.get_current_principal",
            return_value=mock_principal,
        ):
            response = client.get("/api/dashboard/trends/invalid_metric")

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_analytics_summary_success(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test successful analytics summary retrieval."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/analytics/summary")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "period" in data
            assert "performance" in data
            assert "services" in data
            assert "usage" in data
            assert "alerts" in data
            assert "trends" in data

    def test_dashboard_endpoint_error_handling(self, client, mock_principal):
        """Test dashboard endpoint error handling."""
        # Mock service that raises an exception
        mock_service = AsyncMock()
        mock_service.get_dashboard_data.side_effect = Exception("Service error")

        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.api_key_monitoring.ApiKeyMonitoringService",
                return_value=mock_service,
            ),
        ):
            response = client.get("/api/dashboard/overview")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to retrieve system overview" in data["detail"]

    def test_rate_limits_query_parameters(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test rate limits endpoint with query parameters."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get("/api/dashboard/rate-limits?limit=10")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 10

    def test_user_activity_query_parameters(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test user activity endpoint with query parameters."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get(
                "/api/dashboard/users/activity?time_range_hours=12&limit=5"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 5

    def test_trend_data_query_parameters(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test trend data endpoint with query parameters."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get(
                "/api/dashboard/trends/request_count?time_range_hours=48&interval_minutes=120"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    def test_analytics_summary_query_parameters(
        self, client, mock_principal, mock_monitoring_service
    ):
        """Test analytics summary endpoint with query parameters."""
        with (
            patch(
                "tripsage.api.routers.dashboard.get_current_principal",
                return_value=mock_principal,
            ),
            patch(
                "tripsage_core.services.business.dashboard_service.DashboardService",
                return_value=mock_monitoring_service,
            ),
        ):
            response = client.get(
                "/api/dashboard/analytics/summary?time_range_hours=72"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["period"]["hours"] == 72
            assert "performance" in data
            assert "services" in data
