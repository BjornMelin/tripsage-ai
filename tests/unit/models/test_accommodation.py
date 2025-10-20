"""Comprehensive tests for accommodation models.

Tests validation, serialization, and business logic for accommodation-related models.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tests.factories import AccommodationFactory
from tripsage_core.models.db.accommodation import Accommodation
from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    BookingStatus,
    CancellationPolicy,
)


class TestAccommodationModel:
    """Test suite for Accommodation model validation and functionality."""

    def test_accommodation_creation_basic(self, sample_accommodation_dict):
        """Test basic accommodation creation with valid data."""
        accommodation = Accommodation(**sample_accommodation_dict)

        # Test that basic fields are set correctly
        assert accommodation.name is not None
        assert len(accommodation.name) > 0
        assert accommodation.accommodation_type == AccommodationType.HOTEL
        assert accommodation.price_per_night > 0
        assert accommodation.total_price > 0
        assert accommodation.location is not None
        assert len(accommodation.location) > 0

    def test_accommodation_factory_data(self):
        """Test accommodation creation using factory."""
        data = AccommodationFactory.create()
        accommodation = Accommodation(**data)

        assert accommodation.name == "Grand Hyatt Tokyo"
        assert accommodation.accommodation_type == AccommodationType.HOTEL
        assert accommodation.booking_status == BookingStatus.VIEWED

    @pytest.mark.parametrize(
        "accommodation_type",
        [
            AccommodationType.HOTEL,
            AccommodationType.APARTMENT,
            AccommodationType.HOSTEL,
            AccommodationType.RESORT,
            AccommodationType.BED_AND_BREAKFAST,
        ],
    )
    def test_accommodation_types_valid(
        self, sample_accommodation_dict, accommodation_type
    ):
        """Test all valid accommodation types."""
        sample_accommodation_dict["accommodation_type"] = accommodation_type
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.accommodation_type == accommodation_type

    @pytest.mark.parametrize(
        "price_per_night,total_price,error_field",
        [
            (-250.0, 1750.0, "price_per_night"),
            (250.0, -1750.0, "total_price"),
            (-0.01, 1750.0, "price_per_night"),
            (250.0, -0.01, "total_price"),
        ],
    )
    def test_accommodation_price_validation_negative(
        self,
        sample_accommodation_dict,
        price_per_night,
        total_price,
        error_field,
        validation_helper,
    ):
        """Test that negative prices raise validation errors."""
        sample_accommodation_dict.update(
            {
                "price_per_night": price_per_night,
                "total_price": total_price,
            }
        )

        validation_helper.assert_validation_error(
            Accommodation, sample_accommodation_dict, error_field=error_field
        )

    @pytest.mark.parametrize(
        "rating,should_pass",
        [
            (0.0, True),
            (2.5, True),
            (5.0, True),
            (5.5, False),
            (-1.0, False),
            (6.0, False),
            (-0.1, False),
            (None, True),  # Rating is optional
        ],
    )
    def test_accommodation_rating_validation(
        self, sample_accommodation_dict, rating, should_pass, validation_helper
    ):
        """Test rating validation with boundary values."""
        sample_accommodation_dict["rating"] = rating

        if should_pass:
            accommodation = Accommodation(**sample_accommodation_dict)
            assert accommodation.rating == rating
        else:
            if (rating is not None and rating > 5) or (
                rating is not None and rating < 0
            ):
                validation_helper.assert_validation_error(
                    Accommodation,
                    sample_accommodation_dict,
                    error_field="rating",
                )

    def test_accommodation_date_validation_logical(self, sample_accommodation_dict):
        """Test that check-out must be after check-in."""
        today = date.today()
        sample_accommodation_dict.update(
            {
                "check_in": today + timedelta(days=10),
                "check_out": today + timedelta(days=5),  # Before check-in
            }
        )

        with pytest.raises(ValidationError) as exc_info:
            Accommodation(**sample_accommodation_dict)

        # Should contain validation error about dates
        errors = exc_info.value.errors()
        assert any("check_out" in str(error) for error in errors)

    def test_accommodation_stay_duration_calculation(self, sample_accommodation_dict):
        """Test stay duration calculation property."""
        today = date.today()
        check_in = today + timedelta(days=10)
        check_out = today + timedelta(days=17)

        sample_accommodation_dict.update(
            {
                "check_in": check_in,
                "check_out": check_out,
            }
        )

        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.stay_duration == 7  # 7 nights

    def test_accommodation_booking_status_transitions(self, sample_accommodation_dict):
        """Test booking status state transitions."""
        accommodation = Accommodation(**sample_accommodation_dict)

        # Test initial state
        assert accommodation.booking_status == BookingStatus.VIEWED
        assert not accommodation.is_booked
        assert not accommodation.is_canceled

        # Test booking
        accommodation.book()
        assert accommodation.booking_status == BookingStatus.BOOKED
        assert accommodation.is_booked

        # Test cancellation
        accommodation.cancel()
        assert accommodation.booking_status == BookingStatus.CANCELLED
        assert accommodation.is_canceled

    def test_accommodation_amenities_handling(self, sample_accommodation_dict):
        """Test amenities list property and validation."""
        # Test with dict format (JSON storage)
        sample_accommodation_dict["amenities"] = {"list": ["wifi", "pool", "gym"]}
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.amenities_list == ["wifi", "pool", "gym"]

        # Test with empty amenities
        sample_accommodation_dict["amenities"] = {}
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.amenities_list == []

        # Test with None amenities
        sample_accommodation_dict["amenities"] = None
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.amenities_list == []

    @pytest.mark.parametrize("cancellation_policy", list(CancellationPolicy))
    def test_accommodation_cancellation_policies(
        self, sample_accommodation_dict, cancellation_policy
    ):
        """Test all cancellation policy options."""
        sample_accommodation_dict["cancellation_policy"] = cancellation_policy
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.cancellation_policy == cancellation_policy

    def test_accommodation_serialization_round_trip(
        self, sample_accommodation_dict, serialization_helper
    ):
        """Test JSON serialization and deserialization."""
        accommodation = Accommodation(**sample_accommodation_dict)

        # Test JSON round trip
        reconstructed = serialization_helper.test_json_round_trip(accommodation)
        assert reconstructed.name == accommodation.name
        assert reconstructed.price_per_night == accommodation.price_per_night
        assert reconstructed.check_in == accommodation.check_in

        # Test dict round trip
        reconstructed = serialization_helper.test_dict_round_trip(accommodation)
        assert reconstructed.total_price == accommodation.total_price

    def test_accommodation_edge_cases(self, sample_accommodation_dict, edge_case_data):
        """Test edge case values."""
        # Test minimum price
        sample_accommodation_dict.update(
            {
                "price_per_night": edge_case_data["min_price"],
                "total_price": edge_case_data["min_price"] * 7,
            }
        )
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.price_per_night == edge_case_data["min_price"]

        # Test maximum rating
        sample_accommodation_dict["rating"] = edge_case_data["max_rating"]
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.rating == edge_case_data["max_rating"]

        # Test unicode string handling
        sample_accommodation_dict["name"] = edge_case_data["unicode_string"]
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.name == edge_case_data["unicode_string"]

    def test_accommodation_decimal_precision(self, sample_accommodation_dict):
        """Test price precision handling."""
        # Test with high precision decimals
        sample_accommodation_dict.update(
            {
                "price_per_night": Decimal("249.999"),
                "total_price": Decimal("1749.993"),
            }
        )

        accommodation = Accommodation(**sample_accommodation_dict)
        # Should handle decimal precision appropriately
        assert isinstance(accommodation.price_per_night, (float, Decimal))
        assert accommodation.price_per_night > 249.99

    def test_accommodation_factory_variations(self):
        """Test factory method variations."""
        # Test Airbnb factory
        airbnb_data = AccommodationFactory.create_airbnb()
        airbnb = Accommodation(**airbnb_data)
        assert airbnb.accommodation_type == AccommodationType.APARTMENT
        assert airbnb.name == "Modern Tokyo Apartment"

        # Test hostel factory
        hostel_data = AccommodationFactory.create_hostel()
        hostel = Accommodation(**hostel_data)
        assert hostel.accommodation_type == AccommodationType.HOSTEL
        assert hostel.price_per_night == 35.00

    def test_accommodation_calculated_fields(self, sample_accommodation_dict):
        """Test calculated and derived fields."""
        accommodation = Accommodation(**sample_accommodation_dict)

        # Test calculated properties work correctly
        expected_nights = (accommodation.check_out - accommodation.check_in).days
        assert accommodation.stay_duration == expected_nights

        # Test price consistency
        if accommodation.stay_duration > 0:
            expected_total = accommodation.price_per_night * accommodation.stay_duration
            # Allow for small rounding differences
            assert abs(accommodation.total_price - expected_total) < 0.01

    @pytest.mark.parametrize(
        "field_name,invalid_value,expected_error",
        [
            ("distance_to_center", -5.0, "Distance must be non-negative"),
        ],
    )
    def test_accommodation_field_validation(
        self,
        sample_accommodation_dict,
        field_name,
        invalid_value,
        expected_error,
        validation_helper,
    ):
        """Test individual field validation rules."""
        sample_accommodation_dict[field_name] = invalid_value
        validation_helper.assert_validation_error(
            Accommodation, sample_accommodation_dict, error_field=field_name
        )

    def test_accommodation_optional_fields(self, sample_accommodation_dict):
        """Test that optional fields can be None or omitted."""
        optional_fields = [
            "rating",
            "amenities",
            "booking_link",
            "distance_to_center",
            "neighborhood",
        ]

        for field in optional_fields:
            test_data = sample_accommodation_dict.copy()
            test_data[field] = None
            accommodation = Accommodation(**test_data)
            assert getattr(accommodation, field) is None

            # Test omitting the field entirely (if it exists in the original data)
            test_data = sample_accommodation_dict.copy()
            if field in test_data:
                del test_data[field]
            accommodation = Accommodation(**test_data)
            # Should not raise an error

        # Test images field separately (it has a default factory)
        test_data = sample_accommodation_dict.copy()
        del test_data["images"]
        accommodation = Accommodation(**test_data)
        assert accommodation.images == []

    def test_accommodation_business_logic_methods(self, sample_accommodation_dict):
        """Test business logic methods."""
        accommodation = Accommodation(**sample_accommodation_dict)

        # Test booking workflow
        assert not accommodation.is_booked
        accommodation.book()
        assert accommodation.is_booked
        assert accommodation.booking_status == BookingStatus.BOOKED

        # Test cancellation workflow
        accommodation.cancel()
        assert accommodation.is_canceled
        assert accommodation.booking_status == BookingStatus.CANCELLED

        # Test that we can't cancel a non-booked accommodation
        accommodation2 = Accommodation(**sample_accommodation_dict)
        with pytest.raises(
            ValueError, match="Only booked accommodations can be cancelled"
        ):
            accommodation2.cancel()
