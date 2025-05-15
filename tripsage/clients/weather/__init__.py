"""
Weather client module for TripSage.

This module provides clients for communicating with weather service providers,
including the Weather MCP server.
"""

from tripsage.clients.weather.weather_mcp_client import WeatherMCPClient

__all__ = ["WeatherMCPClient"]
