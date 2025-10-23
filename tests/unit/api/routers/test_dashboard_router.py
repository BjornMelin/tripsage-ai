"""Unit tests for dashboard API router."""

from __future__ import annotations

from contextlib import AbstractContextManager, ExitStack
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from tripsage.api.core import dependencies as core_dependencies
from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers import dashboard as dashboard_router
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
    UserActivityData,
)


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_principal() -> Principal:
    """Create authenticated principal."""
    return Principal(
        id="user_123",
        type="user",
        email="user@example.com",
        auth_method="jwt",
        scopes=["dashboard:read"],
        metadata={"role": "admin"},
    )


@pytest.fixture
def dashboard_payload() -> DashboardData:
    """Build reusable dashboard payload."""
    now = datetime.now(UTC)
    metrics = RealTimeMetrics(
        total_requests=1200,
        total_errors=60,
        success_rate=0.95,
        avg_latency_ms=150.0,
        p95_latency_ms=320.0,
        p99_latency_ms=480.0,
        active_keys_count=8,
        unique_users_count=25,
        requests_per_minute=20.0,
        period_start=now - timedelta(hours=24),
        period_end=now,
    )

    services = [
        ServiceAnalytics(
            service_name="openai",
            service_type=ServiceType.OPENAI,
            total_requests=700,
            total_errors=30,
            success_rate=0.957,
            avg_latency_ms=140.0,
            active_keys=5,
            last_health_check=now,
            health_status=ServiceHealthStatus.HEALTHY,
        ),
        ServiceAnalytics(
            service_name="weather",
            service_type=ServiceType.WEATHER,
            total_requests=500,
            total_errors=30,
            success_rate=0.94,
            avg_latency_ms=210.0,
            active_keys=3,
            last_health_check=now,
            health_status=ServiceHealthStatus.DEGRADED,
        ),
    ]

    alerts = [
        AlertData(
            alert_id="alert_1",
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.HIGH,
            title="High error rate",
            message="Elevated error rate detected",
            created_at=now - timedelta(minutes=5),
            updated_at=now,
            service="openai",
            user_id="user_123",
            api_key_id="key_123",
            acknowledged=False,
            resolved=False,
        )
    ]

    users = [
        UserActivityData(
            user_id="user_123",
            request_count=400,
            error_count=10,
            success_rate=0.975,
            avg_latency_ms=130.0,
            services_used=["openai"],
            first_activity=now - timedelta(hours=12),
            last_activity=now,
            total_api_keys=2,
        )
    ]

    return DashboardData(
        metrics=metrics,
        services=services,
        top_users=users,
        recent_alerts=alerts,
        usage_trend=[
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "requests": 80,
                "errors": 4,
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "requests": 100,
                "errors": 6,
            },
        ],
        cache_stats={"connected": True, "hit_rate": 0.88},
    )


def _mock_dependencies(principal: Principal) -> tuple[ExitStack, AsyncMock, AsyncMock]:
    """Apply dependency overrides and return stack plus mocks."""
    mock_settings = Mock()
    mock_settings.environment = "test"
    mock_settings.rate_limit_enabled = False
    mock_settings.rate_limit_enable_monitoring = False

    mock_cache = AsyncMock()
    mock_cache.pipeline.return_value = Mock(
        get=Mock(return_value=None),
        set=Mock(return_value=None),
        execute=Mock(return_value=None),
    )
    mock_db = AsyncMock()

    stack = ExitStack()
    stack.enter_context(
        patch(
            "tripsage.api.core.dependencies.get_settings_dependency",
            return_value=mock_settings,
        )
    )

    async def cache_override() -> AsyncMock:
        return mock_cache

    async def db_override() -> AsyncMock:
        return mock_db

    async def principal_override() -> Principal:
        return principal

    app.dependency_overrides[core_dependencies.get_cache_service_dep] = cache_override
    stack.callback(
        app.dependency_overrides.pop, core_dependencies.get_cache_service_dep, None
    )

    app.dependency_overrides[core_dependencies.get_db] = db_override
    stack.callback(app.dependency_overrides.pop, core_dependencies.get_db, None)

    app.dependency_overrides[dashboard_router.get_current_principal] = (
        principal_override
    )
    stack.callback(
        app.dependency_overrides.pop,
        dashboard_router.get_current_principal,
        None,
    )

    return stack, mock_cache, mock_db


