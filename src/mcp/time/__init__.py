"""
Time API for the TripSage travel planning system.

This module provides tools for handling time and timezone operations.
"""

from ...utils.logging import get_module_logger
from .client import TimeMCPClient, TimeService, get_client, get_service
from .models import (
    ConvertTimeParams,
    FlightArrivalResponse,
    GetCurrentTimeParams,
    ItineraryItem,
    MeetingTimeResponse,
    TimeConversionResponse,
    TimeInfo,
    TimeResponse,
    TimezoneAwareItineraryItem,
)
from .server import TimeMCPServer, create_server

logger = get_module_logger(__name__)

# Tool schemas for OpenAI Agents SDK and Claude integration
GET_CURRENT_TIME_SCHEMA = {
    "name": "get_current_time",
    "description": "Get current time in a specific timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": (
                    "IANA timezone name (e.g., 'America/New_York', "
                    "'Europe/London'). Use 'UTC' as local timezone if no "
                    "timezone provided by the user."
                ),
            }
        },
        "required": ["timezone"],
    },
}

CONVERT_TIME_SCHEMA = {
    "name": "convert_time",
    "description": "Convert time between timezones",
    "parameters": {
        "type": "object",
        "properties": {
            "time": {
                "type": "string",
                "description": "Time to convert in 24-hour format (HH:MM)",
            },
            "source_timezone": {
                "type": "string",
                "description": (
                    "Source IANA timezone name (e.g., 'America/New_York', "
                    "'Europe/London'). Use 'UTC' as local timezone if no source "
                    "timezone provided by the user."
                ),
            },
            "target_timezone": {
                "type": "string",
                "description": (
                    "Target IANA timezone name (e.g., 'Asia/Tokyo', "
                    "'America/San_Francisco'). Use 'UTC' as local timezone if "
                    "no target timezone provided by the user."
                ),
            },
        },
        "required": ["source_timezone", "time", "target_timezone"],
    },
}

CALCULATE_TRAVEL_TIME_SCHEMA = {
    "name": "calculate_travel_time",
    "description": "Calculate travel time between departure and arrival points",
    "parameters": {
        "type": "object",
        "properties": {
            "departure_timezone": {
                "type": "string",
                "description": (
                    "Departure IANA timezone name (e.g., 'America/New_York', "
                    "'Europe/London'). Use 'UTC' as local timezone if no "
                    "departure timezone provided by the user."
                ),
            },
            "departure_time": {
                "type": "string",
                "description": "Departure time in 24-hour format (HH:MM)",
            },
            "arrival_timezone": {
                "type": "string",
                "description": (
                    "Arrival IANA timezone name (e.g., 'Asia/Tokyo', "
                    "'America/San_Francisco'). Use 'UTC' as local timezone if "
                    "no arrival timezone provided by the user."
                ),
            },
            "arrival_time": {
                "type": "string",
                "description": "Arrival time in 24-hour format (HH:MM)",
            },
        },
        "required": [
            "departure_timezone",
            "departure_time",
            "arrival_timezone",
            "arrival_time",
        ],
    },
}

LIST_TIMEZONES_SCHEMA = {
    "name": "list_timezones",
    "description": "List all available IANA timezones",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

FORMAT_DATE_SCHEMA = {
    "name": "format_date",
    "description": "Format a date according to locale and timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": (
                    "Date string in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS) "
                    "or YYYY-MM-DD"
                ),
            },
            "timezone": {
                "type": "string",
                "description": (
                    "IANA timezone name (e.g., 'America/New_York', 'Europe/London') "
                    "Use 'UTC' as local timezone if no timezone provided by the user."
                ),
            },
            "format": {
                "type": "string",
                "description": (
                    "Format type: 'full', 'short', 'date_only', 'time_only', or 'iso'"
                ),
                "enum": ["full", "short", "date_only", "time_only", "iso"],
                "default": "full",
            },
            "locale": {
                "type": "string",
                "description": "Locale code (e.g., 'en-US', 'fr-FR')",
                "default": "en-US",
            },
        },
        "required": ["date", "timezone"],
    },
}

# Export tool schemas for OpenAI Agent SDK integration
TIME_TOOL_SCHEMAS = [
    GET_CURRENT_TIME_SCHEMA,
    CONVERT_TIME_SCHEMA,
    CALCULATE_TRAVEL_TIME_SCHEMA,
    LIST_TIMEZONES_SCHEMA,
    FORMAT_DATE_SCHEMA,
]

# For direct import
__all__ = [
    # Client and service classes
    "TimeMCPClient",
    "TimeService",
    "TimeMCPServer",
    "get_client",
    "get_service",
    "create_server",
    # Schemas
    "TIME_TOOL_SCHEMAS",
    # Models
    "GetCurrentTimeParams",
    "TimeResponse",
    "ConvertTimeParams",
    "TimeConversionResponse",
    "ItineraryItem",
    "TimezoneAwareItineraryItem",
    "FlightArrivalResponse",
    "MeetingTimeResponse",
    "TimeInfo",
]
