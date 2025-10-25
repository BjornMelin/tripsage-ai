"""Integration tests for trip management endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from tripsage.api.core.dependencies import require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import Budget, BudgetBreakdown, TripPreferences
from tripsage_core.services.business.trip_service import (
    TripCreateRequest as CoreTripCreateRequest,
    TripLocation,
    TripResponse as CoreTripResponse,
    get_trip_service,
)


class TripServiceStub:
    """Stubbed trip service returning deterministic responses."""

    def __init__(self) -> None:
        """Initialize canned trip response data."""
        now = datetime.now(UTC)
        self.response = CoreTripResponse(
            id=uuid4(),
            user_id=uuid4(),
            title="Kyoto Adventure",
            description="A spring getaway",
            start_date=now,
            end_date=now + timedelta(days=3),
            destination="Kyoto",
            destinations=[
                TripLocation(
                    name="Kyoto",
                    country="Japan",
                    city="Kyoto",
                    coordinates=None,
                    timezone="Asia/Tokyo",
                )
            ],
            budget=Budget(
                total=1500.0,
                currency="USD",
                breakdown=BudgetBreakdown(
                    accommodation=600.0,
                    transportation=500.0,
                    food=300.0,
                    activities=100.0,
                    miscellaneous=0.0,
                ),
            ),
            travelers=2,
            trip_type=TripType.LEISURE,
            status=TripStatus.PLANNING,
            visibility=TripVisibility.PRIVATE,
            tags=["culture"],
            preferences=TripPreferences.model_validate({}),
            created_at=now,
            updated_at=now,
            note_count=0,
            attachment_count=0,
            collaborator_count=1,
            shared_with=["friend-1"],
        )
        self.create_calls: list[tuple[str, CoreTripCreateRequest]] = []

    async def create_trip(
        self, user_id: str, trip_data: CoreTripCreateRequest
    ) -> CoreTripResponse:
        """Record invocation and return the canned response."""
        self.create_calls.append((user_id, trip_data))
        return self.response

    async def get_trip(self, trip_id: str, user_id: str) -> CoreTripResponse | None:
        """Return the canned response for retrieval scenarios."""
        return self.response


def _principal_stub() -> Principal:
    return Principal(
        id="user-123",
        type="user",
        email="user@example.com",
        auth_method="jwt",
        scopes=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_create_trip_returns_transformed_response(
    app: FastAPI, async_client: AsyncClient
) -> None:
    """POST /trips should adapt the core trip response into API schema."""
    trip_service = TripServiceStub()

    async def _principal_override() -> Principal:
        return _principal_stub()

    async def _trip_service_override() -> TripServiceStub:
        return trip_service

    app.dependency_overrides[require_principal] = _principal_override
    app.dependency_overrides[get_trip_service] = _trip_service_override

    payload: dict[str, Any] = {
        "title": "Kyoto Adventure",
        "description": "A spring getaway",
        "start_date": "2025-04-01",
        "end_date": "2025-04-04",
        "destinations": [
            {
                "name": "Kyoto",
                "country": "Japan",
                "city": "Kyoto",
                "arrival_date": "2025-04-01",
                "departure_date": "2025-04-04",
                "duration_days": 3,
                "coordinates": None,
            }
        ],
    }

    try:
        response = await async_client.post("/api/trips/", json=payload)
    finally:
        app.dependency_overrides.pop(require_principal, None)
        app.dependency_overrides.pop(get_trip_service, None)

    assert response.status_code == 201
    data: dict[str, Any] = response.json()
    assert data["title"] == "Kyoto Adventure"
    assert data["destinations"][0]["name"] == "Kyoto"
    assert data["duration_days"] == 3
    assert trip_service.create_calls


@pytest.mark.asyncio
async def test_get_trip_returns_core_payload(
    app: FastAPI, async_client: AsyncClient
) -> None:
    """GET /trips/{trip_id} should surface the core trip response."""
    trip_service = TripServiceStub()

    async def _principal_override() -> Principal:
        return _principal_stub()

    async def _trip_service_override() -> TripServiceStub:
        return trip_service

    app.dependency_overrides[require_principal] = _principal_override
    app.dependency_overrides[get_trip_service] = _trip_service_override

    trip_id = str(trip_service.response.id)
    try:
        response = await async_client.get(f"/api/trips/{trip_id}")
    finally:
        app.dependency_overrides.pop(require_principal, None)
        app.dependency_overrides.pop(get_trip_service, None)

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert UUID(data["id"]) == trip_service.response.id
    assert data["title"] == trip_service.response.title
    assert data["destinations"][0]["name"] == "Kyoto"