def _mock_dashboard_service(
    payload: DashboardData,
) -> tuple[AsyncMock, AbstractContextManager[AsyncMock]]:
    """Patch DashboardService to return payload."""
    service = AsyncMock(spec=DashboardService)
    service.get_dashboard_data.return_value = payload

    health_checks = {
        ServiceType.OPENAI: ApiValidationResult(
            service=ServiceType.OPENAI,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.HEALTHY,
            latency_ms=120.0,
            message="Healthy",
            checked_at=datetime.now(UTC),
            validated_at=None,
        ),
        ServiceType.WEATHER: ApiValidationResult(
            service=ServiceType.WEATHER,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.DEGRADED,
            latency_ms=320.0,
            message="Latency high",
            checked_at=datetime.now(UTC),
            validated_at=None,
        ),
    }
    api_key_service = AsyncMock()
    api_key_service.check_all_services_health.return_value = health_checks
    service.api_key_service = api_key_service

    rate_limit_status = {
        "requests_in_window": 50,
        "limit": 100,
        "remaining": 50,
        "reset_at": datetime.now(UTC).isoformat(),
        "percentage_used": 50.0,
        "is_throttled": False,
    }
    service.get_rate_limit_status.return_value = rate_limit_status

    patcher: AbstractContextManager[AsyncMock] = patch(
        "tripsage.api.routers.dashboard.DashboardService", return_value=service
    )
    return service, patcher


def test_get_system_overview_success(
    client: TestClient,
    mock_principal: Principal,
    dashboard_payload: DashboardData,
) -> None:
    """System overview endpoint returns transformed metrics."""
    service, service_patch = _mock_dashboard_service(dashboard_payload)
    stack, _, _ = _mock_dependencies(mock_principal)
    stack.enter_context(service_patch)

    with stack:
        response = client.get("/api/dashboard/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_requests_24h"] == dashboard_payload.metrics.total_requests
    assert data["success_rate_24h"] == pytest.approx(
        dashboard_payload.metrics.success_rate, rel=1e-6
    )
    service.get_dashboard_data.assert_awaited()


def test_get_services_status_success(
    client: TestClient,
    mock_principal: Principal,
    dashboard_payload: DashboardData,
) -> None:
    """Services status endpoint returns health information."""
    service, service_patch = _mock_dashboard_service(dashboard_payload)
    stack, _, _ = _mock_dependencies(mock_principal)
    stack.enter_context(service_patch)

    with stack:
        response = client.get("/api/dashboard/services")

    assert response.status_code == 200
    services = response.json()
    assert len(services) == 2
    assert {item["service"] for item in services} == {"openai", "weather"}
    service.api_key_service.check_all_services_health.assert_awaited()


def test_get_usage_metrics_success(
    client: TestClient,
    mock_principal: Principal,
    dashboard_payload: DashboardData,
) -> None:
    """Usage metrics endpoint returns aggregated metrics."""
    service, service_patch = _mock_dashboard_service(dashboard_payload)
    stack, _, _ = _mock_dependencies(mock_principal)
    stack.enter_context(service_patch)

    with stack:
        response = client.get("/api/dashboard/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_requests"] == dashboard_payload.metrics.total_requests
    assert payload["total_errors"] == dashboard_payload.metrics.total_errors
    assert payload["success_rate"] == pytest.approx(
        dashboard_payload.metrics.success_rate, rel=1e-6
    )
    service.get_dashboard_data.assert_awaited()


def test_get_rate_limits_success(
    client: TestClient,
    mock_principal: Principal,
    dashboard_payload: DashboardData,
) -> None:
    """Rate limit endpoint returns cached status."""
    service, service_patch = _mock_dashboard_service(dashboard_payload)
    stack, _, _ = _mock_dependencies(mock_principal)
    stack.enter_context(service_patch)

    with stack:
        response = client.get("/api/dashboard/rate-limits")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["limit"] == 100
    service.get_rate_limit_status.assert_awaited()


def test_analytics_summary_success(
    client: TestClient,
    mock_principal: Principal,
    dashboard_payload: DashboardData,
) -> None:
    """Analytics summary endpoint aggregates data."""
    service, service_patch = _mock_dashboard_service(dashboard_payload)
    stack, _, _ = _mock_dependencies(mock_principal)
    stack.enter_context(service_patch)

    with stack:
        response = client.get("/api/dashboard/analytics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["performance"]["total_requests"]
        == dashboard_payload.metrics.total_requests
    )
    assert (
        payload["usage"]["active_api_keys"]
        == dashboard_payload.metrics.active_keys_count
    )
    service.get_dashboard_data.assert_awaited()
