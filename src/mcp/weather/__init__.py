"""Weather MCP server and client for TripSage."""

from .client import WeatherMCPClient, WeatherService, get_client, get_service
from .server import WeatherMCPServer, create_server

# Tool schemas for AI agent integration
# OpenAI Agents SDK format
GET_CURRENT_WEATHER_SCHEMA = {
    "name": "get_current_weather",
    "description": "Get current weather conditions for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name (e.g., 'Paris')"},
            "country": {
                "type": "string",
                "description": "Country code (e.g., 'FR' for France)",
            },
            "lat": {"type": "number", "description": "Latitude coordinate"},
            "lon": {"type": "number", "description": "Longitude coordinate"},
        },
        "anyOf": [{"required": ["lat", "lon"]}, {"required": ["city"]}],
    },
}

GET_FORECAST_SCHEMA = {
    "name": "get_forecast",
    "description": "Get weather forecast for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name (e.g., 'Paris')"},
            "country": {
                "type": "string",
                "description": "Country code (e.g., 'FR' for France)",
            },
            "lat": {"type": "number", "description": "Latitude coordinate"},
            "lon": {"type": "number", "description": "Longitude coordinate"},
            "days": {
                "type": "integer",
                "minimum": 1,
                "maximum": 16,
                "default": 5,
                "description": "Number of forecast days",
            },
        },
        "anyOf": [{"required": ["lat", "lon"]}, {"required": ["city"]}],
    },
}

GET_TRAVEL_RECOMMENDATION_SCHEMA = {
    "name": "get_travel_recommendation",
    "description": "Get travel recommendations based on weather conditions",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name (e.g., 'Paris')"},
            "country": {
                "type": "string",
                "description": "Country code (e.g., 'FR' for France)",
            },
            "lat": {"type": "number", "description": "Latitude coordinate"},
            "lon": {"type": "number", "description": "Longitude coordinate"},
            "start_date": {
                "type": "string",
                "format": "date",
                "description": "Trip start date (YYYY-MM-DD)",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "description": "Trip end date (YYYY-MM-DD)",
            },
            "activities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Planned activities (e.g., ['hiking', 'sightseeing'])",
            },
        },
        "anyOf": [{"required": ["lat", "lon"]}, {"required": ["city"]}],
    },
}

COMPARE_DESTINATIONS_SCHEMA = {
    "name": "compare_destinations_weather",
    "description": "Compare weather across multiple potential destinations",
    "parameters": {
        "type": "object",
        "properties": {
            "destinations": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of destinations to compare "
                    "(e.g., ['Paris, FR', 'London, GB'])"
                ),
            },
            "date": {
                "type": "string",
                "format": "date",
                "description": (
                    "Date for comparison (YYYY-MM-DD). "
                    "If not provided, uses current date."
                ),
            },
        },
        "required": ["destinations"],
    },
}

GET_OPTIMAL_TRAVEL_TIME_SCHEMA = {
    "name": "get_optimal_travel_time",
    "description": (
        "Get recommendations for the optimal time to travel to a destination"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Travel destination (e.g., 'Paris, FR')",
            },
            "activity_type": {
                "type": "string",
                "description": (
                    "Type of activity planned (e.g., 'beach', 'skiing', 'sightseeing')"
                ),
                "default": "general",
            },
            "months_ahead": {
                "type": "integer",
                "description": "How many months ahead to consider",
                "default": 6,
            },
        },
        "required": ["destination"],
    },
}

# Full schemas list - use this to register tools with agent frameworks
WEATHER_TOOL_SCHEMAS = [
    GET_CURRENT_WEATHER_SCHEMA,
    GET_FORECAST_SCHEMA,
    GET_TRAVEL_RECOMMENDATION_SCHEMA,
    COMPARE_DESTINATIONS_SCHEMA,
    GET_OPTIMAL_TRAVEL_TIME_SCHEMA,
]

# For Claude integration
WEATHER_CLAUDE_TOOLS = [
    {
        "name": "get_current_weather",
        "description": "Get current weather conditions for a location",
        "input_schema": GET_CURRENT_WEATHER_SCHEMA["parameters"],
    },
    {
        "name": "get_forecast",
        "description": "Get weather forecast for a location",
        "input_schema": GET_FORECAST_SCHEMA["parameters"],
    },
    {
        "name": "get_travel_recommendation",
        "description": "Get travel recommendations based on weather conditions",
        "input_schema": GET_TRAVEL_RECOMMENDATION_SCHEMA["parameters"],
    },
    {
        "name": "compare_destinations_weather",
        "description": "Compare weather across multiple potential destinations",
        "input_schema": COMPARE_DESTINATIONS_SCHEMA["parameters"],
    },
    {
        "name": "get_optimal_travel_time",
        "description": (
            "Get recommendations for the optimal time to travel to a destination"
        ),
        "input_schema": GET_OPTIMAL_TRAVEL_TIME_SCHEMA["parameters"],
    },
]

__all__ = [
    "WeatherMCPServer",
    "create_server",
    "WeatherMCPClient",
    "WeatherService",
    "get_client",
    "get_service",
    "GET_CURRENT_WEATHER_SCHEMA",
    "GET_FORECAST_SCHEMA",
    "GET_TRAVEL_RECOMMENDATION_SCHEMA",
    "COMPARE_DESTINATIONS_SCHEMA",
    "GET_OPTIMAL_TRAVEL_TIME_SCHEMA",
    "WEATHER_TOOL_SCHEMAS",
    "WEATHER_CLAUDE_TOOLS",
]
