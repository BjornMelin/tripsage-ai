"""
Travel Agent implementation for TripSage.

This module provides the TravelAgent implementation which integrates various
travel-specific MCP tools and dual storage architecture with OpenAI's WebSearchTool.
"""

import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from agents import function_tool
from src.cache.redis_cache import redis_cache
from src.utils.config import get_config
from src.utils.error_handling import MCPError
from src.utils.logging import get_module_logger
from tripsage.tools.web_tools import CachedWebSearchTool

from .base_agent import TravelAgent as BaseTravelAgent
from .destination_research import TripSageDestinationResearch
from .flight_booking import TripSageFlightBooking
from .flight_search import TripSageFlightSearch

logger = get_module_logger(__name__)
config = get_config()


class LocationParams(BaseModel):
    """Parameters for location-based queries."""

    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None


class FlightSearchParams(BaseModel):
    """Parameters for flight search."""

    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin_class: str = "economy"
    max_price: Optional[float] = None


class AccommodationSearchParams(BaseModel):
    """Parameters for accommodation search."""

    location: str
    check_in_date: str
    check_out_date: str
    adults: int = 1
    children: int = 0
    rooms: int = 1
    property_type: Optional[str] = None
    min_rating: Optional[float] = None
    max_price_per_night: Optional[float] = None
    amenities: Optional[List[str]] = None


