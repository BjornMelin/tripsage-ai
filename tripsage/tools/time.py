"""
Time-related tools for TripSage agents.

This module provides tools for accessing time-related functionality
through the Time MCP server.
"""

from typing import Any, Dict, Optional

from agents import function_tool
from tripsage.clients.time_client import get_time_client
from tripsage.utils.error_decorators import with_error_handling
from tripsage.utils.logging import get_module_logger

logger = get_module_logger(__name__)


@function_tool
@with_error_handling
async def get_current_time_tool(timezone: str) -> Dict[str, Any]:
    """
    Get the current time in a specific timezone.

    Args:
        timezone: IANA timezone name (e.g., "America/New_York", "Europe/London")

    Returns:
        Dictionary containing the current time and formatted time string
    """
    time_client = await get_time_client()
    result = await time_client.get_current_time(timezone)
    return {
        "current_time": result.get("current_time", ""),
        "formatted_time": result.get("formatted_time", ""),
        "timezone": timezone,
    }


@function_tool
@with_error_handling
async def convert_time_tool(
    time_str: str,
    from_timezone: str,
    to_timezone: str,
    format_24h: Optional[bool] = False,
) -> Dict[str, Any]:
    """
    Convert a time from one timezone to another.

    Args:
        time_str: Time string in format HH:MM or HH:MM:SS
        from_timezone: Source IANA timezone name
        to_timezone: Target IANA timezone name
        format_24h: Whether to return time in 24-hour format

    Returns:
        Dictionary containing the converted time
    """
    time_client = await get_time_client()
    result = await time_client.convert_time(
        time_str=time_str,
        from_timezone=from_timezone,
        to_timezone=to_timezone,
        format_24h=format_24h,
    )
    return {
        "converted_time": result.get("converted_time", ""),
        "from_timezone": from_timezone,
        "to_timezone": to_timezone,
    }


@function_tool
@with_error_handling
async def get_time_difference_tool(timezone1: str, timezone2: str) -> Dict[str, Any]:
    """
    Get the time difference between two timezones.

    Args:
        timezone1: First IANA timezone name
        timezone2: Second IANA timezone name

    Returns:
        Dictionary containing the time difference in hours
    """
    time_client = await get_time_client()
    result = await time_client.get_time_difference(
        timezone1=timezone1, timezone2=timezone2
    )
    return {
        "difference_hours": result.get("difference_hours", 0),
        "timezone1": timezone1,
        "timezone2": timezone2,
        "timezone1_current_time": result.get("timezone1_current_time", ""),
        "timezone2_current_time": result.get("timezone2_current_time", ""),
    }
