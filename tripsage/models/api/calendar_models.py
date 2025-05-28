"""
Pydantic models for Google Calendar API integration.

This module provides comprehensive data models for Google Calendar operations,
including event management, reminders, and travel-specific features.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EventVisibility(str, Enum):
    """Event visibility options."""

    DEFAULT = "default"
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


class EventStatus(str, Enum):
    """Event status options."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class AttendeeResponseStatus(str, Enum):
    """Attendee response status options."""

    NEEDS_ACTION = "needsAction"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    ACCEPTED = "accepted"


class ReminderMethod(str, Enum):
    """Reminder notification methods."""

    EMAIL = "email"
    POPUP = "popup"
    SMS = "sms"


class RecurrenceFrequency(str, Enum):
    """Event recurrence frequency options."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class EventDateTime(BaseModel):
    """Date/time representation for events."""

    model_config = ConfigDict(populate_by_name=True)

    date_time: Optional[datetime] = Field(None, alias="dateTime")
    date: Optional[str] = Field(
        None, description="Date in YYYY-MM-DD format for all-day events"
    )
    time_zone: Optional[str] = Field(
        None, alias="timeZone", description="IANA time zone"
    )

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class EventReminder(BaseModel):
    """Event reminder configuration."""

    method: ReminderMethod = Field(default=ReminderMethod.POPUP)
    minutes: int = Field(
        ge=0, le=40320, description="Minutes before event (max 4 weeks)"
    )


class EventAttendee(BaseModel):
    """Event attendee information."""

    model_config = ConfigDict(populate_by_name=True)

    email: str
    display_name: Optional[str] = Field(None, alias="displayName")
    optional: bool = False
    response_status: AttendeeResponseStatus = AttendeeResponseStatus.NEEDS_ACTION
    comment: Optional[str] = None
    additional_guests: int = Field(0, ge=0, alias="additionalGuests")


class ConferenceData(BaseModel):
    """Conference/meeting information for events."""

    model_config = ConfigDict(populate_by_name=True)

    conference_id: Optional[str] = Field(None, alias="conferenceId")
    conference_solution: Optional[Dict[str, Any]] = Field(
        None, alias="conferenceSolution"
    )
    entry_points: Optional[List[Dict[str, Any]]] = Field(None, alias="entryPoints")
    notes: Optional[str] = None


class ExtendedProperties(BaseModel):
    """Extended properties for storing custom metadata."""

    private: Dict[str, str] = Field(default_factory=dict)
    shared: Dict[str, str] = Field(default_factory=dict)


class CalendarEvent(BaseModel):
    """Complete calendar event model."""

    model_config = ConfigDict(populate_by_name=True)

    # Core fields
    id: Optional[str] = None
    etag: Optional[str] = None
    status: EventStatus = EventStatus.CONFIRMED
    html_link: Optional[HttpUrl] = Field(None, alias="htmlLink")
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    # Event details
    summary: str = Field(..., description="Event title")
    description: Optional[str] = None
    location: Optional[str] = None
    color_id: Optional[str] = Field(None, alias="colorId")

    # Timing
    start: EventDateTime
    end: EventDateTime
    end_time_unspecified: bool = Field(False, alias="endTimeUnspecified")
    recurrence: Optional[List[str]] = Field(
        None, description="RFC5545 recurrence rules"
    )
    recurring_event_id: Optional[str] = Field(None, alias="recurringEventId")
    original_start_time: Optional[EventDateTime] = Field(
        None, alias="originalStartTime"
    )

    # Visibility and access
    transparency: str = Field("opaque", description="opaque or transparent")
    visibility: EventVisibility = EventVisibility.DEFAULT
    ical_uid: Optional[str] = Field(None, alias="iCalUID")
    sequence: int = 0

    # Participants
    attendees: List[EventAttendee] = Field(default_factory=list)
    attendees_omitted: bool = Field(False, alias="attendeesOmitted")
    extended_properties: Optional[ExtendedProperties] = Field(
        None, alias="extendedProperties"
    )
    hangout_link: Optional[HttpUrl] = Field(None, alias="hangoutLink")
    conference_data: Optional[ConferenceData] = Field(None, alias="conferenceData")

    # Notifications
    reminders: Dict[str, Any] = Field(default_factory=lambda: {"useDefault": True})

    # Organization
    organizer: Optional[Dict[str, Any]] = None
    creator: Optional[Dict[str, Any]] = None

    # Travel-specific extensions
    travel_metadata: Optional[Dict[str, Any]] = Field(
        None, description="TripSage travel-specific metadata"
    )


class CreateEventRequest(BaseModel):
    """Request model for creating calendar events."""

    model_config = ConfigDict(populate_by_name=True)

    summary: str = Field(..., min_length=1, max_length=1024)
    description: Optional[str] = Field(None, max_length=8192)
    location: Optional[str] = Field(None, max_length=1024)

    start: EventDateTime
    end: EventDateTime

    time_zone: Optional[str] = Field(None, alias="timeZone")
    attendees: List[EventAttendee] = Field(default_factory=list)
    reminders: Optional[Dict[str, Any]] = None

    visibility: EventVisibility = EventVisibility.DEFAULT
    transparency: str = "opaque"

    recurrence: Optional[List[str]] = None
    conference_data_version: Optional[int] = Field(None, alias="conferenceDataVersion")

    # Travel-specific
    travel_metadata: Optional[Dict[str, Any]] = None

    def to_google_format(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Handle extended properties for travel metadata
        if self.travel_metadata:
            if "extendedProperties" not in data:
                data["extendedProperties"] = {"private": {}}
            data["extendedProperties"]["private"]["tripsage_metadata"] = str(
                self.travel_metadata
            )
            data.pop("travel_metadata", None)

        return data


class UpdateEventRequest(BaseModel):
    """Request model for updating calendar events."""

    model_config = ConfigDict(populate_by_name=True)

    summary: Optional[str] = Field(None, min_length=1, max_length=1024)
    description: Optional[str] = Field(None, max_length=8192)
    location: Optional[str] = Field(None, max_length=1024)

    start: Optional[EventDateTime] = None
    end: Optional[EventDateTime] = None

    time_zone: Optional[str] = Field(None, alias="timeZone")
    attendees: Optional[List[EventAttendee]] = None
    reminders: Optional[Dict[str, Any]] = None

    visibility: Optional[EventVisibility] = None
    transparency: Optional[str] = None

    recurrence: Optional[List[str]] = None

    # Travel-specific
    travel_metadata: Optional[Dict[str, Any]] = None

    def to_google_format(self) -> Dict[str, Any]:
        """Convert to Google Calendar API format."""
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Handle extended properties
        if self.travel_metadata:
            if "extendedProperties" not in data:
                data["extendedProperties"] = {"private": {}}
            data["extendedProperties"]["private"]["tripsage_metadata"] = str(
                self.travel_metadata
            )
            data.pop("travel_metadata", None)

        return data


class CalendarListEntry(BaseModel):
    """Calendar list entry model."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#calendarListEntry"
    etag: Optional[str] = None
    id: str
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = Field(None, alias="timeZone")
    summary_override: Optional[str] = Field(None, alias="summaryOverride")
    color_id: Optional[str] = Field(None, alias="colorId")
    background_color: Optional[str] = Field(None, alias="backgroundColor")
    foreground_color: Optional[str] = Field(None, alias="foregroundColor")
    hidden: bool = False
    selected: bool = True
    access_role: str = Field("reader", alias="accessRole")
    default_reminders: List[EventReminder] = Field(
        default_factory=list, alias="defaultReminders"
    )
    notification_settings: Optional[Dict[str, Any]] = Field(
        None, alias="notificationSettings"
    )
    primary: bool = False
    deleted: bool = False
    conference_properties: Optional[Dict[str, Any]] = Field(
        None, alias="conferenceProperties"
    )


