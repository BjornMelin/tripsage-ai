# Weather MCP Server Implementation

This document provides the detailed implementation specification for the Weather MCP Server in TripSage.

## Overview

The Weather MCP Server provides weather data for travel destinations, supporting both current conditions and forecasts. It integrates with OpenWeatherMap API as the primary data source, with fallbacks to additional providers like Visual Crossing Weather API. This weather data is essential for providing accurate travel recommendations based on expected conditions at destinations.

## Architecture Decision

After evaluating multiple weather service implementation approaches, we've decided to implement a FastMCP 2.0 approach that:

1. Uses FastMCP 2.0 as the framework for our MCP server to maintain consistency with other TripSage MCP implementations
2. Integrates directly with OpenWeatherMap API for real-time weather data
3. Provides a clear interface that works seamlessly with both Claude Desktop and OpenAI Agents SDK
4. Implements caching to optimize performance and reduce API costs

This approach provides:

- **Consistency**: Same FastMCP 2.0 framework used across all TripSage MCP implementations
- **Reliability**: Direct integration with established weather API providers
- **Compatibility**: Support for both Claude Desktop and OpenAI Agents SDK
- **Performance**: Optimized caching for frequently requested weather data
- **Extensibility**: Modular design that enables adding new weather data sources

## Python Implementation

### Server Implementation

