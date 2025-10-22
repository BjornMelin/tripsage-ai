# pylint: disable=too-many-lines
"""Accommodation service for accommodation management operations.

This service consolidates accommodation-related business logic including accommodation
search, booking, management, and integration with external accommodation APIs. It
provides clean abstractions over external services with proper data relationships.
"""

import logging
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
    CoreServiceError as ServiceError,
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel


logger = logging.getLogger(__name__)


RECOVERABLE_ERRORS = (
    ServiceError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
    ValueError,
)


class PropertyType(str, Enum):
    """Property type enumeration."""

    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOUSE = "house"
    VILLA = "villa"
    RESORT = "resort"
    HOSTEL = "hostel"
    BED_AND_BREAKFAST = "bed_and_breakfast"
    GUEST_HOUSE = "guest_house"
    OTHER = "other"


class BookingStatus(str, Enum):
    """Accommodation booking status enumeration."""

    SEARCHED = "searched"
    VIEWED = "viewed"
    SAVED = "saved"
    INQUIRED = "inquired"
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CancellationPolicy(str, Enum):
    """Cancellation policy enumeration."""

    FLEXIBLE = "flexible"
    MODERATE = "moderate"
    STRICT = "strict"
    SUPER_STRICT = "super_strict"
    FREE_CANCELLATION = "free_cancellation"
    NO_REFUND = "no_refund"


class AccommodationAmenity(TripSageModel):
    """Accommodation amenity information."""

    name: str = Field(..., description="Amenity name")
    category: str | None = Field(None, description="Amenity category")
    icon: str | None = Field(None, description="Amenity icon identifier")
    description: str | None = Field(None, description="Amenity description")


class AccommodationImage(TripSageModel):
    """Accommodation image information."""

    url: str = Field(..., description="Image URL")
    caption: str | None = Field(None, description="Image caption")
    is_primary: bool = Field(
        default=False, description="Whether this is the primary image"
    )
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")


class AccommodationLocation(TripSageModel):
    """Accommodation location information."""

    address: str | None = Field(None, description="Full address")
    city: str = Field(..., description="City")
    state: str | None = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    postal_code: str | None = Field(None, description="Postal/zip code")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    neighborhood: str | None = Field(None, description="Neighborhood name")
    distance_to_center: float | None = Field(
        None, description="Distance to city center in km"
    )


class AccommodationHost(TripSageModel):
    """Accommodation host information."""

    id: str = Field(..., description="Host ID")
    name: str = Field(..., description="Host name")
    avatar_url: str | None = Field(None, description="Host avatar URL")
    rating: float | None = Field(None, ge=0, le=5, description="Host rating")
    review_count: int | None = Field(None, ge=0, description="Host review count")
    response_rate: float | None = Field(None, ge=0, le=1, description="Response rate")
    response_time: str | None = Field(None, description="Response time")
    is_superhost: bool = Field(default=False, description="Whether host is a superhost")
    verification_badges: list[str] = Field(
        default_factory=list, description="Host verification badges"
    )


class AccommodationSearchRequest(TripSageModel):
    """Request model for accommodation search."""

    user_id: str = Field(..., description="User performing the accommodation search")
    trip_id: str | None = Field(None, description="Associated trip identifier")
    location: str = Field(..., description="Search location (city, address, etc.)")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    guests: int = Field(default=1, ge=1, le=16, description="Number of guests")
    adults: int | None = Field(None, ge=1, le=16, description="Number of adults")
    children: int | None = Field(None, ge=0, le=16, description="Number of children")
    infants: int | None = Field(None, ge=0, le=16, description="Number of infants")

    property_types: list[PropertyType] | None = Field(
        None, description="Preferred property types"
    )
    min_price: float | None = Field(None, ge=0, description="Minimum price per night")
    max_price: float | None = Field(None, ge=0, description="Maximum price per night")
    currency: str = Field(default="USD", description="Currency code")

    bedrooms: int | None = Field(
        None, ge=0, le=10, description="Minimum number of bedrooms"
    )
    beds: int | None = Field(None, ge=0, le=20, description="Minimum number of beds")
    bathrooms: float | None = Field(
        None, ge=0, le=10, description="Minimum number of bathrooms"
    )

    amenities: list[str] | None = Field(None, description="Required amenities")
    accessibility_features: list[str] | None = Field(
        None, description="Required accessibility features"
    )

    instant_book: bool | None = Field(
        None, description="Filter for instant bookable properties"
    )
    free_cancellation: bool | None = Field(
        None, description="Filter for free cancellation"
    )

    max_distance_km: float | None = Field(
        None, ge=0, description="Maximum distance from center"
    )
    min_rating: float | None = Field(
        None, ge=0, le=5, description="Minimum property rating"
    )

    metadata: dict[str, Any] | None = Field(
        None, description="Additional client-provided context for the search"
    )
    sort_by: str | None = Field("relevance", description="Sort criteria")
    sort_order: str | None = Field("asc", description="Sort order (asc/desc)")

    @field_validator("check_out")
    @classmethod
    def validate_check_out(cls, v: date, info) -> date:
        """Validate check-out date is after check-in date."""
        if info.data.get("check_in") and v <= info.data["check_in"]:
            raise ValueError("Check-out date must be after check-in date")
        return v


