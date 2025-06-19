"""Test fixtures for database model tests."""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.models.db.price_history import EntityType
from tripsage_core.models.db.saved_option import OptionType
from tripsage_core.models.db.trip_collaborator import PermissionLevel
from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    AirlineProvider,
    BookingStatus,
    CancellationPolicy,
    DataSource,
    TransportationType,
    TripStatus,
    TripType,
    UserRole,
)

# Temporarily commented out until fixed
# from tripsage_core.models.db.itinerary_item import ItineraryItem, ItemType


@pytest.fixture
def sample_user_dict() -> Dict[str, Any]:
    """Return a sample user dict for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "display_name": "Test User",
        "profile_image": "https://example.com/profile.jpg",
        "role": UserRole.USER,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": datetime.now(timezone.utc),
        "preferences": {"theme": "dark", "notifications": True},
    }


@pytest.fixture
def sample_trip_dict() -> Dict[str, Any]:
    """Return a sample trip dict for testing."""
    return {
        "id": 1,
        "user_id": 1,
        "title": "Sample Trip",
        "description": "A test trip",
        "status": TripStatus.PLANNING,
        "trip_type": TripType.LEISURE,
        "start_date": date.today() + timedelta(days=10),
        "end_date": date.today() + timedelta(days=17),
        "destination": "Tokyo, Japan",
        "budget": 2500.00,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "adults": 2,
        "children": 0,
        "tags": ["vacation", "winter"],
    }


@pytest.fixture
def sample_flight_dict() -> Dict[str, Any]:
    """Return a sample flight dict for testing."""
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "trip_id": 1,
        "origin": "LAX",
        "destination": "NRT",
        "airline": AirlineProvider.JAPAN_AIRLINES,
        "departure_time": now + timedelta(days=10),
        "arrival_time": now + timedelta(days=10, hours=12),
        "price": 1200.00,
        "booking_link": "https://example.com/booking/123",
        "segment_number": 1,
        "search_timestamp": now,
        "booking_status": BookingStatus.VIEWED,
        "data_source": DataSource.DUFFEL,
        "flight_number": "JL123",
        "cabin_class": "economy",
    }


@pytest.fixture
def sample_accommodation_dict() -> Dict[str, Any]:
    """Return a sample accommodation dict for testing."""
    return {
        "id": 1,
        "trip_id": 1,
        "name": "Grand Hyatt Tokyo",
        "accommodation_type": AccommodationType.HOTEL,
        "check_in": date.today() + timedelta(days=10),
        "check_out": date.today() + timedelta(days=17),
        "price_per_night": 250.00,
        "total_price": 1750.00,
        "location": "6-10-3 Roppongi, Minato-ku, Tokyo, Japan",
        "rating": 4.7,
        "amenities": {"wifi": True, "pool": True, "breakfast": True},
        "booking_link": "https://example.com/booking/456",
        "search_timestamp": datetime.now(timezone.utc),
        "booking_status": BookingStatus.VIEWED,
        "cancellation_policy": CancellationPolicy.FLEXIBLE,
        "images": ["https://example.com/hotel1.jpg", "https://example.com/hotel2.jpg"],
    }


@pytest.fixture
def sample_search_parameters_dict() -> Dict[str, Any]:
    """Return a sample search parameters dict for testing."""
    return {
        "id": 1,
        "trip_id": 1,
        "timestamp": datetime.now(timezone.utc),
        "parameter_json": {
            "type": "flight",
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": (date.today() + timedelta(days=10)).isoformat(),
            "return_date": (date.today() + timedelta(days=17)).isoformat(),
            "adults": 2,
            "children": 0,
            "cabin_class": "economy",
            "non_stop": True,
        },
    }


@pytest.fixture
def sample_trip_note_dict() -> Dict[str, Any]:
    """Return a sample trip note dict for testing."""
    return {
        "id": 1,
        "trip_id": 1,
        "timestamp": datetime.now(timezone.utc),
        "content": "Remember to exchange currency before departure",
    }


@pytest.fixture
def sample_price_history_dict() -> Dict[str, Any]:
    """Return a sample price history dict for testing."""
    return {
        "id": 1,
        "entity_type": EntityType.FLIGHT,
        "entity_id": 1,
        "timestamp": datetime.now(timezone.utc),
        "price": 1200.00,
        "currency": "USD",
    }


@pytest.fixture
def sample_saved_option_dict() -> Dict[str, Any]:
    """Return a sample saved option dict for testing."""
    return {
        "id": 1,
        "trip_id": 1,
        "option_type": OptionType.FLIGHT,
        "option_id": 1,
        "timestamp": datetime.now(timezone.utc),
        "notes": "Best price found so far",
    }


@pytest.fixture
def sample_trip_comparison_dict() -> Dict[str, Any]:
    """Return a sample trip comparison dict for testing."""
    return {
        "id": 1,
        "trip_id": 1,
        "timestamp": datetime.now(timezone.utc),
        "comparison_json": {
            "options": [
                {
                    "id": 1,
                    "type": "flight",
                    "price": 1200.00,
                    "airline": "Japan Airlines",
                },
                {"id": 2, "type": "flight", "price": 1350.00, "airline": "ANA"},
            ],
            "criteria": ["price", "duration", "layovers"],
            "selected_option_id": 1,
        },
    }


@pytest.fixture
def sample_transportation_dict() -> Dict[str, Any]:
    """Return a sample transportation dict for testing."""
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "trip_id": 1,
        "transportation_type": TransportationType.TRAIN,
        "provider": "JR Rail",
        "pickup_date": now + timedelta(days=11),
        "dropoff_date": now + timedelta(days=11, hours=3),
        "price": 80.00,
        "notes": "Shinkansen to Kyoto",
        "booking_status": BookingStatus.VIEWED,
    }


@pytest.fixture
def sample_trip_collaborator_dict() -> Dict[str, Any]:
    """Return a sample trip collaborator dict for testing."""
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "trip_id": 123,
        "user_id": uuid4(),
        "permission_level": PermissionLevel.EDIT,
        "added_by": uuid4(),
        "added_at": now,
        "updated_at": now,
    }


class ValidationHelper:
    """Helper class for Pydantic validation testing."""
    
    def assert_validation_error(self, model_class, data_dict, field_name, expected_error_text):
        """Assert that creating a model with given data raises a ValidationError for the specified field."""
        with pytest.raises(ValidationError) as exc_info:
            model_class(**data_dict)
        
        # Check that the error is for the expected field
        errors = exc_info.value.errors()
        field_errors = [error for error in errors if error.get('loc') and field_name in error['loc']]
        
        assert field_errors, f"No validation error found for field '{field_name}'. All errors: {errors}"
        
        # Check that the error message contains expected text
        error_messages = [error['msg'] for error in field_errors]
        assert any(expected_error_text in msg for msg in error_messages), \
            f"Expected error text '{expected_error_text}' not found in error messages: {error_messages}"


class SerializationHelper:
    """Helper class for testing Pydantic model serialization."""
    
    def test_json_round_trip(self, model_instance):
        """Test JSON serialization and deserialization round trip."""
        # Serialize to JSON
        json_data = model_instance.model_dump_json()
        
        # Deserialize back to model
        model_class = type(model_instance)
        return model_class.model_validate_json(json_data)
    
    def test_dict_round_trip(self, model_instance):
        """Test dict serialization and deserialization round trip."""
        # Serialize to dict
        dict_data = model_instance.model_dump()
        
        # Deserialize back to model
        model_class = type(model_instance)
        return model_class.model_validate(dict_data)


@pytest.fixture
def validation_helper():
    """Provide validation helper for testing Pydantic models."""
    return ValidationHelper()


@pytest.fixture
def serialization_helper():
    """Provide serialization helper for testing Pydantic models."""
    return SerializationHelper()


@pytest.fixture
def edge_case_data():
    """Provide edge case test data."""
    return {
        "min_price": 0.01,
        "max_price": 10000.0,
        "max_rating": 5.0,
        "min_rating": 0.0,
        "long_string": "x" * 1000,
        "unicode_string": "Hotel München 🏨",
        "special_chars": "Hotel & B&B \"Quotes\" <script>alert('xss')</script>",
    }
