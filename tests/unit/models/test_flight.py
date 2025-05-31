"""Comprehensive tests for Flight model following Pydantic v2 best practices."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.flight import Flight
from tripsage_core.models.schemas_common.enums import (
    AirlineProvider,
    BookingStatus,
    DataSource,
)


class TestFlightModel:
    """Comprehensive Flight model testing following Pydantic v2 best practices."""

    def test_flight_creation_basic(self, sample_flight_dict):
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

    def test_flight_optional_fields(self):
        """Test creating a Flight model with minimal required fields."""
        now = datetime.now(timezone.utc)
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

    @pytest.mark.parametrize(
        "origin,destination,expected_origin,expected_destination",
        [
            ("LAX", "NRT", "LAX", "NRT"),
            ("lax", "nrt", "LAX", "NRT"),  # Test case conversion
            ("JFK", "CDG", "JFK", "CDG"),
        ],
    )
    def test_airport_codes_valid_parametrized(
        self, origin, destination, expected_origin, expected_destination
    ):
        """Test valid airport codes with parameterized inputs."""
        now = datetime.now(timezone.utc)
        flight = Flight(
            trip_id=1,
            origin=origin,
            destination=destination,
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.origin == expected_origin
        assert flight.destination == expected_destination

    @pytest.mark.parametrize(
        "invalid_code,error_field",
        [
            ("INVALID", "origin"),  # Too long
            ("12", "destination"),  # Too short
            ("1AB", "origin"),  # Contains numbers
            ("", "destination"),  # Empty
        ],
    )
    def test_airport_codes_invalid_parametrized(self, invalid_code, error_field):
        """Test invalid airport codes with specific error messages."""
        now = datetime.now(timezone.utc)
        kwargs = {
            "trip_id": 1,
            "origin": "LAX",
            "destination": "NRT",
            "airline": AirlineProvider.JAPAN_AIRLINES,
            "departure_time": now + timedelta(days=10),
            "arrival_time": now + timedelta(days=10, hours=12),
            "price": 1200.00,
            "search_timestamp": now,
            "data_source": DataSource.DUFFEL,
        }
        kwargs[error_field] = invalid_code

        with pytest.raises(
            ValidationError, match="Airport code must be a 3-letter IATA code"
        ):
            Flight(**kwargs)

    def test_flight_validation_airport_codes(self):
        """Test airport code validation."""
        now = datetime.now(timezone.utc)

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

    def test_flight_validation_dates(self):
        """Test date validation."""
        now = datetime.now(timezone.utc)

        # Test arrival before departure with specific error message
        with pytest.raises(
            ValidationError, match="Arrival time must be after departure time"
        ):
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

    @pytest.mark.parametrize(
        "invalid_price,expected_error",
        [
            (-100.00, "ensure this value is greater than 0"),
            (-0.01, "ensure this value is greater than 0"),
        ],
    )
    def test_flight_validation_price_negative(self, invalid_price, expected_error):
        """Test negative price validation with specific error messages."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError, match=expected_error):
            Flight(
                trip_id=1,
                origin="LAX",
                destination="NRT",
                airline=AirlineProvider.JAPAN_AIRLINES,
                departure_time=now + timedelta(days=10),
                arrival_time=now + timedelta(days=10, hours=12),
                price=invalid_price,
                search_timestamp=now,
                data_source=DataSource.DUFFEL,
            )

    @pytest.mark.parametrize(
        "valid_price",
        [
            (0.01),  # Minimal positive
            (1200.00),  # Normal price
            (10000.00),  # High price
        ],
    )
    def test_flight_validation_price_valid(self, valid_price):
        """Test valid price values."""
        now = datetime.now(timezone.utc)
        flight = Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=valid_price,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.price == valid_price

    def test_flight_validation_price(self):
        """Test price validation."""
        now = datetime.now(timezone.utc)

        # Test negative price (legacy test - keeping for compatibility)
        with pytest.raises(
            ValidationError, match="ensure this value is greater than 0"
        ):
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

    def test_flight_duration_property(self, sample_flight_dict):
        """Test the duration property."""
        flight = Flight(**sample_flight_dict)
        assert flight.duration.total_seconds() == 12 * 3600  # 12 hours

    def test_flight_formatted_duration(self, sample_flight_dict):
        """Test the formatted_duration property."""
        flight = Flight(**sample_flight_dict)
        assert flight.formatted_duration == "12h 0m"

        # Test with minutes
        now = datetime.now(timezone.utc)
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

    def test_flight_is_booked_property(self, sample_flight_dict):
        """Test the is_booked property."""
        flight = Flight(**sample_flight_dict)
        assert flight.is_booked is False

        flight.booking_status = BookingStatus.BOOKED
        assert flight.is_booked is True

    def test_flight_is_canceled_property(self, sample_flight_dict):
        """Test the is_canceled property."""
        flight = Flight(**sample_flight_dict)
        assert flight.is_canceled is False

        flight.booking_status = BookingStatus.CANCELED
        assert flight.is_canceled is True

    def test_flight_book(self, sample_flight_dict):
        """Test booking a flight."""
        flight = Flight(**sample_flight_dict)
        flight.book()
        assert flight.booking_status == BookingStatus.BOOKED

    def test_flight_cancel(self, sample_flight_dict):
        """Test canceling a flight."""
        flight = Flight(**sample_flight_dict)
        flight.book()
        flight.cancel()
        assert flight.booking_status == BookingStatus.CANCELED

        # Cannot cancel a viewed flight with specific error message
        flight = Flight(**sample_flight_dict)
        with pytest.raises(ValueError, match="Only booked flights can be canceled"):
            flight.cancel()

    def test_flight_model_dump(self, sample_flight_dict):
        """Test model_dump method."""
        flight = Flight(**sample_flight_dict)
        flight_dict = flight.model_dump()

        assert flight_dict["origin"] == "LAX"
        assert flight_dict["destination"] == "NRT"
        assert flight_dict["airline"] == AirlineProvider.JAPAN_AIRLINES
        assert flight_dict["price"] == 1200.00
        assert flight_dict["booking_status"] == BookingStatus.VIEWED
        assert flight_dict["data_source"] == DataSource.DUFFEL

    def test_flight_model_validate_json(self):
        """Test model_validate_json method with JSON string input."""
        json_string = """
        {
            "trip_id": 1,
            "origin": "LAX",
            "destination": "NRT",
            "airline": "japan_airlines",
            "departure_time": "2024-12-01T10:00:00Z",
            "arrival_time": "2024-12-01T22:00:00Z",
            "price": 1200.00,
            "search_timestamp": "2024-11-01T09:00:00Z",
            "data_source": "duffel",
            "booking_status": "viewed"
        }
        """
        flight = Flight.model_validate_json(json_string)
        assert flight.origin == "LAX"
        assert flight.destination == "NRT"
        assert flight.airline == AirlineProvider.JAPAN_AIRLINES
        assert flight.price == 1200.00

    def test_flight_model_validate_json_invalid(self):
        """Test model_validate_json with invalid JSON."""
        invalid_json = '{"trip_id": 1, "origin": "INVALID_CODE"}'
        with pytest.raises(
            ValidationError, match="Airport code must be a 3-letter IATA code"
        ):
            Flight.model_validate_json(invalid_json)

    def test_flight_serialization_round_trip(self, sample_flight_dict):
        """Test serialization and deserialization round trip."""
        original_flight = Flight(**sample_flight_dict)

        # Test model_dump -> model_validate round trip
        dumped_dict = original_flight.model_dump()
        reconstructed_flight = Flight.model_validate(dumped_dict)

        assert original_flight.origin == reconstructed_flight.origin
        assert original_flight.destination == reconstructed_flight.destination
        assert original_flight.airline == reconstructed_flight.airline
        assert original_flight.price == reconstructed_flight.price

        # Test model_dump_json -> model_validate_json round trip
        json_string = original_flight.model_dump_json()
        json_reconstructed_flight = Flight.model_validate_json(json_string)

        assert original_flight.origin == json_reconstructed_flight.origin
        assert original_flight.destination == json_reconstructed_flight.destination
        assert original_flight.airline == json_reconstructed_flight.airline
        assert original_flight.price == json_reconstructed_flight.price

    def test_direct_validator_functions(self):
        """Test direct validator function calls."""
        from tripsage_core.models.db.flight import Flight

        # Test validate_airport_code directly
        assert Flight.validate_airport_code("LAX") == "LAX"
        assert (
            Flight.validate_airport_code("lax") == "LAX"
        )  # Should convert to uppercase

        with pytest.raises(
            ValueError, match="Airport code must be a 3-letter IATA code"
        ):
            Flight.validate_airport_code("INVALID")

        with pytest.raises(
            ValueError, match="Airport code must be a 3-letter IATA code"
        ):
            Flight.validate_airport_code("12")

        # Test validate_price directly
        assert Flight.validate_price(1200.00) == 1200.00
        assert Flight.validate_price(0.01) == 0.01

        with pytest.raises(ValueError, match="ensure this value is greater than 0"):
            Flight.validate_price(-100.00)

        # Test validate_segment_number directly
        assert Flight.validate_segment_number(1) == 1
        assert Flight.validate_segment_number(5) == 5

        with pytest.raises(ValueError, match="Segment number must be positive"):
            Flight.validate_segment_number(0)

        with pytest.raises(ValueError, match="Segment number must be positive"):
            Flight.validate_segment_number(-1)

    def test_model_validator_same_airports(self):
        """Test model validator for same origin and destination."""
        now = datetime.now(timezone.utc)
        with pytest.raises(
            ValidationError, match="Origin and destination must be different"
        ):
            Flight(
                trip_id=1,
                origin="LAX",
                destination="LAX",  # Same as origin
                airline=AirlineProvider.JAPAN_AIRLINES,
                departure_time=now + timedelta(days=10),
                arrival_time=now + timedelta(days=10, hours=12),
                price=1200.00,
                search_timestamp=now,
                data_source=DataSource.DUFFEL,
            )

    @pytest.mark.parametrize(
        "string_price,expected_price",
        [
            ("1200.00", 1200.00),
            ("0.01", 0.01),
            ("10000", 10000.00),
        ],
    )
    def test_type_coercion_price(self, string_price, expected_price):
        """Test type coercion for price field (string to float)."""
        now = datetime.now(timezone.utc)
        flight = Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=string_price,  # Pass string that should be coerced to float
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.price == expected_price
        assert isinstance(flight.price, float)

    @pytest.mark.parametrize(
        "string_trip_id,expected_trip_id",
        [
            ("1", 1),
            ("123", 123),
        ],
    )
    def test_type_coercion_trip_id(self, string_trip_id, expected_trip_id):
        """Test type coercion for trip_id field (string to int)."""
        now = datetime.now(timezone.utc)
        flight = Flight(
            trip_id=string_trip_id,  # Pass string that should be coerced to int
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.trip_id == expected_trip_id
        assert isinstance(flight.trip_id, int)

    def test_edge_cases_boundary_values(self):
        """Test edge cases and boundary values."""
        now = datetime.now(timezone.utc)

        # Test minimum valid price
        flight = Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=0.01,  # Minimum valid price
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.price == 0.01

        # Test very large price
        flight = Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now + timedelta(days=10),
            arrival_time=now + timedelta(days=10, hours=12),
            price=999999.99,  # Very large price
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.price == 999999.99

        # Test very short flight duration (1 minute)
        flight = Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now,
            arrival_time=now + timedelta(minutes=1),  # Very short flight
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.duration.total_seconds() == 60
        assert flight.formatted_duration == "0h 1m"

        # Test very long flight duration (24 hours)
        flight = Flight(
            trip_id=1,
            origin="LAX",
            destination="NRT",
            airline=AirlineProvider.JAPAN_AIRLINES,
            departure_time=now,
            arrival_time=now + timedelta(hours=24),  # Very long flight
            price=1200.00,
            search_timestamp=now,
            data_source=DataSource.DUFFEL,
        )
        assert flight.duration.total_seconds() == 24 * 3600
        assert flight.formatted_duration == "24h 0m"
