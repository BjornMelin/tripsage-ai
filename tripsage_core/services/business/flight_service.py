"""Flight service for flight management operations.

This service consolidates flight-related business logic including flight search,
booking, management, and integration with external flight APIs. It provides
clean abstractions over external services while maintaining proper data relationships.
"""
# pylint: disable=duplicate-code

import logging
from datetime import UTC, datetime, time, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
    CoreServiceError as ServiceError,
    CoreValidationError as ValidationError,
)
from tripsage_core.models.domain.flights_canonical import (
    FlightBooking,
    FlightBookingRequest,
    FlightOffer,
    FlightSearchResponse,
    FlightSegment,
)
from tripsage_core.models.schemas_common.enums import (
    BookingStatus,
    CabinClass,
    PassengerType,
)
from tripsage_core.models.schemas_common.flight_schemas import (
    FlightPassenger,
    FlightSearchRequest,
)
from tripsage_core.observability.otel import record_histogram, trace_span


logger = logging.getLogger(__name__)

RECOVERABLE_ERRORS = (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
    ValueError,
    KeyError,
    TypeError,
)


class FlightType(str, Enum):
    """Flight type enumeration."""

    ROUND_TRIP = "round_trip"
    ONE_WAY = "one_way"
    MULTI_CITY = "multi_city"


# Note: Using BookingStatus, CabinClass, PassengerType from schemas_common.enums
# Re-export for convenience
__all__ = [
    "BookingStatus",
    "CabinClass",
    "FlightBooking",
    "FlightBookingRequest",
    "FlightOffer",
    "FlightPassenger",
    "FlightSearchRequest",
    "FlightSearchResponse",
    "FlightSegment",
    "FlightService",
    "FlightType",
    "PassengerType",
]


# Models are imported from the canonical domain module above.