class TravelAgent(BaseTravelAgent):
    """Travel planning agent for TripSage."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the travel agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        super().__init__(name=name, model=model, temperature=temperature)

        # Initialize components
        self.flight_search = TripSageFlightSearch()
        self.flight_booking = TripSageFlightBooking()
        self.destination_research = TripSageDestinationResearch()

        # Add WebSearchTool to the agent's tools with travel-specific domain focus
        # This is part of our hybrid search approach where OpenAI's built-in search
        # serves as the primary method for general queries, while specialized MCP tools
        # (Firecrawl, Browser MCP) are used for deeper, more specific travel research
        self.web_search_tool = CachedWebSearchTool()
        self.agent.tools.append(self.web_search_tool)
        logger.info("Added CachedWebSearchTool to TravelAgent")

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools."""
        # Register weather tools
        self._register_tool(self.get_weather)
        self._register_tool(self.get_weather_forecast)
        self._register_tool(self.get_travel_recommendation)

        # Basic flight tools (will be replaced with enhanced ones)
        self._register_tool(self.search_flights)

        # Enhanced flight search tools
        self._register_tool(self.enhanced_flight_search)
        self._register_tool(self.search_multi_city_flights)
        self._register_tool(self.get_flight_price_history)
        self._register_tool(self.get_flexible_dates_search)

        # Flight booking tools
        self._register_tool(self.book_flight)
        self._register_tool(self.get_booking_status)
        self._register_tool(self.cancel_flight_booking)

        # Accommodation tools
        self._register_tool(self.search_accommodations)

        # Time management tools
        self._register_tool(self.convert_timezone)

        # Trip management tools
        self._register_tool(self.create_trip)
        self._register_tool(self.search_activities)

        # Destination research tools
        self._register_tool(self.search_destination_info)
        self._register_tool(self.get_destination_events)
        self._register_tool(self.crawl_travel_blog)

        # Comparison and recommendation tools
        self._register_tool(self.compare_travel_options)

        # Knowledge graph tools
        self._register_tool(self.store_travel_knowledge)
        self._register_tool(self.retrieve_travel_knowledge)

        # Note: WebSearchTool is added separately in __init__
        # since it doesn't use the function_tool decorator pattern

        # Register MCP clients when available
        self._register_mcp_clients()

    def _register_mcp_clients(self) -> None:
        """Register all available MCP clients with the agent."""
        # Weather MCP Client
        try:
            from ..mcp.weather import get_client as get_weather_client

            weather_client = get_weather_client()
            self._register_mcp_client_tools(weather_client, prefix="weather_")
            logger.info("Registered Weather MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Weather MCP client: %s", str(e))

        # Time MCP Client
        try:
            from ..mcp.time import get_client as get_time_client

            time_client = get_time_client()
            self._register_mcp_client_tools(time_client, prefix="time_")
            logger.info("Registered Time MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Time MCP client: %s", str(e))

        # Flights MCP Client
        try:
            from ..mcp.flights import get_client as get_flights_client

            flights_client = get_flights_client()
            self._register_mcp_client_tools(flights_client, prefix="flights_")
            logger.info("Registered Flights MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Flights MCP client: %s", str(e))

        # Google Maps MCP Client
        try:
            from ..mcp.googlemaps import get_client as get_maps_client

            maps_client = get_maps_client()
            self._register_mcp_client_tools(maps_client, prefix="maps_")
            logger.info("Registered Google Maps MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Google Maps MCP client: %s", str(e))

        # Accommodations MCP Client
        try:
            from ..mcp.accommodations import get_client as get_accommodations_client

            accommodations_client = get_accommodations_client()
            self._register_mcp_client_tools(
                accommodations_client, prefix="accommodations_"
            )
            logger.info("Registered Accommodations MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Accommodations MCP client: %s", str(e))

        # Memory MCP Client (for knowledge graph)
        try:
            from ..mcp.memory import get_client as get_memory_client

            memory_client = get_memory_client()
            self._register_mcp_client_tools(memory_client, prefix="memory_")
            logger.info("Registered Memory MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Memory MCP client: %s", str(e))

        # WebCrawl MCP Client
        try:
            from ..mcp.webcrawl import get_client as get_webcrawl_client

            webcrawl_client = get_webcrawl_client()
            self._register_mcp_client_tools(webcrawl_client, prefix="webcrawl_")
            logger.info("Registered WebCrawl MCP client tools")

            # Connect WebCrawl MCP client to destination research component
            self.destination_research.webcrawl_client = webcrawl_client
            logger.info(
                "Connected WebCrawl MCP client to destination research component"
            )
        except Exception as e:
            logger.warning("Failed to register WebCrawl MCP client: %s", str(e))

    @function_tool
    async def get_weather_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast for a location.

        Args:
            params: Parameters with location information and forecast days

        Returns:
            Weather forecast data
        """
        from ..mcp.weather import get_client

        try:
            # Get weather client
            weather_client = get_client()

            # Extract parameters
            location = params.get("location", {})
            days = params.get("days", 5)

            lat = location.get("lat")
            lon = location.get("lon")
            city = location.get("city")
            country = location.get("country")

            # Call weather MCP
            forecast_data = await weather_client.get_forecast(
                lat=lat, lon=lon, city=city, country=country, days=days
            )

            return forecast_data

        except Exception as e:
            logger.error("Error getting weather forecast: %s", str(e))
            if isinstance(e, MCPError):
                return {"error": e.message}
            return {"error": f"Weather forecast service error: {str(e)}"}

    @function_tool
    async def get_travel_recommendation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get travel recommendations based on weather.

        Args:
            params: Parameters with location information, dates, and activities

        Returns:
            Travel recommendations based on weather
        """
        from ..mcp.weather import get_client

        try:
            # Get weather client
            weather_client = get_client()

            # Extract parameters
            location = params.get("location", {})

            lat = location.get("lat")
            lon = location.get("lon")
            city = location.get("city")
            country = location.get("country")

            # Parse dates
            start_date_str = params.get("start_date")
            end_date_str = params.get("end_date")

            start_date = None
            if start_date_str:
                start_date = datetime.date.fromisoformat(start_date_str)

            end_date = None
            if end_date_str:
                end_date = datetime.date.fromisoformat(end_date_str)

            activities = params.get("activities", [])

            # Call weather MCP
            recommendations = await weather_client.get_travel_recommendation(
                lat=lat,
                lon=lon,
                city=city,
                country=country,
                start_date=start_date,
                end_date=end_date,
                activities=activities,
            )

            return recommendations

        except Exception as e:
            logger.error("Error getting travel recommendations: %s", str(e))
            if isinstance(e, MCPError):
                return {"error": e.message}
            return {"error": f"Travel recommendation service error: {str(e)}"}

    @function_tool
    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for available flights.

        Args:
            params: Flight search parameters including origin,
                destination, dates, and preferences

        Returns:
            Flight search results
        """
        try:
            # Validate parameters
            flight_params = FlightSearchParams(**params)

            # This is a placeholder until the Flights MCP is implemented
            mock_flights = [
                {
                    "id": "f1",
                    "airline": "United Airlines",
                    "flight_number": "UA123",
                    "departure_airport": flight_params.origin,
                    "arrival_airport": flight_params.destination,
                    "departure_time": f"{flight_params.departure_date}T08:00:00",
                    "arrival_time": f"{flight_params.departure_date}T11:30:00",
                    "duration_minutes": 210,
                    "stops": 0,
                    "price": 350.00,
                    "seat_class": flight_params.cabin_class,
                    "available_seats": 12,
                },
                {
                    "id": "f2",
                    "airline": "Delta Air Lines",
                    "flight_number": "DL456",
                    "departure_airport": flight_params.origin,
                    "arrival_airport": flight_params.destination,
                    "departure_time": f"{flight_params.departure_date}T10:15:00",
                    "arrival_time": f"{flight_params.departure_date}T14:45:00",
                    "duration_minutes": 270,
                    "stops": 1,
                    "price": 280.00,
                    "seat_class": flight_params.cabin_class,
                    "available_seats": 8,
                },
                {
                    "id": "f3",
                    "airline": "American Airlines",
                    "flight_number": "AA789",
                    "departure_airport": flight_params.origin,
                    "arrival_airport": flight_params.destination,
                    "departure_time": f"{flight_params.departure_date}T14:30:00",
                    "arrival_time": f"{flight_params.departure_date}T17:45:00",
                    "duration_minutes": 195,
                    "stops": 0,
                    "price": 420.00,
                    "seat_class": flight_params.cabin_class,
                    "available_seats": 5,
                },
            ]

            # Filter by max_price if specified
            if flight_params.max_price:
                mock_flights = [
                    f for f in mock_flights if f["price"] <= flight_params.max_price
                ]

            return {
                "flights": mock_flights,
                "search_criteria": params,
                "results_count": len(mock_flights),
                "note": (
                    "This is mock data. Flight search functionality "
                    "will be implemented with a real API."
                ),
            }

        except Exception as e:
            logger.error("Error searching flights: %s", str(e))
            return {"error": f"Flight search error: {str(e)}"}

    @function_tool
    async def search_accommodations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for accommodations.

        Args:
            params: Accommodation search parameters including
                location, dates, and preferences

        Returns:
            Accommodation search results
        """
        try:
            # Validate parameters
            accommodation_params = AccommodationSearchParams(**params)

            # This is a placeholder until the Accommodations MCP is implemented
            mock_accommodations = [
                {
                    "id": "h1",
                    "name": "Grand Hotel",
                    "type": "hotel",
                    "location": accommodation_params.location,
                    "address": "123 Main St",
                    "coordinates": {"lat": 40.7128, "lng": -74.0060},
                    "rating": 4.5,
                    "price_per_night": 200.00,
                    "amenities": ["wifi", "pool", "breakfast", "gym"],
                    "available_rooms": 3,
                    "images": ["https://example.com/hotel1.jpg"],
                },
                {
                    "id": "h2",
                    "name": "Budget Inn",
                    "type": "hotel",
                    "location": accommodation_params.location,
                    "address": "456 Elm St",
                    "coordinates": {"lat": 40.7200, "lng": -74.0100},
                    "rating": 3.5,
                    "price_per_night": 120.00,
                    "amenities": ["wifi", "breakfast"],
                    "available_rooms": 8,
                    "images": ["https://example.com/hotel2.jpg"],
                },
                {
                    "id": "h3",
                    "name": "Luxury Suites",
                    "type": "apartment",
                    "location": accommodation_params.location,
                    "address": "789 Oak St",
                    "coordinates": {"lat": 40.7150, "lng": -74.0080},
                    "rating": 4.8,
                    "price_per_night": 350.00,
                    "amenities": ["wifi", "pool", "gym", "kitchen", "parking"],
                    "available_rooms": 2,
                    "images": ["https://example.com/hotel3.jpg"],
                },
            ]

            # Filter by property_type if provided
            if accommodation_params.property_type:
                mock_accommodations = [
                    a
                    for a in mock_accommodations
                    if a["type"] == accommodation_params.property_type
                ]

            # Filter by min_rating if provided
            if accommodation_params.min_rating:
                mock_accommodations = [
                    a
                    for a in mock_accommodations
                    if a["rating"] >= accommodation_params.min_rating
                ]

            # Filter by max_price_per_night if provided
            if accommodation_params.max_price_per_night:
                mock_accommodations = [
                    a
                    for a in mock_accommodations
                    if a["price_per_night"] <= accommodation_params.max_price_per_night
                ]

            # Filter by amenities if provided
            if accommodation_params.amenities:
                mock_accommodations = [
                    a
                    for a in mock_accommodations
                    if all(
                        amenity in a["amenities"]
                        for amenity in accommodation_params.amenities
                    )
                ]

            return {
                "accommodations": mock_accommodations,
                "search_criteria": params,
                "results_count": len(mock_accommodations),
                "note": (
                    "This is mock data. Accommodation search functionality "
                    "will be implemented with a real API."
                ),
            }

        except Exception as e:
            logger.error("Error searching accommodations: %s", str(e))
            return {"error": f"Accommodation search error: {str(e)}"}

    @function_tool
    async def enhanced_flight_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced search for flights with advanced filtering and recommendations.

        Uses the TripSageFlightSearch component to provide comprehensive search
        results with intelligent filtering, price analysis, and personalized
        recommendations based on user preferences.

        Args:
            params: Enhanced flight search parameters including:
                origin: Origin airport or city code
                destination: Destination airport or city code
                departure_date: Departure date (YYYY-MM-DD)
                return_date: Return date for round trips (YYYY-MM-DD)
                adults: Number of adult passengers
                children: Number of child passengers
                infants: Number of infant passengers
                cabin_class: Desired cabin class
                    (economy, premium_economy, business, first)
                max_price: Maximum price willing to pay
                preferred_airlines: List of preferred airline codes
                max_stops: Maximum number of stops (0 for non-stop only)
                sort_by: How to sort results (price, duration, best)
                flexible_dates: Whether to include nearby dates in search

        Returns:
            Dictionary with enhanced flight search results
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.search_flights(params)
        except Exception as e:
            logger.error("Error in enhanced flight search: %s", str(e))
            return {"error": f"Enhanced flight search error: {str(e)}"}

    @function_tool
    async def search_multi_city_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for multi-city flight itineraries.

        Allows searching for complex itineraries with multiple segments between
        different city pairs on different dates.

        Args:
            params: Multi-city flight search parameters including:
                segments: List of flight segments, each containing:
                    origin: Origin airport or city code
                    destination: Destination airport or city code
                    date: Departure date (YYYY-MM-DD)
                adults: Number of adult passengers
                children: Number of child passengers
                infants: Number of infant passengers
                cabin_class: Desired cabin class
                max_price: Maximum total price for all segments

        Returns:
            Dictionary with multi-city flight search results
        """
        try:
            # Validate that segments are provided
            segments = params.get("segments", [])
            if not segments or not isinstance(segments, list) or len(segments) < 2:
                return {
                    "error": (
                        "At least two valid segments are required for multi-city search"
                    )
                }

            # Delegate to flight search component
            return await self.flight_search.search_multi_city(params)
        except Exception as e:
            logger.error("Error in multi-city flight search: %s", str(e))
            return {"error": f"Multi-city flight search error: {str(e)}"}

    @function_tool
    async def get_flight_price_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get price history for a specific flight route.

        Retrieves historical pricing data for a given route to help users
        determine if current prices are favorable and whether to book now or wait.

        Args:
            params: Flight route parameters:
                origin: Origin airport or city code
                destination: Destination airport or city code
                cabin_class: Optional cabin class to filter by
                days_back: How many days of history to include (default: 90)

        Returns:
            Dictionary with price history data and trend analysis
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.get_price_history(params)
        except Exception as e:
            logger.error("Error getting flight price history: %s", str(e))
            return {"error": f"Price history error: {str(e)}"}

    @function_tool
    async def get_flexible_dates_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights with flexible dates to find the best prices.

        Searches for flights across a range of dates to help users find the
        optimal travel dates with the best prices.

        Args:
            params: Flexible date search parameters:
                origin: Origin airport or city code
                destination: Destination airport or city code
                date_range_start: Start of date range (YYYY-MM-DD)
                date_range_end: End of date range (YYYY-MM-DD)
                trip_length: Desired trip length in days for round trips
                cabin_class: Desired cabin class
                adults: Number of adult passengers

        Returns:
            Dictionary with flexible date search results
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.search_flexible_dates(params)
        except Exception as e:
            logger.error("Error in flexible date flight search: %s", str(e))
            return {"error": f"Flexible date search error: {str(e)}"}

    @function_tool
    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Book a flight based on selected search results.

        Creates a flight booking based on the selected flight offer from search results
        and passenger information. Stores booking details in dual storage architecture.

        Args:
            params: Flight booking parameters:
                flight_id: ID of selected flight from search results
                passengers: List of passenger information including:
                    first_name: Passenger's first name
                    last_name: Passenger's last name
                    dob: Date of birth (YYYY-MM-DD)
                    email: Contact email
                    phone: Contact phone number
                payment: Payment information object
                trip_id: Optional ID of associated trip

        Returns:
            Dictionary with booking confirmation details
        """
        try:
            # Delegate to flight booking component
            return await self.flight_booking.book_flight(params)
        except Exception as e:
            logger.error("Error booking flight: %s", str(e))
            return {"error": f"Flight booking error: {str(e)}"}

    @function_tool
    async def get_booking_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get the current status of a flight booking.

        Retrieves the latest status of a flight booking, including any updates
        to flight times, gate information, or booking status.

        Args:
            params: Booking status request parameters:
                booking_id: ID of the booking to check
                email: Email associated with the booking

        Returns:
            Dictionary with current booking status information
        """
        try:
            # Delegate to flight booking component
            return await self.flight_booking.get_booking_status(params)
        except Exception as e:
            logger.error("Error getting booking status: %s", str(e))
            return {"error": f"Booking status error: {str(e)}"}

    @function_tool
    async def cancel_flight_booking(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an existing flight booking.

        Attempts to cancel a flight booking and provides refund information
        according to the airline's cancellation policy.

        Args:
            params: Cancellation request parameters:
                booking_id: ID of the booking to cancel
                email: Email associated with the booking
                reason: Optional reason for cancellation

        Returns:
            Dictionary with cancellation confirmation and refund information
        """
        try:
            # Delegate to flight booking component
            return await self.flight_booking.cancel_booking(params)
        except Exception as e:
            logger.error("Error cancelling flight booking: %s", str(e))
            return {"error": f"Cancellation error: {str(e)}"}

    @function_tool
    async def convert_timezone(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert time between timezones.

        Args:
            params: Timezone conversion parameters

        Returns:
            Converted time information
        """
        # This is a placeholder until the Time MCP is implemented
        source_timezone = params.get("source_timezone", "UTC")
        target_timezone = params.get("target_timezone", "UTC")
        time_str = params.get("time", "00:00")

        return {
            "source": {"timezone": source_timezone, "time": time_str},
            "target": {
                "timezone": target_timezone,
                # This would be converted with the actual implementation
                "time": time_str,
            },
            "status": "not_implemented",
            "note": (
                "Timezone conversion functionality will be "
                "implemented with the Time MCP."
            ),
        }

    @function_tool
    async def get_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current weather for a location.

        Args:
            params: Parameters with location information (city, lat/lon, country)

        Returns:
            Current weather data
        """
        from ..mcp.weather import get_client

        try:
            # Get weather client
            weather_client = get_client()

            # Extract parameters
            location = params.get("location", {})

            lat = location.get("lat")
            lon = location.get("lon")
            city = location.get("city")
            country = location.get("country")

            # Call weather MCP
            weather_data = await weather_client.get_current_weather(
                lat=lat, lon=lon, city=city, country=country
            )

            return weather_data

        except Exception as e:
            logger.error("Error getting current weather: %s", str(e))
            if isinstance(e, MCPError):
                return {"error": e.message}
            return {"error": f"Weather service error: {str(e)}"}

    @function_tool
    async def create_trip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip in the system.

        Args:
            params: Trip parameters including user_id, title,
                destination, dates, and budget

        Returns:
            Created trip information
        """
        try:
            from src.utils.dual_storage import trip_service

            # Make sure we have a user_id
            user_id = params.get("user_id")
            if not user_id:
                return {"success": False, "error": "User ID is required"}

            # Create trip using the TripStorageService
            result = await trip_service.create(params)

            # Return a simplified response
            return {
                "success": True,
                "trip_id": result["trip_id"],
                "message": "Trip created successfully",
                "entities_created": result["entities_created"],
                "relations_created": result["relations_created"],
                "trip_details": {
                    "user_id": params.get("user_id"),
                    "title": params.get("title"),
                    "description": params.get("description", ""),
                    "destination": params.get("destination"),
                    "start_date": params.get("start_date"),
                    "end_date": params.get("end_date"),
                    "budget": params.get("budget"),
                },
            }
        except Exception as e:
            logger.error("Error creating trip: %s", str(e))
            return {"success": False, "error": f"Trip creation error: {str(e)}"}

    @function_tool
    async def search_activities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for activities and attractions at a destination.

        Args:
            params: Activity search parameters including
                location, category, and preferences

        Returns:
            Activity search results
        """
        try:
            location = params.get("location", "")
            category = params.get("category", "any")
            max_price = params.get("max_price")
            duration = params.get("duration")

            # This is a placeholder until the Activities MCP is implemented
            mock_activities = [
                {
                    "id": "a1",
                    "name": "City Tour",
                    "category": "sightseeing",
                    "location": location,
                    "price_per_person": 45.00,
                    "duration": "3 hours",
                    "rating": 4.6,
                    "description": (
                        "Explore the city's main attractions with a knowledgeable "
                        "guide."
                    ),
                    "available_slots": 10,
                    "images": ["https://example.com/activity1.jpg"],
                },
                {
                    "id": "a2",
                    "name": "Museum Visit",
                    "category": "cultural",
                    "location": location,
                    "price_per_person": 25.00,
                    "duration": "2 hours",
                    "rating": 4.3,
                    "description": ("Visit the city's renowned art museum."),
                    "available_slots": 20,
                    "images": ["https://example.com/activity2.jpg"],
                },
                {
                    "id": "a3",
                    "name": "Food Tour",
                    "category": "food",
                    "location": location,
                    "price_per_person": 65.00,
                    "duration": "4 hours",
                    "rating": 4.8,
                    "description": (
                        "Sample local cuisine at various restaurants and food markets."
                    ),
                    "available_slots": 8,
                    "images": ["https://example.com/activity3.jpg"],
                },
                {
                    "id": "a4",
                    "name": "Hiking Adventure",
                    "category": "outdoor",
                    "location": location,
                    "price_per_person": 35.00,
                    "duration": "half-day",
                    "rating": 4.2,
                    "description": (
                        "Explore scenic trails around the city with a guide."
                    ),
                    "available_slots": 12,
                    "images": ["https://example.com/activity4.jpg"],
                },
            ]

            # Filter by category if provided
            if category != "any":
                mock_activities = [
                    a for a in mock_activities if a["category"] == category
                ]

            # Filter by max_price if provided
            if max_price:
                mock_activities = [
                    a for a in mock_activities if a["price_per_person"] <= max_price
                ]

            # Filter by duration if provided
            if duration:
                mock_activities = [
                    a for a in mock_activities if a["duration"] == duration
                ]

            return {
                "activities": mock_activities,
                "search_criteria": params,
                "results_count": len(mock_activities),
                "note": (
                    "This is mock data. Activity search functionality "
                    "will be implemented with a real API."
                ),
            }

        except Exception as e:
            logger.error("Error searching activities: %s", str(e))
            return {"error": f"Activity search error: {str(e)}"}

    @function_tool
    async def search_destination_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for comprehensive information about a travel destination.

        Uses both the WebSearchTool and specialized travel resources to gather and
        analyze detailed information about a destination.

        Args:
            params: Parameters including destination name and topics to search for
                destination: Name of the destination (city, country, attraction)
                topics: List of topics (e.g., "attractions", "safety",
                    "transportation", "best_time")
                max_results: Maximum number of results per topic (default: 5)

        Returns:
            Dictionary containing structured information about the destination
        """
        try:
            # Convert info_types to topics if present (for backward compatibility)
            if "info_types" in params and "topics" not in params:
                params["topics"] = params.pop("info_types")

            # Delegate to the destination research component
            return await self.destination_research.search_destination_info(params)

        except Exception as e:
            logger.error("Error searching destination info: %s", str(e))
            return {"error": f"Destination search error: {str(e)}"}

    @function_tool
    async def get_destination_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about events happening at a destination.

        Uses specialized web crawling to find upcoming events at a specific
        destination during a given time period.

        Args:
            params: Parameters for the event search:
                destination: Destination name (e.g., "Paris, France")
                start_date: Start date in YYYY-MM-DD format
                end_date: End date in YYYY-MM-DD format
                categories: List of event categories (optional)

        Returns:
            Dictionary containing event information for the destination
        """
        try:
            # Delegate to the destination research component
            return await self.destination_research.get_destination_events(params)

        except Exception as e:
            logger.error("Error getting destination events: %s", str(e))
            return {"error": f"Events search error: {str(e)}"}

    @function_tool
    async def crawl_travel_blog(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from travel blogs about a destination.

        Uses specialized blog crawling to extract valuable insights, recommendations,
        and tips from travel blogs about a specific destination.

        Args:
            params: Parameters for blog crawling:
                destination: Destination name (e.g., "Paris, France")
                topics: List of topics to extract (e.g., "hidden gems")
                max_blogs: Maximum number of blogs to crawl (default: 3)
                recent_only: Whether to include only recent blogs (default: True)

        Returns:
            Dictionary containing blog insights about the destination
        """
        try:
            # Delegate to the destination research component
            return await self.destination_research.crawl_travel_blog(params)

        except Exception as e:
            logger.error("Error crawling travel blogs: %s", str(e))
            return {"error": f"Blog crawling error: {str(e)}"}

    @function_tool
    async def compare_travel_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare travel options for a specific category using WebSearchTool
        and specialized APIs.

        Args:
            params: Parameters for the comparison
                category: Type of comparison ("flights", "accommodations", "activities")
                origin: Origin location (for flights)
                destination: Destination location
                dates: Travel dates
                preferences: Any specific preferences to consider

        Returns:
            Dictionary containing comparison results
        """
        try:
            # Extract parameters
            category = params.get("category")
            destination = params.get("destination")

            if not category or not destination:
                return {"error": "Category and destination parameters are required"}

            # Specialized handling based on category
            if category == "flights":
                origin = params.get("origin")
                if not origin:
                    return {
                        "error": "Origin parameter is required for flight comparisons"
                    }

                # This would eventually call the Flights MCP
                # For now, we just return structured data for the agent
                return {
                    "category": "flights",
                    "origin": origin,
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": (
                        "The agent will use WebSearchTool for general information "
                        "and Flights MCP for specific data"
                    ),
                }

            elif category == "accommodations":
                # This would eventually call the Accommodations MCP
                return {
                    "category": "accommodations",
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": (
                        "The agent will use WebSearchTool for reviews "
                        "and Accommodations MCP for availability"
                    ),
                }

            elif category == "activities":
                # This would eventually call the Web Crawling MCP
                return {
                    "category": "activities",
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": (
                        "The agent will use WebSearchTool and Web Crawling MCP "
                        "to find activities"
                    ),
                }

            else:
                return {
                    "category": category,
                    "destination": destination,
                    "search_strategy": "web_search",
                    "note": (
                        "The agent will use WebSearchTool to find general information"
                    ),
                }

        except Exception as e:
            logger.error("Error comparing travel options: %s", str(e))
            return {"error": f"Comparison error: {str(e)}"}

    @function_tool
    async def store_travel_knowledge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store travel-related knowledge in the knowledge graph.

        This tool stores entities, relationships, and observations in the
        dual-storage architecture knowledge graph for future reference.

        Args:
            params: Parameters for storing knowledge
                entity_type: Type of entity
                    (Destination, Accommodation, Transportation, etc.)
                entity_name: Name of the entity
                observations: List of facts or observations about the entity
                relations: List of relations to other entities (optional)

        Returns:
            Dictionary with storage confirmation and status
        """
        try:
            from ..mcp.memory import get_client

            # Extract parameters
            entity_type = params.get("entity_type")
            entity_name = params.get("entity_name")
            observations = params.get("observations", [])
            relations = params.get("relations", [])

            if not entity_type or not entity_name:
                return {"error": "Entity type and name are required"}

            if not observations and not relations:
                return {"error": "At least one observation or relation is required"}

            # Get memory client
            memory_client = get_client()

            # Create entity if observations are provided
            if observations:
                await memory_client.create_entities(
                    [
                        {
                            "name": entity_name,
                            "entityType": entity_type,
                            "observations": observations,
                        }
                    ]
                )

            # Create relations if provided
            if relations:
                formatted_relations = []
                for relation in relations:
                    if "from" in relation and "type" in relation and "to" in relation:
                        formatted_relations.append(
                            {
                                "from": relation["from"],
                                "relationType": relation["type"],
                                "to": relation["to"],
                            }
                        )

                if formatted_relations:
                    await memory_client.create_relations(formatted_relations)

            # Cache this knowledge to improve future interactions
            cache_key = f"knowledge:{entity_type}:{entity_name}"
            await redis_cache.set(
                cache_key,
                {
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "observations": observations,
                    "relations": relations,
                },
                ttl=86400,
            )  # 24 hours

            return {
                "success": True,
                "entity_type": entity_type,
                "entity_name": entity_name,
                "observations_stored": len(observations),
                "relations_stored": len(relations) if relations else 0,
                "message": f"Successfully stored knowledge about {entity_name}",
            }

        except Exception as e:
            logger.error("Error storing travel knowledge: %s", str(e))
            if isinstance(e, MCPError):
                return {"error": e.message}
            return {"error": f"Knowledge storage error: {str(e)}"}

    @function_tool
    async def retrieve_travel_knowledge(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve travel-related knowledge from the knowledge graph.

        This tool queries the knowledge graph to find relevant travel information
        based on entity name or search query.

        Args:
            params: Parameters for retrieving knowledge
                entity_name: Name of the entity to retrieve (optional)
                query: Search query to find relevant entities (optional)
                entity_type: Type of entity to filter by (optional)

        Returns:
            Dictionary with retrieved knowledge
        """
        try:
            from ..mcp.memory import get_client

            # Extract parameters
            entity_name = params.get("entity_name")
            query = params.get("query")
            entity_type = params.get("entity_type")

            if not entity_name and not query:
                return {"error": "Either entity_name or query parameter is required"}

            # Get memory client
            memory_client = get_client()

            # Try to get from cache first
            if entity_name:
                cache_key = f"knowledge:{entity_type or '*'}:{entity_name}"
                cached_result = await redis_cache.get(cache_key)
                if cached_result:
                    cached_result["cache_hit"] = True
                    return cached_result

            # Retrieve by entity name
            if entity_name:
                nodes = await memory_client.open_nodes([entity_name])

                # Extract relevant data
                if nodes and len(nodes) > 0:
                    result = {
                        "found": True,
                        "entity_name": entity_name,
                        "entity_type": nodes[0].get("type"),
                        "observations": nodes[0].get("observations", []),
                        "relations": [],
                    }

                    # Get related nodes
                    graph = await memory_client.read_graph()

                    # Find relations where this entity is involved
                    for relation in graph.get("relations", []):
                        if (
                            relation.get("from") == entity_name
                            or relation.get("to") == entity_name
                        ):
                            result["relations"].append(relation)

                    return result
                else:
                    return {
                        "found": False,
                        "entity_name": entity_name,
                        "message": f"No knowledge found for {entity_name}",
                    }

            # Search by query
            if query:
                search_results = await memory_client.search_nodes(query)

                # Filter by entity_type if provided
                if entity_type and search_results:
                    search_results = [
                        node
                        for node in search_results
                        if node.get("type") == entity_type
                    ]

                return {
                    "found": len(search_results) > 0,
                    "query": query,
                    "entity_type": entity_type,
                    "results_count": len(search_results),
                    "results": search_results,
                }

            return {"error": "Invalid parameters for knowledge retrieval"}

        except Exception as e:
            logger.error("Error retrieving travel knowledge: %s", str(e))
            if isinstance(e, MCPError):
                return {"error": e.message}
            return {"error": f"Knowledge retrieval error: {str(e)}"}


def create_agent() -> TravelAgent:
    """Create and return a fully initialized TravelAgent instance.

    Creates a new TravelAgent with all tools registered and ready for use.
    """
    agent = TravelAgent()

    # Register all travel-specific tools
    agent._register_travel_tools()

    logger.info("Created TripSage Travel Agent instance with all tools registered")
    return agent
