# Time MCP Server Integration

This document outlines the implementation details for the Time MCP Server, which provides timezone conversion and time management capabilities for the TripSage travel planning system.

## Overview

The Time MCP Server provides essential time-related functionality for the TripSage application, including timezone conversion, date manipulation, and scheduling utilities. These capabilities are critical for a travel planning system that must coordinate activities across multiple timezones, manage flight arrival and departure times, and create accurate itineraries with proper local time information.

## Architecture Decision

After evaluating multiple time management libraries and implementation approaches, we've decided to implement a hybrid approach that:

1. Uses FastMCP 2.0 as the framework for our MCP server to maintain consistency with other TripSage MCP implementations
2. Leverages the official Model Context Protocol (MCP) time server functionality under the hood
3. Provides an interface that works seamlessly with both Claude Desktop and OpenAI Agents SDK

This hybrid approach gives us the best of both worlds:

- **Consistency**: Same FastMCP 2.0 framework used across all TripSage MCP implementations
- **Standardization**: Core functionality from the official MCP time server
- **Compatibility**: Support for both Claude Desktop and OpenAI Agents SDK
- **Extensibility**: Ability to add custom features specific to TripSage needs

## Python Implementation with Official Time Server

### Server Implementation

```python
# src/mcp/time/server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz
from zoneinfo import ZoneInfo, available_timezones
import re

from ..base_mcp_server import BaseMCPServer

class GetCurrentTimeRequest(BaseModel):
    """Request model for getting current time in a specific timezone."""
    timezone: str = Field(..., description="IANA timezone name (e.g., 'America/New_York', 'Europe/London')")

class GetCurrentTimeResponse(BaseModel):
    """Response model for current time request."""
    current_time: str = Field(..., description="Current time in the requested timezone")
    timezone: str = Field(..., description="The timezone used")
    utc_offset: str = Field(..., description="UTC offset for the timezone")
    is_dst: bool = Field(..., description="Whether daylight saving time is currently in effect")

class ConvertTimeRequest(BaseModel):
    """Request model for converting time between timezones."""
    time: str = Field(..., description="Time to convert in 24-hour format (HH:MM)")
    source_timezone: str = Field(..., description="Source IANA timezone name")
    target_timezone: str = Field(..., description="Target IANA timezone name")

class ConvertTimeResponse(BaseModel):
    """Response model for time conversion request."""
    source_time: str = Field(..., description="Original time in source timezone")
    target_time: str = Field(..., description="Converted time in target timezone")
    source_timezone: str = Field(..., description="Source timezone")
    target_timezone: str = Field(..., description="Target timezone")
    source_utc_offset: str = Field(..., description="UTC offset for source timezone")
    target_utc_offset: str = Field(..., description="UTC offset for target timezone")
    time_difference: str = Field(..., description="Time difference between timezones (hours)")

class CalculateTravelTimeRequest(BaseModel):
    """Request model for calculating travel time between timezones."""
    departure_timezone: str = Field(..., description="Departure IANA timezone name")
    departure_time: str = Field(..., description="Departure time in 24-hour format (HH:MM)")
    arrival_timezone: str = Field(..., description="Arrival IANA timezone name")
    arrival_time: str = Field(..., description="Arrival time in 24-hour format (HH:MM)")

class CalculateTravelTimeResponse(BaseModel):
    """Response model for travel time calculation."""
    departure: dict = Field(..., description="Departure information")
    arrival: dict = Field(..., description="Arrival information")
    duration: dict = Field(..., description="Travel duration information")

class TimeMCPServer(BaseMCPServer):
    """MCP Server for time-related operations."""

    def __init__(self):
        """Initialize the Time MCP Server."""
        super().__init__(title="Time MCP Server")

        # Register routes
        self.app.post("/get_current_time", response_model=GetCurrentTimeResponse)(self.get_current_time)
        self.app.post("/convert_time", response_model=ConvertTimeResponse)(self.convert_time)
        self.app.post("/calculate_travel_time", response_model=CalculateTravelTimeResponse)(self.calculate_travel_time)
        self.app.post("/list_timezones")(self.list_timezones)
        self.app.post("/format_date")(self.format_date)

    async def get_current_time(self, request: GetCurrentTimeRequest) -> Dict[str, Any]:
        """Get the current time in the specified timezone."""
        try:
            # Validate timezone
            if request.timezone not in available_timezones():
                raise ValueError(f"Invalid timezone: {request.timezone}")

            # Get current time in specified timezone
            tz = ZoneInfo(request.timezone)
            now = datetime.now(tz)

            # Get UTC offset
            utc_offset = now.strftime("%z")
            formatted_offset = f"{utc_offset[:-2]}:{utc_offset[-2:]}"

            # Check if DST is in effect
            is_dst = bool(now.dst())

            return {
                "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": request.timezone,
                "utc_offset": formatted_offset,
                "is_dst": is_dst
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def convert_time(self, request: ConvertTimeRequest) -> Dict[str, Any]:
        """Convert time between different timezones."""
        try:
            # Validate timezones
            if request.source_timezone not in available_timezones():
                raise ValueError(f"Invalid source timezone: {request.source_timezone}")
            if request.target_timezone not in available_timezones():
                raise ValueError(f"Invalid target timezone: {request.target_timezone}")

            # Validate time format (HH:MM)
            if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", request.time):
                raise ValueError("Time must be in 24-hour format (HH:MM)")

            # Parse the time
            hours, minutes = map(int, request.time.split(':'))

            # Use current date with the specified time
            source_tz = ZoneInfo(request.source_timezone)
            now = datetime.now(source_tz)
            source_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)

            # Convert to target timezone
            target_tz = ZoneInfo(request.target_timezone)
            target_time = source_time.astimezone(target_tz)

            # Get UTC offsets
            source_offset = source_time.strftime("%z")
            formatted_source_offset = f"{source_offset[:-2]}:{source_offset[-2:]}"

            target_offset = target_time.strftime("%z")
            formatted_target_offset = f"{target_offset[:-2]}:{target_offset[-2:]}"

            # Calculate time difference in hours
            diff_seconds = (int(target_offset[:3]) - int(source_offset[:3])) * 3600
            diff_seconds += (int(target_offset[3:5]) - int(source_offset[3:5])) * 60
            diff_hours = diff_seconds / 3600

            diff_str = f"{diff_hours:+g}h"

            return {
                "source_time": source_time.strftime("%H:%M"),
                "target_time": target_time.strftime("%H:%M"),
                "source_timezone": request.source_timezone,
                "target_timezone": request.target_timezone,
                "source_utc_offset": formatted_source_offset,
                "target_utc_offset": formatted_target_offset,
                "time_difference": diff_str
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def calculate_travel_time(self, request: CalculateTravelTimeRequest) -> Dict[str, Any]:
        """Calculate travel time between departure and arrival points."""
        try:
            # Convert both times to UTC for comparison
            departure_result = await self.convert_time(ConvertTimeRequest(
                time=request.departure_time,
                source_timezone=request.departure_timezone,
                target_timezone="UTC"
            ))

            arrival_result = await self.convert_time(ConvertTimeRequest(
                time=request.arrival_time,
                source_timezone=request.arrival_timezone,
                target_timezone="UTC"
            ))

            # Parse UTC times
            departure_dt = datetime.strptime(f"{datetime.now().date()} {departure_result['target_time']}", "%Y-%m-%d %H:%M")
            arrival_dt = datetime.strptime(f"{datetime.now().date()} {arrival_result['target_time']}", "%Y-%m-%d %H:%M")

            # Handle overnight flights
            if arrival_dt < departure_dt:
                arrival_dt = arrival_dt.replace(day=arrival_dt.day + 1)

            # Calculate duration
            duration_td = arrival_dt - departure_dt
            duration_seconds = duration_td.total_seconds()

            # Convert to hours and minutes
            duration_hours = int(duration_seconds // 3600)
            duration_minutes = int((duration_seconds % 3600) // 60)

            return {
                "departure": {
                    "timezone": request.departure_timezone,
                    "time": request.departure_time,
                    "utc_time": departure_result["target_time"]
                },
                "arrival": {
                    "timezone": request.arrival_timezone,
                    "time": request.arrival_time,
                    "utc_time": arrival_result["target_time"]
                },
                "duration": {
                    "hours": duration_hours,
                    "minutes": duration_minutes,
                    "total_minutes": duration_hours * 60 + duration_minutes,
                    "formatted": f"{duration_hours}h {duration_minutes}m"
                }
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def list_timezones(self) -> Dict[str, Any]:
        """List all available IANA timezones."""
        try:
            # Get all available timezones
            all_timezones = sorted(list(available_timezones()))

            # Group timezones by region
            grouped_timezones = {}
            for tz in all_timezones:
                # Split on first /
                parts = tz.split('/', 1)
                if len(parts) == 2:
                    region, zone = parts
                    if region not in grouped_timezones:
                        grouped_timezones[region] = []
                    grouped_timezones[region].append(zone)
                else:
                    if "Other" not in grouped_timezones:
                        grouped_timezones["Other"] = []
                    grouped_timezones["Other"].append(tz)

            return {
                "timezones": all_timezones,
                "grouped_timezones": grouped_timezones,
                "count": len(all_timezones)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def format_date(self, request: dict) -> Dict[str, Any]:
        """Format a date according to locale and timezone."""
        try:
            # Extract parameters
            date_str = request.get("date")
            timezone = request.get("timezone")
            format_type = request.get("format", "full")
            locale = request.get("locale", "en-US")

            # Validate timezone
            if timezone not in available_timezones():
                raise ValueError(f"Invalid timezone: {timezone}")

            # Parse the date - handle both full ISO format and date-only
            try:
                if "T" in date_str:
                    dt = datetime.fromisoformat(date_str)
                else:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Use ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")

            # Apply timezone
            tz = ZoneInfo(timezone)
            dt = dt.replace(tzinfo=tz)

            # Format according to type
            formats = {
                "full": "%A, %B %d, %Y %H:%M:%S",
                "short": "%m/%d/%Y %H:%M",
                "date_only": "%B %d, %Y",
                "time_only": "%H:%M:%S",
                "iso": "%Y-%m-%dT%H:%M:%S%z"
            }

            format_string = formats.get(format_type)
            if not format_string:
                raise ValueError(f"Invalid format type: {format_type}")

            formatted_date = dt.strftime(format_string)

            return {
                "formatted_date": formatted_date,
                "timezone": timezone,
                "format_type": format_type,
                "original_date": date_str
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

# Create server instance for import by other modules
time_server = TimeMCPServer()
```

