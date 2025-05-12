"""
Weather MCP Client implementation for TripSage.

This module provides a client for interacting with the Weather MCP Server,
which offers weather information and travel recommendations.
"""

from typing import Any, Dict, List, Optional, TypeVar

from agents import function_tool

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..base_mcp_client import BaseMCPClient
from .models import (
    BaseParams,
    BaseResponse,
    CurrentWeatherResponse,
    DestinationWeatherComparison,
    ForecastResponse,
    LocationParams,
    OptimalTravelTime,
    RecommendationResponse,
    TravelWeatherSummary,
)

logger = get_module_logger(__name__)
config = get_config()

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResponse)


class WeatherMCPClient(BaseMCPClient[P, R]):
    """Client for the Weather MCP Server."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True,
    ):
        """Initialize the Weather MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        if endpoint is None:
            endpoint = (
                config.weather_mcp.endpoint
                if hasattr(config, "weather_mcp")
                else "http://localhost:8003"
            )

        api_key = api_key or (
            config.weather_mcp.api_key if hasattr(config, "weather_mcp") else None
        )

        super().__init__(
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=1800,  # 30 minutes default cache TTL for weather data
        )
        self.server_name = "Weather"

    @function_tool
    @redis_cache.cached("weather_current", 1800)  # 30 minutes
    async def get_current_weather(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        skip_cache: bool = False,
    ) -> CurrentWeatherResponse:
        """Get the current weather conditions for a location.

        Args:
            city: City name (e.g., 'Paris')
            country: Country code (e.g., 'FR')
            lat: Latitude coordinate
            lon: Longitude coordinate
            skip_cache: Whether to skip the cache

        Returns:
            CurrentWeatherResponse with current weather information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            # Validate parameters
            location_params = LocationParams(
                lat=lat, lon=lon, city=city, country=country
            )

            params = {}
            if location_params.lat is not None and location_params.lon is not None:
                params["lat"] = location_params.lat
                params["lon"] = location_params.lon
            elif location_params.city:
                params["city"] = location_params.city
                if location_params.country:
                    params["country"] = location_params.country

            response = await self.call_tool(
                "get_current_weather", params, skip_cache=skip_cache
            )

            return CurrentWeatherResponse.model_validate(response)
        except Exception as e:
            logger.error(f"Error getting current weather: {str(e)}")
            raise MCPError(
                message=f"Failed to get current weather: {str(e)}",
                server=self.server_name,
                tool="get_current_weather",
                params={"city": city, "country": country, "lat": lat, "lon": lon},
            ) from e

    @function_tool
    @redis_cache.cached("weather_forecast", 3600)  # 1 hour
    async def get_forecast(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 5,
        skip_cache: bool = False,
    ) -> ForecastResponse:
        """Get weather forecast for a location.

        Args:
            city: City name (e.g., 'Paris')
            country: Country code (e.g., 'FR')
            lat: Latitude coordinate
            lon: Longitude coordinate
            days: Number of forecast days (1-16)
            skip_cache: Whether to skip the cache

        Returns:
            ForecastResponse with forecast information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            # Validate parameters
            location_params = LocationParams(
                lat=lat, lon=lon, city=city, country=country
            )

            # Construct location object for API
            location = {}
            if location_params.lat is not None and location_params.lon is not None:
                location["lat"] = location_params.lat
                location["lon"] = location_params.lon
            elif location_params.city:
                location["city"] = location_params.city
                if location_params.country:
                    location["country"] = location_params.country

            # Ensure days is within valid range
            days = min(max(days, 1), 16)

            params = {"location": location, "days": days}

            response = await self.call_tool(
                "get_forecast", params, skip_cache=skip_cache
            )

            return ForecastResponse.model_validate(response)
        except Exception as e:
            logger.error(f"Error getting weather forecast: {str(e)}")
            raise MCPError(
                message=f"Failed to get weather forecast: {str(e)}",
                server=self.server_name,
                tool="get_forecast",
                params={
                    "location": {
                        "city": city,
                        "country": country,
                        "lat": lat,
                        "lon": lon,
                    },
                    "days": days,
                },
            ) from e

    @function_tool
    @redis_cache.cached("weather_recommendation", 3600)  # 1 hour
    async def get_travel_recommendation(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        activities: Optional[List[str]] = None,
        skip_cache: bool = False,
    ) -> RecommendationResponse:
        """Get travel recommendations based on weather conditions.

        Args:
            city: City name (e.g., 'Paris')
            country: Country code (e.g., 'FR')
            lat: Latitude coordinate
            lon: Longitude coordinate
            start_date: Trip start date (YYYY-MM-DD)
            end_date: Trip end date (YYYY-MM-DD)
            activities: List of planned activities (e.g., ['hiking', 'sightseeing'])
            skip_cache: Whether to skip the cache

        Returns:
            RecommendationResponse with travel recommendations

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            # Validate parameters
            location_params = LocationParams(
                lat=lat, lon=lon, city=city, country=country
            )

            # Construct location object for API
            location = {}
            if location_params.lat is not None and location_params.lon is not None:
                location["lat"] = location_params.lat
                location["lon"] = location_params.lon
            elif location_params.city:
                location["city"] = location_params.city
                if location_params.country:
                    location["country"] = location_params.country

            params = {"location": location}

            if start_date:
                params["start_date"] = start_date

            if end_date:
                params["end_date"] = end_date

            if activities:
                params["activities"] = activities

            response = await self.call_tool(
                "get_travel_recommendation", params, skip_cache=skip_cache
            )

            return RecommendationResponse.model_validate(response)
        except Exception as e:
            logger.error(f"Error getting travel recommendations: {str(e)}")
            raise MCPError(
                message=f"Failed to get travel recommendations: {str(e)}",
                server=self.server_name,
                tool="get_travel_recommendation",
                params={
                    "location": {
                        "city": city,
                        "country": country,
                        "lat": lat,
                        "lon": lon,
                    },
                    "start_date": start_date,
                    "end_date": end_date,
                    "activities": activities,
                },
            ) from e


class WeatherService:
    """High-level service for weather-related operations in TripSage."""

    def __init__(self, client: Optional[WeatherMCPClient] = None):
        """Initialize the Weather Service.

        Args:
            client: WeatherMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or get_client()
        logger.info("Initialized Weather Service")

    async def get_destination_weather(self, destination: str) -> Dict[str, Any]:
        """Get current weather for a travel destination.

        Args:
            destination: Travel destination (city name)

        Returns:
            Dict containing current weather information
        """
        try:
            # Parse out country if provided as "City, Country"
            parts = [part.strip() for part in destination.split(",")]
            city = parts[0]
            country = parts[1] if len(parts) > 1 else None

            weather_response = await self.client.get_current_weather(
                city=city, country=country
            )
            return weather_response.model_dump()
        except Exception as e:
            logger.error(f"Error getting destination weather: {str(e)}")
            return {
                "error": f"Failed to get weather for {destination}: {str(e)}",
                "destination": destination,
            }

    async def get_trip_weather_summary(
        self, destination: str, start_date: str, end_date: str
    ) -> TravelWeatherSummary:
        """Get a weather summary for a trip period.

        Args:
            destination: Travel destination (city name)
            start_date: Trip start date (YYYY-MM-DD)
            end_date: Trip end date (YYYY-MM-DD)

        Returns:
            TravelWeatherSummary containing weather summary for the trip
        """
        try:
            # Parse out country if provided as "City, Country"
            parts = [part.strip() for part in destination.split(",")]
            city = parts[0]
            country = parts[1] if len(parts) > 1 else None

            # Get forecast data
            forecast = await self.client.get_forecast(
                city=city, country=country, days=16
            )

            # Filter daily forecast to trip dates
            trip_days = []
            for day in forecast.daily:
                date = day.date
                if start_date <= date <= end_date:
                    trip_days.append(day.model_dump())

            # Calculate average temperatures for the trip
            avg_temps = [day["temp_avg"] for day in trip_days]
            min_temps = [day["temp_min"] for day in trip_days]
            max_temps = [day["temp_max"] for day in trip_days]

            # Count weather conditions
            weather_counts = {}
            for day in trip_days:
                condition = day["weather"]["main"]
                weather_counts[condition] = weather_counts.get(condition, 0) + 1

            # Find most common condition
            most_common = (
                max(weather_counts.items(), key=lambda x: x[1])
                if weather_counts
                else None
            )

            return TravelWeatherSummary(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                temperature={
                    "average": sum(avg_temps) / len(avg_temps) if avg_temps else None,
                    "min": min(min_temps) if min_temps else None,
                    "max": max(max_temps) if max_temps else None,
                },
                conditions={
                    "most_common": most_common[0] if most_common else None,
                    "frequency": most_common[1] / len(trip_days)
                    if most_common and trip_days
                    else None,
                    "breakdown": weather_counts,
                },
                days=trip_days,
            )
        except Exception as e:
            logger.error(f"Error getting trip weather summary: {str(e)}")
            return TravelWeatherSummary(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                temperature={"average": None, "min": None, "max": None},
                conditions={"most_common": None, "frequency": None, "breakdown": {}},
                days=[],
                error=f"Failed to get trip weather summary: {str(e)}",
            )

    async def compare_destinations_weather(
        self, destinations: List[str], date: Optional[str] = None
    ) -> DestinationWeatherComparison:
        """Compare weather across multiple potential destinations.

        Args:
            destinations: List of destinations to compare
            date: Date for comparison (YYYY-MM-DD). If not provided, uses current date.

        Returns:
            DestinationWeatherComparison containing weather comparison
        """
        try:
            results = []

            # Fetch weather for each destination
            for destination in destinations:
                parts = [part.strip() for part in destination.split(",")]
                city = parts[0]
                country = parts[1] if len(parts) > 1 else None

                try:
                    if date:
                        # Get forecast and find the specified date
                        forecast = await self.client.get_forecast(
                            city=city, country=country
                        )
                        for day in forecast.daily:
                            if day.date == date:
                                results.append(
                                    {
                                        "destination": destination,
                                        "date": date,
                                        "temperature": {
                                            "average": day.temp_avg,
                                            "min": day.temp_min,
                                            "max": day.temp_max,
                                        },
                                        "conditions": day.weather.main,
                                        "description": day.weather.description,
                                    }
                                )
                                break
                    else:
                        # Get current weather
                        weather = await self.client.get_current_weather(
                            city=city, country=country
                        )
                        results.append(
                            {
                                "destination": destination,
                                "temperature": weather.temperature,
                                "feels_like": weather.feels_like,
                                "conditions": weather.weather.main,
                                "description": weather.weather.description,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error getting weather for {destination}: {str(e)}")
                    results.append({"destination": destination, "error": str(e)})

            # Rank destinations based on weather (simple temperature-based ranking)
            valid_results = [r for r in results if "error" not in r]
            ranking = None

            if valid_results:
                # Sort by temperature (higher is better, for this simple example)
                temp_sorted = sorted(
                    valid_results,
                    key=lambda x: x["temperature"]
                    if date is None
                    else x["temperature"]["average"],
                    reverse=True,
                )

                ranking = [r["destination"] for r in temp_sorted]

            return DestinationWeatherComparison(
                destinations=destinations,
                date=date or "current",
                results=results,
                ranking=ranking,
            )
        except Exception as e:
            logger.error(f"Error comparing destinations weather: {str(e)}")
            return DestinationWeatherComparison(
                destinations=destinations,
                date=date or "current",
                results=[],
                error=f"Failed to compare destinations weather: {str(e)}",
            )

    async def get_optimal_travel_time(
        self, destination: str, activity_type: str = "general", months_ahead: int = 6
    ) -> OptimalTravelTime:
        """Get recommendations for the optimal time to travel to a destination.

        Args:
            destination: Travel destination (city name)
            activity_type: Type of activity planned
                (e.g., 'beach', 'skiing', 'sightseeing')
            months_ahead: How many months ahead to consider

        Returns:
            OptimalTravelTime containing optimal travel time recommendations
        """
        try:
            parts = [part.strip() for part in destination.split(",")]
            city = parts[0]
            country = parts[1] if len(parts) > 1 else None

            # Get travel recommendations with activity
            recommendation = await self.client.get_travel_recommendation(
                city=city, country=country, activities=[activity_type]
            )

            # Extract the specific activity recommendation
            activity_recs = [
                rec
                for rec in recommendation.recommendations["activities"]
                if activity_type.lower() in rec.lower()
            ]

            # Analyze forecast-based recommendations
            forecast_recs = recommendation.recommendations["forecast_based"]
            good_days = [rec for rec in forecast_recs if "Good" in rec]

            # Create a simple recommendation
            if activity_recs:
                activity_advice = activity_recs[0]
            else:
                activity_advice = (
                    "No specific recommendations available for this activity type."
                )

            return OptimalTravelTime(
                destination=destination,
                activity_type=activity_type,
                current_weather=recommendation.current_weather.weather.main,
                current_temp=recommendation.current_weather.temperature,
                activity_recommendation=activity_advice,
                good_weather_days=good_days,
                forecast_recommendations=forecast_recs,
                clothing_recommendations=recommendation.recommendations["clothing"],
            )
        except Exception as e:
            logger.error(f"Error getting optimal travel time: {str(e)}")
            return OptimalTravelTime(
                destination=destination,
                activity_type=activity_type,
                current_weather="",
                current_temp=0.0,
                activity_recommendation="",
                good_weather_days=[],
                forecast_recommendations=[],
                clothing_recommendations=[],
                error=f"Failed to get optimal travel time: {str(e)}",
            )


# Initialize default client instance
weather_client = WeatherMCPClient()


def get_client() -> WeatherMCPClient:
    """Get a Weather MCP Client instance.

    Returns:
        WeatherMCPClient instance
    """
    return weather_client


def get_service() -> WeatherService:
    """Get a Weather Service instance.

    Returns:
        WeatherService instance
    """
    return WeatherService(get_client())
