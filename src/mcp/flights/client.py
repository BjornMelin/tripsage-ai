"""
Flight MCP Client implementation for TripSage.

This module provides a client for interacting with the external
Flight MCP Server (ravinahp/flights-mcp), which offers flight search,
comparison, and price tracking tools using the Duffel API.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

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
P = TypeVar("P", bound=BaseModel)
R = TypeVar("R")


class FlightsMCPClient(FastMCPClient, Generic[P, R]):
    """Client for the external ravinahp/flights-mcp Server.

    This client interfaces with the ravinahp/flights-mcp server which provides
    flight search capabilities through the Duffel API. The server is read-only
    and does not support booking operations.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True,
        cache_ttl: int = 1800,
        server_name: str = "Flights",
    ):
        """Initialize the Flights MCP Client.

        Args:
            endpoint: MCP server endpoint URL
            api_key: Duffel API key for authentication (if required)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds
            server_name: Server name for logging and caching
        """
        super().__init__(
            server_name=server_name,
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )

    async def _call_validate_tool(
        self,
        tool_name: str,
        params_model: Type[P],
        response_model: type[R],
        raw_params: Dict[str, Any],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Validate parameters, call a tool, and validate the response.

        Args:
            tool_name: Name of the tool to call
            params_model: Pydantic model type for validating parameters
            response_model: Response model to validate the response
            raw_params: Dictionary of raw parameters for the tool
            skip_cache: Whether to skip the cache
            cache_key: Custom cache key
            cache_ttl: Custom cache TTL in seconds

        Returns:
            Validated response

        Raises:
            MCPError: If parameter validation fails, the request fails,
                      or response validation fails.
        """
        validated_params: P
        try:
            # 1. Validate parameters first
            validated_params = params_model.model_validate(raw_params)
            params_dict = validated_params.model_dump(exclude_none=True)

        except ValidationError as e:
            logger.error(f"Parameter validation failed for {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=raw_params,
            ) from e

        try:
            # 2. Call the tool using validated params dictionary
            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # 3. Validate response
            validated_response = response_model.model_validate(response)
            return validated_response

        except ValidationError as e:
            # Handle response validation errors
            logger.warning(f"Response validation failed for {tool_name}: {str(e)}")
            # Depending on strictness, could raise or return raw/cast response
            # Raising MCPError for consistency:
            raise MCPError(
                message=f"Invalid response format received from {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params_dict,
            ) from e
            # Alternative: return cast(R, response)

        except MCPError:  # Re-raise MCPError from self.call_tool
            raise
        except Exception as e:
            # Handle other errors during the API call
            logger.error(f"Error calling {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Failed to call {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params_dict,
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
        raw_params = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "cabin_class": cabin_class,
            "max_stops": max_stops,
            "max_price": max_price,
            "preferred_airlines": preferred_airlines,
        }

        try:
            # Use the centralized method for validation and call
            response = await self._call_validate_tool(
                tool_name="search_flights",
                params_model=FlightSearchParams,
                response_model=FlightSearchResponse,
                raw_params=raw_params,
                skip_cache=skip_cache,
            )
            return response
        except MCPError as e:
            # Handle specific errors like rate limiting or auth after the call fails
            error_message = str(e.message).lower()
            status_code = e.status_code

            if (
                status_code == 429
                or "rate limit" in error_message
                or "too many requests" in error_message
            ):
                logger.error(f"Rate limit exceeded when searching flights: {str(e)}")
                raise MCPError(
                    message=(
                        "Rate limit exceeded for Duffel API. Please try again later."
                    ),
                    server=self.server_name,
                    tool="search_flights",
                    params=raw_params,
                    status_code=429,
                ) from e
            elif (
                status_code == 401
                or "api key" in error_message
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
                    params=raw_params,
                    status_code=401,
                ) from e
            else:
                # Re-raise other MCP errors from _call_validate_tool
                raise e
        except Exception as e:  # Catch unexpected errors not already MCPError
            logger.error(f"Unexpected error during flight search: {str(e)}")
            raise MCPError(
                message=f"Unexpected error during flight search: {str(e)}",
                server=self.server_name,
                tool="search_flights",
                params=raw_params,
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
        # Convert segments to FlightSegment objects before validation
        try:
            flight_segments = [
                FlightSegment.model_validate(segment) for segment in segments
            ]
        except ValidationError as e:
            # Handle invalid segment structure early
            logger.error(f"Invalid segment structure for multi-city search: {str(e)}")
            raise MCPError(
                message=f"Invalid segment structure: {str(e)}",
                server=self.server_name,
                tool="search_multi_city",
                params={"segments": segments},
            ) from e

        raw_params = {
            "segments": flight_segments,
            "adults": adults,
            "children": children,
            "infants": infants,
            "cabin_class": cabin_class,
        }

        # Use the centralized method
        return await self._call_validate_tool(
            tool_name="search_multi_city",
            params_model=MultiCitySearchParams,
            response_model=FlightSearchResponse,
            raw_params=raw_params,
            skip_cache=skip_cache,
        )

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
        raw_params = {"code": code, "search_term": search_term}

        # Use the centralized method
        return await self._call_validate_tool(
            tool_name="get_airports",
            params_model=AirportSearchParams,
            response_model=AirportSearchResponse,
            raw_params=raw_params,
        )

    async def get_offer_details(self, offer_id: str) -> OfferDetailsResponse:
        """Get detailed information for a specific flight offer.

        Args:
            offer_id: Flight offer ID

        Returns:
            OfferDetailsResponse with flight offer details

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        raw_params = {"offer_id": offer_id}

        # Use the centralized method
        return await self._call_validate_tool(
            tool_name="get_offer_details",
            params_model=OfferDetailsParams,
            response_model=OfferDetailsResponse,
            raw_params=raw_params,
        )

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
        raw_params = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
        }

        # Use the centralized method
        return await self._call_validate_tool(
            tool_name="get_flight_prices",
            params_model=FlightPriceParams,
            response_model=FlightPriceResponse,
            raw_params=raw_params,
            skip_cache=skip_cache,
        )

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
        raw_params = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "email": notification_email,
            "threshold_percentage": price_threshold,
            "frequency": frequency,
        }

        # Use the centralized method
        return await self._call_validate_tool(
            tool_name="track_prices",
            params_model=PriceTrackingParams,
            response_model=PriceTrackingResponse,
            raw_params=raw_params,
        )

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


# Import the factory function for client creation
from .factory import get_client

# For backward compatibility, create a default client instance
flights_client = get_client()