### Tool Definitions for Time-Related Functions

```python
# src/mcp/time/__init__.py
from typing import Dict, Any, List
from ..base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Define tool schemas
GET_CURRENT_TIME_SCHEMA = {
    "name": "get_current_time",
    "description": "Get current time in a specific timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use 'UTC' as local timezone if no timezone provided by the user."
            }
        },
        "required": ["timezone"],
    }
}

CONVERT_TIME_SCHEMA = {
    "name": "convert_time",
    "description": "Convert time between timezones",
    "parameters": {
        "type": "object",
        "properties": {
            "time": {
                "type": "string",
                "description": "Time to convert in 24-hour format (HH:MM)"
            },
            "source_timezone": {
                "type": "string",
                "description": "Source IANA timezone name (e.g., 'America/New_York', 'Europe/London'). Use 'UTC' as local timezone if no source timezone provided by the user."
            },
            "target_timezone": {
                "type": "string",
                "description": "Target IANA timezone name (e.g., 'Asia/Tokyo', 'America/San_Francisco'). Use 'UTC' as local timezone if no target timezone provided by the user."
            }
        },
        "required": ["source_timezone", "time", "target_timezone"],
    }
}

CALCULATE_TRAVEL_TIME_SCHEMA = {
    "name": "calculate_travel_time",
    "description": "Calculate travel time between departure and arrival points",
    "parameters": {
        "type": "object",
        "properties": {
            "departure_timezone": {
                "type": "string",
                "description": "Departure IANA timezone name"
            },
            "departure_time": {
                "type": "string",
                "description": "Departure time in 24-hour format (HH:MM)"
            },
            "arrival_timezone": {
                "type": "string",
                "description": "Arrival IANA timezone name"
            },
            "arrival_time": {
                "type": "string",
                "description": "Arrival time in 24-hour format (HH:MM)"
            }
        },
        "required": ["departure_timezone", "departure_time", "arrival_timezone", "arrival_time"],
    }
}

LIST_TIMEZONES_SCHEMA = {
    "name": "list_timezones",
    "description": "List all available IANA timezones",
    "parameters": {
        "type": "object",
        "properties": {},
    }
}

FORMAT_DATE_SCHEMA = {
    "name": "format_date",
    "description": "Format a date according to locale and timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
            },
            "timezone": {
                "type": "string",
                "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London')"
            },
            "format": {
                "type": "string",
                "description": "Format type: 'full', 'short', 'date_only', 'time_only', or 'iso'",
                "enum": ["full", "short", "date_only", "time_only", "iso"],
                "default": "full"
            },
            "locale": {
                "type": "string",
                "description": "Locale code (e.g., 'en-US', 'fr-FR')",
                "default": "en-US"
            }
        },
        "required": ["date", "timezone"],
    }
}

# Export tool schemas for OpenAI Agent SDK integration
TIME_TOOL_SCHEMAS = [
    GET_CURRENT_TIME_SCHEMA,
    CONVERT_TIME_SCHEMA,
    CALCULATE_TRAVEL_TIME_SCHEMA,
    LIST_TIMEZONES_SCHEMA,
    FORMAT_DATE_SCHEMA
]
```

