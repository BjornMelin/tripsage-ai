"""Test fixtures for database model tests."""

from datetime import date, datetime, timedelta
from typing import Any, Dict

import pytest

from tripsage.models.db.accommodation import (
    AccommodationType,
    CancellationPolicy,
)
from tripsage.models.db.flight import AirlineProvider, BookingStatus, DataSource
from tripsage.models.db.price_history import EntityType
from tripsage.models.db.saved_option import OptionType
from tripsage.models.db.transportation import TransportationType
from tripsage.models.db.trip import TripStatus, TripVisibility
from tripsage.models.db.user import UserRole

# Temporarily commented out until fixed
# from tripsage.models.db.itinerary_item import ItineraryItem, ItemType


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
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "last_login": datetime.now(),
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
        "visibility": TripVisibility.PRIVATE,
        "start_date": date.today() + timedelta(days=10),
        "end_date": date.today() + timedelta(days=17),
        "destination": "Tokyo, Japan",
        "budget": 2500.00,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "adults": 2,
        "children": 0,
        "tags": ["vacation", "winter"],
    }


@pytest.fixture
def sample_flight_dict() -> Dict[str, Any]:
    """Return a sample flight dict for testing."""
    now = datetime.now()
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
        "search_timestamp": datetime.now(),
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
        "timestamp": datetime.now(),
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
        "timestamp": datetime.now(),
        "content": "Remember to exchange currency before departure",
    }


@pytest.fixture
def sample_price_history_dict() -> Dict[str, Any]:
    """Return a sample price history dict for testing."""
    return {
        "id": 1,
        "entity_type": EntityType.FLIGHT,
        "entity_id": 1,
        "timestamp": datetime.now(),
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
        "timestamp": datetime.now(),
        "notes": "Best price found so far",
    }


@pytest.fixture
def sample_trip_comparison_dict() -> Dict[str, Any]:
    """Return a sample trip comparison dict for testing."""
    return {
        "id": 1,
        "trip_id": 1,
        "timestamp": datetime.now(),
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
    now = datetime.now()
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