```python
# src/mcp/weather/server.py
from typing import Any, Dict, List, Optional, Union
import asyncio
import datetime
import httpx
from pydantic import BaseModel, Field, model_validator

from ..base_mcp_server import BaseMCPServer, MCPTool
from ...utils.logging import get_module_logger
from ...utils.error_handling import APIError, MCPError
from ...utils.config import get_config
from ...cache.redis_cache import redis_cache

logger = get_module_logger(__name__)
config = get_config()


class LocationParams(BaseModel):
    """Parameters for location-based weather queries."""

    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None

    @model_validator(mode='after')
    def validate_coordinates_or_city(self) -> 'LocationParams':
        """Validate that either coordinates or city is provided."""
        if (self.lat is None or self.lon is None) and not self.city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        return self


class ForecastParams(BaseModel):
    """Parameters for weather forecast queries."""

    location: LocationParams
    days: int = Field(default=5, ge=1, le=16)


class TravelRecommendationParams(BaseModel):
    """Parameters for travel recommendations based on weather."""

    location: LocationParams
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    activities: Optional[List[str]] = None


class OpenWeatherMapAPI:
    """Client for OpenWeatherMap API."""

    def __init__(self, api_key: str):
        """Initialize the OpenWeatherMap API client.

        Args:
            api_key: OpenWeatherMap API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the OpenWeatherMap API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data

        Raises:
            APIError: If the API request fails
        """
        # Ensure API key is included
        params["appid"] = self.api_key
        # Use metric units
        params["units"] = "metric"

        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise APIError(
                message=f"OpenWeatherMap API error: {e.response.status_code}",
                service="OpenWeatherMap",
                status_code=e.response.status_code,
                response=e.response.text
            )

        except Exception as e:
            raise APIError(
                message=f"OpenWeatherMap API request failed: {str(e)}",
                service="OpenWeatherMap"
            )

    @redis_cache.cached("weather_current", 1800)  # Cache for 30 minutes
    async def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current weather conditions."""
        params: Dict[str, Any] = {}

        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            params["q"] = city if not country else f"{city},{country}"
        else:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        data = await self._make_request("weather", params)

        # Transform the data to a more usable format
        return {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "temp_min": data["main"]["temp_min"],
            "temp_max": data["main"]["temp_max"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "wind_speed": data["wind"]["speed"],
            "wind_direction": data["wind"]["deg"],
            "clouds": data["clouds"]["all"],
            "weather": {
                "id": data["weather"][0]["id"],
                "main": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"]
            },
            "location": {
                "name": data["name"],
                "country": data["sys"]["country"],
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
                "timezone": data["timezone"]
            },
            "timestamp": data["dt"],
            "source": "OpenWeatherMap"
        }

    @redis_cache.cached("weather_forecast", 3600)  # Cache for 1 hour
    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        days: int = 5
    ) -> Dict[str, Any]:
        """Get weather forecast."""
        params: Dict[str, Any] = {}

        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            params["q"] = city if not country else f"{city},{country}"
        else:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        # Limit to the number of days requested (API returns in 3-hour intervals)
        params["cnt"] = min(days * 8, 40)  # 8 intervals per day, max 40 (5 days)

        data = await self._make_request("forecast", params)

        # Group forecast by day
        forecasts_by_day: Dict[str, List[Dict[str, Any]]] = {}

        for item in data["list"]:
            # Convert timestamp to date string
            date = datetime.datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")

            if date not in forecasts_by_day:
                forecasts_by_day[date] = []

            forecasts_by_day[date].append({
                "timestamp": item["dt"],
                "time": datetime.datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                "temperature": item["main"]["temp"],
                "feels_like": item["main"]["feels_like"],
                "temp_min": item["main"]["temp_min"],
                "temp_max": item["main"]["temp_max"],
                "humidity": item["main"]["humidity"],
                "pressure": item["main"]["pressure"],
                "wind_speed": item["wind"]["speed"],
                "wind_direction": item["wind"]["deg"],
                "clouds": item["clouds"]["all"],
                "weather": {
                    "id": item["weather"][0]["id"],
                    "main": item["weather"][0]["main"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"]
                }
            })

        # Calculate daily aggregates
        daily_forecast = []

        for date, intervals in forecasts_by_day.items():
            # Calculate min, max, and average values
            temps = [interval["temperature"] for interval in intervals]
            humidity = [interval["humidity"] for interval in intervals]

            # Most common weather condition
            weather_conditions = [interval["weather"]["main"] for interval in intervals]
            most_common_condition = max(set(weather_conditions), key=weather_conditions.count)

            # Find the interval with the most common condition
            for interval in intervals:
                if interval["weather"]["main"] == most_common_condition:
                    representative_weather = interval["weather"]
                    break
            else:
                representative_weather = intervals[0]["weather"]

            daily_forecast.append({
                "date": date,
                "temp_min": min(temps),
                "temp_max": max(temps),
                "temp_avg": sum(temps) / len(temps),
                "humidity_avg": sum(humidity) / len(humidity),
                "weather": representative_weather,
                "intervals": intervals
            })

        return {
            "location": {
                "name": data["city"]["name"],
                "country": data["city"]["country"],
                "lat": data["city"]["coord"]["lat"],
                "lon": data["city"]["coord"]["lon"],
                "timezone": data["city"]["timezone"]
            },
            "daily": daily_forecast,
            "source": "OpenWeatherMap"
        }


class WeatherMCPServer(BaseMCPServer):
    """Weather MCP Server for TripSage."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3000,
        openweathermap_api_key: Optional[str] = None,
        visual_crossing_api_key: Optional[str] = None
    ):
        """Initialize the Weather MCP Server."""
        super().__init__(
            name="Weather",
            description="Weather information service with OpenWeatherMap",
            version="1.0.0",
            host=host,
            port=port
        )

        # Initialize API clients
        self.openweathermap_api_key = openweathermap_api_key or config.weather_mcp.openweathermap_api_key
        self.openweathermap = OpenWeatherMapAPI(self.openweathermap_api_key)

        # Register tools
        self.register_tool(CurrentWeatherTool(self.openweathermap))
        self.register_tool(ForecastTool(self.openweathermap))
        self.register_tool(TravelRecommendationTool(self.openweathermap))


class CurrentWeatherTool:
    """Tool for getting current weather conditions."""

    name = "get_current_weather"
    description = "Get current weather conditions for a location"

    def __init__(self, openweathermap: OpenWeatherMapAPI):
        """Initialize the tool."""
        self.openweathermap = openweathermap

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool."""
        # Validate parameters
        try:
            location_params = LocationParams(**params)
        except Exception as e:
            raise MCPError(
                message=f"Invalid parameters: {str(e)}",
                server="Weather",
                tool=self.name,
                params=params
            )

        try:
            return await self.openweathermap.get_current_weather(
                lat=location_params.lat,
                lon=location_params.lon,
                city=location_params.city,
                country=location_params.country
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise MCPError(
                    message=f"Weather API error: {e.message}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )
            else:
                raise MCPError(
                    message=f"Error getting current weather: {str(e)}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )


class ForecastTool:
    """Tool for getting weather forecasts."""

    name = "get_forecast"
    description = "Get weather forecast for a location"

    def __init__(self, openweathermap: OpenWeatherMapAPI):
        """Initialize the tool."""
        self.openweathermap = openweathermap

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool."""
        # Validate parameters
        try:
            forecast_params = ForecastParams(**params)
        except Exception as e:
            raise MCPError(
                message=f"Invalid parameters: {str(e)}",
                server="Weather",
                tool=self.name,
                params=params
            )

        try:
            return await self.openweathermap.get_forecast(
                lat=forecast_params.location.lat,
                lon=forecast_params.location.lon,
                city=forecast_params.location.city,
                country=forecast_params.location.country,
                days=forecast_params.days
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise MCPError(
                    message=f"Weather API error: {e.message}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )
            else:
                raise MCPError(
                    message=f"Error getting forecast: {str(e)}",
                    server="Weather",
                    tool=self.name,
                    params=params
                )


class TravelRecommendationTool:
    """Tool for getting travel recommendations based on weather."""

    name = "get_travel_recommendation"
    description = "Get travel recommendations based on weather conditions"

    def __init__(self, openweathermap: OpenWeatherMapAPI):
        """Initialize the tool."""
        self.openweathermap = openweathermap

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool."""
        # Implementation details...
```

### Tool Definitions for Weather-Related Functions