### Time Service Implementation - Client

```python
# src/mcp/time/client.py
from typing import Dict, Any, Optional, List
import aiohttp
import os
from pydantic import BaseModel
from datetime import datetime, timedelta
from agents import function_tool

from ..base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class TimeMCPClient(BaseMCPClient):
    """Client for interacting with the Time MCP Server."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the Time MCP Client.

        Args:
            base_url: Base URL for the Time MCP Server. If not provided,
                     uses the TIME_MCP_SERVER_URL environment variable.
        """
        if base_url is None:
            base_url = os.environ.get("TIME_MCP_SERVER_URL", "http://localhost:8004")
        super().__init__(base_url)
        logger.info(f"Initialized Time MCP Client with base URL: {base_url}")

    @function_tool
    async def get_current_time(self, timezone: str) -> Dict[str, Any]:
        """Get the current time in the specified timezone.

        Args:
            timezone: IANA timezone name (e.g., 'America/New_York', 'Europe/London').
                     Use 'UTC' as local timezone if no timezone provided by the user.

        Returns:
            Dictionary with timezone information including current time
        """
        try:
            endpoint = "/get_current_time"
            data = {"timezone": timezone}
            return await self._post_request(endpoint, data)
        except Exception as e:
            logger.error(f"Error getting current time: {str(e)}")
            return {
                "error": f"Failed to get current time: {str(e)}",
                "timezone": timezone
            }

    @function_tool
    async def convert_time(
        self,
        time: str,
        source_timezone: str,
        target_timezone: str
    ) -> Dict[str, Any]:
        """Convert time between different timezones.

        Args:
            source_timezone: Source IANA timezone name (e.g., 'America/New_York').
                             Use 'UTC' as local timezone if no source timezone provided.
            time: Time to convert in 24-hour format (HH:MM)
            target_timezone: Target IANA timezone name (e.g., 'Asia/Tokyo').
                             Use 'UTC' as local timezone if no target timezone provided.

        Returns:
            Dictionary with source and target timezone information and time difference
        """
        try:
            endpoint = "/convert_time"
            data = {
                "time": time,
                "source_timezone": source_timezone,
                "target_timezone": target_timezone
            }
            return await self._post_request(endpoint, data)
        except Exception as e:
            logger.error(f"Error converting time: {str(e)}")
            return {
                "error": f"Failed to convert time: {str(e)}",
                "source_timezone": source_timezone,
                "target_timezone": target_timezone,
                "time": time
            }

    @function_tool
    async def calculate_travel_time(
        self,
        departure_timezone: str,
        departure_time: str,
        arrival_timezone: str,
        arrival_time: str
    ) -> Dict[str, Any]:
        """Calculate travel time between departure and arrival points.

        Args:
            departure_timezone: Departure IANA timezone name
            departure_time: Departure time in 24-hour format (HH:MM)
            arrival_timezone: Arrival IANA timezone name
            arrival_time: Arrival time in 24-hour format (HH:MM)

        Returns:
            Dictionary with travel duration information accounting for timezone differences
        """
        try:
            endpoint = "/calculate_travel_time"
            data = {
                "departure_timezone": departure_timezone,
                "departure_time": departure_time,
                "arrival_timezone": arrival_timezone,
                "arrival_time": arrival_time
            }
            return await self._post_request(endpoint, data)
        except Exception as e:
            logger.error(f"Error calculating travel time: {str(e)}")
            return {
                "error": f"Failed to calculate travel time: {str(e)}",
                "departure_timezone": departure_timezone,
                "arrival_timezone": arrival_timezone
            }

    @function_tool
    async def list_timezones(self) -> Dict[str, Any]:
        """List all available IANA timezones.

        Returns:
            Dictionary with lists of timezones, grouped by region
        """
        try:
            endpoint = "/list_timezones"
            return await self._post_request(endpoint, {})
        except Exception as e:
            logger.error(f"Error listing timezones: {str(e)}")
            return {
                "error": f"Failed to list timezones: {str(e)}",
                "timezones": [],
                "count": 0
            }

    @function_tool
    async def format_date(
        self,
        date: str,
        timezone: str,
        format: str = "full",
        locale: str = "en-US"
    ) -> Dict[str, Any]:
        """Format a date according to locale and timezone.

        Args:
            date: Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
            timezone: IANA timezone name
            format: Format type ('full', 'short', 'date_only', 'time_only', 'iso')
            locale: Locale code (e.g., 'en-US', 'fr-FR')

        Returns:
            Dictionary with formatted date information
        """
        try:
            endpoint = "/format_date"
            data = {
                "date": date,
                "timezone": timezone,
                "format": format,
                "locale": locale
            }
            return await self._post_request(endpoint, data)
        except Exception as e:
            logger.error(f"Error formatting date: {str(e)}")
            return {
                "error": f"Failed to format date: {str(e)}",
                "date": date,
                "timezone": timezone
            }

# Create client instance for import by other modules
time_client = TimeMCPClient()
```

