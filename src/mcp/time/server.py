"""
Time MCP Server implementation for TripSage.

This module provides timezone conversion and time management capabilities for the
TripSage travel planning system using the FastMCP 2.0 framework.
"""

import asyncio
import datetime
import re
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

from ..fastmcp import FastMCPServer, FastMCPTool, create_tool
from ...utils.logging import get_module_logger
from ...utils.error_handling import APIError, MCPError
from ...utils.config import get_config
from ...cache.redis_cache import redis_cache
from .api_client import get_timezone_db, TimeFormat

logger = get_module_logger(__name__)
config = get_config()


class TimeMCPServer(FastMCPServer):
    """Time MCP Server for TripSage."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8004,
    ):
        """Initialize the Time MCP Server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        super().__init__(
            name="Time",
            description="Time management service for TripSage",
            version="1.0.0",
            host=host,
            port=port,
        )

        # Initialize timezone database
        self.timezone_db = get_timezone_db()

        # Register tools
        self._register_tools()

        logger.info("Initialized Time MCP Server")
    
    def _register_tools(self) -> None:
        """Register all time-related tools."""
        # Current time tool
        self.register_fast_tool(create_tool(
            name="get_current_time",
            description="Get current time in a specific timezone",
            input_schema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone name (e.g., 'America/New_York', 'Europe/London')"
                    }
                },
                "required": ["timezone"]
            },
            handler=self._get_current_time,
            output_schema={
                "type": "object",
                "properties": {
                    "current_time": {"type": "string"},
                    "timezone": {"type": "string"},
                    "utc_offset": {"type": "string"},
                    "is_dst": {"type": "boolean"}
                }
            },
            examples=[
                {
                    "input": {"timezone": "America/New_York"},
                    "output": {
                        "current_time": "2025-05-10 14:30:00",
                        "timezone": "America/New_York",
                        "utc_offset": "-04:00",
                        "is_dst": True
                    }
                }
            ]
        ))
        
        # Convert time tool
        self.register_fast_tool(create_tool(
            name="convert_time",
            description="Convert time between timezones",
            input_schema={
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "Time to convert in 24-hour format (HH:MM)"
                    },
                    "source_timezone": {
                        "type": "string",
                        "description": "Source IANA timezone name"
                    },
                    "target_timezone": {
                        "type": "string",
                        "description": "Target IANA timezone name"
                    }
                },
                "required": ["time", "source_timezone", "target_timezone"]
            },
            handler=self._convert_time,
            output_schema={
                "type": "object",
                "properties": {
                    "source_time": {"type": "string"},
                    "target_time": {"type": "string"},
                    "source_timezone": {"type": "string"},
                    "target_timezone": {"type": "string"},
                    "source_utc_offset": {"type": "string"},
                    "target_utc_offset": {"type": "string"},
                    "time_difference": {"type": "string"}
                }
            },
            examples=[
                {
                    "input": {
                        "time": "14:30",
                        "source_timezone": "America/New_York",
                        "target_timezone": "Europe/London"
                    },
                    "output": {
                        "source_time": "14:30",
                        "target_time": "19:30",
                        "source_timezone": "America/New_York",
                        "target_timezone": "Europe/London",
                        "source_utc_offset": "-04:00",
                        "target_utc_offset": "+01:00",
                        "time_difference": "+5h"
                    }
                }
            ]
        ))
        
        # Travel time calculation tool
        self.register_fast_tool(create_tool(
            name="calculate_travel_time",
            description="Calculate travel time between departure and arrival points",
            input_schema={
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
                "required": ["departure_timezone", "departure_time", "arrival_timezone", "arrival_time"]
            },
            handler=self._calculate_travel_time,
            output_schema={
                "type": "object",
                "properties": {
                    "departure": {"type": "object"},
                    "arrival": {"type": "object"},
                    "duration": {"type": "object"}
                }
            },
            examples=[
                {
                    "input": {
                        "departure_timezone": "America/New_York",
                        "departure_time": "14:30",
                        "arrival_timezone": "Europe/London",
                        "arrival_time": "02:30"
                    },
                    "output": {
                        "departure": {
                            "timezone": "America/New_York",
                            "time": "14:30",
                            "utc_time": "18:30"
                        },
                        "arrival": {
                            "timezone": "Europe/London",
                            "time": "02:30",
                            "utc_time": "01:30"
                        },
                        "duration": {
                            "hours": 7,
                            "minutes": 0,
                            "total_minutes": 420,
                            "formatted": "7h 0m"
                        }
                    }
                }
            ]
        ))
        
        # List timezones tool
        self.register_fast_tool(create_tool(
            name="list_timezones",
            description="List all available IANA timezones",
            input_schema={
                "type": "object",
                "properties": {}
            },
            handler=self._list_timezones,
            output_schema={
                "type": "object",
                "properties": {
                    "timezones": {"type": "array", "items": {"type": "string"}},
                    "grouped_timezones": {"type": "object"},
                    "count": {"type": "integer"}
                }
            }
        ))
        
        # Format date tool
        self.register_fast_tool(create_tool(
            name="format_date",
            description="Format a date according to locale and timezone",
            input_schema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone name"
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
                "required": ["date", "timezone"]
            },
            handler=self._format_date,
            output_schema={
                "type": "object",
                "properties": {
                    "formatted_date": {"type": "string"},
                    "timezone": {"type": "string"},
                    "format_type": {"type": "string"},
                    "original_date": {"type": "string"}
                }
            }
        ))
    
    async def _get_current_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get the current time in the specified timezone.

        Args:
            params: Tool parameters
                - timezone: IANA timezone name

        Returns:
            Dictionary with current time information

        Raises:
            ValueError: If the timezone is invalid
        """
        try:
            # Extract parameters
            timezone = params.get("timezone")

            # Get current time from timezone database
            result = await self.timezone_db.get_current_time(timezone)

            return result
        except Exception as e:
            logger.error("Error in get_current_time: %s", str(e))
            raise ValueError(f"Failed to get current time: {str(e)}")
    
    async def _convert_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert time between different timezones.

        Args:
            params: Tool parameters
                - time: Time to convert in 24-hour format (HH:MM)
                - source_timezone: Source IANA timezone name
                - target_timezone: Target IANA timezone name

        Returns:
            Dictionary with time conversion information

        Raises:
            ValueError: If the time format or timezones are invalid
        """
        try:
            # Extract parameters
            time_str = params.get("time")
            source_timezone = params.get("source_timezone")
            target_timezone = params.get("target_timezone")

            # Use timezone database to convert time
            result = await self.timezone_db.convert_time(
                time_str=time_str,
                source_timezone=source_timezone,
                target_timezone=target_timezone
            )

            return result
        except Exception as e:
            logger.error("Error in convert_time: %s", str(e))
            raise ValueError(f"Failed to convert time: {str(e)}")
    
    async def _calculate_travel_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate travel time between departure and arrival points.

        Args:
            params: Tool parameters
                - departure_timezone: Departure IANA timezone name
                - departure_time: Departure time in 24-hour format (HH:MM)
                - arrival_timezone: Arrival IANA timezone name
                - arrival_time: Arrival time in 24-hour format (HH:MM)

        Returns:
            Dictionary with travel time information

        Raises:
            ValueError: If the time format or timezones are invalid
        """
        try:
            # Extract parameters
            departure_timezone = params.get("departure_timezone")
            departure_time = params.get("departure_time")
            arrival_timezone = params.get("arrival_timezone")
            arrival_time = params.get("arrival_time")

            # Use timezone database to calculate travel time
            result = await self.timezone_db.calculate_travel_time(
                departure_timezone=departure_timezone,
                departure_time=departure_time,
                arrival_timezone=arrival_timezone,
                arrival_time=arrival_time
            )

            # Reformat the result to match the expected output format
            return {
                "departure": {
                    "timezone": departure_timezone,
                    "time": departure_time,
                    "utc_time": result.get("departure_time_utc", departure_time)
                },
                "arrival": {
                    "timezone": arrival_timezone,
                    "time": arrival_time,
                    "utc_time": result.get("arrival_time_utc", arrival_time)
                },
                "duration": {
                    "hours": int(result["travel_time_hours"]),
                    "minutes": int((result["travel_time_hours"] % 1) * 60),
                    "total_minutes": int(result["travel_time_hours"] * 60),
                    "formatted": result["travel_time_formatted"]
                }
            }
        except Exception as e:
            logger.error("Error in calculate_travel_time: %s", str(e))
            raise ValueError(f"Failed to calculate travel time: {str(e)}")
    
    async def _list_timezones(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all available IANA timezones.

        Args:
            params: Tool parameters (none required)

        Returns:
            Dictionary with list of timezones
        """
        try:
            # Get all available timezones from timezone database
            all_timezones = await self.timezone_db.list_timezones()

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
            logger.error("Error in list_timezones: %s", str(e))
            raise ValueError(f"Failed to list timezones: {str(e)}")
    
    async def _format_date(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Format a date according to locale and timezone.

        Args:
            params: Tool parameters
                - date: Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
                - timezone: IANA timezone name
                - format: Format type (full, short, date_only, time_only, iso)
                - locale: Locale code (e.g., 'en-US', 'fr-FR')

        Returns:
            Dictionary with formatted date information

        Raises:
            ValueError: If the date format or timezone is invalid
        """
        try:
            # Extract parameters
            date_str = params.get("date")
            timezone = params.get("timezone")
            format_type_str = params.get("format", "full")
            locale = params.get("locale", "en-US")

            # Convert format_type string to enum
            format_type = TimeFormat(format_type_str)

            # Use timezone database to format date
            result = await self.timezone_db.format_date(
                date_str=date_str,
                timezone=timezone,
                format_type=format_type,
                locale=locale
            )

            return result
        except Exception as e:
            logger.error("Error in format_date: %s", str(e))
            raise ValueError(f"Failed to format date: {str(e)}")


def create_server(host: str = "0.0.0.0", port: int = 8004):
    """Create and return a Time MCP Server instance.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        
    Returns:
        Time MCP Server instance
    """
    return TimeMCPServer(host=host, port=port)


if __name__ == "__main__":
    # Create and run the server
    server = create_server()
    server.run()
"""