```python
# src/mcp/weather/__init__.py
from typing import Dict, Any, List
from ..base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Define tool schemas
GET_CURRENT_WEATHER_SCHEMA = {
    "name": "get_current_weather",
    "description": "Get current weather conditions for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "lat": {
                "type": "number",
                "description": "Latitude coordinate"
            },
            "lon": {
                "type": "number",
                "description": "Longitude coordinate"
            },
            "city": {
                "type": "string",
                "description": "City name (e.g., 'Paris')"
            },
            "country": {
                "type": "string",
                "description": "Country code (e.g., 'FR' for France)"
            }
        },
        "anyOf": [
            {"required": ["lat", "lon"]},
            {"required": ["city"]}
        ]
    }
}

GET_FORECAST_SCHEMA = {
    "name": "get_forecast",
    "description": "Get weather forecast for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "city": {"type": "string"},
                    "country": {"type": "string"}
                },
                "anyOf": [
                    {"required": ["lat", "lon"]},
                    {"required": ["city"]}
                ]
            },
            "days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 16,
                "default": 5,
                "description": "Number of forecast days"
            }
        },
        "required": ["location"]
    }
}

GET_TRAVEL_RECOMMENDATION_SCHEMA = {
    "name": "get_travel_recommendation",
    "description": "Get travel recommendations based on weather conditions",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "city": {"type": "string"},
                    "country": {"type": "string"}
                },
                "anyOf": [
                    {"required": ["lat", "lon"]},
                    {"required": ["city"]}
                ]
            },
            "start_date": {
                "type": "string",
                "format": "date",
                "description": "Trip start date (YYYY-MM-DD)"
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "description": "Trip end date (YYYY-MM-DD)"
            },
            "activities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Planned activities (e.g., ['hiking', 'sightseeing'])"
            }
        },
        "required": ["location"]
    }
}

# Export tool schemas for OpenAI Agent SDK integration
WEATHER_TOOL_SCHEMAS = [
    GET_CURRENT_WEATHER_SCHEMA,
    GET_FORECAST_SCHEMA,
    GET_TRAVEL_RECOMMENDATION_SCHEMA
]
```

### Client Implementation

