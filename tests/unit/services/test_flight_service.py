"""Unit tests for :mod:`tripsage_core.services.business.flight_service`."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

import pytest

from tripsage_core.models.schemas_common.enums import CabinClass
from tripsage_core.models.schemas_common.flight_schemas import FlightSearchRequest
from tripsage_core.services.business.flight_service import FlightService


def _flight_request() -> FlightSearchRequest:
    """Construct a baseline flight search request for tests."""
    return FlightSearchRequest(
        origin="NRT",
        destination="SFO",
        departure_date=date(2025, 5, 1),
        return_date=None,
        adults=1,
        children=0,
        infants=0,
        passengers=None,
        cabin_class=CabinClass.ECONOMY,
        max_stops=None,
        max_price=None,
        currency="USD",
        flexible_dates=False,
        preferred_airlines=None,
        excluded_airlines=None,
        trip_id=None,
    )


@pytest.mark.asyncio
async def test_generate_mock_offers_creates_incremental_options() -> None:
    """Mock offer generation should create incremental price and stop variants."""
    service = FlightService(database_service=object())
    request = _flight_request()

    offers = await cast(Any, service)._generate_mock_offers(request)

    assert len(offers) == 3
    prices = [offer.total_price for offer in offers]
    assert prices == sorted(prices)
    assert [offer.stops_count for offer in offers] == [0, 1, 2]
    assert all(
        segment.origin == request.origin
        for offer in offers
        for segment in offer.outbound_segments
    )


@pytest.mark.asyncio
async def test_score_offers_orders_by_value() -> None:
    """Offer scoring should annotate price metrics and sort by overall score."""
    service = FlightService(database_service=object())
    request = _flight_request()
    offers = await cast(Any, service)._generate_mock_offers(request)

    scored = await cast(Any, service)._score_offers(offers, request)

    assert all(offer.price_score is not None for offer in scored)
    assert scored == sorted(scored, key=lambda offer: offer.score or 0, reverse=True)