class AccommodationListing(TripSageModel):
    """Accommodation listing response model."""

    id: str = Field(..., description="Listing ID")
    user_id: str | None = Field(None, description="User that stored the listing")
    name: str = Field(..., description="Property name")
    description: str | None = Field(None, description="Property description")
    property_type: PropertyType = Field(..., description="Property type")

    location: AccommodationLocation = Field(..., description="Property location")

    price_per_night: float = Field(..., description="Price per night")
    total_price: float | None = Field(None, description="Total price for stay")
    currency: str = Field(..., description="Currency code")

    rating: float | None = Field(None, ge=0, le=5, description="Property rating")
    review_count: int | None = Field(None, ge=0, description="Number of reviews")

    max_guests: int = Field(..., description="Maximum number of guests")
    bedrooms: int | None = Field(None, description="Number of bedrooms")
    beds: int | None = Field(None, description="Number of beds")
    bathrooms: float | None = Field(None, description="Number of bathrooms")

    amenities: list[AccommodationAmenity] = Field(
        default_factory=list, description="Property amenities"
    )
    images: list[AccommodationImage] = Field(
        default_factory=list, description="Property images"
    )

    host: AccommodationHost | None = Field(None, description="Host information")

    check_in_time: str | None = Field(None, description="Check-in time")
    check_out_time: str | None = Field(None, description="Check-out time")

    cancellation_policy: CancellationPolicy | None = Field(
        None, description="Cancellation policy"
    )
    instant_book: bool = Field(default=False, description="Whether instantly bookable")

    source: str | None = Field(
        None, description="Data source (airbnb, booking.com, etc.)"
    )
    source_listing_id: str | None = Field(
        None, description="Original listing ID from source"
    )
    listing_url: str | None = Field(None, description="URL to original listing")
    stored_at: datetime | None = Field(
        None, description="Timestamp when the listing snapshot was stored"
    )

    # Search context
    nights: int | None = Field(None, description="Number of nights for the search")
    is_available: bool = Field(
        default=True, description="Whether available for search dates"
    )

    # Scoring and ranking
    score: float | None = Field(None, ge=0, le=1, description="Relevance score")
    price_score: float | None = Field(
        None, ge=0, le=1, description="Price competitiveness"
    )
    location_score: float | None = Field(
        None, ge=0, le=1, description="Location convenience"
    )


