"""Integration-ish tests for dashboard router with stubbed service.

We monkeypatch the DashboardService used by the router to a deterministic fake
and override the auth dependency that pulls Principal from request.state.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage.api.routers import dashboard as dashboard_router
from tripsage_core.services.business.dashboard_service import ServiceHealthStatus


class _FakeApiKeyService:
    async def check_all_services_health(self) -> dict[Any, Any]:
        """Check all services health."""

        class _Health:
            """Health check."""

            def __init__(self) -> None:
                """Initialize health check."""
                self.status = ServiceHealthStatus.HEALTHY
                self.latency_ms = 120.0
                self.checked_at = datetime.now(UTC)
                self.message = "ok"
                self.details = {"error_rate": 0.01, "uptime_percentage": 99.9}

        # keys are enum members in real impl; dict iteration uses .value in router
        return {type("T", (), {"value": "openai"})(): _Health()}


class _FakeDashboardService:
    """Fake dashboard service."""

    def __init__(
        self,
        cache_service: Any | None = None,
        database_service: Any | None = None,
        settings: Any | None = None,
    ) -> None:
        """Initialize dashboard service."""
        self.cache = cache_service
        self.db = database_service
        self.api_key_service = (
            _FakeApiKeyService() if database_service is not None else None
        )

    async def get_dashboard_data(
        self, time_range_hours: int = 24, top_users_limit: int = 10
    ) -> Any:
        """Get dashboard data."""
        now = datetime.now(UTC)
        metrics = type(
            "M",
            (),
            {
                "total_requests": 1000,
                "total_errors": 50,
                "success_rate": 0.95,
                "active_keys_count": 3,
            },
        )()

        # Use dict subclass with attribute access for top_users so the router
        # can access fields via attributes (e.g., user.user_id) while the
        # response remains JSON-serializable for analytics summary.
        class _UserDict(dict[str, Any]):
            """User dictionary."""

            def __getattr__(self, item: str) -> Any:
                """Get attribute."""
                return self[item]

        top_users = [
            _UserDict(
                user_id="u1",
                request_count=20,
                error_count=1,
                success_rate=0.95,
                last_activity=now,
                services_used=["chat"],
                avg_latency_ms=120.0,
            ),
            _UserDict(
                user_id="u2",
                request_count=15,
                error_count=0,
                success_rate=0.98,
                last_activity=now - timedelta(hours=2),
                services_used=["vision"],
                avg_latency_ms=110.0,
            ),
        ]

        services = [
            type(
                "S",
                (),
                {
                    "service_name": "openai",
                    "health_status": ServiceHealthStatus.HEALTHY,
                    "total_requests": 600,
                },
            )()
        ]

        alerts = []
        trend = [
            {
                "timestamp": now - timedelta(hours=1),
                "requests": 100,
                "errors": 5,
                "success_rate": 0.95,
            }
        ]
        return type(
            "D",
            (),
            {
                "metrics": metrics,
                "services": services,
                "top_users": top_users,
                "recent_alerts": alerts,
                "usage_trend": trend,
                "cache_stats": {},
            },
        )()

    async def get_rate_limit_status(
        self, key_id: str, window_minutes: int = 60
    ) -> dict[str, Any]:
        """Get rate limit status."""
        now = datetime.now(UTC)
        return {
            "requests_in_window": 42,
            "limit": 100,
            "remaining": 58,
            "reset_at": (now + timedelta(minutes=10)).isoformat(),
        }

    async def _get_usage_trends(self, time_range_hours: int) -> list[dict[str, Any]]:
        """Return simple hourly usage trend data for the given period."""
        now = datetime.now(UTC)
        return [
            {
                "timestamp": (now - timedelta(hours=h)).isoformat(),
                "requests": 100 + h,
                "errors": 5,
                "success_rate": 0.95,
            }
            for h in range(time_range_hours, 0, -1)
        ]

    async def _get_recent_alerts(self):
        """Get recent alerts."""
        now = datetime.now(UTC)

        @dataclass
        class _EnumVal:
            """Enum value."""

            value: str

        @dataclass
        class _Alert:  # pylint: disable=too-many-instance-attributes
            """Alert."""

            alert_id: str
            alert_type: _EnumVal
            severity: _EnumVal
            message: str
            created_at: datetime
            api_key_id: str
            service: str
            acknowledged: bool
            details: dict[str, Any]

        a1 = _Alert(
            alert_id="a1",
            alert_type=_EnumVal("perf"),
            severity=_EnumVal("high"),
            message="hi",
            created_at=now,
            api_key_id="k1",
            service="openai",
            acknowledged=False,
            details={},
        )
        a2 = _Alert(
            alert_id="a2",
            alert_type=_EnumVal("security"),
            severity=_EnumVal("low"),
            message="lo",
            created_at=now,
            api_key_id="k2",
            service="maps",
            acknowledged=True,
            details={},
        )
        return [a1, a2]

    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge alert."""
        return alert_id == "a1"

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve alert."""
        return alert_id == "a1"


def _override_principal_and_service(
    app: FastAPI, principal: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tripsage.api.core import dependencies as deps

    # Settings/Cache/DB can be simple objects
    class _Settings:
        environment = "testing"

    def _provide_settings() -> _Settings:
        return _Settings()

    def _provide_cache() -> object:
        return object()

    def _provide_db() -> object:
        return object()

    app.dependency_overrides[deps.get_settings_dependency] = _provide_settings
    app.dependency_overrides[deps.get_cache_service_dep] = _provide_cache
    app.dependency_overrides[deps.get_db] = _provide_db

    # Principal injection (router-level helper)
    def _provide_principal() -> object:
        return principal

    app.dependency_overrides[dashboard_router.get_current_principal] = (
        _provide_principal
    )

    # Replace service type
    monkeypatch.setattr(dashboard_router, "DashboardService", _FakeDashboardService)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_overview_services_and_metrics(
    principal: Any,
    async_client_factory: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate overview, services list, and metrics responses."""
    app = FastAPI()
    app.include_router(dashboard_router.router, prefix="/api")
    _override_principal_and_service(app, principal, monkeypatch)

    cf = cast(Callable[[FastAPI], AsyncClient], async_client_factory)
    async with cf(app) as client:
        r = await client.get("/api/dashboard/overview")
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["status"] == "healthy"

        r = await client.get("/api/dashboard/services")
        assert r.status_code == status.HTTP_200_OK
        # api_key_service set when db provided; our override supplies an object()
        assert isinstance(r.json(), list)

        r = await client.get("/api/dashboard/metrics?time_range_hours=2")
        assert r.status_code == status.HTTP_200_OK
        assert r.json()["total_requests"] == 1000


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limits_alerts_ack_dismiss_and_activity(
    principal: Any,
    async_client_factory: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover rate-limits, alerts, acknowledge/dismiss, activity, trends, summary."""
    app = FastAPI()
    app.include_router(dashboard_router.router, prefix="/api")
    _override_principal_and_service(app, principal, monkeypatch)

    cf = cast(Callable[[FastAPI], AsyncClient], async_client_factory)
    async with cf(app) as client:
        # rate limits derive keys from top_users
        r = await client.get("/api/dashboard/rate-limits?limit=3")
        assert r.status_code == status.HTTP_200_OK
        assert len(r.json()) >= 1

        # alerts filtering by severity
        r = await client.get("/api/dashboard/alerts?severity=high")
        assert r.status_code == status.HTTP_200_OK
        items = r.json()
        assert all(it["severity"] == "high" for it in items)

        # acknowledge success
        r = await client.post("/api/dashboard/alerts/a1/acknowledge")
        assert r.status_code == status.HTTP_200_OK and r.json()["success"] is True

        # acknowledge unknown -> 404
        r = await client.post("/api/dashboard/alerts/zzz/acknowledge")
        assert r.status_code == status.HTTP_404_NOT_FOUND

        # dismiss success then unknown
        r = await client.delete("/api/dashboard/alerts/a1")
        assert r.status_code == status.HTTP_200_OK and r.json()["success"] is True
        r = await client.delete("/api/dashboard/alerts/zzz")
        assert r.status_code == status.HTTP_404_NOT_FOUND

        # users activity
        r = await client.get("/api/dashboard/users/activity?time_range_hours=2&limit=2")
        assert r.status_code == status.HTTP_200_OK
        assert len(r.json()) == 2

        # trends and analytics summary
        r = await client.get(
            "/api/dashboard/trends/request_count?time_range_hours=1&interval_minutes=60"
        )
        assert r.status_code == status.HTTP_200_OK
        assert len(r.json()) >= 1

        r = await client.get("/api/dashboard/analytics/summary?time_range_hours=2")
        assert r.status_code == status.HTTP_200_OK
        assert "performance" in r.json() and "services" in r.json()
