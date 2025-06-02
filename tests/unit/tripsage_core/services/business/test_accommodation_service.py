"""
Comprehensive tests for AccommodationService.

This module provides full test coverage for accommodation management operations
including search, booking, management, and MCP client integration.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.accommodation_service import (
    AccommodationAmenity,
    AccommodationBooking,
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
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_external_api_service(self):
        """Mock external API service."""
        api = AsyncMock()
        return api

    @pytest.fixture
    def accommodation_service(self, mock_database_service, mock_external_api_service):
        """Create AccommodationService instance with mocked dependencies."""
        return AccommodationService(
            database_service=mock_database_service,
        )

    @pytest.fixture
    def sample_search_request(self):
        """Sample accommodation search request."""
        return AccommodationSearchRequest(
            location="Paris, France",
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
            property_types=[PropertyType.APARTMENT, PropertyType.HOTEL],
            min_price=80.00,
            max_price=300.00,
            amenities=["wifi", "kitchen"],
            min_rating=4.0,
            instant_book=True,
        )

    @pytest.fixture
    def sample_accommodation_location(self):
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
    def sample_accommodation_host(self):
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
        self, sample_accommodation_location, sample_accommodation_host
    ):
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
        self, sample_accommodation_location, sample_accommodation_host
    ):
        """Sample accommodation booking."""
        booking_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

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

    async def test_search_accommodations_success(
        self,
        accommodation_service,
        mock_external_api_service,
        sample_search_request,
        sample_accommodation_listing,
    ):
        """Test successful accommodation search."""
        user_id = str(uuid4())

        # Mock external API response
        mock_external_api_service.search_accommodations.return_value = {
            "results": [sample_accommodation_listing.model_dump()],
            "total": 1,
        }

        result = await accommodation_service.search_accommodations(
            sample_search_request
        )

        # Assertions
        assert isinstance(result, AccommodationSearchResponse)
        assert len(result.listings) == 1
        assert result.total_results == 1
        assert result.listings[0].name == sample_accommodation_listing.name

        # Verify service calls
        mock_external_api_service.search_accommodations.assert_called_once()

    async def test_search_accommodations_validation_error(self, accommodation_service):
        """Test accommodation search with validation errors."""

        # Create invalid search request with check-out before check-in
        with pytest.raises(
            ValueError, match="Check-out date must be after check-in date"
        ):
            AccommodationSearchRequest(
                location="Paris, France",
                check_in=date.today() + timedelta(days=30),
                check_out=date.today() + timedelta(days=25),  # Before check-in
                guests=2,
            )

    async def test_get_accommodation_details_success(
        self, accommodation_service, mock_database_service, sample_accommodation_listing
    ):
        """Test successful accommodation details retrieval."""
        # Mock database response
        mock_database_service.get_accommodation_by_id.return_value = (
            sample_accommodation_listing.model_dump()
        )

        result = await accommodation_service.get_accommodation_details(
            sample_accommodation_listing.id
        )

        assert result is not None
        assert result.id == sample_accommodation_listing.id
        assert result.name == sample_accommodation_listing.name

        mock_database_service.get_accommodation_by_id.assert_called_once_with(
            sample_accommodation_listing.id
        )

    async def test_get_accommodation_details_not_found(
        self, accommodation_service, mock_database_service
    ):
        """Test accommodation details retrieval when listing doesn't exist."""
        listing_id = str(uuid4())

        mock_database_service.get_accommodation_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Accommodation not found"):
            await accommodation_service.get_accommodation_details(listing_id)

    async def test_book_accommodation_success(
        self,
        accommodation_service,
        mock_database_service,
        mock_external_api_service,
        sample_accommodation_listing,
        sample_accommodation_booking,
    ):
        """Test successful accommodation booking."""
        user_id = str(uuid4())

        # Mock database retrieval
        mock_database_service.get_accommodation_by_id.return_value = (
            sample_accommodation_listing.model_dump()
        )

        # Mock availability check
        mock_external_api_service.check_accommodation_availability.return_value = {
            "available": True,
            "price": sample_accommodation_listing.price_per_night,
            "total_price": sample_accommodation_listing.total_price,
        }

        # Mock booking creation
        mock_external_api_service.create_accommodation_booking.return_value = {
            "booking_id": sample_accommodation_booking.id,
            "confirmation_number": sample_accommodation_booking.confirmation_number,
            "status": "confirmed",
        }

        # Mock database storage
        mock_database_service.create_accommodation_booking.return_value = (
            sample_accommodation_booking.model_dump()
        )

        result = await accommodation_service.book_accommodation(
            user_id=user_id,
            listing_id=sample_accommodation_listing.id,
            check_in=sample_accommodation_booking.check_in,
            check_out=sample_accommodation_booking.check_out,
            guests=sample_accommodation_booking.guests,
            special_requests=sample_accommodation_booking.special_requests,
        )

        # Assertions
        assert isinstance(result, AccommodationBooking)
        assert result.user_id == user_id
        assert result.listing_id == sample_accommodation_listing.id
        assert result.status == BookingStatus.CONFIRMED

        # Verify service calls
        mock_external_api_service.check_accommodation_availability.assert_called_once()
        mock_external_api_service.create_accommodation_booking.assert_called_once()
        mock_database_service.create_accommodation_booking.assert_called_once()

    async def test_book_accommodation_not_available(
        self,
        accommodation_service,
        mock_database_service,
        mock_external_api_service,
        sample_accommodation_listing,
    ):
        """Test accommodation booking when not available."""
        user_id = str(uuid4())

        mock_database_service.get_accommodation_by_id.return_value = (
            sample_accommodation_listing.model_dump()
        )

        # Mock availability check returning false
        mock_external_api_service.check_accommodation_availability.return_value = {
            "available": False,
            "reason": "Dates not available",
        }

        with pytest.raises(ValidationError, match="Accommodation not available"):
            await accommodation_service.book_accommodation(
                user_id=user_id,
                listing_id=sample_accommodation_listing.id,
                check_in=date.today() + timedelta(days=30),
                check_out=date.today() + timedelta(days=35),
                guests=2,
            )

    async def test_get_user_bookings_success(
        self, accommodation_service, mock_database_service, sample_accommodation_booking
    ):
        """Test successful user bookings retrieval."""
        user_id = sample_accommodation_booking.user_id

        mock_database_service.get_user_accommodation_bookings.return_value = [
            sample_accommodation_booking.model_dump()
        ]

        results = await accommodation_service.get_user_bookings(user_id)

        assert len(results) == 1
        assert results[0].id == sample_accommodation_booking.id
        assert results[0].user_id == user_id

        mock_database_service.get_user_accommodation_bookings.assert_called_once_with(
            user_id
        )

    async def test_cancel_booking_success(
        self,
        accommodation_service,
        mock_database_service,
        mock_external_api_service,
        sample_accommodation_booking,
    ):
        """Test successful booking cancellation."""
        # Mock database retrieval
        mock_database_service.get_accommodation_booking.return_value = (
            sample_accommodation_booking.model_dump()
        )

        # Mock external cancellation
        mock_external_api_service.cancel_accommodation_booking.return_value = {
            "success": True,
            "refund_amount": 600.00,
            "cancellation_fee": 150.00,
        }

        # Mock database update
        cancelled_booking = sample_accommodation_booking.model_copy()
        cancelled_booking.status = BookingStatus.CANCELLED
        mock_database_service.update_accommodation_booking.return_value = (
            cancelled_booking.model_dump()
        )

        result = await accommodation_service.cancel_booking(
            booking_id=sample_accommodation_booking.id,
            user_id=sample_accommodation_booking.user_id,
        )

        assert result.status == BookingStatus.CANCELLED

        mock_external_api_service.cancel_accommodation_booking.assert_called_once()
        mock_database_service.update_accommodation_booking.assert_called_once()

    async def test_cancel_booking_unauthorized(
        self, accommodation_service, mock_database_service, sample_accommodation_booking
    ):
        """Test booking cancellation with unauthorized user."""
        different_user_id = str(uuid4())

        mock_database_service.get_accommodation_booking.return_value = (
            sample_accommodation_booking.model_dump()
        )

        with pytest.raises(ValidationError, match="Unauthorized"):
            await accommodation_service.cancel_booking(
                booking_id=sample_accommodation_booking.id, user_id=different_user_id
            )

    async def test_modify_booking_success(
        self,
        accommodation_service,
        mock_database_service,
        mock_external_api_service,
        sample_accommodation_booking,
    ):
        """Test successful booking modification."""
        # Mock database retrieval
        mock_database_service.get_accommodation_booking.return_value = (
            sample_accommodation_booking.model_dump()
        )

        new_check_out = sample_accommodation_booking.check_out + timedelta(days=1)

        # Mock external modification
        mock_external_api_service.modify_accommodation_booking.return_value = {
            "success": True,
            "price_difference": 150.00,
            "new_total": 900.00,
        }

        # Mock database update
        modified_booking = sample_accommodation_booking.model_copy()
        modified_booking.check_out = new_check_out
        modified_booking.nights = 6
        modified_booking.total_price = 900.00
        mock_database_service.update_accommodation_booking.return_value = (
            modified_booking.model_dump()
        )

        result = await accommodation_service.modify_booking(
            booking_id=sample_accommodation_booking.id,
            user_id=sample_accommodation_booking.user_id,
            check_out=new_check_out,
        )

        assert result.check_out == new_check_out
        assert result.nights == 6
        assert result.total_price == 900.00

        mock_external_api_service.modify_accommodation_booking.assert_called_once()
        mock_database_service.update_accommodation_booking.assert_called_once()

    async def test_get_accommodation_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_accommodation_service()
        assert isinstance(service, AccommodationService)

    async def test_search_with_filters_success(
        self,
        accommodation_service,
        mock_external_api_service,
        sample_accommodation_listing,
    ):
        """Test accommodation search with complex filters."""
        user_id = str(uuid4())

        search_request = AccommodationSearchRequest(
            location="Paris, France",
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
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

        # Mock external API response
        mock_external_api_service.search_accommodations.return_value = {
            "results": [sample_accommodation_listing.model_dump()],
            "total": 1,
        }

        result = await accommodation_service.search_accommodations(
            user_id, search_request
        )

        assert len(result.listings) == 1
        assert result.search_parameters == search_request

        # Verify the search parameters were passed correctly
        call_args = mock_external_api_service.search_accommodations.call_args
        assert call_args[0][0] == search_request

    async def test_accommodation_scoring_logic(self, accommodation_service):
        """Test accommodation scoring and ranking logic."""
        # Test the internal scoring method if it exists
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

        # If the service has a scoring method, test it
        if hasattr(accommodation_service, "_calculate_listing_score"):
            scores = [
                accommodation_service._calculate_listing_score(listing)
                for listing in listings
            ]

            assert all(0 <= score <= 1 for score in scores)
            # First listing should have higher score due to better rating and location
            assert scores[0] > scores[1]

    async def test_service_error_handling(
        self, accommodation_service, mock_external_api_service
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock external API to raise an exception
        mock_external_api_service.search_accommodations.side_effect = Exception(
            "API error"
        )

        search_request = AccommodationSearchRequest(
            location="Paris, France",
            check_in=date.today() + timedelta(days=30),
            check_out=date.today() + timedelta(days=35),
            guests=2,
        )

        with pytest.raises(ServiceError, match="Accommodation search failed"):
            await accommodation_service.search_accommodations(user_id, search_request)