class AccommodationBooking(TripSageModel):
    """Accommodation booking response model."""

    id: str = Field(..., description="Booking ID")
    user_id: str = Field(..., description="User ID")
    trip_id: str | None = Field(None, description="Associated trip ID")
    guest_name: str = Field(..., description="Primary guest full name")
    guest_email: str = Field(..., description="Primary guest email address")
    guest_phone: str | None = Field(
        None, description="Primary guest contact phone number"
    )

    listing_id: str = Field(..., description="Booked listing ID")
    confirmation_number: str | None = Field(
        None, description="Booking confirmation number"
    )

    property_name: str = Field(..., description="Property name")
    property_type: PropertyType = Field(..., description="Property type")
    location: AccommodationLocation = Field(..., description="Property location")

    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    nights: int = Field(..., description="Number of nights")
    guests: int = Field(..., description="Number of guests")

    price_per_night: float = Field(..., description="Price per night")
    total_price: float = Field(..., description="Total booking price")
    currency: str = Field(..., description="Currency")

    status: BookingStatus = Field(..., description="Booking status")
    booked_at: datetime = Field(..., description="Booking timestamp")

    cancellation_policy: CancellationPolicy | None = Field(
        None, description="Cancellation policy"
    )
    is_cancellable: bool = Field(
        default=False, description="Whether booking can be cancelled"
    )
    is_refundable: bool = Field(
        default=False, description="Whether booking is refundable"
    )
    hold_only: bool = Field(
        default=False, description="Whether the booking is held without payment"
    )
    payment_method: str | None = Field(
        None, description="Payment method reference used for the booking"
    )

    host: AccommodationHost | None = Field(None, description="Host information")
    special_requests: str | None = Field(
        None, description="Special requests from guest"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional booking metadata"
    )
    created_at: datetime | None = Field(
        None, description="Timestamp when the booking record was created"
    )


class AccommodationSearchResponse(TripSageModel):
    """Accommodation search response model."""

    search_id: str = Field(..., description="Search ID")
    user_id: str = Field(..., description="User that initiated the search")
    trip_id: str | None = Field(None, description="Associated trip identifier")
    listings: list[AccommodationListing] = Field(..., description="Search results")
    search_parameters: AccommodationSearchRequest = Field(
        ..., description="Original search parameters"
    )

    total_results: int = Field(..., description="Total number of results")
    results_returned: int = Field(..., description="Number of results returned")

    min_price: float | None = Field(None, description="Minimum price found")
    max_price: float | None = Field(None, description="Maximum price found")
    avg_price: float | None = Field(None, description="Average price")

    search_duration_ms: int | None = Field(
        None, description="Search duration in milliseconds"
    )
    cached: bool = Field(default=False, description="Whether results were cached")


class AccommodationBookingRequest(TripSageModel):
    """Request model for accommodation booking."""

    listing_id: str = Field(..., description="Listing ID to book")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    guests: int = Field(..., ge=1, le=16, description="Number of guests")

    guest_name: str = Field(..., description="Primary guest name")
    guest_email: str = Field(..., description="Guest email address")
    guest_phone: str | None = Field(None, description="Guest phone number")

    special_requests: str | None = Field(None, description="Special requests")
    trip_id: str | None = Field(None, description="Associated trip ID")

    payment_method: str | None = Field(None, description="Payment method")
    hold_only: bool = Field(default=False, description="Hold booking without payment")

    metadata: dict[str, Any] | None = Field(
        None, description="Additional booking metadata"
    )


