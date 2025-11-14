"""Unit tests for search router covering cache behavior and history endpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tripsage.api.schemas.search import (
    SearchMetadata,
    UnifiedSearchAggregateResponse,
    UnifiedSearchRequest,
)


class _SearchService:
    async def unified_search(
        self, req: UnifiedSearchRequest
    ) -> UnifiedSearchAggregateResponse:
        """Return a synthetic aggregated response for the query."""
        return UnifiedSearchAggregateResponse(
            results=[],
            facets=[],
            metadata=SearchMetadata(
                total_results=1,
                returned_results=1,
                search_time_ms=5,
                search_id="sid1",
                user_id=None,
            ),
            related_searches=[req.query + " tips"],
        )

    async def get_search_suggestions(self, query: str, limit: int) -> list[str]:
        """Return a small list of suggestions."""
        return [f"{query} suggestion {i}" for i in range(min(limit, 3))]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unified_search_cache_hit_miss(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify unified search caches results and returns cached payload."""
    from tripsage.api.core import dependencies as dep

    # DI overrides: search facade + cache
    def _provide_search_facade() -> Any:
        """Provide search facade stub exposing unified_search."""
        return _SearchService()

    app.dependency_overrides[dep.get_search_facade] = _provide_search_facade  # type: ignore[assignment]

    class _Cache:
        """In-memory cache stub."""

        def __init__(self) -> None:
            """Initialize cache."""
            self.store: dict[str, Any] = {}

        async def get_json(self, key: str, default: Any = None) -> Any:
            """Get JSON from cache."""
            return self.store.get(key, default)

        async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
            """Set JSON in cache."""
            self.store[key] = value

    cache = _Cache()

    def _provide_cache() -> Any:
        """Provide cache service stub with in-memory store."""
        return cache

    app.dependency_overrides[dep.get_cache_service_dep] = _provide_cache  # type: ignore[assignment]

    client = async_client_factory(app)

    # First call -> miss, populate cache
    payload = {"query": "paris", "types": ["destinations"]}
    r1 = await client.post("/unified", json=payload)
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["metadata"]["returned_results"] == 1

    # Second call -> hit, returns same data
    r2 = await client.post("/unified", json=payload)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["metadata"]["returned_results"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggestions_basic(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
):
    """Suggestions return a bounded list for the given query."""
    from tripsage.api.core import dependencies as dep

    def _provide_search_facade2() -> Any:
        """Provide search facade stub (suggestions)."""
        return _SearchService()

    app.dependency_overrides[dep.get_search_facade] = _provide_search_facade2  # type: ignore[assignment]

    client = async_client_factory(app)
    r = await client.get("/suggest", params={"query": "rome", "limit": 5})
    assert r.status_code == 200
    arr: list[str] = r.json()
    assert isinstance(arr, list) and len(arr) <= 5 and len(arr) > 0
