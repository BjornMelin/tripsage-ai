"""Tests for Flight model."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.flight import Flight
from tripsage_core.models.schemas_common.enums import (
    AirlineProvider,
    BookingStatus,
    DataSource,
)


def test_flight_creation(sample_flight_dict):
    """Test creating a Flight model with valid data."""
    flight = Flight(**sample_flight_dict)
    assert flight.id == 1
    assert flight.trip_id == 1
    assert flight.origin == "LAX"
    assert flight.destination == "NRT"
    assert flight.airline == AirlineProvider.JAPAN_AIRLINES
    assert flight.price == 1200.00
    assert flight.booking_status == BookingStatus.VIEWED
    assert flight.data_source == DataSource.DUFFEL


def test_flight_optional_fields():
    """Test creating a Flight model with minimal required fields."""
    now = datetime.now(datetime.UTC)
    minimal_flight = Flight(
        trip_id=1,
        origin="LAX",
        destination="NRT",
        airline=AirlineProvider.JAPAN_AIRLINES,
        departure_time=now + timedelta(days=10),
        arrival_time=now + timedelta(days=10, hours=12),
        price=1200.00,
        search_timestamp=now,
        data_source=DataSource.DUFFEL,
    )

    assert minimal_flight.trip_id == 1
    assert minimal_flight.id is None
    assert minimal_flight.booking_link is None
    assert minimal_flight.segment_number == 1  # Default value
    assert minimal_flight.booking_status == BookingStatus.VIEWED  # Default value


def test_flight_validation_airport_codes():
    """Test airport code validation."""
    now = datetime.now(datetime.UTC)

    # Test valid code
    flight = Flight(
        trip_id=1,
        origin="LAX",
        destination="NRT",
        airline=AirlineProvider.JAPAN_AIRLINES,
        departure_time=now + timedelta(days=10),
        arrival_time=now + timedelta(days=10, hours=12),
        price=1200.00,
        search_timestamp=now,
        data_source=DataSource.DUFFEL,
    )
    assert flight.origin == "LAX"

    # Test invalid origin code
    with pytest.raises(ValidationError) as excinfo:
        Flight(
            trip_id=1,
            origin="INVALID",  # Too long
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
    assert "Airport code must be a 3-letter IATA code" in str(excinfo.value)

    # Test invalid destination code
    with pytest.raises(ValidationError) as excinfo:
        Flight(
            trip_id=1,
            origin="LAX",
            destination="12",  # Too short
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
    assert "Airport code must be a 3-letter IATA code" in str(excinfo.value)


def test_flight_validation_dates():
    """Test date validation."""
    now = datetime.now(datetime.UTC)

    # Test arrival before departure
    with pytest.raises(ValidationError) as excinfo:
        Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=9),  # Before departure
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
    assert "Arrival time must be after departure time" in str(excinfo.value)


def test_flight_validation_price():
    """Test price validation."""
    now = datetime.now(datetime.UTC)

    # Test negative price
    with pytest.raises(ValidationError) as excinfo:
        Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=-100.00,  # Negative price
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
    assert "ensure this value is greater than 0" in str(excinfo.value)


def test_flight_duration_property(sample_flight_dict):
    """Test the duration property."""
    flight = Flight(**sample_flight_dict)
    assert flight.duration.total_seconds() == 12 * 3600  # 12 hours


def test_flight_formatted_duration(sample_flight_dict):
    """Test the formatted_duration property."""
    flight = Flight(**sample_flight_dict)
    assert flight.formatted_duration == "12h 0m"

    # Test with minutes
    now = datetime.now(datetime.UTC)
    flight = Flight(
        trip_id=1,
        origin="LAX",
        destination="NRT",
        airline=AirlineProvider.JAPAN_AIRLINES,
        departure_time=now,
        arrival_time=now + timedelta(hours=9, minutes=45),
        price=1200.00,
        search_timestamp=now,
        data_source=DataSource.DUFFEL,
    )
    assert flight.formatted_duration == "9h 45m"


def test_flight_is_booked_property(sample_flight_dict):
    """Test the is_booked property."""
    flight = Flight(**sample_flight_dict)
    assert flight.is_booked is False

    flight.booking_status = BookingStatus.BOOKED
    assert flight.is_booked is True


def test_flight_is_canceled_property(sample_flight_dict):
    """Test the is_canceled property."""
    flight = Flight(**sample_flight_dict)
    assert flight.is_canceled is False

    flight.booking_status = BookingStatus.CANCELED
    assert flight.is_canceled is True


def test_flight_book(sample_flight_dict):
    """Test booking a flight."""
    flight = Flight(**sample_flight_dict)
    flight.book()
    assert flight.booking_status == BookingStatus.BOOKED


def test_flight_cancel(sample_flight_dict):
    """Test canceling a flight."""
    flight = Flight(**sample_flight_dict)
    flight.book()
    flight.cancel()
    assert flight.booking_status == BookingStatus.CANCELED

    # Cannot cancel a viewed flight
    flight = Flight(**sample_flight_dict)
    with pytest.raises(ValueError) as excinfo:
        flight.cancel()
    assert "Only booked flights can be canceled" in str(excinfo.value)


def test_flight_model_dump(sample_flight_dict):
    """Test model_dump method."""
    flight = Flight(**sample_flight_dict)
    flight_dict = flight.model_dump()

    assert flight_dict["origin"] == "LAX"
    assert flight_dict["destination"] == "NRT"
    assert flight_dict["airline"] == AirlineProvider.JAPAN_AIRLINES
    assert flight_dict["price"] == 1200.00
    assert flight_dict["booking_status"] == BookingStatus.VIEWED
    assert flight_dict["data_source"] == DataSource.DUFFEL
