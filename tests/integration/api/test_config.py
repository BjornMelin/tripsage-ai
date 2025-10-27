"""Integration tests for configuration endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tripsage.api.core.dependencies import require_principal


@pytest.mark.asyncio
async def test_list_agent_types(async_client: AsyncClient) -> None:
    """GET /config/agents should return the canonical agent identifiers."""
    response = await async_client.get("/api/config/agents")

    assert response.status_code == 200
    payload: list[str] = response.json()
    assert "budget_agent" in payload
    assert "itinerary_agent" in payload


@pytest.mark.asyncio
async def test_get_agent_config_valid(async_client: AsyncClient) -> None:
    """GET /config/agents/{agent_type} should surface the default config."""
    response = await async_client.get("/api/config/agents/budget_agent")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["agent_type"] == "budget_agent"
    assert data["model"]


@pytest.mark.asyncio
async def test_update_agent_config_overrides_fields(
    async_client: AsyncClient, app: FastAPI
) -> None:
    """PUT /config/agents/{agent_type} should merge provided updates."""

    async def _principal_override():
        class _P:
            id = "user-123"
        return _P()  # minimal object with id

    app.dependency_overrides[require_principal] = _principal_override
    try:
        payload = {"temperature": 0.42, "model": "gpt-4o-mini"}
        response = await async_client.put(
            "/api/config/agents/budget_agent",
            json=payload,
        )
    finally:
        app.dependency_overrides.pop(require_principal, None)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert abs(data["temperature"] - 0.42) < 1e-9
    assert data["model"] == "gpt-4o-mini"
    assert data["updated_by"] == "user-123"
