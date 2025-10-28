"""Unit tests for activities router endpoints using DI overrides.

Covers save/list/delete flows with a DatabaseService-like stub and a minimal
TripService stub for access checks. Uses the per-router mini-app pattern to
avoid heavy DI container wiring and keep tests fast and deterministic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypedDict

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


class _SavedItem(TypedDict):
    """Typed shape for saved itinerary item rows (required keys)."""

    id: str
    trip_id: str | None
    user_id: str
    title: str
    description: str | None
    item_type: str
    external_id: str
    metadata: dict[str, Any]
    created_at: str
    booking_status: str


def _saved_items_factory() -> list[_SavedItem]:
    """Typed factory for saved items list to satisfy type checkers."""
    return []


@dataclass
class _FakeDBService:
    """In-memory DatabaseService stub with chainable client.delete path."""

    rows: list[_SavedItem] = field(default_factory=_saved_items_factory)

    # Simple insert/select API mirroring DatabaseService
    async def insert(self, *, table: str, data: _SavedItem, user_id: str) -> None:
        """Insert a row into the database."""
        assert table == "itinerary_items"
        assert data["user_id"] == user_id
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
    ) -> list[_SavedItem]:
        """Select rows from the database."""
        assert table == "itinerary_items"
        _ = columns

        # Basic filter on user_id and optional equality criteria
        def _matches(row: _SavedItem) -> bool:
            """Check if row matches filters and user_id."""
            for k, v in filters.items():
                if k not in row:
                    continue
                if row[k] != v:  # type: ignore[index]
                    return False
            return row.get("user_id") == user_id

        candidates = [r for r in self.rows if _matches(r)]
        # order_by is optional; we keep simple for unit test purposes
        if limit is not None or offset is not None:
            start = offset or 0
            end = None if limit is None else start + limit
            candidates = candidates[start:end]
        return candidates

    # Minimal chainable client used by delete_saved_activity
    class _Client:
        """Chainable client for delete operations."""

        def __init__(self, svc: _FakeDBService) -> None:
            """Initialize client with service reference."""
            self._svc = svc
            self._to_delete_ids: list[str] = []

        def table(self, table: str) -> _FakeDBService._Client:
            """Set table for operation chaining."""
            assert table == "itinerary_items"
            return self

        def delete(self) -> _FakeDBService._Client:
            """Mark operation as delete for chaining."""
            return self

        def eq(self, field: str, value: str) -> _FakeDBService._Client:
            """Add equality filter for delete operation."""
            # The router deletes by primary key id
            if field == "id":
                self._to_delete_ids.append(value)
            return self

        def execute(self) -> dict[str, Any]:  # synchronous in router
            """Execute delete operation and return result."""
            before = len(self._svc.rows)
            self._svc.rows = [
                r for r in self._svc.rows if r.get("id") not in set(self._to_delete_ids)
            ]
            deleted = before - len(self._svc.rows)
            return {"deleted": deleted}

    @property
    def client(self) -> _FakeDBService._Client:
        """Get chainable client for delete operations."""
        return _FakeDBService._Client(self)


@dataclass
class _FakeTrip:
    """Fake trip data structure for testing."""

    id: str
    title: str


class _FakeTripService:
    """Minimal TripService stub for access checks."""

    def __init__(self) -> None:
        """Initialize with known trip IDs."""
        self._known: set[str] = {"trip-1"}

    async def get_trip(self, *, trip_id: str, user_id: str) -> _FakeTrip | None:
        """Return fake trip if ID is known."""
        return _FakeTrip(id=trip_id, title="Trip") if trip_id in self._known else None


def _build_app_and_overrides(
    principal: Any, db: _FakeDBService, trip_svc: _FakeTripService
) -> FastAPI:
    """Build app and apply overrides."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "activities_router_module", "tripsage/api/routers/activities.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(module.router, prefix="/api/activities")

    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    def _provide_db() -> _FakeDBService:
        """Provide database stub for DI."""
        return db

    def _provide_trip_service() -> _FakeTripService:
        """Provide trip service stub for DI."""
        return trip_svc

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_db] = _provide_db  # type: ignore[assignment]
    app.dependency_overrides[dep.get_trip_service] = _provide_trip_service  # type: ignore[assignment]

    # Override activity service provider to avoid container lookups
    class _FakeActivityService:
        """Fake activity service to prevent container lookups."""

        async def search_activities(
            self, *_args: Any, **_kwargs: Any
        ) -> Any:  # pragma: no cover
            """Return empty activities list."""
            return {"activities": []}

        async def get_activity_details(
            self, *_args: Any, **_kwargs: Any
        ) -> Any:  # pragma: no cover
            """Return None for activity details."""
            return None

    app.dependency_overrides[dep.get_activity_service_dep] = _FakeActivityService  # type: ignore[assignment]

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_and_list_saved_activities(
    principal: Any, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """Test saving an activity persists an item and GET /saved lists it."""
    db = _FakeDBService()
    trip_svc = _FakeTripService()
    app = _build_app_and_overrides(principal, db, trip_svc)

    client = async_client_factory(app)
    # Save activity bound to a known trip
    payload = {"activity_id": "act-1", "trip_id": "trip-1", "notes": "n"}
    r = await client.post("/api/activities/save", json=payload)
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["activity_id"] == "act-1" and body["trip_id"] == "trip-1"

    # List saved activities returns our entry
    r = await client.get("/api/activities/saved")
    assert r.status_code == status.HTTP_200_OK
    rows: list[dict[str, Any]] = r.json()
    assert isinstance(rows, list) and any(row["activity_id"] == "act-1" for row in rows)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_saved_activity_success_and_not_found(
    principal: Any, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """Test deleting an existing saved activity returns 204; unknown id returns 404."""
    db = _FakeDBService()
    trip_svc = _FakeTripService()
    app = _build_app_and_overrides(principal, db, trip_svc)

    client = async_client_factory(app)

    # Pre-seed a saved item matching by external_id
    now = datetime.now(UTC).isoformat()
    db.rows.append(
        {
            "id": "row-1",
            "trip_id": "trip-1",
            "user_id": principal.id,
            "title": "Saved Activity: act-x",
            "description": None,
            "item_type": "activity",
            "external_id": "act-x",
            "metadata": {"activity_id": "act-x", "notes": None},
            "created_at": now,
            "booking_status": "planned",
        }
    )

    # Known id delete -> 204
    r = await client.delete("/api/activities/saved/act-x")
    assert r.status_code == status.HTTP_204_NO_CONTENT

    # Unknown id -> 404
    r = await client.delete("/api/activities/saved/act-missing")
    assert r.status_code == status.HTTP_404_NOT_FOUND
