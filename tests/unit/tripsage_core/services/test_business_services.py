"""
Comprehensive tests for TripSage Core business services using modern FastAPI
and dependency injection patterns.

This test module follows latest best practices from 2024:
- FastAPI dependency injection testing with app.dependency_overrides
- Modern async/await patterns for service testing
- Pydantic v2 models for request/response validation
- Proper mocking of external dependencies
- Service layer isolation and business logic testing
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from tripsage_core.models.domain.accommodation import (
    AccommodationLocation,
    AccommodationOffer,
)
from tripsage_core.models.domain.flight import (
    FlightLocation,
    FlightOffer,
    FlightSegment,
)
from tripsage_core.models.domain.memory import MemoryContext, UserPreference
from tripsage_core.models.domain.trip import TripItinerary, TripLocation
from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    BookingStatus,
    CabinClass,
    CurrencyCode,
    TripStatus,
)
from tripsage_core.services.business.accommodation_service import AccommodationService
from tripsage_core.services.business.auth_service import AuthService
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.services.business.memory_service import MemoryService
from tripsage_core.services.business.trip_service import TripService
from tripsage_core.services.business.user_service import UserService
from tripsage_core.services.infrastructure.cache_service import CacheService
from tripsage_core.services.infrastructure.database_service import DatabaseService


class TestAccommodationService:
    """Test suite for accommodation service business logic."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for testing."""
        mock_db = AsyncMock(spec=DatabaseService)
        return mock_db

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service for testing."""
        mock_cache = AsyncMock(spec=CacheService)
        return mock_cache

    @pytest.fixture
    def accommodation_service(self, mock_database_service, mock_cache_service):
        """Accommodation service with mocked dependencies."""
        return AccommodationService(
            database_service=mock_database_service,
            cache_service=mock_cache_service,
        )

    @pytest.fixture
    def sample_accommodation_data(self) -> Dict[str, Any]:
        """Sample accommodation data for testing."""
        return {
            "offer_id": "acc-123",
            "name": "Luxury Hotel NYC",
            "accommodation_type": AccommodationType.HOTEL,
            "location": {
                "address": "123 Main St",
                "city": "New York",
                "country": "United States",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
            "price": Decimal("299.99"),
            "currency": CurrencyCode.USD,
            "availability_start": date(2024, 6, 1),
            "availability_end": date(2024, 6, 30),
            "max_guests": 4,
            "average_rating": 4.7,
            "total_reviews": 1524,
            "booking_status": BookingStatus.VIEWED,
        }

    @pytest.mark.asyncio
    async def test_search_accommodations_success(
        self,
        accommodation_service,
        mock_database_service,
        mock_cache_service,
        sample_accommodation_data,
    ):
        """Test successful accommodation search."""
        # Mock cache miss
        mock_cache_service.get.return_value = None

        # Mock database response
        location = AccommodationLocation(**sample_accommodation_data["location"])
        accommodation = AccommodationOffer(
            **{**sample_accommodation_data, "location": location}
        )
        mock_database_service.search_accommodations.return_value = [accommodation]

        # Execute search
        search_params = {
            "destination": "New York",
            "check_in": date(2024, 6, 1),
            "check_out": date(2024, 6, 5),
            "guests": 2,
            "max_price": Decimal("500.00"),
        }

        results = await accommodation_service.search_accommodations(**search_params)

        # Assertions
        assert len(results) == 1
        assert results[0].offer_id == "acc-123"
        assert results[0].name == "Luxury Hotel NYC"
        assert results[0].accommodation_type == AccommodationType.HOTEL

        # Verify database was called with correct parameters
        mock_database_service.search_accommodations.assert_called_once()

        # Verify cache was set
        mock_cache_service.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_accommodations_with_cache_hit(
        self,
        accommodation_service,
        mock_database_service,
        mock_cache_service,
        sample_accommodation_data,
    ):
        """Test accommodation search with cache hit."""
        # Mock cache hit
        location = AccommodationLocation(**sample_accommodation_data["location"])
        cached_accommodation = AccommodationOffer(
            **{**sample_accommodation_data, "location": location}
        )
        mock_cache_service.get.return_value = [cached_accommodation]

        # Execute search
        search_params = {
            "destination": "New York",
            "check_in": date(2024, 6, 1),
            "check_out": date(2024, 6, 5),
            "guests": 2,
        }

        results = await accommodation_service.search_accommodations(**search_params)

        # Assertions
        assert len(results) == 1
        assert results[0].offer_id == "acc-123"

        # Verify database was NOT called due to cache hit
        mock_database_service.search_accommodations.assert_not_called()

        # Verify cache was checked
        mock_cache_service.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_accommodation_by_id_success(
        self, accommodation_service, mock_database_service, sample_accommodation_data
    ):
        """Test successful accommodation retrieval by ID."""
        location = AccommodationLocation(**sample_accommodation_data["location"])
        accommodation = AccommodationOffer(
            **{**sample_accommodation_data, "location": location}
        )
        mock_database_service.get_accommodation_by_id.return_value = accommodation

        result = await accommodation_service.get_accommodation_by_id("acc-123")

        assert result is not None
        assert result.offer_id == "acc-123"
        assert result.name == "Luxury Hotel NYC"

        mock_database_service.get_accommodation_by_id.assert_called_once_with("acc-123")

    @pytest.mark.asyncio
    async def test_get_accommodation_by_id_not_found(
        self, accommodation_service, mock_database_service
    ):
        """Test accommodation retrieval when not found."""
        mock_database_service.get_accommodation_by_id.return_value = None

        result = await accommodation_service.get_accommodation_by_id("nonexistent")

        assert result is None
        mock_database_service.get_accommodation_by_id.assert_called_once_with(
            "nonexistent"
        )

    @pytest.mark.asyncio
    async def test_book_accommodation_success(
        self, accommodation_service, mock_database_service, sample_accommodation_data
    ):
        """Test successful accommodation booking."""
        location = AccommodationLocation(**sample_accommodation_data["location"])
        accommodation = AccommodationOffer(
            **{**sample_accommodation_data, "location": location}
        )

        # Mock successful booking
        booked_accommodation = AccommodationOffer(
            **{
                **sample_accommodation_data,
                "location": location,
                "booking_status": BookingStatus.BOOKED,
            }
        )
        mock_database_service.get_accommodation_by_id.return_value = accommodation
        mock_database_service.update_accommodation.return_value = booked_accommodation

        booking_data = {
            "guest_name": "John Doe",
            "guest_email": "john@example.com",
            "check_in": date(2024, 6, 1),
            "check_out": date(2024, 6, 5),
            "guests": 2,
        }

        result = await accommodation_service.book_accommodation("acc-123", booking_data)

        assert result is not None
        assert result.booking_status == BookingStatus.BOOKED

        mock_database_service.get_accommodation_by_id.assert_called_once_with("acc-123")
        mock_database_service.update_accommodation.assert_called_once()

    @pytest.mark.asyncio
    async def test_book_accommodation_not_found(
        self, accommodation_service, mock_database_service
    ):
        """Test booking accommodation that doesn't exist."""
        mock_database_service.get_accommodation_by_id.return_value = None

        booking_data = {
            "guest_name": "John Doe",
            "guest_email": "john@example.com",
            "check_in": date(2024, 6, 1),
            "check_out": date(2024, 6, 5),
            "guests": 2,
        }

        with pytest.raises(HTTPException) as exc_info:
            await accommodation_service.book_accommodation("nonexistent", booking_data)

        assert exc_info.value.status_code == 404
        assert "Accommodation not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_cancel_accommodation_booking_success(
        self, accommodation_service, mock_database_service, sample_accommodation_data
    ):
        """Test successful accommodation booking cancellation."""
        location = AccommodationLocation(**sample_accommodation_data["location"])
        booked_accommodation = AccommodationOffer(
            **{
                **sample_accommodation_data,
                "location": location,
                "booking_status": BookingStatus.BOOKED,
            }
        )

        cancelled_accommodation = AccommodationOffer(
            **{
                **sample_accommodation_data,
                "location": location,
                "booking_status": BookingStatus.CANCELLED,
            }
        )

        mock_database_service.get_accommodation_by_id.return_value = (
            booked_accommodation
        )
        mock_database_service.update_accommodation.return_value = (
            cancelled_accommodation
        )

        result = await accommodation_service.cancel_accommodation_booking("acc-123")

        assert result is not None
        assert result.booking_status == BookingStatus.CANCELLED

        mock_database_service.update_accommodation.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_accommodations_by_criteria(
        self, accommodation_service, mock_database_service, sample_accommodation_data
    ):
        """Test filtering accommodations by various criteria."""
        location = AccommodationLocation(**sample_accommodation_data["location"])
        accommodations = [
            AccommodationOffer(**{**sample_accommodation_data, "location": location}),
            AccommodationOffer(
                **{
                    **sample_accommodation_data,
                    "offer_id": "acc-124",
                    "price": Decimal("199.99"),
                    "location": location,
                }
            ),
        ]

        mock_database_service.search_accommodations.return_value = accommodations

        # Test price filtering
        filters = {
            "max_price": Decimal("250.00"),
            "min_rating": 4.5,
            "accommodation_types": [AccommodationType.HOTEL],
        }

        result = await accommodation_service.filter_accommodations(filters)

        # Both accommodations should match the criteria
        assert len(result) == 2
        assert all(acc.accommodation_type == AccommodationType.HOTEL for acc in result)
        assert all(acc.average_rating >= 4.5 for acc in result)


