"""Pydantic models for direct API integrations.

This package contains data models for the direct API service implementations,
replacing the previous MCP server abstraction layer.
"""

from tripsage_core.models.api.calendar_models import (
    CalendarEvent,
    CalendarList,
    CreateEventRequest,
    EventDateTime,
    EventReminder,
    UpdateEventRequest,
)
from tripsage_core.models.api.flights_models import (
    Airport,
    FlightOffer,
    FlightOfferRequest,
    Passenger,
    PaymentRequest,
    PriceBreakdown,
    Segment,
)
from tripsage_core.models.api.weather_models import (
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    WeatherAlert,
    WeatherCondition,
    WeatherForecast,
)


__all__ = [
    # Flight models
    "Airport",
    # Calendar models
    "CalendarEvent",
    "CalendarList",
    "CreateEventRequest",
    # Weather models
    "CurrentWeather",
    "DailyForecast",
    "EventDateTime",
    "EventReminder",
    "FlightOffer",
    "FlightOfferRequest",
    "HourlyForecast",
    "Passenger",
    "PaymentRequest",
    "PriceBreakdown",
    "Segment",
    "UpdateEventRequest",
    "WeatherAlert",
    "WeatherCondition",
    "WeatherForecast",
]