```python
# src/mcp/weather/client.py
from typing import Any, Dict, List, Optional, Union
import datetime

from ..base_mcp_client import BaseMCPClient
from ...utils.logging import get_module_logger
from ...utils.config import get_config
from ...cache.redis_cache import redis_cache
from agents import function_tool

logger = get_module_logger(__name__)
config = get_config()


class WeatherMCPClient(BaseMCPClient):
    """Client for the Weather MCP Server."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True
    ):
        """Initialize the Weather MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        super().__init__(
            endpoint=endpoint or config.weather_mcp.endpoint,
            api_key=api_key or config.weather_mcp.api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=1800  # 30 minutes default cache TTL for weather data
        )

    @function_tool
    @redis_cache.cached("weather_current", 1800)  # 30 minutes
    async def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get current weather conditions.

        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            skip_cache: Whether to skip the cache

        Returns:
            Current weather data

        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        if (lat is None or lon is None) and not city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        params = {}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        if city:
            params["city"] = city
        if country:
            params["country"] = country

        return await self.call_tool("get_current_weather", params, skip_cache=skip_cache)

    @function_tool
    @redis_cache.cached("weather_forecast", 3600)  # 1 hour
    async def get_forecast(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        days: int = 5,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get weather forecast.

        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            days: Number of forecast days
            skip_cache: Whether to skip the cache

        Returns:
            Forecast data

        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        if (lat is None or lon is None) and not city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        params = {
            "days": days
        }

        location = {}
        if lat is not None and lon is not None:
            location["lat"] = lat
            location["lon"] = lon
        if city:
            location["city"] = city
        if country:
            location["country"] = country

        params["location"] = location

        return await self.call_tool("get_forecast", params, skip_cache=skip_cache)

    @function_tool
    @redis_cache.cached("weather_travel", 3600)  # 1 hour
    async def get_travel_recommendation(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        activities: Optional[List[str]] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get travel recommendations based on weather.

        Args:
            lat: Latitude
            lon: Longitude
            city: City name
            country: Country code
            start_date: Trip start date
            end_date: Trip end date
            activities: Desired activities
            skip_cache: Whether to skip the cache

        Returns:
            Travel recommendations

        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        if (lat is None or lon is None) and not city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        params = {}

        location = {}
        if lat is not None and lon is not None:
            location["lat"] = lat
            location["lon"] = lon
        if city:
            location["city"] = city
        if country:
            location["country"] = country

        params["location"] = location

        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        if activities:
            params["activities"] = activities

        return await self.call_tool("get_travel_recommendation", params, skip_cache=skip_cache)


# Additional TripSage-specific Weather Service
class WeatherService:
    """High-level service for weather-related operations in TripSage."""

    def __init__(self, client: Optional[WeatherMCPClient] = None):
        """Initialize the Weather Service.

        Args:
            client: WeatherMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or get_client()
        logger.info("Initialized Weather Service")

    async def analyze_weather_for_destination(
        self,
        destination: str,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """Analyze weather for a travel destination during a specific period.

        Args:
            destination: Travel destination (city name)
            start_date: Trip start date
            end_date: Trip end date

        Returns:
            Weather analysis for the destination
        """
        try:
            # Get forecast for the destination
            forecast = await self.client.get_forecast(
                city=destination,
                days=(end_date - start_date).days + 1
            )

            # Get travel recommendations
            recommendations = await self.client.get_travel_recommendation(
                city=destination,
                start_date=start_date,
                end_date=end_date,
                activities=["sightseeing", "outdoor dining", "hiking"]
            )

            # Analyze weather patterns
            daily_temps = [day["temp_avg"] for day in forecast["daily"]]
            avg_temp = sum(daily_temps) / len(daily_temps)
            min_temp = min([day["temp_min"] for day in forecast["daily"]])
            max_temp = max([day["temp_max"] for day in forecast["daily"]])

            # Count weather conditions
            conditions = {}
            for day in forecast["daily"]:
                condition = day["weather"]["main"]
                conditions[condition] = conditions.get(condition, 0) + 1

            # Find the most common condition
            most_common_condition = max(conditions, key=conditions.get)

            # Calculate chance of rain
            rainy_conditions = ["Rain", "Drizzle", "Thunderstorm"]
            rainy_days = sum(1 for day in forecast["daily"] if day["weather"]["main"] in rainy_conditions)
            chance_of_rain = rainy_days / len(forecast["daily"]) * 100

            return {
                "destination": destination,
                "trip_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration": (end_date - start_date).days + 1
                },
                "weather_summary": {
                    "average_temperature": round(avg_temp, 1),
                    "min_temperature": round(min_temp, 1),
                    "max_temperature": round(max_temp, 1),
                    "most_common_condition": most_common_condition,
                    "chance_of_rain": round(chance_of_rain, 1)
                },
                "daily_forecast": forecast["daily"],
                "recommendations": recommendations["recommendations"]
            }
        except Exception as e:
            logger.error(f"Error analyzing weather for destination: {str(e)}")
            return {
                "error": f"Failed to analyze weather for {destination}: {str(e)}",
                "destination": destination
            }

    async def plan_best_weather_itinerary(
        self,
        destinations: List[str],
        total_days: int,
        preferred_weather: str = "sunny"
    ) -> Dict[str, Any]:
        """Create an itinerary based on weather conditions across multiple destinations.

        Args:
            destinations: List of destinations to consider
            total_days: Total trip duration in days
            preferred_weather: Preferred weather condition (sunny, moderate, etc.)

        Returns:
            Weather-optimized itinerary
        """
        try:
            # Get weather for all destinations
            destination_weather = {}

            for destination in destinations:
                try:
                    current = await self.client.get_current_weather(city=destination)
                    forecast = await self.client.get_forecast(city=destination, days=10)

                    destination_weather[destination] = {
                        "current": current,
                        "forecast": forecast
                    }
                except Exception as e:
                    logger.warning(f"Error getting weather for {destination}: {str(e)}")

            # Score destinations by weather preference
            destination_scores = {}

            # Define preferred conditions
            if preferred_weather.lower() == "sunny":
                preferred_conditions = ["Clear", "Sunny"]
            elif preferred_weather.lower() == "moderate":
                preferred_conditions = ["Clouds", "Partly cloudy"]
            elif preferred_weather.lower() == "cool":
                preferred_conditions = ["Clouds", "Fog", "Mist"]
            else:
                preferred_conditions = ["Clear", "Sunny", "Clouds"]

            # Score each destination
            for destination, weather in destination_weather.items():
                score = 0

                # Score current weather
                if weather["current"]["weather"]["main"] in preferred_conditions:
                    score += 5

                # Score upcoming days
                for i, day in enumerate(weather["forecast"]["daily"][:total_days]):
                    if day["weather"]["main"] in preferred_conditions:
                        # More weight to earlier days
                        score += 3 * (1 - i * 0.1)

                    # Temperature factor (assume 20-25C is ideal)
                    temp_score = 1 - min(abs(day["temp_avg"] - 22.5) / 10, 1)
                    score += temp_score * 2

                destination_scores[destination] = score

            # Rank destinations
            ranked_destinations = sorted(
                destination_scores.keys(),
                key=lambda d: destination_scores[d],
                reverse=True
            )

            # Create weather-based itinerary
            itinerary = []
            remaining_days = total_days
            assigned_destinations = []

            for destination in ranked_destinations:
                if remaining_days <= 0:
                    break

                # Calculate days to allocate (proportional to score)
                total_score = sum(destination_scores[d] for d in ranked_destinations if d not in assigned_destinations)
                proportion = destination_scores[destination] / total_score if total_score > 0 else 0
                days_to_allocate = max(1, min(int(proportion * total_days), remaining_days))

                # Get best consecutive days
                best_days = []
                best_score = 0

                for start in range(len(destination_weather[destination]["forecast"]["daily"]) - days_to_allocate + 1):
                    days = destination_weather[destination]["forecast"]["daily"][start:start + days_to_allocate]

                    # Calculate score for this sequence
                    sequence_score = sum(
                        3 if day["weather"]["main"] in preferred_conditions else 1
                        for day in days
                    )

                    if sequence_score > best_score:
                        best_score = sequence_score
                        best_days = days

                # Add to itinerary
                itinerary.append({
                    "destination": destination,
                    "days": days_to_allocate,
                    "weather_score": destination_scores[destination],
                    "best_days": best_days
                })

                remaining_days -= days_to_allocate
                assigned_destinations.append(destination)

            return {
                "total_days": total_days,
                "preferred_weather": preferred_weather,
                "destinations_ranked": ranked_destinations,
                "weather_optimized_itinerary": itinerary
            }

        except Exception as e:
            logger.error(f"Error planning weather-based itinerary: {str(e)}")
            return {
                "error": f"Failed to plan weather-based itinerary: {str(e)}"
            }

    async def find_best_travel_month(
        self,
        destination: str,
        preferred_activities: List[str] = None
    ) -> Dict[str, Any]:
        """Find the best month to visit a destination based on historical weather patterns.

        Args:
            destination: Destination to analyze
            preferred_activities: List of preferred activities

        Returns:
            Recommendations on the best time to visit
        """
        # This is a simplified example since historical data API calls would be needed
        # In a real implementation, we would query historical weather API endpoints

        # Simplified destination-to-best-months mapping
        destination_best_months = {
            "paris": {
                "best": ["May", "June", "September"],
                "good": ["April", "July", "August", "October"],
                "avoid": ["November", "December", "January", "February"],
                "notes": "Spring and early fall offer pleasant temperatures and fewer crowds."
            },
            "tokyo": {
                "best": ["March", "April", "October", "November"],
                "good": ["May", "September"],
                "avoid": ["June", "July", "August"],
                "notes": "Cherry blossom season (late March-early April) is beautiful but crowded. Avoid rainy season in June and hot, humid summer."
            },
            "new york": {
                "best": ["May", "September", "October"],
                "good": ["April", "June", "July", "August"],
                "avoid": ["January", "February", "December"],
                "notes": "Fall offers pleasant temperatures and beautiful foliage. Summer can be hot but vibrant. Winter is cold but festive."
            },
            "bangkok": {
                "best": ["November", "December", "January", "February"],
                "good": ["March", "October"],
                "avoid": ["April", "May", "June", "July", "August", "September"],
                "notes": "Dry season (November-February) offers the most comfortable weather. Avoid hot season (April-May) and rainy season (June-October)."
            },
            "sydney": {
                "best": ["October", "November", "March", "April"],
                "good": ["September", "December", "February", "May"],
                "avoid": ["June", "July", "August"],
                "notes": "Spring (September-November) and fall (March-May) offer pleasant temperatures. January can be very hot. June-August is winter."
            }
        }

        # Activity-specific recommendations
        activity_recommendations = {
            "hiking": {
                "ideal_conditions": ["Clear", "Partly cloudy"],
                "ideal_temp_range": (15, 25),
                "avoid": ["Rain", "Snow", "Extreme heat"]
            },
            "beach": {
                "ideal_conditions": ["Clear", "Sunny"],
                "ideal_temp_range": (25, 35),
                "avoid": ["Rain", "Wind", "Cold"]
            },
            "sightseeing": {
                "ideal_conditions": ["Clear", "Partly cloudy"],
                "ideal_temp_range": (18, 28),
                "avoid": ["Heavy rain", "Extreme heat", "Extreme cold"]
            },
            "skiing": {
                "ideal_conditions": ["Snow"],
                "ideal_temp_range": (-5, 5),
                "avoid": ["Rain", "Extreme cold"]
            }
        }

        destination_lower = destination.lower()

        if destination_lower in destination_best_months:
            result = {
                "destination": destination,
                "best_months": destination_best_months[destination_lower]["best"],
                "good_months": destination_best_months[destination_lower]["good"],
                "avoid_months": destination_best_months[destination_lower]["avoid"],
                "general_notes": destination_best_months[destination_lower]["notes"]
            }

            # Add activity-specific recommendations if provided
            if preferred_activities:
                activity_notes = []

                for activity in preferred_activities:
                    if activity.lower() in activity_recommendations:
                        activity_notes.append(
                            f"{activity}: Best in {', '.join(destination_best_months[destination_lower]['best'])}. "
                            f"Ideal conditions: {', '.join(activity_recommendations[activity.lower()]['ideal_conditions'])}. "
                            f"Avoid: {', '.join(activity_recommendations[activity.lower()]['avoid'])}."
                        )

                if activity_notes:
                    result["activity_specific_notes"] = activity_notes

            return result
        else:
            # Get current weather as fallback
            try:
                current = await self.client.get_current_weather(city=destination)
                return {
                    "destination": destination,
                    "note": "Detailed monthly recommendations not available for this destination.",
                    "current_weather": current
                }
            except Exception as e:
                logger.error(f"Error getting weather info for {destination}: {str(e)}")
                return {
                    "error": f"Unable to provide recommendations for {destination}"
                }
```

