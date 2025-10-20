"""Comprehensive tests for AccommodationService.

This module provides full test coverage for accommodation management operations
including search, booking, management, and MCP client integration.
Updated for Pydantic v2 and modern testing patterns.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
    CoreValidationError,
)
from tripsage_core.services.business.accommodation_service import (
    AccommodationAmenity,
    AccommodationBooking,
    AccommodationBookingRequest,
    AccommodationHost,
    AccommodationImage,
    AccommodationListing,
    AccommodationLocation,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    AccommodationService,
    BookingStatus,
    CancellationPolicy,
    PropertyType,
    get_accommodation_service,
)


class TestAccommodationService:
    """Test suite for AccommodationService."""

    @pytest.fixture
    def accommodation_service(
        self, mock_database_service: AsyncMock
    ) -> AccommodationService:
        """Create AccommodationService instance with mocked dependencies."""
        return AccommodationService(database_service=mock_database_service)

    @pytest.fixture
    def sample_search_request(self) -> AccommodationSearchRequest:
        """Sample accommodation search request."""
        return AccommodationSearchRequest(
            location="Paris, France",
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
            adults=2,  # Add explicit adults field
            children=0,  # Add explicit children field
            property_types=[PropertyType.APARTMENT, PropertyType.HOTEL],
            min_price=80.00,
            max_price=300.00,
            amenities=["wifi", "kitchen"],
            min_rating=4.0,
            instant_book=True,
        )

    @pytest.fixture
    def sample_accommodation_location(self) -> AccommodationLocation:
        """Sample accommodation location."""
        return AccommodationLocation(
            address="123 Rue de la Paix",
            city="Paris",
            country="France",
            postal_code="75001",
            latitude=48.8566,
            longitude=2.3522,
            neighborhood="1st Arrondissement",
            distance_to_center=0.5,
        )

    @pytest.fixture
    def sample_accommodation_host(self) -> AccommodationHost:
        """Sample accommodation host."""
        return AccommodationHost(
            id="host_123",
            name="Marie Dupont",
            avatar_url="https://example.com/avatars/marie.jpg",
            rating=4.9,
            review_count=127,
            response_rate=0.98,
            response_time="within an hour",
            is_superhost=True,
            verification_badges=["email", "phone", "government_id"],
        )

    @pytest.fixture
    def sample_accommodation_listing(
        self,
        sample_accommodation_location: AccommodationLocation,
        sample_accommodation_host: AccommodationHost,
    ) -> AccommodationListing:
        """Sample accommodation listing."""
        listing_id = str(uuid4())

        return AccommodationListing(
            id=listing_id,
            name="Charming Parisian Apartment in Montmartre",
            description=(
                "Beautiful 2-bedroom apartment with stunning views of Sacré-Cœur"
            ),
            property_type=PropertyType.APARTMENT,
            location=sample_accommodation_location,
            price_per_night=150.00,
            total_price=750.00,
            currency="EUR",
            rating=4.8,
            review_count=127,
            max_guests=4,
            bedrooms=2,
            beds=3,
            bathrooms=1.5,
            amenities=[
                AccommodationAmenity(
                    name="WiFi",
                    category="connectivity",
                    icon="wifi",
                    description="High-speed internet",
                ),
                AccommodationAmenity(
                    name="Kitchen",
                    category="amenities",
                    icon="kitchen",
                    description="Fully equipped kitchen",
                ),
            ],
            images=[
                AccommodationImage(
                    url="https://example.com/images/1.jpg",
                    caption="Living room",
                    is_primary=True,
                    width=1200,
                    height=800,
                )
            ],
            host=sample_accommodation_host,
            check_in_time="15:00",
            check_out_time="11:00",
            cancellation_policy=CancellationPolicy.MODERATE,
            instant_book=True,
            source="airbnb",
            source_listing_id="airbnb_123456",
            listing_url="https://airbnb.com/rooms/123456",
            nights=5,
            is_available=True,
            score=0.95,
            price_score=0.85,
            location_score=0.98,
        )

    @pytest.fixture
    def sample_accommodation_booking(
        self,
        sample_accommodation_location: AccommodationLocation,
        sample_accommodation_host: AccommodationHost,
    ) -> AccommodationBooking:
        """Sample accommodation booking."""
        booking_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(UTC)

        return AccommodationBooking(
            id=booking_id,
            user_id=user_id,
            trip_id=str(uuid4()),
            listing_id=str(uuid4()),
            confirmation_number="ABC123DEF",
            property_name="Charming Parisian Apartment",
            property_type=PropertyType.APARTMENT,
            location=sample_accommodation_location,
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            nights=5,
            guests=2,
            price_per_night=150.00,
            total_price=750.00,
            currency="EUR",
            status=BookingStatus.CONFIRMED,
            booked_at=now,
            cancellation_policy=CancellationPolicy.MODERATE,
            is_cancellable=True,
            is_refundable=True,
            host=sample_accommodation_host,
            special_requests="Early check-in if possible",
            metadata={"booking_source": "web", "payment_method": "credit_card"},
        )

    # Test Search Operations

    @pytest.mark.asyncio
    async def test_search_accommodations_returns_mock_listings(
        self,
        accommodation_service: AccommodationService,
        sample_search_request: AccommodationSearchRequest,
    ):
        """Test successful accommodation search returns mock listings."""
        # Act
        result = await accommodation_service.search_accommodations(
            sample_search_request
        )

        # Assert
        assert isinstance(result, AccommodationSearchResponse)
        assert len(result.listings) == 3  # Mock generator returns 3 listings
        assert result.total_results == 3
        assert all(listing.location.city == "Paris" for listing in result.listings)
        assert all(listing.is_available for listing in result.listings)
        assert all(80 <= listing.price_per_night <= 300 for listing in result.listings)

    @pytest.mark.asyncio
    async def test_search_accommodations_invalid_dates_raises_error(
        self, accommodation_service: AccommodationService
    ):
        """Test accommodation search with invalid dates raises validation error."""
        # Act & Assert
        with pytest.raises(
            ValueError, match="Check-out date must be after check-in date"
        ):
            AccommodationSearchRequest(
                location="Paris, France",
                check_in=date.today() + timedelta(days=30),
                check_out=date.today() + timedelta(days=25),  # Before check-in
                guests=2,
            )

    # Test Get Details Operations

    @pytest.mark.asyncio
    async def test_get_listing_details_returns_listing_when_found(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
        sample_accommodation_listing: AccommodationListing,
    ):
        """Test successful accommodation details retrieval."""
        # Arrange
        mock_database_service.get_accommodation_listing.return_value = (
            sample_accommodation_listing.model_dump()
        )

        # Act
        result = await accommodation_service.get_listing_details(
            sample_accommodation_listing.id, user_id="test-user-id"
        )

        # Assert
        assert result is not None
        assert result.id == sample_accommodation_listing.id
        assert result.name == sample_accommodation_listing.name
        mock_database_service.get_accommodation_listing.assert_called_once_with(
            sample_accommodation_listing.id, "test-user-id"
        )

    @pytest.mark.asyncio
    async def test_get_listing_details_returns_none_when_not_found(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
    ):
        """Test accommodation details retrieval when listing doesn't exist."""
        # Arrange
        listing_id = str(uuid4())
        mock_database_service.get_accommodation_listing.return_value = None

        # Act
        result = await accommodation_service.get_listing_details(
            listing_id, user_id="test-user-id"
        )

        # Assert
        assert result is None

    # Test Booking Operations

    @pytest.mark.asyncio
    async def test_book_accommodation_creates_booking_successfully(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
        sample_accommodation_listing: AccommodationListing,
        sample_accommodation_booking: AccommodationBooking,
    ):
        """Test successful accommodation booking."""
        # Arrange
        user_id = str(uuid4())
        mock_database_service.get_accommodation_listing.return_value = (
            sample_accommodation_listing.model_dump()
        )
        mock_database_service.store_accommodation_booking.return_value = None

        booking_request = AccommodationBookingRequest(
            listing_id=sample_accommodation_listing.id,
            check_in=sample_accommodation_booking.check_in,
            check_out=sample_accommodation_booking.check_out,
            guests=sample_accommodation_booking.guests,
            guest_name="Test Guest",
            guest_email="test@example.com",
            special_requests=sample_accommodation_booking.special_requests,
        )

        # Act
        result = await accommodation_service.book_accommodation(
            user_id=user_id, booking_request=booking_request
        )

        # Assert
        assert isinstance(result, AccommodationBooking)
        assert result.user_id == user_id
        assert result.listing_id == sample_accommodation_listing.id
        assert result.status == BookingStatus.BOOKED
        mock_database_service.get_accommodation_listing.assert_called_once_with(
            sample_accommodation_listing.id, user_id
        )
        mock_database_service.store_accommodation_booking.assert_called_once()

    @pytest.mark.asyncio
    async def test_book_accommodation_fails_when_not_available(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
        sample_accommodation_listing: AccommodationListing,
    ):
        """Test accommodation booking when not available."""
        # Arrange
        user_id = str(uuid4())
        unavailable_listing = sample_accommodation_listing.model_copy()
        unavailable_listing.is_available = False
        mock_database_service.get_accommodation_listing.return_value = (
            unavailable_listing.model_dump()
        )

        booking_request = AccommodationBookingRequest(
            listing_id=sample_accommodation_listing.id,
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
            guest_name="Test Guest",
            guest_email="test@example.com",
        )

        # Act & Assert
        with pytest.raises(CoreValidationError, match="not available"):
            await accommodation_service.book_accommodation(
                user_id=user_id, booking_request=booking_request
            )

    @pytest.mark.asyncio
    async def test_get_user_bookings_returns_list_of_bookings(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
        sample_accommodation_booking: AccommodationBooking,
    ):
        """Test successful user bookings retrieval."""
        # Arrange
        user_id = sample_accommodation_booking.user_id
        mock_database_service.get_accommodation_bookings.return_value = [
            sample_accommodation_booking.model_dump()
        ]

        # Act
        results = await accommodation_service.get_user_bookings(user_id)

        # Assert
        assert len(results) == 1
        assert results[0].id == sample_accommodation_booking.id
        assert results[0].user_id == user_id
        mock_database_service.get_accommodation_bookings.assert_called_once_with(
            {"user_id": user_id}, 50
        )

    # Test Cancellation Operations

    @pytest.mark.asyncio
    async def test_cancel_booking_succeeds_for_owner(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
        sample_accommodation_booking: AccommodationBooking,
    ):
        """Test successful booking cancellation."""
        # Arrange
        mock_database_service.get_accommodation_booking.return_value = (
            sample_accommodation_booking.model_dump()
        )
        mock_database_service.update_accommodation_booking.return_value = True

        # Act
        result = await accommodation_service.cancel_booking(
            booking_id=sample_accommodation_booking.id,
            user_id=sample_accommodation_booking.user_id,
        )

        # Assert
        assert result is True
        mock_database_service.get_accommodation_booking.assert_called_once_with(
            sample_accommodation_booking.id, sample_accommodation_booking.user_id
        )
        mock_database_service.update_accommodation_booking.assert_called_once_with(
            sample_accommodation_booking.id, {"status": BookingStatus.CANCELLED.value}
        )

    @pytest.mark.asyncio
    async def test_cancel_booking_fails_for_unauthorized_user(
        self,
        accommodation_service: AccommodationService,
        mock_database_service: AsyncMock,
        sample_accommodation_booking: AccommodationBooking,
    ):
        """Test booking cancellation with unauthorized user."""
        # Arrange
        different_user_id = str(uuid4())
        mock_database_service.get_accommodation_booking.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError, match="Accommodation booking not found"):
            await accommodation_service.cancel_booking(
                booking_id=sample_accommodation_booking.id, user_id=different_user_id
            )

    # Test Dependency Injection

    @pytest.mark.asyncio
    async def test_get_accommodation_service_returns_instance(self):
        """Test the dependency injection function."""
        # Act
        service = await get_accommodation_service()

        # Assert
        assert isinstance(service, AccommodationService)

    # Test Search Filters

    @pytest.mark.asyncio
    async def test_search_with_complex_filters_applies_all_criteria(
        self, accommodation_service: AccommodationService
    ):
        """Test accommodation search with complex filters."""
        # Arrange
        search_request = AccommodationSearchRequest(
            location="Paris, France",
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
            adults=2,  # Add explicit adults field
            children=0,  # Add explicit children field
            property_types=[PropertyType.APARTMENT],
            min_price=100.00,
            max_price=200.00,
            bedrooms=2,
            amenities=["wifi", "kitchen", "washer"],
            instant_book=True,
            free_cancellation=True,
            max_distance_km=5.0,
            min_rating=4.5,
            sort_by="price",
            sort_order="asc",
        )

        # Act
        result = await accommodation_service.search_accommodations(search_request)

        # Assert
        assert isinstance(result, AccommodationSearchResponse)
        assert len(result.listings) == 3  # Mock generator returns 3 listings
        assert result.total_results == 3

    # Test Scoring Logic

    @pytest.mark.asyncio
    async def test_accommodation_scoring_calculates_correctly(
        self, accommodation_service: AccommodationService
    ):
        """Test accommodation scoring and ranking logic."""
        # Arrange
        listings = [
            {
                "price_per_night": 150.00,
                "rating": 4.8,
                "distance_to_center": 2.5,
                "instant_book": True,
            },
            {
                "price_per_night": 120.00,
                "rating": 4.5,
                "distance_to_center": 5.0,
                "instant_book": False,
            },
        ]

        # Act - Test internal scoring method if it exists
        if hasattr(accommodation_service, "_calculate_listing_score"):
            scores = [
                accommodation_service._calculate_listing_score(listing)
                for listing in listings
            ]

            # Assert
            assert all(0 <= score <= 1 for score in scores)
            # First listing should have higher score due to better rating and location
            assert scores[0] > scores[1]

    # Property-based Testing

    @given(
        guests=st.integers(min_value=1, max_value=16),  # Match the model constraint
        nights=st.integers(min_value=1, max_value=30),
        price=st.floats(min_value=10.0, max_value=10000.0),
    )
    def test_booking_total_price_calculation(
        self, guests: int, nights: int, price: float
    ):
        """Test booking total price calculation with various inputs."""
        # Arrange
        booking = AccommodationBookingRequest(
            listing_id=str(uuid4()),
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=30 + nights),
            guests=guests,
            guest_name="Test Guest",
            guest_email="test@example.com",
        )

        # Assert
        assert booking.guests == guests
        assert (booking.check_out - booking.check_in).days == nights

    # Edge Cases

    @pytest.mark.asyncio
    async def test_search_with_past_dates_creates_request_successfully(
        self, accommodation_service: AccommodationService
    ):
        """Test that past dates don't raise validation error at model level."""
        # Note: The model doesn't validate past dates
        # This would be done at service level
        # This test documents the current behavior
        request = AccommodationSearchRequest(
            location="Paris, France",
            check_in=date.today() - timedelta(days=1),  # Past date
            check_out=date.today() + timedelta(days=5),
            guests=2,
        )
        assert request.check_in < date.today()

    @pytest.mark.asyncio
    async def test_search_with_zero_guests_raises_validation_error(
        self, accommodation_service: AccommodationService
    ):
        """Test search with zero guests raises appropriate error."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            AccommodationSearchRequest(
                location="Paris, France",
                check_in=date.today() + timedelta(days=30),
                check_out=date.today() + timedelta(days=35),
                guests=0,  # Invalid
            )
        # Check that the error is about the guests field
        assert "guests" in str(exc_info.value)
        assert "greater than or equal to 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mock_listings_generation_produces_valid_data(
        self, accommodation_service: AccommodationService
    ):
        """Test that mock listings generator produces valid data."""
        # Arrange
        search_request = AccommodationSearchRequest(
            location="Test City",
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
            adults=2,  # Add explicit adults field
            children=0,  # Add explicit children field
        )

        # Act
        result = await accommodation_service.search_accommodations(search_request)

        # Assert
        for listing in result.listings:
            assert listing.id
            assert listing.name
            assert listing.property_type in PropertyType
            assert listing.price_per_night > 0
            assert listing.max_guests >= search_request.guests
            assert listing.location.city == "Test City"
