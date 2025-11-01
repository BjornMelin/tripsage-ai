"""Integration smoke tests for health endpoints (unique module name)."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_smoke(async_client: AsyncClient):
    """Health endpoint returns component list and 200."""
    resp = await async_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert isinstance(data["components"], list)
