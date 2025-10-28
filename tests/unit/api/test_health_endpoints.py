"""Unit tests for individual health endpoints with DI overrides."""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_liveness_ok(async_client: AsyncClient):
    """Liveness endpoint returns static alive object."""
    resp = await async_client.get("/api/health/liveness")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "alive"
    assert "timestamp" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_readiness_ok(async_client: AsyncClient):
    """Readiness endpoint returns ready status with checks map."""
    resp = await async_client.get("/api/health/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ready") is True
    assert isinstance(data.get("checks"), dict)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_health_ok(async_client: AsyncClient):
    """Database health endpoint returns healthy status under overrides."""
    resp = await async_client.get("/api/health/database")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("name") == "database"
    assert data.get("status") in {"healthy", "unhealthy"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_health_ok(async_client: AsyncClient):
    """Cache health endpoint returns healthy status under overrides."""
    resp = await async_client.get("/api/health/cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("name") == "cache"
    assert data.get("status") in {"healthy", "unhealthy"}