class AccommodationService:
    """Accommodation service for search, booking, and management.

    This service handles:
    - Accommodation search with multiple providers
    - Accommodation booking and management
    - Price monitoring and comparisons
    - Integration with external accommodation APIs
    - Caching and optimization
    - Trip integration
    """

    def __init__(
        self,
        database_service=None,
        external_accommodation_service=None,
        cache_ttl: int = 300,
    ):
        """Initialize the accommodation service.

        Args:
            database_service: Database service for persistence
            external_accommodation_service: External accommodation API service
            cache_ttl: Cache TTL in seconds
        """
        # Import here to avoid circular imports
        if database_service is None:
            import asyncio

            from tripsage_core.services.infrastructure import get_database_service

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            database_service = loop.run_until_complete(get_database_service())

        if external_accommodation_service is None:
            # Try to import MCP accommodation client
            try:
                from tripsage_core.clients.accommodations import AccommodationMCPClient

                # Default local MCP base URL; can be made configurable via Settings.
                external_accommodation_service = AccommodationMCPClient(
                    base_url="http://localhost:3000"
                )
            except ImportError:
                logger.warning("External accommodation service not available")
                external_accommodation_service = None

        self.db: Any = database_service  # dynamic backend, attribute surface varies
        self.external_service: Any = external_accommodation_service
        self.cache_ttl = cache_ttl

        # In-memory cache for search results
        self._search_cache: dict[str, tuple] = {}

    async def search_accommodations(
        self, search_request: AccommodationSearchRequest
    ) -> AccommodationSearchResponse:
        """Search for accommodation listings.

        Args:
            search_request: Accommodation search parameters

        Returns:
            Accommodation search results

        Raises:
            ValidationError: If search parameters are invalid
            ServiceError: If search fails
        """
        try:
            if not search_request.user_id:
                raise ValidationError("User ID is required for accommodation search")

            search_id = str(uuid4())
            start_time = datetime.now(UTC)

            # Check cache first
            cache_key = self._generate_search_cache_key(search_request)
            cached_result = self._get_cached_search(cache_key)

            if cached_result:
                logger.info(
                    "Returning cached accommodation search results",
                    extra={"search_id": search_id, "cache_key": cache_key},
                )

                return AccommodationSearchResponse(
                    search_id=search_id,
                    user_id=search_request.user_id,
                    trip_id=search_request.trip_id,
                    listings=cached_result["listings"],
                    search_parameters=search_request,
                    total_results=len(cached_result["listings"]),
                    results_returned=len(cached_result["listings"]),
                    min_price=cached_result.get("min_price"),
                    max_price=cached_result.get("max_price"),
                    avg_price=cached_result.get("avg_price"),
                    search_duration_ms=None,
                    cached=True,
                )

            # Perform external search
            listings = []
            if self.external_service:
                try:
                    external_listings = await self._search_external_api(search_request)
                    listings.extend(external_listings)
                except RECOVERABLE_ERRORS as error:
                    logger.exception(
                        "External accommodation search failed",
                        extra={"error": str(error), "search_id": search_id},
                    )

            # Add fallback/mock listings if no external service
            if not listings and not self.external_service:
                try:
                    listings = await self._generate_mock_listings(search_request)
                except Exception as error:  # pragma: no cover - safety net
                    logger.exception(
                        "Fallback accommodation listing generation failed",
                        extra={
                            "error": str(error),
                            "location": search_request.location,
                        },
                    )
                    raise ServiceError(
                        f"Accommodation search failed: {error!s}"
                    ) from error

            # Score and rank listings
            scored_listings = await self._score_listings(listings, search_request)

            # Calculate price statistics
            prices = [listing.price_per_night for listing in scored_listings]
            min_price = min(prices) if prices else None
            max_price = max(prices) if prices else None
            avg_price = sum(prices) / len(prices) if prices else None

            # Cache results
            self._cache_search_results(
                cache_key,
                {
                    "listings": scored_listings,
                    "min_price": min_price,
                    "max_price": max_price,
                    "avg_price": avg_price,
                },
            )

            # Store search in database
            await self._store_search_history(search_id, search_request, scored_listings)

            search_duration = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            logger.info(
                "Accommodation search completed",
                extra={
                    "search_id": search_id,
                    "listings_count": len(scored_listings),
                    "duration_ms": search_duration,
                },
            )

            return AccommodationSearchResponse(
                search_id=search_id,
                user_id=search_request.user_id,
                trip_id=search_request.trip_id,
                listings=scored_listings,
                search_parameters=search_request,
                total_results=len(scored_listings),
                results_returned=len(scored_listings),
                min_price=min_price,
                max_price=max_price,
                avg_price=avg_price,
                search_duration_ms=search_duration,
                cached=False,
            )

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Accommodation search failed",
                extra={
                    "error": str(error),
                    "location": search_request.location,
                    "check_in": search_request.check_in,
                    "check_out": search_request.check_out,
                },
            )
            raise ServiceError(f"Accommodation search failed: {error!s}") from error

    async def get_listing_details(
        self, listing_id: str, user_id: str
    ) -> AccommodationListing | None:
        """Get detailed information about an accommodation listing.

        Args:
            listing_id: Listing ID
            user_id: User ID for access control

        Returns:
            Accommodation listing details or None if not found
        """
        try:
            # Try to get from database first
            listing_data = await self.db.get_accommodation_listing(listing_id, user_id)
            if listing_data:
                return AccommodationListing(**listing_data)

            # Try external service if available
            if self.external_service:
                try:
                    external_listing = await self.external_service.get_listing_details(
                        listing_id
                    )
                    if external_listing:
                        # Convert to our model
                        converted_listing = await self._convert_external_listing(
                            external_listing
                        )

                        # Store for future reference
                        await self._store_listing(converted_listing, user_id)

                        return converted_listing
                except RECOVERABLE_ERRORS as error:
                    logger.warning(
                        "Failed to get external listing details",
                        extra={"listing_id": listing_id, "error": str(error)},
                    )

            return None

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get listing details",
                extra={
                    "listing_id": listing_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            return None

    async def book_accommodation(
        self, user_id: str, booking_request: AccommodationBookingRequest
    ) -> AccommodationBooking:
        """Book an accommodation listing.

        Args:
            user_id: User ID
            booking_request: Booking request with guest details

        Returns:
            Accommodation booking information

        Raises:
            NotFoundError: If listing not found
            ValidationError: If booking data is invalid
            ServiceError: If booking fails
        """
        try:
            # Get listing details
            listing = await self.get_listing_details(
                booking_request.listing_id, user_id
            )
            if not listing:
                raise NotFoundError("Accommodation listing not found")

            # Check availability
            if not listing.is_available:
                raise ValidationError(
                    "Accommodation is not available for selected dates"
                )

            booking_id = str(uuid4())
            now = datetime.now(UTC)
            nights = (booking_request.check_out - booking_request.check_in).days

            # Calculate total price
            total_price = listing.price_per_night * nights

            # Create booking record
            booking = AccommodationBooking(
                id=booking_id,
                user_id=user_id,
                trip_id=booking_request.trip_id,
                guest_name=booking_request.guest_name,
                guest_email=booking_request.guest_email,
                guest_phone=booking_request.guest_phone,
                listing_id=booking_request.listing_id,
                property_name=listing.name,
                property_type=listing.property_type,
                location=listing.location,
                check_in=booking_request.check_in,
                check_out=booking_request.check_out,
                nights=nights,
                guests=booking_request.guests,
                price_per_night=listing.price_per_night,
                total_price=total_price,
                currency=listing.currency,
                confirmation_number=None,
                status=BookingStatus.INQUIRED
                if booking_request.hold_only
                else BookingStatus.BOOKED,
                booked_at=now,
                cancellation_policy=listing.cancellation_policy,
                host=listing.host,
                special_requests=booking_request.special_requests,
                hold_only=booking_request.hold_only,
                payment_method=booking_request.payment_method,
                metadata=booking_request.metadata or {},
                created_at=now,
            )

            # Attempt external booking if not hold-only
            if not booking_request.hold_only and self.external_service:
                try:
                    external_booking = await self._book_external_accommodation(
                        listing, booking_request, user_id
                    )
                    if external_booking:
                        booking.confirmation_number = external_booking.get(
                            "confirmation_number"
                        )
                        booking.status = BookingStatus.CONFIRMED
                        booking.is_cancellable = external_booking.get(
                            "is_cancellable", False
                        )
                        booking.is_refundable = external_booking.get(
                            "is_refundable", False
                        )
                except RECOVERABLE_ERRORS as error:
                    logger.exception(
                        "External booking failed",
                        extra={
                            "booking_id": booking_id,
                            "listing_id": booking_request.listing_id,
                            "error": str(error),
                        },
                    )
                    # Continue with inquiry status if external booking fails
                    booking.status = BookingStatus.INQUIRED

            # Store booking in database
            await self._store_booking(booking)

            logger.info(
                "Accommodation booked successfully",
                extra={
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "listing_id": booking_request.listing_id,
                    "status": booking.status.value,
                },
            )

            return booking

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Accommodation booking failed",
                extra={
                    "user_id": user_id,
                    "listing_id": booking_request.listing_id,
                    "error": str(error),
                },
            )
            raise ServiceError(f"Accommodation booking failed: {error!s}") from error

    async def get_user_bookings(
        self,
        user_id: str,
        trip_id: str | None = None,
        status: BookingStatus | None = None,
        limit: int = 50,
    ) -> list[AccommodationBooking]:
        """Get accommodation bookings for a user.

        Args:
            user_id: User ID
            trip_id: Optional trip ID filter
            status: Optional status filter
            limit: Maximum number of bookings

        Returns:
            List of accommodation bookings
        """
        try:
            filters = {"user_id": user_id}
            if trip_id:
                filters["trip_id"] = trip_id
            if status:
                filters["status"] = status.value

            results = await self.db.get_accommodation_bookings(filters, limit)

            return [AccommodationBooking(**result) for result in results]

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get user bookings",
                extra={"user_id": user_id, "error": str(error)},
            )
            return []

    async def cancel_booking(self, booking_id: str, user_id: str) -> bool:
        """Cancel an accommodation booking.

        Args:
            booking_id: Booking ID
            user_id: User ID for authorization

        Returns:
            True if cancellation successful

        Raises:
            NotFoundError: If booking not found
            PermissionError: If user doesn't own booking
            ValidationError: If booking cannot be cancelled
        """
        try:
            # Get booking
            booking_data = await self.db.get_accommodation_booking(booking_id, user_id)
            if not booking_data:
                raise NotFoundError("Accommodation booking not found")

            booking = AccommodationBooking(**booking_data)

            # Check if cancellable
            if booking.status in {BookingStatus.CANCELLED, BookingStatus.COMPLETED}:
                raise ValidationError("Booking is already cancelled or completed")

            if not booking.is_cancellable:
                raise ValidationError("Booking cannot be cancelled")

            # Attempt external cancellation if booked externally
            if (
                booking.status in {BookingStatus.BOOKED, BookingStatus.CONFIRMED}
                and self.external_service
            ):
                try:
                    await self._cancel_external_booking(booking)
                except RECOVERABLE_ERRORS as error:
                    logger.warning(
                        "External cancellation failed",
                        extra={"booking_id": booking_id, "error": str(error)},
                    )

            # Update booking status
            success = await self.db.update_accommodation_booking(
                booking_id, {"status": BookingStatus.CANCELLED.value}
            )

            if success:
                logger.info(
                    "Accommodation booking cancelled",
                    extra={"booking_id": booking_id, "user_id": user_id},
                )

            return success

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to cancel booking",
                extra={
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            return False

    async def _search_external_api(
        self, search_request: AccommodationSearchRequest
    ) -> list[AccommodationListing]:
        """Search accommodations using external API."""
        if not self.external_service:
            return []

        try:
            # Convert to external API format
            external_request = {
                "location": search_request.location,
                "check_in": search_request.check_in,
                "check_out": search_request.check_out,
                "guests": (search_request.adults or 0) + (search_request.children or 0),
                "property_types": search_request.property_types,
                "min_price": search_request.min_price,
                "max_price": search_request.max_price,
                "amenities": search_request.amenities,
                "instant_book": getattr(search_request, "instant_book", None),
            }

            # Call external API
            external_listings = await self.external_service.search_accommodations(
                **external_request
            )

            # Convert to our model
            return [
                await self._convert_external_listing(external_listing)
                for external_listing in external_listings
            ]

        except RECOVERABLE_ERRORS as error:
            logger.exception("External API search failed", extra={"error": str(error)})
            return []

    async def _convert_external_listing(self, external_listing) -> AccommodationListing:
        """Convert external API listing to our model."""
        # This is a simplified conversion - in practice you'd map all fields
        return AccommodationListing.model_validate(
            {
                "id": external_listing.get("id", str(uuid4())),
                "name": external_listing.get("name", "Unknown Property"),
                "property_type": external_listing.get("property_type", "other"),
                "location": {
                    "city": external_listing.get("location", {}).get("city", "Unknown"),
                    "country": external_listing.get("location", {}).get(
                        "country", "Unknown"
                    ),
                },
                "price_per_night": float(external_listing.get("price_per_night", 0)),
                "currency": external_listing.get("currency", "USD"),
                "max_guests": external_listing.get("max_guests", 1),
                "rating": external_listing.get("rating"),
                "source": "external_api",
                "source_listing_id": external_listing.get("id"),
            }
        )

    async def _generate_mock_listings(
        self, search_request: AccommodationSearchRequest
    ) -> list[AccommodationListing]:
        """Generate mock accommodation listings for testing."""
        nights = (search_request.check_out - search_request.check_in).days

        # Generate a few mock listings with different property types and prices
        property_types = [
            PropertyType.HOTEL,
            PropertyType.APARTMENT,
            PropertyType.HOUSE,
        ]
        base_price = 80.0

        return [
            AccommodationListing.model_validate(
                {
                    "id": str(uuid4()),
                    "name": f"Sample {property_types[i].value.title()} {i + 1}",
                    "description": (
                        "A beautiful "
                        f"{property_types[i].value} in {search_request.location}"
                    ),
                    "property_type": property_types[i].value,
                    "location": {
                        "city": search_request.location.split(",")[0].strip(),
                        "country": "United States",
                        "neighborhood": "Downtown",
                        "distance_to_center": 1.0 + i * 0.5,
                    },
                    "price_per_night": base_price + (i * 30),
                    "total_price": (base_price + (i * 30)) * nights,
                    "currency": getattr(search_request, "currency", "USD"),
                    "rating": 4.0 + (i * 0.3),
                    "review_count": 50 + (i * 25),
                    "max_guests": (search_request.adults or 0)
                    + (search_request.children or 0)
                    + i,
                    "bedrooms": 1 + i,
                    "beds": 1 + i,
                    "bathrooms": 1.0 + (i * 0.5),
                    "amenities": [
                        {"name": "WiFi"},
                        {
                            "name": "Kitchen" if i > 0 else "Restaurant",
                        },
                        {
                            "name": "Pool" if i == 2 else "Air Conditioning",
                        },
                    ],
                    "images": [
                        {
                            "url": f"https://example.com/image{i + 1}.jpg",
                            "is_primary": True,
                        }
                    ],
                    "nights": nights,
                    "source": "mock",
                    "instant_book": i % 2 == 0,
                }
            )
            for i in range(3)
        ]

    async def _score_listings(
        self,
        listings: list[AccommodationListing],
        search_request: AccommodationSearchRequest,
    ) -> list[AccommodationListing]:
        """Score and rank accommodation listings."""
        if not listings:
            return listings

        # Simple scoring based on price, rating, and search criteria match
        prices = [listing.price_per_night for listing in listings]
        min_price = min(prices)
        max_price = max(prices)

        for listing in listings:
            # Price score (lower price = higher score)
            if max_price > min_price:
                price_score = 1 - (listing.price_per_night - min_price) / (
                    max_price - min_price
                )
            else:
                price_score = 1.0

            # Location score (closer to center = higher score)
            location_score = 1.0
            if listing.location.distance_to_center:
                location_score = max(0, 1 - (listing.location.distance_to_center / 10))

            # Rating score
            rating_score = (listing.rating or 3.0) / 5.0

            # Property type preference score
            type_score = 1.0
            if (
                search_request.property_types
                and listing.property_type in search_request.property_types
            ):
                type_score = 1.2  # Boost for preferred property types

            # Overall score (weighted average)
            overall_score = (
                (price_score * 0.4)
                + (location_score * 0.2)
                + (rating_score * 0.3)
                + (type_score * 0.1)
            )

            listing.price_score = price_score
            listing.location_score = location_score
            listing.score = min(1.0, overall_score)

        # Sort by score (highest first)
        return sorted(listings, key=lambda x: x.score or 0, reverse=True)

    def _generate_search_cache_key(
        self, search_request: AccommodationSearchRequest
    ) -> str:
        """Generate cache key for search request."""
        import hashlib

        key_data = (
            f"{search_request.user_id}:{search_request.trip_id or 'none'}:"
            f"{search_request.location}:{search_request.check_in}:"
            f"{search_request.check_out}:"
            f"{search_request.guests}:"
            f"{(search_request.adults or 0)}:{(search_request.children or 0)}:"
            f"{search_request.min_price}:{search_request.max_price}"
        )

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_search(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached search results if still valid."""
        if cache_key in self._search_cache:
            result, timestamp = self._search_cache[cache_key]
            import time

            if time.time() - timestamp < self.cache_ttl:
                return result
            del self._search_cache[cache_key]
        return None

    def _cache_search_results(self, cache_key: str, result: dict[str, Any]) -> None:
        """Cache search results."""
        import time

        self._search_cache[cache_key] = (result, time.time())

        # Simple cache cleanup
        if len(self._search_cache) > 1000:
            oldest_keys = sorted(
                self._search_cache.keys(), key=lambda k: self._search_cache[k][1]
            )[:200]
            for key in oldest_keys:
                del self._search_cache[key]

    async def _store_search_history(
        self,
        search_id: str,
        search_request: AccommodationSearchRequest,
        listings: list[AccommodationListing],
    ) -> None:
        """Store search history in database."""
        try:
            search_data = {
                "id": search_id,
                "user_id": search_request.user_id,
                "trip_id": search_request.trip_id,
                "location": search_request.location,
                "check_in": search_request.check_in.isoformat(),
                "check_out": search_request.check_out.isoformat(),
                "guests": search_request.guests,
                "adults": search_request.adults,
                "children": search_request.children,
                "infants": search_request.infants,
                "listings_count": len(listings),
                "search_timestamp": datetime.now(UTC).isoformat(),
                "metadata": search_request.metadata or {},
            }

            await self.db.store_accommodation_search(search_data)

        except RECOVERABLE_ERRORS as error:
            logger.warning(
                "Failed to store search history",
                extra={"search_id": search_id, "error": str(error)},
            )

    async def _store_listing(self, listing: AccommodationListing, user_id: str) -> None:
        """Store accommodation listing in database."""
        try:
            listing_data = listing.model_dump()
            listing_data["user_id"] = user_id
            listing_data["stored_at"] = (
                listing.stored_at.isoformat()
                if listing.stored_at
                else datetime.now(UTC).isoformat()
            )

            await self.db.store_accommodation_listing(listing_data)

        except RECOVERABLE_ERRORS as error:
            logger.warning(
                "Failed to store listing",
                extra={"listing_id": listing.id, "error": str(error)},
            )

    async def _store_booking(self, booking: AccommodationBooking) -> None:
        """Store accommodation booking in database."""
        try:
            booking_data = booking.model_dump()
            booking_data["created_at"] = (
                booking.created_at.isoformat()
                if booking.created_at
                else datetime.now(UTC).isoformat()
            )

            await self.db.store_accommodation_booking(booking_data)

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to store booking",
                extra={"booking_id": booking.id, "error": str(error)},
            )
            raise

    async def _book_external_accommodation(
        self,
        listing: AccommodationListing,
        booking_request: AccommodationBookingRequest,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Book accommodation using external API."""
        if not self.external_service:
            return None

        try:
            # Convert to external API format
            external_booking_request = {
                "listing_id": listing.source_listing_id or listing.id,
                "check_in": booking_request.check_in,
                "check_out": booking_request.check_out,
                "guests": booking_request.guests,
                "guest_name": booking_request.guest_name,
                "guest_email": booking_request.guest_email,
                "guest_phone": booking_request.guest_phone,
                "special_requests": booking_request.special_requests,
                "user_id": user_id,
                "trip_id": booking_request.trip_id,
                "payment_method": booking_request.payment_method,
                "hold_only": booking_request.hold_only,
                "metadata": booking_request.metadata or {},
            }

            # Create external booking
            external_booking = await self.external_service.book_accommodation(
                external_booking_request
            )

            return {
                "confirmation_number": external_booking.get("confirmation_number"),
                "is_cancellable": external_booking.get("is_cancellable", False),
                "is_refundable": external_booking.get("is_refundable", False),
            }

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "External booking failed",
                extra={"listing_id": listing.id, "error": str(error)},
            )
            return None

    async def _cancel_external_booking(self, booking: AccommodationBooking) -> None:
        """Cancel booking using external API."""
        if not self.external_service:
            return

        try:
            # This would call the external API to cancel
            # Implementation depends on the external service
            pass

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "External cancellation failed",
                extra={"booking_id": booking.id, "error": str(error)},
            )


# Dependency function for FastAPI
async def get_accommodation_service() -> AccommodationService:
    """Get accommodation service instance for dependency injection."""
    return AccommodationService()
