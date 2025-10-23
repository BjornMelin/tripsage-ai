"""Minimal tests for DestinationService final constructor and external search hook."""

from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.business.destination_service import (
    DestinationCategory,
    DestinationSearchRequest,
    DestinationService,
)


@pytest.fixture
def service_with_mocks() -> DestinationService:
    """Create service with an external_destination_service mock bound."""
    external = AsyncMock()
    external.search_destinations.return_value = [
        {"id": "ext-1", "name": "Paris", "country": "France"}
    ]
    return DestinationService(
        external_destination_service=external,
        database_service=AsyncMock(),
        weather_service=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_external_search_path_returns_converted_results(
    service_with_mocks: DestinationService,
) -> None:
    """External search returns converted Destination objects when service present."""
    req = DestinationSearchRequest(
        query="Paris",
        categories=[DestinationCategory.CITY],
        min_safety_rating=None,
        max_safety_rating=None,
        travel_month=None,
        budget_range=None,
        continent=None,
        country=None,
        climate_preference=None,
    )
    results = await service_with_mocks._search_external_destinations(req)
    assert results and results[0].name == "Paris"
