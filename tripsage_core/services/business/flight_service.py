"""
Flight service for comprehensive flight management operations.

This service consolidates flight-related business logic including flight search,
booking, management, and integration with external flight APIs. It provides
clean abstractions over external services while maintaining proper data relationships.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import Field, field_validator

from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import (
    BookingStatus,
    CabinClass,
    PassengerType,
)
from tripsage_core.models.schemas_common.flight_schemas import (
    FlightPassenger,
    FlightSearchRequest,
)

logger = logging.getLogger(__name__)


class FlightType(str, Enum):
    """Flight type enumeration."""

    ROUND_TRIP = "round_trip"
    ONE_WAY = "one_way"
    MULTI_CITY = "multi_city"


# Note: Using BookingStatus, CabinClass, PassengerType from schemas_common.enums
# Re-export for convenience
__all__ = [
    "FlightService",
    "FlightType",
    "FlightSegment",
    "FlightOffer",
    "FlightBooking",
    "FlightBookingRequest",
    "FlightSearchResponse",
    "BookingStatus",
    "CabinClass",
    "PassengerType",
    "FlightPassenger",
    "FlightSearchRequest",
    "get_flight_service",
]


class FlightSegment(TripSageModel):
    """Flight segment information."""

    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: datetime = Field(..., description="Departure date and time")
    arrival_date: datetime = Field(..., description="Arrival date and time")
    airline: Optional[str] = Field(None, description="Airline code")
    flight_number: Optional[str] = Field(None, description="Flight number")
    aircraft_type: Optional[str] = Field(None, description="Aircraft type")
    duration_minutes: Optional[int] = Field(
        None, description="Flight duration in minutes"
    )

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format."""
        if len(v) != 3 or not v.isalpha():
            raise ValueError("Airport code must be 3 letters")
        return v.upper()


class FlightOffer(TripSageModel):
    """Flight offer response model."""

    id: str = Field(..., description="Offer ID")
    search_id: Optional[str] = Field(None, description="Associated search ID")
    outbound_segments: List[FlightSegment] = Field(
        ..., description="Outbound flight segments"
    )
    return_segments: Optional[List[FlightSegment]] = Field(
        None, description="Return flight segments"
    )

    total_price: float = Field(..., description="Total price")
    base_price: Optional[float] = Field(None, description="Base fare price")
    taxes: Optional[float] = Field(None, description="Taxes and fees")
    currency: str = Field(..., description="Price currency")

    cabin_class: CabinClass = Field(..., description="Cabin class")
    booking_class: Optional[str] = Field(None, description="Booking class code")

    total_duration: Optional[int] = Field(
        None, description="Total travel time in minutes"
    )
    stops_count: int = Field(default=0, description="Number of stops")
    airlines: List[str] = Field(default_factory=list, description="Airlines involved")

    expires_at: Optional[datetime] = Field(None, description="Offer expiration time")
    bookable: bool = Field(default=True, description="Whether offer can be booked")

    source: Optional[str] = Field(
        None, description="Source API (duffel, amadeus, etc.)"
    )
    source_offer_id: Optional[str] = Field(
        None, description="Original offer ID from source"
    )

    # Scoring and ranking
    score: Optional[float] = Field(None, ge=0, le=1, description="Quality score")
    price_score: Optional[float] = Field(
        None, ge=0, le=1, description="Price competitiveness"
    )
    convenience_score: Optional[float] = Field(
        None, ge=0, le=1, description="Convenience score"
    )


class FlightBooking(TripSageModel):
    """Flight booking response model."""

    id: str = Field(..., description="Booking ID")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    user_id: str = Field(..., description="User ID")

    offer_id: str = Field(..., description="Booked offer ID")
    confirmation_number: Optional[str] = Field(
        None, description="Airline confirmation number"
    )

    passengers: List[FlightPassenger] = Field(..., description="Passenger details")
    outbound_segments: List[FlightSegment] = Field(..., description="Outbound segments")
    return_segments: Optional[List[FlightSegment]] = Field(
        None, description="Return segments"
    )

    total_price: float = Field(..., description="Total booking price")
    currency: str = Field(..., description="Price currency")

    status: BookingStatus = Field(..., description="Booking status")
    booked_at: datetime = Field(..., description="Booking timestamp")
    expires_at: Optional[datetime] = Field(None, description="Booking expiration")

    cancellable: bool = Field(
        default=False, description="Whether booking can be cancelled"
    )
    refundable: bool = Field(default=False, description="Whether booking is refundable")

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FlightSearchResponse(TripSageModel):
    """Flight search response model."""

    search_id: str = Field(..., description="Search ID")
    offers: List[FlightOffer] = Field(..., description="Flight offers")
    search_parameters: FlightSearchRequest = Field(
        ..., description="Original search parameters"
    )
    total_results: int = Field(..., description="Total number of results")
    search_duration_ms: Optional[int] = Field(
        None, description="Search duration in milliseconds"
    )
    cached: bool = Field(default=False, description="Whether results were cached")


