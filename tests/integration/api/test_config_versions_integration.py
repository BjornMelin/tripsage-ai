"""Integration tests for config versions and rollback invalid agent type."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


class _Admin:
    """Admin principal stub."""

    id = "admin-1"
    type = "user"
    auth_method = "jwt"
    scopes: ClassVar[list[str]] = ["admin"]
    metadata: ClassVar[dict[str, list[str]]] = {"roles": ["admin"]}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_config_versions_and_rollback_invalid(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """GET versions returns list; rollback invalid agent yields 404."""
    from tripsage.api.core import dependencies as dep

    def _provide_admin() -> Any:
        """Provide admin principal for DI."""
        return _Admin()

    app.dependency_overrides[dep.require_admin_principal] = _provide_admin  # type: ignore[assignment]

    client = async_client_factory(app)

    # Versions list for valid type
    r = await client.get("/api/config/agents/budget_agent/versions")
    assert r.status_code == status.HTTP_200_OK
    arr = r.json()
    assert isinstance(arr, list)

    # Rollback invalid agent type
    r = await client.post("/api/config/agents/unknown_agent/rollback/v1")
    assert r.status_code == status.HTTP_404_NOT_FOUND
