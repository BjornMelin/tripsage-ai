"""Unit tests for :mod:`tripsage_core.services.business.accommodation_service`."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

import pytest

from tripsage_core.services.business.accommodation_service import (
    AccommodationSearchRequest,
    AccommodationService,
)


def _search_request() -> AccommodationSearchRequest:
    """Create a deterministic accommodation search request for tests."""
    today = date(2025, 4, 1)
    return AccommodationSearchRequest(
        user_id="user-1",
        trip_id=None,
        location="Kyoto, Japan",
        check_in=today,
        check_out=today + timedelta(days=3),
        guests=2,
        adults=2,
        children=0,
        infants=0,
        property_types=None,
        min_price=None,
        max_price=None,
        currency="USD",
        bedrooms=None,
        beds=None,
        bathrooms=None,
        amenities=None,
        accessibility_features=None,
        instant_book=None,
        free_cancellation=None,
        max_distance_km=None,
        min_rating=None,
        metadata=None,
        sort_by="relevance",
        sort_order="asc",
    )


@pytest.mark.asyncio
async def test_generate_mock_listings_produces_ranked_variants() -> None:
    """Mock listing generation should produce multiple priced variants."""
    service = AccommodationService(database_service=object())
    request = _search_request()

    listings = await cast(Any, service)._generate_mock_listings(request)

    assert len(listings) == 3
    assert all(listing.nights == 3 for listing in listings)
    prices = [listing.price_per_night for listing in listings]
    assert prices == sorted(prices)
    assert listings[0].location.city == "Kyoto"


@pytest.mark.asyncio
async def test_score_listings_adds_metrics_and_sorts() -> None:
    """Listing scoring should annotate fields and sort by descending score."""
    service = AccommodationService(database_service=object())
    request = _search_request()
    listings = await cast(Any, service)._generate_mock_listings(request)

    scored = await cast(Any, service)._score_listings(listings, request)

    assert all(listing.price_score is not None for listing in scored)
    assert scored == sorted(scored, key=lambda item: item.score or 0, reverse=True)
