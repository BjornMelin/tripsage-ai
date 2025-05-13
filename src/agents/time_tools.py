"""
Time-related function tools for TripSage agents.

This module provides OpenAI Agents SDK function tools for time operations
using the Time MCP client, allowing agents to get current time, convert
time between timezones, and perform other time-related operations.
"""

from typing import Any, Dict, List

from agents import function_tool

from ..mcp.time.client import get_client, get_service
from ..utils.decorators import with_error_handling
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Get the Time MCP client and service
time_client = get_client()
time_service = get_service()


@function_tool
@with_error_handling
async def get_current_time_tool(timezone: str) -> Dict[str, Any]:
    """Get the current time in a specific timezone.

    Args:
        timezone: IANA timezone name (e.g., 'America/New_York', 'Europe/London')

    Returns:
        Dictionary with current time information including timezone and DST status
    """
    logger.info(f"Getting current time for timezone: {timezone}")
    result = await time_client.get_current_time(timezone)
    return {
        "current_time": result.get("current_time", ""),
        "current_date": result.get("current_date", ""),
        "timezone": result.get("timezone", timezone),
        "utc_offset": result.get("utc_offset", ""),
        "is_dst": result.get("is_dst", False),
        "formatted": (
            f"{result.get('current_date', '')} {result.get('current_time', '')} "
            f"({timezone})"
        ),
    }


@function_tool
@with_error_handling
async def convert_timezone_tool(time: str, from_tz: str, to_tz: str) -> Dict[str, Any]:
    """Convert time between different timezones.

    Args:
        time: Time to convert in 24-hour format (HH:MM)
        from_tz: Source IANA timezone name (e.g., 'America/New_York')
        to_tz: Target IANA timezone name (e.g., 'Asia/Tokyo')

    Returns:
        Dictionary with time conversion information
    """
    logger.info(f"Converting time {time} from {from_tz} to {to_tz}")
    result = await time_client.convert_time(
        time=time, source_timezone=from_tz, target_timezone=to_tz
    )
    return {
        "source_time": result.get("source_time", time),
        "source_timezone": result.get("source_timezone", from_tz),
        "target_time": result.get("target_time", ""),
        "target_timezone": result.get("target_timezone", to_tz),
        "time_difference": result.get("time_difference", ""),
        "formatted": (
            f"{time} {from_tz} = {result.get('target_time', '')} {to_tz} "
            f"(difference: {result.get('time_difference', '')})"
        ),
    }


@function_tool
@with_error_handling
async def get_local_time_tool(location: str) -> Dict[str, Any]:
    """Get the current local time for a travel destination.

    Args:
        location: Travel destination name (e.g., 'New York', 'Tokyo')

    Returns:
        Dictionary with current time information for the location
    """
    logger.info(f"Getting local time for location: {location}")
    result = await time_service.get_local_time(location)
    return {
        "location": location,
        "current_time": result.get("current_time", ""),
        "current_date": result.get("current_date", ""),
        "timezone": result.get("timezone", ""),
        "utc_offset": result.get("utc_offset", ""),
        "is_dst": result.get("is_dst", False),
        "formatted": (
            f"Current time in {location}: {result.get('current_date', '')} "
            f"{result.get('current_time', '')} ({result.get('timezone', '')})"
        ),
    }


