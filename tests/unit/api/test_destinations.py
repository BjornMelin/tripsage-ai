"""Unit tests for destinations router using DI overrides.

Covers: search, get details (200/404), save destination (201), list saved,
and recommendations. Uses a minimal FakeDestinationService that returns
Pydantic models from tripsage.api.schemas.destinations to keep types aligned.
"""

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


class _FakeDestinationService:
    """Destination service stub returning typed Pydantic models."""

    async def search_destinations(
        self, request: DestinationSearchRequest
    ) -> DestinationSearchResponse:
        """Return one result for the given query."""
        dest = Destination.model_validate(
            {
                "id": "dest-1",
                "name": "Paris",
                "country": "FR",
                "city": "Paris",
            }
        )
        return DestinationSearchResponse(
            search_id="search-1",
            destinations=[dest],
            search_parameters=request,
            total_results=1,
            results_returned=1,
            search_duration_ms=10,
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
        """Return details for known id or None when missing."""
        if destination_id != "dest-1":
            return None
        return Destination.model_validate(
            {
                "id": "dest-1",
                "name": "Paris",
                "country": "FR",
                "city": "Paris",
            }
        )

    async def save_destination(
        self, user_id: str, request: SavedDestinationRequest
    ) -> SavedDestination:
        """Persist a saved destination and return SavedDestination model."""
        dest = Destination.model_validate(
            {
                "id": request.destination_id,
                "name": "Paris",
                "country": "FR",
                "city": "Paris",
            }
        )
        return SavedDestination(
            id="saved-1",
            user_id=user_id,
            trip_id=request.trip_id,
            destination=dest,
            notes=request.notes,
            priority=request.priority,
            planned_visit_date=None,
            duration_days=None,
            saved_at=datetime.now(UTC),
        )

    async def get_saved_destinations(self, user_id: str) -> list[SavedDestination]:
        """Return a list containing one saved destination for the user."""
        dest = Destination.model_validate(
            {"id": "dest-1", "name": "Paris", "country": "FR", "city": "Paris"}
        )
        return [
            SavedDestination(
                id="saved-1",
                user_id=user_id,
                trip_id=None,
                destination=dest,
                notes=None,
                priority=3,
                planned_visit_date=None,
                duration_days=None,
                saved_at=datetime.now(UTC),
            )
        ]

    async def get_destination_recommendations(
        self, *, user_id: str, recommendation_request: DestinationRecommendationRequest
    ) -> list[DestinationRecommendation]:
        """Return one recommendation for the user based on request."""
        dest = Destination.model_validate(
            {"id": "dest-1", "name": "Paris", "country": "FR", "city": "Paris"}
        )
        rec = DestinationRecommendation.model_validate(
            {
                "destination": dest.model_dump(),
                "match_score": 0.9,
                "reasons": ["culture", "food"],
                "best_for": ["city breaks"],
            }
        )
        return [rec]


def _build_app(principal: Any) -> FastAPI:
    """Build app and apply overrides."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "destinations_router_module", "tripsage/api/routers/destinations.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]

    app = FastAPI()
    app.include_router(module.router, prefix="/api/destinations")

    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    def _provide_dest_svc() -> _FakeDestinationService:
        """Provide destination service stub."""
        return _FakeDestinationService()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_destination_service] = _provide_dest_svc  # type: ignore[assignment]

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_get_save_list_and_recommend(
    principal: Any, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> None:
    """End-to-end exercise of destination endpoints with DI stubs."""
    app = _build_app(principal)
    client = async_client_factory(app)

    # Search
    req = {"query": "paris"}
    r = await client.post("/api/destinations/search", json=req)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["total_results"] == 1 and data["results_returned"] == 1

    # Get details 200
    r = await client.get("/api/destinations/dest-1")
    assert r.status_code == status.HTTP_200_OK

    # Get details 404
    r = await client.get("/api/destinations/unknown-id")
    assert r.status_code == status.HTTP_404_NOT_FOUND

    # Save destination (201)
    save = {"destination_id": "dest-1", "trip_id": None, "notes": "n"}
    r = await client.post("/api/destinations/saved", json=save)
    assert r.status_code == status.HTTP_201_CREATED
    body = r.json()
    assert body["destination"]["id"] == "dest-1"

    # List saved
    r = await client.get("/api/destinations/saved")
    # Note: router order must place '/saved' before '/{destination_id}'
    # for this to be 200
    assert r.status_code == status.HTTP_200_OK
    arr: list[dict[str, Any]] = r.json()
    assert isinstance(arr, list) and len(arr) >= 1

    # Recommendations
    rec_req = {"user_interests": ["food", "museums"]}
    r = await client.post("/api/destinations/recommendations", json=rec_req)
    assert r.status_code == status.HTTP_200_OK
    recs = r.json()
    assert isinstance(recs, list) and recs and recs[0]["destination"]["id"] == "dest-1"