## OpenAI Agents SDK Integration

```python
# src/agents/weather_agent.py (example integration)
from agents import Agent, function_tool
from src.mcp.weather.client import WeatherMCPClient, WeatherService

# Create weather_agent for specialized weather functions
weather_agent = Agent(
    name="Weather Agent",
    instructions=(
        "You specialize in weather analysis for travel planning. "
        "You can provide current weather conditions, forecasts, and recommendations "
        "for travel destinations. Consider weather patterns when making suggestions "
        "for activities, clothing, and travel timing."
    ),
    tools=[
        weather_client.get_current_weather,
        weather_client.get_forecast,
        weather_client.get_travel_recommendation
    ]
)

# Example of integrating with the main travel agent
async def create_travel_agent():
    # Initialize services
    weather_client = WeatherMCPClient()
    weather_service = WeatherService(weather_client)

    @function_tool
    async def analyze_weather_for_trip(
        destination: str,
        arrival_date: str,
        departure_date: str
    ) -> str:
        """Analyze weather conditions for a trip and provide recommendations.

        Args:
            destination: Name of the destination city
            arrival_date: Trip arrival date in YYYY-MM-DD format
            departure_date: Trip departure date in YYYY-MM-DD format

        Returns:
            Formatted weather analysis and recommendations
        """
        try:
            # Parse dates
            arrival = datetime.datetime.fromisoformat(arrival_date).date()
            departure = datetime.datetime.fromisoformat(departure_date).date()

            # Get weather analysis
            result = await weather_service.analyze_weather_for_destination(
                destination=destination,
                start_date=arrival,
                end_date=departure
            )

            if "error" in result:
                return f"Error analyzing weather: {result['error']}"

            # Format the response
            response = f"Weather Analysis for {destination} ({arrival_date} to {departure_date}):\n\n"

            # Weather summary
            summary = result["weather_summary"]
            response += f"Temperature: Average {summary['average_temperature']}°C (range: {summary['min_temperature']}°C to {summary['max_temperature']}°C)\n"
            response += f"Conditions: Mostly {summary['most_common_condition'].lower()}\n"
            response += f"Chance of rain: {summary['chance_of_rain']}%\n\n"

            # Recommendations
            response += "Recommendations:\n"
            for category, items in result["recommendations"].items():
                if isinstance(items, list):
                    response += f"- {category.replace('_', ' ').title()}: {', '.join(items)}\n"
                else:
                    response += f"- {category.replace('_', ' ').title()}: {items}\n"

            return response
        except Exception as e:
            return f"Error processing weather data: {str(e)}"

    # Create the main travel agent with the analyze_weather_for_trip tool
    travel_agent = Agent(
        name="TripSage Travel Agent",
        instructions=(
            "You are a travel planning assistant that helps users find flights, "
            "accommodations, and activities. Use the appropriate tools to search for flights, "
            "analyze weather conditions, and provide comprehensive travel plans."
        ),
        tools=[
            analyze_weather_for_trip,
            weather_client.get_current_weather,
            weather_client.get_forecast,
            weather_client.get_travel_recommendation
        ],
        # Add other travel tools as needed
    )

    return travel_agent
```

