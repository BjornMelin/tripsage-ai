"""
Time MCP Client implementation for TripSage.

This module provides a client for interacting with the Model Context Protocol's
Time MCP Server, which offers timezone conversion and time management capabilities.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from agents import function_tool

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..fastmcp import FastMCPClient
from .models import (
    ConvertTimeParams,
    FlightArrivalResponse,
    GetCurrentTimeParams,
    ItineraryItem,
    MeetingTimeResponse,
    TimeConversionResponse,
    TimeResponse,
    TimezoneAwareItineraryItem,
)

logger = get_module_logger(__name__)
config = get_config()


class TimeMCPClient(FastMCPClient):
    """Client for the official Time MCP Server."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True,
    ):
        """Initialize the Time MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        if endpoint is None:
            endpoint = (
                config.time_mcp.endpoint
                if hasattr(config, "time_mcp")
                else "http://localhost:8004"
            )

        api_key = api_key or (
            config.time_mcp.api_key if hasattr(config, "time_mcp") else None
        )

        super().__init__(
            server_name="Time",
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=1800,  # 30 minutes default cache TTL for time data
        )

    @function_tool
    @redis_cache.cached("time_current", 60)  # Cache for 1 minute since time changes
    async def get_current_time(
        self, timezone: str, skip_cache: bool = False
    ) -> TimeResponse:
        """Get the current time in the specified timezone.

        Args:
            timezone: IANA timezone name (e.g., 'America/New_York', 'Europe/London')
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with current time information

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters with Pydantic model
            _params = GetCurrentTimeParams(timezone=timezone)

            # Call the MCP tool with validated parameters
            response = await self.call_tool(
                "get_current_time", {"timezone": timezone}, skip_cache=skip_cache
            )

            # Parse the response string into a dictionary
            if isinstance(response, str):
                response = json.loads(response)

            # Transform response to match our expected format
            result = {
                "timezone": response.get("timezone"),
                "current_time": response.get("datetime").split("T")[1].split("+")[0],
                "current_date": response.get("datetime").split("T")[0],
                "utc_offset": (
                    response.get("datetime").split("+")[1]
                    if "+" in response.get("datetime", "")
                    else response.get("datetime").split("-")[-1]
                ),
                "is_dst": response.get("is_dst", False),
            }

            # Validate response with Pydantic model
            return TimeResponse.model_validate(result)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for get_current_time: {str(e)}",
                server=self.server_name,
                tool="get_current_time",
                params={"timezone": timezone},
            ) from e
        except Exception as e:
            logger.error(f"Error getting current time: {str(e)}")
            raise MCPError(
                message=f"Failed to get current time: {str(e)}",
                server=self.server_name,
                tool="get_current_time",
                params={"timezone": timezone},
            ) from e

    @function_tool
    @redis_cache.cached("time_convert", 3600)  # 1 hour (timezone offsets are stable)
    async def convert_time(
        self,
        time: str,
        source_timezone: str,
        target_timezone: str,
        skip_cache: bool = False,
    ) -> TimeConversionResponse:
        """Convert time between different timezones.

        Args:
            time: Time to convert in 24-hour format (HH:MM)
            source_timezone: Source IANA timezone name
            target_timezone: Target IANA timezone name
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with time conversion information

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters with Pydantic model
            _params = ConvertTimeParams(
                time=time,
                source_timezone=source_timezone,
                target_timezone=target_timezone,
            )

            # Call the MCP tool with validated parameters
            response = await self.call_tool(
                "convert_time",
                {
                    "source_timezone": source_timezone,
                    "time": time,
                    "target_timezone": target_timezone,
                },
                skip_cache=skip_cache,
            )

            # Parse the response string into a dictionary
            if isinstance(response, str):
                response = json.loads(response)

            # Extract the relevant information
            source_info = response.get("source", {})
            target_info = response.get("target", {})

            # Build and validate the response model
            conversion_response = {
                "source": {
                    "timezone": source_info.get("timezone"),
                    "datetime": source_info.get("datetime", ""),
                    "is_dst": source_info.get("is_dst", False),
                },
                "target": {
                    "timezone": target_info.get("timezone"),
                    "datetime": target_info.get("datetime", ""),
                    "is_dst": target_info.get("is_dst", False),
                },
                "time_difference": response.get("time_difference", ""),
            }

            # Validate with Pydantic model
            return TimeConversionResponse.model_validate(conversion_response)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for convert_time: {str(e)}",
                server=self.server_name,
                tool="convert_time",
                params={
                    "time": time,
                    "source_timezone": source_timezone,
                    "target_timezone": target_timezone,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error converting time: {str(e)}")
            raise MCPError(
                message=f"Failed to convert time: {str(e)}",
                server=self.server_name,
                tool="convert_time",
                params={
                    "time": time,
                    "source_timezone": source_timezone,
                    "target_timezone": target_timezone,
                },
            ) from e


class TimeService:
    """High-level service for time-related operations in TripSage."""

    def __init__(self, client: Optional[TimeMCPClient] = None):
        """Initialize the Time Service.

        Args:
            client: TimeMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or time_client
        logger.info("Initialized Time Service")

    async def get_local_time(self, location: str) -> TimeResponse:
        """Get the current local time for a travel destination.

        Args:
            location: Travel destination (will be mapped to appropriate timezone)

        Returns:
            Dictionary containing current time information
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
            logger.warning(
                f"No timezone mapping found for location: {location}, using UTC"
            )

        return await self.client.get_current_time(timezone)

    async def calculate_flight_arrival(
        self,
        departure_time: str,
        departure_timezone: str,
        flight_duration_hours: float,
        arrival_timezone: str,
    ) -> FlightArrivalResponse:
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
            departure_date = departure_date_info.current_date

            # Parse departure time
            hours, minutes = map(int, departure_time.split(":"))

            # Create datetime object for departure
            _departure_dt = datetime.strptime(
                f"{departure_date} {departure_time}", "%Y-%m-%d %H:%M"
            )

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

            arrival_day_offset = 0
            while arrival_hours >= 24:
                arrival_day_offset += 1
                arrival_hours -= 24

            # Format arrival time
            arrival_time_in_departure_tz = f"{arrival_hours:02d}:{arrival_minutes:02d}"

            # Convert to arrival timezone
            conversion = await self.client.convert_time(
                time=arrival_time_in_departure_tz,
                source_timezone=departure_timezone,
                target_timezone=arrival_timezone,
            )

            # Create and validate response
            result = {
                "departure_time": departure_time,
                "departure_timezone": departure_timezone,
                "flight_duration": f"{duration_hours}h {duration_minutes}m",
                "arrival_time_departure_tz": arrival_time_in_departure_tz,
                "arrival_time_local": conversion.target.datetime.split("T")[1].split(
                    "+"
                )[0],
                "arrival_timezone": arrival_timezone,
                "time_difference": conversion.time_difference,
                "day_offset": arrival_day_offset,
            }

            return FlightArrivalResponse.model_validate(result)
        except Exception as e:
            logger.error(f"Error calculating flight arrival: {str(e)}")
            error_result = {
                "error": f"Failed to calculate flight arrival: {str(e)}",
                "departure_time": departure_time,
                "departure_timezone": departure_timezone,
                "flight_duration": "",
                "arrival_time_departure_tz": "",
                "arrival_time_local": "",
                "arrival_timezone": arrival_timezone,
                "time_difference": "",
                "day_offset": 0,
            }
            return FlightArrivalResponse.model_validate(error_result)

    async def create_timezone_aware_itinerary(
        self, itinerary_items: List[Dict[str, Any]]
    ) -> List[TimezoneAwareItineraryItem]:
        """Create a timezone-aware itinerary for a multi-city trip.

        Args:
            itinerary_items: List of itinerary items with location,
                activity, and time info

        Returns:
            List of itinerary items with timezone information added
        """
        try:
            processed_itinerary = []

            for item in itinerary_items:
                # Validate input item
                item_model = ItineraryItem.model_validate(item)

                # Get local timezone for the location
                location_info = await self.get_local_time(item_model.location)
                location_timezone = location_info.timezone

                # If time is in UTC, convert to local time
                local_time = item_model.time or ""
                if item_model.time and item_model.time_format == "UTC":
                    time_conversion = await self.client.convert_time(
                        time=item_model.time,
                        source_timezone="UTC",
                        target_timezone=location_timezone,
                    )
                    local_time = time_conversion.target.datetime.split("T")[1].split(
                        "+"
                    )[0]

                # Add timezone information to the itinerary item
                processed_item = {
                    "location": item_model.location,
                    "activity": item_model.activity,
                    "time": item_model.time,
                    "time_format": item_model.time_format,
                    "timezone": location_timezone,
                    "local_time": local_time,
                    "utc_offset": location_info.utc_offset,
                }

                # Add any extra fields from the original item
                for key, value in item.items():
                    if key not in processed_item:
                        processed_item[key] = value

                processed_itinerary.append(
                    TimezoneAwareItineraryItem.model_validate(processed_item)
                )

            return processed_itinerary
        except Exception as e:
            logger.error(f"Error creating timezone-aware itinerary: {str(e)}")
            return [
                TimezoneAwareItineraryItem.model_validate(item)
                for item in itinerary_items
            ]

    async def find_meeting_times(
        self,
        first_timezone: str,
        second_timezone: str,
        first_available_hours: tuple = (9, 17),
        second_available_hours: tuple = (9, 17),
    ) -> List[MeetingTimeResponse]:
        """Find suitable meeting times across different timezones.

        Args:
            first_timezone: First participant's timezone
            second_timezone: Second participant's timezone
            first_available_hours: Tuple of (start_hour, end_hour)
                for first participant
            second_available_hours: Tuple of (start_hour, end_hour)
                for second participant

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
                        target_timezone=second_timezone,
                    )

                    second_time = conversion.target.datetime.split("T")[1].split("+")[0]
                    second_hour, second_minute = map(int, second_time.split(":")[0:2])

                    # Check if time is suitable (w/i available hours in second timezone)
                    if second_start <= second_hour < second_end:
                        meeting_time = {
                            "first_timezone": first_timezone,
                            "first_time": first_time,
                            "second_timezone": second_timezone,
                            "second_time": second_time,
                            "time_difference": conversion.time_difference,
                        }
                        suitable_times.append(
                            MeetingTimeResponse.model_validate(meeting_time)
                        )

            return suitable_times
        except Exception as e:
            logger.error(f"Error finding meeting times: {str(e)}")
            return []


# Initialize global client instance
time_client = TimeMCPClient()


def get_client() -> TimeMCPClient:
    """Get a Time MCP Client instance.

    Returns:
        TimeMCPClient instance
    """
    return time_client


def get_service() -> TimeService:
    """Get a Time Service instance.

    Returns:
        TimeService instance
    """
    return TimeService(time_client)
