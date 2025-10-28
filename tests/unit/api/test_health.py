"""Unit-level health endpoint checks using minimal app client."""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_ok(async_client: AsyncClient):
    """Health endpoint returns a valid status."""
    resp = await async_client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") in {"healthy", "degraded", "unhealthy"}