## Claude Desktop Integration

For Claude Desktop, the integration leverages the MCP protocol with the FastMCP server:

```python
# Example Claude prompt addition for weather tool integration

"""
You have access to weather tools to help with travel planning:

1. get_current_weather - Get current weather conditions for a location
   - Parameters:
     - lat (number, optional) - Latitude coordinate
     - lon (number, optional) - Longitude coordinate
     - city (string, optional) - City name (e.g., 'Paris')
     - country (string, optional) - Country code (e.g., 'FR' for France)
   - Notes: Either coordinates (lat, lon) or city must be provided

2. get_forecast - Get weather forecast for a location
   - Parameters:
     - location (object) - Location information with either coordinates or city
       - lat (number, optional) - Latitude coordinate
       - lon (number, optional) - Longitude coordinate
       - city (string, optional) - City name
       - country (string, optional) - Country code
     - days (integer, optional) - Number of forecast days (default: 5)

3. get_travel_recommendation - Get weather-based travel recommendations
   - Parameters:
     - location (object) - Location information with either coordinates or city
       - lat (number, optional) - Latitude coordinate
       - lon (number, optional) - Longitude coordinate
       - city (string, optional) - City name
       - country (string, optional) - Country code
     - start_date (string, optional) - Trip start date in YYYY-MM-DD format
     - end_date (string, optional) - Trip end date in YYYY-MM-DD format
     - activities (array, optional) - Planned activities (e.g., ['hiking', 'sightseeing'])

Use these tools to help users with weather-related aspects of their travel planning, such as:
- Determining current weather at their destination
- Checking forecasts for upcoming trips
- Planning activities based on expected weather conditions
- Recommending appropriate clothing and gear based on weather
- Suggesting the best times to visit specific destinations
"""
```

## Example Use Cases for Travel Planning

### Determining Current Weather at Destinations

```python
async def check_destination_weather(destination: str):
    """Get the current weather at a travel destination."""
    weather_client = WeatherMCPClient()
    result = await weather_client.get_current_weather(city=destination)

    if "error" in result:
        return f"Error getting weather for {destination}: {result['error']}"

    weather_description = result["weather"]["description"]
    temperature = result["temperature"]
    feels_like = result["feels_like"]
    humidity = result["humidity"]
    wind_speed = result["wind_speed"]

    message = (
        f"Current weather in {destination}:\n"
        f"- Conditions: {weather_description}\n"
        f"- Temperature: {temperature}°C (feels like {feels_like}°C)\n"
        f"- Humidity: {humidity}%\n"
        f"- Wind Speed: {wind_speed} m/s"
    )

    return message
```

This helps travelers:

- Check current conditions before departure
- Prepare appropriate clothing for arrival
- Adjust day-of-arrival activities if needed

### Weather-Based Itinerary Planning

