"""
Time-related function tools for TripSage agents.

This module provides OpenAI Agents SDK function tools for time operations
using the Time MCP client, allowing agents to get current time, convert
time between timezones, and perform other time-related operations.
"""

from typing import Any, Dict, List

from openai_agents_sdk import function_tool

from tripsage.config.app_settings import settings
from tripsage.tools.schemas.time import (
    ConvertTimeParams,
    GetCurrentTimeParams,
    ItineraryItem,
    TimeConversionResponse,
    TimeResponse,
)
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


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

    # Validate parameters
    params = GetCurrentTimeParams(timezone=timezone)

    # Call the Time MCP
    result = await validate_and_call_mcp_tool(
        endpoint=settings.time_mcp_endpoint,
        tool_name="get_current_time",
        params={"timezone": timezone},
        response_model=TimeResponse,
        timeout=30.0,
        server_name="Time MCP",
    )

    return {
        "current_time": result.current_time,
        "current_date": result.current_date,
        "timezone": result.timezone,
        "utc_offset": result.utc_offset,
        "is_dst": result.is_dst,
        "formatted": (f"{result.current_date} {result.current_time} ({timezone})"),
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

    # Validate parameters
    params = ConvertTimeParams(
        time=time,
        source_timezone=from_tz,
        target_timezone=to_tz,
    )

    # Call the Time MCP
    result = await validate_and_call_mcp_tool(
        endpoint=settings.time_mcp_endpoint,
        tool_name="convert_time",
        params={
            "time": time,
            "source_timezone": from_tz,
            "target_timezone": to_tz,
        },
        response_model=TimeConversionResponse,
        timeout=30.0,
        server_name="Time MCP",
    )

    # Extract target time from datetime
    target_time = ""
    if "T" in result.target.datetime:
        target_time = result.target.datetime.split("T")[1].split("+")[0]

    return {
        "source_time": time,
        "source_timezone": from_tz,
        "target_time": target_time,
        "target_timezone": to_tz,
        "time_difference": result.time_difference,
        "formatted": (
            f"{time} {from_tz} = {target_time} {to_tz} "
            f"(difference: {result.time_difference})"
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

    # Map location to timezone
    # This is a simplified mapping - in production, you would use a more
    # comprehensive mapping service or geocoding + timezone lookup
    location_timezone_map = {
        "new york": "America/New_York",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "tokyo": "Asia/Tokyo",
        "sydney": "Australia/Sydney",
        "los angeles": "America/Los_Angeles",
        "san francisco": "America/Los_Angeles",
        "chicago": "America/Chicago",
        "berlin": "Europe/Berlin",
        "rome": "Europe/Rome",
        "dubai": "Asia/Dubai",
        "hong kong": "Asia/Hong_Kong",
        "singapore": "Asia/Singapore",
        "bangkok": "Asia/Bangkok",
        "delhi": "Asia/Kolkata",
        "mumbai": "Asia/Kolkata",
        "beijing": "Asia/Shanghai",
        "shanghai": "Asia/Shanghai",
        "toronto": "America/Toronto",
        "vancouver": "America/Vancouver",
        "melbourne": "Australia/Melbourne",
        "auckland": "Pacific/Auckland",
        "rio de janeiro": "America/Sao_Paulo",
        "sao paulo": "America/Sao_Paulo",
        "mexico city": "America/Mexico_City",
        "johannesburg": "Africa/Johannesburg",
        "cairo": "Africa/Cairo",
        "istanbul": "Europe/Istanbul",
        "moscow": "Europe/Moscow",
    }

    location_lower = location.lower()
    if location_lower in location_timezone_map:
        timezone = location_timezone_map[location_lower]
    else:
        # Default to UTC if location not found
        timezone = "UTC"
        logger.warning(f"No timezone mapping found for location: {location}, using UTC")

    # Get current time in the location's timezone
    result = await get_current_time_tool(timezone)

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
    departure_info = await get_local_time_tool(departure_location)
    departure_timezone = departure_info.get("timezone", "UTC")

    # Get timezone for arrival location
    arrival_info = await get_local_time_tool(arrival_location)
    arrival_timezone = arrival_info.get("timezone", "UTC")

    # Calculate flight arrival time
    departure_date_info = await get_current_time_tool(departure_timezone)
    departure_date = departure_date_info.get("current_date", "")

    # Parse departure time
    try:
        hours, minutes = map(int, departure_time.split(":"))
    except ValueError:
        return {"error": "Invalid departure time format. Please use HH:MM format."}

    # Add flight duration
    duration_hours = int(flight_duration_hours)
    duration_minutes = int((flight_duration_hours - duration_hours) * 60)

    # Calculate arrival time in departure timezone
    arrival_hours = hours + duration_hours
    arrival_minutes = minutes + duration_minutes

    # Adjust for overflow
    while arrival_minutes >= 60:
        arrival_hours += 1
        arrival_minutes -= 60

    day_offset = 0
    while arrival_hours >= 24:
        day_offset += 1
        arrival_hours -= 24

    # Format arrival time
    arrival_time_in_departure_tz = f"{arrival_hours:02d}:{arrival_minutes:02d}"

    # Convert to arrival timezone
    conversion = await convert_timezone_tool(
        time=arrival_time_in_departure_tz,
        from_tz=departure_timezone,
        to_tz=arrival_timezone,
    )

    # Create response
    result = {
        "departure_location": departure_location,
        "departure_timezone": departure_timezone,
        "departure_time": departure_time,
        "flight_duration": f"{duration_hours}h {duration_minutes}m",
        "arrival_location": arrival_location,
        "arrival_timezone": arrival_timezone,
        "arrival_time_local": conversion.get("target_time", ""),
        "arrival_time_departure_tz": arrival_time_in_departure_tz,
        "day_offset": day_offset,
        "time_difference": conversion.get("time_difference", ""),
    }

    day_text = (
        f" (+{day_offset} day{'s' if day_offset > 1 else ''})" if day_offset > 0 else ""
    )

    result["formatted"] = (
        f"Flight from {departure_location} ({departure_time}) "
        f"to {arrival_location}\nDuration: "
        f"{result['flight_duration']}\n"
        f"Local arrival time: {result['arrival_time_local']}{day_text} "
        f"({arrival_timezone})\n"
        f"Time zone difference: {result['time_difference']}"
    )

    return result


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
    try:
        first_start, first_end = map(int, first_available_hours.split("-"))
        second_start, second_end = map(int, second_available_hours.split("-"))
    except ValueError:
        return {
            "error": "Invalid hours format. Please use the format 'start-end' (e.g., '9-17')."
        }

    # Get timezone for first location
    first_info = await get_local_time_tool(first_location)
    first_timezone = first_info.get("timezone", "UTC")

    # Get timezone for second location
    second_info = await get_local_time_tool(second_location)
    second_timezone = second_info.get("timezone", "UTC")

    # Find suitable meeting times
    suitable_times = []

    # Step through each hour in the first timezone's available range
    for hour in range(first_start, first_end):
        for minute in [0, 30]:  # Check both :00 and :30 times
            first_time = f"{hour:02d}:{minute:02d}"

            # Convert to second timezone
            conversion = await convert_timezone_tool(
                time=first_time,
                from_tz=first_timezone,
                to_tz=second_timezone,
            )

            second_time = conversion.get("target_time", "00:00")

            try:
                # Extract hour from time string
                second_hour = int(second_time.split(":")[0])
            except (ValueError, IndexError):
                # Reset to midnight if parsing fails
                second_hour = 0

            # Check if time is suitable (within available hours in second timezone)
            if second_start <= second_hour < second_end:
                meeting_time = {
                    "first_timezone": first_timezone,
                    "first_time": first_time,
                    "second_timezone": second_timezone,
                    "second_time": second_time,
                    "time_difference": conversion.get("time_difference", ""),
                }
                suitable_times.append(meeting_time)

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

    processed_itinerary = []

    for item in itinerary_items:
        # Validate input item
        try:
            item_model = ItineraryItem.model_validate(item)
        except Exception as e:
            logger.warning(f"Invalid itinerary item: {str(e)}")
            # Include the original item in the response
            processed_itinerary.append(item)
            continue

        # Get local timezone for the location
        location_info = await get_local_time_tool(item_model.location)
        location_timezone = location_info.get("timezone", "UTC")

        # If time is in UTC, convert to local time
        local_time = item_model.time or ""
        if item_model.time and item_model.time_format == "UTC":
            time_conversion = await convert_timezone_tool(
                time=item_model.time,
                from_tz="UTC",
                to_tz=location_timezone,
            )
            local_time = time_conversion.get("target_time", "00:00")

        # Add timezone information to the itinerary item
        processed_item = {
            "location": item_model.location,
            "activity": item_model.activity,
            "time": item_model.time,
            "time_format": item_model.time_format,
            "timezone": location_timezone,
            "local_time": local_time,
            "utc_offset": location_info.get("utc_offset", ""),
        }

        # Add any extra fields from the original item
        for key, value in item.items():
            if key not in processed_item:
                processed_item[key] = value

        processed_itinerary.append(processed_item)

    return {"itinerary": processed_itinerary, "count": len(processed_itinerary)}
