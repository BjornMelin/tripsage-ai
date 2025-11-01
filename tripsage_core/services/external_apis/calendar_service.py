"""Google Calendar API service implementation with TripSage Core integration.

This module provides direct integration with Google Calendar API using the
google-api-python-client library, replacing the previous MCP server abstraction.
"""

import asyncio
import json
import logging
import os
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import googleapiclient.discovery as gdisc
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
    CoreServiceError,
)
from tripsage_core.infrastructure.retry_policies import tripsage_retry
from tripsage_core.models.api.calendar_models import (
    CalendarEvent,
    CalendarList,
    CreateEventRequest,
    EventsListRequest,
    EventsListResponse,
    FreeBusyRequest,
    FreeBusyResponse,
    TravelEventRequest,
    UpdateEventRequest,
)
from tripsage_core.services.external_apis.base_service import (
    JSONValue,
    sanitize_response,
)
from tripsage_core.services.infrastructure.cache_service import (
    CacheService,
    get_cache_service,
)


logger = logging.getLogger(__name__)

# If modifying these scopes, delete the token file
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


"""Retry logic moved to Tenacity policies via generic_retry."""

CredentialsLoader = Callable[[str, Sequence[str]], Credentials]
BuildCallable = Callable[..., Resource]

_CREDENTIALS_FROM_FILE: CredentialsLoader = cast(
    CredentialsLoader, cast(Any, Credentials).from_authorized_user_file
)
_BUILD: BuildCallable = cast(BuildCallable, cast(Any, gdisc).build)