### Additional TripSage-Specific Time Service

```python
# src/mcp/time/client.py (continued)

class TimeService:
    """High-level service for time-related operations in TripSage."""

    def __init__(self, client: Optional[TimeMCPClient] = None):
        """Initialize the Time Service.

        Args:
            client: TimeMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or time_client
        logger.info("Initialized Time Service")

    async def get_local_time(self, location: str) -> Dict[str, Any]:
        """Get the current local time for a travel destination.

        Args:
            location: Travel destination (will be mapped to appropriate timezone)

        Returns:
            Dict containing current time information
        """
        # Map location to timezone - this is a simplified example
        # A real implementation would use a location-to-timezone mapping service
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
            "sydney": "Australia/Sydney",
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

        return await self.client.get_current_time(timezone)

    async def calculate_flight_arrival(
        self,
        departure_time: str,
        departure_timezone: str,
        flight_duration_hours: float,
        arrival_timezone: str
    ) -> Dict[str, Any]:
        """Calculate the arrival time for a flight.

        Args:
            departure_time: Departure time in 24-hour format (HH:MM)
            departure_timezone: Departure location timezone
            flight_duration_hours: Flight duration in hours
            arrival_timezone: Arrival location timezone

        Returns:
            Dict containing arrival time information
        """
        try:
            # Get current date in departure timezone for context
            departure_date_info = await self.client.get_current_time(departure_timezone)
            departure_date = departure_date_info["current_time"].split()[0]

            # Parse departure time
            hours, minutes = map(int, departure_time.split(':'))

            # Create datetime object for departure
            departure_dt = datetime.strptime(
                f"{departure_date} {departure_time}",
                "%Y-%m-%d %H:%M"
            )

            # Add flight duration
            duration_hours = int(flight_duration_hours)
            duration_minutes = int((flight_duration_hours - duration_hours) * 60)
            arrival_dt = departure_dt + timedelta(
                hours=duration_hours,
                minutes=duration_minutes
            )

            # Format for time conversion
            arrival_time_in_departure_tz = arrival_dt.strftime("%H:%M")

            # Convert to arrival timezone
            conversion = await self.client.convert_time(
                time=arrival_time_in_departure_tz,
                source_timezone=departure_timezone,
                target_timezone=arrival_timezone
            )

            return {
                "departure_time": departure_time,
                "departure_timezone": departure_timezone,
                "flight_duration": f"{duration_hours}h {duration_minutes}m",
                "arrival_time_departure_tz": arrival_time_in_departure_tz,
                "arrival_time_local": conversion["target_time"],
                "arrival_timezone": arrival_timezone,
                "time_difference": conversion["time_difference"],
            }
        except Exception as e:
            logger.error(f"Error calculating flight arrival: {str(e)}")
            return {
                "error": f"Failed to calculate flight arrival: {str(e)}",
                "departure_time": departure_time,
                "departure_timezone": departure_timezone,
                "arrival_timezone": arrival_timezone
            }

    async def create_timezone_aware_itinerary(self, itinerary_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create a timezone-aware itinerary for a multi-city trip.

        Args:
            itinerary_items: List of itinerary items with location, activity, and time info

        Returns:
            List of itinerary items with timezone information added
        """
        try:
            processed_itinerary = []

            for item in itinerary_items:
                # Get local timezone for the location
                location_info = await self.get_local_time(item["location"])
                location_timezone = location_info["timezone"]

                # If time is in UTC, convert to local time
                if "time" in item and item.get("time_format", "UTC") == "UTC":
                    time_conversion = await self.client.convert_time(
                        time=item["time"],
                        source_timezone="UTC",
                        target_timezone=location_timezone
                    )
                    local_time = time_conversion["target_time"]
                else:
                    local_time = item.get("time", "")

                # Add timezone information to the itinerary item
                processed_item = {
                    **item,
                    "timezone": location_timezone,
                    "local_time": local_time,
                    "utc_offset": location_info["utc_offset"] if "utc_offset" in location_info else ""
                }

                processed_itinerary.append(processed_item)

            return processed_itinerary
        except Exception as e:
            logger.error(f"Error creating timezone-aware itinerary: {str(e)}")
            return itinerary_items  # Return original items on error

    async def find_meeting_times(
        self,
        first_timezone: str,
        second_timezone: str,
        first_available_hours: tuple = (9, 17),
        second_available_hours: tuple = (9, 17)
    ) -> List[Dict[str, Any]]:
        """Find suitable meeting times across different timezones.

        Args:
            first_timezone: First participant's timezone
            second_timezone: Second participant's timezone
            first_available_hours: Tuple of (start_hour, end_hour) for first participant
            second_available_hours: Tuple of (start_hour, end_hour) for second participant

        Returns:
            List of suitable meeting times in both timezones
        """
        try:
            first_start, first_end = first_available_hours
            second_start, second_end = second_available_hours

            suitable_times = []

            # Step through each hour in the first timezone's available range
            for hour in range(first_start, first_end):
                for minute in [0, 30]:  # Check both :00 and :30 times
                    first_time = f"{hour:02d}:{minute:02d}"

                    # Convert to second timezone
                    conversion = await self.client.convert_time(
                        time=first_time,
                        source_timezone=first_timezone,
                        target_timezone=second_timezone
                    )

                    second_time = conversion["target_time"]
                    second_hour, second_minute = map(int, second_time.split(':'))

                    # Check if time is suitable (within available hours in second timezone)
                    if second_start <= second_hour < second_end:
                        suitable_times.append({
                            "first_timezone": first_timezone,
                            "first_time": first_time,
                            "second_timezone": second_timezone,
                            "second_time": second_time,
                            "time_difference": conversion["time_difference"]
                        })

            return suitable_times
        except Exception as e:
            logger.error(f"Error finding meeting times: {str(e)}")
            return []

# Create service instance for import by other modules
time_service = TimeService()
```

