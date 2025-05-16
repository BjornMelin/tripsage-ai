"""
Weather-related function tools for TripSage.

This module provides OpenAI Agents SDK function tools for weather operations,
allowing agents to get current weather, forecasts, and weather-based
travel recommendations using the Weather MCP through the abstraction layer.
"""

from typing import Any, Dict, List, Optional

from agents import function_tool
from tripsage.mcp_abstraction.manager import mcp_manager
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
    """Get current weather conditions for a location.

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
        # Call the Weather MCP through the abstraction layer
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
    """Get weather forecast for a location.

    Args:
        city: City name (e.g., 'Paris')
        country: Country code (e.g., 'FR')
        lat: Latitude coordinate (optional if city is provided)
        lon: Longitude coordinate (optional if city is provided)
        days: Number of forecast days (default: 5)

    Returns:
        Dictionary with forecast information
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

    # Validate days parameter
    days = max(1, min(16, days))  # Ensure days is between 1 and 16

    try:
        # Call the Weather MCP through the abstraction layer
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

        # Format daily summaries for better readability
        formatted_result = f"Weather forecast for {result.location.get('name', '')}:\n"
        for i, day in enumerate(result.forecast[:5]):  # Limit to first 5 days
            formatted_result += (
                f"Day {i + 1}: {day.weather.description}, "
                f"High: {day.temp_max}°C, Low: {day.temp_min}°C\n"
            )

        return {
            "location": result.location,
            "timezone": result.timezone,
            "forecast": [
                {
                    "date": day.date,
                    "temperature": {
                        "day": day.temperature,
                        "min": day.temp_min,
                        "max": day.temp_max,
                        "night": day.temp_night,
                        "evening": day.temp_evening,
                        "morning": day.temp_morning,
                    },
                    "feels_like": {
                        "day": day.feels_like,
                        "night": day.feels_like_night,
                        "evening": day.feels_like_evening,
                        "morning": day.feels_like_morning,
                    },
                    "humidity": day.humidity,
                    "pressure": day.pressure,
                    "wind_speed": day.wind_speed,
                    "wind_direction": day.wind_direction,
                    "clouds": day.clouds,
                    "weather": {
                        "id": day.weather.id,
                        "main": day.weather.main,
                        "description": day.weather.description,
                        "icon": day.weather.icon,
                    },
                    "rain": day.rain,
                    "snow": day.snow,
                    "uvi": day.uvi,
                }
                for day in result.forecast
            ],
            "source": result.source,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting weather forecast: {str(e)}")
        return {"error": f"Failed to get weather forecast: {str(e)}"}


@function_tool
@with_error_handling
async def get_weather_recommendation_tool(
    city: Optional[str] = None,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    activity_type: str = "general",
) -> Dict[str, Any]:
    """Get weather-based travel recommendations for a location.

    Args:
        city: City name (e.g., 'Paris')
        country: Country code (e.g., 'FR')
        lat: Latitude coordinate (optional if city is provided)
        lon: Longitude coordinate (optional if city is provided)
        activity_type: Type of activity
            (e.g., 'outdoor', 'sightseeing', 'beach', 'hiking')

    Returns:
        Dictionary with weather recommendations
    """
    # Get current weather first
    weather_result = await get_current_weather_tool(
        city=city, country=country, lat=lat, lon=lon
    )

    if "error" in weather_result:
        return weather_result

    temperature = weather_result["temperature"]
    humidity = weather_result["humidity"]
    wind_speed = weather_result["wind_speed"]
    weather_main = weather_result["weather"]["main"]
    weather_desc = weather_result["weather"]["description"]

    # Basic recommendation logic
    recommendations = []
    suitable_activities = []
    warnings = []

    # Temperature-based recommendations
    if temperature < 0:
        recommendations.append("Very cold weather - wear heavy winter clothing")
        suitable_activities.extend(["winter sports", "indoor activities"])
        warnings.append("Risk of frostbite in exposed skin")
    elif temperature < 10:
        recommendations.append("Cool weather - bring warm layers")
        suitable_activities.extend(["hiking", "city tours", "museums"])
    elif temperature < 20:
        recommendations.append("Mild weather - light jacket recommended")
        suitable_activities.extend(["outdoor sightseeing", "cycling", "walking tours"])
    elif temperature < 30:
        recommendations.append("Pleasant weather - comfortable clothing")
        suitable_activities.extend(["all outdoor activities", "beach", "water sports"])
    else:
        recommendations.append("Hot weather - stay hydrated and use sun protection")
        suitable_activities.extend(["water activities", "indoor attractions"])
        warnings.append("Heat exposure risk - avoid midday sun")

    # Weather conditions
    if weather_main == "Rain":
        recommendations.append("Rainy conditions - bring waterproof gear")
        warnings.append("Outdoor activities may be affected")
        suitable_activities = ["museums", "indoor shopping", "covered attractions"]
    elif weather_main == "Snow":
        recommendations.append("Snowy conditions - wear appropriate footwear")
        suitable_activities = ["winter sports", "indoor activities"]
        warnings.append("Travel may be affected by snow")
    elif weather_main == "Thunderstorm":
        recommendations.append("Storms expected - avoid outdoor activities")
        warnings.append("Dangerous weather conditions")
        suitable_activities = ["indoor activities only"]

    # Activity-specific recommendations
    activity_recommendations = {
        "beach": {
            "min_temp": 20,
            "ideal_temp": 25,
            "max_wind": 30,
            "avoid_weather": ["Rain", "Thunderstorm"],
        },
        "hiking": {
            "min_temp": 5,
            "ideal_temp": 18,
            "max_wind": 40,
            "avoid_weather": ["Thunderstorm", "Heavy Rain"],
        },
        "sightseeing": {
            "min_temp": 0,
            "ideal_temp": 20,
            "max_wind": 50,
            "avoid_weather": ["Thunderstorm"],
        },
        "outdoor": {
            "min_temp": 10,
            "ideal_temp": 22,
            "max_wind": 35,
            "avoid_weather": ["Thunderstorm", "Heavy Rain"],
        },
    }

    activity_info = activity_recommendations.get(
        activity_type, activity_recommendations["general"]
    )

    # Check if activity is suitable
    activity_suitable = True
    unsuitable_reasons = []

    if temperature < activity_info.get("min_temp", -10):
        activity_suitable = False
        unsuitable_reasons.append("too cold")
    if wind_speed > activity_info.get("max_wind", 100):
        activity_suitable = False
        unsuitable_reasons.append("too windy")
    if weather_main in activity_info.get("avoid_weather", []):
        activity_suitable = False
        unsuitable_reasons.append(f"unsuitable weather ({weather_main.lower()})")

    location_name = weather_result["location"]["name"]
    recommendation_text = f"Weather recommendation for {location_name}:\n"
    recommendation_text += f"Current conditions: {temperature}°C, {weather_desc}\n"
    if activity_suitable:
        activity_name = activity_type.capitalize()
        recommendation_text += f"✓ {activity_name} activities are recommended\n"
    else:
        activity_name = activity_type.capitalize()
        reasons = ", ".join(unsuitable_reasons)
        not_recommended = f"not recommended: {reasons}"
        recommendation_text += f"✗ {activity_name} activities {not_recommended}\n"
    recommendation_text += "\nRecommendations:\n"
    for rec in recommendations:
        recommendation_text += f"- {rec}\n"
    if warnings:
        recommendation_text += "\nWarnings:\n"
        for warning in warnings:
            recommendation_text += f"⚠️ {warning}\n"

    return {
        "location": weather_result["location"],
        "activity_type": activity_type,
        "suitable_for_activity": activity_suitable,
        "unsuitable_reasons": unsuitable_reasons,
        "recommendations": recommendations,
        "suitable_activities": suitable_activities,
        "warnings": warnings,
        "current_conditions": {
            "temperature": temperature,
            "weather": weather_main,
            "description": weather_desc,
            "humidity": humidity,
            "wind_speed": wind_speed,
        },
        "formatted": recommendation_text,
    }


@function_tool
@with_error_handling
async def get_destination_weather_tool(
    destination: str, arrival_date: Optional[str] = None
) -> Dict[str, Any]:
    """Get weather information for a travel destination.

    Args:
        destination: Travel destination name (e.g., 'Paris, France')
        arrival_date: Expected arrival date (YYYY-MM-DD format)

    Returns:
        Dictionary with destination weather information
    """
    logger.info(f"Getting weather for destination: {destination}")

    # Parse destination to extract city and country
    parts = destination.split(",")
    city = parts[0].strip()
    country = parts[1].strip() if len(parts) > 1 else None

    # Get current weather
    current_weather = await get_current_weather_tool(city=city, country=country)

    # Get forecast if arrival date is specified
    forecast = None
    if arrival_date:
        forecast_result = await get_weather_forecast_tool(city=city, country=country)
        if "error" not in forecast_result:
            forecast = forecast_result

    # Prepare response
    result = {
        "destination": destination,
        "current_weather": current_weather,
        "arrival_date": arrival_date,
    }

    if forecast:
        result["forecast"] = forecast
        # Try to find forecast for arrival date
        for day in forecast.get("forecast", []):
            if day["date"].startswith(arrival_date):
                result["arrival_day_forecast"] = day
                break

    return result


@function_tool
@with_error_handling
async def get_trip_weather_summary_tool(
    destinations: List[str], dates: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get weather summary for multiple trip destinations.

    Args:
        destinations: List of destination names
        dates: Optional list of dates corresponding to each destination

    Returns:
        Dictionary with weather summary for all destinations
    """
    logger.info(f"Getting weather summary for {len(destinations)} destinations")

    results = []
    for i, destination in enumerate(destinations):
        date = dates[i] if dates and i < len(dates) else None
        weather_info = await get_destination_weather_tool(
            destination=destination, arrival_date=date
        )
        results.append(weather_info)

    # Create summary
    summary = {
        "destinations": destinations,
        "weather_data": results,
        "overall_summary": _create_trip_weather_summary(results),
    }

    return summary


def _create_trip_weather_summary(results: List[Dict[str, Any]]) -> str:
    """Create a text summary of weather conditions across all destinations."""
    summary_parts = []
    summary_parts.append(f"Weather summary for {len(results)} destinations:\n")

    for result in results:
        destination = result["destination"]
        current = result.get("current_weather", {})

        if "error" in current:
            summary_parts.append(f"• {destination}: Unable to fetch weather data\n")
            continue

        # Get the formatted weather info if available
        formatted = current.get("formatted", "")

        summary_parts.append(f"• {destination}: {formatted}\n")

        # Add arrival day forecast if available
        arrival_forecast = result.get("arrival_day_forecast")
        if arrival_forecast:
            arrival_date = result.get("arrival_date", "")
            day_temp = arrival_forecast.get("temperature", {}).get("day", "N/A")
            day_desc = arrival_forecast.get("weather", {}).get("description", "N/A")
            summary_parts.append(
                f"  Forecast for {arrival_date}: {day_desc}, {day_temp}°C\n"
            )

    return "".join(summary_parts)