class GoogleCalendarServiceError(CoreAPIError):
    """Exception raised for Google Calendar service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize the Google Calendar service error.

        Args:
            message: Human-readable error message
            original_error: The original exception that caused this error
        """
        super().__init__(
            message=message,
            code="CALENDAR_SERVICE_ERROR",
            api_service="GoogleCalendarService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class GoogleCalendarService:
    """Service for Google Calendar API operations with Core integration."""

    def __init__(
        self,
        credentials_file: str | None = None,
        token_file: str | None = None,
        settings: Settings | None = None,
    ):
        """Initialize the Google Calendar service.

        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store user tokens
            settings: Core application settings
        """
        self.settings = settings or get_settings()

        # File configuration
        self._file_config = {
            "credentials_file": (
                credentials_file
                or getattr(self.settings, "google_calendar_credentials_file", None)
                or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json")
            ),
            "token_file": (
                token_file
                or getattr(self.settings, "google_calendar_token_file", None)
                or os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "token.json")
            ),
        }

        self.cache_service: CacheService | None = None
        self._service: Resource | None = None
        self._credentials: Credentials | None = None
        self._connected = False

        # Cache configuration
        self._cache_config = {
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
                except CoreServiceError as cache_error:
                    # Log warning but continue without cache
                    logger.warning(
                        "Calendar service cache initialization failed: %s",
                        cache_error,
                    )

            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to connect to Google Calendar API: {e!s}",
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
        creds: Credentials | None = None

        # Token file stores the user's access and refresh tokens
        token_file = self._file_config["token_file"]
        if Path(token_file).exists():
            try:
                creds = _CREDENTIALS_FROM_FILE(token_file, SCOPES)
            except Exception as e:
                raise GoogleCalendarServiceError(
                    f"Error loading credentials: {e}", original_error=e
                ) from e

        # If there are no (valid) credentials available, let the user log in
        if creds is None or not creds.valid:
            if (
                creds is not None
                and getattr(creds, "expired", False)
                and getattr(creds, "refresh_token", None) is not None
            ):
                try:
                    refresh_method = cast(
                        Callable[[Request], None], cast(Any, creds).refresh
                    )
                    refresh_method(Request())
                except Exception as e:
                    raise GoogleCalendarServiceError(
                        f"Error refreshing credentials: {e}", original_error=e
                    ) from e
            else:
                credentials_file = self._file_config["credentials_file"]
                if not Path(credentials_file).exists():
                    raise GoogleCalendarServiceError(
                        f"Credentials file not found: {credentials_file}"
                    )

                flow = _gc_flow_from_client_secrets_file(credentials_file, SCOPES)
                creds = _gc_run_local_server(flow, port=0)

            # Save the credentials for next run
            to_json_method = cast(
                Callable[[bool | None], str], cast(Any, creds).to_json
            )
            with Path(token_file).open("w", encoding="utf-8") as token:
                token.write(to_json_method(None))

        self._credentials = creds
        self._service = _gc_build("calendar", "v3", credentials=creds)

    def _get_service(self) -> Resource:
        """Get the Google Calendar service instance."""
        if not self._service:
            raise CoreServiceError(
                message="Service not initialized. Call connect() first.",
                code="SERVICE_NOT_INITIALIZED",
                service="GoogleCalendarService",
            )
        return self._service

    async def _get_from_cache(self, key: str) -> JSONValue | None:
        """Get data from cache."""
        if not self.cache_service:
            return None

        try:
            data = await self.cache_service.get(key)
            if data:
                parsed = sanitize_response(data)
                return parsed if isinstance(parsed, (dict, list)) else None
        except (json.JSONDecodeError, CoreServiceError) as cache_error:
            logger.debug("Calendar cache read failed for key %s: %s", key, cache_error)
        return None

    async def _set_cache(self, key: str, value: JSONValue, ttl: int) -> None:
        """Set data in cache."""
        if not self.cache_service:
            return

        try:
            await self.cache_service.set(key, json.dumps(value), ttl=ttl)
        except (ValueError, CoreServiceError) as cache_error:
            logger.debug(
                "Calendar cache write failed for key %s: %s",
                key,
                cache_error,
            )

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def list_calendars(
        self, show_hidden: bool = False, show_deleted: bool = False
    ) -> CalendarList:
        """List all calendars accessible by the user.

        Args:
            show_hidden: Include hidden calendars
            show_deleted: Include deleted calendars

        Returns:
            Calendar list response
        """
        await self.ensure_connected()

        cache_key = f"calendar_list:{show_hidden}:{show_deleted}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return CalendarList.model_validate(cached_data)

        service = cast(Any, self._get_service())
        calendar_list: list[dict[str, Any]] = []
        page_token = None

        while True:
            try:
                # Execute synchronously in thread pool
                result_raw = await asyncio.get_event_loop().run_in_executor(
                    None,
                    # type: ignore[union-attr] # pylint: disable=no-member
                    lambda pt=page_token: service.calendarList()
                    .list(
                        showHidden=show_hidden,
                        showDeleted=show_deleted,
                        pageToken=pt,
                    )
                    .execute(),
                )

                result_any = sanitize_response(result_raw)
                result = result_any if isinstance(result_any, dict) else {}

                items_any = result.get("items", [])
                items_list: list[dict[str, Any]] = (
                    [cast(dict[str, Any], i) for i in items_any if isinstance(i, dict)]
                    if isinstance(items_any, list)
                    else []
                )
                calendar_list.extend(items_list)

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

            except HttpError as e:
                raise GoogleCalendarServiceError(
                    f"Error listing calendars: {e}", original_error=e
                ) from e

        # Create CalendarList response
        response = CalendarList.model_validate(
            {
                "kind": result.get("kind", "calendar#calendarList"),
                "etag": result.get("etag"),
                "nextPageToken": result.get("nextPageToken"),
                "nextSyncToken": result.get("nextSyncToken"),
                "items": calendar_list,
            }
        )

        await self._set_cache(
            cache_key,
            cast(JSONValue, response.model_dump()),
            self._cache_config["calendar_list"],
        )

        return response

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def create_event(
        self,
        calendar_id: str,
        event_request: CreateEventRequest,
        send_notifications: bool = True,
        conference_data_version: int | None = None,
    ) -> CalendarEvent:
        """Create a new calendar event.

        Args:
            calendar_id: Calendar ID (use 'primary' for main calendar)
            event_request: Event creation request data
            send_notifications: Send notifications to attendees
            conference_data_version: Version for conference data

        Returns:
            Created calendar event
        """
        await self.ensure_connected()

        service = cast(Any, self._get_service())

        # Convert Pydantic model to Google API format
        event_data = event_request.to_google_format()

        try:
            result_raw = await asyncio.get_event_loop().run_in_executor(
                None,
                # type: ignore[union-attr] # pylint: disable=no-member
                lambda: service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event_data,
                    sendNotifications=send_notifications,
                    conferenceDataVersion=conference_data_version,
                )
                .execute(),
            )

            result_any = sanitize_response(result_raw)
            result = result_any if isinstance(result_any, dict) else {}
            return CalendarEvent.model_validate(result)

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error creating event: {e}", original_error=e
            ) from e

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_request: UpdateEventRequest,
        send_notifications: bool = True,
    ) -> CalendarEvent:
        """Update an existing calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID to update
            event_request: Event update request data
            send_notifications: Send notifications to attendees

        Returns:
            Updated calendar event
        """
        await self.ensure_connected()

        service = cast(Any, self._get_service())

        # Convert Pydantic model to Google API format
        event_data = event_request.to_google_format()

        try:
            result_raw = await asyncio.get_event_loop().run_in_executor(
                None,
                # type: ignore[union-attr] # pylint: disable=no-member
                lambda: service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=event_data,
                    sendNotifications=send_notifications,
                )
                .execute(),
            )

            result_any = sanitize_response(result_raw)
            result = result_any if isinstance(result_any, dict) else {}
            return CalendarEvent.model_validate(result)

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error updating event: {e}", original_error=e
            ) from e

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        send_notifications: bool = True,
    ) -> bool:
        """Delete a calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID to delete
            send_notifications: Send notifications to attendees

        Returns:
            True if successful
        """
        await self.ensure_connected()

        service = cast(Any, self._get_service())

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                # type: ignore[union-attr] # pylint: disable=no-member
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
            status = int(getattr(getattr(e, "resp", None), "status", 0) or 0)
            if status == 404:
                return False
            raise GoogleCalendarServiceError(
                f"Error deleting event: {e}", original_error=e
            ) from e

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def get_event(
        self,
        calendar_id: str,
        event_id: str,
        time_zone: str | None = None,
    ) -> CalendarEvent:
        """Get a specific calendar event.

        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            time_zone: Time zone for date/time values

        Returns:
            Calendar event
        """
        await self.ensure_connected()

        service = cast(Any, self._get_service())

        try:
            result_raw = await asyncio.get_event_loop().run_in_executor(
                None,
                # type: ignore[union-attr] # pylint: disable=no-member
                lambda: service.events()  # type: ignore[union-attr] # pylint: disable=no-member
                .get(
                    calendarId=calendar_id,
                    eventId=event_id,
                    timeZone=time_zone,
                )
                .execute(),
            )

            result_any = sanitize_response(result_raw)
            result = result_any if isinstance(result_any, dict) else {}
            return CalendarEvent.model_validate(result)

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error getting event: {e}", original_error=e
            ) from e

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def list_events(
        self,
        request: EventsListRequest,
    ) -> EventsListResponse:
        """List calendar events with various filters.

        Args:
            request: Event listing request parameters

        Returns:
            Events list response with metadata
        """
        await self.ensure_connected()

        # Create cache key from request data
        cache_key = f"events:{request.calendar_id}:{hash(request.model_dump_json())}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return EventsListResponse.model_validate(cached_data)

        service = cast(Any, self._get_service())
        events: list[CalendarEvent] = []
        page_token = request.page_token

        try:
            while True:
                # Build request parameters from Pydantic model
                request_params = request.model_dump(
                    by_alias=True,
                    exclude_none=True,
                    exclude={"calendar_id"},  # calendar_id is passed separately
                )
                request_params["calendarId"] = request.calendar_id
                request_params["maxResults"] = min(
                    request.max_results - len(events), 250
                )
                request_params["pageToken"] = page_token

                result_raw = await asyncio.get_event_loop().run_in_executor(
                    None,
                    # type: ignore[union-attr] # pylint: disable=no-member
                    lambda rp=request_params: service.events().list(**rp).execute(),  # type: ignore[union-attr] # pylint: disable=no-member
                )

                result_any = sanitize_response(result_raw)
                result = result_any if isinstance(result_any, dict) else {}

                items_any = result.get("items", [])
                if isinstance(items_any, list):
                    events.extend(
                        [
                            CalendarEvent.model_validate(item)
                            for item in items_any
                            if isinstance(item, dict)
                        ]
                    )

                page_token = result.get("nextPageToken")
                if not page_token or len(events) >= request.max_results:
                    break

            response_payload: dict[str, Any] = {
                "kind": result.get("kind", "calendar#events"),
                "etag": result.get("etag"),
                "summary": result.get("summary"),
                "description": result.get("description"),
                "updated": result.get("updated"),
                "timeZone": result.get("timeZone"),
                "accessRole": result.get("accessRole"),
                "defaultReminders": result.get("defaultReminders", []),
                "nextPageToken": page_token,
                "nextSyncToken": result.get("nextSyncToken"),
                "items": events[: request.max_results],
            }

            response = EventsListResponse.model_validate(response_payload)

            await self._set_cache(
                cache_key,
                cast(JSONValue, response.model_dump()),
                self._cache_config["events"],
            )
            return response

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error listing events: {e}", original_error=e
            ) from e

    @tripsage_retry(exceptions=(HttpError,), attempts=3, max_delay=10.0)
    async def get_free_busy(
        self,
        request: FreeBusyRequest,
    ) -> FreeBusyResponse:
        """Query free/busy information for calendars.

        Args:
            request: Free/busy query request parameters

        Returns:
            Free/busy response data
        """
        await self.ensure_connected()

        # Create cache key from request data
        cache_key = f"free_busy:{hash(request.model_dump_json())}"
        cached_data = await self._get_from_cache(cache_key)
        if cached_data:
            return FreeBusyResponse.model_validate(cached_data)

        service = cast(Any, self._get_service())

        # Convert Pydantic model to Google API format
        request_data = request.model_dump(by_alias=True, exclude_none=True)

        try:
            result_raw = await asyncio.get_event_loop().run_in_executor(
                None,
                # type: ignore[union-attr] # pylint: disable=no-member
                lambda: service.freebusy().query(body=request_data).execute(),  # type: ignore[union-attr] # pylint: disable=no-member
            )

            # Create and validate response
            result_any = sanitize_response(result_raw)
            result = result_any if isinstance(result_any, dict) else {}
            response = FreeBusyResponse.model_validate(result)

            await self._set_cache(
                cache_key,
                cast(JSONValue, response.model_dump()),
                self._cache_config["free_busy"],
            )
            return response

        except HttpError as e:
            raise GoogleCalendarServiceError(
                f"Error querying free/busy: {e}", original_error=e
            ) from e

    # Travel-specific methods

    async def create_travel_event(
        self,
        request: TravelEventRequest,
    ) -> CalendarEvent:
        """Create a travel-specific calendar event with metadata.

        Args:
            request: Travel event creation request

        Returns:
            Created calendar event
        """
        # Convert travel request to create event request
        create_request = request.to_create_event_request()

        return await self.create_event(request.calendar_id, create_request)

    async def sync_trip_to_calendar(
        self,
        calendar_id: str,
        trip_id: str,
        trip_data: dict[str, Any],
    ) -> list[CalendarEvent]:
        """Sync an entire trip itinerary to calendar.

        Args:
            calendar_id: Calendar ID
            trip_id: Trip identifier
            trip_data: Trip itinerary data

        Returns:
            List of created calendar events
        """
        events: list[CalendarEvent] = []

        # Create events for flights
        for flight in trip_data.get("flights", []):
            request = TravelEventRequest(
                calendar_id=calendar_id,
                title=f"Flight: {flight['from']} → {flight['to']}",
                start=datetime.fromisoformat(flight["departure"]),
                end=datetime.fromisoformat(flight["arrival"]),
                location=f"{flight['from_airport']} to {flight['to_airport']}",
                description=(
                    f"Flight {flight['flight_number']}\nBooking: "
                    f"{flight.get('booking_reference', 'N/A')}"
                ),
                travel_type="flight",
                booking_reference=flight.get("booking_reference"),
            )
            event = await self.create_travel_event(request)
            events.append(event)

        # Create events for accommodations
        for hotel in trip_data.get("accommodations", []):
            # Check-in event
            checkin_request = TravelEventRequest(
                calendar_id=calendar_id,
                title=f"Check-in: {hotel['name']}",
                start=datetime.fromisoformat(hotel["checkin"]),
                end=datetime.fromisoformat(hotel["checkin"]) + timedelta(hours=1),
                location=hotel["address"],
                description=f"Confirmation: {hotel.get('confirmation_number', 'N/A')}",
                travel_type="accommodation",
                booking_reference=hotel.get("confirmation_number"),
            )
            checkin_event = await self.create_travel_event(checkin_request)
            events.append(checkin_event)

            # Check-out event
            checkout_request = TravelEventRequest(
                calendar_id=calendar_id,
                title=f"Check-out: {hotel['name']}",
                start=datetime.fromisoformat(hotel["checkout"]),
                end=datetime.fromisoformat(hotel["checkout"]) + timedelta(hours=1),
                location=hotel["address"],
                description=f"Checkout for {hotel['name']}",
                travel_type="accommodation",
                booking_reference=hotel.get("confirmation_number"),
            )
            checkout_event = await self.create_travel_event(checkout_request)
            events.append(checkout_event)

        # Create events for activities
        for activity in trip_data.get("activities", []):
            request = TravelEventRequest(
                calendar_id=calendar_id,
                title=activity["name"],
                start=datetime.fromisoformat(activity["start"]),
                end=datetime.fromisoformat(activity["end"]),
                location=activity.get("location"),
                description=activity.get("description"),
                travel_type="activity",
                booking_reference=activity.get("booking_reference"),
            )
            event = await self.create_travel_event(request)
            events.append(event)

        return events

    async def _clear_events_cache(self, calendar_id: str) -> None:
        """Clear events cache for a calendar."""
        if not self.cache_service:
            return

        # Clear all event-related cache keys for this calendar
        pattern = f"events:{calendar_id}:*"
        try:
            await self.cache_service.delete_pattern(pattern)
        except CoreServiceError as cache_error:
            logger.debug(
                "Calendar cache invalidation failed for pattern %s: %s",
                pattern,
                cache_error,
            )

    async def health_check(self) -> bool:
        """Check if the Google Calendar API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self.ensure_connected()
            # Simple test request
            await self.list_calendars()
            return True
        except CoreServiceError:
            return False

    async def close(self) -> None:
        """Clean up resources."""
        await self.disconnect()


def create_calendar_service() -> GoogleCalendarService:
    """Create a new Google Calendar service instance.

    Returns:
        GoogleCalendarService instance
    """
    return GoogleCalendarService()


def create_calendar_service_with_token(token_file: str) -> GoogleCalendarService:
    """Create a new Google Calendar service instance with custom token file.

    Args:
        token_file: Path to token file

    Returns:
        GoogleCalendarService instance
    """
    return GoogleCalendarService(token_file=token_file)


def _gc_flow_from_client_secrets_file(  # pragma: no cover
    credentials_file: str, scopes: Sequence[str]
) -> InstalledAppFlow:
    """Return an OAuth flow object using Google OAuth client secrets."""
    flow_factory = cast(
        Callable[[str, Sequence[str]], InstalledAppFlow],
        cast(Any, InstalledAppFlow).from_client_secrets_file,
    )
    return flow_factory(credentials_file, scopes)


def _gc_run_local_server(  # pragma: no cover
    flow: InstalledAppFlow, *, port: int
) -> Credentials:
    """Run the local OAuth server and return credentials."""
    run_local_server = cast(
        Callable[..., Credentials], cast(Any, flow).run_local_server
    )
    return run_local_server(port=port)


def _gc_build(  # pragma: no cover
    service: str, version: str, *, credentials: Credentials
) -> Resource:
    """Build a Google API client resource."""
    return _BUILD(service, version, credentials=credentials)
