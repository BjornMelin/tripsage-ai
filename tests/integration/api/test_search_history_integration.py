"""Integration tests for search history endpoints (recent/save) with DB stub."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


class _DB:
    """Database stub for integration tests."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    # pylint: disable=too-many-positional-arguments
    async def select(
        self,
        table: str,
        columns: str,
        filters: dict[str, Any],
        limit: int | None = None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent searches for a user, honoring the optional limit.

        Signature mirrors the production DatabaseService to keep DI simple.
        """
        uid = filters.get("user_id")
        return [r for r in self.rows if r.get("user_id") == uid][: (limit or 20)]

    async def insert(self, table: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Insert a row and return it wrapped in a list (Supabase-like)."""
        self.rows.append(data)
        return [data]

    async def delete(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Delete a row by ``id`` and ``user_id``; return affected IDs list."""
        uid = filters.get("user_id")
        sid = filters.get("id")
        before = len(self.rows)

        def _keep(r: dict[str, Any]) -> bool:
            """Keep row if it doesn't match the delete filters."""
            return not (r.get("id") == sid and r.get("user_id") == uid)

        self.rows = [r for r in self.rows if _keep(r)]
        if len(self.rows) < before:
            return [{"id": sid}]
        return []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_save_and_recent(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """Saving a search then fetching recent returns the saved entry."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    db = _DB()
    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]

    def _provide_db() -> _DB:
        """Provide database stub for DI."""
        return db

    app.dependency_overrides[dep.get_db] = _provide_db  # type: ignore[assignment]

    client = async_client_factory(app)

    # Save a search
    payload: dict[str, Any] = {
        "query": "paris",
        "resource_types": ["destination"],
        "filters": {},
    }
    r = await client.post("/save", json=payload)
    assert r.status_code == status.HTTP_200_OK
    saved_id = r.json()["id"]
    assert saved_id

    # Recent should include the saved search
    r = await client.get("/recent?limit=5")
    assert r.status_code == status.HTTP_200_OK
    arr: list[dict[str, Any]] = r.json()
    assert isinstance(arr, list) and any((it.get("id") == saved_id) for it in arr)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_recent_db_failure(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """DB failure on recent translates to a 500 error."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    class _DBFail(_DB):
        async def select(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            """Simulate a DB outage by raising an OSError."""
            raise OSError("db down")

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]

    def _provide_db_fail() -> _DB:
        """Provide database stub for DI."""
        return _DBFail()

    app.dependency_overrides[dep.get_db] = _provide_db_fail  # type: ignore[assignment]

    client = async_client_factory(app)
    r = await client.get("/recent")
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
