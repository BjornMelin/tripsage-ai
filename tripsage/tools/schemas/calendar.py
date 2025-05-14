"""
Google Calendar related schemas for TripSage tools.

This module provides Pydantic models for validating Google Calendar related data
when interacting with the Google Calendar MCP server.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, HttpUrl, model_validator

from tripsage.models.base import TripSageBaseResponse, TripSageModel


class EventTime(TripSageModel):
    """Model for event time information."""

    date_time: Optional[str] = Field(
        None, description="Date and time in ISO 8601 format"
    )
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    time_zone: Optional[str] = Field(None, description="Time zone name (IANA format)")

    @model_validator(mode="after")
    def validate_date_or_date_time(self):
        """Ensure either date or date_time is present, but not both."""
        if self.date_time is None and self.date is None:
            raise ValueError("Either date_time or date must be provided")
        if self.date_time is not None and self.date is not None:
            raise ValueError("Only one of date_time or date should be provided")
        return self


class EventStatus(str, Enum):
    """Event status options."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class EventAttendee(TripSageModel):
    """Model for event attendee information."""

    email: str = Field(..., description="Email address of the attendee")
    display_name: Optional[str] = Field(
        None, description="Display name of the attendee"
    )
    response_status: Optional[str] = Field(
        None,
        description=(
            "Attendee's response status (accepted, declined, needsAction, tentative)"
        ),
    )
    optional: Optional[bool] = Field(None, description="Whether attendee is optional")


class EventReminder(TripSageModel):
    """Model for event reminder information."""

    method: str = Field(..., description="Reminder method (email, popup)")
    minutes: int = Field(..., description="Minutes before event to trigger reminder")


class EventVisibility(str, Enum):
    """Event visibility options."""

    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class Calendar(TripSageModel):
    """Model for Google Calendar information."""

    id: str = Field(..., description="Unique identifier for the calendar")
    summary: str = Field(..., description="Title of the calendar")
    description: Optional[str] = Field(None, description="Description of the calendar")
    time_zone: Optional[str] = Field(None, description="Time zone of the calendar")
    primary: Optional[bool] = Field(
        None, description="Whether this is the primary calendar"
    )


