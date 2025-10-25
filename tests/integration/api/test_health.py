"""Integration tests for health endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tripsage.api.core import dependencies


class _StubDatabase:
    """Stubbed database service."""

    async def health_check(self) -> bool:  # pragma: no cover - trivial
        """Check database health."""
        return True


class _StubCache:
    """Stubbed cache service."""

    async def health_check(self) -> bool:  # pragma: no cover - trivial
        """Check cache health."""
        return True


@pytest.fixture
def health_overrides(app, test_settings):
    """Inject stubbed dependencies for health checks."""
    db = _StubDatabase()
    cache = _StubCache()

    async def _get_db() -> _StubDatabase:
        """Get stubbed database service."""
        return db

    async def _get_cache() -> _StubCache:
        """Get stubbed cache service."""
        return cache

    app.state.database_monitor = None  # type: ignore[attr-defined]
    app.state.cache_service = cache  # type: ignore[attr-defined]
    app.dependency_overrides[dependencies.get_db] = _get_db
    app.dependency_overrides[dependencies.get_cache_service_dep] = _get_cache
    app.dependency_overrides[dependencies.get_settings_dependency] = (
        lambda: test_settings
    )

    yield

    app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint_reports_components(app, health_overrides):
    """Ensure the health endpoint returns component status information."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "testing"
    component_names = {component["name"] for component in data["components"]}
    assert {"application", "database", "cache"}.issubset(component_names)