class TestFlightService:
    """Test suite for flight service business logic."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for testing."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service for testing."""
        return AsyncMock(spec=CacheService)

    @pytest.fixture
    def flight_service(self, mock_database_service, mock_cache_service):
        """Flight service with mocked dependencies."""
        return FlightService(
            database_service=mock_database_service,
            cache_service=mock_cache_service,
        )

    @pytest.fixture
    def sample_flight_data(self) -> Dict[str, Any]:
        """Sample flight data for testing."""
        departure_location = FlightLocation(
            airport_code="JFK",
            airport_name="John F. Kennedy International Airport",
            city="New York",
            country="United States",
        )

        arrival_location = FlightLocation(
            airport_code="LAX",
            airport_name="Los Angeles International Airport",
            city="Los Angeles",
            country="United States",
        )

        segment = FlightSegment(
            segment_id="seg-123",
            departure_location=departure_location,
            arrival_location=arrival_location,
            departure_time=datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc),
            arrival_time=datetime(2024, 6, 15, 14, 30, tzinfo=timezone.utc),
            flight_number="AA123",
            airline="American Airlines",
            aircraft_type="Boeing 737",
            cabin_class=CabinClass.ECONOMY,
        )

        return {
            "offer_id": "flt-123",
            "segments": [segment],
            "passengers": [],
            "baggage": [],
            "total_price": Decimal("450.00"),
            "currency": CurrencyCode.USD,
            "booking_status": BookingStatus.VIEWED,
            "refundable": True,
            "changes_allowed": True,
        }

    @pytest.mark.asyncio
    async def test_search_flights_success(
        self,
        flight_service,
        mock_database_service,
        mock_cache_service,
        sample_flight_data,
    ):
        """Test successful flight search."""
        # Mock cache miss
        mock_cache_service.get.return_value = None

        # Mock database response
        flight = FlightOffer(**sample_flight_data)
        mock_database_service.search_flights.return_value = [flight]

        # Execute search
        search_params = {
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": date(2024, 6, 15),
            "return_date": None,  # One-way flight
            "passengers": 1,
            "cabin_class": CabinClass.ECONOMY,
        }

        results = await flight_service.search_flights(**search_params)

        # Assertions
        assert len(results) == 1
        assert results[0].offer_id == "flt-123"
        assert results[0].total_price == Decimal("450.00")
        assert results[0].refundable is True

        # Verify database was called
        mock_database_service.search_flights.assert_called_once()

        # Verify cache was set
        mock_cache_service.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_flights_round_trip(
        self,
        flight_service,
        mock_database_service,
        mock_cache_service,
        sample_flight_data,
    ):
        """Test round-trip flight search."""
        # Create return flight
        return_flight_data = sample_flight_data.copy()
        return_flight_data["offer_id"] = "flt-124"
        return_flight_data["total_price"] = Decimal("480.00")

        outbound_flight = FlightOffer(**sample_flight_data)
        return_flight = FlightOffer(**return_flight_data)

        mock_cache_service.get.return_value = None
        mock_database_service.search_flights.return_value = [
            outbound_flight,
            return_flight,
        ]

        search_params = {
            "origin": "JFK",
            "destination": "LAX",
            "departure_date": date(2024, 6, 15),
            "return_date": date(2024, 6, 20),  # Round-trip
            "passengers": 1,
            "cabin_class": CabinClass.ECONOMY,
        }

        results = await flight_service.search_flights(**search_params)

        assert len(results) == 2
        assert any(f.offer_id == "flt-123" for f in results)
        assert any(f.offer_id == "flt-124" for f in results)

    @pytest.mark.asyncio
    async def test_book_flight_success(
        self, flight_service, mock_database_service, sample_flight_data
    ):
        """Test successful flight booking."""
        flight = FlightOffer(**sample_flight_data)
        booked_flight = FlightOffer(
            **{**sample_flight_data, "booking_status": BookingStatus.BOOKED}
        )

        mock_database_service.get_flight_by_id.return_value = flight
        mock_database_service.update_flight.return_value = booked_flight

        booking_data = {
            "passenger_details": [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1990-01-01",
                    "passport_number": "123456789",
                }
            ],
            "contact_info": {
                "email": "john@example.com",
                "phone": "+1-555-123-4567",
            },
        }

        result = await flight_service.book_flight("flt-123", booking_data)

        assert result is not None
        assert result.booking_status == BookingStatus.BOOKED

        mock_database_service.get_flight_by_id.assert_called_once_with("flt-123")
        mock_database_service.update_flight.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_flight_price_breakdown(
        self, flight_service, mock_database_service, sample_flight_data
    ):
        """Test flight price breakdown calculation."""
        flight = FlightOffer(**sample_flight_data)
        mock_database_service.get_flight_by_id.return_value = flight

        breakdown = await flight_service.get_flight_price_breakdown("flt-123")

        assert breakdown is not None
        assert "base_fare" in breakdown
        assert "taxes" in breakdown
        assert "fees" in breakdown
        assert "total" in breakdown
        assert breakdown["total"] == Decimal("450.00")


