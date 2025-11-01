"""Integration tests for search analytics and bulk search endpoints.

Covers:
- GET /analytics with cache-stored analytics list filtered by user
- POST /bulk happy path and over-limit (400) error path
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage.api.schemas.search import (
    SearchMetadata,
    UnifiedSearchAggregateResponse,
    UnifiedSearchRequest,
)


class _Cache:
    """In-memory cache stub for analytics and search caching."""

    def __init__(self) -> None:
        """Initialize in-memory cache stub."""
        self.store: dict[str, Any] = {}

    async def get_json(self, key: str, default: Any | None = None) -> Any:
        """Get JSON from cache."""
        return self.store.get(key, default)

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set JSON in cache."""
        self.store[key] = value


class _SearchService:
    """Unified search service stub for bulk endpoint."""

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
                search_time_ms=3,
                search_id="sid-bulk",
                user_id=None,
            ),
            related_searches=[f"{req.query} tips"],
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_analytics_happy(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
) -> None:
    """Analytics aggregates per-user entries and returns summary."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    cache = _Cache()

    # Seed analytics for date key with mixed users
    date = "2025-01-01"
    key = f"analytics:search:{date}"
    cache.store[key] = [
        {
            "user_id": principal.id,
            "query": "paris",
            "cache_status": "cache_hit",
            "timestamp": datetime.now(UTC).isoformat(),
        },
        {
            "user_id": principal.id,
            "query": "rome",
            "cache_status": "cache_miss",
            "timestamp": datetime.now(UTC).isoformat(),
        },
        {
            "user_id": "other",
            "query": "london",
            "cache_status": "cache_hit",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    ]

    def _provide_cache() -> _Cache:
        """Provide cache service stub for DI."""
        return cache

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_cache_service_dep] = _provide_cache  # type: ignore[assignment]

    client = async_client_factory(app)
    r = await client.get("/analytics", params={"date": date})
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["total_searches"] == 2
    assert body["cache_hits"] == 1 and body["cache_misses"] == 1
    assert any(p["query"] == "paris" for p in body["popular_queries"])  # type: ignore[index]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_analytics_cache_failure(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
) -> None:
    """Cache error surfaces as 500 according to router error handling."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    class _BrokenCache(_Cache):
        """Broken cache service stub for DI."""

        async def get_json(self, key: str, default: Any | None = None) -> Any:
            """Simulate a cache outage by raising an OSError."""
            raise OSError("cache down")

    def _provide_cache() -> _BrokenCache:
        """Provide broken cache service stub for DI."""
        return _BrokenCache()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_cache_service_dep] = _provide_cache  # type: ignore[assignment]

    client = async_client_factory(app)
    r = await client.get("/analytics", params={"date": "2025-01-02"})
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bulk_search_happy_and_over_limit(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """Bulk search returns list for ≤10 items; 400 when >10 requests."""
    from tripsage.api.core import dependencies as dep

    def _provide_service() -> _SearchService:
        """Provide search service stub for DI."""
        return _SearchService()

    cache = _Cache()

    def _provide_cache() -> _Cache:
        """Provide cache service stub for DI."""
        return cache

    app.dependency_overrides[dep.get_unified_search_service_dep] = _provide_service  # type: ignore[assignment]
    app.dependency_overrides[dep.get_cache_service_dep] = _provide_cache  # type: ignore[assignment]

    client = async_client_factory(app)
    # Happy: two requests
    body: list[dict[str, Any]] = [
        {"query": "paris", "types": ["destinations"]},
        {"query": "rome", "types": ["destinations"]},
    ]
    r = await client.post("/bulk", json=body)
    assert r.status_code == status.HTTP_200_OK
    arr: list[dict[str, Any]] = r.json()
    assert isinstance(arr, list) and len(arr) == 2

    # Error: 11 requests → 400
    too_many = [{"query": f"q{i}", "types": ["destinations"]} for i in range(11)]
    r = await client.post("/bulk", json=too_many)
    assert r.status_code == status.HTTP_400_BAD_REQUEST
