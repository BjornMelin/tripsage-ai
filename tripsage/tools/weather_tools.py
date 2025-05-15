"""
Weather-related function tools for TripSage.

This module provides OpenAI Agents SDK function tools for weather operations,
allowing agents to get current weather, forecasts, and weather-based
travel recommendations using the Weather MCP.
"""

from typing import Any, Dict, List, Optional

from agents import function_tool
from tripsage.clients.weather import WeatherMCPClient
from tripsage.tools.schemas.weather import (
    WeatherLocation,
)
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

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Call the Weather MCP client
        result = await client.get_current_weather(
            city=location.city,
            country=location.country,
            lat=location.lat,
            lon=location.lon,
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
    finally:
        # Ensure client is disconnected
        await client.disconnect()


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

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Call the Weather MCP client
        result = await client.get_forecast(
            city=location.city,
            country=location.country,
            lat=location.lat,
            lon=location.lon,
            days=days,
        )

        # Create a summary of the forecast
        daily_summaries: List[str] = []
        for day in result.daily:
            daily_summaries.append(
                f"{day.date}: {day.temp_min}°C to {day.temp_max}°C, "
                f"{day.weather.description}"
            )

        formatted_result = (
            f"Weather forecast for {result.location.get('name', '')}:\n"
            f"{chr(10).join(daily_summaries)}"
        )

        return {
            "location": result.location,
            "daily": [day.model_dump() for day in result.daily],
            "source": result.source,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting weather forecast: {str(e)}")
        return {"error": f"Failed to get weather forecast: {str(e)}"}
    finally:
        # Ensure client is disconnected
        await client.disconnect()


@function_tool
@with_error_handling
async def get_travel_recommendation_tool(
    city: Optional[str] = None,
    country: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get travel recommendations based on weather conditions.

    Args:
        city: City name (e.g., 'Paris')
        country: Country code (e.g., 'FR')
        lat: Latitude coordinate (optional if city is provided)
        lon: Longitude coordinate (optional if city is provided)
        start_date: Trip start date (YYYY-MM-DD)
        end_date: Trip end date (YYYY-MM-DD)
        activities: Planned activities (e.g., ['hiking', 'sightseeing'])

    Returns:
        Dictionary with travel recommendations
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

    logger.info(f"Getting travel recommendations for location: {location.model_dump()}")

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Call the Weather MCP client
        result = await client.get_travel_recommendation(
            city=location.city,
            country=location.country,
            lat=location.lat,
            lon=location.lon,
            start_date=start_date,
            end_date=end_date,
            activities=activities,
        )

        # Format the recommendations for better readability
        recommendations = result.recommendations
        summary = recommendations.get("summary", "")
        clothing_tips = recommendations.get("clothing", [])
        activity_tips = recommendations.get("activities", [])
        forecast_tips = recommendations.get("forecast_based", [])

        formatted_result = f"{summary}\n\nClothing recommendations:\n"
        for tip in clothing_tips:
            formatted_result += f"- {tip}\n"

        formatted_result += "\nActivity recommendations:\n"
        for tip in activity_tips:
            formatted_result += f"- {tip}\n"

        if forecast_tips:
            formatted_result += "\nForecast-based recommendations:\n"
            for tip in forecast_tips:
                formatted_result += f"- {tip}\n"

        return {
            "current_weather": result.current_weather,
            "forecast": result.forecast,
            "recommendations": result.recommendations,
            "formatted": formatted_result,
        }
    except Exception as e:
        logger.error(f"Error getting travel recommendations: {str(e)}")
        return {"error": f"Failed to get travel recommendations: {str(e)}"}
    finally:
        # Ensure client is disconnected
        await client.disconnect()


@function_tool
@with_error_handling
async def get_destination_weather_tool(destination: str) -> Dict[str, Any]:
    """Get current weather for a travel destination.

    Args:
        destination: Travel destination (e.g., "Paris" or "Paris, FR")

    Returns:
        Dictionary containing current weather information
    """
    logger.info(f"Getting weather for destination: {destination}")

    # Parse city and country from destination string
    parts = [part.strip() for part in destination.split(",")]
    city = parts[0]
    country = parts[1] if len(parts) > 1 else None

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Call the Weather MCP client
        result = await client.get_current_weather(
            city=city,
            country=country,
        )

        # Format the result
        formatted_result = (
            f"Weather in {destination}: {result.temperature}°C, "
            f"{result.weather.description}. "
            f"Feels like: {result.feels_like}°C. "
            f"Wind: {result.wind_speed} m/s."
        )

        return {
            "destination": destination,
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
        logger.error(f"Error getting destination weather: {str(e)}")
        return {"error": f"Failed to get weather for {destination}: {str(e)}"}
    finally:
        # Ensure client is disconnected
        await client.disconnect()


@function_tool
@with_error_handling
async def get_trip_weather_summary_tool(
    destination: str, start_date: str, end_date: str
) -> Dict[str, Any]:
    """Get a weather summary for a trip period.

    Args:
        destination: Travel destination (e.g., "Paris" or "Paris, FR")
        start_date: Trip start date (YYYY-MM-DD)
        end_date: Trip end date (YYYY-MM-DD)

    Returns:
        Dictionary containing weather summary for the trip period
    """
    logger.info(
        f"Getting trip weather summary for {destination} from "
        f"{start_date} to {end_date}"
    )

    # Parse city and country from destination string
    parts = [part.strip() for part in destination.split(",")]
    city = parts[0]
    country = parts[1] if len(parts) > 1 else None

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Call the Weather MCP client to get forecast
        forecast_result = await client.get_forecast(
            city=city,
            country=country,
            days=16,  # Maximum forecast days
        )

        # Filter daily forecast to trip dates
        trip_days = []
        for day in forecast_result.daily:
            date = day.date
            if start_date <= date <= end_date:
                trip_days.append(day.model_dump())

        # Calculate temperature statistics
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
            max(weather_counts.items(), key=lambda x: x[1]) if weather_counts else None
        )

        # Create summary result
        summary = {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "temperature": {
                "average": sum(avg_temps) / len(avg_temps) if avg_temps else None,
                "min": min(min_temps) if min_temps else None,
                "max": max(max_temps) if max_temps else None,
            },
            "conditions": {
                "most_common": most_common[0] if most_common else None,
                "frequency": most_common[1] / len(trip_days)
                if most_common and trip_days
                else None,
                "breakdown": weather_counts,
            },
            "days": trip_days,
        }

        # Create formatted summary
        trip_length = len(trip_days)
        most_common_condition = most_common[0] if most_common else "unknown"
        avg_temp = summary["temperature"]["average"]
        temp_range = (
            f"{summary['temperature']['min']}°C to {summary['temperature']['max']}°C"
        )

        formatted_result = (
            f"Weather summary for {destination} ({start_date} to {end_date}):\n"
            f"• Trip duration: {trip_length} days\n"
            f"• Average temperature: {avg_temp:.1f}°C (range: {temp_range})\n"
            f"• Most common condition: {most_common_condition} "
            f"({int(weather_counts.get(most_common_condition, 0))} days)\n\n"
            f"Daily breakdown:\n"
        )

        for day in trip_days:
            formatted_result += (
                f"• {day['date']}: {day['temp_min']}°C to {day['temp_max']}°C, "
                f"{day['weather']['description']}\n"
            )

        summary["formatted"] = formatted_result
        return summary

    except Exception as e:
        logger.error(f"Error getting trip weather summary: {str(e)}")
        return {
            "error": f"Failed to get trip weather summary: {str(e)}",
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
        }
    finally:
        # Ensure client is disconnected
        await client.disconnect()


@function_tool
@with_error_handling
async def compare_destinations_weather_tool(
    destinations: List[str], date: Optional[str] = None
) -> Dict[str, Any]:
    """Compare weather across multiple potential destinations.

    Args:
        destinations: List of destinations to compare
        date: Date for comparison (YYYY-MM-DD). If not provided, uses current date.

    Returns:
        Dictionary containing weather comparison results
    """
    logger.info(f"Comparing weather across destinations: {destinations}")

    results = []

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Fetch weather for each destination
        for destination in destinations:
            parts = [part.strip() for part in destination.split(",")]
            city = parts[0]
            country = parts[1] if len(parts) > 1 else None

            try:
                if date:
                    # Get forecast and find the specified date
                    forecast_result = await client.get_forecast(
                        city=city, country=country
                    )

                    # Find the forecast for the specified date
                    date_forecast = None
                    for day in forecast_result.daily:
                        if day.date == date:
                            date_forecast = day
                            break

                    if date_forecast:
                        results.append(
                            {
                                "destination": destination,
                                "date": date,
                                "temperature": {
                                    "average": date_forecast.temp_avg,
                                    "min": date_forecast.temp_min,
                                    "max": date_forecast.temp_max,
                                },
                                "conditions": date_forecast.weather.main,
                                "description": date_forecast.weather.description,
                            }
                        )
                    else:
                        results.append(
                            {
                                "destination": destination,
                                "error": f"No forecast available for {date}",
                            }
                        )
                else:
                    # Get current weather
                    weather_result = await client.get_current_weather(
                        city=city, country=country
                    )

                    results.append(
                        {
                            "destination": destination,
                            "temperature": weather_result.temperature,
                            "feels_like": weather_result.feels_like,
                            "conditions": weather_result.weather.main,
                            "description": weather_result.weather.description,
                        }
                    )
            except Exception as e:
                logger.warning(f"Error getting weather for {destination}: {str(e)}")
                results.append({"destination": destination, "error": str(e)})

        # Rank destinations based on weather (simple temperature-based ranking)
        valid_results = [r for r in results if "error" not in r]
        ranking = None

        if valid_results:
            # Sort by temperature (higher is better)
            if date:
                temp_sorted = sorted(
                    valid_results,
                    key=lambda x: x["temperature"]["average"],
                    reverse=True,
                )
            else:
                temp_sorted = sorted(
                    valid_results,
                    key=lambda x: x["temperature"],
                    reverse=True,
                )

            ranking = [r["destination"] for r in temp_sorted]

        # Create comparison result
        comparison = {
            "destinations": destinations,
            "date": date or "current",
            "results": results,
            "ranking": ranking,
        }

        # Create formatted output
        formatted_result = f"Weather comparison for {len(destinations)} destinations"
        if date:
            formatted_result += f" on {date}:\n\n"
        else:
            formatted_result += " (current weather):\n\n"

        for i, result in enumerate(results):
            formatted_result += f"{i + 1}. {result['destination']}: "

            if "error" in result:
                formatted_result += f"Error: {result['error']}\n"
            else:
                if date:
                    formatted_result += (
                        f"{result['temperature']['average']}°C "
                        f"({result['temperature']['min']}°C to "
                        f"{result['temperature']['max']}°C), "
                        f"{result['description']}\n"
                    )
                else:
                    formatted_result += (
                        f"{result['temperature']}°C, {result['description']}\n"
                    )

        if ranking:
            formatted_result += "\nRanking (based on temperature):\n"
            for i, dest in enumerate(ranking):
                formatted_result += f"{i + 1}. {dest}\n"

        comparison["formatted"] = formatted_result
        return comparison
    finally:
        # Ensure client is disconnected
        await client.disconnect()


@function_tool
@with_error_handling
async def get_optimal_travel_time_tool(
    destination: str, activity_type: str = "general", months_ahead: int = 6
) -> Dict[str, Any]:
    """Get recommendations for the optimal time to travel to a destination.

    Args:
        destination: Travel destination (e.g., "Paris" or "Paris, FR")
        activity_type: Type of activity planned (e.g., 'beach', 'skiing', 'sightseeing')
        months_ahead: How many months ahead to consider

    Returns:
        Dictionary containing optimal travel time recommendations
    """
    logger.info(
        f"Getting optimal travel time for {destination} for {activity_type} activities"
    )

    # Parse city and country from destination string
    parts = [part.strip() for part in destination.split(",")]
    city = parts[0]
    country = parts[1] if len(parts) > 1 else None

    # Get client instance
    client = await WeatherMCPClient.get_instance()

    try:
        # Get travel recommendations
        result = await client.get_travel_recommendation(
            city=city, country=country, activities=[activity_type]
        )

        # Extract information from the recommendations
        recommendations = result.recommendations
        current_weather = result.current_weather

        # Extract the specific activity recommendation
        activity_recs = [
            rec
            for rec in recommendations.get("activities", [])
            if activity_type.lower() in rec.lower()
        ]

        # Analyze forecast-based recommendations
        forecast_recs = recommendations.get("forecast_based", [])
        good_days = [rec for rec in forecast_recs if "Good" in rec]

        # Create a specific recommendation for the activity
        if activity_recs:
            activity_advice = activity_recs[0]
        else:
            activity_advice = (
                "No specific recommendations available for this activity type."
            )

        # Create the result
        response = {
            "destination": destination,
            "activity_type": activity_type,
            "current_weather": current_weather.get("weather", {}).get("main"),
            "current_temp": current_weather.get("temperature"),
            "activity_recommendation": activity_advice,
            "good_weather_days": good_days,
            "forecast_recommendations": forecast_recs,
            "clothing_recommendations": recommendations.get("clothing", []),
        }

        # Create formatted output
        formatted_result = (
            f"Optimal travel recommendations for {activity_type} in {destination}:\n\n"
            f"Current weather: {response['current_weather']}, "
            f"{response['current_temp']}°C\n\n"
            f"Activity recommendation: {activity_advice}\n\n"
            f"Upcoming good weather days:\n"
        )

        for day in good_days:
            formatted_result += f"• {day}\n"

        formatted_result += "\nGeneral recommendations:\n"
        for rec in forecast_recs:
            if rec not in good_days:
                formatted_result += f"• {rec}\n"

        formatted_result += "\nClothing recommendations:\n"
        for item in response["clothing_recommendations"]:
            formatted_result += f"• {item}\n"

        response["formatted"] = formatted_result
        return response

    except Exception as e:
        logger.error(f"Error getting optimal travel time: {str(e)}")
        return {
            "error": f"Failed to get optimal travel time: {str(e)}",
            "destination": destination,
            "activity_type": activity_type,
        }
    finally:
        # Ensure client is disconnected
        await client.disconnect()
