"""
Pydantic models for direct API integrations.

This package contains data models for the direct API service implementations,
replacing the previous MCP server abstraction layer.
"""

from tripsage.models.api.calendar_models import (
    CalendarEvent,
    CalendarList,
    CreateEventRequest,
    EventDateTime,
    EventReminder,
    UpdateEventRequest,
)
from tripsage.models.api.flights_models import (
    Airport,
    FlightOffer,
    FlightOfferRequest,
    FlightSegment,
    Passenger,
    PriceBreakdown,
)
from tripsage.models.api.weather_models import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherAlert,
    WeatherCondition,
    WeatherForecast,
)

__all__ = [
    # Calendar models
    "CalendarEvent",
    "CalendarList",
    "CreateEventRequest",
    "EventDateTime",
    "EventReminder",
    "UpdateEventRequest",
    # Flight models
    "Airport",
    "FlightOffer",
    "FlightOfferRequest",
    "FlightSegment",
    "Passenger",
    "PriceBreakdown",
    # Weather models
    "CurrentWeather",
    "DailyForecast",
    "HourlyForecast",
    "WeatherAlert",
    "WeatherCondition",
    "WeatherForecast",
]