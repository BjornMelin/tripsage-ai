"""
Time MCP Client implementation for TripSage.

This module provides a client for interacting with the Time MCP Server,
which offers timezone conversion and time management capabilities.
"""

import datetime
from typing import Any, Dict, List, Optional

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..fastmcp import FastMCPClient

logger = get_module_logger(__name__)
config = get_config()


class TimeMCPClient(FastMCPClient):
    """Client for the Time MCP Server."""

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

    @redis_cache.cached("time_current", 300)  # 5 minutes (time changes!)
    async def get_current_time(
        self, timezone: str, skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Get the current time in the specified timezone.

        Args:
            timezone: IANA timezone name (e.g., 'America/New_York', 'Europe/London')
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with current time information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            return await self.call_tool(
                "get_current_time", {"timezone": timezone}, skip_cache=skip_cache
            )
        except Exception as e:
            logger.error(f"Error getting current time: {str(e)}")
            raise MCPError(
                message=f"Failed to get current time: {str(e)}",
                server=self.server_name,
                tool="get_current_time",
                params={"timezone": timezone},
            ) from e

    @redis_cache.cached("time_convert", 3600)  # 1 hour (timezone offsets are stable)
    async def convert_time(
        self,
        time: str,
        source_timezone: str,
        target_timezone: str,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Convert time between different timezones.

        Args:
            time: Time to convert in 24-hour format (HH:MM)
            source_timezone: Source IANA timezone name
            target_timezone: Target IANA timezone name
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with time conversion information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            params = {
                "time": time,
                "source_timezone": source_timezone,
                "target_timezone": target_timezone,
            }
            return await self.call_tool("convert_time", params, skip_cache=skip_cache)
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

    @redis_cache.cached("time_travel", 3600)  # 1 hour
    async def calculate_travel_time(
        self,
        departure_timezone: str,
        departure_time: str,
        arrival_timezone: str,
        arrival_time: str,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Calculate travel time between departure and arrival points.

        Args:
            departure_timezone: Departure IANA timezone name
            departure_time: Departure time in 24-hour format (HH:MM)
            arrival_timezone: Arrival IANA timezone name
            arrival_time: Arrival time in 24-hour format (HH:MM)
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with travel time information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            params = {
                "departure_timezone": departure_timezone,
                "departure_time": departure_time,
                "arrival_timezone": arrival_timezone,
                "arrival_time": arrival_time,
            }
            return await self.call_tool(
                "calculate_travel_time", params, skip_cache=skip_cache
            )
        except Exception as e:
            logger.error(f"Error calculating travel time: {str(e)}")
            raise MCPError(
                message=f"Failed to calculate travel time: {str(e)}",
                server=self.server_name,
                tool="calculate_travel_time",
                params=params,
            ) from e

    @redis_cache.cached(
        "time_timezones", 86400
    )  # 24 hours (timezones don't change often)
    async def list_timezones(self, skip_cache: bool = False) -> Dict[str, Any]:
        """List all available IANA timezones.

        Args:
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with list of timezones

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            return await self.call_tool("list_timezones", {}, skip_cache=skip_cache)
        except Exception as e:
            logger.error(f"Error listing timezones: {str(e)}")
            raise MCPError(
                message=f"Failed to list timezones: {str(e)}",
                server=self.server_name,
                tool="list_timezones",
                params={},
            ) from e

    @redis_cache.cached("time_format", 3600)  # 1 hour
    async def format_date(
        self,
        date: str,
        timezone: str,
        format: str = "full",
        locale: str = "en-US",
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Format a date according to locale and timezone.

        Args:
            date: Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
            timezone: IANA timezone name
            format: Format type (full, short, date_only, time_only, iso)
            locale: Locale code (e.g., 'en-US', 'fr-FR')
            skip_cache: Whether to skip the cache

        Returns:
            Dictionary with formatted date information

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            params = {
                "date": date,
                "timezone": timezone,
                "format": format,
                "locale": locale,
            }
            return await self.call_tool("format_date", params, skip_cache=skip_cache)
        except Exception as e:
            logger.error(f"Error formatting date: {str(e)}")
            raise MCPError(
                message=f"Failed to format date: {str(e)}",
                server=self.server_name,
                tool="format_date",
                params=params,
            ) from e


class TimeService:
    """High-level service for time-related operations in TripSage."""

    def __init__(self, client: Optional[TimeMCPClient] = None):
        """Initialize the Time Service.

        Args:
            client: TimeMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or get_client()
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
            hours, minutes = map(int, departure_time.split(":"))

            # Create datetime object for departure
            departure_dt = datetime.datetime.strptime(
                f"{departure_date} {departure_time}", "%Y-%m-%d %H:%M"
            )

            # Add flight duration
            duration_hours = int(flight_duration_hours)
            duration_minutes = int((flight_duration_hours - duration_hours) * 60)
            arrival_dt = departure_dt + datetime.timedelta(
                hours=duration_hours, minutes=duration_minutes
            )

            # Format for time conversion
            arrival_time_in_departure_tz = arrival_dt.strftime("%H:%M")

            # Convert to arrival timezone
            conversion = await self.client.convert_time(
                time=arrival_time_in_departure_tz,
                source_timezone=departure_timezone,
                target_timezone=arrival_timezone,
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
                "arrival_timezone": arrival_timezone,
            }

    async def create_timezone_aware_itinerary(
        self, itinerary_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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
                # Get local timezone for the location
                location_info = await self.get_local_time(item["location"])
                location_timezone = location_info["timezone"]

                # If time is in UTC, convert to local time
                if "time" in item and item.get("time_format", "UTC") == "UTC":
                    time_conversion = await self.client.convert_time(
                        time=item["time"],
                        source_timezone="UTC",
                        target_timezone=location_timezone,
                    )
                    local_time = time_conversion["target_time"]
                else:
                    local_time = item.get("time", "")

                # Add timezone information to the itinerary item
                processed_item = {
                    **item,
                    "timezone": location_timezone,
                    "local_time": local_time,
                    "utc_offset": (
                        location_info["utc_offset"]
                        if "utc_offset" in location_info
                        else ""
                    ),
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
        second_available_hours: tuple = (9, 17),
    ) -> List[Dict[str, Any]]:
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

                    second_time = conversion["target_time"]
                    second_hour, second_minute = map(int, second_time.split(":"))

                    # Check if time is suitable (w/i available hours in second timezone)
                    if second_start <= second_hour < second_end:
                        suitable_times.append(
                            {
                                "first_timezone": first_timezone,
                                "first_time": first_time,
                                "second_timezone": second_timezone,
                                "second_time": second_time,
                                "time_difference": conversion["time_difference"],
                            }
                        )

            return suitable_times
        except Exception as e:
            logger.error(f"Error finding meeting times: {str(e)}")
            return []


def get_client() -> TimeMCPClient:
    """Get a Time MCP Client instance.

    Returns:
        TimeMCPClient instance
    """
    return TimeMCPClient()


def get_service() -> TimeService:
    """Get a Time Service instance.

    Returns:
        TimeService instance
    """
    return TimeService(get_client())
