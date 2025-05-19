"""
Time-related function tools for TripSage agents.

This module provides OpenAI Agents SDK function tools for time operations
using the Time MCP through the abstraction layer, allowing agents to get
current time, convert time between timezones, and perform other time-related
operations.
"""

from typing import Any, Dict, List

from agents import function_tool
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.tools.schemas.time import (
    ConvertTimeParams,
    GetCurrentTimeParams,
    ItineraryItem,
)
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
    try:
        # Validate timezone format - if this passes, the timezone is valid
        GetCurrentTimeParams(timezone=timezone)
    except ValueError as e:
        return {"error": str(e)}

    # Call the Time MCP through the abstraction layer
    try:
        result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="get_current_time",
            params={"timezone": timezone},
        )

        return {
            "current_time": result.current_time,
            "current_date": result.current_date,
            "timezone": result.timezone,
            "utc_offset": result.utc_offset,
            "is_dst": result.is_dst,
            "formatted": (f"{result.current_date} {result.current_time} ({timezone})"),
        }
    except Exception as e:
        logger.error(f"Error getting current time: {str(e)}")
        return {"error": f"Failed to get current time: {str(e)}"}


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
    try:
        # Validate parameter formats - if this passes, the parameters are valid
        ConvertTimeParams(
            time=time,
            source_timezone=from_tz,
            target_timezone=to_tz,
        )
    except ValueError as e:
        return {"error": str(e)}

    # Call the Time MCP through the abstraction layer
    try:
        result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="convert_time",
            params={
                "time": time,
                "source_timezone": from_tz,
                "target_timezone": to_tz,
            },
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
    except Exception as e:
        logger.error(f"Error converting time: {str(e)}")
        return {"error": f"Failed to convert time: {str(e)}"}


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
        "montreal": "America/Toronto",
        "miami": "America/New_York",
        "boston": "America/New_York",
        "seattle": "America/Los_Angeles",
        "atlanta": "America/New_York",
        "denver": "America/Denver",
        "phoenix": "America/Phoenix",
        "madrid": "Europe/Madrid",
        "barcelona": "Europe/Madrid",
        "amsterdam": "Europe/Amsterdam",
        "moscow": "Europe/Moscow",
        "cairo": "Africa/Cairo",
        "johannesburg": "Africa/Johannesburg",
        "melbourne": "Australia/Melbourne",
        "perth": "Australia/Perth",
        "auckland": "Pacific/Auckland",
        "seoul": "Asia/Seoul",
        "taipei": "Asia/Taipei",
        "istanbul": "Europe/Istanbul",
        "athens": "Europe/Athens",
        "prague": "Europe/Prague",
        "vienna": "Europe/Vienna",
        "zurich": "Europe/Zurich",
        "stockholm": "Europe/Stockholm",
        "oslo": "Europe/Oslo",
        "copenhagen": "Europe/Copenhagen",
        "brussels": "Europe/Brussels",
        "lisbon": "Europe/Lisbon",
        "dublin": "Europe/Dublin",
        "edinburgh": "Europe/London",
        "tel aviv": "Asia/Jerusalem",
        "kuala lumpur": "Asia/Kuala_Lumpur",
        "jakarta": "Asia/Jakarta",
        "manila": "Asia/Manila",
        "ho chi minh city": "Asia/Ho_Chi_Minh",
        "hanoi": "Asia/Bangkok",
        "mexico city": "America/Mexico_City",
        "buenos aires": "America/Argentina/Buenos_Aires",
        "rio de janeiro": "America/Sao_Paulo",
        "sao paulo": "America/Sao_Paulo",
        "lima": "America/Lima",
        "santiago": "America/Santiago",
        "bogota": "America/Bogota",
    }

    # Find timezone for location (case-insensitive)
    location_lower = location.lower()
    timezone = location_timezone_map.get(location_lower)

    if not timezone:
        # Try partial matching
        for city, tz in location_timezone_map.items():
            if location_lower in city or city in location_lower:
                timezone = tz
                break

    if not timezone:
        return {
            "error": f"Cannot determine timezone for location: {location}. "
            "Please provide a major city name or IANA timezone."
        }

    # Get current time for the determined timezone
    return await get_current_time_tool(timezone=timezone)


@function_tool
@with_error_handling
async def calculate_time_difference_tool(
    time1_zone: str, time2_zone: str
) -> Dict[str, Any]:
    """Calculate the time difference between two timezones.

    Args:
        time1_zone: First IANA timezone name
        time2_zone: Second IANA timezone name

    Returns:
        Dictionary with time difference information
    """
    logger.info(f"Calculating time difference between {time1_zone} and {time2_zone}")

    try:
        # Get current time in both zones
        time1_result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="get_current_time",
            params={"timezone": time1_zone},
        )

        time2_result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="get_current_time",
            params={"timezone": time2_zone},
        )

        # Calculate difference based on UTC offsets
        offset1 = time1_result.utc_offset
        offset2 = time2_result.utc_offset

        # Parse offsets (format: "+05:30" or "-08:00")
        def parse_offset(offset_str):
            if not offset_str:
                return 0
            sign = 1 if offset_str[0] == "+" else -1
            parts = offset_str[1:].split(":")
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return sign * (hours * 60 + minutes)

        offset1_minutes = parse_offset(offset1)
        offset2_minutes = parse_offset(offset2)
        difference_minutes = offset2_minutes - offset1_minutes

        # Convert to hours and minutes
        hours = abs(difference_minutes) // 60
        minutes = abs(difference_minutes) % 60
        difference_str = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"

        if difference_minutes > 0:
            difference_str = f"+{difference_str}"
        elif difference_minutes < 0:
            difference_str = f"-{difference_str}"
        else:
            difference_str = "No time difference"

        return {
            "timezone1": time1_zone,
            "timezone2": time2_zone,
            "utc_offset1": offset1,
            "utc_offset2": offset2,
            "difference": difference_str,
            "difference_minutes": difference_minutes,
            "formatted": f"{time2_zone} is {difference_str} from {time1_zone}",
        }
    except Exception as e:
        logger.error(f"Error calculating time difference: {str(e)}")
        return {"error": f"Failed to calculate time difference: {str(e)}"}