## OpenAI Agents SDK Integration

```python
# src/agents/travel_agent.py (example integration)
from agents import Agent, function_tool
from src.mcp.time.client import time_client, TimeService

# Create time_agent for specialized time functions
time_agent = Agent(
    name="Time Management Agent",
    instructions=(
        "You specialize in time-related calculations for travel planning. "
        "You can provide current times in different timezones and convert times "
        "between timezones to help travelers plan their itineraries effectively. "
        "Consider timezone differences when calculating flight arrivals and creating meeting schedules."
    ),
    tools=[
        time_client.get_current_time,
        time_client.convert_time,
        time_client.calculate_travel_time,
        time_client.list_timezones,
        time_client.format_date
    ]
)

# Example of integrating with the main travel agent
async def create_travel_agent():
    # Initialize services
    time_service = TimeService()

    @function_tool
    async def calculate_flight_arrival_time(
        departure_airport: str,
        arrival_airport: str,
        departure_time: str,
        flight_duration: float
    ) -> str:
        """Calculate flight arrival time accounting for timezone differences.

        Args:
            departure_airport: IATA code of departure airport (e.g., LAX)
            arrival_airport: IATA code of arrival airport (e.g., JFK)
            departure_time: Local departure time in 24-hour format (HH:MM)
            flight_duration: Flight duration in hours (e.g., 5.5)

        Returns:
            Formatted flight arrival information
        """
        # Get airport timezones (simplified example)
        airport_timezone_map = {
            "JFK": "America/New_York",
            "LAX": "America/Los_Angeles",
            "LHR": "Europe/London",
            "CDG": "Europe/Paris",
            "HND": "Asia/Tokyo",
            "SYD": "Australia/Sydney",
            # Add more as needed
        }

        departure_timezone = airport_timezone_map.get(departure_airport, "UTC")
        arrival_timezone = airport_timezone_map.get(arrival_airport, "UTC")

        result = await time_service.calculate_flight_arrival(
            departure_time=departure_time,
            departure_timezone=departure_timezone,
            flight_duration_hours=flight_duration,
            arrival_timezone=arrival_timezone
        )

        if "error" in result:
            return f"Error calculating arrival time: {result['error']}"

        return (
            f"Flight from {departure_airport} to {arrival_airport}:\n"
            f"Departure: {result['departure_time']} ({departure_timezone})\n"
            f"Flight duration: {result['flight_duration']}\n"
            f"Local arrival time: {result['arrival_time_local']} ({arrival_timezone})\n"
            f"Time difference: {result['time_difference']}"
        )

    # Create the main travel agent with the calculate_flight_arrival_time tool
    travel_agent = Agent(
        name="TripSage Travel Agent",
        instructions=(
            "You are a travel planning assistant that helps users find flights, "
            "accommodations, and activities. Use the appropriate tools to search for flights, "
            "convert time between timezones, and provide comprehensive travel plans."
        ),
        tools=[
            calculate_flight_arrival_time,
            time_client.get_current_time,
            time_client.convert_time,
            time_client.calculate_travel_time
        ],
        # Add other travel tools as needed
    )

    return travel_agent
```

