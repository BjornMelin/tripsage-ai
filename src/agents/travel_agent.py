"""
Travel Agent implementation for TripSage.

This module provides the TravelAgent implementation which integrates various
travel-specific MCP tools and dual storage architecture with OpenAI's WebSearchTool.
"""

import datetime
import json
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from agents import WebSearchTool, function_tool
from agents.extensions.allowed_domains import AllowedDomains

from ..cache.redis_cache import redis_cache
from ..utils.config import get_config
from ..utils.error_handling import MCPError, TripSageError, log_exception
from ..utils.logging import get_module_logger
from .base_agent import TravelAgent as BaseTravelAgent

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

        # Add WebSearchTool to the agent's tools with travel-specific domain focus
        # This is part of our hybrid search approach where OpenAI's built-in search
        # serves as the primary method for general queries, while specialized MCP tools
        # (Firecrawl, Browser MCP) are used for deeper, more specific travel research
        self.web_search_tool = WebSearchTool(
            allowed_domains=AllowedDomains(
                domains=[
                    # Travel information and guides
                    "tripadvisor.com",
                    "lonelyplanet.com",
                    "wikitravel.org",
                    "travel.state.gov",
                    "wikivoyage.org",
                    "frommers.com",
                    "roughguides.com",
                    "fodors.com",
                    # Flight and transportation
                    "kayak.com",
                    "skyscanner.com",
                    "expedia.com",
                    "booking.com",
                    "hotels.com",
                    "airbnb.com",
                    "vrbo.com",
                    "orbitz.com",
                    # Airlines
                    "united.com",
                    "aa.com",
                    "delta.com",
                    "southwest.com",
                    "britishairways.com",
                    "lufthansa.com",
                    "emirates.com",
                    "cathaypacific.com",
                    "qantas.com",
                    # Weather and climate
                    "weather.com",
                    "accuweather.com",
                    "weatherspark.com",
                    "climate.gov",
                    # Government travel advisories
                    "travel.state.gov",
                    "smartraveller.gov.au",
                    "gov.uk/foreign-travel-advice",
                    # Social and review sites
                    "tripadvisor.com",
                    "yelp.com",
                ]
            ),
            # Block content farms and untrustworthy sources
            blocked_domains=["pinterest.com", "quora.com"],
        )
        self.agent.tools.append(self.web_search_tool)
        logger.info(
            "Added WebSearchTool to TravelAgent with travel-specific domain configuration"
        )

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools."""
        # Register weather tools
        self._register_tool(self.get_weather)
        self._register_tool(self.get_weather_forecast)
        self._register_tool(self.get_travel_recommendation)

        # Flight tools will be registered once implemented
        self._register_tool(self.search_flights)

        # Accommodation tools will be registered once implemented
        self._register_tool(self.search_accommodations)

        # Time management tools
        self._register_tool(self.convert_timezone)

        # Trip management tools
        self._register_tool(self.create_trip)
        self._register_tool(self.search_activities)

        # Search-related tools
        self._register_tool(self.search_destination_info)
        self._register_tool(self.compare_travel_options)

        # Note: WebSearchTool is added separately in __init__
        # since it doesn't use the function_tool decorator pattern

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
            params: Flight search parameters including origin, destination, dates, and preferences

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
                "note": "This is mock data. Flight search functionality will be implemented with a real API.",
            }

        except Exception as e:
            logger.error("Error searching flights: %s", str(e))
            return {"error": f"Flight search error: {str(e)}"}

    @function_tool
    async def search_accommodations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for accommodations.

        Args:
            params: Accommodation search parameters including location, dates, and preferences

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
                "note": "This is mock data. Accommodation search functionality will be implemented with a real API.",
            }

        except Exception as e:
            logger.error("Error searching accommodations: %s", str(e))
            return {"error": f"Accommodation search error: {str(e)}"}

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
                "time": time_str,  # This would be converted with the actual implementation
            },
            "status": "not_implemented",
            "note": "Timezone conversion functionality will be implemented with the Time MCP.",
        }

    @function_tool
    async def create_trip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip in the system.

        Args:
            params: Trip parameters including user_id, title, destination, dates, and budget

        Returns:
            Created trip information
        """
        try:
            # In a real implementation, we would connect to Supabase
            # This is a placeholder
            trip_id = "trip_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")

            return {
                "success": True,
                "trip_id": trip_id,
                "message": "Trip created successfully",
                "trip_details": {
                    "user_id": params.get("user_id"),
                    "title": params.get("title"),
                    "description": params.get("description", ""),
                    "destination": params.get("destination"),
                    "start_date": params.get("start_date"),
                    "end_date": params.get("end_date"),
                    "budget": params.get("budget"),
                },
                "note": "This is a mock trip creation. Database integration will be implemented.",
            }

        except Exception as e:
            logger.error("Error creating trip: %s", str(e))
            return {"success": False, "error": f"Trip creation error: {str(e)}"}

    @function_tool
    async def search_activities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for activities and attractions at a destination.

        Args:
            params: Activity search parameters including location, category, and preferences

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
                    "description": "Explore the city's main attractions with a knowledgeable guide.",
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
                    "description": "Visit the city's renowned art museum.",
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
                    "description": "Sample local cuisine at various restaurants and food markets.",
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
                    "description": "Explore scenic trails around the city with a guide.",
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
                "note": "This is mock data. Activity search functionality will be implemented with a real API.",
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
            params: Parameters including destination name and info types to search for
                destination: Name of the destination (city, country, attraction)
                info_types: List of info types (e.g., "attractions", "safety", "transportation", "best_time")

        Returns:
            Dictionary containing structured information about the destination
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            info_types = params.get("info_types", ["general"])

            if not destination:
                return {"error": "Destination parameter is required"}

            # Build queries for each info type
            search_results = {}

            for info_type in info_types:
                query = self._build_destination_query(destination, info_type)

                # WebSearchTool is used automatically through the agent
                # Results will be returned to the agent which will process them

                # This would use our redis cache when implemented
                cache_key = f"destination:{destination}:info_type:{info_type}"
                cached_result = await redis_cache.get(cache_key)

                if cached_result:
                    search_results[info_type] = cached_result
                else:
                    # Note: We let the agent use the WebSearchTool
                    # This function mainly provides structure and caching
                    search_results[info_type] = {
                        "query": query,
                        "cache": "miss",
                        "note": "Data will be provided by WebSearchTool and processed by the agent",
                    }

            return {
                "destination": destination,
                "info_types": info_types,
                "search_results": search_results,
            }

        except Exception as e:
            logger.error("Error searching destination info: %s", str(e))
            return {"error": f"Destination search error: {str(e)}"}

    def _build_destination_query(self, destination: str, info_type: str) -> str:
        """Build an optimized search query for a destination and info type.

        Args:
            destination: Name of the destination
            info_type: Type of information to search for

        Returns:
            A formatted search query string
        """
        query_templates = {
            "general": "travel guide {destination} best things to do",
            "attractions": "top attractions in {destination} must-see sights",
            "safety": "{destination} travel safety information for tourists",
            "transportation": "how to get around {destination} public transportation",
            "best_time": "best time to visit {destination} weather seasons",
            "budget": "{destination} travel cost budget accommodation food",
            "food": "best restaurants in {destination} local cuisine food specialties",
            "culture": "{destination} local customs culture etiquette tips",
            "day_trips": "best day trips from {destination} nearby attractions",
            "family": "things to do in {destination} with children family-friendly",
        }

        template = query_templates.get(
            info_type, "travel information about {destination} {info_type}"
        )
        return template.format(destination=destination, info_type=info_type)

    @function_tool
    async def compare_travel_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare travel options for a specific category using WebSearchTool and specialized APIs.

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
                    "note": "The agent will use WebSearchTool for general information and Flights MCP for specific data",
                }

            elif category == "accommodations":
                # This would eventually call the Accommodations MCP
                return {
                    "category": "accommodations",
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": "The agent will use WebSearchTool for reviews and Accommodations MCP for availability",
                }

            elif category == "activities":
                # This would eventually call the Web Crawling MCP
                return {
                    "category": "activities",
                    "destination": destination,
                    "search_strategy": "hybrid",
                    "note": "The agent will use WebSearchTool and Web Crawling MCP to find activities",
                }

            else:
                return {
                    "category": category,
                    "destination": destination,
                    "search_strategy": "web_search",
                    "note": "The agent will use WebSearchTool to find general information",
                }

        except Exception as e:
            logger.error("Error comparing travel options: %s", str(e))
            return {"error": f"Comparison error: {str(e)}"}


def create_agent() -> TravelAgent:
    """Create and return a TravelAgent instance."""
    return TravelAgent()
