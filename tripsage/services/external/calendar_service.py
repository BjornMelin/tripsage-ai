"""
Google Calendar API service implementation.

This module provides direct integration with Google Calendar API using the
google-api-python-client library, replacing the previous MCP server abstraction.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from tripsage.models.api.calendar_models import (
    CalendarEvent,
    CalendarList,
    CalendarListEntry,
    CreateEventRequest,
    EventAttendee,
    EventDateTime,
    EventReminder,
    EventsListRequest,
    EventsListResponse,
    FreeBusyRequest,
    FreeBusyResponse,
    UpdateEventRequest,
)
from tripsage.services.dragonfly_service import get_cache_service
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# If modifying these scopes, delete the token file
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (HttpError,),
):
    """Decorator for async retry logic."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
            raise last_exception

        return wrapper

    return decorator


class GoogleCalendarService:
    """Service for Google Calendar API operations."""

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
        cache_service: Optional[Any] = None,
    ):
        """
        Initialize the Google Calendar service.

        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store user tokens
            cache_service: Optional DragonflyDB cache service for caching
        """
        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json"
        )
        self.token_file = token_file or os.getenv(
            "GOOGLE_CALENDAR_TOKEN_FILE", "token.json"
        )
        self.cache_service = cache_service
        self._service: Optional[Resource] = None
        self._credentials: Optional[Credentials] = None

        # Cache settings
        self.cache_ttl = {
            "calendar_list": 3600,  # 1 hour
            "events": 300,  # 5 minutes
            "free_busy": 60,  # 1 minute
        }

    async def initialize(self) -> None:
        """Initialize the service and authenticate."""
        await self._authenticate()
        
        # Initialize cache service if not provided
        if self.cache_service is None:
            try:
                self.cache_service = await get_cache_service()
            except Exception as e:
                logger.warning(f"Failed to initialize cache service: {e}")
                self.cache_service = None

    async def _authenticate(self) -> None:
        """Authenticate with Google Calendar API."""
        creds = None

        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                logger.info("Loaded credentials from token file")
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Obtained new credentials via OAuth flow")

            # Save the credentials for next run
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self._credentials = creds
        self._service = build("calendar", "v3", credentials=creds)

    def _get_service(self) -> Resource:
        """Get the Google Calendar service instance."""
        if not self._service:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        return self._service

    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache."""
        if not self.cache_service:
            return None

        try:
            data = await self.cache_service.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None

    async def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        """Set data in cache."""
        if not self.cache_service:
            return

        try:
            await self.cache_service.set(key, json.dumps(value), expire=ttl)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    @with_error_handling
    @async_retry()
    async def list_calendars(
        self, show_hidden: bool = False, show_deleted: bool = False
    ) -> CalendarList:
        """
        List all calendars accessible by the user.

        Args:
            show_hidden: Include hidden calendars
            show_deleted: Include deleted calendars

        Returns:
            CalendarList with all accessible calendars
        """
        cache_key = f"calendar_list:{show_hidden}:{show_deleted}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return CalendarList(**cached_data)

        service = self._get_service()
        calendar_list = []
        page_token = None

        while True:
            try:
                # Execute synchronously in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda pt=page_token: service.calendarList()
                    .list(
                        showHidden=show_hidden,
                        showDeleted=show_deleted,
                        pageToken=pt,
                    )
                    .execute(),
                )

                items = result.get("items", [])
                calendar_list.extend([CalendarListEntry(**item) for item in items])

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

            except HttpError as e:
                logger.error(f"Error listing calendars: {e}")
                raise

        response = CalendarList(items=calendar_list)
        await self._set_cache(
            cache_key,
            response.model_dump(by_alias=True),
            self.cache_ttl["calendar_list"],
        )

        return response

    @with_error_handling
    @async_retry()
    async def create_event(
        self,
        calendar_id: str,
        event: CreateEventRequest,
        send_notifications: bool = True,
        conference_data_version: Optional[int] = None,
    ) -> CalendarEvent:
        """
        Create a new calendar event.

        Args:
            calendar_id: Calendar ID (use 'primary' for main calendar)
            event: Event creation request
            send_notifications: Send notifications to attendees
            conference_data_version: Version for conference data

        Returns:
            Created calendar event
        """
        service = self._get_service()
        event_data = event.to_google_format()

        # Add travel metadata if provided
        if event.travel_metadata:
            self._add_travel_metadata(event_data, event.travel_metadata)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event_data,
                    sendNotifications=send_notifications,
                    conferenceDataVersion=conference_data_version,
                )
                .execute(),
            )

            return CalendarEvent(**result)

        except HttpError as e:
            logger.error(f"Error creating event: {e}")
            raise

    @with_error_handling
    @async_retry()
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: UpdateEventRequest,
        send_notifications: bool = True,
    ) -> CalendarEvent:
        """
        Update an existing calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID to update
            event: Event update request
            send_notifications: Send notifications to attendees

        Returns:
            Updated calendar event
        """
        service = self._get_service()

        # Get current event first
        current_event = await self.get_event(calendar_id, event_id)

        # Convert to dict and update with new data
        event_data = current_event.model_dump(by_alias=True, exclude_none=True)
        update_data = event.to_google_format()
        event_data.update(update_data)

        # Add travel metadata if provided
        if event.travel_metadata:
            self._add_travel_metadata(event_data, event.travel_metadata)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event_data,
                    sendNotifications=send_notifications,
                )
                .execute(),
            )

            return CalendarEvent(**result)

        except HttpError as e:
            logger.error(f"Error updating event: {e}")
            raise

    @with_error_handling
    @async_retry()
    async def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        send_notifications: bool = True,
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID to delete
            send_notifications: Send notifications to attendees

        Returns:
            True if successful
        """
        service = self._get_service()

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.events()
                .delete(
                    calendarId=calendar_id,
                    eventId=event_id,
                    sendNotifications=send_notifications,
                )
                .execute(),
            )

            # Clear cache
            await self._clear_events_cache(calendar_id)
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Event not found: {event_id}")
                return False
            logger.error(f"Error deleting event: {e}")
            raise

    @with_error_handling
    @async_retry()
    async def get_event(
        self,
        calendar_id: str,
        event_id: str,
        time_zone: Optional[str] = None,
    ) -> CalendarEvent:
        """
        Get a specific calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            time_zone: Time zone for date/time values

        Returns:
            Calendar event
        """
        service = self._get_service()

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.events()
                .get(
                    calendarId=calendar_id,
                    eventId=event_id,
                    timeZone=time_zone,
                )
                .execute(),
            )

            return CalendarEvent(**result)

        except HttpError as e:
            logger.error(f"Error getting event: {e}")
            raise

    @with_error_handling
    @async_retry()
    async def list_events(
        self,
        params: EventsListRequest,
    ) -> EventsListResponse:
        """
        List calendar events with various filters.

        Args:
            params: Event listing parameters

        Returns:
            List of calendar events
        """
        cache_key = f"events:{params.calendar_id}:{params.model_dump_json()}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return EventsListResponse(**cached_data)

        service = self._get_service()
        events = []
        page_token = params.page_token

        while True:
            try:
                request_params = params.model_dump(by_alias=True, exclude_none=True)
                request_params["pageToken"] = page_token

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda rp=request_params: service.events().list(**rp).execute(),
                )

                items = result.get("items", [])
                events.extend([CalendarEvent(**item) for item in items])

                page_token = result.get("nextPageToken")
                if not page_token or len(events) >= params.max_results:
                    break

            except HttpError as e:
                logger.error(f"Error listing events: {e}")
                raise

        response = EventsListResponse(
            items=events[: params.max_results],
            summary=result.get("summary", ""),
            time_zone=result.get("timeZone", "UTC"),
            access_role=result.get("accessRole", "reader"),
            updated=datetime.fromisoformat(
                result.get("updated", datetime.now().isoformat())
            ),
            next_page_token=page_token,
        )

        await self._set_cache(
            cache_key, response.model_dump(by_alias=True), self.cache_ttl["events"]
        )

        return response

    @with_error_handling
    @async_retry()
    async def get_free_busy(
        self,
        request: FreeBusyRequest,
    ) -> FreeBusyResponse:
        """
        Query free/busy information for calendars.

        Args:
            request: Free/busy query parameters

        Returns:
            Free/busy information
        """
        cache_key = f"free_busy:{request.model_dump_json()}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return FreeBusyResponse(**cached_data)

        service = self._get_service()
        request_data = request.model_dump(by_alias=True)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.freebusy().query(body=request_data).execute(),
            )

            response = FreeBusyResponse(**result)
            await self._set_cache(
                cache_key,
                response.model_dump(by_alias=True),
                self.cache_ttl["free_busy"],
            )

            return response

        except HttpError as e:
            logger.error(f"Error querying free/busy: {e}")
            raise

    # Travel-specific methods

    async def create_travel_event(
        self,
        calendar_id: str,
        title: str,
        start: datetime,
        end: datetime,
        location: Optional[str] = None,
        description: Optional[str] = None,
        travel_type: str = "flight",
        booking_reference: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[EventReminder]] = None,
    ) -> CalendarEvent:
        """
        Create a travel-specific calendar event with metadata.

        Args:
            calendar_id: Calendar ID
            title: Event title
            start: Start datetime
            end: End datetime
            location: Location/destination
            description: Event description
            travel_type: Type of travel (flight, hotel, activity)
            booking_reference: Booking/confirmation number
            attendees: List of attendee emails
            reminders: Event reminders

        Returns:
            Created calendar event
        """
        # Build travel metadata
        travel_metadata = {
            "type": travel_type,
            "booking_reference": booking_reference,
            "created_by": "tripsage",
            "created_at": datetime.now().isoformat(),
        }

        # Create event request
        event_request = CreateEventRequest(
            summary=title,
            description=description,
            location=location,
            start=EventDateTime(date_time=start),
            end=EventDateTime(date_time=end),
            attendees=[EventAttendee(email=email) for email in (attendees or [])],
            reminders={
                "useDefault": False,
                "overrides": [
                    {"method": r.method.value, "minutes": r.minutes}
                    for r in (reminders or [])
                ],
            }
            if reminders
            else {"useDefault": True},
            travel_metadata=travel_metadata,
        )

        return await self.create_event(calendar_id, event_request)

    async def sync_trip_to_calendar(
        self,
        calendar_id: str,
        trip_id: str,
        trip_data: Dict[str, Any],
    ) -> List[CalendarEvent]:
        """
        Sync an entire trip itinerary to calendar.

        Args:
            calendar_id: Calendar ID
            trip_id: Trip identifier
            trip_data: Trip itinerary data

        Returns:
            List of created calendar events
        """
        events = []

        # Create events for flights
        for flight in trip_data.get("flights", []):
            event = await self.create_travel_event(
                calendar_id=calendar_id,
                title=f"Flight: {flight['from']} → {flight['to']}",
                start=datetime.fromisoformat(flight["departure"]),
                end=datetime.fromisoformat(flight["arrival"]),
                location=f"{flight['from_airport']} to {flight['to_airport']}",
                description=(
                    f"Flight {flight['flight_number']}\n"
                    f"Booking: {flight.get('booking_reference', 'N/A')}"
                ),
                travel_type="flight",
                booking_reference=flight.get("booking_reference"),
                reminders=[
                    EventReminder(method="popup", minutes=180),  # 3 hours
                    EventReminder(method="email", minutes=1440),  # 24 hours
                ],
            )
            events.append(event)

        # Create events for accommodations
        for hotel in trip_data.get("accommodations", []):
            # Check-in event
            checkin_event = await self.create_travel_event(
                calendar_id=calendar_id,
                title=f"Check-in: {hotel['name']}",
                start=datetime.fromisoformat(hotel["checkin"]),
                end=datetime.fromisoformat(hotel["checkin"]) + timedelta(hours=1),
                location=hotel["address"],
                description=f"Confirmation: {hotel.get('confirmation_number', 'N/A')}",
                travel_type="accommodation",
                booking_reference=hotel.get("confirmation_number"),
            )
            events.append(checkin_event)

            # Check-out event
            checkout_event = await self.create_travel_event(
                calendar_id=calendar_id,
                title=f"Check-out: {hotel['name']}",
                start=datetime.fromisoformat(hotel["checkout"]),
                end=datetime.fromisoformat(hotel["checkout"]) + timedelta(hours=1),
                location=hotel["address"],
                travel_type="accommodation",
                booking_reference=hotel.get("confirmation_number"),
            )
            events.append(checkout_event)

        # Create events for activities
        for activity in trip_data.get("activities", []):
            event = await self.create_travel_event(
                calendar_id=calendar_id,
                title=activity["name"],
                start=datetime.fromisoformat(activity["start"]),
                end=datetime.fromisoformat(activity["end"]),
                location=activity.get("location"),
                description=activity.get("description"),
                travel_type="activity",
                booking_reference=activity.get("booking_reference"),
            )
            events.append(event)

        return events

    async def _add_travel_metadata(
        self, event_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        """Add TripSage travel metadata to event data."""
        if "extendedProperties" not in event_data:
            event_data["extendedProperties"] = {"private": {}}

        event_data["extendedProperties"]["private"]["tripsage_metadata"] = json.dumps(
            metadata
        )

    async def _clear_events_cache(self, calendar_id: str) -> None:
        """Clear events cache for a calendar."""
        if not self.cache_service:
            return

        try:
            # Clear all event-related cache keys for this calendar
            pattern = f"events:{calendar_id}:*"
            await self.cache_service.delete_pattern(pattern)
        except Exception as e:
            logger.warning(f"Error clearing events cache: {e}")

    async def close(self) -> None:
        """Clean up resources."""
        # Google API client doesn't need explicit cleanup
        pass