## Claude Desktop Integration

For Claude Desktop, the integration leverages the MCP protocol with the FastMCP server:

```python
# Example Claude prompt addition for time tool integration

"""
You have access to time management tools to help with travel planning:

1. get_current_time - Get the current time in a specific timezone
   - Parameters: timezone (string) - IANA timezone name (e.g., 'America/New_York')

2. convert_time - Convert time between different timezones
   - Parameters:
     - time (string) - Time to convert in 24-hour format (HH:MM)
     - source_timezone (string) - Source IANA timezone name
     - target_timezone (string) - Target IANA timezone name

3. calculate_travel_time - Calculate travel time between departure and arrival points
   - Parameters:
     - departure_timezone (string) - Departure IANA timezone name
     - departure_time (string) - Departure time in 24-hour format (HH:MM)
     - arrival_timezone (string) - Arrival IANA timezone name
     - arrival_time (string) - Arrival time in 24-hour format (HH:MM)

4. list_timezones - List all available IANA timezones
   - Parameters: (none)

5. format_date - Format a date according to locale and timezone
   - Parameters:
     - date (string) - Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
     - timezone (string) - IANA timezone name
     - format (string, optional) - Format type: 'full', 'short', 'date_only', 'time_only', or 'iso'
     - locale (string, optional) - Locale code (e.g., 'en-US', 'fr-FR')

Use these tools to help users with time-related aspects of their travel planning, such as:
- Determining current local time at their destination
- Converting flight arrival/departure times between timezones
- Planning activities across multiple timezones
- Understanding time differences for international travel
- Calculating actual flight durations accounting for timezone changes
"""
```

