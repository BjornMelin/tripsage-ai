"""Integration tests for config router with admin principal override."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_config_agents_list(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """Verify agents list endpoint works under admin principal."""
    from tripsage.api.core import dependencies as dep

    class _Admin:
        """Admin principal stub for integration tests."""

        id = "admin-user-1"
        type = "user"
        auth_method = "jwt"
        scopes: ClassVar[list[str]] = ["admin"]
        metadata: ClassVar[dict[str, list[str]]] = {"roles": ["admin"]}

    def _provide_admin() -> Any:
        """Provide admin principal for DI."""
        return _Admin()

    app.dependency_overrides[dep.require_admin_principal] = _provide_admin  # type: ignore[assignment]

    client = async_client_factory(app)
    r = await client.get("/api/config/agents")
    assert r.status_code == status.HTTP_200_OK
    arr = r.json()
    assert isinstance(arr, list) and "budget_agent" in arr
