"""Unit tests for FlightService booking and cancellation flows.

These tests exercise the final canonical service behavior using mocked
database and external service dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from tripsage_core.models.domain.flights_canonical import (
    FlightBookingRequest,
    FlightOffer,
    FlightSegment,
)
from tripsage_core.models.schemas_common.enums import (
    BookingStatus,
    CabinClass,
    PassengerType,
)
from tripsage_core.models.schemas_common.flight_schemas import FlightPassenger
from tripsage_core.services.business.flight_service import (
    FlightService,
)


@pytest.mark.asyncio
async def test_book_flight_saves_booking_success():
    """Booking succeeds with external service absent and DB is written."""
    # Arrange service with mocked DB and no external API
    mock_db = AsyncMock()
    service = FlightService(database_service=mock_db, external_flight_service=None)

    # Mock offer lookup used by book_flight
    # pylint: disable=duplicate-code
    offer = FlightOffer(  # type: ignore[reportCallIssue]
        id="off_1",
        search_id="s_1",
        outbound_segments=[
            FlightSegment(
                origin="LAX",
                destination="NRT",
                departure_date=datetime.now(UTC) + timedelta(days=1),
                arrival_date=datetime.now(UTC) + timedelta(days=1, hours=11),
                airline="AA",
                flight_number="AA100",
                aircraft_type=None,
                duration_minutes=None,
            )
        ],
        total_price=500.0,
        currency="USD",
        cabin_class=CabinClass.ECONOMY,
        return_segments=None,
        base_price=None,
        taxes=None,
        booking_class=None,
        total_duration=None,
        expires_at=None,
        source=None,
        source_offer_id=None,
        score=None,
        price_score=None,
        convenience_score=None,
        bookable=True,
    )
    service.get_offer_details = AsyncMock(return_value=offer)  # type: ignore[attr-defined]

    booking_req = FlightBookingRequest(
        offer_id="off_1",
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
        trip_id="trip_1",
        metadata={},
    )

    # Act
    booking = await service.book_flight(user_id="user_1", booking_request=booking_req)

    # Assert
    assert booking.offer_id == "off_1"
    assert booking.user_id == "user_1"
    assert booking.status in {BookingStatus.SAVED, BookingStatus.BOOKED}
    mock_db.store_flight_booking.assert_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cancel_booking_success():
    """Cancellation updates booking status and returns True."""
    mock_db = AsyncMock()
    service = FlightService(database_service=mock_db, external_flight_service=None)

    booking_id = "b_1"
    user_id = "u_1"
    now = datetime.now(UTC)
    mock_db.get_flight_booking = AsyncMock(  # type: ignore[attr-defined]
        return_value={
            "id": booking_id,
            "trip_id": "t_1",
            "user_id": user_id,
            "offer_id": "off_1",
            "passengers": [
                {
                    "type": "adult",
                    "given_name": "Jane",
                    "family_name": "Doe",
                }
            ],
            "outbound_segments": [
                {
                    "origin": "LAX",
                    "destination": "NRT",
                    "departure_date": now.isoformat(),
                    "arrival_date": (now + timedelta(hours=11)).isoformat(),
                    "airline": "AA",
                    "flight_number": "AA100",
                }
            ],
            "return_segments": None,
            "total_price": 500.0,
            "currency": "USD",
            "status": "booked",
            "booked_at": now.isoformat(),
            "cancellable": True,
            "refundable": True,
            "metadata": {},
        }
    )
    mock_db.update_flight_booking = AsyncMock(return_value=True)  # type: ignore[attr-defined]

    success = await service.cancel_booking(booking_id=booking_id, user_id=user_id)

    assert success is True
    mock_db.update_flight_booking.assert_awaited_with(  # type: ignore[attr-defined]
        booking_id, {"status": "cancelled"}
    )
