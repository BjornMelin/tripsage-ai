"""Tests for Accommodation model."""

import pytest
from datetime import date, timedelta
from tripsage.models.db.accommodation import (
    Accommodation, 
    AccommodationType, 
    BookingStatus,
    CancellationPolicy
)
from pydantic import ValidationError


def test_accommodation_creation(sample_accommodation_dict):
    """Test creating an Accommodation model with valid data."""
    accommodation = Accommodation(**sample_accommodation_dict)
    assert accommodation.id == 1
    assert accommodation.trip_id == 1
    assert accommodation.name == "Grand Hyatt Tokyo"
    assert accommodation.type == AccommodationType.HOTEL
    assert accommodation.price_per_night == 250.00
    assert accommodation.total_price == 1750.00
    assert accommodation.booking_status == BookingStatus.VIEWED
    assert accommodation.cancellation_policy == CancellationPolicy.FLEXIBLE


def test_accommodation_optional_fields():
    """Test creating an Accommodation model with minimal required fields."""
    today = date.today()
    minimal_accommodation = Accommodation(
        trip_id=1,
        name="Grand Hyatt Tokyo",
        type=AccommodationType.HOTEL,
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
    assert minimal_accommodation.booking_status == BookingStatus.VIEWED  # Default value
    assert minimal_accommodation.cancellation_policy == CancellationPolicy.UNKNOWN  # Default value
    assert minimal_accommodation.images == []  # Default value


def test_accommodation_validation_dates():
    """Test date validation."""
    today = date.today()
    
    # Test check_out before check_in
    with pytest.raises(ValidationError) as excinfo:
        Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=17),  # Later date
            check_out=today + timedelta(days=10),  # Earlier date
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
        )
    assert "Check-out date must be after check-in date" in str(excinfo.value)


def test_accommodation_validation_price():
    """Test price validation."""
    today = date.today()
    
    # Test negative price_per_night
    with pytest.raises(ValidationError) as excinfo:
        Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=-250.00,  # Negative price
            total_price=1750.00,
            location="Tokyo, Japan",
        )
    assert "ensure this value is greater than 0" in str(excinfo.value)
    
    # Test negative total_price
    with pytest.raises(ValidationError) as excinfo:
        Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=-1750.00,  # Negative price
            location="Tokyo, Japan",
        )
    assert "ensure this value is greater than 0" in str(excinfo.value)


def test_accommodation_validation_rating():
    """Test rating validation."""
    today = date.today()
    
    # Test rating above 5.0
    with pytest.raises(ValidationError) as excinfo:
        Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
            rating=5.5,  # Above maximum
        )
    assert "ensure this value is less than or equal to 5" in str(excinfo.value)
    
    # Test rating below 0.0
    with pytest.raises(ValidationError) as excinfo:
        Accommodation(
            trip_id=1,
            name="Grand Hyatt Tokyo",
            type=AccommodationType.HOTEL,
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=17),
            price_per_night=250.00,
            total_price=1750.00,
            location="Tokyo, Japan",
            rating=-1.0,  # Below minimum
        )
    assert "ensure this value is greater than or equal to 0" in str(excinfo.value)


def test_accommodation_stay_duration(sample_accommodation_dict):
    """Test the stay_duration property."""
    accommodation = Accommodation(**sample_accommodation_dict)
    assert accommodation.stay_duration == 7


def test_accommodation_is_booked_property(sample_accommodation_dict):
    """Test the is_booked property."""
    accommodation = Accommodation(**sample_accommodation_dict)
    assert accommodation.is_booked is False
    
    accommodation.booking_status = BookingStatus.BOOKED
    assert accommodation.is_booked is True


def test_accommodation_is_canceled_property(sample_accommodation_dict):
    """Test the is_canceled property."""
    accommodation = Accommodation(**sample_accommodation_dict)
    assert accommodation.is_canceled is False
    
    accommodation.booking_status = BookingStatus.CANCELED
    assert accommodation.is_canceled is True


def test_accommodation_book(sample_accommodation_dict):
    """Test booking an accommodation."""
    accommodation = Accommodation(**sample_accommodation_dict)
    accommodation.book()
    assert accommodation.booking_status == BookingStatus.BOOKED


def test_accommodation_cancel(sample_accommodation_dict):
    """Test canceling an accommodation."""
    # First book it
    accommodation = Accommodation(**sample_accommodation_dict)
    accommodation.book()
    
    # Now cancel it
    accommodation.cancel()
    assert accommodation.booking_status == BookingStatus.CANCELED
    
    # Cannot cancel a viewed accommodation
    accommodation = Accommodation(**sample_accommodation_dict)
    with pytest.raises(ValueError) as excinfo:
        accommodation.cancel()
    assert "Only booked accommodations can be canceled" in str(excinfo.value)


def test_accommodation_has_flexible_cancellation(sample_accommodation_dict):
    """Test the has_flexible_cancellation property."""
    accommodation = Accommodation(**sample_accommodation_dict)
    assert accommodation.has_flexible_cancellation is True
    
    accommodation.cancellation_policy = CancellationPolicy.STRICT
    assert accommodation.has_flexible_cancellation is False


def test_accommodation_is_refundable(sample_accommodation_dict):
    """Test the is_refundable property."""
    accommodation = Accommodation(**sample_accommodation_dict)
    assert accommodation.is_refundable is True
    
    accommodation.cancellation_policy = CancellationPolicy.NON_REFUNDABLE
    assert accommodation.is_refundable is False


def test_accommodation_total_price_calculation():
    """Test the automatic calculation of total_price."""
    today = date.today()
    
    accommodation = Accommodation(
        trip_id=1,
        name="Grand Hyatt Tokyo",
        type=AccommodationType.HOTEL,
        check_in=today + timedelta(days=10),
        check_out=today + timedelta(days=17),
        price_per_night=250.00,
        total_price=0.0,  # We'll let it calculate this
        location="Tokyo, Japan",
        calculate_total_price=True,  # Tell it to calculate
    )
    
    expected_total = 250.00 * 7  # 7 nights at $250 per night
    assert accommodation.total_price == expected_total


def test_accommodation_model_dump(sample_accommodation_dict):
    """Test model_dump method."""
    accommodation = Accommodation(**sample_accommodation_dict)
    accommodation_dict = accommodation.model_dump()
    
    assert accommodation_dict["name"] == "Grand Hyatt Tokyo"
    assert accommodation_dict["type"] == AccommodationType.HOTEL
    assert accommodation_dict["price_per_night"] == 250.00
    assert accommodation_dict["booking_status"] == BookingStatus.VIEWED
    assert accommodation_dict["cancellation_policy"] == CancellationPolicy.FLEXIBLE