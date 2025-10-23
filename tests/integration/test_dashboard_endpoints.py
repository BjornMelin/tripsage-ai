"""Integration-style tests for dashboard endpoints using patched dependencies."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from slowapi import extension as slowapi_extension


# SlowAPI's decorator validates function signatures at import-time, causing
# unrelated routers to explode in tests. Neutralize the decorator so imports
# succeed without pulling those routers into this suite.
slowapi_extension.Limiter.limit = lambda *args, **kwargs: (lambda func: func)

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


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    """Return FastAPI test client."""
    return TestClient(app)


@pytest.fixture(name="principal")
def fixture_principal() -> Principal:
    """Return authenticated principal."""
    return Principal(
        id="integration_user",
        type="user",
        email="integration@example.com",
        auth_method="jwt",
        scopes=["dashboard:read"],
        metadata={"role": "operator"},
    )


def _build_dashboard_payload() -> DashboardData:
    """Construct dashboard payload shared across tests."""
    now = datetime.now(UTC)
    metrics = RealTimeMetrics(
        total_requests=3600,
        total_errors=120,
        success_rate=0.966,
        avg_latency_ms=140.0,
        p95_latency_ms=275.0,
        p99_latency_ms=340.0,
        active_keys_count=18,
        unique_users_count=64,
        requests_per_minute=60.0,
        period_start=now - timedelta(hours=24),
        period_end=now,
    )

    services = [
        ServiceAnalytics(
            service_name="openai",
            service_type=ServiceType.OPENAI,
            total_requests=2200,
            total_errors=60,
            success_rate=0.973,
            avg_latency_ms=135.0,
            active_keys=12,
            last_health_check=now,
            health_status=ServiceHealthStatus.HEALTHY,
        ),
        ServiceAnalytics(
            service_name="weather",
            service_type=ServiceType.WEATHER,
            total_requests=1400,
            total_errors=60,
            success_rate=0.957,
            avg_latency_ms=188.0,
            active_keys=6,
            last_health_check=now,
            health_status=ServiceHealthStatus.DEGRADED,
        ),
    ]

    alerts = [
        AlertData(
            alert_id="integration_alert",
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            severity=AlertSeverity.MEDIUM,
            title="Latency increase",
            message="Latency exceeded 200ms for weather service",
            created_at=now - timedelta(minutes=12),
            updated_at=now - timedelta(minutes=4),
            service="weather",
            user_id=None,
            api_key_id=None,
            acknowledged=True,
            acknowledged_by="integration_user",
            acknowledged_at=now - timedelta(minutes=8),
        )
    ]

    users = [
        UserActivityData(
            user_id="integration_user",
            request_count=900,
            error_count=30,
            success_rate=0.966,
            avg_latency_ms=150.0,
            services_used=["openai", "weather"],
            first_activity=now - timedelta(hours=18),
            last_activity=now,
            total_api_keys=3,
        )
    ]

    return DashboardData(
        metrics=metrics,
        services=services,
        top_users=users,
        recent_alerts=alerts,
        usage_trend=[
            {
                "timestamp": (now - timedelta(hours=3)).isoformat(),
                "requests": 180,
                "errors": 8,
            },
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "requests": 210,
                "errors": 9,
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat(),
                "requests": 240,
                "errors": 10,
            },
        ],
        cache_stats={"connected": True, "hit_rate": 0.9},
    )


def _patch_dependencies(
    principal: Principal, payload: DashboardData
) -> tuple[ExitStack, AsyncMock]:
    """Create dependency override stack and patched service."""
    mock_settings = Mock()
    mock_settings.environment = "integration"
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

    dashboard_service = AsyncMock(spec=DashboardService)
    dashboard_service.get_dashboard_data.return_value = payload
    dashboard_service.get_rate_limit_status.return_value = {
        "requests_in_window": 120,
        "limit": 200,
        "remaining": 80,
        "reset_at": datetime.now(UTC).isoformat(),
        "percentage_used": 60.0,
        "is_throttled": False,
    }

    api_key_service = AsyncMock()
    api_key_service.check_all_services_health.return_value = {
        ServiceType.OPENAI: ApiValidationResult(
            service=ServiceType.OPENAI,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.HEALTHY,
            latency_ms=110.0,
            message="Operating normally",
            checked_at=datetime.now(UTC),
            validated_at=None,
        ),
        ServiceType.WEATHER: ApiValidationResult(
            service=ServiceType.WEATHER,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.DEGRADED,
            latency_ms=210.0,
            message="Latency elevated",
            checked_at=datetime.now(UTC),
            validated_at=None,
        ),
        ServiceType.GOOGLEMAPS: ApiValidationResult(
            service=ServiceType.GOOGLEMAPS,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.UNHEALTHY,
            latency_ms=510.0,
            message="Service unavailable",
            checked_at=datetime.now(UTC),
            validated_at=None,
        ),
        ServiceType.EMAIL: ApiValidationResult(
            service=ServiceType.EMAIL,
            is_valid=None,
            status=None,
            health_status=ServiceHealthStatus.UNKNOWN,
            latency_ms=0.0,
            message="Health status unknown",
            checked_at=None,
            validated_at=None,
        ),
    }
    dashboard_service.api_key_service = api_key_service

    stack.enter_context(
        patch(
            "tripsage.api.routers.dashboard.DashboardService",
            return_value=dashboard_service,
        )
    )

    return stack, dashboard_service


def test_overview_and_services_flow(client: TestClient, principal: Principal) -> None:
    """Exercise overview and services endpoints together."""
    payload = _build_dashboard_payload()
    stack, service = _patch_dependencies(principal, payload)

    with stack:
        overview = client.get("/api/dashboard/overview")
        services = client.get("/api/dashboard/services")

    service.get_dashboard_data.assert_awaited()

    assert overview.status_code == 200
    assert services.status_code == 200

    overview_body = overview.json()
    assert overview_body["success_rate_24h"] == pytest.approx(
        payload.metrics.success_rate, rel=1e-6
    )

    services_body = services.json()
    assert len(services_body) == 4
    services_index = {item["service"]: item for item in services_body}

    assert services_index["openai"]["status"] == "healthy"
    assert services_index["weather"]["status"] == "degraded"
    assert services_index["googlemaps"]["status"] == "unhealthy"
    assert services_index["email"]["status"] == "unknown"
    assert services_index["email"]["last_check"] is None


def test_metrics_and_rate_limits(client: TestClient, principal: Principal) -> None:
    """Exercise metrics and rate limit endpoints."""
    payload = _build_dashboard_payload()
    stack, service = _patch_dependencies(principal, payload)

    with stack:
        metrics = client.get("/api/dashboard/metrics?time_range_hours=6")
        rate_limits = client.get("/api/dashboard/rate-limits")

    service.get_dashboard_data.assert_awaited()

    assert metrics.status_code == 200
    assert rate_limits.status_code == 200

    metrics_body = metrics.json()
    assert metrics_body["total_requests"] == payload.metrics.total_requests
    assert metrics_body["unique_users"] == len(payload.top_users)

    rate_limits_body = rate_limits.json()
    assert rate_limits_body[0]["limit"] == 200
