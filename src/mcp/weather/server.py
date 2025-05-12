"""
Weather MCP Server implementation for TripSage.

This module provides weather information services for the
TripSage travel planning system using the FastMCP 2.0 framework.
"""

from typing import Any, Dict, List, Optional

from ...utils.error_handling import APIError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..fastmcp import FastMCPServer, create_tool
from .api_client import WeatherLocation, get_weather_api_client

logger = get_module_logger(__name__)


# Location model now imported from api_client


# API clients are now imported from api_client


class WeatherMCPServer(FastMCPServer):
    """Weather MCP Server for TripSage using FastMCP 2.0."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8003):
        """Initialize the Weather MCP Server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        super().__init__(
            name="Weather",
            description="Weather information service for TripSage travel planning",
            version="1.0.0",
            host=host,
            port=port,
        )

        # Initialize API clients
        self.weather_api = get_weather_api_client()

        # Register tools
        self._register_tools()

        logger.info("Initialized Weather MCP Server")

    def _register_tools(self) -> None:
        """Register all weather-related tools."""
        # Current weather tool
        self.register_fast_tool(
            create_tool(
                name="get_current_weather",
                description="Get current weather conditions for a location",
                input_schema={
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number", "description": "Latitude coordinate"},
                        "lon": {
                            "type": "number",
                            "description": "Longitude coordinate",
                        },
                        "city": {
                            "type": "string",
                            "description": "City name (e.g., 'Paris')",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code (e.g., 'FR' for France)",
                        },
                    },
                    "anyOf": [{"required": ["lat", "lon"]}, {"required": ["city"]}],
                },
                handler=self._get_current_weather,
                output_schema={
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number"},
                        "feels_like": {"type": "number"},
                        "temp_min": {"type": "number"},
                        "temp_max": {"type": "number"},
                        "humidity": {"type": "number"},
                        "pressure": {"type": "number"},
                        "wind_speed": {"type": "number"},
                        "wind_direction": {"type": "number"},
                        "clouds": {"type": "number"},
                        "weather": {"type": "object"},
                        "location": {"type": "object"},
                        "timestamp": {"type": "number"},
                        "source": {"type": "string"},
                    },
                },
                examples=[
                    {
                        "input": {"city": "Paris", "country": "FR"},
                        "output": {
                            "temperature": 22.5,
                            "feels_like": 21.8,
                            "temp_min": 20.1,
                            "temp_max": 24.2,
                            "humidity": 65,
                            "pressure": 1013,
                            "wind_speed": 3.5,
                            "wind_direction": 270,
                            "clouds": 20,
                            "weather": {
                                "id": 800,
                                "main": "Clear",
                                "description": "clear sky",
                                "icon": "01d",
                            },
                            "location": {
                                "name": "Paris",
                                "country": "FR",
                                "lat": 48.8566,
                                "lon": 2.3522,
                                "timezone": 7200,
                            },
                            "timestamp": 1686571200,
                            "source": "OpenWeatherMap",
                        },
                    }
                ],
            )
        )

        # Forecast tool
        self.register_fast_tool(
            create_tool(
                name="get_forecast",
                description="Get weather forecast for a location",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                                "city": {"type": "string"},
                                "country": {"type": "string"},
                            },
                            "anyOf": [
                                {"required": ["lat", "lon"]},
                                {"required": ["city"]},
                            ],
                        },
                        "days": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 16,
                            "default": 5,
                            "description": "Number of forecast days",
                        },
                    },
                    "required": ["location"],
                },
                handler=self._get_forecast,
                output_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "object"},
                        "daily": {"type": "array"},
                        "source": {"type": "string"},
                    },
                },
            )
        )

        # Travel recommendation tool
        self.register_fast_tool(
            create_tool(
                name="get_travel_recommendation",
                description="Get travel recommendations based on weather conditions",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                                "city": {"type": "string"},
                                "country": {"type": "string"},
                            },
                            "anyOf": [
                                {"required": ["lat", "lon"]},
                                {"required": ["city"]},
                            ],
                        },
                        "start_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Trip start date (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Trip end date (YYYY-MM-DD)",
                        },
                        "activities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Planned activities (e.g., ['hiking', 'sightseeing'])"
                            ),
                        },
                    },
                    "required": ["location"],
                },
                handler=self._get_travel_recommendation,
                output_schema={
                    "type": "object",
                    "properties": {
                        "current_weather": {"type": "object"},
                        "forecast": {"type": "object"},
                        "recommendations": {"type": "object"},
                    },
                },
            )
        )

    async def _get_current_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current weather conditions for a location.

        Args:
            params: Tool parameters
                - lat: Latitude coordinate (optional if city is provided)
                - lon: Longitude coordinate (optional if city is provided)
                - city: City name (optional if lat/lon are provided)
                - country: Country code (optional)

        Returns:
            Dictionary with current weather information

        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        try:
            # Validate parameters and create a location object
            try:
                location = WeatherLocation(**params)
            except Exception as e:
                raise ValueError(f"Invalid parameters: {str(e)}") from e

            # Call OpenWeatherMap API
            current_weather = await self.weather_api.get_current_weather(location)

            # Convert to dictionary
            return current_weather.model_dump()

        except Exception as e:
            logger.error("Error in get_current_weather: %s", str(e))
            if isinstance(e, APIError):
                raise ValueError(f"Weather API error: {e.message}") from e
            else:
                raise ValueError(f"Error getting current weather: {str(e)}") from e

    async def _get_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast for a location.

        Args:
            params: Tool parameters
                - location: Location object with either lat/lon or city/country
                - days: Number of forecast days (default: 5)

        Returns:
            Dictionary with forecast information

        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        try:
            # Extract location parameters
            location_data = params.get("location", {})
            days = params.get("days", 5)

            # Validate location parameters
            try:
                location = WeatherLocation(**location_data)
            except Exception as e:
                raise ValueError(f"Invalid location parameters: {str(e)}") from e

            # Call weather API
            forecast = await self.weather_api.get_forecast(location, days=days)

            # Convert to dictionary
            return forecast.model_dump()

        except Exception as e:
            logger.error("Error in get_forecast: %s", str(e))
            if isinstance(e, APIError):
                raise ValueError(f"Weather API error: {e.message}") from e
            else:
                raise ValueError(f"Error getting forecast: {str(e)}") from e

    async def _get_travel_recommendation(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get travel recommendations based on weather conditions.

        Args:
            params: Tool parameters
                - location: Location object with either lat/lon or city/country
                - start_date: Trip start date (optional)
                - end_date: Trip end date (optional)
                - activities: Planned activities (optional)

        Returns:
            Dictionary with travel recommendations

        Raises:
            ValueError: If neither coordinates nor city is provided
        """
        try:
            # Extract parameters
            location_data = params.get("location", {})
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            activities = params.get("activities", [])

            # Validate location parameters
            try:
                location = WeatherLocation(**location_data)
            except Exception as e:
                raise ValueError(f"Invalid location parameters: {str(e)}") from e

            # Get current weather and forecast
            current = await self.weather_api.get_current_weather(location)
            # Get a week of forecast data
            forecast = await self.weather_api.get_forecast(location, days=7)

            # Generate recommendations based on weather
            recommendations = self._generate_recommendations(
                current.model_dump(),
                forecast.model_dump(),
                start_date,
                end_date,
                activities,
            )

            return {
                "current_weather": current.model_dump(),
                "forecast": forecast.model_dump(),
                "recommendations": recommendations,
            }
        except Exception as e:
            logger.error("Error in get_travel_recommendation: %s", str(e))
            if isinstance(e, APIError):
                raise ValueError(f"Weather API error: {e.message}") from e
            else:
                raise ValueError(
                    f"Error generating travel recommendations: {str(e)}"
                ) from e

    def _generate_recommendations(
        self,
        current: Dict[str, Any],
        forecast: Dict[str, Any],
        start_date: Optional[str],
        end_date: Optional[str],
        activities: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Generate travel recommendations based on weather data.

        Args:
            current: Current weather data
            forecast: Forecast data
            start_date: Trip start date
            end_date: Trip end date
            activities: Desired activities

        Returns:
            Travel recommendations
        """
        # Get the weather condition and temperature
        weather_condition = current["weather"]["main"]
        temperature = current["temperature"]

        # Define weather categories
        outdoor_friendly = ["Clear", "Clouds", "Few clouds", "Partly cloudy"]
        indoor_recommended = ["Rain", "Thunderstorm", "Drizzle", "Snow", "Mist", "Fog"]

        # Define temperature categories
        cold = temperature < 10
        cool = 10 <= temperature < 20
        moderate = 20 <= temperature < 25
        warm = 25 <= temperature < 30
        hot = temperature >= 30

        # Generate clothing recommendations
        clothing_recommendations = []
        if cold:
            clothing_recommendations.extend(
                [
                    "Pack heavy winter clothing, including a coat, gloves, and a hat.",
                    "Layer clothing for insulation and flexibility.",
                    "Bring thermal undergarments for extra warmth.",
                ]
            )
        elif cool:
            clothing_recommendations.extend(
                [
                    "Pack a light jacket or sweater for cooler periods.",
                    "Consider bringing long-sleeved shirts and pants.",
                    "A light scarf might be useful for windy conditions.",
                ]
            )
        elif moderate:
            clothing_recommendations.extend(
                [
                    "Pack a mix of short and long-sleeved shirts.",
                    "Light sweaters or cardigans for evenings.",
                    "Comfortable walking shoes for exploration.",
                ]
            )
        elif warm:
            clothing_recommendations.extend(
                [
                    "Pack lightweight, breathable clothing.",
                    "Bring a hat and sunglasses for sun protection.",
                    "Consider moisture-wicking fabrics for comfort.",
                ]
            )
        elif hot:
            clothing_recommendations.extend(
                [
                    "Pack very lightweight, loose-fitting clothing.",
                    "Bring a hat, sunglasses, and sunscreen.",
                    "Consider UV-protective clothing for extended outdoor activities.",
                ]
            )

        # Generate activity recommendations
        activity_recommendations = []
        if weather_condition in outdoor_friendly:
            activity_recommendations.extend(
                [
                    "Weather is suitable for outdoor activities.",
                    "Consider parks, hiking, or sightseeing.",
                    "Open-air restaurants and cafes would be enjoyable.",
                ]
            )
        else:
            activity_recommendations.extend(
                [
                    "Weather may be challenging for outdoor activities.",
                    "Consider museums, galleries, or indoor attractions.",
                    "Have backup indoor plans available.",
                ]
            )

        # Add activity-specific recommendations if activities were specified
        if activities:
            activity_specific = []
            for activity in activities:
                if activity.lower() == "hiking":
                    if weather_condition in outdoor_friendly and not hot:
                        activity_specific.append("Good conditions for hiking.")
                    else:
                        activity_specific.append(
                            "Consider rescheduling hiking due to weather."
                        )

                elif activity.lower() == "beach":
                    if weather_condition == "Clear" and (warm or hot):
                        activity_specific.append("Excellent beach weather.")
                    else:
                        activity_specific.append("Not ideal beach conditions.")

                elif activity.lower() in ["museum", "shopping", "indoor"]:
                    if weather_condition in indoor_recommended:
                        activity_specific.append(
                            f"Perfect weather for {activity.lower()} activities."
                        )
                    else:
                        activity_specific.append(
                            "Good option, but consider outdoor activities "
                            "given the nice weather."
                        )

            activity_recommendations.extend(activity_specific)

        # Forecast-based recommendations
        forecast_recommendations = []
        for day in forecast["daily"][:5]:  # Look at the next 5 days
            date = day["date"]
            condition = day["weather"]["main"]
            max_temp = day["temp_max"]

            if condition in outdoor_friendly and max_temp > 20:
                forecast_recommendations.append(
                    f"Good outdoor weather on {date}. Plan outdoor activities."
                )
            elif condition in indoor_recommended:
                forecast_recommendations.append(
                    f"Possible {condition.lower()} on {date}. Plan indoor activities."
                )

        return {
            "summary": f"Current conditions: {temperature}°C, {weather_condition}",
            "clothing": clothing_recommendations,
            "activities": activity_recommendations,
            "forecast_based": forecast_recommendations,
        }


def create_server(
    host: str = settings.weather_mcp.endpoint.split("://")[1].split(":")[0]
    if "://" in settings.weather_mcp.endpoint
    else "0.0.0.0",
    port: int = int(settings.weather_mcp.endpoint.split(":")[-1])
    if ":" in settings.weather_mcp.endpoint
    else 8003,
):
    """Create and return a Weather MCP Server instance.

    Args:
        host: Host to bind to
        port: Port to listen on

    Returns:
        Weather MCP Server instance
    """
    return WeatherMCPServer(host=host, port=port)


if __name__ == "__main__":
    # Create and run the server
    server = create_server()
    server.run()
