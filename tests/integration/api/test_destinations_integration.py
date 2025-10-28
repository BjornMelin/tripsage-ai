"""Integration tests for destinations router using app fixture and DI stubs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from tripsage.api.schemas.destinations import (
    Destination,
    DestinationRecommendation,
    DestinationRecommendationRequest,
    DestinationSearchRequest,
    DestinationSearchResponse,
    SavedDestination,
    SavedDestinationRequest,
)


class _DestSvc:
    """Destinations service stub used in integration tests."""

    async def search_destinations(
        self, request: DestinationSearchRequest
    ) -> DestinationSearchResponse:
        """Search destinations."""
        dest = Destination.model_validate(
            {"id": "d1", "name": "Paris", "country": "FR", "city": "Paris"}
        )
        return DestinationSearchResponse(
            search_id="s1",
            destinations=[dest],
            search_parameters=request,
            total_results=1,
            results_returned=1,
            search_duration_ms=5,
            cached=False,
        )

    async def get_destination_details(
        self,
        destination_id: str,
        *,
        include_weather: bool,
        include_pois: bool,
        include_advisory: bool,
    ) -> Destination | None:
        """Get destination details."""
        if destination_id != "d1":
            return None
        return Destination.model_validate(
            {"id": "d1", "name": "Paris", "country": "FR", "city": "Paris"}
        )

    async def save_destination(
        self, user_id: str, request: SavedDestinationRequest
    ) -> SavedDestination:
        """Save destination."""
        dest = Destination.model_validate(
            {"id": request.destination_id, "name": "Paris", "country": "FR"}
        )
        return SavedDestination(
            id="sd1",
            user_id=user_id,
            trip_id=request.trip_id,
            destination=dest,
            notes=request.notes,
            priority=request.priority,
            planned_visit_date=None,
            duration_days=None,
            saved_at=datetime.now(UTC),
        )

    async def get_destination_recommendations(
        self, *, user_id: str, recommendation_request: DestinationRecommendationRequest
    ) -> list[DestinationRecommendation]:
        """Get destination recommendations."""
        dest = Destination.model_validate(
            {"id": "d1", "name": "Paris", "country": "FR", "city": "Paris"}
        )
        rec = DestinationRecommendation.model_validate(
            {
                "destination": dest.model_dump(),
                "match_score": 0.9,
                "reasons": ["culture"],
                "best_for": ["city breaks"],
            }
        )
        return [rec]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_destinations_search_and_get_404(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """Search returns results; unknown id yields 404."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    def _provide_dest_svc() -> _DestSvc:
        """Provide destination service stub."""
        return _DestSvc()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_destination_service] = _provide_dest_svc  # type: ignore[assignment]

    client = async_client_factory(app)

    r = await client.post("/api/destinations/search", json={"query": "paris"})
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["total_results"] == 1

    r = await client.get("/api/destinations/unknown")
    assert r.status_code == status.HTTP_404_NOT_FOUND
