"""Unit tests for :mod:`tripsage_core.services.business.trip_service`."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import pytest

from tripsage_core.models.trip import Budget, BudgetBreakdown
from tripsage_core.services.business.trip_service import (
    TripCreateRequest,
    TripLocation,
    TripService,
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService


class _TripDatabaseStub:
    """Minimal asynchronous database stub for :class:`TripService` tests."""

    def __init__(self, record: dict[str, Any], collaborators: list[dict[str, Any]]):
        """Initialize the database stub."""
        self.record = record
        self.collaborators = collaborators
        self.related_counts = {
            "notes": 2,
            "attachments": 1,
            "collaborators": len(collaborators),
        }
        self.created_payload: dict[str, Any] | None = None

    async def create_trip(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a trip record."""
        self.created_payload = payload
        return self.record

    async def get_trip_related_counts(self, trip_id: str) -> dict[str, int]:
        """Get the related counts for a trip."""
        return self.related_counts

    async def get_trip_collaborators(self, trip_id: str) -> list[dict[str, Any]]:
        """Get the collaborators for a trip."""
        return self.collaborators

    async def get_trip_by_id(self, trip_id: str) -> dict[str, Any] | None:
        """Get a trip by ID."""
        if trip_id == self.record["id"]:
            return self.record
        return None


def _trip_record(owner_id: str, request: TripCreateRequest) -> dict[str, Any]:
    """Construct a database record from a trip creation request."""
    now = datetime.now(UTC)
    return {
        "id": str(uuid4()),
        "user_id": owner_id,
        "title": request.title,
        "description": request.description,
        "start_date": request.start_date.date(),
        "end_date": request.end_date.date(),
        "destination": request.destination,
        "destinations": [dest.model_dump() for dest in request.destinations],
        "budget_breakdown": request.budget.model_dump(),
        "travelers": request.travelers,
        "trip_type": request.trip_type.value,
        "status": TripStatus.PLANNING.value,
        "visibility": request.visibility.value,
        "tags": request.tags,
        "preferences_extended": (
            request.preferences.model_dump() if request.preferences else {}
        ),
        "created_at": now,
        "updated_at": now,
    }


@pytest.mark.asyncio
async def test_create_trip_persists_dates_and_counts() -> None:
    """Trip creation should persist normalized dates and map related counts."""
    owner_id = str(uuid4())
    request = TripCreateRequest(
        title="Spring Getaway",
        description="A relaxing spring break",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=5),
        destination="Kyoto",
        destinations=[
            TripLocation(
                name="Kyoto",
                country="Japan",
                city="Kyoto",
                coordinates={"lat": 35.0116, "lng": 135.7681},
                timezone="Asia/Tokyo",
            )
        ],
        budget=Budget(
            total=1500.0,
            currency="USD",
            spent=200.0,
            breakdown=BudgetBreakdown(accommodation=600.0, food=300.0),
        ),
        travelers=2,
        trip_type=TripType.LEISURE,
        visibility=TripVisibility.SHARED,
        tags=["culture", "food"],
        preferences=None,
    )

    collaborator_id = str(uuid4())
    record = _trip_record(owner_id, request)
    db = _TripDatabaseStub(
        record=record,
        collaborators=[{"user_id": collaborator_id, "permission": "edit"}],
    )

    service = TripService(database_service=cast(DatabaseService, db))
    result = await service.create_trip(owner_id, request)

    assert db.created_payload is not None
    start_value = db.created_payload["start_date"]
    normalized_start = (
        start_value.date() if isinstance(start_value, datetime) else start_value
    )
    assert isinstance(normalized_start, date)
    # pylint: disable=no-member
    assert normalized_start.isoformat() == request.start_date.date().isoformat()
    assert result.note_count == db.related_counts["notes"]
    assert result.attachment_count == db.related_counts["attachments"]
    assert result.shared_with == [collaborator_id]


@pytest.mark.asyncio
async def test_check_trip_access_allows_collaborator() -> None:
    """Collaborators should be granted access even when not owners."""
    owner_id = str(uuid4())
    collaborator_id = str(uuid4())
    request = TripCreateRequest(
        title="Summer Trek",
        description=None,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
        destination="Reykjavik",
        destinations=[],
        budget=Budget(
            total=900.0,
            currency="EUR",
            spent=0.0,
            breakdown=BudgetBreakdown(),
        ),
        travelers=1,
        trip_type=TripType.LEISURE,
        visibility=TripVisibility.PRIVATE,
        tags=[],
        preferences=None,
    )

    record = _trip_record(owner_id, request)
    collaborators = [
        {"user_id": collaborator_id, "permission": "view"},
    ]
    db = _TripDatabaseStub(record=record, collaborators=collaborators)
    service = TripService(database_service=cast(DatabaseService, db))

    has_access = await cast(Any, service)._check_trip_access(
        record["id"], collaborator_id, require_owner=False
    )
    owner_only = await cast(Any, service)._check_trip_access(
        record["id"], collaborator_id, require_owner=True
    )

    assert has_access is True
    assert owner_only is False
