"""Integration tests for memory preference endpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


class _MemSvc:
    """Memory service stub for preference and search endpoints."""

    async def add_user_preference(
        self, user_id: str, key: str, value: str, category: str
    ) -> dict[str, object]:
        """Add user preference."""
        return {
            "ok": True,
            "user_id": user_id,
            "key": key,
            "value": value,
            "category": category,
        }

    async def search_memories(self, user_id: str, req: Any) -> list[dict[str, object]]:
        """Search memories."""
        raise RuntimeError("search failed")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_preference_and_search_error(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """POST /preference succeeds; POST /search error bubbles to 500."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    def _provide_memsvc() -> _MemSvc:
        """Provide memory service stub for DI."""
        return _MemSvc()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_memory_service] = _provide_memsvc  # type: ignore[assignment]

    client = async_client_factory(app)

    # preference uses query params
    r = await client.post(
        "/api/memory/preference",
        params={"key": "lang", "value": "en", "category": "general"},
    )
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body.get("ok") is True and body.get("user_id") == principal.id

    # search error path
    r = await client.post("/api/memory/search", json={"query": "hotel", "limit": 5})
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
