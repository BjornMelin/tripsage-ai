"""
Weather-related function tools using the MCP abstraction layer.

This module demonstrates how to refactor existing tools to use the unified
MCP abstraction layer instead of direct client instances.
"""

from typing import Any, Dict, Optional

from agents import function_tool
from tripsage.mcp_abstraction import mcp_manager
from tripsage.tools.schemas.weather import WeatherLocation
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
@with_error_handling
async def get_current_weather_tool(
    city: Optional[str] = None,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    """Get current weather conditions for a location using MCP abstraction layer.

    Args:
        city: City name (e.g., 'Paris')
        country: Country code (e.g., 'FR')
        lat: Latitude coordinate (optional if city is provided)
        lon: Longitude coordinate (optional if city is provided)

    Returns:
        Dictionary with current weather information
    """
    # Validate location parameters
    try:
        location = WeatherLocation(
            city=city,
            country=country,
            lat=lat,
            lon=lon,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting current weather for location: {location.model_dump()}")

    try:
        # Use the MCP manager to invoke the weather service
        # Note: We're using standardized method names here
        result = await mcp_manager.invoke(
            mcp_name="weather",
            method_name="get_current_weather",
            params={
                "city": location.city,
                "country": location.country,
                "lat": location.lat,
                "lon": location.lon,
            },
        )

        # The result should be similar to the original implementation
        # Format the result for better readability
        formatted_result = (
            f"Current weather in {result.location.get('name', '')}: "
            f"{result.temperature}°C, {result.weather.description}. "
            f"Feels like: {result.feels_like}°C. "
            f"Wind: {result.wind_speed} m/s."
        )

        return {
            "temperature": result.temperature,
            "feels_like": result.feels_like,
            "temp_min": result.temp_min,
            "temp_max": result.temp_max,
            "humidity": result.humidity,
            "pressure": result.pressure,
            "wind_speed": result.wind_speed,
            "wind_direction": result.wind_direction,
            "clouds": result.clouds,
            "weather": {
                "id": result.weather.id,
                "main": result.weather.main,
                "description": result.weather.description,
                "icon": result.weather.icon,
            },
            "location": result.location,
            "timestamp": result.timestamp,
            "source": result.source,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting current weather: {str(e)}")
        return {"error": f"Failed to get current weather: {str(e)}"}


@function_tool
@with_error_handling
async def get_weather_forecast_tool(
    city: Optional[str] = None,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    days: int = 5,
) -> Dict[str, Any]:
    """Get weather forecast for a location using MCP abstraction layer.

    Args:
        city: City name (e.g., 'Paris')
        country: Country code (e.g., 'FR')
        lat: Latitude coordinate (optional if city is provided)
        lon: Longitude coordinate (optional if city is provided)
        days: Number of days for forecast (default: 5)

    Returns:
        Dictionary with weather forecast information
    """
    # Validate location parameters
    try:
        location = WeatherLocation(
            city=city,
            country=country,
            lat=lat,
            lon=lon,
        )
    except ValueError as e:
        return {"error": str(e)}

    logger.info(f"Getting weather forecast for location: {location.model_dump()}")

    try:
        # Use the MCP manager to invoke the weather service
        result = await mcp_manager.invoke(
            mcp_name="weather",
            method_name="get_forecast",
            params={
                "city": location.city,
                "country": location.country,
                "lat": location.lat,
                "lon": location.lon,
                "days": days,
            },
        )

        # Format the result for better readability
        forecast_summary = []
        for day in result.forecast:
            summary = (
                f"{day.date}: {day.weather.description}. "
                f"Temp: {day.temperature_min}°C - {day.temperature_max}°C"
            )
            forecast_summary.append(summary)

        return {
            "location": result.location,
            "forecast": [
                {
                    "date": day.date,
                    "temperature_min": day.temperature_min,
                    "temperature_max": day.temperature_max,
                    "weather": {
                        "id": day.weather.id,
                        "main": day.weather.main,
                        "description": day.weather.description,
                        "icon": day.weather.icon,
                    },
                    "humidity": day.humidity,
                    "pressure": day.pressure,
                    "wind_speed": day.wind_speed,
                    "clouds": day.clouds,
                    "precipitation": day.precipitation,
                }
                for day in result.forecast
            ],
            "timestamp": result.timestamp,
            "source": result.source,
            "formatted": "\n".join(forecast_summary),
        }
    except Exception as e:
        logger.error(f"Error getting weather forecast: {str(e)}")
        return {"error": f"Failed to get weather forecast: {str(e)}"}
