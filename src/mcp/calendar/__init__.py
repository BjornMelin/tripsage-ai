"""
Google Calendar MCP module for TripSage.

This module provides integration with Google Calendar through the
nspady/google-calendar-mcp Model Context Protocol server.
"""

from .client import CalendarMCPClient, CalendarService, get_client, get_service
from .models import (
    Calendar,
    CalendarListResponse,
    CreateEventParams,
    CreateItineraryEventsParams,
    CreateItineraryEventsResponse,
    DeleteEventParams,
    Event,
    EventAttendee,
    EventListResponse,
    EventReminder,
    EventSearchResponse,
    EventStatus,
    EventTime,
    EventVisibility,
    ItineraryItem,
    ItineraryItemType,
    ListCalendarsParams,
    ListEventsParams,
    SearchEventsParams,
    UpdateEventParams,
)

__all__ = [
    "CalendarMCPClient",
    "CalendarService",
    "get_client",
    "get_service",
    "Calendar",
    "CalendarListResponse",
    "CreateEventParams",
    "CreateItineraryEventsParams",
    "CreateItineraryEventsResponse",
    "DeleteEventParams",
    "Event",
    "EventAttendee",
    "EventListResponse",
    "EventReminder",
    "EventSearchResponse",
    "EventStatus",
    "EventTime",
    "EventVisibility",
    "ItineraryItem",
    "ItineraryItemType",
    "ListCalendarsParams",
    "ListEventsParams",
    "SearchEventsParams",
    "UpdateEventParams",
]
