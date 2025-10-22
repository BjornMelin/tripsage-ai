"""Tests for flight models.

Tests validation, serialization, and business logic for flight-related models.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tests.factories import FlightFactory
from tripsage_core.models.db.flight import Flight
from tripsage_core.models.schemas_common.enums import (
    AirlineProvider,
    BookingStatus,
    DataSource,
)


class TestFlightModel:
    """Test suite for Flight model validation and functionality."""

    def test_flight_creation_basic(self, sample_flight_dict):
        """Test basic flight creation with valid data."""
        flight = Flight(**sample_flight_dict)

        assert flight.origin == "LAX"
        assert flight.destination == "NRT"
        assert flight.airline == AirlineProvider.JAPAN_AIRLINES
        assert flight.price == 1200.00
        assert flight.segment_number == 1

    def test_flight_factory_data(self):
        """Test flight creation using factory."""
        data = FlightFactory.create()
        flight = Flight(**data)

        assert flight.origin == "LAX"
        assert flight.destination == "NRT"
        assert flight.booking_status == BookingStatus.VIEWED
        assert flight.data_source == DataSource.DUFFEL

    @pytest.mark.parametrize(
        "airline",
        [
            AirlineProvider.AMERICAN,
            AirlineProvider.DELTA,
            AirlineProvider.UNITED,
            AirlineProvider.JAPAN_AIRLINES,
            AirlineProvider.LUFTHANSA,
            AirlineProvider.BRITISH_AIRWAYS,
            AirlineProvider.AIR_FRANCE,
        ],
    )
    def test_flight_airlines_valid(self, sample_flight_dict, airline):
        """Test all valid airline providers."""
        sample_flight_dict["airline"] = airline
        flight = Flight(**sample_flight_dict)
        assert flight.airline == airline

    @pytest.mark.parametrize(
        "price,should_pass",
        [
            (0.01, True),  # Minimum valid price
            (50.00, True),  # Low price
            (1500.00, True),  # High price
            (99999.99, True),  # Very high price
            (0.00, False),  # Zero price should fail
            (-1.00, False),  # Negative price should fail
            (-0.01, False),  # Small negative should fail
        ],
    )
    def test_flight_price_validation(
        self, sample_flight_dict, price, should_pass, validation_helper
    ):
        """Test price validation with boundary values."""
        sample_flight_dict["price"] = price

        if should_pass:
            flight = Flight(**sample_flight_dict)
            assert flight.price == price
        else:
            validation_helper.assert_validation_error(
                Flight, sample_flight_dict, error_field="price"
            )

    def test_flight_datetime_validation(self, sample_flight_dict):
        """Test departure and arrival time validation."""
        now = datetime.now(UTC)
        departure = now + timedelta(hours=2)
        arrival = departure + timedelta(hours=12)

        sample_flight_dict.update(
            {
                "departure_time": departure,
                "arrival_time": arrival,
            }
        )

        flight = Flight(**sample_flight_dict)
        assert flight.departure_time == departure
        assert flight.arrival_time == arrival

    def test_flight_datetime_logical_validation(self, sample_flight_dict):
        """Test that arrival time must be after departure time."""
        now = datetime.now(UTC)
        departure = now + timedelta(hours=12)
        arrival = now + timedelta(hours=2)  # Before departure

        sample_flight_dict.update(
            {
                "departure_time": departure,
                "arrival_time": arrival,
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            Flight(**sample_flight_dict)

        errors = exc_info.value.errors()
        assert any("arrival_time" in str(error) for error in errors)

    def test_flight_duration_calculation(self, sample_flight_dict):
        """Test flight duration calculation."""
        now = datetime.now(UTC)
        departure = now + timedelta(hours=2)
        arrival = departure + timedelta(hours=8, minutes=30)  # 8.5 hour flight

        sample_flight_dict.update(
            {
                "departure_time": departure,
                "arrival_time": arrival,
            }
        )

        flight = Flight(**sample_flight_dict)
        assert flight.duration_minutes == 510  # 8.5 hours = 510 minutes

    def test_flight_airport_codes_validation(
        self, sample_flight_dict, validation_helper
    ):
        """Test airport code validation."""
        # Test invalid origin codes
        invalid_codes = ["", "A", "AB", "ABCD", "123", "ab1"]

        for invalid_code in invalid_codes:
            test_data = sample_flight_dict.copy()
            test_data["origin"] = invalid_code
            validation_helper.assert_validation_error(
                Flight, test_data, error_field="origin"
            )

        # Test valid codes (make sure origin and destination are different)
        valid_codes = ["LAX", "JFK", "LHR", "CDG", "SFO"]
        sample_flight_dict["destination"] = "NRT"  # Keep destination constant
        for valid_code in valid_codes:
            test_data = sample_flight_dict.copy()
            test_data["origin"] = valid_code
            flight = Flight(**test_data)
            assert flight.origin == valid_code

    @pytest.mark.parametrize("booking_status", list(BookingStatus))
    def test_flight_booking_statuses(self, sample_flight_dict, booking_status):
        """Test all booking status options."""
        sample_flight_dict["booking_status"] = booking_status
        flight = Flight(**sample_flight_dict)
        assert flight.booking_status == booking_status

    @pytest.mark.parametrize("data_source", list(DataSource))
    def test_flight_data_sources(self, sample_flight_dict, data_source):
        """Test all data source options."""
        sample_flight_dict["data_source"] = data_source
        flight = Flight(**sample_flight_dict)
        assert flight.data_source == data_source

    def test_flight_serialization_round_trip(
        self, sample_flight_dict, serialization_helper
    ):
        """Test JSON serialization and deserialization."""
        flight = Flight(**sample_flight_dict)

        # Test JSON round trip
        reconstructed = serialization_helper.test_json_round_trip(flight)
        assert reconstructed.origin == flight.origin
        assert reconstructed.destination == flight.destination
        assert reconstructed.price == flight.price

        # Test dict round trip
        reconstructed = serialization_helper.test_dict_round_trip(flight)
        assert reconstructed.airline == flight.airline

    def test_flight_booking_workflow(self, sample_flight_dict):
        """Test flight booking state transitions."""
        flight = Flight(**sample_flight_dict)

        # Test initial state
        assert flight.booking_status == BookingStatus.VIEWED
        assert not flight.is_booked
        assert not flight.is_canceled

        # Test booking
        flight.book()
        assert flight.booking_status == BookingStatus.BOOKED
        assert flight.is_booked

        # Test cancellation
        flight.cancel()
        assert flight.booking_status == BookingStatus.CANCELLED
        assert flight.is_canceled

    def test_flight_factory_variations(self):
        """Test factory method variations."""
        # Test return flight factory
        return_flight_data = FlightFactory.create_return_flight()
        return_flight = Flight(**return_flight_data)
        assert return_flight.origin == "NRT"
        assert return_flight.destination == "LAX"
        assert return_flight.segment_number == 2

        # Test domestic flight factory
        domestic_data = FlightFactory.create_domestic_flight()
        domestic = Flight(**domestic_data)
        assert domestic.origin == "LAX"
        assert domestic.destination == "SFO"
        assert domestic.airline == AirlineProvider.AMERICAN

    def test_flight_segment_number_validation(
        self, sample_flight_dict, validation_helper
    ):
        """Test segment number validation."""
        # Test invalid segment numbers
        invalid_segments = [0, -1, -10]

        for invalid_segment in invalid_segments:
            sample_flight_dict["segment_number"] = invalid_segment
            validation_helper.assert_validation_error(
                Flight, sample_flight_dict, error_field="segment_number"
            )

        # Test valid segment numbers
        valid_segments = [1, 2, 3, 10]
        for valid_segment in valid_segments:
            sample_flight_dict["segment_number"] = valid_segment
            flight = Flight(**sample_flight_dict)
            assert flight.segment_number == valid_segment

    def test_flight_trip_id_validation(self, sample_flight_dict, validation_helper):
        """Test trip_id validation."""
        # Test invalid trip IDs
        # Note: trip_id doesn't have specific validation in the model
        # It accepts any integer value including negative numbers
        valid_ids = [0, -1, -10, 1, 100, 9999]

        for valid_id in valid_ids:
            sample_flight_dict["trip_id"] = valid_id
            flight = Flight(**sample_flight_dict)
            assert flight.trip_id == valid_id

    def test_flight_edge_cases(self, sample_flight_dict, edge_case_data):
        """Test edge case values."""
        # Test minimum price
        sample_flight_dict["price"] = edge_case_data["min_price"]
        flight = Flight(**sample_flight_dict)
        assert flight.price == edge_case_data["min_price"]

        # Test maximum price
        sample_flight_dict["price"] = edge_case_data["max_price"]
        flight = Flight(**sample_flight_dict)
        assert flight.price == edge_case_data["max_price"]

    def test_flight_decimal_precision(self, sample_flight_dict):
        """Test price precision handling."""
        # Test with high precision decimal
        sample_flight_dict["price"] = Decimal("1199.999")

        flight = Flight(**sample_flight_dict)
        # Should handle decimal precision appropriately
        assert isinstance(flight.price, (float, Decimal))
        assert flight.price > 1199.99

    def test_flight_search_timestamp_handling(self, sample_flight_dict):
        """Test search timestamp field."""
        now = datetime.now(UTC)
        sample_flight_dict["search_timestamp"] = now

        flight = Flight(**sample_flight_dict)
        assert flight.search_timestamp == now

        # Test that search timestamp can be in the past
        past_time = now - timedelta(days=1)
        sample_flight_dict["search_timestamp"] = past_time
        flight = Flight(**sample_flight_dict)
        assert flight.search_timestamp == past_time

    def test_flight_optional_fields(self, sample_flight_dict):
        """Test that optional fields can be None or omitted."""
        # booking_link is the only optional field in Flight model
        optional_fields = ["booking_link"]

        for field in optional_fields:
            test_data = sample_flight_dict.copy()
            test_data[field] = None
            flight = Flight(**test_data)
            assert getattr(flight, field) is None

            # Test omitting the field entirely
            test_data = sample_flight_dict.copy()
            if field in test_data:
                del test_data[field]
            flight = Flight(**test_data)
            assert getattr(flight, field) is None

    def test_flight_business_logic_methods(self, sample_flight_dict):
        """Test business logic methods."""
        flight = Flight(**sample_flight_dict)

        # Test booking workflow
        assert not flight.is_booked
        flight.book()
        assert flight.is_booked
        assert flight.booking_status == BookingStatus.BOOKED

        # Test cancellation workflow
        flight.cancel()
        assert flight.is_canceled
        assert flight.booking_status == BookingStatus.CANCELLED

    def test_flight_timezone_handling(self, sample_flight_dict):
        """Test timezone-aware datetime handling."""
        # Test with different timezones
        utc_time = datetime.now(UTC)

        sample_flight_dict.update(
            {
                "departure_time": utc_time,
                "arrival_time": utc_time + timedelta(hours=8),
            }
        )

        flight = Flight(**sample_flight_dict)
        assert flight.departure_time.tzinfo is not None
        assert flight.arrival_time.tzinfo is not None

    @pytest.mark.parametrize(
        "field_name,invalid_value,expected_error",
        [
            ("origin", "ab", "3-letter IATA code"),
            ("destination", "ABCD", "3-letter IATA code"),
            ("price", 0, "greater than 0"),
            ("price", -10, "greater than 0"),
            ("segment_number", 0, "must be positive"),
            ("segment_number", -1, "must be positive"),
        ],
    )
    def test_flight_field_validation(
        self,
        sample_flight_dict,
        field_name,
        invalid_value,
        expected_error,
        validation_helper,
    ):
        """Test individual field validation rules."""
        sample_flight_dict[field_name] = invalid_value
        validation_helper.assert_validation_error(
            Flight, sample_flight_dict, error_field=field_name
        )