class FlightService:
    """Comprehensive flight service for search, booking, and management.

    This service handles:
    - Flight search with multiple providers
    - Flight booking and management
    - Price monitoring and alerts
    - Integration with external flight APIs
    - Caching and optimization
    - Trip integration
    """

    def __init__(
        self, *, database_service, external_flight_service=None, cache_ttl: int = 300
    ):
        """Initialize the flight service.

        Args:
            database_service: Database service for persistence
            external_flight_service: External flight API service
            cache_ttl: Cache TTL in seconds
        """
        # Dependencies must be provided explicitly via DI

        # Allow dynamic attributes on services for type checker flexibility
        self.db: Any = database_service
        self.external_service: Any = external_flight_service
        self.cache_ttl = cache_ttl

        # In-memory cache for search results
        self._search_cache: dict[str, tuple] = {}

    async def search_flights(
        self, search_request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for flight offers.

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
            start_time = datetime.now(UTC)

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
                    search_duration_ms=0,
                    cached=True,
                )

            # Perform external search
            offers = []
            if self.external_service:
                try:
                    external_offers = await self._search_external_api(search_request)
                    offers.extend(external_offers)
                except RECOVERABLE_ERRORS as error:
                    logger.exception(
                        "External flight search failed",
                        extra={"error": str(error), "search_id": search_id},
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
                (datetime.now(UTC) - start_time).total_seconds() * 1000
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

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Flight search failed",
                extra={
                    "error": str(error),
                    "origin": search_request.origin,
                    "destination": search_request.destination,
                },
            )
            raise ServiceError(f"Flight search failed: {error!s}") from error

    async def get_offer_details(
        self, offer_id: str, user_id: str
    ) -> FlightOffer | None:
        """Get detailed information about a flight offer.

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
                except RECOVERABLE_ERRORS as error:
                    logger.warning(
                        "Failed to get external offer details",
                        extra={"offer_id": offer_id, "error": str(error)},
                    )

            return None

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get offer details",
                extra={"offer_id": offer_id, "user_id": user_id, "error": str(error)},
            )
            return None

    async def book_flight(
        self, user_id: str, booking_request: FlightBookingRequest
    ) -> FlightBooking:
        """Book a flight offer.

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
            if offer.expires_at and datetime.now(UTC) > offer.expires_at:
                raise ValidationError("Flight offer has expired")

            if not offer.bookable:
                raise ValidationError("Flight offer is not bookable")

            booking_id = str(uuid4())
            now = datetime.now(UTC)

            # Create booking record
            booking = FlightBooking(  # type: ignore[reportCallIssue]
                id=booking_id,
                trip_id=booking_request.trip_id,
                user_id=user_id,
                offer_id=booking_request.offer_id,
                passengers=booking_request.passengers,
                outbound_segments=offer.outbound_segments,
                return_segments=offer.return_segments,
                total_price=offer.total_price,
                currency=offer.currency,
                status=BookingStatus.SAVED
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
                except RECOVERABLE_ERRORS as error:
                    logger.exception(
                        "External booking failed",
                        extra={
                            "booking_id": booking_id,
                            "offer_id": booking_request.offer_id,
                            "error": str(error),
                        },
                    )
                    # Continue with saved status if external booking fails
                    booking.status = BookingStatus.SAVED

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

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Flight booking failed",
                extra={
                    "user_id": user_id,
                    "offer_id": booking_request.offer_id,
                    "error": str(error),
                },
            )
            raise ServiceError(f"Flight booking failed: {error!s}") from error

    async def get_user_bookings(
        self,
        user_id: str,
        trip_id: str | None = None,
        status: BookingStatus | None = None,
        limit: int = 50,
    ) -> list[FlightBooking]:
        """Get flight bookings for a user.

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

            return [FlightBooking(**result) for result in results]

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get user bookings",
                extra={"user_id": user_id, "error": str(error)},
            )
            return []

    async def cancel_booking(self, booking_id: str, user_id: str) -> bool:
        """Cancel a flight booking.

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
            if booking.status in {BookingStatus.CANCELLED}:
                raise ValidationError("Booking is already cancelled or expired")

            # Attempt external cancellation if booked externally
            if booking.status == BookingStatus.BOOKED and self.external_service:
                try:
                    await self._cancel_external_booking(booking)
                except RECOVERABLE_ERRORS as error:
                    logger.warning(
                        "External cancellation failed",
                        extra={"booking_id": booking_id, "error": str(error)},
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

    @trace_span(
        "flights.search_external",
        attrs=lambda a, k: {"origin": a[1].origin, "destination": a[1].destination},
    )
    @record_histogram("flights.search_external.duration", unit="s")
    async def _search_external_api(
        self, search_request: FlightSearchRequest
    ) -> list[FlightOffer]:
        """Search flights using external API."""
        if not self.external_service:
            return []

        try:
            # Build passengers if detailed list not provided
            passengers_list = search_request.passengers or (
                [
                    FlightPassenger(
                        type=PassengerType.ADULT,
                        age=None,
                        given_name=None,
                        family_name=None,
                        title=None,
                        date_of_birth=None,
                        email=None,
                        phone=None,
                    )
                    for _ in range(search_request.adults)
                ]
                + [
                    FlightPassenger(
                        type=PassengerType.CHILD,
                        age=None,
                        given_name=None,
                        family_name=None,
                        title=None,
                        date_of_birth=None,
                        email=None,
                        phone=None,
                    )
                    for _ in range(search_request.children)
                ]
                + [
                    FlightPassenger(
                        type=PassengerType.INFANT,
                        age=None,
                        given_name=None,
                        family_name=None,
                        title=None,
                        date_of_birth=None,
                        email=None,
                        phone=None,
                    )
                    for _ in range(search_request.infants)
                ]
            )

            external_passengers = [
                {
                    "type": p.type.value,
                    "given_name": (p.given_name or ""),
                    "family_name": (p.family_name or ""),
                }
                for p in passengers_list
            ]

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

            return [
                await self._convert_external_offer(external_offer)
                for external_offer in external_offers
            ]

        except RECOVERABLE_ERRORS as error:
            logger.exception("External API search failed", extra={"error": str(error)})
            return []

    @trace_span("flights.convert_offer")
    async def _convert_external_offer(self, external_offer) -> FlightOffer:
        """Convert a Duffel offer (model or dict) into service FlightOffer."""
        from tripsage_core.models.mappers.flights_mapper import (
            duffel_offer_to_service_offer,
        )

        try:
            return duffel_offer_to_service_offer(external_offer)
        except (AttributeError, KeyError, TypeError, ValueError):
            logger.exception(
                "Failed to convert external offer; returning minimal fallback"
            )
            # Minimal safe fallback to avoid breaking flow
            try:
                oid = getattr(external_offer, "id", None) or external_offer.get("id")  # type: ignore[attr-defined]
            except (AttributeError, KeyError):
                oid = str(uuid4())
            return FlightOffer(  # type: ignore[reportCallIssue]
                id=str(oid),
                outbound_segments=[],
                total_price=0.0,
                currency="USD",
                cabin_class=CabinClass.ECONOMY,
                source="duffel",
                source_offer_id=str(oid),
            )

    async def _generate_mock_offers(
        self, search_request: FlightSearchRequest
    ) -> list[FlightOffer]:
        """Generate mock flight offers for testing."""
        # Generate a few mock offers with different prices and options
        base_price = 300.0
        return [
            FlightOffer(
                id=str(uuid4()),
                outbound_segments=[
                    FlightSegment(
                        origin=search_request.origin,
                        destination=search_request.destination,
                        # Normalize date → datetime for mock data
                        departure_date=(
                            search_request.departure_date
                            if isinstance(search_request.departure_date, datetime)
                            else datetime.combine(
                                search_request.departure_date, time(9, 0), tzinfo=UTC
                            )
                        ),
                        arrival_date=(
                            (
                                search_request.departure_date
                                if isinstance(search_request.departure_date, datetime)
                                else datetime.combine(
                                    search_request.departure_date,
                                    time(9, 0),
                                    tzinfo=UTC,
                                )
                            )
                            + timedelta(hours=3)
                        ),
                        airline=f"AA{100 + i}",
                        flight_number=f"AA{1000 + i}",
                        aircraft_type=None,
                        duration_minutes=None,
                    )
                ],
                total_price=base_price + (i * 50),
                currency=search_request.currency,
                cabin_class=search_request.cabin_class,
                stops_count=i,
                airlines=[f"AA{100 + i}"],
                source="mock",
                bookable=True,
                search_id=None,
                return_segments=None,
                base_price=None,
                taxes=None,
                booking_class=None,
                total_duration=None,
                expires_at=None,
                source_offer_id=None,
                score=None,
                price_score=None,
                convenience_score=None,
            )
            for i in range(3)
        ]

    async def _score_offers(
        self, offers: list[FlightOffer], search_request: FlightSearchRequest
    ) -> list[FlightOffer]:
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
        from datetime import date as _date

        def _norm_date(val: datetime | _date | None):
            if val is None:
                return ""
            if isinstance(val, datetime):
                return val.date().isoformat()
            # `val` may be a date object; it has isoformat
            return val.isoformat()

        passenger_count = (
            len(search_request.passengers or []) or search_request.total_passengers
        )

        key_data = (
            f"{search_request.origin}:{search_request.destination}:"
            f"{_norm_date(search_request.departure_date)}:"
            f"{_norm_date(search_request.return_date)}:"
            f"{passenger_count}:{search_request.cabin_class.value}"
        )

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_search(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached search results if still valid."""
        if cache_key in self._search_cache:
            result, timestamp = self._search_cache[cache_key]
            import time as _time

            if _time.time() - timestamp < self.cache_ttl:
                return result
            del self._search_cache[cache_key]
        return None

    def _cache_search_results(self, cache_key: str, offers: list[FlightOffer]) -> None:
        """Cache search results."""
        import time as _time

        self._search_cache[cache_key] = ({"offers": offers}, _time.time())

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
        offers: list[FlightOffer],
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
                "passenger_count": len(search_request.passengers or []),
                "cabin_class": search_request.cabin_class.value,
                "offers_count": len(offers),
                "search_timestamp": datetime.now(UTC).isoformat(),
            }

            await self.db.store_flight_search(search_data)

        except RECOVERABLE_ERRORS as error:
            logger.warning(
                "Failed to store search history",
                extra={"search_id": search_id, "error": str(error)},
            )

    async def _store_offer(self, offer: FlightOffer, user_id: str) -> None:
        """Store flight offer in database."""
        try:
            offer_data = offer.model_dump()
            offer_data["user_id"] = user_id
            offer_data["stored_at"] = datetime.now(UTC).isoformat()

            await self.db.store_flight_offer(offer_data)

        except RECOVERABLE_ERRORS as error:
            logger.warning(
                "Failed to store offer",
                extra={"offer_id": offer.id, "error": str(error)},
            )

    async def _store_booking(self, booking: FlightBooking) -> None:
        """Store flight booking in database."""
        try:
            booking_data = booking.model_dump()
            booking_data["created_at"] = datetime.now(UTC).isoformat()

            await self.db.store_flight_booking(booking_data)

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to store booking",
                extra={"booking_id": booking.id, "error": str(error)},
            )
            raise

    async def _book_external_flight(
        self, offer: FlightOffer, booking_request: FlightBookingRequest
    ) -> dict[str, Any] | None:
        """Book flight using external API."""
        if not self.external_service:
            return None

        try:
            external_passengers = [
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
                for passenger in booking_request.passengers
            ]

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

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "External booking failed",
                extra={"offer_id": offer.id, "error": str(error)},
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

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "External cancellation failed",
                extra={"booking_id": booking.id, "error": str(error)},
            )


# FINAL-ONLY: Remove FastAPI dependency factory; construct via API DI where needed.