class TestTripService:
    """Test suite for trip service business logic."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for testing."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        return AsyncMock(spec=MemoryService)

    @pytest.fixture
    def trip_service(self, mock_database_service, mock_memory_service):
        """Trip service with mocked dependencies."""
        return TripService(
            database_service=mock_database_service,
            memory_service=mock_memory_service,
        )

    @pytest.fixture
    def sample_trip_data(self) -> Dict[str, Any]:
        """Sample trip data for testing."""
        location = TripLocation(
            name="Paris, France",
            country="France",
            city="Paris",
            visit_duration_days=5,
        )

        return {
            "itinerary_id": "trip-123",
            "name": "European Adventure",
            "destinations": [location],
            "start_date": date(2024, 6, 1),
            "end_date": date(2024, 6, 15),
            "status": TripStatus.PLANNING,
            "created_by": "user-456",
        }

    @pytest.mark.asyncio
    async def test_create_trip_success(
        self, trip_service, mock_database_service, mock_memory_service, sample_trip_data
    ):
        """Test successful trip creation."""
        trip = TripItinerary(**sample_trip_data)
        mock_database_service.create_trip.return_value = trip

        # Mock memory service to store trip context
        mock_memory_service.add_memory.return_value = "memory-123"

        trip_data = {
            "name": "European Adventure",
            "destinations": ["Paris, France"],
            "start_date": date(2024, 6, 1),
            "end_date": date(2024, 6, 15),
            "user_id": "user-456",
        }

        result = await trip_service.create_trip(trip_data)

        assert result is not None
        assert result.name == "European Adventure"
        assert result.status == TripStatus.PLANNING
        assert len(result.destinations) == 1

        mock_database_service.create_trip.assert_called_once()
        mock_memory_service.add_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_trips(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test retrieving user trips."""
        trip = TripItinerary(**sample_trip_data)
        mock_database_service.get_trips_by_user.return_value = [trip]

        results = await trip_service.get_user_trips("user-456")

        assert len(results) == 1
        assert results[0].itinerary_id == "trip-123"
        assert results[0].created_by == "user-456"

        mock_database_service.get_trips_by_user.assert_called_once_with("user-456")

    @pytest.mark.asyncio
    async def test_update_trip_status(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test updating trip status."""
        trip = TripItinerary(**sample_trip_data)
        updated_trip = TripItinerary(
            **{**sample_trip_data, "status": TripStatus.BOOKED}
        )

        mock_database_service.get_trip_by_id.return_value = trip
        mock_database_service.update_trip.return_value = updated_trip

        result = await trip_service.update_trip_status("trip-123", TripStatus.BOOKED)

        assert result is not None
        assert result.status == TripStatus.BOOKED

        mock_database_service.get_trip_by_id.assert_called_once_with("trip-123")
        mock_database_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_trip_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip deletion."""
        trip = TripItinerary(**sample_trip_data)
        mock_database_service.get_trip_by_id.return_value = trip
        mock_database_service.delete_trip.return_value = True

        result = await trip_service.delete_trip("trip-123", "user-456")

        assert result is True

        mock_database_service.get_trip_by_id.assert_called_once_with("trip-123")
        mock_database_service.delete_trip.assert_called_once_with("trip-123")

    @pytest.mark.asyncio
    async def test_delete_trip_unauthorized(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip deletion by unauthorized user."""
        trip = TripItinerary(**sample_trip_data)
        mock_database_service.get_trip_by_id.return_value = trip

        with pytest.raises(HTTPException) as exc_info:
            await trip_service.delete_trip("trip-123", "different-user")

        assert exc_info.value.status_code == 403
        assert "Not authorized" in str(exc_info.value.detail)


class TestMemoryService:
    """Test suite for memory service business logic."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for testing."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def memory_service(self, mock_database_service):
        """Memory service with mocked dependencies."""
        return MemoryService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_add_memory_success(self, memory_service, mock_database_service):
        """Test successful memory addition."""
        mock_database_service.create_memory.return_value = "memory-123"

        memory_data = {
            "user_id": "user-456",
            "content": {"preference": "budget_travel", "value": "under_100"},
            "memory_type": "user_preferences",
            "metadata": {"source": "user_input"},
        }

        result = await memory_service.add_memory(**memory_data)

        assert result == "memory-123"
        mock_database_service.create_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memories_by_user(self, memory_service, mock_database_service):
        """Test retrieving memories by user."""
        memory_context = MemoryContext(
            context_id="ctx-123",
            user_id="user-456",
            session_id="session-789",
            conversation_history=[],
            extracted_preferences={},
            context_timestamp=datetime.now(timezone.utc),
        )

        mock_database_service.get_memories_by_user.return_value = [memory_context]

        results = await memory_service.get_memories("user-456")

        assert len(results) == 1
        assert results[0].user_id == "user-456"

        mock_database_service.get_memories_by_user.assert_called_once_with(
            "user-456", None
        )

    @pytest.mark.asyncio
    async def test_search_memories_by_content(
        self, memory_service, mock_database_service
    ):
        """Test searching memories by content."""
        user_preference = UserPreference(
            preference_id="pref-123",
            user_id="user-456",
            category="travel_style",
            preference_key="budget",
            preference_value="economy",
            confidence_score=0.8,
            source="conversation",
            created_at=datetime.now(timezone.utc),
        )

        mock_database_service.search_memories.return_value = [user_preference]

        results = await memory_service.search_memories("user-456", "budget travel")

        assert len(results) == 1
        assert results[0].preference_value == "economy"

        mock_database_service.search_memories.assert_called_once()


class TestAuthService:
    """Test suite for authentication service business logic."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for testing."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def auth_service(self, mock_database_service):
        """Auth service with mocked dependencies."""
        return AuthService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_database_service):
        """Test successful user authentication."""
        user_data = {
            "user_id": "user-123",
            "email": "test@example.com",
            "hashed_password": "hashed_password_here",
            "is_active": True,
        }

        mock_database_service.get_user_by_email.return_value = user_data

        # Mock password verification
        with patch.object(auth_service, "verify_password", return_value=True):
            result = await auth_service.authenticate_user(
                "test@example.com", "password"
            )

        assert result is not None
        assert result["email"] == "test@example.com"
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(
        self, auth_service, mock_database_service
    ):
        """Test authentication with invalid credentials."""
        mock_database_service.get_user_by_email.return_value = None

        result = await auth_service.authenticate_user("invalid@example.com", "password")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_access_token(self, auth_service):
        """Test access token creation."""
        user_data = {"user_id": "user-123", "email": "test@example.com"}

        token = await auth_service.create_access_token(user_data)

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_service):
        """Test successful token verification."""
        user_data = {"user_id": "user-123", "email": "test@example.com"}
        token = await auth_service.create_access_token(user_data)

        decoded_data = await auth_service.verify_token(token)

        assert decoded_data is not None
        assert decoded_data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_service):
        """Test verification of invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.verify_token("invalid_token")

        assert exc_info.value.status_code == 401


class TestUserService:
    """Test suite for user service business logic."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service for testing."""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def user_service(self, mock_database_service):
        """User service with mocked dependencies."""
        return UserService(database_service=mock_database_service)

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_database_service):
        """Test successful user creation."""
        user_data = {
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "secure_password",
        }

        created_user = {
            "user_id": "user-123",
            "email": "newuser@example.com",
            "full_name": "New User",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }

        mock_database_service.get_user_by_email.return_value = (
            None  # User doesn't exist
        )
        mock_database_service.create_user.return_value = created_user

        result = await user_service.create_user(user_data)

        assert result is not None
        assert result["email"] == "newuser@example.com"
        assert result["is_active"] is True

        mock_database_service.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, mock_database_service):
        """Test user creation with existing email."""
        existing_user = {
            "user_id": "user-456",
            "email": "existing@example.com",
        }

        mock_database_service.get_user_by_email.return_value = existing_user

        user_data = {
            "email": "existing@example.com",
            "full_name": "Another User",
            "password": "password",
        }

        with pytest.raises(HTTPException) as exc_info:
            await user_service.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "Email already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_profile(self, user_service, mock_database_service):
        """Test retrieving user profile."""
        user_profile = {
            "user_id": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "preferences": {"theme": "dark", "notifications": True},
        }

        mock_database_service.get_user_by_id.return_value = user_profile

        result = await user_service.get_user_profile("user-123")

        assert result is not None
        assert result["email"] == "test@example.com"
        assert result["preferences"]["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_update_user_profile(self, user_service, mock_database_service):
        """Test updating user profile."""
        existing_user = {
            "user_id": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
        }

        updated_user = {
            "user_id": "user-123",
            "email": "test@example.com",
            "full_name": "Updated Test User",
        }

        mock_database_service.get_user_by_id.return_value = existing_user
        mock_database_service.update_user.return_value = updated_user

        update_data = {"full_name": "Updated Test User"}

        result = await user_service.update_user_profile("user-123", update_data)

        assert result is not None
        assert result["full_name"] == "Updated Test User"

        mock_database_service.update_user.assert_called_once()


# Integration tests with FastAPI dependency injection
class TestServiceIntegrationWithFastAPI:
    """Test service integration with FastAPI dependency injection."""

    @pytest.fixture
    def app(self):
        """FastAPI application for testing."""
        app = FastAPI()

        # Module-level singleton for dependency injection
        _accommodation_service = AccommodationService()

        def get_accommodation_service():
            return _accommodation_service

        # Create dependency at module level to avoid B008 error
        accommodation_service_dep = Depends(get_accommodation_service)

        @app.get("/accommodations/search")
        async def search_accommodations(
            destination: str,
            accommodation_service: AccommodationService = accommodation_service_dep,
        ):
            return await accommodation_service.search_accommodations(
                destination=destination,
                check_in=date.today(),
                check_out=date.today(),
                guests=1,
            )

        return app

    @pytest.fixture
    def client(self, app):
        """Test client for FastAPI application."""
        return TestClient(app)

    def test_dependency_injection_override(self, app, client):
        """Test overriding dependencies for testing."""
        # Create mock service
        mock_accommodation_service = AsyncMock(spec=AccommodationService)
        mock_accommodation_service.search_accommodations.return_value = []

        # Override dependency
        app.dependency_overrides[AccommodationService] = (
            lambda: mock_accommodation_service
        )

        try:
            response = client.get("/accommodations/search?destination=Paris")
            assert response.status_code == 200
            assert response.json() == []

            # Verify mock was called
            mock_accommodation_service.search_accommodations.assert_called_once()
        finally:
            # Clean up override
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
