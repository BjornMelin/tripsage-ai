"""Integration tests for activities router with DI overrides."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage_core.types import JSONObject


class _DB:
    """Database stub for integration tests."""

    def __init__(self) -> None:
        """Initialize database stub."""
        self.rows: list[JSONObject] = []

    async def insert(self, *, table: str, data: JSONObject, user_id: str) -> None:
        """Insert data into database."""
        self.rows.append(data)

    async def select(
        self,
        *,
        table: str,
        columns: str,
        filters: dict[str, Any],
        user_id: str,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[JSONObject]:
        """Select data from database."""
        return [r for r in self.rows if r.get("user_id") == user_id]

    class _Client:
        """Client for database operations."""

        def __init__(self, svc: _DB) -> None:
            """Initialize client."""
            self._svc = svc
            self._ids: list[str] = []

        def table(self, _: str) -> _DB._Client:
            """Set table for operation."""
            return self

        def delete(self) -> _DB._Client:
            """Delete operation."""
            return self

        def eq(self, field: str, value: str) -> _DB._Client:
            """Add equality filter for delete operation."""
            if field == "id":
                self._ids.append(value)
            return self

        def execute(self) -> dict[str, Any]:
            """Execute deletion against in-memory store."""
            before = len(self._svc.rows)
            to_delete = set(self._ids)
            self._svc.rows = [r for r in self._svc.rows if r.get("id") not in to_delete]
            return {"deleted": before - len(self._svc.rows)}

    @property
    def client(self) -> _DB._Client:
        """Get client for database operations."""
        return _DB._Client(self)


class _TripSvc:
    """Trip service stub for integration tests."""

    async def get_trip(self, *, trip_id: str, user_id: str) -> Any:
        """Get trip."""
        return {"id": trip_id, "title": "T"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_activity_save_and_delete_404(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """Save activity ok; delete unknown returns 404."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance."""
        return principal

    def _provide_db() -> _DB:
        """Provide database stub."""
        return _DB()

    def _provide_trip() -> _TripSvc:
        """Provide trip service stub."""
        return _TripSvc()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_db] = _provide_db  # type: ignore[assignment]
    app.dependency_overrides[dep.get_trip_service] = _provide_trip  # type: ignore[assignment]

    client = async_client_factory(app)

    payload = {"activity_id": "a1", "trip_id": "t1", "notes": "n"}
    r = await client.post("/api/activities/save", json=payload)
    assert r.status_code == status.HTTP_200_OK

    r = await client.delete("/api/activities/saved/missing")
    assert r.status_code == status.HTTP_404_NOT_FOUND
