"""
Direct API integrations for TripSage services.

This package contains service implementations that directly integrate with
external APIs, replacing the previous MCP (Model Context Protocol) server
abstraction layer for improved performance and simplicity.

Services included:
- Google Calendar API
- Duffel Flights API
- OpenWeatherMap API
"""

from tripsage.services.api.calendar_service import GoogleCalendarService
from tripsage.services.api.flights_service import DuffelFlightsService
from tripsage.services.api.weather_service import OpenWeatherMapService

__all__ = [
    "GoogleCalendarService",
    "DuffelFlightsService",
    "OpenWeatherMapService",
]
