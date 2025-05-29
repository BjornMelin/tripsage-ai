"""
Google Calendar API service implementation with TripSage Core integration.

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

from tripsage_core.config.base_app_settings import CoreAppSettings, get_settings
from tripsage_core.exceptions.exceptions import CoreAPIError, CoreServiceError
from tripsage_core.services.infrastructure.cache_service import get_cache_service

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
                        await asyncio.sleep(wait_time)
                    else:
                        raise CoreAPIError(
                            message=(
                                f"Google Calendar API failed after {max_attempts} "
                                f"attempts: {e}"
                            ),
                            code="CALENDAR_API_ERROR",
                            service="GoogleCalendarService",
                            details={"attempts": max_attempts, "error": str(e)},
                        ) from e
            raise last_exception

        return wrapper

    return decorator


class GoogleCalendarServiceError(CoreAPIError):
    """Exception raised for Google Calendar service errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="CALENDAR_SERVICE_ERROR",
            service="GoogleCalendarService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class GoogleCalendarService:
    """Service for Google Calendar API operations with Core integration."""

    def __init__(
        self,
        credentials_file: Optional[str] = None,
        token_file: Optional[str] = None,
        settings: Optional[CoreAppSettings] = None,
    ):
        """
        Initialize the Google Calendar service.

        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store user tokens
            settings: Core application settings
        """
        self.settings = settings or get_settings()

        # Get credentials paths from settings or environment
        self.credentials_file = (
            credentials_file
            or getattr(self.settings, "google_calendar_credentials_file", None)
            or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json")
        )
        self.token_file = (
            token_file
            or getattr(self.settings, "google_calendar_token_file", None)
            or os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "token.json")
        )

        self.cache_service = None
        self._service: Optional[Resource] = None
        self._credentials: Optional[Credentials] = None
        self._connected = False

        # Cache settings
        self.cache_ttl = {
            "calendar_list": 3600,  # 1 hour
            "events": 300,  # 5 minutes
            "free_busy": 60,  # 1 minute
        }

    async def connect(self) -> None:
        """Initialize the service and authenticate."""
        if self._connected:
            return

        try:
            await self._authenticate()

            # Initialize cache service if not provided
            if self.cache_service is None:
                try:
                    self.cache_service = await get_cache_service()
                except Exception:
                    # Log warning but continue without cache
                    pass

            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to connect to Google Calendar API: {str(e)}",
                code="CONNECTION_FAILED",
                service="GoogleCalendarService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Clean up resources."""
        self._service = None
        self._credentials = None
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def _authenticate(self) -> None:
        """Authenticate with Google Calendar API."""
        creds = None

        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                raise GoogleCalendarServiceError(
                    f"Error loading credentials: {e}", original_error=e
                ) from e

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    raise GoogleCalendarServiceError(
                        f"Error refreshing credentials: {e}", original_error=e
                    ) from e

            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise GoogleCalendarServiceError(
                        f"Credentials file not found: {self.credentials_file}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for next run
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self._credentials = creds
        self._service = build("calendar", "v3", credentials=creds)

    def _get_service(self) -> Resource:
        """Get the Google Calendar service instance."""
        if not self._service:
            raise CoreServiceError(
                message="Service not initialized. Call connect() first.",
                code="SERVICE_NOT_INITIALIZED",
                service="GoogleCalendarService",
            )
        return self._service

    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache."""
        if not self.cache_service:
            return None

        try:
            data = await self.cache_service.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass  # Cache errors are non-fatal
        return None

    async def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        """Set data in cache."""
        if not self.cache_service:
            return

        try:
            await self.cache_service.set(key, json.dumps(value), ttl=ttl)
        except Exception:
            pass  # Cache errors are non-fatal

    @async_retry()
    async def list_calendars(
        self, show_hidden: bool = False, show_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        List all calendars accessible by the user.

        Args:
            show_hidden: Include hidden calendars
            show_deleted: Include deleted calendars

        Returns:
            Dictionary with calendar list
        """
        await self.ensure_connected()

        cache_key = f"calendar_list:{show_hidden}:{show_deleted}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

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
                calendar_list.extend(items)

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

            except HttpError as e:
                raise GoogleCalendarServiceError(
                    f"Error listing calendars: {e}", original_error=e
                ) from e

        response = {"items": calendar_list}
        await self._set_cache(cache_key, response, self.cache_ttl["calendar_list"])

        return response

    @async_retry()
    async def create_event(
        self,
        calendar_id: str,
        event_data: Dict[str, Any],
        send_notifications: bool = True,
        conference_data_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.

        Args:
            calendar_id: Calendar ID (use 'primary' for main calendar)
            event_data: Event data dictionary
            send_notifications: Send notifications to attendees
            conference_data_version: Version for conference data

        Returns:
            Created calendar event
        """
        await self.ensure_connected()

        service = self._get_service()

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

            return result

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error creating event: {e}", original_error=e
            ) from e

    @async_retry()
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_data: Dict[str, Any],
        send_notifications: bool = True,
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID to update
            event_data: Event update data
            send_notifications: Send notifications to attendees

        Returns:
            Updated calendar event
        """
        await self.ensure_connected()

        service = self._get_service()

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

            return result

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error updating event: {e}", original_error=e
            ) from e

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
        await self.ensure_connected()

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
                return False
            raise GoogleCalendarServiceError(
                f"Error deleting event: {e}", original_error=e
            ) from e

    @async_retry()
    async def get_event(
        self,
        calendar_id: str,
        event_id: str,
        time_zone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            time_zone: Time zone for date/time values

        Returns:
            Calendar event
        """
        await self.ensure_connected()

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

            return result

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error getting event: {e}", original_error=e
            ) from e

    @async_retry()
    async def list_events(
        self,
        calendar_id: str,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 250,
        single_events: bool = True,
        order_by: str = "startTime",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        List calendar events with various filters.

        Args:
            calendar_id: Calendar ID
            time_min: Lower bound for event start time (RFC3339 timestamp)
            time_max: Upper bound for event start time (RFC3339 timestamp)
            max_results: Maximum number of events to return
            single_events: Expand recurring events into instances
            order_by: Order of events returned
            **kwargs: Additional parameters

        Returns:
            Dictionary with events list and metadata
        """
        await self.ensure_connected()

        cache_key = f"events:{calendar_id}:{hash(str(sorted(kwargs.items())))}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        service = self._get_service()
        events = []
        page_token = None

        try:
            while True:
                request_params = {
                    "calendarId": calendar_id,
                    "maxResults": min(max_results - len(events), 250),
                    "singleEvents": single_events,
                    "orderBy": order_by,
                    "pageToken": page_token,
                }

                if time_min:
                    request_params["timeMin"] = time_min
                if time_max:
                    request_params["timeMax"] = time_max

                request_params.update(kwargs)

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda rp=request_params: service.events().list(**rp).execute(),
                )

                items = result.get("items", [])
                events.extend(items)

                page_token = result.get("nextPageToken")
                if not page_token or len(events) >= max_results:
                    break

            response = {
                "items": events[:max_results],
                "summary": result.get("summary", ""),
                "timeZone": result.get("timeZone", "UTC"),
                "accessRole": result.get("accessRole", "reader"),
                "updated": result.get("updated", datetime.now().isoformat()),
                "nextPageToken": page_token,
            }

            await self._set_cache(cache_key, response, self.cache_ttl["events"])
            return response

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error listing events: {e}", original_error=e
            ) from e

    @async_retry()
    async def get_free_busy(
        self,
        calendars: List[str],
        time_min: str,
        time_max: str,
        time_zone: str = "UTC",
    ) -> Dict[str, Any]:
        """
        Query free/busy information for calendars.

        Args:
            calendars: List of calendar IDs to query
            time_min: Start time (RFC3339 timestamp)
            time_max: End time (RFC3339 timestamp)
            time_zone: Time zone for the query

        Returns:
            Free/busy information
        """
        await self.ensure_connected()

        cache_key = f"free_busy:{hash(str(sorted(calendars)))}:{time_min}:{time_max}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        service = self._get_service()
        request_data = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": time_zone,
            "items": [{"id": cal_id} for cal_id in calendars],
        }

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: service.freebusy().query(body=request_data).execute(),
            )

            await self._set_cache(cache_key, result, self.cache_ttl["free_busy"])
            return result

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error querying free/busy: {e}", original_error=e
            ) from e

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
    ) -> Dict[str, Any]:
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

        Returns:
            Created calendar event
        """
        # Build travel metadata
        travel_metadata = {
            "type": travel_type,
            "booking_reference": booking_reference,
            "created_by": "tripsage-core",
            "created_at": datetime.now().isoformat(),
        }

        # Create event data
        event_data = {
            "summary": title,
            "description": description or "",
            "location": location,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "extendedProperties": {
                "private": {"tripsage_metadata": json.dumps(travel_metadata)}
            },
        }

        if attendees:
            event_data["attendees"] = [{"email": email} for email in attendees]

        return await self.create_event(calendar_id, event_data)

    async def sync_trip_to_calendar(
        self,
        calendar_id: str,
        trip_id: str,
        trip_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
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

    async def _clear_events_cache(self, calendar_id: str) -> None:
        """Clear events cache for a calendar."""
        if not self.cache_service:
            return

        try:
            # Clear all event-related cache keys for this calendar
            pattern = f"events:{calendar_id}:*"
            await self.cache_service.delete_pattern(pattern)
        except Exception:
            pass  # Cache errors are non-fatal

    async def health_check(self) -> bool:
        """
        Check if the Google Calendar API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self.ensure_connected()
            # Simple test request
            await self.list_calendars()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Clean up resources."""
        await self.disconnect()


# Global service instance
_calendar_service: Optional[GoogleCalendarService] = None


async def get_calendar_service() -> GoogleCalendarService:
    """
    Get the global Google Calendar service instance.

    Returns:
        GoogleCalendarService instance
    """
    global _calendar_service

    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
        await _calendar_service.connect()

    return _calendar_service


async def close_calendar_service() -> None:
    """Close the global Google Calendar service instance."""
    global _calendar_service

    if _calendar_service:
        await _calendar_service.close()
        _calendar_service = None
