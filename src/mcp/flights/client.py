"""
Flight MCP Client implementation for TripSage.

This module provides a client for interacting with the Flight MCP Server,
which offers flight search, comparison, booking, and price tracking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ...cache.redis_cache import redis_cache
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..fastmcp import FastMCPClient

logger = get_module_logger(__name__)


class FlightSearchParams(BaseModel):
    """Parameters for flight search queries."""

    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin_class: str = "economy"
    max_stops: Optional[int] = None
    max_price: Optional[float] = None
    preferred_airlines: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()

    @model_validator(mode="after")
    def validate_return_date_after_departure(self) -> "FlightSearchParams":
        """Validate that return date is after departure date if provided."""
        if (
            self.return_date
            and self.departure_date
            and self.return_date < self.departure_date
        ):
            raise ValueError("Return date must be after departure date")
        return self


class FlightsMCPClient(FastMCPClient):
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
    ) -> Dict[str, Any]:
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
            Dictionary with flight search results

        Raises:
            MCPError: If the MCP request fails
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

            # Convert to API parameters
            api_params = params.model_dump(exclude_none=True)

            return await self.call_tool(
                "search_flights", api_params, skip_cache=skip_cache
            )
        except Exception as e:
            # Check for rate limiting or API key issues
            error_message = str(e).lower()
            if "rate limit" in error_message or "too many requests" in error_message:
                logger.error(
                    f"Rate limit exceeded when searching flights: {str(e)}"
                )
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
    ) -> Dict[str, Any]:
        """Search for multi-city flight itineraries.

        Args:
            segments: List of flight segments, each with origin, destination, and date
            adults: Number of adult passengers
            children: Number of child passengers
            infants: Number of infant passengers
            cabin_class: Cabin class (economy, premium_economy, business, first)
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with multi-city flight search results

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            # Validate segments
            if not segments or len(segments) < 2:
                raise ValueError(
                    "At least two segments are required for multi-city search"
                )

            for segment in segments:
                if (
                    "origin" not in segment
                    or "destination" not in segment
                    or "departure_date" not in segment
                ):
                    raise ValueError(
                        "Each segment must include origin, destination, "
                        "and departure_date"
                    )

            # Create params
            params = {
                "segments": segments,
                "adults": adults,
                "children": children,
                "infants": infants,
                "cabin_class": cabin_class,
            }

            return await self.call_tool(
                "search_multi_city", params, skip_cache=skip_cache
            )
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
    ) -> Dict[str, Any]:
        """Get airport information by IATA code or search term.

        Args:
            code: IATA airport code
            search_term: Airport name or city to search for

        Returns:
            Dictionary with airport information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            if not code and not search_term:
                raise ValueError("Either code or search_term must be provided")

            params = {}
            if code:
                params["code"] = code.upper()
            if search_term:
                params["search_term"] = search_term

            return await self.call_tool("get_airports", params)
        except Exception as e:
            logger.error(f"Error getting airport information: {str(e)}")
            raise MCPError(
                message=f"Failed to get airport information: {str(e)}",
                server=self.server_name,
                tool="get_airports",
                params={"code": code, "search_term": search_term},
            ) from e

    async def get_offer_details(self, offer_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific flight offer.

        Args:
            offer_id: Flight offer ID

        Returns:
            Dictionary with flight offer details

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            return await self.call_tool("get_offer_details", {"offer_id": offer_id})
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
    ) -> Dict[str, Any]:
        """Get current and historical prices for a flight route.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with price history information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            params = {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
            }

            if return_date:
                params["return_date"] = return_date

            return await self.call_tool(
                "get_flight_prices", params, skip_cache=skip_cache
            )
        except Exception as e:
            logger.error(f"Error getting flight prices: {str(e)}")
            raise MCPError(
                message=f"Failed to get flight prices: {str(e)}",
                server=self.server_name,
                tool="get_flight_prices",
                params=params,
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
    ) -> Dict[str, Any]:
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
            Dictionary with tracking confirmation

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            params = {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
                "email": notification_email,
                "frequency": frequency,
            }

            if return_date:
                params["return_date"] = return_date

            if price_threshold:
                params["threshold_percentage"] = price_threshold

            return await self.call_tool("track_prices", params)
        except Exception as e:
            logger.error(f"Error tracking flight prices: {str(e)}")
            raise MCPError(
                message=f"Failed to track flight prices: {str(e)}",
                server=self.server_name,
                tool="track_prices",
                params=params,
            ) from e

    async def create_order(
        self,
        offer_id: str,
        passengers: List[Dict[str, Any]],
        payment_details: Dict[str, Any],
        contact_details: Dict[str, Any],
    ) -> Dict[str, Any]:
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
            Dictionary with error message (operation not supported)

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

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get details of an existing flight booking order.

        Note: This operation is not supported by the ravinahp/flights-mcp server,
        which is read-only and cannot access booking information. This method is
        implemented for API compatibility but will return an error.

        Args:
            order_id: Order ID to retrieve

        Returns:
            Dictionary with error message (operation not supported)

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
                if airports.get("airports") and len(airports["airports"]) > 0:
                    origin_code = airports["airports"][0]["iata_code"]
                else:
                    raise ValueError(f"Could not find airport for {origin}")

            if len(destination) != 3:
                # Search for destination airport
                airports = await self.client.get_airports(search_term=destination)
                if airports.get("airports") and len(airports["airports"]) > 0:
                    destination_code = airports["airports"][0]["iata_code"]
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
            if "offers" in results and results["offers"]:
                for offer in results["offers"]:
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
                results["offers"].sort(
                    key=lambda x: x.get("_value_score", float("inf"))
                )

                # Remove internal score
                for offer in results["offers"]:
                    if "_value_score" in offer:
                        del offer["_value_score"]

            return {
                "origin": {"code": origin_code, "input": origin},
                "destination": {"code": destination_code, "input": destination},
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "max_price": max_price,
                "results": results,
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
            if "offers" in current_prices and current_prices["offers"]:
                prices = [
                    o.get("total_amount", float("inf"))
                    for o in current_prices["offers"]
                ]
                lowest_price = min(prices) if prices else None

            # Calculate insights from history
            if "prices" in price_history and price_history["prices"]:
                prices = price_history["prices"]
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
                    "price_history": price_history,
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
