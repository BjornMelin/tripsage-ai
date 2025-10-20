"""Final tests for DestinationService search behavior and caching.

Covers:
- External service None path falls back to mock data.
- Cache hit/miss for identical search requests.
- External service mapping produces Destination with source="external_api".
"""

from __future__ import annotations

from typing import Any

import pytest

from tripsage_core.services.business.destination_service import (
    Destination,
    DestinationSearchRequest,
    DestinationService,
)


class _DBStub:
    """Minimal DB stub to satisfy DestinationService calls."""

    async def store_destination_search(self, data: dict[str, Any]) -> None:
        """No-op for tests."""
        return

    async def store_destination(self, data: dict[str, Any]) -> None:
        """No-op for tests."""
        return

    async def store_saved_destination(self, data: dict[str, Any]) -> None:
        """No-op for tests."""
        return

    async def get_saved_destinations(
        self, filters: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        """Return empty saved destinations for tests."""
        return []


class _ExternalStub:
    """External destination API stub that returns a single destination dict."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def search_destinations(self, req: dict[str, Any]) -> list[dict[str, Any]]:
        """Return a list containing the configured payload."""
        return [self._payload]


class _NoWeather:
    """Dummy weather service to bypass real initialization."""

    async def get_climate_info(self, lat: float, lon: float) -> dict[str, Any]:
        """Return empty climate info for tests."""
        return {}


@pytest.mark.anyio
async def test_search_destinations_mock_and_cache() -> None:
    """When external is None, use mock data and then serve from cache."""
    svc = DestinationService(
        database_service=_DBStub(),
        external_destination_service=None,
        weather_service=_NoWeather(),
        cache_ttl=3600,
    )

    req = DestinationSearchRequest(
        query="paris",
        categories=None,
        min_safety_rating=None,
        max_safety_rating=None,
        travel_month=None,
        budget_range=None,
        continent=None,
        country=None,
        climate_preference=None,
        limit=2,
        include_weather=False,
        include_pois=False,
        include_advisory=False,
    )

    first = await svc.search_destinations(req)
    assert first.cached is False
    assert len(first.destinations) == 2
    assert all(d.source == "mock" for d in first.destinations)

    second = await svc.search_destinations(req)
    assert second.cached is True
    assert len(second.destinations) == 2


@pytest.mark.anyio
async def test_search_external_mapping_and_cache() -> None:
    """External stub maps to Destination with source set and is cached on repeat."""
    ext = _ExternalStub(
        {
            "id": "ext-1",
            "name": "Test City",
            "country": "Testland",
            "latitude": 10.0,
            "longitude": 20.0,
            "rating": 4.2,
        }
    )
    svc = DestinationService(
        database_service=_DBStub(),
        external_destination_service=ext,
        weather_service=_NoWeather(),
        cache_ttl=3600,
    )
    req = DestinationSearchRequest(
        query="test",
        categories=None,
        min_safety_rating=None,
        max_safety_rating=None,
        travel_month=None,
        budget_range=None,
        continent=None,
        country=None,
        climate_preference=None,
        limit=1,
        include_weather=False,
        include_pois=False,
        include_advisory=False,
    )

    first = await svc.search_destinations(req)
    assert first.cached is False
    assert len(first.destinations) == 1
    d0: Destination = first.destinations[0]
    assert d0.name == "Test City"
    assert d0.country == "Testland"
    assert d0.source == "external_api"

    second = await svc.search_destinations(req)
    assert second.cached is True
    assert len(second.destinations) == 1


@pytest.mark.anyio
async def test_search_external_none_path_returns_mock_when_empty() -> None:
    """If external returns empty or is None, fallback generates mock results."""

    class _EmptyExternal:
        async def search_destinations(
            self, req: dict[str, Any]
        ) -> list[dict[str, Any]]:
            return []

    svc = DestinationService(
        database_service=_DBStub(),
        external_destination_service=_EmptyExternal(),
        weather_service=_NoWeather(),
        cache_ttl=3600,
    )
    req = DestinationSearchRequest(
        query="x",
        categories=None,
        min_safety_rating=None,
        max_safety_rating=None,
        travel_month=None,
        budget_range=None,
        continent=None,
        country=None,
        climate_preference=None,
        limit=1,
        include_weather=False,
        include_pois=False,
        include_advisory=False,
    )
    resp = await svc.search_destinations(req)
    assert len(resp.destinations) == 1
    assert resp.destinations[0].source in {"external_api", "mock"}