@function_tool
@with_error_handling
async def calculate_flight_arrival_tool(
    departure_time: str,
    departure_location: str,
    flight_duration_hours: float,
    arrival_location: str,
) -> Dict[str, Any]:
    """Calculate the arrival time for a flight accounting for timezone differences.

    Args:
        departure_time: Departure time in 24-hour format (HH:MM)
        departure_location: Departure location (city name)
        flight_duration_hours: Flight duration in hours (e.g., 5.5)
        arrival_location: Arrival location (city name)

    Returns:
        Dictionary with arrival time information
    """
    logger.info(
        f"Calculating flight arrival: {departure_time} from {departure_location} "
        f"to {arrival_location} (duration: {flight_duration_hours}h)"
    )

    # Get timezone for departure location
    departure_info = await time_service.get_local_time(departure_location)
    departure_timezone = departure_info.get("timezone", "UTC")

    # Get timezone for arrival location
    arrival_info = await time_service.get_local_time(arrival_location)
    arrival_timezone = arrival_info.get("timezone", "UTC")

    # Calculate arrival time
    result = await time_service.calculate_flight_arrival(
        departure_time=departure_time,
        departure_timezone=departure_timezone,
        flight_duration_hours=flight_duration_hours,
        arrival_timezone=arrival_timezone,
    )

    day_offset = result.get("day_offset", 0)
    day_text = (
        f" (+{day_offset} day{'s' if day_offset > 1 else ''})" if day_offset > 0 else ""
    )

    return {
        "departure_location": departure_location,
        "departure_timezone": departure_timezone,
        "departure_time": departure_time,
        "flight_duration": result.get("flight_duration", f"{flight_duration_hours}h"),
        "arrival_location": arrival_location,
        "arrival_timezone": arrival_timezone,
        "arrival_time_local": result.get("arrival_time_local", ""),
        "day_offset": day_offset,
        "time_difference": result.get("time_difference", ""),
        "formatted": (
            f"Flight from {departure_location} ({departure_time}) "
            f"to {arrival_location}\nDuration: "
            f"{result.get('flight_duration', f'{flight_duration_hours}h')}\n"
            f"Local arrival time: {result.get('arrival_time_local', '')}{day_text} "
            f"({arrival_timezone})\n"
            f"Time zone difference: {result.get('time_difference', '')}"
        ),
    }


@function_tool
@with_error_handling
async def find_meeting_times_tool(
    first_location: str,
    second_location: str,
    first_available_hours: str = "9-17",
    second_available_hours: str = "9-17",
) -> Dict[str, Any]:
    """Find suitable meeting times across different timezones.

    Args:
        first_location: First participant's location (city name)
        second_location: Second participant's location (city name)
        first_available_hours: Hours range for first participant (format: "9-17")
        second_available_hours: Hours range for second participant (format: "9-17")

    Returns:
        Dictionary with suitable meeting times in both timezones
    """
    logger.info(
        f"Finding meeting times for {first_location} ({first_available_hours}) "
        f"and {second_location} ({second_available_hours})"
    )

    # Parse available hours
    first_start, first_end = map(int, first_available_hours.split("-"))
    second_start, second_end = map(int, second_available_hours.split("-"))

    # Get timezone for first location
    first_info = await time_service.get_local_time(first_location)
    first_timezone = first_info.get("timezone", "UTC")

    # Get timezone for second location
    second_info = await time_service.get_local_time(second_location)
    second_timezone = second_info.get("timezone", "UTC")

    # Find suitable meeting times
    suitable_times = await time_service.find_meeting_times(
        first_timezone=first_timezone,
        second_timezone=second_timezone,
        first_available_hours=(first_start, first_end),
        second_available_hours=(second_start, second_end),
    )

    # Format results
    if not suitable_times:
        return {
            "first_location": first_location,
            "first_timezone": first_timezone,
            "second_location": second_location,
            "second_timezone": second_timezone,
            "suitable_times": [],
            "time_difference": "",
            "count": 0,
            "formatted": (
                f"No suitable meeting times found between {first_location} and "
                f"{second_location} during specified hours."
            ),
        }

    # Get time difference from any suitable time
    time_difference = suitable_times[0].get("time_difference", "")

    formatted_times = []
    for i, time in enumerate(suitable_times[:5], 1):  # Show top 5 options
        formatted_times.append(
            f"{i}. {time['first_time']} in {first_location} = "
            f"{time['second_time']} in {second_location}"
        )

    formatted_result = (
        f"Suitable meeting times between {first_location} and {second_location}:\n"
        f"{chr(10).join(formatted_times)}\n\n"
        f"Time difference: {time_difference}"
    )

    return {
        "first_location": first_location,
        "first_timezone": first_timezone,
        "second_location": second_location,
        "second_timezone": second_timezone,
        "suitable_times": suitable_times,
        "time_difference": time_difference,
        "count": len(suitable_times),
        "formatted": formatted_result,
    }


@function_tool
@with_error_handling
async def create_timezone_aware_itinerary_tool(
    itinerary_items: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Create a timezone-aware itinerary for a multi-city trip.

    Args:
        itinerary_items: List of itinerary items with location, activity,
                         and time info (in UTC or local time)

    Returns:
        Dictionary with timezone-aware itinerary items
    """
    logger.info(f"Creating timezone-aware itinerary with {len(itinerary_items)} items")
    processed_itinerary = await time_service.create_timezone_aware_itinerary(
        itinerary_items
    )

    return {"itinerary": processed_itinerary, "count": len(processed_itinerary)}
