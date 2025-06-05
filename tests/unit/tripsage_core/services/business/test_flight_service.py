"""
Comprehensive tests for FlightService.

This module provides full test coverage for flight management operations
including flight search, booking, cancellation, and external API integration.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
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
    get_flight_service,
)


class TestFlightService:
    """Test suite for FlightService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_external_flight_service(self):
        """Mock external flight service (Duffel)."""
        external = AsyncMock()
        return external

    @pytest.fixture
    def flight_service(self, mock_database_service, mock_external_flight_service):
        """Create FlightService instance with mocked dependencies."""
        return FlightService(
            database_service=mock_database_service,
            external_flight_service=mock_external_flight_service,
            cache_ttl=300,
        )

    @pytest.fixture
    def sample_flight_passenger(self):
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
    def sample_flight_search_request(self, sample_flight_passenger):
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
    def sample_flight_segment(self):
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
    def sample_flight_offer(self, sample_flight_segment):
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
    def sample_flight_booking(self, sample_flight_offer, sample_flight_passenger):
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

    @pytest.mark.asyncio
    async def test_search_flights_success(
        self,
        flight_service,
        mock_external_flight_service,
        sample_flight_search_request,
        sample_flight_offer,
    ):
        """Test successful flight search."""
        # Mock external API response
        external_offers = [
            {
                "id": sample_flight_offer.id,
                "total_amount": 1250.00,
                "total_currency": "USD",
                "segments": [sample_flight_offer.outbound_segments[0].model_dump()],
            }
        ]
        mock_external_flight_service.search_flights.return_value = external_offers

        # Mock database storage
        mock_database_service = flight_service.db
        mock_database_service.store_flight_search.return_value = None

        result = await flight_service.search_flights(sample_flight_search_request)

        # Assertions
        assert isinstance(result, FlightSearchResponse)
        assert len(result.offers) == 1
        assert result.offers[0].total_price == 1250.00
        assert result.total_results == 1
        assert result.cached is False

        # Verify service calls
        mock_external_flight_service.search_flights.assert_called_once()
        mock_database_service.store_flight_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_flights_cached_results(
        self, flight_service, sample_flight_search_request, sample_flight_offer
    ):
        """Test flight search with cached results."""
        # First search to populate cache
        flight_service._cache_search_results(
            flight_service._generate_search_cache_key(sample_flight_search_request),
            [sample_flight_offer],
        )

        result = await flight_service.search_flights(sample_flight_search_request)

        assert len(result.offers) == 1
        assert result.cached is True

        # Should not call external service
        assert flight_service.external_service.search_flights.called is False

    @pytest.mark.asyncio
    async def test_search_flights_validation_error(
        self, flight_service, sample_flight_passenger
    ):
        """Test flight search with validation errors."""
        # Set invalid dates (return date before departure)
        with pytest.raises(
            ValueError, match="Return date must be after departure date"
        ):
            FlightSearchRequest(
                origin="JFK",
                destination="CDG",
                departure_date=datetime.now(timezone.utc) + timedelta(days=30),
                return_date=datetime.now(timezone.utc)
                + timedelta(days=25),  # Before departure
                passengers=[sample_flight_passenger],
            )

    @pytest.mark.asyncio
    async def test_search_flights_no_results(
        self, flight_service, mock_external_flight_service, sample_flight_search_request
    ):
        """Test flight search with no results."""
        mock_external_flight_service.search_flights.return_value = []

        result = await flight_service.search_flights(sample_flight_search_request)

        assert len(result.offers) == 0
        assert result.total_results == 0

    @pytest.mark.asyncio
    async def test_get_offer_details_success(
        self, flight_service, mock_database_service, sample_flight_offer
    ):
        """Test successful flight offer retrieval."""
        user_id = str(uuid4())
        mock_database_service.get_flight_offer.return_value = (
            sample_flight_offer.model_dump()
        )

        result = await flight_service.get_offer_details(sample_flight_offer.id, user_id)

        assert result is not None
        assert result.id == sample_flight_offer.id
        assert result.total_price == sample_flight_offer.total_price
        mock_database_service.get_flight_offer.assert_called_once_with(
            sample_flight_offer.id, user_id
        )

    @pytest.mark.asyncio
    async def test_get_offer_details_not_found(
        self, flight_service, mock_database_service
    ):
        """Test flight offer retrieval when offer doesn't exist."""
        offer_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_flight_offer.return_value = None

        result = await flight_service.get_offer_details(offer_id, user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_book_flight_success(
        self,
        flight_service,
        mock_database_service,
        mock_external_flight_service,
        sample_flight_offer,
        sample_flight_passenger,
    ):
        """Test successful flight booking."""
        user_id = str(uuid4())

        booking_request = FlightBookingRequest(
            offer_id=sample_flight_offer.id,
            passengers=[sample_flight_passenger],
            trip_id=str(uuid4()),
        )

        # Mock offer retrieval
        mock_database_service.get_flight_offer.return_value = (
            sample_flight_offer.model_dump()
        )

        # Mock external booking
        external_booking = {
            "booking_reference": "ABC123",
            "cancellable": True,
            "refundable": False,
        }
        mock_external_flight_service.create_order.return_value = external_booking

        # Mock database storage
        mock_database_service.store_flight_booking.return_value = None

        result = await flight_service.book_flight(user_id, booking_request)

        # Assertions
        assert isinstance(result, FlightBooking)
        assert result.user_id == user_id
        assert result.offer_id == sample_flight_offer.id
        assert result.status == BookingStatus.BOOKED
        assert result.confirmation_number == "ABC123"
        assert len(result.passengers) == 1

        # Verify service calls
        mock_external_flight_service.create_order.assert_called_once()
        mock_database_service.store_flight_booking.assert_called_once()

    @pytest.mark.asyncio
    async def test_book_flight_offer_expired(
        self,
        flight_service,
        mock_database_service,
        sample_flight_offer,
        sample_flight_passenger,
    ):
        """Test flight booking with expired offer."""
        user_id = str(uuid4())

        # Set offer as expired
        sample_flight_offer.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        booking_request = FlightBookingRequest(
            offer_id=sample_flight_offer.id, passengers=[sample_flight_passenger]
        )

        mock_database_service.get_flight_offer.return_value = (
            sample_flight_offer.model_dump()
        )

        with pytest.raises(ValidationError, match="Flight offer has expired"):
            await flight_service.book_flight(user_id, booking_request)

    @pytest.mark.asyncio
    async def test_book_flight_hold_only(
        self,
        flight_service,
        mock_database_service,
        sample_flight_offer,
        sample_flight_passenger,
    ):
        """Test flight booking with hold only option."""
        user_id = str(uuid4())

        booking_request = FlightBookingRequest(
            offer_id=sample_flight_offer.id,
            passengers=[sample_flight_passenger],
            hold_only=True,
        )

        mock_database_service.get_flight_offer.return_value = (
            sample_flight_offer.model_dump()
        )
        mock_database_service.store_flight_booking.return_value = None

        result = await flight_service.book_flight(user_id, booking_request)

        assert result.status == BookingStatus.HOLD
        # Should not call external booking service for hold
        assert flight_service.external_service.create_order.called is False

    @pytest.mark.asyncio
    async def test_get_user_bookings_success(
        self, flight_service, mock_database_service, sample_flight_booking
    ):
        """Test successful user bookings retrieval."""
        user_id = sample_flight_booking.user_id

        mock_database_service.get_flight_bookings.return_value = [
            sample_flight_booking.model_dump()
        ]

        results = await flight_service.get_user_bookings(user_id)

        assert len(results) == 1
        assert results[0].id == sample_flight_booking.id
        assert results[0].status == sample_flight_booking.status
        mock_database_service.get_flight_bookings.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_booking_success(
        self,
        flight_service,
        mock_database_service,
        mock_external_flight_service,
        sample_flight_booking,
    ):
        """Test successful booking cancellation."""
        mock_database_service.get_flight_booking.return_value = (
            sample_flight_booking.model_dump()
        )
        mock_database_service.update_flight_booking.return_value = True

        result = await flight_service.cancel_booking(
            sample_flight_booking.id, sample_flight_booking.user_id
        )

        assert result is True
        mock_database_service.update_flight_booking.assert_called_once_with(
            sample_flight_booking.id, {"status": BookingStatus.CANCELLED.value}
        )

    @pytest.mark.asyncio
    async def test_cancel_booking_already_cancelled(
        self, flight_service, mock_database_service, sample_flight_booking
    ):
        """Test booking cancellation when already cancelled."""
        # Set booking as already cancelled
        sample_flight_booking.status = BookingStatus.CANCELLED

        mock_database_service.get_flight_booking.return_value = (
            sample_flight_booking.model_dump()
        )

        with pytest.raises(
            ValidationError, match="Booking is already cancelled or expired"
        ):
            await flight_service.cancel_booking(
                sample_flight_booking.id, sample_flight_booking.user_id
            )

    @pytest.mark.asyncio
    async def test_search_flights_mock_offers(
        self, flight_service, sample_flight_search_request
    ):
        """Test flight search with mock offers when no external service."""
        # Remove external service
        flight_service.external_service = None

        result = await flight_service.search_flights(sample_flight_search_request)

        # Should generate mock offers
        assert len(result.offers) > 0
        assert all(offer.source == "mock" for offer in result.offers)

    @pytest.mark.asyncio
    async def test_score_offers(self, flight_service, sample_flight_search_request):
        """Test offer scoring algorithm."""
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

        scored_offers = await flight_service._score_offers(
            offers, sample_flight_search_request
        )

        # Should be ranked by score
        assert all(hasattr(offer, "score") for offer in scored_offers)
        assert scored_offers[0].score >= scored_offers[1].score
        assert scored_offers[1].score >= scored_offers[2].score

    def test_airport_code_validation(self):
        """Test airport code validation."""
        # Valid codes
        segment = FlightSegment(
            origin="JFK",
            destination="CDG",
            departure_date=datetime.now(timezone.utc),
            arrival_date=datetime.now(timezone.utc) + timedelta(hours=8),
        )
        assert segment.origin == "JFK"
        assert segment.destination == "CDG"

        # Invalid codes
        with pytest.raises(ValueError, match="Airport code must be 3 letters"):
            FlightSegment(
                origin="JFKK",  # Too long
                destination="CDG",
                departure_date=datetime.now(timezone.utc),
                arrival_date=datetime.now(timezone.utc) + timedelta(hours=8),
            )

        with pytest.raises(ValueError, match="Airport code must be 3 letters"):
            FlightSegment(
                origin="J1K",  # Contains number
                destination="CDG",
                departure_date=datetime.now(timezone.utc),
                arrival_date=datetime.now(timezone.utc) + timedelta(hours=8),
            )

    def test_passenger_email_validation(self):
        """Test passenger email validation."""
        # Valid email
        passenger = FlightPassenger(type=PassengerType.ADULT, email="john@example.com")
        assert passenger.email == "john@example.com"

        # Invalid email
        with pytest.raises(ValueError, match="Invalid email format"):
            FlightPassenger(type=PassengerType.ADULT, email="invalid-email")

    def test_booking_request_validation(self):
        """Test booking request validation."""
        # Complete passenger info
        passenger = FlightPassenger(
            type=PassengerType.ADULT, given_name="John", family_name="Doe"
        )

        request = FlightBookingRequest(offer_id=str(uuid4()), passengers=[passenger])
        assert request.passengers[0].given_name == "John"

        # Incomplete passenger info
        incomplete_passenger = FlightPassenger(
            type=PassengerType.ADULT,
            given_name="John",  # Missing family name
        )

        with pytest.raises(
            ValueError, match="Given name and family name are required for booking"
        ):
            FlightBookingRequest(
                offer_id=str(uuid4()), passengers=[incomplete_passenger]
            )

    @pytest.mark.asyncio
    async def test_service_error_handling(
        self, flight_service, mock_external_flight_service, sample_flight_search_request
    ):
        """Test service error handling."""
        # Mock external service to raise an exception
        mock_external_flight_service.search_flights.side_effect = Exception(
            "External API error"
        )

        with pytest.raises(ServiceError, match="Flight search failed"):
            await flight_service.search_flights(sample_flight_search_request)

    @pytest.mark.asyncio
    async def test_get_flight_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_flight_service()
        assert isinstance(service, FlightService)

    def test_cache_key_generation(self, flight_service, sample_flight_search_request):
        """Test cache key generation."""
        key1 = flight_service._generate_search_cache_key(sample_flight_search_request)
        key2 = flight_service._generate_search_cache_key(sample_flight_search_request)

        # Same request should generate same key
        assert key1 == key2

        # Different request should generate different key
        sample_flight_search_request.origin = "LAX"
        key3 = flight_service._generate_search_cache_key(sample_flight_search_request)
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_external_api_conversion(
        self, flight_service, mock_external_flight_service, sample_flight_search_request
    ):
        """Test external API response conversion."""
        external_offer = {
            "id": "ext_123",
            "total_amount": 1500.00,
            "total_currency": "USD",
        }

        converted = await flight_service._convert_external_offer(external_offer)

        assert isinstance(converted, FlightOffer)
        assert converted.total_price == 1500.00
        assert converted.currency == "USD"
        assert converted.source == "external_api"
        assert converted.source_offer_id == "ext_123"