```python
async def plan_activities_by_weather(
    destination: str,
    arrival_date_str: str,
    departure_date_str: str,
    activities: List[str]
):
    """Plan activities based on weather forecast."""
    try:
        # Parse dates
        arrival_date = datetime.datetime.fromisoformat(arrival_date_str).date()
        departure_date = datetime.datetime.fromisoformat(departure_date_str).date()

        # Get weather forecast and recommendations
        weather_client = WeatherMCPClient()
        forecast = await weather_client.get_forecast(
            city=destination,
            days=(departure_date - arrival_date).days + 1
        )

        recommendations = await weather_client.get_travel_recommendation(
            city=destination,
            start_date=arrival_date,
            end_date=departure_date,
            activities=activities
        )

        # Map activities to best days
        activity_to_day_map = {}

        # Define weather preferences for activities
        activity_preferences = {
            "hiking": {"good": ["Clear", "Clouds"], "bad": ["Rain", "Thunderstorm", "Snow"]},
            "beach": {"good": ["Clear", "Sunny"], "bad": ["Rain", "Clouds", "Thunderstorm"]},
            "museum": {"good": ["Rain", "Thunderstorm", "Snow"], "bad": []},
            "sightseeing": {"good": ["Clear", "Clouds"], "bad": ["Thunderstorm", "Heavy rain"]},
            "shopping": {"good": [], "bad": []},  # Indoor activity, weather doesn't matter much
            "dining": {"good": ["Clear", "Clouds"], "bad": ["Thunderstorm", "Heavy rain"]}
        }

        # Create day-by-day itinerary
        daily_itinerary = []

        current_date = arrival_date
        day_index = 0
        while current_date <= departure_date:
            # Find the day in the forecast
            forecast_day = None
            for day in forecast["daily"]:
                if day["date"] == current_date.isoformat():
                    forecast_day = day
                    break

            if not forecast_day:
                break

            # Determine suitable activities for this day
            suitable_activities = []

            weather_condition = forecast_day["weather"]["main"]
            for activity in activities:
                activity_lower = activity.lower()

                preferences = next(
                    (v for k, v in activity_preferences.items() if activity_lower in k or k in activity_lower),
                    {"good": [], "bad": []}
                )

                if not preferences["bad"] or weather_condition not in preferences["bad"]:
                    suitable_activities.append(activity)

                    # Record this as a good day for this activity
                    if activity_lower not in activity_to_day_map:
                        activity_to_day_map[activity_lower] = []

                    activity_to_day_map[activity_lower].append(
                        {
                            "date": current_date.isoformat(),
                            "weather": weather_condition,
                            "temperature": forecast_day["temp_avg"],
                            "is_ideal": weather_condition in preferences.get("good", [])
                        }
                    )

            # Create day entry
            daily_itinerary.append({
                "date": current_date.isoformat(),
                "day": day_index + 1,
                "weather": {
                    "condition": weather_condition,
                    "description": forecast_day["weather"]["description"],
                    "temperature": forecast_day["temp_avg"],
                    "temp_min": forecast_day["temp_min"],
                    "temp_max": forecast_day["temp_max"]
                },
                "suggested_activities": suitable_activities,
                "clothing_tip": get_clothing_tip(forecast_day["temp_avg"], weather_condition)
            })

            current_date += datetime.timedelta(days=1)
            day_index += 1

        return {
            "destination": destination,
            "trip_period": {
                "arrival": arrival_date.isoformat(),
                "departure": departure_date.isoformat(),
                "duration": (departure_date - arrival_date).days + 1
            },
            "weather_summary": recommendations["recommendations"]["summary"],
            "daily_itinerary": daily_itinerary,
            "best_days_by_activity": activity_to_day_map
        }

    except Exception as e:
        return {"error": f"Error planning weather-based itinerary: {str(e)}"}

def get_clothing_tip(temperature: float, condition: str) -> str:
    """Get clothing recommendation based on temperature and weather condition."""
    if temperature < 5:
        return "Heavy winter clothing, gloves, scarf, and hat"
    elif temperature < 15:
        return "Warm jacket, long sleeves, and possibly a light scarf"
    elif temperature < 22:
        return "Light jacket or sweater, comfortable for layering"
    elif temperature < 28:
        return "T-shirt with a light layer for evening, comfortable pants"
    else:
        return "Light summer clothing, sun protection recommended"
```

This helps travelers:

- Schedule outdoor activities on the best weather days
- Have backup indoor activities for rainy days
- Pack appropriate clothing for changing conditions
- Make the most of their trip regardless of weather

### Finding Best Time to Visit

```python
async def find_best_time_to_visit(destination: str, activity: str = None):
    """Find the best time of year to visit a destination."""
    weather_service = WeatherService()

    try:
        activities = [activity] if activity else None
        result = await weather_service.find_best_travel_month(
            destination=destination,
            preferred_activities=activities
        )

        if "error" in result:
            return f"Error finding best time to visit {destination}: {result['error']}"

        message = f"Best time to visit {destination}:\n\n"

        if "best_months" in result:
            message += f"Best months: {', '.join(result['best_months'])}\n"
            message += f"Good months: {', '.join(result['good_months'])}\n"
            message += f"Months to avoid: {', '.join(result['avoid_months'])}\n\n"

            if "general_notes" in result:
                message += f"General notes: {result['general_notes']}\n\n"

        if "activity_specific_notes" in result and result["activity_specific_notes"]:
            message += "Activity-specific recommendations:\n"
            for note in result["activity_specific_notes"]:
                message += f"- {note}\n"

        return message

    except Exception as e:
        return f"Error finding best time to visit {destination}: {str(e)}"
```

This helps travelers:

- Plan trips during ideal weather conditions
- Avoid rainy or extreme temperature seasons
- Align travel dates with preferred activities
- Make informed decisions on when to book

### Weather Comparison for Multiple Destinations

```python
async def compare_destinations_weather(
    destinations: List[str],
    travel_date_str: str
):
    """Compare weather across multiple possible destinations."""
    try:
        # Parse date
        travel_date = datetime.datetime.fromisoformat(travel_date_str).date()

        # Get weather for all destinations
        weather_client = WeatherMCPClient()
        comparison = []

        for destination in destinations:
            try:
                forecast = await weather_client.get_forecast(
                    city=destination,
                    days=5  # Get a few days around the travel date
                )

                # Find the forecast for the travel date
                travel_day = None
                for day in forecast["daily"]:
                    if day["date"] == travel_date.isoformat():
                        travel_day = day
                        break

                if travel_day:
                    comparison.append({
                        "destination": destination,
                        "temperature": travel_day["temp_avg"],
                        "weather": travel_day["weather"]["main"],
                        "description": travel_day["weather"]["description"],
                        "humidity": travel_day["humidity_avg"],
                        "is_rainy": travel_day["weather"]["main"] in ["Rain", "Thunderstorm", "Drizzle"],
                        "is_clear": travel_day["weather"]["main"] in ["Clear", "Sunny"]
                    })
                else:
                    comparison.append({
                        "destination": destination,
                        "error": "No forecast available for the specified date"
                    })

            except Exception as e:
                comparison.append({
                    "destination": destination,
                    "error": str(e)
                })

        # Sort by weather preference (clear days first, then by temperature)
        comparison.sort(key=lambda x: (
            -1 if x.get("is_clear", False) else 0,
            1 if x.get("is_rainy", False) else 0,
            -abs(x.get("temperature", 0) - 23)  # Sort by closeness to ideal temp (23°C)
        ))

        return {
            "travel_date": travel_date.isoformat(),
            "destinations_by_weather": comparison
        }

    except Exception as e:
        return {"error": f"Error comparing destinations: {str(e)}"}
```

