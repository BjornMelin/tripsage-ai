"""Unit tests for health router."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from tripsage.api.core import dependencies as core_dependencies
from tripsage.api.main import app


@pytest.fixture
async def async_client():
    """Return async HTTP client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _dependency_context(
    *,
    db: AsyncMock | None = None,
    cache: AsyncMock | None = None,
    settings: Mock | None = None,
) -> tuple[ExitStack, AsyncMock, AsyncMock]:
    """Set up dependency overrides for health endpoints."""
    mock_settings = settings or Mock()
    mock_settings.environment = getattr(mock_settings, "environment", "test")

    mock_db = db or AsyncMock()
    mock_db.execute_sql.return_value = [{"health_check": 1}]
    mock_db.get_pool_stats.return_value = {
        "pool_size": 10,
        "checked_out": 2,
        "overflow": 0,
    }

    mock_cache = cache or AsyncMock()
    mock_cache.ping.return_value = True
    mock_cache.info.return_value = {
        "used_memory_human": "1.2M",
        "connected_clients": "1",
        "total_commands_processed": "500",
    }

    stack = ExitStack()
    stack.enter_context(
        patch(
            "tripsage.api.core.dependencies.get_settings_dependency",
            return_value=mock_settings,
        )
    )

    async def db_override() -> AsyncMock:
        return mock_db

    async def cache_override() -> AsyncMock:
        return mock_cache

    app.dependency_overrides[core_dependencies.get_db] = db_override
    stack.callback(app.dependency_overrides.pop, core_dependencies.get_db, None)

    app.dependency_overrides[core_dependencies.get_cache_service_dep] = cache_override
    stack.callback(
        app.dependency_overrides.pop, core_dependencies.get_cache_service_dep, None
    )

    return stack, mock_db, mock_cache


@pytest.mark.anyio
async def test_comprehensive_health_check(async_client: AsyncClient):
    """Health endpoint returns component statuses."""
    stack, _, _ = _dependency_context()
    with stack:
        response = await async_client.get("/api/health")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()

    assert payload["status"] == "healthy"
    assert payload["environment"] == "test"
    assert len(payload["components"]) == 3

    for component in payload["components"]:
        assert component["status"] in {"healthy", "degraded", "unhealthy"}


@pytest.mark.anyio
async def test_readiness_health_returns_checks(async_client: AsyncClient):
    """Readiness endpoint reports dependency checks."""
    stack, _, _ = _dependency_context()
    with stack:
        response = await async_client.get("/api/health/readiness")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["ready"] is True
    assert payload["checks"]["database"] is True
    assert payload["checks"]["cache"] is True


@pytest.mark.anyio
async def test_cache_health_details(async_client: AsyncClient):
    """Cache health endpoint surfaces cache metrics."""
    stack, _, _ = _dependency_context()
    with stack:
        response = await async_client.get("/api/health/cache")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["details"]["used_memory"] == "1.2M"


@pytest.mark.anyio
async def test_database_health_handles_failures(async_client: AsyncClient):
    """Database health gracefully reports errors."""
    mock_settings = Mock()
    mock_settings.environment = "test"

    failing_db = AsyncMock()
    failing_db.execute_sql.side_effect = RuntimeError("connection lost")
    stack, _, _ = _dependency_context(db=failing_db, settings=mock_settings)
    with stack:
        response = await async_client.get("/api/health/database")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["status"] == "unhealthy"
    assert "connection lost" in payload["message"]