@function_tool
@with_error_handling
async def schedule_meeting_time_tool(
    participants: List[Dict[str, str]], duration_hours: float = 1.0
) -> Dict[str, Any]:
    """Suggest optimal meeting times across multiple timezones.

    Args:
        participants: List of participant dicts with 'name' and 'timezone' keys
        duration_hours: Meeting duration in hours

    Returns:
        Dictionary with suggested meeting times for all participants
    """
    logger.info(
        f"Finding meeting time for {len(participants)} participants "
        f"({duration_hours}h duration)"
    )

    if not participants or len(participants) < 2:
        return {"error": "At least 2 participants required for meeting scheduling"}

    try:
        # Call the Time MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="find_meeting_time",
            params={
                "participants": [
                    {
                        "name": p["name"],
                        "timezone": p["timezone"],
                        "availability": p.get("availability", "09:00-17:00"),
                    }
                    for p in participants
                ],
                "duration_hours": duration_hours,
            },
        )

        return {
            "suggested_utc_time": result.suggested_utc_time,
            "local_times": result.local_times,
            "is_optimal": result.is_optimal,
            "conflicts": result.conflicts,
            "duration_hours": duration_hours,
            "formatted": (
                f"Suggested meeting time: {result.suggested_utc_time} UTC\n"
                + "\n".join(
                    [f"- {name}: {time}" for name, time in result.local_times.items()]
                )
            ),
        }
    except Exception as e:
        logger.error(f"Error scheduling meeting: {str(e)}")
        return {"error": f"Failed to schedule meeting: {str(e)}"}


@function_tool
@with_error_handling
async def process_travel_itinerary_times_tool(
    itinerary: List[ItineraryItem],
) -> Dict[str, Any]:
    """Process and convert times in a travel itinerary to local timezones.

    Args:
        itinerary: List of itinerary items with locations and times

    Returns:
        Dictionary with processed itinerary including local times
    """
    logger.info(f"Processing times for {len(itinerary)} itinerary items")

    try:
        # Convert to the expected format for the MCP
        items = []
        for item in itinerary:
            items.append(
                {
                    "name": item.name,
                    "location": item.location,
                    "datetime": item.datetime,
                    "duration_hours": item.duration_hours,
                }
            )

        # Call the Time MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="process_itinerary",
            params={
                "items": items,
            },
        )

        # Process the results
        processed_items = []
        for item in result.processed_items:
            processed_items.append(
                {
                    "name": item.name,
                    "location": item.location,
                    "original_datetime": item.original_datetime,
                    "local_datetime": item.local_datetime,
                    "timezone": item.timezone,
                    "duration_hours": item.duration_hours,
                    "formatted": (
                        f"{item.name} at {item.location}: "
                        f"{item.local_datetime} ({item.timezone})"
                    ),
                }
            )

        # Create summary
        timezones = list({item["timezone"] for item in processed_items})
        summary = (
            f"Itinerary crosses {len(timezones)} timezone(s): {', '.join(timezones)}"
        )

        return {
            "processed_items": processed_items,
            "timezones": timezones,
            "summary": summary,
            "formatted": "\n".join([item["formatted"] for item in processed_items]),
        }
    except Exception as e:
        logger.error(f"Error processing itinerary times: {str(e)}")
        return {"error": f"Failed to process itinerary times: {str(e)}"}


@function_tool
@with_error_handling
async def calculate_flight_arrival_time_tool(
    departure_time: str,
    departure_timezone: str,
    flight_duration_hours: float,
    arrival_timezone: str,
) -> Dict[str, Any]:
    """Calculate arrival time for a flight accounting for timezone changes.

    Args:
        departure_time: Departure time in 24-hour format (HH:MM)
        departure_timezone: IANA timezone of departure
        flight_duration_hours: Flight duration in hours
        arrival_timezone: IANA timezone of arrival

    Returns:
        Dictionary with calculated arrival time information
    """
    logger.info(
        f"Calculating arrival time for {flight_duration_hours}h flight "
        f"from {departure_timezone} to {arrival_timezone}"
    )

    try:
        # Call the Time MCP through the abstraction layer
        result = await mcp_manager.invoke(
            mcp_name="time",
            method_name="calculate_arrival_time",
            params={
                "departure_time": departure_time,
                "departure_timezone": departure_timezone,
                "flight_duration_hours": flight_duration_hours,
                "arrival_timezone": arrival_timezone,
            },
        )

        return {
            "departure_time": result.departure_time,
            "arrival_time": result.arrival_time,
            "departure_timezone": departure_timezone,
            "arrival_timezone": arrival_timezone,
            "flight_duration": flight_duration_hours,
            "formatted": (
                f"Departure: {result.departure_time} ({departure_timezone})\n"
                f"Arrival: {result.arrival_time} ({arrival_timezone})\n"
                f"Flight duration: {flight_duration_hours}h"
            ),
        }
    except Exception as e:
        logger.error(f"Error calculating flight arrival time: {str(e)}")
        return {"error": f"Failed to calculate arrival time: {str(e)}"}