This helps travelers:

- Compare multiple potential destinations for the same dates
- Choose destinations with the most favorable weather
- Make informed decisions between multiple travel options
- Optimize their travel experience based on weather preferences

## Deployment Strategy

The Weather MCP Server can be deployed using Docker, following TripSage's standard deployment pattern:

```dockerfile
# Dockerfile.weather-mcp
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/mcp/base_mcp_server.py src/mcp/base_mcp_server.py
COPY src/mcp/weather/ src/mcp/weather/
COPY src/utils/ src/utils/
COPY src/cache/ src/cache/

# Set environment variables
ENV PYTHONPATH=/app
ENV WEATHER_MCP_SERVER_PORT=8003
ENV OPENWEATHERMAP_API_KEY=${OPENWEATHERMAP_API_KEY}

# Expose port
EXPOSE 8003

# Run the server
CMD ["python", "-m", "src.mcp.weather.server"]
```

## Testing Strategy

Comprehensive testing should be implemented for the Weather MCP Server:

```python
# src/mcp/weather/tests/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.mcp.weather.client import WeatherMCPClient, WeatherService

@pytest.fixture
def weather_client():
    """Create a weather client for testing."""
    return WeatherMCPClient("http://test-server")

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    server_mock = AsyncMock()
    server_mock.invoke_tool = AsyncMock()
    return server_mock

@pytest.mark.asyncio
async def test_get_current_weather(weather_client, mock_server):
    """Test get_current_weather method."""
    # Setup mock
    with patch.object(weather_client, 'call_tool', new_callable=AsyncMock) as mock_call:
        # Create mock response
        mock_response = {
            "temperature": 22.5,
            "feels_like": 21.8,
            "humidity": 65,
            "weather": {
                "main": "Clear",
                "description": "clear sky"
            },
            "location": {
                "name": "Paris",
                "country": "FR"
            }
        }

        mock_call.return_value = mock_response

        # Call method
        result = await weather_client.get_current_weather(city="Paris")

        # Assertions
        assert result == mock_response
        mock_call.assert_called_once_with(
            "get_current_weather",
            {"city": "Paris"},
            skip_cache=False
        )

@pytest.mark.asyncio
async def test_analyze_weather_for_destination():
    """Test analyze_weather_for_destination method."""
    # Create WeatherService with mocked client
    client = WeatherMCPClient()
    weather_service = WeatherService(client)

    # Setup mocks
    with patch.object(client, 'get_forecast') as mock_forecast, \
         patch.object(client, 'get_travel_recommendation') as mock_recommendation:

        # Mock responses
        mock_forecast.return_value = {
            "location": {
                "name": "Paris",
                "country": "FR"
            },
            "daily": [
                {
                    "date": "2025-05-15",
                    "temp_min": 18.5,
                    "temp_max": 25.2,
                    "temp_avg": 22.1,
                    "humidity_avg": 60,
                    "weather": {
                        "main": "Clear",
                        "description": "clear sky"
                    }
                },
                {
                    "date": "2025-05-16",
                    "temp_min": 17.8,
                    "temp_max": 24.5,
                    "temp_avg": 21.5,
                    "humidity_avg": 65,
                    "weather": {
                        "main": "Clouds",
                        "description": "scattered clouds"
                    }
                }
            ]
        }

        mock_recommendation.return_value = {
            "recommendations": {
                "summary": "Current conditions: 22.1°C, Clear",
                "clothing": ["Light clothing suitable for warm weather"],
                "activities": ["Weather is suitable for outdoor activities"]
            }
        }

        # Call method
        result = await weather_service.analyze_weather_for_destination(
            destination="Paris",
            start_date=datetime.now().date(),
            end_date=datetime.now().date()
        )

        # Assertions
        assert "destination" in result
        assert result["destination"] == "Paris"
        assert "weather_summary" in result
        assert "recommendations" in result
```

## Conclusion

Our FastMCP 2.0 implementation of the Weather MCP Server for TripSage provides a robust solution for weather data integration that:

1. Maintains consistent use of FastMCP 2.0 across all MCP implementations
2. Integrates directly with OpenWeatherMap for reliable weather data
3. Adds TripSage-specific functionality like travel recommendations and weather-based itinerary planning
4. Works seamlessly with both Claude Desktop and OpenAI Agents SDK
5. Provides essential weather functionality for travel planning applications

This implementation ensures that TripSage can provide accurate, timely weather information to help travelers make informed decisions about destinations, activities, and packing requirements, enhancing the overall quality of their travel plans.
