"""
Time MCP client implementation for TripSage.

This module provides a client for the Time MCP server which handles
time-related operations like getting current time, converting between
timezones, and calculating time differences.
"""

from typing import Any, Dict, Optional

from tripsage.clients.base_client import BaseMCPClient
from tripsage.utils.logging import get_module_logger
from tripsage.utils.settings import get_settings

logger = get_module_logger(__name__)
settings = get_settings()

# Global client instance for singleton pattern
_time_client: Optional[BaseMCPClient] = None


class TimeMCPClient(BaseMCPClient):
    """Client for the Time MCP server."""

    def __init__(self):
        """Initialize the Time MCP client."""
        super().__init__(
            endpoint=settings.time_mcp.endpoint,
            api_key=(
                settings.time_mcp.api_key.get_secret_value()
                if settings.time_mcp.api_key
                else None
            ),
            server_name="time-mcp",
        )

    async def get_current_time(self, timezone: str) -> Dict[str, Any]:
        """Get the current time in a specific timezone.

        Args:
            timezone: IANA timezone name (e.g., "America/New_York")

        Returns:
            Dictionary with current time information
        """
        params = {"timezone": timezone}
        return await self.call_tool("get_current_time", params)

    async def convert_time(
        self,
        time_str: str,
        from_timezone: str,
        to_timezone: str,
        format_24h: bool = False,
    ) -> Dict[str, Any]:
        """Convert a time from one timezone to another.

        Args:
            time_str: Time string in format HH:MM or HH:MM:SS
            from_timezone: Source IANA timezone name
            to_timezone: Target IANA timezone name
            format_24h: Whether to return time in 24-hour format

        Returns:
            Dictionary with converted time information
        """
        params = {
            "time": time_str,
            "from_timezone": from_timezone,
            "to_timezone": to_timezone,
            "format_24h": format_24h,
        }
        return await self.call_tool("convert_time", params)

    async def get_time_difference(
        self, timezone1: str, timezone2: str
    ) -> Dict[str, Any]:
        """Get the time difference between two timezones.

        Args:
            timezone1: First IANA timezone name
            timezone2: Second IANA timezone name

        Returns:
            Dictionary with time difference information
        """
        params = {
            "timezone1": timezone1,
            "timezone2": timezone2,
        }
        return await self.call_tool("get_time_difference", params)


async def get_time_client() -> TimeMCPClient:
    """Get or create the Time MCP client singleton.

    Returns:
        Initialized TimeMCPClient instance
    """
    global _time_client

    if _time_client is None:
        _time_client = TimeMCPClient()
        await _time_client.initialize()

    return _time_client


async def close_time_client() -> None:
    """Close the Time MCP client singleton."""
    global _time_client

    if _time_client is not None:
        await _time_client.close()
        _time_client = None
