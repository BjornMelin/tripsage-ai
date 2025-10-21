"""FlightService tests with a Duffel-like provider (no network).

These tests validate that FlightService consumes a provider returning Duffel
offer dictionaries and maps them into canonical FlightOffer models, and that
booking consumes provider.create_order results.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tripsage_core.models.domain.flights_canonical import (
    FlightBookingRequest,
)
from tripsage_core.models.schemas_common.enums import CabinClass, PassengerType
from tripsage_core.models.schemas_common.flight_schemas import (
    FlightPassenger,
    FlightSearchRequest,
)
from tripsage_core.services.business.flight_service import FlightService


def _duffel_offer_sample() -> dict[str, Any]:
    """Minimal Duffel-like offer payload compatible with the mapper."""
    return {
        "id": "off_abc",
        "total_amount": "324.50",
        "total_currency": "USD",
        "cabin_class": "economy",
        "slices": [
            {
                "segments": [
                    {
                        "segment": {
                            "origin": {"iata_code": "LAX"},
                            "destination": {"iata_code": "NRT"},
                            "departing_at": datetime.now(UTC).isoformat(),
                            "arriving_at": datetime.now(UTC).isoformat(),
                            "marketing_carrier": {"iata_code": "AA"},
                            "marketing_carrier_flight_number": "100",
                        }
                    }
                ]
            }
        ],
    }


@pytest.mark.asyncio
async def test_search_maps_duffel_offers_to_canonical() -> None:
    """FlightService maps Duffel provider offers into canonical models."""
    mock_db = AsyncMock()
    provider = AsyncMock()
    provider.search_flights = AsyncMock(return_value=[_duffel_offer_sample()])

    service = FlightService(database_service=mock_db, external_flight_service=provider)

    req = FlightSearchRequest(
        origin="LAX",
        destination="NRT",
        departure_date=datetime.now(UTC).date(),
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

    resp = await service.search_flights(req)
    assert resp.total_results == 1
    offer = resp.offers[0]
    assert offer.currency == "USD"
    assert offer.cabin_class == CabinClass.ECONOMY
    assert offer.outbound_segments and offer.outbound_segments[0].origin == "LAX"


@pytest.mark.asyncio
async def test_booking_sets_confirmation_number_from_provider() -> None:
    """Booking consumes provider order and sets confirmation number and status."""
    mock_db = AsyncMock()
    provider = AsyncMock()
    provider.get_offer_details = AsyncMock(return_value=_duffel_offer_sample())
    provider.create_order = AsyncMock(return_value={"booking_reference": "CONF999"})

    # Ensure DB path doesn't short-circuit provider
    mock_db.get_flight_offer = AsyncMock(return_value=None)
    service = FlightService(database_service=mock_db, external_flight_service=provider)

    booking_req = FlightBookingRequest(
        offer_id="off_abc",
        passengers=[
            FlightPassenger(
                type=PassengerType.ADULT,
                age=None,
                given_name="A",
                family_name="B",
                title=None,
                date_of_birth=None,
                email=None,
                phone=None,
            )
        ],
        trip_id=None,
        hold_only=False,
        metadata=None,
    )

    booking = await service.book_flight(user_id="user_x", booking_request=booking_req)
    assert booking.confirmation_number == "CONF999"
