"""End-to-end flow tests for agent configuration endpoints."""

from __future__ import annotations

import pytest

from tripsage.api.core import auth


@pytest.fixture
def config_overrides(app):
    """Stub authentication to simplify configuration flows."""
    app.dependency_overrides[auth.get_current_user_id] = lambda: "user-123"
    yield
    app.dependency_overrides.pop(auth.get_current_user_id, None)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_update_agent_configuration(async_client, config_overrides):
    """Verify that agent configurations can be listed and updated end-to-end."""
    list_response = await async_client.get("/api/config/agents")
    assert list_response.status_code == 200
    body = list_response.json()
    assert "budget_agent" in body

    payload = {"max_tokens": 1500, "temperature": 0.2}
    update_response = await async_client.put(
        "/api/config/agents/budget_agent",
        json=payload,
    )
    assert update_response.status_code == 200

    updated = update_response.json()
    assert updated["max_tokens"] == 1500
    assert updated["temperature"] == pytest.approx(0.2)
    assert updated["updated_by"] == "user-123"
