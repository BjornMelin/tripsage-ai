"""Pydantic models for Google Calendar API integration.

This module provides data models for Google Calendar operations,
including event management, reminders, and travel-specific features.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


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

    date_time: datetime | None = Field(None, alias="dateTime")
    date: str | None = Field(
        None, description="Date in YYYY-MM-DD format for all-day events"
    )
    time_zone: str | None = Field(None, alias="timeZone", description="IANA time zone")

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """Validate date format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format") from None
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
    display_name: str | None = Field(None, alias="displayName")
    optional: bool = False
    response_status: AttendeeResponseStatus = AttendeeResponseStatus.NEEDS_ACTION
    comment: str | None = None
    additional_guests: int = Field(0, ge=0, alias="additionalGuests")


class ConferenceData(BaseModel):
    """Conference/meeting information for events."""

    model_config = ConfigDict(populate_by_name=True)

    conference_id: str | None = Field(None, alias="conferenceId")
    conference_solution: dict[str, Any] | None = Field(None, alias="conferenceSolution")
    entry_points: list[dict[str, Any]] | None = Field(None, alias="entryPoints")
    notes: str | None = None


class ExtendedProperties(BaseModel):
    """Extended properties for storing custom metadata."""

    private: dict[str, str] = Field(default_factory=dict)
    shared: dict[str, str] = Field(default_factory=dict)


class CalendarEvent(BaseModel):
    """Complete calendar event model."""

    model_config = ConfigDict(populate_by_name=True)

    # Core fields
    id: str | None = None
    etag: str | None = None
    status: EventStatus = EventStatus.CONFIRMED
    html_link: HttpUrl | None = Field(None, alias="htmlLink")
    created: datetime | None = None
    updated: datetime | None = None

    # Event details
    summary: str = Field(..., description="Event title")
    description: str | None = None
    location: str | None = None
    color_id: str | None = Field(None, alias="colorId")

    # Timing
    start: EventDateTime
    end: EventDateTime
    end_time_unspecified: bool = Field(False, alias="endTimeUnspecified")
    recurrence: list[str] | None = Field(None, description="RFC5545 recurrence rules")
    recurring_event_id: str | None = Field(None, alias="recurringEventId")
    original_start_time: EventDateTime | None = Field(None, alias="originalStartTime")

    # Visibility and access
    transparency: str = Field("opaque", description="opaque or transparent")
    visibility: EventVisibility = EventVisibility.DEFAULT
    ical_uid: str | None = Field(None, alias="iCalUID")
    sequence: int = 0

    # Participants
    attendees: list[EventAttendee] = Field(default_factory=list)
    attendees_omitted: bool = Field(False, alias="attendeesOmitted")
    extended_properties: ExtendedProperties | None = Field(
        None, alias="extendedProperties"
    )
    hangout_link: HttpUrl | None = Field(None, alias="hangoutLink")
    conference_data: ConferenceData | None = Field(None, alias="conferenceData")

    # Notifications
    reminders: dict[str, Any] = Field(default_factory=lambda: {"useDefault": True})

    # Organization
    organizer: dict[str, Any] | None = None
    creator: dict[str, Any] | None = None

    # Travel-specific extensions
    travel_metadata: dict[str, Any] | None = Field(
        None, description="TripSage travel-specific metadata"
    )


class CreateEventRequest(BaseModel):
    """Request model for creating calendar events."""

    model_config = ConfigDict(populate_by_name=True)

    summary: str = Field(..., min_length=1, max_length=1024)
    description: str | None = Field(None, max_length=8192)
    location: str | None = Field(None, max_length=1024)

    start: EventDateTime
    end: EventDateTime

    time_zone: str | None = Field(None, alias="timeZone")
    attendees: list[EventAttendee] = Field(default_factory=list)
    reminders: dict[str, Any] | None = None

    visibility: EventVisibility = EventVisibility.DEFAULT
    transparency: str = "opaque"

    recurrence: list[str] | None = None
    conference_data_version: int | None = Field(None, alias="conferenceDataVersion")

    # Travel-specific
    travel_metadata: dict[str, Any] | None = None

    def to_google_format(self) -> dict[str, Any]:
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

    summary: str | None = Field(None, min_length=1, max_length=1024)
    description: str | None = Field(None, max_length=8192)
    location: str | None = Field(None, max_length=1024)

    start: EventDateTime | None = None
    end: EventDateTime | None = None

    time_zone: str | None = Field(None, alias="timeZone")
    attendees: list[EventAttendee] | None = None
    reminders: dict[str, Any] | None = None

    visibility: EventVisibility | None = None
    transparency: str | None = None

    recurrence: list[str] | None = None

    # Travel-specific
    travel_metadata: dict[str, Any] | None = None

    def to_google_format(self) -> dict[str, Any]:
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
    etag: str | None = None
    id: str
    summary: str
    description: str | None = None
    location: str | None = None
    time_zone: str | None = Field(None, alias="timeZone")
    summary_override: str | None = Field(None, alias="summaryOverride")
    color_id: str | None = Field(None, alias="colorId")
    background_color: str | None = Field(None, alias="backgroundColor")
    foreground_color: str | None = Field(None, alias="foregroundColor")
    hidden: bool = False
    selected: bool = True
    access_role: str = Field("reader", alias="accessRole")
    default_reminders: list[EventReminder] = Field(
        default_factory=list, alias="defaultReminders"
    )
    notification_settings: dict[str, Any] | None = Field(
        None, alias="notificationSettings"
    )
    primary: bool = False
    deleted: bool = False
    conference_properties: dict[str, Any] | None = Field(
        None, alias="conferenceProperties"
    )


