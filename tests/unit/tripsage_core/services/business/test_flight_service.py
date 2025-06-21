"""Comprehensive tests for FlightService.

This module provides full test coverage for flight management operations
including flight search, booking, cancellation, and external API integration.
Updated for Pydantic v2 and modern testing patterns.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.flight_service import (
    BookingStatus,
    CabinClass,
    FlightBooking,
    FlightBookingRequest,
    FlightOffer,
    FlightPassenger,
    FlightSearchRequest,
    FlightSearchResponse,
    FlightSegment,
    FlightService,
    PassengerType,
)


class TestFlightService:
    """Test suite for FlightService."""

    @pytest.fixture
    def mock_external_flight_service(self) -> AsyncMock:
        """Mock external flight service (Duffel)."""
        external = AsyncMock()
        external.search_flights = AsyncMock()
        external.create_order = AsyncMock()
        return external

    @pytest.fixture
    def flight_service(
        self, mock_database_service: AsyncMock, mock_external_flight_service: AsyncMock
    ) -> FlightService:
        """Create FlightService instance with mocked dependencies."""
        return FlightService(
            database_service=mock_database_service,
            external_flight_service=mock_external_flight_service,
            cache_ttl=300,
        )

    @pytest.fixture
    def sample_flight_passenger(self) -> FlightPassenger:
        """Sample flight passenger."""
        return FlightPassenger(
            type=PassengerType.ADULT,
            given_name="John",
            family_name="Doe",
            title="Mr",
            date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
            email="john.doe@example.com",
            phone="+1234567890",
        )

    @pytest.fixture
    def sample_flight_search_request(self, sample_flight_passenger: FlightPassenger) -> FlightSearchRequest:
        """Sample flight search request."""
        return FlightSearchRequest(
            origin="JFK",
            destination="CDG",
            departure_date=datetime.now(timezone.utc) + timedelta(days=30),
            return_date=datetime.now(timezone.utc) + timedelta(days=37),
            passengers=[sample_flight_passenger],
            cabin_class=CabinClass.ECONOMY,
            max_stops=1,
            max_price=2000.00,
            currency="USD",
            preferred_airlines=["AF", "DL"],
            flexible_dates=True,
        )

    @pytest.fixture
    def sample_flight_segment(self) -> FlightSegment:
        """Sample flight segment."""
        now = datetime.now(timezone.utc)
        return FlightSegment(
            origin="JFK",
            destination="CDG",
            departure_date=now + timedelta(days=30, hours=10),
            arrival_date=now + timedelta(days=30, hours=18),
            airline="AF",
            flight_number="AF007",
            aircraft_type="Boeing 777-300ER",
            duration_minutes=480,
        )

    @pytest.fixture
    def sample_flight_offer(self, sample_flight_segment: FlightSegment) -> FlightOffer:
        """Sample flight offer."""
        offer_id = str(uuid4())

        return FlightOffer(
            id=offer_id,
            search_id=str(uuid4()),
            outbound_segments=[sample_flight_segment],
            return_segments=[],
            total_price=1250.00,
            base_price=950.00,
            taxes=300.00,
            currency="USD",
            cabin_class=CabinClass.ECONOMY,
            booking_class="Y",
            total_duration=480,
            stops_count=0,
            airlines=["AF"],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            bookable=True,
            source="duffel",
            source_offer_id="duffel_offer_123",
            score=0.85,
            price_score=0.9,
            convenience_score=0.8,
        )

    @pytest.fixture
    def sample_flight_booking(
        self, sample_flight_offer: FlightOffer, sample_flight_passenger: FlightPassenger
    ) -> FlightBooking:
        """Sample flight booking."""
        booking_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return FlightBooking(
            id=booking_id,
            user_id=user_id,
            trip_id=str(uuid4()),
            offer_id=sample_flight_offer.id,
            confirmation_number="ABC123",
            passengers=[sample_flight_passenger],
            outbound_segments=sample_flight_offer.outbound_segments,
            return_segments=sample_flight_offer.return_segments,
            total_price=sample_flight_offer.total_price,
            currency=sample_flight_offer.currency,
            status=BookingStatus.BOOKED,
            booked_at=now,
            expires_at=sample_flight_offer.expires_at,
            cancellable=True,
            refundable=False,
            metadata={"booking_source": "web", "payment_method": "credit_card"},
        )

    # Test Search Operations

    @pytest.mark.asyncio
    async def test_search_flights_returns_offers_successfully(
        self,
        flight_service: FlightService,
        mock_external_flight_service: AsyncMock,
        mock_database_service: AsyncMock,
        sample_flight_search_request: FlightSearchRequest,
        sample_flight_offer: FlightOffer,
    ):
        """Test successful flight search."""
        # Arrange
        external_offers = [
            {
                "id": sample_flight_offer.id,
                "total_amount": 1250.00,
                "total_currency": "USD",
                "segments": [sample_flight_offer.outbound_segments[0].model_dump()],
            }
        ]
        mock_external_flight_service.search_flights.return_value = external_offers
        mock_database_service.store_flight_search.return_value = None

        # Act
        result = await flight_service.search_flights(sample_flight_search_request)

        # Assert
        assert isinstance(result, FlightSearchResponse)
        assert len(result.offers) == 1
        assert result.offers[0].total_price == 1250.00
        assert result.total_results == 1
        assert result.cached is False
        mock_external_flight_service.search_flights.assert_called_once()
        mock_database_service.store_flight_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_flights_returns_cached_results_when_available(
        self,
        flight_service: FlightService,
        sample_flight_search_request: FlightSearchRequest,
        sample_flight_offer: FlightOffer,
    ):
        """Test flight search with cached results."""
        # Arrange - Populate cache
        cache_key = flight_service._generate_search_cache_key(sample_flight_search_request)
        flight_service._cache_search_results(cache_key, [sample_flight_offer])

        # Act
        result = await flight_service.search_flights(sample_flight_search_request)

        # Assert
        assert len(result.offers) == 1
        assert result.cached is True
        assert flight_service.external_service.search_flights.called is False

    @pytest.mark.asyncio
    async def test_search_flights_invalid_dates_raises_validation_error(self, sample_flight_passenger: FlightPassenger):
        """Test flight search with validation errors."""
        # Act & Assert
        with pytest.raises(ValueError, match="Return date must be after departure date"):
            FlightSearchRequest(
                origin="JFK",
                destination="CDG",
                departure_date=datetime.now(timezone.utc) + timedelta(days=30),
                return_date=(datetime.now(timezone.utc) + timedelta(days=25)),  # Before departure
                passengers=[sample_flight_passenger],
            )

    @pytest.mark.asyncio
    async def test_search_flights_returns_empty_when_no_results(
        self,
        flight_service: FlightService,
        mock_external_flight_service: AsyncMock,
        sample_flight_search_request: FlightSearchRequest,
    ):
        """Test flight search with no results."""
        # Arrange
        mock_external_flight_service.search_flights.return_value = []

        # Act
        result = await flight_service.search_flights(sample_flight_search_request)

        # Assert
        assert len(result.offers) == 0
        assert result.total_results == 0

    # Test Get Offer Details

    @pytest.mark.asyncio
    async def test_get_offer_details_returns_offer_when_found(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        sample_flight_offer: FlightOffer,
        sample_user_id: str,
    ):
        """Test successful flight offer retrieval."""
        # Arrange
        mock_database_service.get_flight_offer.return_value = sample_flight_offer.model_dump()

        # Act
        result = await flight_service.get_offer_details(sample_flight_offer.id, sample_user_id)

        # Assert
        assert result is not None
        assert result.id == sample_flight_offer.id
        assert result.total_price == sample_flight_offer.total_price
        mock_database_service.get_flight_offer.assert_called_once_with(sample_flight_offer.id, sample_user_id)

    @pytest.mark.asyncio
    async def test_get_offer_details_returns_none_when_not_found(
        self, flight_service: FlightService, mock_database_service: AsyncMock
    ):
        """Test flight offer retrieval when offer doesn't exist."""
        # Arrange
        offer_id = str(uuid4())
        user_id = str(uuid4())
        mock_database_service.get_flight_offer.return_value = None

        # Act
        result = await flight_service.get_offer_details(offer_id, user_id)

        # Assert
        assert result is None

    # Test Booking Operations

    @pytest.mark.asyncio
    async def test_book_flight_creates_booking_successfully(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        mock_external_flight_service: AsyncMock,
        sample_flight_offer: FlightOffer,
        sample_flight_passenger: FlightPassenger,
        sample_user_id: str,
    ):
        """Test successful flight booking."""
        # Arrange
        booking_request = FlightBookingRequest(
            offer_id=sample_flight_offer.id,
            passengers=[sample_flight_passenger],
            trip_id=str(uuid4()),
        )

        mock_database_service.get_flight_offer.return_value = sample_flight_offer.model_dump()
        external_booking = {
            "booking_reference": "ABC123",
            "cancellable": True,
            "refundable": False,
        }
        mock_external_flight_service.create_order.return_value = external_booking
        mock_database_service.store_flight_booking.return_value = None

        # Act
        result = await flight_service.book_flight(sample_user_id, booking_request)

        # Assert
        assert isinstance(result, FlightBooking)
        assert result.user_id == sample_user_id
        assert result.offer_id == sample_flight_offer.id
        assert result.status == BookingStatus.BOOKED
        assert result.confirmation_number == "ABC123"
        assert len(result.passengers) == 1
        mock_external_flight_service.create_order.assert_called_once()
        mock_database_service.store_flight_booking.assert_called_once()

    @pytest.mark.asyncio
    async def test_book_flight_fails_when_offer_expired(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        sample_flight_offer: FlightOffer,
        sample_flight_passenger: FlightPassenger,
        sample_user_id: str,
    ):
        """Test flight booking with expired offer."""
        # Arrange
        sample_flight_offer.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        booking_request = FlightBookingRequest(offer_id=sample_flight_offer.id, passengers=[sample_flight_passenger])
        mock_database_service.get_flight_offer.return_value = sample_flight_offer.model_dump()

        # Act & Assert
        with pytest.raises(ValidationError, match="Flight offer has expired"):
            await flight_service.book_flight(sample_user_id, booking_request)

    @pytest.mark.asyncio
    async def test_book_flight_hold_only_creates_hold_booking(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        sample_flight_offer: FlightOffer,
        sample_flight_passenger: FlightPassenger,
        sample_user_id: str,
    ):
        """Test flight booking with hold only option."""
        # Arrange
        booking_request = FlightBookingRequest(
            offer_id=sample_flight_offer.id,
            passengers=[sample_flight_passenger],
            hold_only=True,
        )
        mock_database_service.get_flight_offer.return_value = sample_flight_offer.model_dump()
        mock_database_service.store_flight_booking.return_value = None

        # Act
        result = await flight_service.book_flight(sample_user_id, booking_request)

        # Assert
        assert result.status == BookingStatus.HOLD
        assert flight_service.external_service.create_order.called is False

    # Test User Bookings

    @pytest.mark.asyncio
    async def test_get_user_bookings_returns_list_of_bookings(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        sample_flight_booking: FlightBooking,
    ):
        """Test successful user bookings retrieval."""
        # Arrange
        user_id = sample_flight_booking.user_id
        mock_database_service.get_flight_bookings.return_value = [sample_flight_booking.model_dump()]

        # Act
        results = await flight_service.get_user_bookings(user_id)

        # Assert
        assert len(results) == 1
        assert results[0].id == sample_flight_booking.id
        assert results[0].status == sample_flight_booking.status
        mock_database_service.get_flight_bookings.assert_called_once()

    # Test Cancellation

    @pytest.mark.asyncio
    async def test_cancel_booking_succeeds_when_allowed(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        sample_flight_booking: FlightBooking,
    ):
        """Test successful booking cancellation."""
        # Arrange
        mock_database_service.get_flight_booking.return_value = sample_flight_booking.model_dump()
        mock_database_service.update_flight_booking.return_value = True

        # Act
        result = await flight_service.cancel_booking(sample_flight_booking.id, sample_flight_booking.user_id)

        # Assert
        assert result is True
        mock_database_service.update_flight_booking.assert_called_once_with(
            sample_flight_booking.id, {"status": BookingStatus.CANCELLED.value}
        )

    @pytest.mark.asyncio
    async def test_cancel_booking_fails_when_already_cancelled(
        self,
        flight_service: FlightService,
        mock_database_service: AsyncMock,
        sample_flight_booking: FlightBooking,
    ):
        """Test booking cancellation when already cancelled."""
        # Arrange
        sample_flight_booking.status = BookingStatus.CANCELLED
        mock_database_service.get_flight_booking.return_value = sample_flight_booking.model_dump()

        # Act & Assert
        with pytest.raises(ValidationError, match="Booking is already cancelled or expired"):
            await flight_service.cancel_booking(sample_flight_booking.id, sample_flight_booking.user_id)

    # Test Mock Offers

    @pytest.mark.asyncio
    async def test_search_flights_generates_mock_offers_without_external_service(
        self,
        flight_service: FlightService,
        sample_flight_search_request: FlightSearchRequest,
    ):
        """Test flight search with mock offers when no external service."""
        # Arrange
        flight_service.external_service = None

        # Act
        result = await flight_service.search_flights(sample_flight_search_request)

        # Assert
        assert len(result.offers) > 0
        assert all(offer.source == "mock" for offer in result.offers)

    # Test Scoring

    @pytest.mark.asyncio
    async def test_score_offers_ranks_by_composite_score(
        self,
        flight_service: FlightService,
        sample_flight_search_request: FlightSearchRequest,
    ):
        """Test offer scoring algorithm."""
        # Arrange
        offers = [
            FlightOffer(
                id=str(uuid4()),
                outbound_segments=[],
                total_price=1500.00,
                currency="USD",
                cabin_class=CabinClass.ECONOMY,
                stops_count=0,
                airlines=["AA"],
            ),
            FlightOffer(
                id=str(uuid4()),
                outbound_segments=[],
                total_price=1200.00,
                currency="USD",
                cabin_class=CabinClass.ECONOMY,
                stops_count=1,
                airlines=["AA"],
            ),
            FlightOffer(
                id=str(uuid4()),
                outbound_segments=[],
                total_price=1800.00,
                currency="USD",
                cabin_class=CabinClass.ECONOMY,
                stops_count=0,
                airlines=["AA"],
            ),
        ]

        # Act
        scored_offers = await flight_service._score_offers(offers, sample_flight_search_request)

        # Assert
        assert all(hasattr(offer, "score") for offer in scored_offers)
        assert scored_offers[0].score >= scored_offers[1].score
        assert scored_offers[1].score >= scored_offers[2].score

    # Test Validation

    def test_airport_code_validation_accepts_valid_codes(self):
        """Test airport code validation."""
        # Arrange & Act
        segment = FlightSegment(
            origin="JFK",
            destination="CDG",
            departure_date=datetime.now(timezone.utc),
            arrival_date=datetime.now(timezone.utc) + timedelta(hours=8),
        )

        # Assert
        assert segment.origin == "JFK"
        assert segment.destination == "CDG"

    def test_airport_code_validation_rejects_invalid_codes(self):
        """Test airport code validation with invalid codes."""
        # Act & Assert - Too long
        with pytest.raises(ValueError, match="Airport code must be 3 letters"):
            FlightSegment(
                origin="JFKK",  # Too long
                destination="CDG",
                departure_date=datetime.now(timezone.utc),
                arrival_date=datetime.now(timezone.utc) + timedelta(hours=8),
            )

        # Act & Assert - Contains number
        with pytest.raises(ValueError, match="Airport code must be 3 letters"):
            FlightSegment(
                origin="J1K",  # Contains number
                destination="CDG",
                departure_date=datetime.now(timezone.utc),
                arrival_date=datetime.now(timezone.utc) + timedelta(hours=8),
            )

    def test_passenger_email_validation_accepts_valid_email(self):
        """Test passenger email validation."""
        # Arrange & Act
        passenger = FlightPassenger(type=PassengerType.ADULT, email="john@example.com")

        # Assert
        assert passenger.email == "john@example.com"

    def test_passenger_email_validation_rejects_invalid_email(self):
        """Test passenger email validation with invalid email."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email format"):
            FlightPassenger(type=PassengerType.ADULT, email="invalid-email")

    def test_booking_request_requires_complete_passenger_info(self):
        """Test booking request validation."""
        # Arrange - Complete passenger info
        passenger = FlightPassenger(type=PassengerType.ADULT, given_name="John", family_name="Doe")
        request = FlightBookingRequest(offer_id=str(uuid4()), passengers=[passenger])

        # Assert
        assert request.passengers[0].given_name == "John"

        # Arrange - Incomplete passenger info
        incomplete_passenger = FlightPassenger(
            type=PassengerType.ADULT,
            given_name="John",  # Missing family name
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Given name and family name are required for booking"):
            FlightBookingRequest(offer_id=str(uuid4()), passengers=[incomplete_passenger])

    # Test Error Handling

    @pytest.mark.asyncio
    async def test_service_handles_external_api_errors(
        self,
        flight_service: FlightService,
        mock_external_flight_service: AsyncMock,
        sample_flight_search_request: FlightSearchRequest,
    ):
        """Test service error handling."""
        # Arrange
        mock_external_flight_service.search_flights.side_effect = Exception("External API error")

        # Act
        result = await flight_service.search_flights(sample_flight_search_request)

        # Assert - The service returns empty results on error instead of raising
        assert result.offers == []
        assert result.total_results == 0

    # Test Dependency Injection

    @pytest.mark.asyncio
    async def test_get_flight_service_with_mocked_dependencies(
        self, mock_database_service: AsyncMock, mock_external_flight_service: AsyncMock
    ):
        """Test creating flight service with dependencies."""
        # Act
        service = FlightService(
            database_service=mock_database_service,
            external_flight_service=mock_external_flight_service,
        )

        # Assert
        assert isinstance(service, FlightService)

    # Test Cache Key Generation

    def test_cache_key_generation_is_deterministic(
        self,
        flight_service: FlightService,
        sample_flight_search_request: FlightSearchRequest,
    ):
        """Test cache key generation."""
        # Act
        key1 = flight_service._generate_search_cache_key(sample_flight_search_request)
        key2 = flight_service._generate_search_cache_key(sample_flight_search_request)

        # Assert - Same request should generate same key
        assert key1 == key2

        # Act - Different request should generate different key
        sample_flight_search_request.origin = "LAX"
        key3 = flight_service._generate_search_cache_key(sample_flight_search_request)

        # Assert
        assert key1 != key3

    # Test External API Conversion

    @pytest.mark.asyncio
    async def test_external_api_conversion_preserves_data(self, flight_service: FlightService):
        """Test external API response conversion."""
        # Arrange
        external_offer = {
            "id": "ext_123",
            "total_amount": 1500.00,
            "total_currency": "USD",
        }

        # Act
        converted = await flight_service._convert_external_offer(external_offer)

        # Assert
        assert isinstance(converted, FlightOffer)
        assert converted.total_price == 1500.00
        assert converted.currency == "USD"
        assert converted.source == "external_api"
        assert converted.source_offer_id == "ext_123"

    # Property-based Testing

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        price=st.floats(min_value=100.0, max_value=10000.0),
        stops=st.integers(min_value=0, max_value=3),
        duration=st.integers(min_value=60, max_value=1440),
    )
    def test_offer_scoring_within_bounds(
        self,
        mock_database_service: AsyncMock,
        mock_external_flight_service: AsyncMock,
        price: float,
        stops: int,
        duration: int,
    ):
        """Test that offer scores are always between 0 and 1."""
        # Arrange - Create a fresh service instance for each test case
        flight_service = FlightService(
            database_service=mock_database_service,
            external_flight_service=mock_external_flight_service,
        )

        offer = FlightOffer(
            id=str(uuid4()),
            outbound_segments=[],
            total_price=price,
            currency="USD",
            cabin_class=CabinClass.ECONOMY,
            stops_count=stops,
            total_duration=duration,
            airlines=["AA"],
        )

        # Act
        if hasattr(flight_service, "_calculate_offer_score"):
            score = flight_service._calculate_offer_score(offer, max_price=10000.0)

            # Assert
            assert 0 <= score <= 1

    # Edge Cases

    @pytest.mark.asyncio
    async def test_search_with_very_long_date_range(
        self, flight_service: FlightService, sample_flight_passenger: FlightPassenger
    ):
        """Test search with very long date range."""
        # Arrange
        search_request = FlightSearchRequest(
            origin="JFK",
            destination="CDG",
            departure_date=datetime.now(timezone.utc) + timedelta(days=30),
            return_date=(datetime.now(timezone.utc) + timedelta(days=365)),  # One year later
            passengers=[sample_flight_passenger],
        )

        # Act
        result = await flight_service.search_flights(search_request)

        # Assert
        assert isinstance(result, FlightSearchResponse)

    @pytest.mark.asyncio
    async def test_search_with_many_passengers(self, flight_service: FlightService):
        """Test search with maximum number of passengers."""
        # Arrange
        passengers = [
            FlightPassenger(
                type=PassengerType.ADULT,
                given_name=f"Passenger{i}",
                family_name="Test",
            )
            for i in range(9)  # Most airlines limit to 9 passengers
        ]

        search_request = FlightSearchRequest(
            origin="JFK",
            destination="CDG",
            departure_date=datetime.now(timezone.utc) + timedelta(days=30),
            passengers=passengers,
        )

        # Act
        result = await flight_service.search_flights(search_request)

        # Assert
        assert isinstance(result, FlightSearchResponse)
