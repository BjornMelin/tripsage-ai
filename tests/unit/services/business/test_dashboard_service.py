"""Unit tests for DashboardService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from tripsage_core.services.business.api_key_service import (
    ApiValidationResult,
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
)


pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_cache_service() -> AsyncMock:
    """Create a mock cache service."""
    cache = AsyncMock()
    cache.is_connected = True
    return cache


@pytest.fixture
def mock_database_service() -> AsyncMock:
    """Create a mock database service."""
    return AsyncMock()


@pytest.fixture
def mock_api_key_service() -> AsyncMock:
    """Create a mock ApiKeyService."""
    service = AsyncMock()
    now = datetime.now(UTC)
    service.check_all_services_health.return_value = {
        ServiceType.OPENAI: ApiValidationResult(
            service=ServiceType.OPENAI,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.HEALTHY,
            latency_ms=150.0,
            message="Operational",
            checked_at=now,
            validated_at=None,
        ),
        ServiceType.WEATHER: ApiValidationResult(
            service=ServiceType.WEATHER,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.DEGRADED,
            latency_ms=450.0,
            message="Elevated latency",
            checked_at=now,
            validated_at=None,
        ),
    }
    return service


@pytest.fixture
def dashboard_service(
    mock_cache_service: AsyncMock,
    mock_database_service: AsyncMock,
    mock_api_key_service: AsyncMock,
) -> DashboardService:
    """Create DashboardService with mocked dependencies."""
    with patch(
        "tripsage_core.services.business.dashboard_service.ApiKeyService",
        return_value=mock_api_key_service,
    ):
        return DashboardService(
            cache_service=mock_cache_service,
            database_service=mock_database_service,
            settings=None,
        )


@pytest.fixture
def sample_usage_logs() -> list[dict[str, object]]:
    """Create representative usage logs."""
    now = datetime.now(UTC)
    return [
        {
            "user_id": "user_a",
            "key_id": "key_a",
            "service": "openai",
            "timestamp": now - timedelta(minutes=10),
            "success": True,
            "latency_ms": 120.0,
        },
        {
            "user_id": "user_a",
            "key_id": "key_a",
            "service": "openai",
            "timestamp": now - timedelta(minutes=20),
            "success": False,
            "latency_ms": 300.0,
        },
        {
            "user_id": "user_b",
            "key_id": "key_b",
            "service": "weather",
            "timestamp": now - timedelta(minutes=5),
            "success": True,
            "latency_ms": 180.0,
        },
    ]


class TestDashboardService:
    """Tests covering the main DashboardService functionality."""

    async def test_get_dashboard_data_fallback(
        self, dashboard_service: DashboardService
    ) -> None:
        """Return fallback data when dependencies raise."""
        dashboard_service.db = None
        dashboard_service.cache = None

        result = await dashboard_service.get_dashboard_data()

        assert result.metrics.total_requests > 0
        assert result.metrics.success_rate == pytest.approx(0.95, rel=1e-2)
        assert not result.top_users
        assert not result.recent_alerts

    async def test_get_dashboard_data_with_metrics(
        self,
        dashboard_service: DashboardService,
        mock_database_service: AsyncMock,
        sample_usage_logs: list[dict[str, object]],
    ) -> None:
        """Return dashboard data populated from usage logs."""
        mock_database_service.select.return_value = sample_usage_logs
        assert isinstance(dashboard_service.cache, AsyncMock)
        dashboard_service.cache.get_json.return_value = None

        result = await dashboard_service.get_dashboard_data(time_range_hours=1)

        assert result.metrics.total_requests == len(sample_usage_logs)
        assert result.metrics.total_errors == 1
        assert result.services  # Service analytics from mocked ApiKeyService
        assert result.top_users
        assert result.usage_trend

    async def test_real_time_metrics_from_logs(
        self,
        dashboard_service: DashboardService,
        mock_database_service: AsyncMock,
        sample_usage_logs: list[dict[str, object]],
    ) -> None:
        """Aggregate real-time metrics from usage logs."""
        mock_database_service.select.return_value = sample_usage_logs
        assert isinstance(dashboard_service.cache, AsyncMock)
        dashboard_service.cache.get_json.return_value = None

        metrics = await dashboard_service._get_real_time_metrics(time_range_hours=1)

        assert metrics.total_requests == 3
        assert metrics.total_errors == 1
        assert metrics.success_rate == pytest.approx(2 / 3, rel=1e-6)
        assert metrics.unique_users_count == 2
        assert metrics.active_keys_count == 2

    async def test_service_analytics(
        self,
        dashboard_service: DashboardService,
        mock_api_key_service: AsyncMock,
        mock_database_service: AsyncMock,
        sample_usage_logs: list[dict[str, object]],
    ) -> None:
        """Return per-service analytics using health checks."""
        mock_database_service.select.return_value = sample_usage_logs
        mock_api_key_service.check_all_services_health.return_value = {
            ServiceType.OPENAI: ApiValidationResult(
                service=ServiceType.OPENAI,
                is_valid=None,
                status=None,
                health_status=ServiceHealthStatus.HEALTHY,
                latency_ms=120.0,
                message="All good",
                checked_at=datetime.now(UTC),
                validated_at=None,
            )
        }

        services = await dashboard_service._get_service_analytics(time_range_hours=1)

        assert len(services) == 1
        service = services[0]
        assert service.service_name == "openai"
        assert service.total_requests == 2
        assert service.total_errors == 1
        assert service.success_rate == pytest.approx(0.5, rel=1e-6)

    async def test_user_activity_data(
        self,
        dashboard_service: DashboardService,
        mock_database_service: AsyncMock,
        sample_usage_logs: list[dict[str, object]],
    ) -> None:
        """Aggregate user activity data."""
        mock_database_service.select.return_value = sample_usage_logs

        users = await dashboard_service._get_user_activity_data(
            time_range_hours=1, limit=5
        )

        assert len(users) == 2
        assert {user.user_id for user in users} == {"user_a", "user_b"}

    async def test_alert_lifecycle(self, dashboard_service: DashboardService) -> None:
        """Create, acknowledge, and resolve alerts."""
        alert = await dashboard_service.create_alert(
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="High error rate",
            message="Investigate errors",
        )
        assert isinstance(alert, AlertData)

        acknowledged = await dashboard_service.acknowledge_alert(
            alert.alert_id, user_id="user_a"
        )
        assert acknowledged

        resolved = await dashboard_service.resolve_alert(alert.alert_id)
        assert resolved

    async def test_rate_limit_status_without_cache(
        self, dashboard_service: DashboardService
    ) -> None:
        """Return deterministic defaults when cache unavailable."""
        dashboard_service.cache = None
        status = await dashboard_service.get_rate_limit_status(
            key_id="key_123", window_minutes=60
        )

        assert status["limit"] == 1000
        assert status["reset_at"]
        assert status["percentage_used"] >= 0

    async def test_rate_limit_status_with_cache(
        self, dashboard_service: DashboardService, mock_cache_service: AsyncMock
    ) -> None:
        """Return cached rate limit status."""
        assert isinstance(dashboard_service.cache, AsyncMock)
        mock_cache_service.get_json.return_value = {
            "count": 80,
            "limit": 100,
            "reset_at": datetime.now(UTC).isoformat(),
        }

        status = await dashboard_service.get_rate_limit_status(
            key_id="key_abc", window_minutes=15
        )

        assert status["requests_in_window"] == 80
        assert status["limit"] == 100
        assert status["is_throttled"] is False

    def test_overall_health_score(self) -> None:
        """Compute overall health score from metrics and services."""
        metrics = RealTimeMetrics(
            total_requests=1000,
            total_errors=20,
            success_rate=0.98,
            avg_latency_ms=140.0,
            p95_latency_ms=250.0,
            p99_latency_ms=320.0,
            active_keys_count=12,
            unique_users_count=50,
            requests_per_minute=40.0,
            period_start=datetime.now(UTC) - timedelta(hours=1),
            period_end=datetime.now(UTC),
        )
        services = [
            ServiceAnalytics(
                service_name="openai",
                service_type=ServiceType.OPENAI,
                total_requests=600,
                total_errors=10,
                success_rate=0.99,
                avg_latency_ms=130.0,
                active_keys=8,
                last_health_check=datetime.now(UTC),
                health_status=ServiceHealthStatus.HEALTHY,
            ),
            ServiceAnalytics(
                service_name="weather",
                service_type=ServiceType.WEATHER,
                total_requests=400,
                total_errors=10,
                success_rate=0.975,
                avg_latency_ms=160.0,
                active_keys=4,
                last_health_check=datetime.now(UTC),
                health_status=ServiceHealthStatus.HEALTHY,
            ),
        ]

        dashboard_data = DashboardData(
            metrics=metrics,
            services=services,
            top_users=[],
            recent_alerts=[],
            usage_trend=[],
            cache_stats={},
        )

        score = dashboard_data.overall_health_score
        assert 0 < score <= 100
        assert score >= 70.0


class TestDashboardServiceCaching:
    """Tests focused on caching behaviour."""

    async def test_metrics_cached(
        self,
        dashboard_service: DashboardService,
        mock_database_service: AsyncMock,
        mock_cache_service: AsyncMock,
        sample_usage_logs: list[dict[str, object]],
    ) -> None:
        """Store computed metrics in cache."""
        mock_cache_service.get_json.return_value = None
        mock_database_service.select.return_value = sample_usage_logs

        await dashboard_service._get_real_time_metrics(time_range_hours=1)

        assert mock_cache_service.set_json.called

    async def test_rate_limit_cache_miss(
        self, dashboard_service: DashboardService, mock_cache_service: AsyncMock
    ) -> None:
        """Fallback to defaults on cache miss."""
        mock_cache_service.get_json.return_value = None

        status = await dashboard_service.get_rate_limit_status("key_xyz", 30)

        assert status["limit"] == 1000
        assert status["remaining"] >= 0