class CalendarList(BaseModel):
    """Calendar list response model."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#calendarList"
    etag: str | None = None
    next_page_token: str | None = Field(None, alias="nextPageToken")
    next_sync_token: str | None = Field(None, alias="nextSyncToken")
    items: list[CalendarListEntry] = Field(default_factory=list)


class FreeBusyCalendarItem(BaseModel):
    """Calendar item for free/busy queries."""

    id: str = Field(..., description="Calendar ID")


class FreeBusyRequest(BaseModel):
    """Request model for free/busy queries."""

    model_config = ConfigDict(populate_by_name=True)

    time_min: datetime = Field(..., alias="timeMin")
    time_max: datetime = Field(..., alias="timeMax")
    time_zone: str | None = Field(None, alias="timeZone")
    group_expansion_max: int = Field(50, alias="groupExpansionMax", ge=1, le=100)
    calendar_expansion_max: int = Field(50, alias="calendarExpansionMax", ge=1, le=50)
    items: list[FreeBusyCalendarItem] = Field(
        ..., description="List of calendars to query"
    )


class FreeBusyResponse(BaseModel):
    """Free/busy query response model."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#freeBusy"
    time_min: datetime = Field(..., alias="timeMin")
    time_max: datetime = Field(..., alias="timeMax")
    groups: dict[str, Any] = Field(default_factory=dict)
    calendars: dict[str, dict[str, Any]] = Field(default_factory=dict)


class EventsListRequest(BaseModel):
    """Request parameters for listing events."""

    model_config = ConfigDict(populate_by_name=True)

    calendar_id: str = Field("primary", alias="calendarId")
    always_include_email: bool = Field(False, alias="alwaysIncludeEmail")
    ical_uid: str | None = Field(None, alias="iCalUID")
    max_attendees: int | None = Field(None, alias="maxAttendees", ge=1)
    max_results: int = Field(250, alias="maxResults", ge=1, le=2500)
    order_by: str | None = Field(None, alias="orderBy", pattern="^(startTime|updated)$")
    page_token: str | None = Field(None, alias="pageToken")
    private_extended_property: list[str] | None = Field(
        None, alias="privateExtendedProperty"
    )
    q: str | None = Field(None, description="Free text search query")
    shared_extended_property: list[str] | None = Field(
        None, alias="sharedExtendedProperty"
    )
    show_deleted: bool = Field(False, alias="showDeleted")
    show_hidden_invitations: bool = Field(False, alias="showHiddenInvitations")
    single_events: bool = Field(False, alias="singleEvents")
    sync_token: str | None = Field(None, alias="syncToken")
    time_max: datetime | None = Field(None, alias="timeMax")
    time_min: datetime | None = Field(None, alias="timeMin")
    time_zone: str | None = Field(None, alias="timeZone")
    updated_min: datetime | None = Field(None, alias="updatedMin")


class EventsListResponse(BaseModel):
    """Response model for event listings."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str = "calendar#events"
    etag: str | None = None
    summary: str | None = None
    description: str | None = None
    updated: datetime | None = None
    time_zone: str | None = Field(None, alias="timeZone")
    access_role: str | None = Field(None, alias="accessRole")
    default_reminders: list[EventReminder] = Field(
        default_factory=list, alias="defaultReminders"
    )
    next_page_token: str | None = Field(None, alias="nextPageToken")
    next_sync_token: str | None = Field(None, alias="nextSyncToken")
    items: list[CalendarEvent] = Field(default_factory=list)


class TravelEventRequest(BaseModel):
    """Request model for creating travel-specific calendar events."""

    model_config = ConfigDict(populate_by_name=True)

    calendar_id: str = Field(..., description="Calendar ID to create event in")
    title: str = Field(..., min_length=1, max_length=1024, description="Event title")
    start: datetime = Field(..., description="Event start datetime")
    end: datetime = Field(..., description="Event end datetime")

    location: str | None = Field(
        None, max_length=1024, description="Location/destination"
    )
    description: str | None = Field(
        None, max_length=8192, description="Event description"
    )

    travel_type: str = Field(
        "flight",
        description="Type of travel",
        pattern="^(flight|hotel|activity|transportation)$",
    )
    booking_reference: str | None = Field(
        None, max_length=256, description="Booking/confirmation number"
    )
    attendees: list[EmailStr] = Field(
        default_factory=list, description="List of attendee email addresses"
    )

    def to_create_event_request(self) -> CreateEventRequest:
        """Convert to a CreateEventRequest with travel metadata."""
        # Build travel metadata
        travel_metadata = {
            "type": self.travel_type,
            "booking_reference": self.booking_reference,
            "created_by": "tripsage-core",
            "created_at": datetime.now().isoformat(),
        }

        event_payload = {
            "summary": self.title,
            "description": self.description or "",
            "location": self.location,
            "start": {
                "dateTime": self.start.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": self.end.isoformat(),
                "timeZone": "UTC",
            },
            "timeZone": "UTC",
            "conferenceDataVersion": None,
            "attendees": [{"email": email} for email in self.attendees],
            "travel_metadata": travel_metadata,
        }

        return CreateEventRequest.model_validate(event_payload)
