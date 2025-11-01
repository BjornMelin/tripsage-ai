"""Unit tests for memory router with DI overrides."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any as _Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_context(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: _Any,
):
    """`GET /api/memory/context` returns a basic context payload."""
    from tripsage.api.core import dependencies as dep
    from tripsage_core.services.business.memory_service import UserContextResponse

    # Provide principal via require_principal override
    def _provide_principal() -> _Any:
        """Provide principal instance for DI."""
        return principal

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]

    class _MemorySvc:
        """Memory service stub."""

        async def get_user_context(self, user_id: str) -> UserContextResponse:
            """Return minimal context for user."""
            return UserContextResponse(
                preferences=[{"currency": "USD"}],
                past_trips=[],
                saved_destinations=[],
                budget_patterns=[],
                travel_style=[],
                dietary_restrictions=[],
                accommodation_preferences=[],
                activity_preferences=[],
                insights={"user_id": user_id},
                summary="",
            )

    def _provide_memory_service() -> _Any:
        """Provide memory service stub."""
        return _MemorySvc()

    app.dependency_overrides[dep.get_memory_service] = _provide_memory_service  # type: ignore[assignment]

    client = async_client_factory(app)
    resp = await client.get("/api/memory/context")
    assert resp.status_code == 200
    data = resp.json()
    assert data["insights"]["user_id"] == principal.id
    assert data["preferences"][0]["currency"] == "USD"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_update_preferences(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: _Any,
):
    """`PUT /api/memory/preferences` updates preferences via service."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal2() -> _Any:
        """Provide principal instance for DI (preferences test)."""
        return principal

    app.dependency_overrides[dep.require_principal] = _provide_principal2  # type: ignore[assignment]

    class _MemorySvc:
        """Memory service class."""

        async def update_user_preferences(self, user_id: str, prefs: dict[str, _Any]):
            """Update user preferences."""
            assert user_id == principal.id
            assert prefs["lang"] == "en"
            return {"ok": True, "preferences": prefs}

    def _provide_memory_service2() -> _Any:
        """Provide memory service stub (preferences test)."""
        return _MemorySvc()

    app.dependency_overrides[dep.get_memory_service] = _provide_memory_service2  # type: ignore[assignment]

    client = async_client_factory(app)
    resp = await client.put(
        "/api/memory/preferences", json={"preferences": {"lang": "en"}}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