## Example Use Cases for Travel Planning

### Determining Local Time at Destinations

```python
async def check_destination_time(destination: str):
    """Get the current local time at a travel destination."""
    result = await time_service.get_local_time(destination)
    print(f"Current time in {destination}: {result['current_time']} ({result['timezone']})")
    print(f"UTC Offset: {result['utc_offset']}")
    return result
```

This helps travelers:

- Plan communication with hotels or tour operators
- Understand business hours at their destination
- Adjust for jetlag by knowing the time difference

### Flight Arrival Time Calculation

```python
async def plan_flight_arrival(
    departure_city: str,
    departure_time: str,
    departure_timezone: str,
    flight_duration: float,
    arrival_city: str,
    arrival_timezone: str
):
    """Calculate and display flight arrival information."""
    arrival_info = await time_service.calculate_flight_arrival(
        departure_time=departure_time,
        departure_timezone=departure_timezone,
        flight_duration_hours=flight_duration,
        arrival_timezone=arrival_timezone
    )

    print(f"Flight from {departure_city} to {arrival_city}:")
    print(f"Departure: {arrival_info['departure_time']} {departure_timezone}")
    print(f"Flight duration: {arrival_info['flight_duration']}")
    print(f"Arrival (local time): {arrival_info['arrival_time_local']} {arrival_timezone}")
    print(f"Time difference: {arrival_info['time_difference']}")

    return arrival_info
```

This helps travelers:

- Understand when they'll actually arrive at their destination
- Plan for transportation upon arrival
- Determine if they'll need to book a hotel for the arrival night

### Multi-City Itinerary Planning

```python
async def create_multi_city_itinerary(itinerary_items):
    """Create a time-aware multi-city itinerary."""
    # Process itinerary items to add timezone information
    timezone_aware_itinerary = await time_service.create_timezone_aware_itinerary(itinerary_items)

    # Format for display
    formatted_itinerary = []
    for item in timezone_aware_itinerary:
        formatted_item = {
            "day": item["day"],
            "location": item["location"],
            "description": item["description"],
            "local_time": f"{item['local_time']} ({item['timezone']})",
            "activity_type": item["type"]
        }
        formatted_itinerary.append(formatted_item)

    return formatted_itinerary
```

This helps travelers:

- Create realistic day-by-day itineraries that account for time differences
- Ensure adequate connection times at airports
- Plan activities considering timezone changes

### Meeting and Event Scheduling