class Event(TripSageModel):
    """Model for Google Calendar event information."""

    id: Optional[str] = Field(None, description="Unique identifier for the event")
    calendar_id: Optional[str] = Field(
        None, description="ID of the calendar containing the event"
    )
    summary: str = Field(..., description="Title of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    start: EventTime = Field(..., description="Start time information")
    end: EventTime = Field(..., description="End time information")
    status: Optional[EventStatus] = Field(None, description="Status of the event")
    html_link: Optional[HttpUrl] = Field(
        None, description="Link to the event in Google Calendar"
    )
    created: Optional[str] = Field(None, description="Creation time of the event")
    updated: Optional[str] = Field(None, description="Last update time of the event")
    attendees: Optional[List[EventAttendee]] = Field(
        None, description="List of attendees"
    )
    reminders: Optional[Dict[str, List[EventReminder]]] = Field(
        None, description="Reminders for the event"
    )
    recurrence: Optional[List[str]] = Field(
        None, description="Recurrence rules for the event"
    )
    visibility: Optional[EventVisibility] = Field(
        None, description="Visibility of the event"
    )
    conference_data: Optional[Dict] = Field(
        None, description="Conference data for the event"
    )


# API Request/Response Models
class ListCalendarsParams(TripSageModel):
    """Parameters for listing calendars."""

    max_results: Optional[int] = Field(
        None, description="Maximum number of calendars to return"
    )


class CalendarListResponse(TripSageBaseResponse):
    """Response model for listing calendars."""

    calendars: List[Calendar] = Field(..., description="List of calendars")
    next_page_token: Optional[str] = Field(None, description="Token for pagination")


class ListEventsParams(TripSageModel):
    """Parameters for listing events."""

    calendar_id: str = Field(..., description="ID of the calendar to list events from")
    time_min: Optional[str] = Field(None, description="Start time in ISO 8601 format")
    time_max: Optional[str] = Field(None, description="End time in ISO 8601 format")
    max_results: Optional[int] = Field(
        None, description="Maximum number of events to return"
    )
    single_events: Optional[bool] = Field(
        None, description="Whether to expand recurring events"
    )
    order_by: Optional[str] = Field(
        None, description="Order of events (startTime, updated)"
    )


class EventListResponse(TripSageBaseResponse):
    """Response model for listing events."""

    events: List[Event] = Field(..., description="List of events")
    next_page_token: Optional[str] = Field(None, description="Token for pagination")


class SearchEventsParams(TripSageModel):
    """Parameters for searching events."""

    calendar_id: str = Field(..., description="ID of the calendar to search")
    query: str = Field(..., description="Search query string")
    time_min: Optional[str] = Field(None, description="Start time in ISO 8601 format")
    time_max: Optional[str] = Field(None, description="End time in ISO 8601 format")
    max_results: Optional[int] = Field(
        None, description="Maximum number of events to return"
    )


class EventSearchResponse(TripSageBaseResponse):
    """Response model for searching events."""

    events: List[Event] = Field(..., description="List of matching events")
    next_page_token: Optional[str] = Field(None, description="Token for pagination")


class CreateEventParams(TripSageModel):
    """Parameters for creating an event."""

    calendar_id: str = Field(..., description="ID of the calendar to create event in")
    summary: str = Field(..., description="Title of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    start: EventTime = Field(..., description="Start time information")
    end: EventTime = Field(..., description="End time information")
    attendees: Optional[List[EventAttendee]] = Field(
        None, description="List of attendees"
    )
    reminders: Optional[Dict[str, List[EventReminder]]] = Field(
        None, description="Reminders for the event"
    )
    recurrence: Optional[List[str]] = Field(
        None, description="Recurrence rules for the event"
    )
    visibility: Optional[EventVisibility] = Field(
        None, description="Visibility of the event"
    )
    conference_data: Optional[Dict] = Field(
        None, description="Conference data for the event"
    )


class UpdateEventParams(TripSageModel):
    """Parameters for updating an event."""

    calendar_id: str = Field(..., description="ID of the calendar containing the event")
    event_id: str = Field(..., description="ID of the event to update")
    summary: Optional[str] = Field(None, description="New title of the event")
    description: Optional[str] = Field(None, description="New description of the event")
    location: Optional[str] = Field(None, description="New location of the event")
    start: Optional[EventTime] = Field(None, description="New start time information")
    end: Optional[EventTime] = Field(None, description="New end time information")
    attendees: Optional[List[EventAttendee]] = Field(
        None, description="New list of attendees"
    )
    reminders: Optional[Dict[str, List[EventReminder]]] = Field(
        None, description="New reminders for the event"
    )
    recurrence: Optional[List[str]] = Field(None, description="New recurrence rules")
    visibility: Optional[EventVisibility] = Field(None, description="New visibility")


class DeleteEventParams(TripSageModel):
    """Parameters for deleting an event."""

    calendar_id: str = Field(..., description="ID of the calendar containing the event")
    event_id: str = Field(..., description="ID of the event to delete")


class ItineraryItemType(str, Enum):
    """Type of itinerary item."""

    FLIGHT = "flight"
    ACCOMMODATION = "accommodation"
    ACTIVITY = "activity"
    TRANSPORTATION = "transportation"
    DINING = "dining"
    OTHER = "other"


class ItineraryItem(TripSageModel):
    """Model for a TripSage itinerary item."""

    type: ItineraryItemType = Field(..., description="Type of itinerary item")
    title: str = Field(..., description="Title of the itinerary item")
    description: Optional[str] = Field(
        None, description="Description of the itinerary item"
    )
    location: Optional[str] = Field(None, description="Location of the itinerary item")
    start_time: str = Field(..., description="Start time in ISO 8601 format")
    end_time: Optional[str] = Field(None, description="End time in ISO 8601 format")
    duration_minutes: Optional[int] = Field(
        None, description="Duration in minutes (used if end_time not provided)"
    )
    time_zone: Optional[str] = Field(None, description="Time zone (IANA format)")
    confirmation_number: Optional[str] = Field(
        None, description="Confirmation or booking number"
    )
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

    @model_validator(mode="after")
    def validate_time_info(self):
        """Ensure either end_time or duration_minutes is provided."""
        if not self.end_time and self.duration_minutes is None:
            raise ValueError("Either end_time or duration_minutes must be provided")
        return self


class CreateItineraryEventsParams(TripSageModel):
    """Parameters for creating events from an itinerary."""

    calendar_id: str = Field(..., description="ID of the calendar to create events in")
    itinerary_items: List[ItineraryItem] = Field(
        ..., description="List of itinerary items to convert to events"
    )
    trip_name: Optional[str] = Field(
        None, description="Name of the trip for event grouping"
    )


class CreateItineraryEventsResponse(TripSageBaseResponse):
    """Response for creating events from an itinerary."""

    created_events: List[Event] = Field(..., description="List of created events")
    failed_items: List[Dict[str, Any]] = Field(
        ..., description="List of items that failed to create with errors"
    )
    trip_name: Optional[str] = Field(None, description="Name of the trip")
