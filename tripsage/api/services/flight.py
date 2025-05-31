"""Flight service for TripSage API.

This service acts as a thin wrapper around the core flight service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import Depends

from tripsage.api.models.flights import (
    Airport,
    AirportSearchRequest,
    AirportSearchResponse,
    FlightOffer,
    FlightSearchRequest,
    FlightSearchResponse,
    MultiCityFlightSearchRequest,
    SavedFlightRequest,
    SavedFlightResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.flight_service import (
    FlightService as CoreFlightService,
)
from tripsage_core.services.business.flight_service import (
    get_flight_service as get_core_flight_service,
)

logger = logging.getLogger(__name__)


class FlightService:
    """
    API flight service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_flight_service: Optional[CoreFlightService] = None):
        """
        Initialize the API flight service.

        Args:
            core_flight_service: Core flight service
        """
        self.core_flight_service = core_flight_service

    async def _get_core_flight_service(self) -> CoreFlightService:
        """Get or create core flight service instance."""
        if self.core_flight_service is None:
            self.core_flight_service = await get_core_flight_service()
        return self.core_flight_service

    async def search_flights(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for flights based on the provided criteria.

        Args:
            request: Flight search request parameters

        Returns:
            Flight search results

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If search fails
        """
        try:
            logger.info(
                f"Searching for flights from {request.origin} to {request.destination} "
                f"on {request.departure_date}"
            )

            # Adapt API request to core model
            core_request = self._adapt_flight_search_request(request)

            # Search via core service
            core_service = await self._get_core_flight_service()
            core_response = await core_service.search_flights(core_request)

            # Adapt core response to API model
            return self._adapt_flight_search_response(core_response, request)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Flight search failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in flight search: {str(e)}")
            raise ServiceError("Flight search failed") from e

    async def search_multi_city_flights(
        self, request: MultiCityFlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for multi-city flights based on the provided criteria.

        Args:
            request: Multi-city flight search request parameters

        Returns:
            Flight search results

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If search fails
        """
        try:
            logger.info(
                f"Searching for multi-city flights with {len(request.segments)} segments"
            )

            # Adapt API request to core model
            core_request = self._adapt_multi_city_request(request)

            # Search via core service
            core_service = await self._get_core_flight_service()
            core_response = await core_service.search_multi_city_flights(core_request)

            # Adapt core response to API model
            return self._adapt_flight_search_response(core_response, request)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Multi-city flight search failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in multi-city flight search: {str(e)}")
            raise ServiceError("Multi-city flight search failed") from e

    async def search_airports(
        self, request: AirportSearchRequest
    ) -> AirportSearchResponse:
        """Search for airports based on the provided query.

        Args:
            request: Airport search request parameters

        Returns:
            Airport search results

        Raises:
            ServiceError: If search fails
        """
        try:
            logger.info(f"Searching for airports with query: '{request.query}'")

            # Adapt API request to core model
            core_request = self._adapt_airport_search_request(request)

            # Search via core service
            core_service = await self._get_core_flight_service()
            core_response = await core_service.search_airports(core_request)

            # Adapt core response to API model
            return self._adapt_airport_search_response(core_response)

        except Exception as e:
            logger.error(f"Airport search failed: {str(e)}")
            raise ServiceError("Airport search failed") from e

    async def get_flight_offer(self, offer_id: str) -> Optional[FlightOffer]:
        """Get details of a specific flight offer.

        Args:
            offer_id: Flight offer ID

        Returns:
            Flight offer details if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting flight offer with ID: {offer_id}")

            # Get offer via core service
            core_service = await self._get_core_flight_service()
            core_offer = await core_service.get_flight_offer(offer_id)

            if core_offer is None:
                return None

            # Adapt core response to API model
            return self._adapt_flight_offer(core_offer)

        except Exception as e:
            logger.error(f"Failed to get flight offer {offer_id}: {str(e)}")
            raise ServiceError("Failed to get flight offer") from e

    async def save_flight(
        self, user_id: str, request: SavedFlightRequest
    ) -> Optional[SavedFlightResponse]:
        """Save a flight offer for a trip.

        Args:
            user_id: User ID
            request: Save flight request

        Returns:
            Saved flight response if successful, None otherwise

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If save fails
        """
        try:
            logger.info(
                f"Saving flight offer {request.offer_id} for user {user_id} "
                f"and trip {request.trip_id}"
            )

            # Adapt API request to core model
            core_request = self._adapt_save_flight_request(request)

            # Save via core service
            core_service = await self._get_core_flight_service()
            core_response = await core_service.save_flight(user_id, core_request)

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_saved_flight_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to save flight: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving flight: {str(e)}")
            raise ServiceError("Failed to save flight") from e

    async def delete_saved_flight(self, user_id: str, saved_flight_id: UUID) -> bool:
        """Delete a saved flight.

        Args:
            user_id: User ID
            saved_flight_id: Saved flight ID

        Returns:
            True if deleted, False otherwise

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting saved flight {saved_flight_id} for user {user_id}")

            # Delete via core service
            core_service = await self._get_core_flight_service()
            return await core_service.delete_saved_flight(user_id, str(saved_flight_id))

        except Exception as e:
            logger.error(f"Failed to delete saved flight: {str(e)}")
            raise ServiceError("Failed to delete saved flight") from e

    async def list_saved_flights(
        self, user_id: str, trip_id: Optional[UUID] = None
    ) -> List[SavedFlightResponse]:
        """List saved flights for a user, optionally filtered by trip.

        Args:
            user_id: User ID
            trip_id: Optional trip ID to filter by

        Returns:
            List of saved flights

        Raises:
            ServiceError: If listing fails
        """
        try:
            logger.info(
                f"Listing saved flights for user {user_id}"
                + (f" and trip {trip_id}" if trip_id else "")
            )

            # List via core service
            core_service = await self._get_core_flight_service()
            core_flights = await core_service.list_saved_flights(
                user_id, str(trip_id) if trip_id else None
            )

            # Adapt core response to API model
            return [
                self._adapt_saved_flight_response(flight) for flight in core_flights
            ]

        except Exception as e:
            logger.error(f"Failed to list saved flights: {str(e)}")
            raise ServiceError("Failed to list saved flights") from e

    async def health_check(self) -> bool:
        """Check if the flight service is operational.

        Returns:
            True if service is operational, False otherwise
        """
        try:
            core_service = await self._get_core_flight_service()
            return await core_service.health_check()
        except Exception:
            return False

    def _adapt_flight_search_request(self, request: FlightSearchRequest) -> dict:
        """Adapt API flight search request to core model."""
        return {
            "origin": request.origin,
            "destination": request.destination,
            "departure_date": request.departure_date,
            "return_date": request.return_date,
            "adults": getattr(request, "adults", 1),
            "children": getattr(request, "children", 0),
            "infants": getattr(request, "infants", 0),
            "cabin_class": request.cabin_class,
            "max_stops": getattr(request, "max_stops", None),
            "max_price": getattr(request, "max_price", None),
            "preferred_airlines": getattr(request, "preferred_airlines", None),
        }

    def _adapt_multi_city_request(self, request: MultiCityFlightSearchRequest) -> dict:
        """Adapt API multi-city request to core model."""
        return {
            "segments": [
                {
                    "origin": segment.origin,
                    "destination": segment.destination,
                    "departure_date": segment.departure_date,
                }
                for segment in request.segments
            ],
            "adults": getattr(request, "adults", 1),
            "children": getattr(request, "children", 0),
            "infants": getattr(request, "infants", 0),
            "cabin_class": request.cabin_class,
        }

    def _adapt_airport_search_request(self, request: AirportSearchRequest) -> dict:
        """Adapt API airport search request to core model."""
        return {
            "query": request.query,
            "limit": request.limit,
        }

    def _adapt_save_flight_request(self, request: SavedFlightRequest) -> dict:
        """Adapt API save flight request to core model."""
        return {
            "offer_id": request.offer_id,
            "trip_id": str(request.trip_id) if request.trip_id else None,
            "notes": request.notes,
        }

    def _adapt_flight_search_response(
        self, core_response, original_request
    ) -> FlightSearchResponse:
        """Adapt core flight search response to API model."""
        # This is a simplified adaptation - in practice, you'd need detailed mapping
        flight_offers = []
        for core_offer in core_response.get("offers", []):
            flight_offer = self._adapt_flight_offer(core_offer)
            if flight_offer:
                flight_offers.append(flight_offer)

        return FlightSearchResponse(
            results=flight_offers,
            count=len(flight_offers),
            currency=core_response.get("currency", "USD"),
            search_id=core_response.get("search_id", ""),
            trip_id=original_request.trip_id,
            min_price=core_response.get("min_price"),
            max_price=core_response.get("max_price"),
            search_request=original_request,
        )

    def _adapt_airport_search_response(self, core_response) -> AirportSearchResponse:
        """Adapt core airport search response to API model."""
        airports = []
        for core_airport in core_response.get("airports", []):
            airport = Airport(
                code=core_airport.get("code", ""),
                name=core_airport.get("name", ""),
                city=core_airport.get("city", ""),
                country=core_airport.get("country", ""),
                country_code=core_airport.get("country_code", ""),
                latitude=core_airport.get("latitude", 0.0),
                longitude=core_airport.get("longitude", 0.0),
            )
            airports.append(airport)

        return AirportSearchResponse(
            results=airports,
            count=len(airports),
        )

    def _adapt_flight_offer(self, core_offer) -> Optional[FlightOffer]:
        """Adapt core flight offer to API model."""
        if not core_offer:
            return None

        # This is a simplified adaptation - real implementation would need detailed mapping
        return FlightOffer(
            id=core_offer.get("id", ""),
            origin=core_offer.get("origin", ""),
            destination=core_offer.get("destination", ""),
            departure_date=core_offer.get("departure_date"),
            return_date=core_offer.get("return_date"),
            airline=core_offer.get("airline", ""),
            airline_name=core_offer.get("airline_name", ""),
            price=core_offer.get("price", 0.0),
            currency=core_offer.get("currency", "USD"),
            cabin_class=core_offer.get("cabin_class", "economy"),
            stops=core_offer.get("stops", 0),
            duration_minutes=core_offer.get("duration_minutes", 0),
            segments=core_offer.get("segments", []),
            booking_link=core_offer.get("booking_link", ""),
        )

    def _adapt_saved_flight_response(self, core_response) -> SavedFlightResponse:
        """Adapt core saved flight response to API model."""
        return SavedFlightResponse(
            id=core_response.get("id"),
            user_id=core_response.get("user_id", ""),
            trip_id=core_response.get("trip_id"),
            offer=self._adapt_flight_offer(core_response.get("offer")),
            saved_at=core_response.get("saved_at"),
            notes=core_response.get("notes"),
        )


# Module-level dependency annotation
_core_flight_service_dep = Depends(get_core_flight_service)


# Dependency function for FastAPI
async def get_flight_service(
    core_flight_service: CoreFlightService = _core_flight_service_dep,
) -> FlightService:
    """
    Get flight service instance for dependency injection.

    Args:
        core_flight_service: Core flight service

    Returns:
        FlightService instance
    """
    return FlightService(core_flight_service=core_flight_service)
