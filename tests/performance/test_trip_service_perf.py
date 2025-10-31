"""Performance smoke tests for TripService workflows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from tripsage_core.models.schemas_common.enums import TripType, TripVisibility
from tripsage_core.models.trip import Budget, BudgetBreakdown
from tripsage_core.services.business.trip_service import TripCreateRequest, TripService


class _TripDbStub:
    """Minimal async database stub for TripService performance checks."""

    def __init__(self, trip_payload: dict[str, Any]) -> None:
        self._trip_payload = trip_payload
        self.create_calls: list[dict[str, Any]] = []

    async def create_trip(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Record payload and return the prepared response."""
        self.create_calls.append(payload)
        return self._trip_payload

    async def get_trip_related_counts(self, _trip_id: str) -> dict[str, int]:
        """Return empty related counts for the trip."""
        return {"notes": 0, "attachments": 0, "collaborators": 0}

    async def get_trip_collaborators(self, _trip_id: str) -> list[dict[str, str]]:
        """Return an empty collaborator list."""
        return []


@pytest.mark.performance
@pytest.mark.perf
@pytest.mark.timeout(0.5)
@pytest.mark.asyncio
async def test_trip_creation_latency_with_stubbed_dependencies() -> None:
    """Trip creation should complete within the 300ms latency budget."""
    now = datetime.now(UTC)
    user_id = str(uuid4())
    trip_id = str(uuid4())
    budget = Budget(
        total=1200.0,
        spent=0.0,
        currency="USD",
        breakdown=BudgetBreakdown(
            accommodation=400.0,
            transportation=300.0,
            food=200.0,
            activities=200.0,
            miscellaneous=100.0,
        ),
    )
    trip_payload = {
        "id": trip_id,
        "user_id": user_id,
        "title": "Perf Trip",
        "description": "Latency measurement",
        "start_date": now,
        "end_date": now + timedelta(days=3),
        "destination": "Lisbon",
        "destinations": [],
        "budget_breakdown": budget.model_dump(),
        "travelers": 2,
        "trip_type": "leisure",
        "status": "planning",
        "visibility": "private",
        "tags": ["perf"],
        "preferences_extended": {},
        "created_at": now,
        "updated_at": now,
    }
    db_stub = _TripDbStub(trip_payload)
    service = TripService(database_service=cast(Any, db_stub))

    request_data = {
        "title": "Perf Trip",
        "description": "Latency measurement",
        "start_date": now,
        "end_date": now + timedelta(days=3),
        "destination": "Lisbon",
        "budget": budget.model_dump(),
        "travelers": 2,
        "trip_type": TripType.LEISURE,
        "visibility": TripVisibility.PRIVATE,
        "tags": ["perf"],
    }
    request = TripCreateRequest.model_validate(request_data)

    start = datetime.now(UTC)
    response = await service.create_trip(user_id, request)
    elapsed = (datetime.now(UTC) - start).total_seconds()

    assert response.id == UUID(trip_id)
    assert elapsed < 0.3
