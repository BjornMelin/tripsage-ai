"""Tests for booking status transition utilities."""

from datetime import UTC

from tripsage_core.models.db.accommodation import Accommodation, BookingStatus
from tripsage_core.models.db.flight import Flight
from tripsage_core.models.db.transportation import Transportation
from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    AirlineProvider,
    CancellationPolicy,
    DataSource,
    TransportationType,
)
from tripsage_core.utils.booking_utils import (
    get_standard_booking_transitions,
    validate_booking_status_transition,
)


def test_validate_booking_status_transition() -> None:
    """Test validate_booking_status_transition utility function."""
    transitions = get_standard_booking_transitions()

    # Valid transitions
    assert (
        validate_booking_status_transition(
            BookingStatus.VIEWED, BookingStatus.SAVED, transitions
        )
        is True
    )
    assert (
        validate_booking_status_transition(
            BookingStatus.VIEWED, BookingStatus.BOOKED, transitions
        )
        is True
    )
    assert (
        validate_booking_status_transition(
            BookingStatus.SAVED, BookingStatus.BOOKED, transitions
        )
        is True
    )
    assert (
        validate_booking_status_transition(
            BookingStatus.BOOKED, BookingStatus.CANCELLED, transitions
        )
        is True
    )

    # Invalid transitions
    assert (
        validate_booking_status_transition(
            BookingStatus.BOOKED, BookingStatus.SAVED, transitions
        )
        is False
    )
    assert (
        validate_booking_status_transition(
            BookingStatus.CANCELLED, BookingStatus.BOOKED, transitions
        )
        is False
    )
    assert (
        validate_booking_status_transition(
            BookingStatus.BOOKED, BookingStatus.VIEWED, transitions
        )
        is False
    )


def test_accommodation_update_status() -> None:
    """Test Accommodation.update_status uses shared utility."""
    from datetime import date

    accommodation = Accommodation(
        id=None,
        trip_id=1,
        name="Test Hotel",
        accommodation_type=AccommodationType.HOTEL,
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        price_per_night=100.0,
        total_price=400.0,
        location="123 Main St, Test City",
        rating=4.5,
        amenities=None,
        booking_link=None,
        search_timestamp=None,
        cancellation_policy=CancellationPolicy.FREE,
        distance_to_center=None,
        neighborhood=None,
        booking_status=BookingStatus.VIEWED,
    )

    # Valid transitions
    assert accommodation.update_status(BookingStatus.SAVED) is True
    assert accommodation.booking_status == BookingStatus.SAVED

    assert accommodation.update_status(BookingStatus.BOOKED) is True
    assert accommodation.booking_status == BookingStatus.BOOKED

    # Invalid transition
    assert accommodation.update_status(BookingStatus.VIEWED) is False
    assert accommodation.booking_status == BookingStatus.BOOKED  # Unchanged


def test_flight_update_status() -> None:
    """Test Flight.update_status uses shared utility."""
    from datetime import datetime

    flight = Flight(
        id=None,
        trip_id=1,
        origin="NRT",
        destination="SFO",
        airline=AirlineProvider.AMERICAN,
        departure_time=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        arrival_time=datetime(2025, 6, 1, 18, 0, tzinfo=UTC),
        price=500.0,
        booking_link=None,
        segment_number=1,
        search_timestamp=datetime.now(UTC),
        data_source=DataSource.EXPEDIA,
        booking_status=BookingStatus.VIEWED,
    )

    # Valid transitions
    assert flight.update_status(BookingStatus.SAVED) is True
    assert flight.booking_status == BookingStatus.SAVED

    assert flight.update_status(BookingStatus.BOOKED) is True
    assert flight.booking_status == BookingStatus.BOOKED

    # Invalid transition
    assert flight.update_status(BookingStatus.VIEWED) is False
    assert flight.booking_status == BookingStatus.BOOKED  # Unchanged


def test_transportation_update_status() -> None:
    """Test Transportation.update_status uses shared utility."""
    from datetime import datetime

    transportation = Transportation(
        id=None,
        trip_id=1,
        transportation_type=TransportationType.CAR_RENTAL,
        provider="Test Rental",
        pickup_date=datetime(2025, 6, 1, 10, 0, tzinfo=UTC),
        dropoff_date=datetime(2025, 6, 1, 14, 0, tzinfo=UTC),
        price=50.0,
        notes=None,
        booking_status=BookingStatus.VIEWED,
    )

    # Valid transitions
    assert transportation.update_status(BookingStatus.SAVED) is True
    assert transportation.booking_status == BookingStatus.SAVED

    assert transportation.update_status(BookingStatus.BOOKED) is True
    assert transportation.booking_status == BookingStatus.BOOKED

    # Invalid transition
    assert transportation.update_status(BookingStatus.VIEWED) is False
    assert transportation.booking_status == BookingStatus.BOOKED  # Unchanged
