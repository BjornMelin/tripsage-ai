"""Unit tests for configuration router (admin-only endpoints)."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


def _build_app_admin() -> FastAPI:
    """Build app and apply overrides."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "config_router_module", "tripsage/api/routers/config.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(module.router, prefix="/api")

    from tripsage.api.core import dependencies as dep

    class _Admin:
        """Admin principal stub."""

        id = "admin-user-1"
        type = "user"
        auth_method = "jwt"
        scopes: ClassVar[list[str]] = ["admin"]
        metadata: ClassVar[dict[str, list[str]]] = {"roles": ["admin"]}

    def _provide_admin() -> object:
        """Provide admin principal for DI."""
        return _Admin()

    app.dependency_overrides[dep.require_admin_principal] = _provide_admin  # type: ignore[assignment]
    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agents_list_get_put_and_rollback(
    async_client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    """Exercise list/get/update/rollback admin endpoints."""
    app = _build_app_admin()
    client = async_client_factory(app)

    # List agents
    r = await client.get("/api/config/agents")
    assert r.status_code == status.HTTP_200_OK
    agents = r.json()
    assert "budget_agent" in agents

    # Get config exists
    r = await client.get("/api/config/agents/budget_agent")
    assert r.status_code == status.HTTP_200_OK
    cfg = r.json()
    assert cfg["agent_type"] == "budget_agent" and "temperature" in cfg

    # Get missing -> 404
    r = await client.get("/api/config/agents/unknown_agent")
    assert r.status_code == status.HTTP_404_NOT_FOUND

    # Update agent config
    payload = {"temperature": 0.2, "max_tokens": 1500}
    r = await client.put("/api/config/agents/budget_agent", json=payload)
    assert r.status_code == status.HTTP_200_OK
    upd = r.json()
    assert upd["temperature"] == 0.2 and upd["max_tokens"] == 1500

    # Rollback (placeholder implementation returns 200 JSON)
    r = await client.post("/api/config/agents/budget_agent/rollback/v1")
    assert r.status_code == status.HTTP_200_OK
    msg = r.json()
    assert msg["agent_type"] == "budget_agent" and msg["version_id"] == "v1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_environment_summary(
    async_client_factory: Callable[[FastAPI], AsyncClient],
) -> None:
    """`GET /api/config/environment` returns environment summary."""
    app = _build_app_admin()
    client = async_client_factory(app)

    r = await client.get("/api/config/environment")
    assert r.status_code == status.HTTP_200_OK
    env = r.json()
    assert "environment" in env and "global_defaults" in env
