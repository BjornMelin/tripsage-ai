"""Comprehensive tests for Accommodation model following Pydantic v2 best practices."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.accommodation import Accommodation
from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    BookingStatus,
    CancellationPolicy,
)


class TestAccommodationModel:
    """Accommodation model testing following Pydantic v2 best practices."""

    def test_accommodation_creation(self, sample_accommodation_dict):
        """Test creating an Accommodation model with valid data."""
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.id == 1
        assert accommodation.trip_id == 1
        assert accommodation.name == "Grand Hyatt Tokyo"
        assert accommodation.accommodation_type == AccommodationType.HOTEL
        assert accommodation.price_per_night == 250.00
        assert accommodation.total_price == 1750.00
        assert accommodation.booking_status == BookingStatus.VIEWED
        assert accommodation.cancellation_policy == CancellationPolicy.FLEXIBLE

    def test_accommodation_optional_fields(self):
        """Test creating an Accommodation model with minimal required fields."""
        today = date.today()
        minimal_accommodation = Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
        )

        assert minimal_accommodation.trip_id == 1
        assert minimal_accommodation.id is None
        assert minimal_accommodation.rating is None
        assert minimal_accommodation.amenities is None
        assert minimal_accommodation.booking_link is None
        assert (
            minimal_accommodation.booking_status == BookingStatus.VIEWED
        )  # Default value
        assert (
            minimal_accommodation.cancellation_policy == CancellationPolicy.UNKNOWN
        )  # Default value
        assert minimal_accommodation.images == []  # Default value

    def test_accommodation_validation_dates(self):
        """Test date validation."""
        today = date.today()

        # Test check_out before check_in with specific error message
        with pytest.raises(
            ValidationError, match="Check-out date must be after check-in date"
        ):
            Accommodation(
                trip_id=1,
                name="Grand Hyatt Tokyo",
                accommodation_type=AccommodationType.HOTEL,
                check_in=today + timedelta(days=17),  # Later date
                check_out=today + timedelta(days=10),  # Earlier date
                price_per_night=250.00,
                total_price=1750.00,
                location="Tokyo, Japan",
            )

    @pytest.mark.parametrize(
        "price_field,invalid_price,expected_error",
        [
            ("price_per_night", -250.00, "ensure this value is greater than 0"),
            ("total_price", -1750.00, "ensure this value is greater than 0"),
            ("price_per_night", -0.01, "ensure this value is greater than 0"),
            ("total_price", -0.01, "ensure this value is greater than 0"),
        ],
    )
    def test_accommodation_validation_price_parametrized(
        self, price_field, invalid_price, expected_error
    ):
        """Test price validation with parameterized inputs."""
        today = date.today()
        kwargs = {
            "trip_id": 1,
            "name": "Grand Hyatt Tokyo",
            "accommodation_type": AccommodationType.HOTEL,
            "check_in": today + timedelta(days=10),
            "check_out": today + timedelta(days=17),
            "price_per_night": 250.00,
            "total_price": 1750.00,
            "location": "Tokyo, Japan",
        }
        kwargs[price_field] = invalid_price

        with pytest.raises(ValidationError, match=expected_error):
            Accommodation(**kwargs)

    @pytest.mark.parametrize(
        "invalid_rating,expected_error",
        [
            (5.5, "ensure this value is less than or equal to 5"),
            (-1.0, "ensure this value is greater than or equal to 0"),
            (6.0, "ensure this value is less than or equal to 5"),
            (-0.1, "ensure this value is greater than or equal to 0"),
        ],
    )
    def test_accommodation_validation_rating_parametrized(
        self, invalid_rating, expected_error
    ):
        """Test rating validation with parameterized inputs."""
        today = date.today()
        with pytest.raises(ValidationError, match=expected_error):
            Accommodation(
                trip_id=1,
                name="Grand Hyatt Tokyo",
                accommodation_type=AccommodationType.HOTEL,
                check_in=today + timedelta(days=10),
                check_out=today + timedelta(days=17),
                price_per_night=250.00,
                total_price=1750.00,
                location="Tokyo, Japan",
                rating=invalid_rating,
            )

    @pytest.mark.parametrize(
        "valid_rating",
        [
            0.0,  # Minimum valid
            2.5,  # Middle value
            5.0,  # Maximum valid
            None,  # Optional value
        ],
    )
    def test_accommodation_validation_rating_valid(self, valid_rating):
        """Test valid rating values."""
        today = date.today()
        accommodation = Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
            rating=valid_rating,
        )
        assert accommodation.rating == valid_rating

    def test_accommodation_stay_duration(self, sample_accommodation_dict):
        """Test the stay_duration property."""
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.stay_duration == 7

    def test_accommodation_is_booked_property(self, sample_accommodation_dict):
        """Test the is_booked property."""
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.is_booked is False

        accommodation.booking_status = BookingStatus.BOOKED
        assert accommodation.is_booked is True

    def test_accommodation_is_canceled_property(self, sample_accommodation_dict):
        """Test the is_canceled property."""
        accommodation = Accommodation(**sample_accommodation_dict)
        assert accommodation.is_canceled is False

        accommodation.booking_status = BookingStatus.CANCELLED
        assert accommodation.is_canceled is True

    def test_accommodation_book(self, sample_accommodation_dict):
        """Test booking an accommodation."""
        accommodation = Accommodation(**sample_accommodation_dict)
        accommodation.book()
        assert accommodation.booking_status == BookingStatus.BOOKED

    def test_accommodation_cancel(self, sample_accommodation_dict):
        """Test canceling an accommodation."""
        accommodation = Accommodation(**sample_accommodation_dict)
        accommodation.book()
        accommodation.cancel()
        assert accommodation.booking_status == BookingStatus.CANCELLED

        # Cannot cancel a viewed accommodation with specific error message
        accommodation = Accommodation(**sample_accommodation_dict)
        with pytest.raises(
            ValueError, match="Only booked accommodations can be cancelled"
        ):
            accommodation.cancel()

    def test_accommodation_model_validate_json(self):
        """Test model_validate_json method with JSON string input."""
        json_string = """
        {
            "trip_id": 1,
            "name": "Grand Hyatt Tokyo",
            "accommodation_type": "hotel",
            "check_in": "2024-12-10",
            "check_out": "2024-12-17",
            "price_per_night": 250.00,
            "total_price": 1750.00,
            "location": "Tokyo, Japan",
            "rating": 4.5,
            "booking_status": "viewed",
            "cancellation_policy": "flexible"
        }
        """
        accommodation = Accommodation.model_validate_json(json_string)
        assert accommodation.name == "Grand Hyatt Tokyo"
        assert accommodation.accommodation_type == AccommodationType.HOTEL
        assert accommodation.rating == 4.5
        assert accommodation.price_per_night == 250.00

    def test_accommodation_model_validate_json_invalid(self):
        """Test model_validate_json with invalid JSON."""
        invalid_json = '{"trip_id": 1, "rating": 6.0}'  # Invalid rating
        with pytest.raises(
            ValidationError, match="ensure this value is less than or equal to 5"
        ):
            Accommodation.model_validate_json(invalid_json)

    def test_accommodation_serialization_round_trip(self, sample_accommodation_dict):
        """Test serialization and deserialization round trip."""
        original_accommodation = Accommodation(**sample_accommodation_dict)

        # Test model_dump -> model_validate round trip
        dumped_dict = original_accommodation.model_dump()
        reconstructed_accommodation = Accommodation.model_validate(dumped_dict)

        assert original_accommodation.name == reconstructed_accommodation.name
        assert (
            original_accommodation.accommodation_type
            == reconstructed_accommodation.accommodation_type
        )
        assert (
            original_accommodation.price_per_night
            == reconstructed_accommodation.price_per_night
        )
        assert (
            original_accommodation.total_price
            == reconstructed_accommodation.total_price
        )

        # Test model_dump_json -> model_validate_json round trip
        json_string = original_accommodation.model_dump_json()
        json_reconstructed_accommodation = Accommodation.model_validate_json(
            json_string
        )

        assert original_accommodation.name == json_reconstructed_accommodation.name
        assert (
            original_accommodation.accommodation_type
            == json_reconstructed_accommodation.accommodation_type
        )
        assert (
            original_accommodation.price_per_night
            == json_reconstructed_accommodation.price_per_night
        )
        assert (
            original_accommodation.total_price
            == json_reconstructed_accommodation.total_price
        )

    def test_direct_validator_functions(self):
        """Test direct validator function calls."""
        from tripsage_core.models.db.accommodation import Accommodation

        # Test validate_price directly
        assert Accommodation.validate_price(250.00) == 250.00
        assert Accommodation.validate_price(0.01) == 0.01

        with pytest.raises(ValueError, match="ensure this value is greater than 0"):
            Accommodation.validate_price(-100.00)

        # Test validate_rating directly
        assert Accommodation.validate_rating(4.5) == 4.5
        assert Accommodation.validate_rating(None) is None
        assert Accommodation.validate_rating(0.0) == 0.0
        assert Accommodation.validate_rating(5.0) == 5.0

        with pytest.raises(
            ValueError, match="ensure this value is greater than or equal to 0"
        ):
            Accommodation.validate_rating(-1.0)

        with pytest.raises(
            ValueError, match="ensure this value is less than or equal to 5"
        ):
            Accommodation.validate_rating(5.5)

        # Test validate_distance directly
        assert Accommodation.validate_distance(10.5) == 10.5
        assert Accommodation.validate_distance(None) is None
        assert Accommodation.validate_distance(0.0) == 0.0

        with pytest.raises(ValueError, match="Distance must be non-negative"):
            Accommodation.validate_distance(-5.0)

    @pytest.mark.parametrize(
        "string_price,expected_price",
        [
            ("250.00", 250.00),
            ("0.01", 0.01),
            ("1750", 1750.00),
        ],
    )
    def test_type_coercion_price(self, string_price, expected_price):
        """Test type coercion for price fields (string to float)."""
        today = date.today()
        accommodation = Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=string_price,  # Pass string that should be coerced to float
            total_price=expected_price * 7,  # 7 nights
            location="Tokyo, Japan",
        )
        assert accommodation.price_per_night == expected_price
        assert isinstance(accommodation.price_per_night, float)

    @pytest.mark.parametrize(
        "string_trip_id,expected_trip_id",
        [
            ("1", 1),
            ("123", 123),
        ],
    )
    def test_type_coercion_trip_id(self, string_trip_id, expected_trip_id):
        """Test type coercion for trip_id field (string to int)."""
        today = date.today()
        accommodation = Accommodation(
            trip_id=string_trip_id,  # Pass string that should be coerced to int
            name="Grand Hyatt Tokyo",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
        )
        assert accommodation.trip_id == expected_trip_id
        assert isinstance(accommodation.trip_id, int)

    def test_edge_cases_boundary_values(self):
        """Test edge cases and boundary values."""
        today = date.today()

        # Test minimum valid price
        accommodation = Accommodation(
            trip_id=1,
            name="Budget Hostel",
            accommodation_type=AccommodationType.HOSTEL,
            check_in=today + timedelta(days=1),
            check_out=today + timedelta(days=2),  # 1 night stay
            price_per_night=0.01,  # Minimum valid price
            total_price=0.01,
            location="Budget Location",
        )
        assert accommodation.price_per_night == 0.01
        assert accommodation.stay_duration == 1

        # Test very large price
        accommodation = Accommodation(
            trip_id=1,
            name="Luxury Resort",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=9999.99,  # Very large price
            total_price=69999.93,
            location="Exclusive Location",
        )
        assert accommodation.price_per_night == 9999.99

        # Test boundary rating values
        accommodation = Accommodation(
            trip_id=1,
            name="Perfect Hotel",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
            rating=5.0,  # Maximum valid rating
        )
        assert accommodation.rating == 5.0

        accommodation = Accommodation(
            trip_id=1,
            name="New Hotel",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
            rating=0.0,  # Minimum valid rating
        )
        assert accommodation.rating == 0.0

    def test_auto_calculate_total_price(self):
        """Test automatic total price calculation feature."""
        today = date.today()
        accommodation = Accommodation(
            trip_id=1,
            name="Auto-Calc Hotel",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),  # 7 nights
            price_per_night=100.00,
            total_price=0.00,  # Will be overridden
            location="Tokyo, Japan",
            calculate_total_price=True,
        )
        assert accommodation.total_price == 700.00  # 7 nights * 100.00

    def test_accommodation_properties(self, sample_accommodation_dict):
        """Test various accommodation properties."""
        accommodation = Accommodation(**sample_accommodation_dict)

        # Test duration-related properties
        assert accommodation.duration_nights == 7
        assert accommodation.stay_duration == 7

        # Test price-related properties (approx comparison for floating point)
        assert abs(accommodation.price_with_taxes - 1925.00) < 0.01  # 1750 * 1.1

        # Test status properties
        assert accommodation.is_active is True
        assert accommodation.is_booked is False
        assert accommodation.is_canceled is False

        # Test cancellation policy properties
        accommodation.cancellation_policy = CancellationPolicy.FREE
        assert accommodation.has_free_cancellation is True
        assert accommodation.has_flexible_cancellation is False
        assert accommodation.is_refundable is True

        accommodation.cancellation_policy = CancellationPolicy.FLEXIBLE
        assert accommodation.has_free_cancellation is False
        assert accommodation.has_flexible_cancellation is True
        assert accommodation.is_refundable is True

        accommodation.cancellation_policy = CancellationPolicy.NO_REFUND
        assert accommodation.has_free_cancellation is False
        assert accommodation.has_flexible_cancellation is False
        assert accommodation.is_refundable is False

    def test_amenities_list_property(self):
        """Test amenities_list property with different formats."""
        today = date.today()

        # Test with dict containing 'list' key
        accommodation = Accommodation(
            trip_id=1,
            name="Hotel with Amenities",
            accommodation_type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
            amenities={"list": ["wifi", "pool", "gym"]},
        )
        assert accommodation.amenities_list == ["wifi", "pool", "gym"]

        # Test with dict containing 'amenities' key
        accommodation.amenities = {"amenities": ["spa", "restaurant"]}
        assert accommodation.amenities_list == ["spa", "restaurant"]

        # Test with simple dict
        accommodation.amenities = {"wifi": True, "pool": False, "gym": True}
        assert set(accommodation.amenities_list) == {"wifi", "gym"}

        # Test with no amenities
        accommodation.amenities = None
        assert accommodation.amenities_list == []
