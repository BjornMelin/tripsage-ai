"""Flight service for TripSage API.

This module provides the FlightService class for flight-related operations.
Supports both MCP and direct HTTP integration via feature flags (Issue #163).
"""

import logging
import uuid
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

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
from tripsage.config.feature_flags import IntegrationMode, feature_flags
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.models.flight import CabinClass
from tripsage.services.duffel_http_client import DuffelHTTPClient
from tripsage.tools.schemas.flights import FlightSearchParams
from tripsage.utils.error_handling import with_error_handling

logger = logging.getLogger(__name__)


class FlightService:
    """Service for flight-related operations.

    Supports both MCP and direct HTTP integration based on feature flags.
    When flights_integration is DIRECT, uses DuffelHTTPClient for direct API calls.
    When flights_integration is set to MCP, uses MCPManager for MCP-based integration.
    """

    def __init__(self):
        """Initialize the FlightService."""
        self.duffel_client: Optional[DuffelHTTPClient] = None
        self._initialize_clients()

    def _initialize_clients(self) -> None:
        """Initialize the appropriate client based on feature flags."""
        if feature_flags.flights_integration == IntegrationMode.DIRECT:
            try:
                self.duffel_client = DuffelHTTPClient()
                logger.info("FlightService initialized with direct HTTP client")
            except Exception as e:
                logger.warning(f"Failed to initialize DuffelHTTPClient: {str(e)}")
                logger.info("FlightService will fall back to MCP or mock data")
                self.duffel_client = None
        else:
            logger.info("FlightService initialized with MCP integration")

    def _validate_flight_search_request(self, request: FlightSearchRequest) -> None:
        """Validate flight search request parameters.

        Args:
            request: Flight search request to validate

        Raises:
            ValueError: When validation fails
        """
        from datetime import date, datetime

        # Validate dates
        today = date.today()
        departure_date = request.departure_date

        # Convert datetime to date if needed
        if isinstance(departure_date, datetime):
            departure_date = departure_date.date()
        elif isinstance(departure_date, str):
            try:
                departure_date = datetime.fromisoformat(departure_date).date()
            except ValueError as e:
                raise ValueError(f"Invalid departure date format: {departure_date}") from e

        if departure_date < today:
            raise ValueError("Departure date cannot be in the past")

        # Validate return date if provided
        if request.return_date:
            return_date = request.return_date
            if isinstance(return_date, datetime):
                return_date = return_date.date()
            elif isinstance(return_date, str):
                try:
                    return_date = datetime.fromisoformat(return_date).date()
                except ValueError as e:
                    raise ValueError(f"Invalid return date format: {return_date}") from e

            if return_date < departure_date:
                raise ValueError("Return date cannot be before departure date")

        # Validate airport codes (basic IATA format)
        if (
            not request.origin
            or len(request.origin) != 3
            or not request.origin.isalpha()
        ):
            raise ValueError(f"Invalid origin airport code: {request.origin}")

        if (
            not request.destination
            or len(request.destination) != 3
            or not request.destination.isalpha()
        ):
            raise ValueError(f"Invalid destination airport code: {request.destination}")

        # Validate passenger counts
        adults = getattr(request, "adults", 1)
        children = getattr(request, "children", 0)
        infants = getattr(request, "infants", 0)

        if adults < 1:
            raise ValueError("At least one adult passenger is required")
        if adults > 9:
            raise ValueError("Maximum 9 adult passengers allowed")
        if children < 0 or children > 8:
            raise ValueError("Children count must be between 0 and 8")
        if infants < 0 or infants > adults:
            raise ValueError("Infants count cannot exceed adult count")

        # Validate preferred airlines format if provided
        preferred_airlines = getattr(request, "preferred_airlines", None)
        if preferred_airlines:
            for airline in preferred_airlines:
                if not airline or len(airline) < 2 or len(airline) > 3:
                    raise ValueError(f"Invalid airline code format: {airline}")

    async def _convert_api_models_to_flight_search_params(
        self, request: FlightSearchRequest
    ) -> FlightSearchParams:
        """Convert API models to internal flight search params."""
        return FlightSearchParams(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date.isoformat()
            if hasattr(request.departure_date, "isoformat")
            else str(request.departure_date),
            return_date=request.return_date.isoformat()
            if request.return_date and hasattr(request.return_date, "isoformat")
            else str(request.return_date)
            if request.return_date
            else None,
            adults=getattr(request, "adults", 1),
            children=getattr(request, "children", 0),
            infants=getattr(request, "infants", 0),
            cabin_class=request.cabin_class,
            max_stops=getattr(request, "max_stops", None),
            max_price=getattr(request, "max_price", None),
            preferred_airlines=getattr(request, "preferred_airlines", None),
        )

    async def _convert_duffel_response_to_api_models(
        self, duffel_response, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Convert Duffel response to API models."""
        flight_offers = []

        for offer in duffel_response.offers:
            # Extract basic flight information from Duffel offer
            segments = []
            if offer.get("slices"):
                for slice_data in offer["slices"]:
                    for segment in slice_data.get("segments", []):
                        segments.append(
                            {
                                "departure_airport": segment.get("origin", {}).get(
                                    "iata_code", ""
                                ),
                                "arrival_airport": segment.get("destination", {}).get(
                                    "iata_code", ""
                                ),
                                "departure_time": segment.get("departing_at", ""),
                                "arrival_time": segment.get("arriving_at", ""),
                                "flight_number": segment.get(
                                    "marketing_carrier_flight_number", ""
                                ),
                                "duration_minutes": 180,  # Default fallback
                            }
                        )

            flight_offer = FlightOffer(
                id=offer["id"],
                origin=request.origin,
                destination=request.destination,
                departure_date=request.departure_date,
                return_date=request.return_date,
                airline=segments[0].get("flight_number", "").split()[0]
                if segments
                else "Unknown",
                airline_name="Unknown Airline",  # Would need airline lookup
                price=offer["total_amount"],
                currency=offer["total_currency"],
                cabin_class=request.cabin_class,
                stops=max(0, len(segments) - 1) if segments else 0,
                duration_minutes=sum(
                    seg.get("duration_minutes", 180) for seg in segments
                ),
                segments=segments,
                booking_link="https://duffel.com/book",  # Placeholder
            )
            flight_offers.append(flight_offer)

        return FlightSearchResponse(
            results=flight_offers,
            count=len(flight_offers),
            currency=flight_offers[0].currency if flight_offers else "USD",
            search_id=duffel_response.search_id or str(uuid.uuid4()),
            trip_id=request.trip_id,
            min_price=min(offer.price for offer in flight_offers)
            if flight_offers
            else None,
            max_price=max(offer.price for offer in flight_offers)
            if flight_offers
            else None,
            search_request=request,
        )

    @with_error_handling
    async def search_flights(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for flights based on the provided criteria.

        Args:
            request: Flight search request parameters

        Returns:
            Flight search results
        """
        logger.info(
            f"Searching for flights from {request.origin} to {request.destination} "
            f"on {request.departure_date} using {feature_flags.flights_integration.value} integration"
        )

        # Validate request parameters
        try:
            self._validate_flight_search_request(request)
        except ValueError as e:
            logger.error(f"Flight search request validation failed: {str(e)}")
            # Return empty response for invalid requests (validation error logged)
            return FlightSearchResponse(
                results=[],
                count=0,
                currency="USD",
                search_id=str(uuid.uuid4()),
                trip_id=request.trip_id,
                min_price=None,
                max_price=None,
                search_request=request,
            )

        if feature_flags.flights_integration == IntegrationMode.DIRECT:
            # Use direct HTTP client
            if self.duffel_client is None:
                try:
                    self.duffel_client = DuffelHTTPClient()
                except Exception as e:
                    logger.error(f"Failed to initialize DuffelHTTPClient: {str(e)}")
                    return await self._get_mock_flight_response(request)

            try:
                # Convert to internal format
                search_params = await self._convert_api_models_to_flight_search_params(
                    request
                )

                # Make direct API call
                duffel_response = await self.duffel_client.search_flights(search_params)

                # Convert back to API format
                return await self._convert_duffel_response_to_api_models(
                    duffel_response, request
                )

            except Exception as e:
                logger.error(f"Direct API flight search failed: {str(e)}")
                # Fall back to mock data
                return await self._get_mock_flight_response(request)

        else:
            # Use MCP integration (fallback)
            try:
                search_params = await self._convert_api_models_to_flight_search_params(
                    request
                )

                result = await mcp_manager.invoke(
                    mcp_name="duffel_flights",
                    method_name="search_flights",
                    params=search_params.model_dump(by_alias=True),
                )

                # Convert MCP result to API format
                return await self._convert_duffel_response_to_api_models(
                    result, request
                )

            except Exception as e:
                logger.error(f"MCP flight search failed: {str(e)}")
                # Fall back to mock data
                return await self._get_mock_flight_response(request)

    async def _get_mock_flight_response(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Generate mock flight response for fallback scenarios."""
        logger.warning("Using mock flight data as fallback")

        search_id = str(uuid.uuid4())

        # Create a mock flight offer
        offer = FlightOffer(
            id=f"offer-{uuid.uuid4()}",
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            return_date=request.return_date,
            airline="AA",
            airline_name="American Airlines",
            price=499.99,
            currency="USD",
            cabin_class=request.cabin_class,
            stops=0,
            duration_minutes=180,
            segments=[
                {
                    "departure_airport": request.origin,
                    "arrival_airport": request.destination,
                    "departure_time": f"{request.departure_date}T08:00:00",
                    "arrival_time": f"{request.departure_date}T11:00:00",
                    "flight_number": "AA123",
                    "duration_minutes": 180,
                }
            ],
            booking_link="https://example.com/book/12345",
        )

        return FlightSearchResponse(
            results=[offer],
            count=1,
            currency="USD",
            search_id=search_id,
            trip_id=request.trip_id,
            min_price=499.99,
            max_price=499.99,
            search_request=request,
        )

    async def search_multi_city_flights(
        self, request: MultiCityFlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for multi-city flights based on the provided criteria.

        Args:
            request: Multi-city flight search request parameters

        Returns:
            Flight search results
        """
        logger.info(
            f"Searching for multi-city flights with {len(request.segments)} segments"
        )

        # Placeholder implementation
        search_id = str(uuid.uuid4())

        # Create a mock flight offer with multiple segments
        segments = []
        for i, segment in enumerate(request.segments):
            segments.append(
                {
                    "departure_airport": segment.origin,
                    "arrival_airport": segment.destination,
                    "departure_time": f"{segment.departure_date}T08:00:00",
                    "arrival_time": f"{segment.departure_date}T11:00:00",
                    "flight_number": f"AA{1000 + i}",
                    "duration_minutes": 180,
                }
            )

        offer = FlightOffer(
            id=f"offer-{uuid.uuid4()}",
            origin=request.segments[0].origin,
            destination=request.segments[-1].destination,
            departure_date=request.segments[0].departure_date,
            return_date=None,
            airline="AA",
            airline_name="American Airlines",
            price=899.99,
            currency="USD",
            cabin_class=request.cabin_class,
            stops=len(request.segments) - 1,
            duration_minutes=180 * len(request.segments),
            segments=segments,
            booking_link="https://example.com/book/12345",
        )

        return FlightSearchResponse(
            results=[offer],
            count=1,
            currency="USD",
            search_id=search_id,
            trip_id=request.trip_id,
            min_price=899.99,
            max_price=899.99,
            search_request=request,
        )

    async def search_airports(
        self, request: AirportSearchRequest
    ) -> AirportSearchResponse:
        """Search for airports based on the provided query.

        Args:
            request: Airport search request parameters

        Returns:
            Airport search results
        """
        logger.info(f"Searching for airports with query: '{request.query}'")

        # Placeholder implementation with mock data
        results = []

        # If the query looks like an IATA code, add a specific result
        if len(request.query) == 3 and request.query.isalpha():
            code = request.query.upper()
            airport = Airport(
                code=code,
                name=f"{code} International Airport",
                city="Sample City",
                country="United States",
                country_code="US",
                latitude=37.7749,
                longitude=-122.4194,
            )
            results.append(airport)
        else:
            # Add some sample airports
            sample_airports = [
                Airport(
                    code="JFK",
                    name="John F. Kennedy International Airport",
                    city="New York",
                    country="United States",
                    country_code="US",
                    latitude=40.6413,
                    longitude=-73.7781,
                ),
                Airport(
                    code="LAX",
                    name="Los Angeles International Airport",
                    city="Los Angeles",
                    country="United States",
                    country_code="US",
                    latitude=33.9416,
                    longitude=-118.4085,
                ),
                Airport(
                    code="SFO",
                    name="San Francisco International Airport",
                    city="San Francisco",
                    country="United States",
                    country_code="US",
                    latitude=37.6213,
                    longitude=-122.3790,
                ),
            ]

            # Filter based on query
            query_lower = request.query.lower()
            results = [
                airport
                for airport in sample_airports
                if (
                    query_lower in airport.name.lower()
                    or query_lower in airport.city.lower()
                    or query_lower in airport.code.lower()
                )
            ][: request.limit]

        return AirportSearchResponse(
            results=results,
            count=len(results),
        )

    async def get_flight_offer(self, offer_id: str) -> Optional[FlightOffer]:
        """Get details of a specific flight offer.

        Args:
            offer_id: Flight offer ID

        Returns:
            Flight offer details if found, None otherwise
        """
        logger.info(f"Getting flight offer with ID: {offer_id}")

        # Placeholder implementation
        if not offer_id.startswith("offer-"):
            return None

        # Create a mock flight offer
        return FlightOffer(
            id=offer_id,
            origin="JFK",
            destination="LAX",
            departure_date=date.today(),
            return_date=None,
            airline="AA",
            airline_name="American Airlines",
            price=499.99,
            currency="USD",
            cabin_class=CabinClass.ECONOMY,
            stops=0,
            duration_minutes=360,
            segments=[
                {
                    "departure_airport": "JFK",
                    "arrival_airport": "LAX",
                    "departure_time": f"{date.today()}T08:00:00",
                    "arrival_time": f"{date.today()}T14:00:00",
                    "flight_number": "AA123",
                    "duration_minutes": 360,
                }
            ],
            booking_link="https://example.com/book/12345",
        )

    async def save_flight(
        self, user_id: str, request: SavedFlightRequest
    ) -> Optional[SavedFlightResponse]:
        """Save a flight offer for a trip.

        Args:
            user_id: User ID
            request: Save flight request

        Returns:
            Saved flight response if successful, None otherwise
        """
        logger.info(
            f"Saving flight offer {request.offer_id} for user {user_id} "
            f"and trip {request.trip_id}"
        )

        # Get the flight offer
        offer = await self.get_flight_offer(request.offer_id)
        if not offer:
            logger.warning(f"Flight offer {request.offer_id} not found")
            return None

        # Placeholder implementation - in a real app, we would save to a database
        saved_id = uuid.uuid4()

        return SavedFlightResponse(
            id=saved_id,
            user_id=user_id,
            trip_id=request.trip_id,
            offer=offer,
            saved_at=datetime.now(),
            notes=request.notes,
        )

    async def delete_saved_flight(self, user_id: str, saved_flight_id: UUID) -> bool:
        """Delete a saved flight.

        Args:
            user_id: User ID
            saved_flight_id: Saved flight ID

        Returns:
            True if deleted, False otherwise
        """
        logger.info(f"Deleting saved flight {saved_flight_id} for user {user_id}")

        # Placeholder implementation
        return True

    async def list_saved_flights(
        self, user_id: str, trip_id: Optional[UUID] = None
    ) -> List[SavedFlightResponse]:
        """List saved flights for a user, optionally filtered by trip.

        Args:
            user_id: User ID
            trip_id: Optional trip ID to filter by

        Returns:
            List of saved flights
        """
        logger.info(
            f"Listing saved flights for user {user_id}"
            + (f" and trip {trip_id}" if trip_id else "")
        )

        # Placeholder implementation - returns empty list
        return []

    async def health_check(self) -> bool:
        """Check if the flight service is operational.

        Returns:
            True if service is operational, False otherwise
        """
        if feature_flags.flights_integration == IntegrationMode.DIRECT:
            if self.duffel_client is None:
                try:
                    self.duffel_client = DuffelHTTPClient()
                except Exception:
                    return False
            return await self.duffel_client.health_check()
        else:
            # For MCP, we could check MCP manager availability
            try:
                # Basic health check - try to access MCP manager
                return mcp_manager is not None
            except Exception:
                return False

    async def close(self) -> None:
        """Close any open connections."""
        if self.duffel_client:
            await self.duffel_client.close()
            logger.debug("FlightService connections closed")