class FlightBookingRequest(TripSageModel):
    """Request model for flight booking."""

    offer_id: str = Field(..., description="Offer ID to book")
    passengers: List[FlightPassenger] = Field(
        ..., description="Complete passenger information"
    )
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    hold_only: bool = Field(default=False, description="Hold booking without payment")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional booking metadata"
    )

    @field_validator("passengers")
    @classmethod
    def validate_passengers(cls, v: List[FlightPassenger]) -> List[FlightPassenger]:
        """Validate passenger information is complete for booking."""
        for passenger in v:
            if not passenger.given_name or not passenger.family_name:
                raise ValueError("Given name and family name are required for booking")
        return v


class FlightService:
    """
    Comprehensive flight service for search, booking, and management.

    This service handles:
    - Flight search with multiple providers
    - Flight booking and management
    - Price monitoring and alerts
    - Integration with external flight APIs
    - Caching and optimization
    - Trip integration
    """

    def __init__(
        self, database_service=None, external_flight_service=None, cache_ttl: int = 300
    ):
        """
        Initialize the flight service.

        Args:
            database_service: Database service for persistence
            external_flight_service: External flight API service
            cache_ttl: Cache TTL in seconds
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        if external_flight_service is None:
            # Import external service dynamically
            try:
                from tripsage_core.services.external_apis.duffel_http_client import (
                    DuffelHTTPClient as DuffelFlightsService,
                )

                external_flight_service = DuffelFlightsService()
            except ImportError:
                logger.warning("External flights service not available")
                external_flight_service = None

        self.db = database_service
        self.external_service = external_flight_service
        self.cache_ttl = cache_ttl

        # In-memory cache for search results
        self._search_cache: Dict[str, tuple] = {}

    async def search_flights(
        self, search_request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """
        Search for flight offers.

        Args:
            search_request: Flight search parameters

        Returns:
            Flight search results with offers

        Raises:
            ValidationError: If search parameters are invalid
            ServiceError: If search fails
        """
        try:
            search_id = str(uuid4())
            start_time = datetime.now(timezone.utc)

            # Check cache first
            cache_key = self._generate_search_cache_key(search_request)
            cached_result = self._get_cached_search(cache_key)

            if cached_result:
                logger.info(
                    "Returning cached flight search results",
                    extra={"search_id": search_id, "cache_key": cache_key},
                )

                return FlightSearchResponse(
                    search_id=search_id,
                    offers=cached_result["offers"],
                    search_parameters=search_request,
                    total_results=len(cached_result["offers"]),
                    cached=True,
                )

            # Perform external search
            offers = []
            if self.external_service:
                try:
                    external_offers = await self._search_external_api(search_request)
                    offers.extend(external_offers)
                except Exception as e:
                    logger.error(
                        "External flight search failed",
                        extra={"error": str(e), "search_id": search_id},
                    )

            # Add fallback/mock offers if no external service
            if not offers and not self.external_service:
                offers = await self._generate_mock_offers(search_request)

            # Score and rank offers
            scored_offers = await self._score_offers(offers, search_request)

            # Cache results
            self._cache_search_results(cache_key, scored_offers)

            # Store search in database
            await self._store_search_history(search_id, search_request, scored_offers)

            search_duration = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            logger.info(
                "Flight search completed",
                extra={
                    "search_id": search_id,
                    "offers_count": len(scored_offers),
                    "duration_ms": search_duration,
                },
            )

            return FlightSearchResponse(
                search_id=search_id,
                offers=scored_offers,
                search_parameters=search_request,
                total_results=len(scored_offers),
                search_duration_ms=search_duration,
                cached=False,
            )

        except Exception as e:
            logger.error(
                "Flight search failed",
                extra={
                    "error": str(e),
                    "origin": search_request.origin,
                    "destination": search_request.destination,
                },
            )
            raise ServiceError(f"Flight search failed: {str(e)}") from e

    async def get_offer_details(
        self, offer_id: str, user_id: str
    ) -> Optional[FlightOffer]:
        """
        Get detailed information about a flight offer.

        Args:
            offer_id: Offer ID
            user_id: User ID for access control

        Returns:
            Flight offer details or None if not found
        """
        try:
            # Try to get from database first
            offer_data = await self.db.get_flight_offer(offer_id, user_id)
            if offer_data:
                return FlightOffer(**offer_data)

            # Try external service if available
            if self.external_service:
                try:
                    external_offer = await self.external_service.get_offer_details(
                        offer_id
                    )
                    if external_offer:
                        # Convert to our model
                        converted_offer = await self._convert_external_offer(
                            external_offer
                        )

                        # Store for future reference
                        await self._store_offer(converted_offer, user_id)

                        return converted_offer
                except Exception as e:
                    logger.warning(
                        "Failed to get external offer details",
                        extra={"offer_id": offer_id, "error": str(e)},
                    )

            return None

        except Exception as e:
            logger.error(
                "Failed to get offer details",
                extra={"offer_id": offer_id, "user_id": user_id, "error": str(e)},
            )
            return None

    async def book_flight(
        self, user_id: str, booking_request: FlightBookingRequest
    ) -> FlightBooking:
        """
        Book a flight offer.

        Args:
            user_id: User ID
            booking_request: Booking request with passenger details

        Returns:
            Flight booking information

        Raises:
            NotFoundError: If offer not found
            ValidationError: If booking data is invalid
            ServiceError: If booking fails
        """
        try:
            # Get offer details
            offer = await self.get_offer_details(booking_request.offer_id, user_id)
            if not offer:
                raise NotFoundError("Flight offer not found")

            # Check if offer is still valid
            if offer.expires_at and datetime.now(timezone.utc) > offer.expires_at:
                raise ValidationError("Flight offer has expired")

            if not offer.bookable:
                raise ValidationError("Flight offer is not bookable")

            booking_id = str(uuid4())
            now = datetime.now(timezone.utc)

            # Create booking record
            booking = FlightBooking(
                id=booking_id,
                trip_id=booking_request.trip_id,
                user_id=user_id,
                offer_id=booking_request.offer_id,
                passengers=booking_request.passengers,
                outbound_segments=offer.outbound_segments,
                return_segments=offer.return_segments,
                total_price=offer.total_price,
                currency=offer.currency,
                status=BookingStatus.HOLD
                if booking_request.hold_only
                else BookingStatus.BOOKED,
                booked_at=now,
                metadata=booking_request.metadata or {},
            )

            # Attempt external booking if not hold-only
            if not booking_request.hold_only and self.external_service:
                try:
                    external_booking = await self._book_external_flight(
                        offer, booking_request
                    )
                    if external_booking:
                        booking.confirmation_number = external_booking.get(
                            "confirmation_number"
                        )
                        booking.status = BookingStatus.BOOKED
                        booking.cancellable = external_booking.get("cancellable", False)
                        booking.refundable = external_booking.get("refundable", False)
                except Exception as e:
                    logger.error(
                        "External booking failed",
                        extra={
                            "booking_id": booking_id,
                            "offer_id": booking_request.offer_id,
                            "error": str(e),
                        },
                    )
                    # Continue with hold status if external booking fails
                    booking.status = BookingStatus.HOLD

            # Store booking in database
            await self._store_booking(booking)

            logger.info(
                "Flight booked successfully",
                extra={
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "offer_id": booking_request.offer_id,
                    "status": booking.status.value,
                },
            )

            return booking

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Flight booking failed",
                extra={
                    "user_id": user_id,
                    "offer_id": booking_request.offer_id,
                    "error": str(e),
                },
            )
            raise ServiceError(f"Flight booking failed: {str(e)}") from e

    async def get_user_bookings(
        self,
        user_id: str,
        trip_id: Optional[str] = None,
        status: Optional[BookingStatus] = None,
        limit: int = 50,
    ) -> List[FlightBooking]:
        """
        Get flight bookings for a user.

        Args:
            user_id: User ID
            trip_id: Optional trip ID filter
            status: Optional status filter
            limit: Maximum number of bookings

        Returns:
            List of flight bookings
        """
        try:
            filters = {"user_id": user_id}
            if trip_id:
                filters["trip_id"] = trip_id
            if status:
                filters["status"] = status.value

            results = await self.db.get_flight_bookings(filters, limit)

            bookings = []
            for result in results:
                bookings.append(FlightBooking(**result))

            return bookings

        except Exception as e:
            logger.error(
                "Failed to get user bookings",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def cancel_booking(self, booking_id: str, user_id: str) -> bool:
        """
        Cancel a flight booking.

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
            booking_data = await self.db.get_flight_booking(booking_id, user_id)
            if not booking_data:
                raise NotFoundError("Flight booking not found")

            booking = FlightBooking(**booking_data)

            # Check if cancellable
            if booking.status in {BookingStatus.CANCELLED, BookingStatus.EXPIRED}:
                raise ValidationError("Booking is already cancelled or expired")

            # Attempt external cancellation if booked externally
            if booking.status == BookingStatus.BOOKED and self.external_service:
                try:
                    await self._cancel_external_booking(booking)
                except Exception as e:
                    logger.warning(
                        "External cancellation failed",
                        extra={"booking_id": booking_id, "error": str(e)},
                    )

            # Update booking status
            success = await self.db.update_flight_booking(
                booking_id, {"status": BookingStatus.CANCELLED.value}
            )

            if success:
                logger.info(
                    "Flight booking cancelled",
                    extra={"booking_id": booking_id, "user_id": user_id},
                )

            return success

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to cancel booking",
                extra={"booking_id": booking_id, "user_id": user_id, "error": str(e)},
            )
            return False

    async def _search_external_api(
        self, search_request: FlightSearchRequest
    ) -> List[FlightOffer]:
        """Search flights using external API."""
        if not self.external_service:
            return []

        try:
            # Convert passengers for external API
            external_passengers = []
            for passenger in search_request.passengers:
                external_passengers.append(
                    {
                        "type": passenger.type.value,
                        "given_name": passenger.given_name or "",
                        "family_name": passenger.family_name or "",
                    }
                )

            # Call external API
            external_offers = await self.external_service.search_flights(
                origin=search_request.origin,
                destination=search_request.destination,
                departure_date=search_request.departure_date,
                return_date=search_request.return_date,
                passengers=external_passengers,
                cabin_class=search_request.cabin_class.value,
                max_connections=search_request.max_stops,
                currency=search_request.currency,
            )

            # Convert to our model
            converted_offers = []
            for external_offer in external_offers:
                converted_offer = await self._convert_external_offer(external_offer)
                converted_offers.append(converted_offer)

            return converted_offers

        except Exception as e:
            logger.error("External API search failed", extra={"error": str(e)})
            return []

    async def _convert_external_offer(self, external_offer) -> FlightOffer:
        """Convert external API offer to our model."""
        # This is a simplified conversion - in practice you'd map all fields
        return FlightOffer(
            id=external_offer.get("id", str(uuid4())),
            outbound_segments=[],  # Would parse segments from external format
            total_price=float(external_offer.get("total_amount", 0)),
            currency=external_offer.get("total_currency", "USD"),
            cabin_class=CabinClass.ECONOMY,  # Would parse from external data
            source="external_api",
            source_offer_id=external_offer.get("id"),
        )

    async def _generate_mock_offers(
        self, search_request: FlightSearchRequest
    ) -> List[FlightOffer]:
        """Generate mock flight offers for testing."""
        offers = []

        # Generate a few mock offers with different prices and options
        base_price = 300.0
        for i in range(3):
            offer = FlightOffer(
                id=str(uuid4()),
                outbound_segments=[
                    FlightSegment(
                        origin=search_request.origin,
                        destination=search_request.destination,
                        departure_date=search_request.departure_date,
                        arrival_date=search_request.departure_date.replace(
                            hour=search_request.departure_date.hour + 3
                        ),
                        airline=f"AA{100 + i}",
                        flight_number=f"AA{1000 + i}",
                    )
                ],
                total_price=base_price + (i * 50),
                currency=search_request.currency,
                cabin_class=search_request.cabin_class,
                stops_count=i,
                airlines=[f"AA{100 + i}"],
                source="mock",
                bookable=True,
            )
            offers.append(offer)

        return offers

    async def _score_offers(
        self, offers: List[FlightOffer], search_request: FlightSearchRequest
    ) -> List[FlightOffer]:
        """Score and rank flight offers."""
        if not offers:
            return offers

        # Simple scoring based on price and convenience
        prices = [offer.total_price for offer in offers]
        min_price = min(prices)
        max_price = max(prices)

        for offer in offers:
            # Price score (lower price = higher score)
            if max_price > min_price:
                price_score = 1 - (offer.total_price - min_price) / (
                    max_price - min_price
                )
            else:
                price_score = 1.0

            # Convenience score (fewer stops = higher score)
            convenience_score = max(0, 1 - (offer.stops_count * 0.3))

            # Overall score (weighted average)
            overall_score = (price_score * 0.7) + (convenience_score * 0.3)

            offer.price_score = price_score
            offer.convenience_score = convenience_score
            offer.score = overall_score

        # Sort by score (highest first)
        return sorted(offers, key=lambda x: x.score or 0, reverse=True)

    def _generate_search_cache_key(self, search_request: FlightSearchRequest) -> str:
        """Generate cache key for search request."""
        import hashlib

        key_data = (
            f"{search_request.origin}:{search_request.destination}:"
            f"{search_request.departure_date.date()}:"
            f"{search_request.return_date.date() if search_request.return_date else ''}:"  # noqa: E501
            f"{len(search_request.passengers)}:{search_request.cabin_class.value}"
        )

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_search(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached search results if still valid."""
        if cache_key in self._search_cache:
            result, timestamp = self._search_cache[cache_key]
            import time

            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self._search_cache[cache_key]
        return None

    def _cache_search_results(self, cache_key: str, offers: List[FlightOffer]) -> None:
        """Cache search results."""
        import time

        self._search_cache[cache_key] = ({"offers": offers}, time.time())

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
        search_request: FlightSearchRequest,
        offers: List[FlightOffer],
    ) -> None:
        """Store search history in database."""
        try:
            search_data = {
                "id": search_id,
                "origin": search_request.origin,
                "destination": search_request.destination,
                "departure_date": search_request.departure_date.isoformat(),
                "return_date": search_request.return_date.isoformat()
                if search_request.return_date
                else None,
                "passenger_count": len(search_request.passengers),
                "cabin_class": search_request.cabin_class.value,
                "offers_count": len(offers),
                "search_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await self.db.store_flight_search(search_data)

        except Exception as e:
            logger.warning(
                "Failed to store search history",
                extra={"search_id": search_id, "error": str(e)},
            )

    async def _store_offer(self, offer: FlightOffer, user_id: str) -> None:
        """Store flight offer in database."""
        try:
            offer_data = offer.model_dump()
            offer_data["user_id"] = user_id
            offer_data["stored_at"] = datetime.now(timezone.utc).isoformat()

            await self.db.store_flight_offer(offer_data)

        except Exception as e:
            logger.warning(
                "Failed to store offer", extra={"offer_id": offer.id, "error": str(e)}
            )

    async def _store_booking(self, booking: FlightBooking) -> None:
        """Store flight booking in database."""
        try:
            booking_data = booking.model_dump()
            booking_data["created_at"] = datetime.now(timezone.utc).isoformat()

            await self.db.store_flight_booking(booking_data)

        except Exception as e:
            logger.error(
                "Failed to store booking",
                extra={"booking_id": booking.id, "error": str(e)},
            )
            raise

    async def _book_external_flight(
        self, offer: FlightOffer, booking_request: FlightBookingRequest
    ) -> Optional[Dict[str, Any]]:
        """Book flight using external API."""
        if not self.external_service:
            return None

        try:
            # Convert passengers for external API
            external_passengers = []
            for passenger in booking_request.passengers:
                external_passengers.append(
                    {
                        "type": passenger.type.value,
                        "given_name": passenger.given_name,
                        "family_name": passenger.family_name,
                        "born_on": passenger.date_of_birth.date()
                        if passenger.date_of_birth
                        else None,
                        "email": passenger.email,
                        "phone_number": passenger.phone,
                    }
                )

            # Create external booking
            external_order = await self.external_service.create_order(
                offer_id=offer.source_offer_id or offer.id,
                passengers=external_passengers,
                payment={"type": "balance", "amount": 0},  # Test payment
            )

            return {
                "confirmation_number": external_order.get("booking_reference"),
                "cancellable": True,
                "refundable": False,
            }

        except Exception as e:
            logger.error(
                "External booking failed",
                extra={"offer_id": offer.id, "error": str(e)},
            )
            return None

    async def _cancel_external_booking(self, booking: FlightBooking) -> None:
        """Cancel booking using external API."""
        if not self.external_service:
            return

        try:
            # This would call the external API to cancel
            # Implementation depends on the external service
            pass

        except Exception as e:
            logger.error(
                "External cancellation failed",
                extra={"booking_id": booking.id, "error": str(e)},
            )


# Dependency function for FastAPI
async def get_flight_service() -> FlightService:
    """
    Get flight service instance for dependency injection.

    Returns:
        FlightService instance
    """
    return FlightService()