```python
async def schedule_calls_across_timezones(
    traveler_location: str,
    contact_location: str
):
    """Find suitable times for calls between a traveler and a contact in different locations."""
    # Get timezone for traveler's location
    traveler_info = await time_service.get_local_time(traveler_location)
    traveler_timezone = traveler_info["timezone"]

    # Get timezone for contact's location
    contact_info = await time_service.get_local_time(contact_location)
    contact_timezone = contact_info["timezone"]

    # Find suitable meeting times (business hours in both timezones)
    suitable_times = await time_service.find_meeting_times(
        first_timezone=traveler_timezone,
        second_timezone=contact_timezone,
        first_available_hours=(9, 17),  # 9 AM to 5 PM traveler's time
        second_available_hours=(9, 17)  # 9 AM to 5 PM contact's time
    )

    if not suitable_times:
        return f"No suitable meeting times found between {traveler_location} and {contact_location} during business hours."

    # Format results
    result = f"Suitable meeting times between {traveler_location} and {contact_location}:\n\n"
    for i, time in enumerate(suitable_times[:5], 1):  # Show top 5 options
        result += (
            f"{i}. {time['first_time']} in {traveler_location} ({time['first_timezone']}) = "
            f"{time['second_time']} in {contact_location} ({time['second_timezone']})\n"
        )

    result += f"\nTime difference: {suitable_times[0]['time_difference']}"

    return result
```

This helps travelers:

- Schedule meetings that respect business hours in both timezones
- Coordinate with tour operators or accommodations
- Plan video calls with family members while traveling

## Deployment Strategy

The Time MCP Server can be deployed using Docker, following TripSage's standard deployment pattern:

```dockerfile
# Dockerfile.time-mcp
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/mcp/base_mcp_server.py src/mcp/base_mcp_server.py
COPY src/mcp/time/ src/mcp/time/
COPY src/utils/logging.py src/utils/logging.py

# Set environment variables
ENV PYTHONPATH=/app
ENV TIME_MCP_SERVER_PORT=8004

# Expose port
EXPOSE 8004

# Run the server
CMD ["python", "-m", "src.mcp.time.server"]
```

## Testing Strategy

Comprehensive testing should be implemented for the Time MCP Server:

```python
# src/mcp/time/tests/test_client.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.mcp.time.client import TimeMCPClient, TimeService

@pytest.fixture
def time_client():
    """Create a time client for testing."""
    return TimeMCPClient("http://test-server")

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    server_mock = AsyncMock()
    server_mock.invoke_tool = AsyncMock()
    return server_mock

@pytest.mark.asyncio
async def test_get_current_time(time_client, mock_server):
    """Test get_current_time method."""
    # Setup mock
    with patch.object(time_client, '_post_request', return_value=AsyncMock()):
        # Create mock response
        mock_response = {
            "current_time": "2023-07-15 14:30:00",
            "timezone": "America/New_York",
            "utc_offset": "-04:00",
            "is_dst": True
        }

        time_client._post_request.return_value = mock_response

        # Call method
        result = await time_client.get_current_time("America/New_York")

        # Assertions
        assert result == mock_response
        time_client._post_request.assert_called_once_with(
            "/get_current_time",
            {"timezone": "America/New_York"}
        )

@pytest.mark.asyncio
async def test_calculate_flight_arrival(time_client):
    """Test calculate_flight_arrival method."""
    # Create TimeService with mocked client
    time_service = TimeService(time_client)

    # Setup mocks
    with patch.object(time_client, 'get_current_time') as mock_get_time, \
         patch.object(time_client, 'convert_time') as mock_convert_time:

        # Mock responses
        mock_get_time.return_value = {
            "current_time": "2023-07-15 12:00:00",
            "timezone": "America/New_York",
            "utc_offset": "-04:00",
            "is_dst": True
        }

        mock_convert_time.return_value = {
            "source_time": "15:30",
            "target_time": "21:30",
            "source_timezone": "America/New_York",
            "target_timezone": "Europe/Paris",
            "source_utc_offset": "-04:00",
            "target_utc_offset": "+02:00",
            "time_difference": "+6h"
        }

        # Call method
        result = await time_service.calculate_flight_arrival(
            departure_time="10:00",
            departure_timezone="America/New_York",
            flight_duration_hours=5.5,
            arrival_timezone="Europe/Paris"
        )

        # Assertions
        assert result["departure_time"] == "10:00"
        assert result["departure_timezone"] == "America/New_York"
        assert result["flight_duration"] == "5h 30m"
        assert result["arrival_time_local"] == "21:30"
        assert result["arrival_timezone"] == "Europe/Paris"
        assert result["time_difference"] == "+6h"
```

## Conclusion

Our Python implementation of the Time MCP Server for TripSage provides a robust solution for timezone and time management that:

1. Maintains consistent use of FastMCP 2.0 across all MCP implementations
2. Leverages the official MCP time server functionality for accuracy and standards compliance
3. Adds TripSage-specific functionality like flight arrival time calculation and itinerary timezone awareness
4. Works seamlessly with both Claude Desktop and OpenAI Agents SDK
5. Provides essential time functionality for international travel planning

This hybrid approach ensures TripSage travel plans are time-aware and timezone-correct, helping travelers manage the complexities of international travel with clear time information across different regions.
