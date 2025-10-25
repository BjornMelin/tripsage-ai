"""Unit tests for :mod:`tripsage_core.services.business.destination_service`."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from tripsage_core.services.business.destination_service import (
    Destination,
    DestinationCategory,
    DestinationSearchRequest,
    DestinationService,
)


@pytest.mark.asyncio
async def test_search_destinations_uses_cache_when_available() -> None:
    """Cached search results should short-circuit destination generation."""
    service = DestinationService(database_service=object(), weather_service=object())
    request = DestinationSearchRequest(
        query="Kyoto",
        categories=[DestinationCategory.CULTURAL],
        min_safety_rating=None,
        max_safety_rating=None,
        travel_month=None,
        budget_range=None,
        continent=None,
        country="Japan",
        climate_preference=None,
        limit=3,
        include_weather=False,
        include_pois=False,
        include_advisory=False,
    )

    cached_destination = Destination(
        id="dest-kyoto",
        name="Kyoto",
        country="Japan",
        region="Kansai",
        city="Kyoto",
        description="Historic city",
        long_description=None,
        categories=[DestinationCategory.CULTURAL],
        latitude=35.0,
        longitude=135.0,
        timezone="Asia/Tokyo",
        currency="JPY",
        languages=["Japanese"],
        images=[],
        rating=4.8,
        review_count=1200,
        safety_rating=4.5,
        visa_requirements=None,
        local_transportation="Subway",
        popular_activities=["Temple tours"],
        points_of_interest=[],
        weather=None,
        best_time_to_visit=["April", "October"],
        travel_advisory=None,
        source="cache",
        last_updated=datetime.now(UTC),
        relevance_score=0.9,
    )

    cache_key = cast(Any, service)._generate_search_cache_key(request)
    cast(Any, service)._search_cache[cache_key] = (
        {"destinations": [cached_destination]},
        time.time(),
    )

    response = await service.search_destinations(request)

    assert response.cached is True
    assert response.destinations == [cached_destination]


def test_get_cached_search_expires_entries() -> None:
    """Expired cache entries should be evicted before retrieval."""
    service = DestinationService(database_service=object(), weather_service=object())
    service.cache_ttl = 1

    cast(Any, service)._cache_search_results("key", {"destinations": []})
    assert cast(Any, service)._get_cached_search("key") == {"destinations": []}

    cast(Any, service)._search_cache["key"] = (
        {"destinations": []},
        time.time() - 5,
    )
    assert cast(Any, service)._get_cached_search("key") is None
