"""
Flight MCP Client implementation for TripSage.

This module provides a client for interacting with the Flight MCP Server,
which offers flight search, comparison, booking, and price tracking.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, cast

from pydantic import ValidationError

from ...cache.redis_cache import redis_cache
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..fastmcp import FastMCPClient
from .models import (
    AirportSearchParams,
    AirportSearchResponse,
    BookingResponse,
    FlightPriceParams,
    FlightPriceResponse,
    FlightSearchParams,
    FlightSearchResponse,
    FlightSegment,
    MultiCitySearchParams,
    OfferDetailsParams,
    OfferDetailsResponse,
    OrderDetailsResponse,
    PriceTrackingParams,
    PriceTrackingResponse,
)

logger = get_module_logger(__name__)

# Define generic types for parameter and response models
P = TypeVar("P")
R = TypeVar("R")


class FlightsMCPClient(FastMCPClient, Generic[P, R]):
    """Client for the Flights MCP Server."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True,
    ):
        """Initialize the Flights MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to settings value)
            api_key: API key for authentication (defaults to settings value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        if endpoint is None:
            endpoint = settings.flights_mcp.endpoint

        if api_key is None and settings.flights_mcp.api_key:
            api_key = settings.flights_mcp.api_key.get_secret_value()

        super().__init__(
            server_name="Flights",
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=1800,  # 30 minutes default cache TTL for flight data
        )

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: P,
        response_model: type[R],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Call a tool and validate both parameters and response.

        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool (validated Pydantic model)
            response_model: Response model to validate the response
            skip_cache: Whether to skip the cache
            cache_key: Custom cache key
            cache_ttl: Custom cache TTL in seconds

        Returns:
            Validated response

        Raises:
            MCPError: If the request fails or validation fails
        """
        try:
            # Convert parameters to dict using model_dump() for Pydantic v2
            params_dict = (
                params.model_dump(exclude_none=True)
                if hasattr(params, "model_dump")
                else params
            )

            # Call the tool
            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            try:
                # Validate response
                validated_response = response_model.model_validate(response)
                return validated_response
            except ValidationError as e:
                logger.warning(f"Response validation failed for {tool_name}: {str(e)}")
                # Return the raw response if validation fails
                # This is to ensure backward compatibility
                return cast(R, response)
        except ValidationError as e:
            logger.error(f"Parameter validation failed for {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Failed to call {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e

    @redis_cache.cached("flight_search", 1800)  # 30 minutes cache
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_stops: Optional[int] = None,
        max_price: Optional[float] = None,
        preferred_airlines: Optional[List[str]] = None,
        skip_cache: bool = False,
    ) -> FlightSearchResponse:
        """Search for flights matching the specified criteria.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class (economy, premium_economy, business, first)
            max_stops: Maximum number of stops
            max_price: Maximum price in USD
            preferred_airlines: List of preferred airline codes
            skip_cache: Whether to skip the cache

        Returns:
            FlightSearchResponse with flight search results

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Validate parameters
            params = FlightSearchParams(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
                max_stops=max_stops,
                max_price=max_price,
                preferred_airlines=preferred_airlines,
            )

            response = await self._call_validate_tool(
                "search_flights",
                params,
                FlightSearchResponse,
                skip_cache=skip_cache,
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in search_flights: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for flight search: {str(e)}",
                server=self.server_name,
                tool="search_flights",
                params={
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                },
            ) from e
        except Exception as e:
            # Check for rate limiting or API key issues
            error_message = str(e).lower()
            if "rate limit" in error_message or "too many requests" in error_message:
                logger.error(f"Rate limit exceeded when searching flights: {str(e)}")
                raise MCPError(
                    message=(
                        "Rate limit exceeded for Duffel API. Please try again later."
                    ),
                    server=self.server_name,
                    tool="search_flights",
                    params={
                        "origin": origin,
                        "destination": destination,
                        "departure_date": departure_date,
                    },
                    status_code=429,  # Too Many Requests
                ) from e
            elif (
                "api key" in error_message
                or "authentication" in error_message
                or "unauthorized" in error_message
            ):
                logger.error(
                    f"API authentication error when searching flights: {str(e)}"
                )
                raise MCPError(
                    message=(
                        "Duffel API authentication failed. Please check your API key."
                    ),
                    server=self.server_name,
                    tool="search_flights",
                    params={
                        "origin": origin,
                        "destination": destination,
                    },
                    status_code=401,  # Unauthorized
                ) from e
            else:
                # General error
                logger.error(f"Error searching flights: {str(e)}")
                raise MCPError(
                    message=f"Failed to search flights: {str(e)}",
                    server=self.server_name,
                    tool="search_flights",
                    params={
                        "origin": origin,
                        "destination": destination,
                        "departure_date": departure_date,
                        "return_date": return_date,
                    },
                ) from e

    @redis_cache.cached("multi_city_flight_search", 1800)  # 30 minutes cache
    async def search_multi_city(
        self,
        segments: List[Dict[str, Any]],
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        skip_cache: bool = False,
    ) -> FlightSearchResponse:
        """Search for multi-city flight itineraries.

        Args:
            segments: List of flight segments, each with origin, destination, and date
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class (economy, premium_economy, business, first)
            skip_cache: Whether to skip the cache

        Returns:
            FlightSearchResponse with multi-city flight search results

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Convert segments to FlightSegment objects
            flight_segments = []
            for segment in segments:
                flight_segments.append(FlightSegment.model_validate(segment))

            # Validate parameters
            params = MultiCitySearchParams(
                segments=flight_segments,
                adults=adults,
                children=children,
                infants=infants,
                cabin_class=cabin_class,
            )

            response = await self._call_validate_tool(
                "search_multi_city",
                params,
                FlightSearchResponse,
                skip_cache=skip_cache,
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in search_multi_city: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for multi-city search: {str(e)}",
                server=self.server_name,
                tool="search_multi_city",
                params={"segments": segments},
            ) from e
        except Exception as e:
            logger.error(f"Error searching multi-city flights: {str(e)}")
            raise MCPError(
                message=f"Failed to search multi-city flights: {str(e)}",
                server=self.server_name,
                tool="search_multi_city",
                params={"segments": segments},
            ) from e

    async def get_airports(
        self, code: Optional[str] = None, search_term: Optional[str] = None
    ) -> AirportSearchResponse:
        """Get airport information by IATA code or search term.

        Args:
            code: IATA airport code
            search_term: Airport name or city to search for

        Returns:
            AirportSearchResponse with airport information

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Validate parameters
            params = AirportSearchParams(
                code=code,
                search_term=search_term,
            )

            response = await self._call_validate_tool(
                "get_airports",
                params,
                AirportSearchResponse,
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in get_airports: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for airport search: {str(e)}",
                server=self.server_name,
                tool="get_airports",
                params={"code": code, "search_term": search_term},
            ) from e
        except Exception as e:
            logger.error(f"Error getting airport information: {str(e)}")
            raise MCPError(
                message=f"Failed to get airport information: {str(e)}",
                server=self.server_name,
                tool="get_airports",
                params={"code": code, "search_term": search_term},
            ) from e

    async def get_offer_details(self, offer_id: str) -> OfferDetailsResponse:
        """Get detailed information for a specific flight offer.

        Args:
            offer_id: Flight offer ID

        Returns:
            OfferDetailsResponse with flight offer details

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Validate parameters
            params = OfferDetailsParams(
                offer_id=offer_id,
            )

            response = await self._call_validate_tool(
                "get_offer_details",
                params,
                OfferDetailsResponse,
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in get_offer_details: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for offer details: {str(e)}",
                server=self.server_name,
                tool="get_offer_details",
                params={"offer_id": offer_id},
            ) from e
        except Exception as e:
            logger.error(f"Error getting offer details: {str(e)}")
            raise MCPError(
                message=f"Failed to get offer details: {str(e)}",
                server=self.server_name,
                tool="get_offer_details",
                params={"offer_id": offer_id},
            ) from e

    @redis_cache.cached("flight_price_history", 3600)  # 1 hour cache
    async def get_flight_prices(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        skip_cache: bool = False,
    ) -> FlightPriceResponse:
        """Get current and historical prices for a flight route.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)
            skip_cache: Whether to skip the cache

        Returns:
            FlightPriceResponse with price history information

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Validate parameters
            params = FlightPriceParams(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
            )

            response = await self._call_validate_tool(
                "get_flight_prices",
                params,
                FlightPriceResponse,
                skip_cache=skip_cache,
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in get_flight_prices: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for flight prices: {str(e)}",
                server=self.server_name,
                tool="get_flight_prices",
                params={
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error getting flight prices: {str(e)}")
            raise MCPError(
                message=f"Failed to get flight prices: {str(e)}",
                server=self.server_name,
                tool="get_flight_prices",
                params={
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                },
            ) from e

    async def track_prices(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        notification_email: str = None,
        price_threshold: Optional[float] = None,
        frequency: str = "daily",
    ) -> PriceTrackingResponse:
        """Track price changes for a flight route.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)
            notification_email: Email to send notifications to
            price_threshold: Target price threshold for alerts
            frequency: How often to check for price changes (hourly, daily, weekly)

        Returns:
            PriceTrackingResponse with tracking confirmation

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Validate parameters
            params = PriceTrackingParams(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                email=notification_email,
                threshold_percentage=price_threshold,
                frequency=frequency,
            )

            response = await self._call_validate_tool(
                "track_prices",
                params,
                PriceTrackingResponse,
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in track_prices: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for price tracking: {str(e)}",
                server=self.server_name,
                tool="track_prices",
                params={
                    "origin": origin,
                    "destination": destination,
                    "email": notification_email,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error tracking flight prices: {str(e)}")
            raise MCPError(
                message=f"Failed to track flight prices: {str(e)}",
                server=self.server_name,
                tool="track_prices",
                params={
                    "origin": origin,
                    "destination": destination,
                    "email": notification_email,
                },
            ) from e

    async def create_order(
        self,
        offer_id: str,
        passengers: List[Dict[str, Any]],
        payment_details: Dict[str, Any],
        contact_details: Dict[str, Any],
    ) -> BookingResponse:
        """Create a flight booking order.

        Note: This operation is not supported by the ravinahp/flights-mcp server,
        which is read-only and cannot book flights. This method is implemented
        for API compatibility but will return an error.

        Args:
            offer_id: Flight offer ID to book
            passengers: List of passenger information
            payment_details: Payment information
            contact_details: Contact information

        Returns:
            BookingResponse with error message (operation not supported)

        Raises:
            MCPError: Always raised since operation is not supported
        """
        logger.warning("Booking operations are not supported by ravinahp/flights-mcp")

        # Return a standardized error response for unsupported operations
        error_message = (
            "Flight booking operations are not supported by the "
            "ravinahp/flights-mcp server, which is read-only and cannot book flights. "
            "Please use a different flight booking service if you need to "
            "complete a booking."
        )

        raise MCPError(
            message=error_message,
            server=self.server_name,
            tool="create_order",
            params={"offer_id": offer_id},
            status_code=501,  # Not Implemented
        )

    async def get_order(self, order_id: str) -> OrderDetailsResponse:
        """Get details of an existing flight booking order.

        Note: This operation is not supported by the ravinahp/flights-mcp server,
        which is read-only and cannot access booking information. This method is
        implemented for API compatibility but will return an error.

        Args:
            order_id: Order ID to retrieve

        Returns:
            OrderDetailsResponse with error message (operation not supported)

        Raises:
            MCPError: Always raised since operation is not supported
        """
        logger.warning("Order operations are not supported by ravinahp/flights-mcp")

        # Return a standardized error response for unsupported operations
        error_message = (
            "Flight order operations are not supported by the "
            "ravinahp/flights-mcp server, which is read-only and cannot access "
            "booking information. Please use a different flight booking service "
            "if you need to access order details."
        )

        raise MCPError(
            message=error_message,
            server=self.server_name,
            tool="get_order",
            params={"order_id": order_id},
            status_code=501,  # Not Implemented
        )

    def list_tools_sync(self) -> List[Dict[str, str]]:
        """Synchronous version of list_tools for use in initialization.

        Returns:
            List of tool metadata with at least a name field
        """
        return [
            {"name": "search_flights", "description": "Search for available flights"},
            {
                "name": "search_multi_city",
                "description": "Search for multi-city flights",
            },
            {
                "name": "get_airports",
                "description": "Get airport information by code or search term",
            },
            {
                "name": "get_offer_details",
                "description": "Get detailed flight offer information",
            },
            {
                "name": "get_flight_prices",
                "description": "Get current and historical prices for a flight route",
            },
            {
                "name": "track_prices",
                "description": "Track price changes for a flight route",
            },
            # Note: The following operations are included for API compatibility
            # but are not supported by ravinahp/flights-mcp
            {
                "name": "create_order",
                "description": "Create a flight booking order (not supported)",
            },
            {
                "name": "get_order",
                "description": "Get details of an existing order (not supported)",
            },
        ]

    def get_tool_metadata_sync(self, tool_name: str) -> Dict[str, Any]:
        """Synchronous version of get_tool_metadata for use in initialization.

        Args:
            tool_name: Tool name

        Returns:
            Tool metadata with at least a description field
        """
        tool_metadata = {
            "search_flights": {
                "description": "Search for available flights based on criteria",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin airport IATA code",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination airport IATA code",
                        },
                        "departure_date": {
                            "type": "string",
                            "description": "Departure date (YYYY-MM-DD)",
                        },
                        "return_date": {
                            "type": "string",
                            "description": "Return date (YYYY-MM-DD)",
                        },
                        "adults": {
                            "type": "integer",
                            "description": "Number of adult passengers",
                        },
                        "cabin_class": {
                            "type": "string",
                            "description": (
                                "Cabin class (economy, premium_economy, "
                                "business, first)"
                            ),
                        },
                    },
                    "required": ["origin", "destination", "departure_date"],
                },
            },
            "search_multi_city": {
                "description": "Search for multi-city flight itineraries",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "segments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "origin": {"type": "string"},
                                    "destination": {"type": "string"},
                                    "departure_date": {"type": "string"},
                                },
                            },
                        },
                        "adults": {"type": "integer"},
                        "cabin_class": {"type": "string"},
                    },
                    "required": ["segments"],
                },
            },
            "get_airports": {
                "description": "Get airport information by IATA code or search term",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "search_term": {"type": "string"},
                    },
                },
            },
            "get_offer_details": {
                "description": "Get detailed information for a specific flight offer",
                "parameters_schema": {
                    "type": "object",
                    "properties": {"offer_id": {"type": "string"}},
                    "required": ["offer_id"],
                },
            },
            "get_fare_rules": {
                "description": (
                    "Get fare rules for a flight offer (not supported by "
                    "ravinahp/flights-mcp)"
                ),
                "parameters_schema": {
                    "type": "object",
                    "properties": {"offer_id": {"type": "string"}},
                    "required": ["offer_id"],
                },
            },
            "get_flight_prices": {
                "description": "Get current and historical prices for a flight route",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "destination": {"type": "string"},
                        "departure_date": {"type": "string"},
                        "return_date": {"type": "string"},
                    },
                    "required": ["origin", "destination", "departure_date"],
                },
            },
            "track_prices": {
                "description": "Track price changes for a flight route",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "destination": {"type": "string"},
                        "departure_date": {"type": "string"},
                        "return_date": {"type": "string"},
                        "email": {"type": "string"},
                        "threshold_percentage": {"type": "number"},
                        "frequency": {
                            "type": "string",
                            "enum": ["hourly", "daily", "weekly"],
                        },
                    },
                    "required": [
                        "origin",
                        "destination",
                        "departure_date",
                        "email",
                    ],
                },
            },
            "create_order": {
                "description": (
                    "Create a flight booking order (not supported by "
                    "ravinahp/flights-mcp)"
                ),
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "offer_id": {"type": "string"},
                        "passengers": {"type": "array"},
                        "payment_details": {"type": "object"},
                        "contact_details": {"type": "object"},
                    },
                    "required": [
                        "offer_id",
                        "passengers",
                        "payment_details",
                        "contact_details",
                    ],
                },
            },
        }

        return tool_metadata.get(
            tool_name,
            {
                "name": tool_name,
                "description": (
                    f"Call the {tool_name} tool from {self.server_name} MCP."
                ),
                "parameters_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        )


class FlightService:
    """High-level service for flight-related operations in TripSage.

    Note: When using ravinahp/flights-mcp as the backend, this service is limited to
    search-only functionality. Booking operations are not supported as
    ravinahp/flights-mcp is a read-only MCP server.
    """

    def __init__(self, client: Optional[FlightsMCPClient] = None):
        """Initialize the Flight Service.

        Args:
            client: FlightsMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or get_client()
        logger.info("Initialized Flight Service")

        # Log a warning if we're using ravinahp/flights-mcp, which has limitations
        logger.info(
            "Note: ravinahp/flights-mcp is read-only - booking operations "
            "are not supported"
        )

    async def search_best_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Search for best flight options based on price and convenience.

        Args:
            origin: Origin airport IATA code or city name
            destination: Destination airport IATA code or city name
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)
            adults: Number of adult passengers
            max_price: Maximum price in USD

        Returns:
            Dictionary containing best flight options
        """
        try:
            # Convert city names to airport codes if needed
            origin_code = origin
            destination_code = destination

            if len(origin) != 3:
                # Search for origin airport
                airports = await self.client.get_airports(search_term=origin)
                if airports.airports and len(airports.airports) > 0:
                    origin_code = airports.airports[0].iata_code
                else:
                    raise ValueError(f"Could not find airport for {origin}")

            if len(destination) != 3:
                # Search for destination airport
                airports = await self.client.get_airports(search_term=destination)
                if airports.airports and len(airports.airports) > 0:
                    destination_code = airports.airports[0].iata_code
                else:
                    raise ValueError(f"Could not find airport for {destination}")

            # Search for flights
            results = await self.client.search_flights(
                origin=origin_code,
                destination=destination_code,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                max_price=max_price,
            )

            # Sort results by best value (combination of price and duration)
            if results.offers:
                # Convert to dict for easier manipulation
                results_dict = results.model_dump()
                for offer in results_dict["offers"]:
                    # Calculate a value score (lower is better)
                    price = offer.get("total_amount", 0)
                    durations = []
                    for slice in offer.get("slices", []):
                        duration_minutes = 0
                        for segment in slice.get("segments", []):
                            if "duration_minutes" in segment:
                                duration_minutes += segment["duration_minutes"]
                        durations.append(duration_minutes)

                    avg_duration = sum(durations) / len(durations) if durations else 0
                    stops = sum(
                        len(slice.get("segments", [])) - 1
                        for slice in offer.get("slices", [])
                    )

                    # Value score formula: price + (duration * 0.5) + (stops * 100)
                    offer["_value_score"] = price + (avg_duration * 0.5) + (stops * 100)

                # Sort by value score
                results_dict["offers"].sort(
                    key=lambda x: x.get("_value_score", float("inf"))
                )

                # Remove internal score
                for offer in results_dict["offers"]:
                    if "_value_score" in offer:
                        del offer["_value_score"]

                return {
                    "origin": {"code": origin_code, "input": origin},
                    "destination": {"code": destination_code, "input": destination},
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "adults": adults,
                    "max_price": max_price,
                    "results": results_dict,
                }
            else:
                # No offers found
                return {
                    "origin": {"code": origin_code, "input": origin},
                    "destination": {"code": destination_code, "input": destination},
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "adults": adults,
                    "max_price": max_price,
                    "results": results.model_dump(),
                }

        except Exception as e:
            logger.error(f"Error searching best flights: {str(e)}")
            return {
                "error": f"Failed to search for best flights: {str(e)}",
                "origin": origin,
                "destination": destination,
            }

    async def get_price_insights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get pricing insights for a route, including trends and recommendations.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)

        Returns:
            Dictionary with pricing insights and recommendations
        """
        try:
            # Get price history
            price_history = await self.client.get_flight_prices(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
            )

            # Get current prices
            current_prices = await self.client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
            )

            # Extract lowest current price
            lowest_price = None
            if current_prices.offers:
                prices = [o.total_amount for o in current_prices.offers]
                lowest_price = min(prices) if prices else None

            # Calculate insights from history
            if price_history.prices:
                prices = price_history.prices
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)

                # Analyze trends
                trend = "stable"
                if len(prices) > 3:
                    recent_avg = sum(prices[-3:]) / 3
                    earlier_avg = sum(prices[:-3]) / (len(prices) - 3)
                    if recent_avg < earlier_avg * 0.95:
                        trend = "decreasing"
                    elif recent_avg > earlier_avg * 1.05:
                        trend = "increasing"

                # Generate recommendation
                recommendation = "monitor"
                if lowest_price:
                    if lowest_price <= min_price * 1.05:
                        recommendation = "book_now"
                    elif lowest_price <= avg_price * 0.9:
                        recommendation = "good_price"
                    elif trend == "increasing":
                        recommendation = "prices_rising"

                return {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "current_price": lowest_price,
                    "historical": {
                        "average": avg_price,
                        "minimum": min_price,
                        "maximum": max_price,
                    },
                    "analysis": {
                        "trend": trend,
                        "vs_average": (
                            ((lowest_price / avg_price) - 1) * 100
                            if lowest_price
                            else None
                        ),
                        "vs_minimum": (
                            ((lowest_price / min_price) - 1) * 100
                            if lowest_price
                            else None
                        ),
                    },
                    "recommendation": recommendation,
                    "price_history": price_history.model_dump(),
                }
            else:
                return {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "current_price": lowest_price,
                    "message": "Insufficient price history available for insights",
                }

        except Exception as e:
            logger.error(f"Error getting price insights: {str(e)}")
            return {
                "error": f"Failed to get price insights: {str(e)}",
                "origin": origin,
                "destination": destination,
            }


def get_client() -> FlightsMCPClient:
    """Get a Flights MCP Client instance.

    Returns:
        FlightsMCPClient instance
    """
    return FlightsMCPClient()


def get_service() -> FlightService:
    """Get a Flight Service instance.

    Returns:
        FlightService instance
    """
    return FlightService(get_client())
