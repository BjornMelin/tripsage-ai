"""
Test data factories for TripSage AI.

This module provides factory classes for generating consistent test data
across the entire test suite. Uses the factory pattern to create realistic
test data for models, requests, and responses.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import uuid4

from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    AirlineProvider,
    BookingStatus,
    CancellationPolicy,
    CurrencyCode,
    DataSource,
    TripStatus,
    TripType,
    TripVisibility,
    UserRole,
)


class BaseFactory:
    """Base factory with common utilities."""

    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID for testing."""
        return str(uuid4())

    @staticmethod
    def future_date(days: int = 30) -> date:
        """Generate a future date for testing."""
        return date.today() + timedelta(days=days)

    @staticmethod
    def future_datetime(days: int = 30, hours: int = 0) -> datetime:
        """Generate a future datetime for testing."""
        return datetime.now(timezone.utc) + timedelta(days=days, hours=hours)


class UserFactory(BaseFactory):
    """Factory for creating test user data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test user with optional overrides."""
        defaults = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "John",
            "last_name": "Doe",
            "role": UserRole.USER,
            "is_active": True,
            "preferred_currency": CurrencyCode.USD,
            "timezone": "America/Los_Angeles",
            "password_hash": "mock_hash_for_testing",
            "created_at": cls.future_datetime(-30),
            "updated_at": cls.future_datetime(-1),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_admin(cls, **kwargs) -> Dict[str, Any]:
        """Create a test admin user."""
        return cls.create(
            role=UserRole.ADMIN, email="admin@example.com", username="admin", **kwargs
        )

    @classmethod
    def create_batch(cls, count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple test users."""
        return [
            cls.create(
                id=i,
                email=f"user{i}@example.com",
                username=f"user{i}",
            )
            for i in range(1, count + 1)
        ]


class TripFactory(BaseFactory):
    """Factory for creating test trip data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test trip with optional overrides."""
        defaults = {
            "id": 1,
            "user_id": 1,
            "name": "Tokyo Adventure",
            "description": "A wonderful trip to Tokyo exploring culture and cuisine",
            "start_date": cls.future_date(30),
            "end_date": cls.future_date(37),
            "destination": "Tokyo, Japan",
            "status": TripStatus.PLANNING,
            "trip_type": TripType.LEISURE,
            "visibility": TripVisibility.PRIVATE,
            "budget": 5000.00,
            "currency": CurrencyCode.USD,
            "travelers_count": 2,
            "created_at": cls.future_datetime(-7),
            "updated_at": cls.future_datetime(-1),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_business_trip(cls, **kwargs) -> Dict[str, Any]:
        """Create a business trip."""
        return cls.create(
            name="Business Conference",
            trip_type=TripType.BUSINESS,
            budget=3000.00,
            travelers_count=1,
            **kwargs,
        )

    @classmethod
    def create_family_trip(cls, **kwargs) -> Dict[str, Any]:
        """Create a family trip."""
        return cls.create(
            name="Family Vacation", travelers_count=4, budget=8000.00, **kwargs
        )


class AccommodationFactory(BaseFactory):
    """Factory for creating test accommodation data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test accommodation with optional overrides."""
        defaults = {
            "id": 1,
            "trip_id": 1,
            "name": "Grand Hyatt Tokyo",
            "accommodation_type": AccommodationType.HOTEL,
            "check_in": cls.future_date(10),
            "check_out": cls.future_date(17),
            "price_per_night": 250.00,
            "total_price": 1750.00,
            "location": "Tokyo, Japan",
            "rating": 4.5,
            "amenities": {"list": ["wifi", "pool", "gym", "spa"]},
            "booking_link": "https://example.com/booking/12345",
            "booking_status": BookingStatus.VIEWED,
            "cancellation_policy": CancellationPolicy.FLEXIBLE,
            "distance_to_center": 2.5,
            "neighborhood": "Roppongi",
            "images": [
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg",
            ],
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_airbnb(cls, **kwargs) -> Dict[str, Any]:
        """Create an Airbnb accommodation."""
        return cls.create(
            accommodation_type=AccommodationType.APARTMENT,
            name="Modern Tokyo Apartment",
            price_per_night=120.00,
            total_price=840.00,
            **kwargs,
        )

    @classmethod
    def create_hostel(cls, **kwargs) -> Dict[str, Any]:
        """Create a hostel accommodation."""
        return cls.create(
            accommodation_type=AccommodationType.HOSTEL,
            name="Tokyo Backpackers Hostel",
            price_per_night=35.00,
            total_price=245.00,
            rating=3.8,
            **kwargs,
        )


class FlightFactory(BaseFactory):
    """Factory for creating test flight data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test flight with optional overrides."""
        departure_time = cls.future_datetime(30)
        defaults = {
            "id": 1,
            "trip_id": 1,
            "origin": "LAX",
            "destination": "NRT",
            "airline": AirlineProvider.JAPAN_AIRLINES,
            "departure_time": departure_time,
            "arrival_time": departure_time + timedelta(hours=12),
            "price": 1200.00,
            "search_timestamp": cls.future_datetime(-1),
            "booking_status": BookingStatus.VIEWED,
            "data_source": DataSource.DUFFEL,
            "segment_number": 1,
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_return_flight(cls, **kwargs) -> Dict[str, Any]:
        """Create a return flight."""
        departure_time = cls.future_datetime(37)
        return cls.create(
            id=2,
            origin="NRT",
            destination="LAX",
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=11),
            segment_number=2,
            **kwargs,
        )

    @classmethod
    def create_domestic_flight(cls, **kwargs) -> Dict[str, Any]:
        """Create a domestic flight."""
        departure_time = cls.future_datetime(15)
        return cls.create(
            origin="LAX",
            destination="SFO",
            airline=AirlineProvider.AMERICAN,
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(hours=1.5),
            price=200.00,
            **kwargs,
        )


class ChatFactory(BaseFactory):
    """Factory for creating test chat data."""

    @classmethod
    def create_message(cls, **kwargs) -> Dict[str, Any]:
        """Create a test chat message."""
        defaults = {
            "id": cls.generate_id(),
            "content": "I'm looking for a great hotel in Tokyo",
            "role": "user",
            "timestamp": cls.future_datetime(-1),
            "session_id": cls.generate_id(),
            "user_id": 1,
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_websocket_message(cls, **kwargs):
        """Create a WebSocket message object for event tests."""
        from tripsage_core.models.schemas_common.chat import ChatMessage, MessageRole
        from uuid import UUID

        defaults = {
            "role": MessageRole.USER,
            "content": "I'm looking for a great hotel in Tokyo",
            "timestamp": cls.future_datetime(-1),
        }
        return ChatMessage(**{**defaults, **kwargs})

    @classmethod
    def create_assistant_message(cls, **kwargs) -> Dict[str, Any]:
        """Create an assistant response message."""
        return cls.create_message(
            content=(
                "I'd be happy to help you find a hotel in Tokyo! "
                "What's your budget and preferred area?"
            ),
            role="assistant",
            **kwargs,
        )

    @classmethod
    def create_conversation(cls, message_count: int = 4) -> List[Dict[str, Any]]:
        """Create a conversation with multiple messages."""
        session_id = cls.generate_id()
        messages = []

        for i in range(message_count):
            role = "user" if i % 2 == 0 else "assistant"
            content = (
                f"User message {i // 2 + 1}"
                if role == "user"
                else f"Assistant response {i // 2 + 1}"
            )

            messages.append(
                cls.create_message(
                    content=content,
                    role=role,
                    session_id=session_id,
                    timestamp=cls.future_datetime(-message_count + i),
                )
            )

        return messages

    @classmethod
    def create_response(cls, **kwargs) -> Dict[str, Any]:
        """Create a chat service response."""
        defaults = {
            "response": (
                "I'd be happy to help you plan your trip! Where would you like to go?"
            ),
            "session_id": cls.generate_id(),
            "user_id": 1,
            "timestamp": cls.future_datetime(),
            "status": "completed",
            "token_usage": {
                "prompt_tokens": 50,
                "completion_tokens": 25,
                "total_tokens": 75,
            },
        }
        return {**defaults, **kwargs}


class APIKeyFactory(BaseFactory):
    """Factory for creating test API key data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test API key."""
        defaults = {
            "id": 1,
            "user_id": 1,
            "service_name": "openai",
            "encrypted_key": "encrypted_test_key_data",
            "key_hash": "hash_of_test_key",
            "is_active": True,
            "created_at": cls.future_datetime(-7),
            "last_used": cls.future_datetime(-1),
            "usage_count": 42,
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_service_keys(cls, user_id: int = 1) -> List[Dict[str, Any]]:
        """Create API keys for common services."""
        services = ["openai", "anthropic", "google_maps", "duffel"]
        return [
            cls.create(
                id=i + 1,
                user_id=user_id,
                service_name=service,
            )
            for i, service in enumerate(services)
        ]


class SearchFactory(BaseFactory):
    """Factory for creating test search data."""

    @classmethod
    def create_accommodation_search(cls, **kwargs) -> Dict[str, Any]:
        """Create accommodation search parameters."""
        defaults = {
            "destination": "Tokyo, Japan",
            "check_in": cls.future_date(30),
            "check_out": cls.future_date(37),
            "guests": 2,
            "min_price": 50.00,
            "max_price": 500.00,
            "accommodation_type": AccommodationType.HOTEL,
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_flight_search(cls, **kwargs) -> Dict[str, Any]:
        """Create flight search parameters."""
        defaults = {
            "origin": "LAX",
            "destination": "NRT",
            "departure_date": cls.future_date(30),
            "return_date": cls.future_date(37),
            "passengers": 2,
            "cabin_class": "economy",
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_search_results(cls, count: int = 5) -> Dict[str, Any]:
        """Create mock search results."""
        return {
            "results": [
                AccommodationFactory.create(id=i, name=f"Hotel {i}")
                for i in range(1, count + 1)
            ],
            "total": count,
            "page": 1,
            "has_more": False,
        }


class DestinationFactory(BaseFactory):
    """Factory for creating test destination data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test destination."""
        defaults = {
            "id": cls.generate_id(),
            "name": "Tokyo",
            "country": "Japan",
            "location_type": "city",
            "description": "Japan's bustling capital",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "timezone": "Asia/Tokyo",
            "population": 13960000,
            "language": "Japanese",
            "currency": "JPY",
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_search_response(cls, **kwargs) -> Dict[str, Any]:
        """Create a destination search response."""
        defaults = {
            "destinations": [cls.create()],
            "total_count": 1,
            "page": 1,
            "per_page": 10,
            "search_query": "Tokyo",
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_details_response(cls, **kwargs) -> Dict[str, Any]:
        """Create a destination details response."""
        base_destination = cls.create(**kwargs)
        details = {
            **base_destination,
            "attractions": [
                {"name": "Tokyo Tower", "type": "landmark"},
                {"name": "Senso-ji Temple", "type": "temple"},
            ],
            "weather": {
                "average_temperature": "15°C",
                "best_time_to_visit": "March-May, September-November",
            },
            "travel_tips": [
                "Learn basic Japanese phrases",
                "Get a JR Pass for train travel",
            ],
        }
        return details

    @classmethod
    def create_saved_destination(cls, **kwargs) -> Dict[str, Any]:
        """Create a saved destination."""
        defaults = {
            "id": cls.generate_id(),
            "user_id": "test-user-id",
            "destination_id": cls.generate_id(),
            "destination_name": "Tokyo",
            "notes": "Want to visit during cherry blossom season",
            "saved_at": cls.future_datetime(-1).isoformat(),
            "trip_id": None,
        }
        return {**defaults, **kwargs}


class ItineraryFactory(BaseFactory):
    """Factory for creating test itinerary data."""

    @classmethod
    def create(cls, **kwargs) -> Dict[str, Any]:
        """Create a test itinerary."""
        defaults = {
            "id": cls.generate_id(),
            "user_id": "test-user-id",
            "name": "Tokyo Adventure",
            "description": "5-day trip exploring Tokyo",
            "start_date": cls.future_date(30).isoformat(),
            "end_date": cls.future_date(35).isoformat(),
            "destination": "Tokyo, Japan",
            "status": "active",
            "created_at": cls.future_datetime(-7).isoformat(),
            "updated_at": cls.future_datetime(-1).isoformat(),
            "items_count": 5,
            "total_duration_hours": 48,
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_item(cls, **kwargs) -> Dict[str, Any]:
        """Create a test itinerary item."""
        defaults = {
            "id": cls.generate_id(),
            "itinerary_id": cls.generate_id(),
            "name": "Visit Tokyo Tower",
            "description": "Iconic Tokyo landmark with great city views",
            "start_time": cls.future_datetime(30).isoformat(),
            "end_time": cls.future_datetime(30, 2).isoformat(),
            "location": "Tokyo Tower, Tokyo",
            "item_type": "attraction",
            "status": "planned",
            "order_index": 1,
            "duration_minutes": 120,
            "cost": 1000.0,
            "currency": "JPY",
            "notes": "Buy tickets in advance",
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_search_response(cls, **kwargs) -> Dict[str, Any]:
        """Create an itinerary search response."""
        defaults = {
            "itineraries": [cls.create()],
            "total_count": 1,
            "page": 1,
            "per_page": 10,
            "filters_applied": {
                "destination": "Tokyo",
                "date_range": "2024-05-01 to 2024-05-31",
            },
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_conflict_response(cls, **kwargs) -> Dict[str, Any]:
        """Create an itinerary conflict check response."""
        defaults = {
            "has_conflicts": False,
            "conflicts": [],
            "suggestions": ["Consider adding buffer time between activities"],
            "total_items_checked": 5,
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_optimize_response(cls, **kwargs) -> Dict[str, Any]:
        """Create an itinerary optimization response."""
        defaults = {
            "optimized_itinerary": cls.create(),
            "improvements": [
                "Reduced travel time by 30 minutes",
                "Optimized attraction visit order",
            ],
            "optimization_score": 0.85,
            "time_saved_minutes": 30,
            "cost_saved": 500.0,
        }
        return {**defaults, **kwargs}


class MemoryFactory(BaseFactory):
    """Factory for creating test memory data."""

    @classmethod
    def create_conversation_result(cls, **kwargs) -> Dict[str, Any]:
        """Create a conversation memory result."""
        defaults = {
            "memory_id": cls.generate_id(),
            "status": "success",
            "messages_stored": 2,
            "session_id": "test-session-123",
            "created_at": cls.future_datetime(-1).isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_user_context(cls, **kwargs) -> Dict[str, Any]:
        """Create user context data."""
        defaults = {
            "user_id": "test-user-id",
            "preferences": {
                "budget_range": "medium",
                "accommodation_type": "hotel",
                "travel_style": "balanced",
                "dietary_restrictions": [],
            },
            "travel_history": [
                {
                    "destination": "Tokyo, Japan",
                    "dates": "2023-05-01 to 2023-05-07",
                    "rating": 5,
                }
            ],
            "recent_searches": [
                {
                    "query": "hotels in Tokyo",
                    "timestamp": cls.future_datetime(-3).isoformat(),
                }
            ],
            "last_updated": cls.future_datetime(-1).isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_memories(cls, count: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Create a list of memory entries."""
        memories = []
        for i in range(count):
            memory = {
                "id": cls.generate_id(),
                "content": f"Memory content {i + 1}",
                "type": "conversation",
                "relevance_score": 0.8 - (i * 0.1),
                "created_at": cls.future_datetime(-i - 1).isoformat(),
                "metadata": {
                    "session_id": f"session-{i + 1}",
                    "topic": "travel_planning",
                },
            }
            memories.append({**memory, **kwargs})
        return memories

    @classmethod
    def create_preferences(cls, **kwargs) -> Dict[str, Any]:
        """Create user preferences."""
        defaults = {
            "budget_range": "medium",
            "accommodation_type": "hotel",
            "travel_style": "balanced",
            "dietary_restrictions": [],
            "preferred_airlines": ["Japan Airlines", "ANA"],
            "accessibility_needs": [],
            "language_preference": "english",
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_memory_stats(cls, **kwargs) -> Dict[str, Any]:
        """Create memory statistics."""
        defaults = {
            "total_memories": 25,
            "conversation_count": 15,
            "preference_count": 8,
            "travel_history_count": 2,
            "last_activity": cls.future_datetime(-1).isoformat(),
            "storage_used_kb": 156.7,
            "oldest_memory": cls.future_datetime(-30).isoformat(),
        }
        return {**defaults, **kwargs}


class WebSocketFactory(BaseFactory):
    """Factory for creating test WebSocket data."""

    @classmethod
    def create_auth_request(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket authentication request."""
        defaults = {
            "access_token": "test-token-12345",
            "user_id": cls.generate_id(),
            "session_id": cls.generate_id(),
            "channels": [],
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_auth_response(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket authentication response."""
        defaults = {
            "success": True,
            "connection_id": f"conn-{cls.generate_id()[:8]}",
            "user_id": cls.generate_id(),
            "session_id": cls.generate_id(),
            "channels": [],
            "expires_at": cls.future_datetime(1).isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_chat_message(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket chat message."""
        defaults = {
            "type": "chat_message",
            "payload": {
                "content": "Hello, I need help planning a trip to Tokyo",
                "attachments": [],
                "metadata": {},
            },
            "timestamp": cls.future_datetime().isoformat(),
            "message_id": cls.generate_id(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_heartbeat_message(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket heartbeat message."""
        defaults = {"type": "heartbeat", "timestamp": cls.future_datetime().isoformat()}
        return {**defaults, **kwargs}

    @classmethod
    def create_subscribe_request(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket subscription request."""
        defaults = {
            "type": "subscribe",
            "payload": {"channels": ["chat", "agent_status"], "filters": {}},
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_connection_event(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket connection event."""
        defaults = {
            "type": "connection",
            "status": "connected",
            "connection_id": f"conn-{cls.generate_id()[:8]}",
            "user_id": cls.generate_id(),
            "session_id": cls.generate_id(),
            "timestamp": cls.future_datetime().isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_error_event(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket error event."""
        defaults = {
            "type": "error",
            "error_code": "VALIDATION_ERROR",
            "error_message": "Invalid message format",
            "user_id": cls.generate_id(),
            "session_id": cls.generate_id(),
            "timestamp": cls.future_datetime().isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_typing_event(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket typing indicator event."""
        defaults = {
            "type": "typing",
            "user_id": cls.generate_id(),
            "session_id": cls.generate_id(),
            "is_typing": True,
            "timestamp": cls.future_datetime().isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_message_chunk(cls, **kwargs) -> Dict[str, Any]:
        """Create a WebSocket message chunk for streaming."""
        defaults = {
            "type": "message_chunk",
            "content": "This is a chunk of the response",
            "chunk_index": 1,
            "is_final": False,
            "user_id": cls.generate_id(),
            "session_id": cls.generate_id(),
            "timestamp": cls.future_datetime().isoformat(),
        }
        return {**defaults, **kwargs}

    @classmethod
    def create_connection_stats(cls, **kwargs) -> Dict[str, Any]:
        """Create WebSocket connection statistics."""
        defaults = {
            "total_connections": 5,
            "active_connections": 3,
            "channels": {"chat": 2, "agent_status": 1},
            "messages_per_minute": 25.5,
            "avg_connection_duration": "00:15:30",
            "last_updated": cls.future_datetime().isoformat(),
        }
        return {**defaults, **kwargs}


# Export all factories
__all__ = [
    "BaseFactory",
    "UserFactory",
    "TripFactory",
    "AccommodationFactory",
    "FlightFactory",
    "ChatFactory",
    "APIKeyFactory",
    "SearchFactory",
    "DestinationFactory",
    "ItineraryFactory",
    "MemoryFactory",
    "WebSocketFactory",
]