class CalendarList(BaseModel):
    """Calendar list response model."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#calendarList"
    etag: Optional[str] = None
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    next_sync_token: Optional[str] = Field(None, alias="nextSyncToken")
    items: List[CalendarListEntry] = Field(default_factory=list)


class FreeBusyRequest(BaseModel):
    """Request model for free/busy queries."""

    model_config = ConfigDict(populate_by_name=True)

    time_min: datetime = Field(..., alias="timeMin")
    time_max: datetime = Field(..., alias="timeMax")
    time_zone: Optional[str] = Field(None, alias="timeZone")
    group_expansion_max: int = Field(50, alias="groupExpansionMax", ge=1, le=100)
    calendar_expansion_max: int = Field(50, alias="calendarExpansionMax", ge=1, le=50)
    items: List[Dict[str, str]] = Field(..., description="List of calendars to query")


class FreeBusyResponse(BaseModel):
    """Free/busy query response model."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#freeBusy"
    time_min: datetime = Field(..., alias="timeMin")
    time_max: datetime = Field(..., alias="timeMax")
    groups: Dict[str, Any] = Field(default_factory=dict)
    calendars: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class EventsListRequest(BaseModel):
    """Request parameters for listing events."""

    model_config = ConfigDict(populate_by_name=True)

    calendar_id: str = Field("primary", alias="calendarId")
    always_include_email: bool = Field(False, alias="alwaysIncludeEmail")
    ical_uid: Optional[str] = Field(None, alias="iCalUID")
    max_attendees: Optional[int] = Field(None, alias="maxAttendees", ge=1)
    max_results: int = Field(250, alias="maxResults", ge=1, le=2500)
    order_by: Optional[str] = Field(
        None, alias="orderBy", pattern="^(startTime|updated)$"
    )
    page_token: Optional[str] = Field(None, alias="pageToken")
    private_extended_property: Optional[List[str]] = Field(
        None, alias="privateExtendedProperty"
    )
    q: Optional[str] = Field(None, description="Free text search query")
    shared_extended_property: Optional[List[str]] = Field(
        None, alias="sharedExtendedProperty"
    )
    show_deleted: bool = Field(False, alias="showDeleted")
    show_hidden_invitations: bool = Field(False, alias="showHiddenInvitations")
    single_events: bool = Field(False, alias="singleEvents")
    sync_token: Optional[str] = Field(None, alias="syncToken")
    time_max: Optional[datetime] = Field(None, alias="timeMax")
    time_min: Optional[datetime] = Field(None, alias="timeMin")
    time_zone: Optional[str] = Field(None, alias="timeZone")
    updated_min: Optional[datetime] = Field(None, alias="updatedMin")


class EventsListResponse(BaseModel):
    """Response model for event listings."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#events"
    etag: Optional[str] = None
    summary: str
    description: Optional[str] = None
    updated: datetime
    time_zone: str = Field(..., alias="timeZone")
    access_role: str = Field(..., alias="accessRole")
    default_reminders: List[EventReminder] = Field(
        default_factory=list, alias="defaultReminders"
    )
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    next_sync_token: Optional[str] = Field(None, alias="nextSyncToken")
    items: List[CalendarEvent] = Field(default_factory=list)
