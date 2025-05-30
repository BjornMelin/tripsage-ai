"""Tests for Google Calendar service implementation."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from tripsage_core.models.api.calendar_models import (
    CreateEventRequest,
    EventAttendee,
    EventReminder,
    UpdateEventRequest,
)
from tripsage_core.services.api.calendar_service import GoogleCalendarService


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth2 credentials."""
    creds = MagicMock(spec=Credentials)
    creds.expired = False
    creds.valid = True
    creds.token = "mock_token"
    creds.refresh = MagicMock()
    return creds


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.GOOGLE_CALENDAR_CREDENTIALS = {
        "token": "mock_token",
        "refresh_token": "mock_refresh_token",
        "client_id": "mock_client_id",
        "client_secret": "mock_client_secret",
    }
    settings.GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
    return settings


@pytest.fixture
def mock_redis():
    """Mock Redis service."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest_asyncio.fixture
async def calendar_service(mock_settings, mock_credentials, mock_redis):
    """Create calendar service instance for testing."""
    with patch(
        "tripsage.services.api.calendar_service.Credentials"
    ) as mock_creds_class:
        mock_creds_class.from_authorized_user_info.return_value = mock_credentials
        service = GoogleCalendarService()
        service.redis = mock_redis
        # Mock the service build
        service.service = MagicMock()
        return service


class TestGoogleCalendarService:
    """Test cases for Google Calendar service."""

    @pytest.mark.asyncio
    async def test_init_with_credentials(self, mock_settings, mock_credentials):
        """Test service initialization with credentials."""
        with patch(
            "tripsage.services.api.calendar_service.Credentials"
        ) as mock_creds_class:
            mock_creds_class.from_authorized_user_info.return_value = mock_credentials
            with patch("tripsage.services.api.calendar_service.build") as mock_build:
                service = GoogleCalendarService()
                assert service.credentials == mock_credentials
                mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_without_credentials(self):
        """Test service initialization without credentials."""
        with patch("tripsage.services.api.calendar_service.settings") as mock_settings:
            mock_settings.GOOGLE_CALENDAR_CREDENTIALS = None
            with pytest.raises(
                ValueError, match="Google Calendar credentials not configured"
            ):
                GoogleCalendarService()

    @pytest.mark.asyncio
    async def test_refresh_credentials(self, calendar_service, mock_credentials):
        """Test credential refresh."""
        mock_credentials.expired = True
        calendar_service.credentials = mock_credentials

        await calendar_service._refresh_credentials()

        mock_credentials.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_credentials_error(self, calendar_service, mock_credentials):
        """Test credential refresh error handling."""
        mock_credentials.expired = True
        mock_credentials.refresh.side_effect = RefreshError("Refresh failed")
        calendar_service.credentials = mock_credentials

        with pytest.raises(RefreshError):
            await calendar_service._refresh_credentials()

    @pytest.mark.asyncio
    async def test_list_calendars(self, calendar_service):
        """Test listing calendars."""
        # Mock API response
        mock_response = {
            "items": [
                {
                    "id": "primary",
                    "summary": "My Calendar",
                    "description": "Primary calendar",
                    "timeZone": "America/New_York",
                    "accessRole": "owner",
                },
                {
                    "id": "secondary",
                    "summary": "Work Calendar",
                    "timeZone": "America/New_York",
                    "accessRole": "writer",
                },
            ]
        }

        calendar_service.service.calendarList.return_value.list.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        calendars = await calendar_service.list_calendars()

        assert len(calendars) == 2
        assert calendars[0].id == "primary"
        assert calendars[0].summary == "My Calendar"
        assert calendars[1].id == "secondary"
        assert calendars[1].summary == "Work Calendar"

    @pytest.mark.asyncio
    async def test_create_event(self, calendar_service):
        """Test creating an event."""
        event_request = CreateEventRequest(
            summary="Test Meeting",
            description="Test description",
            start=datetime.now() + timedelta(hours=1),
            end=datetime.now() + timedelta(hours=2),
            location="Conference Room A",
            attendees=[EventAttendee(email="test@example.com")],
            reminders=[EventReminder(method="email", minutes=30)],
        )

        mock_response = {
            "id": "event123",
            "summary": "Test Meeting",
            "description": "Test description",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event123",
            "created": datetime.now().isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "start": {"dateTime": event_request.start.isoformat() + "Z"},
            "end": {"dateTime": event_request.end.isoformat() + "Z"},
            "location": "Conference Room A",
            "attendees": [
                {"email": "test@example.com", "responseStatus": "needsAction"}
            ],
            "reminders": {"overrides": [{"method": "email", "minutes": 30}]},
        }

        calendar_service.service.events.return_value.insert.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        event = await calendar_service.create_event("primary", event_request)

        assert event.id == "event123"
        assert event.summary == "Test Meeting"
        assert event.location == "Conference Room A"
        assert len(event.attendees) == 1
        assert event.attendees[0].email == "test@example.com"

    @pytest.mark.asyncio
    async def test_update_event(self, calendar_service):
        """Test updating an event."""
        update_request = UpdateEventRequest(
            summary="Updated Meeting",
            description="Updated description",
        )

        # Mock get event response
        mock_get_response = {
            "id": "event123",
            "summary": "Original Meeting",
            "description": "Original description",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event123",
            "created": datetime.now().isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "start": {
                "dateTime": (datetime.now() + timedelta(hours=1)).isoformat() + "Z"
            },
            "end": {
                "dateTime": (datetime.now() + timedelta(hours=2)).isoformat() + "Z"
            },
        }

        # Mock update response
        mock_update_response = mock_get_response.copy()
        mock_update_response["summary"] = "Updated Meeting"
        mock_update_response["description"] = "Updated description"

        calendar_service.service.events.return_value.get.return_value.execute = (
            AsyncMock(return_value=mock_get_response)
        )
        calendar_service.service.events.return_value.update.return_value.execute = (
            AsyncMock(return_value=mock_update_response)
        )

        event = await calendar_service.update_event(
            "primary", "event123", update_request
        )

        assert event.id == "event123"
        assert event.summary == "Updated Meeting"
        assert event.description == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_event(self, calendar_service):
        """Test deleting an event."""
        calendar_service.service.events.return_value.delete.return_value.execute = (
            AsyncMock()
        )

        await calendar_service.delete_event("primary", "event123")

        calendar_service.service.events.return_value.delete.assert_called_once()
        calendar_service.service.events.return_value.delete.assert_called_with(
            calendarId="primary", eventId="event123"
        )

    @pytest.mark.asyncio
    async def test_get_event(self, calendar_service):
        """Test getting a single event."""
        mock_response = {
            "id": "event123",
            "summary": "Test Meeting",
            "description": "Test description",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event123",
            "created": datetime.now().isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "start": {
                "dateTime": (datetime.now() + timedelta(hours=1)).isoformat() + "Z"
            },
            "end": {
                "dateTime": (datetime.now() + timedelta(hours=2)).isoformat() + "Z"
            },
        }

        calendar_service.service.events.return_value.get.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        event = await calendar_service.get_event("primary", "event123")

        assert event.id == "event123"
        assert event.summary == "Test Meeting"
        assert event.description == "Test description"

    @pytest.mark.asyncio
    async def test_list_events(self, calendar_service):
        """Test listing events."""
        mock_response = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Meeting 1",
                    "status": "confirmed",
                    "htmlLink": "https://calendar.google.com/event?eid=event1",
                    "created": datetime.now().isoformat() + "Z",
                    "updated": datetime.now().isoformat() + "Z",
                    "start": {
                        "dateTime": (datetime.now() + timedelta(hours=1)).isoformat()
                        + "Z"
                    },
                    "end": {
                        "dateTime": (datetime.now() + timedelta(hours=2)).isoformat()
                        + "Z"
                    },
                },
                {
                    "id": "event2",
                    "summary": "Meeting 2",
                    "status": "confirmed",
                    "htmlLink": "https://calendar.google.com/event?eid=event2",
                    "created": datetime.now().isoformat() + "Z",
                    "updated": datetime.now().isoformat() + "Z",
                    "start": {
                        "dateTime": (datetime.now() + timedelta(hours=3)).isoformat()
                        + "Z"
                    },
                    "end": {
                        "dateTime": (datetime.now() + timedelta(hours=4)).isoformat()
                        + "Z"
                    },
                },
            ]
        }

        calendar_service.service.events.return_value.list.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        events = await calendar_service.list_events(
            "primary",
            time_min=datetime.now(),
            time_max=datetime.now() + timedelta(days=1),
        )

        assert len(events) == 2
        assert events[0].id == "event1"
        assert events[0].summary == "Meeting 1"
        assert events[1].id == "event2"
        assert events[1].summary == "Meeting 2"

    @pytest.mark.asyncio
    async def test_get_free_busy(self, calendar_service):
        """Test getting free/busy information."""
        time_min = datetime.now()
        time_max = time_min + timedelta(days=1)

        mock_response = {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": (time_min + timedelta(hours=1)).isoformat() + "Z",
                            "end": (time_min + timedelta(hours=2)).isoformat() + "Z",
                        },
                        {
                            "start": (time_min + timedelta(hours=4)).isoformat() + "Z",
                            "end": (time_min + timedelta(hours=5)).isoformat() + "Z",
                        },
                    ]
                }
            }
        }

        calendar_service.service.freebusy.return_value.query.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        free_busy = await calendar_service.get_free_busy(
            ["primary"],
            time_min=time_min,
            time_max=time_max,
        )

        assert "primary" in free_busy
        assert len(free_busy["primary"]["busy"]) == 2

    @pytest.mark.asyncio
    async def test_create_travel_event(self, calendar_service):
        """Test creating a travel-specific event."""
        mock_response = {
            "id": "flight123",
            "summary": "Flight to NYC",
            "description": "Flight booking reference: ABC123\nTravel type: flight",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=flight123",
            "created": datetime.now().isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "start": {
                "dateTime": (datetime.now() + timedelta(hours=3)).isoformat() + "Z"
            },
            "end": {
                "dateTime": (datetime.now() + timedelta(hours=6)).isoformat() + "Z"
            },
            "location": "JFK Airport",
            "colorId": "9",  # Blue for flights
        }

        calendar_service.service.events.return_value.insert.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        event = await calendar_service.create_travel_event(
            "primary",
            title="Flight to NYC",
            start=datetime.now() + timedelta(hours=3),
            end=datetime.now() + timedelta(hours=6),
            location="JFK Airport",
            travel_type="flight",
            booking_reference="ABC123",
        )

        assert event.id == "flight123"
        assert event.summary == "Flight to NYC"
        assert "ABC123" in event.description
        assert event.color_id == "9"

    @pytest.mark.asyncio
    async def test_sync_trip_to_calendar(self, calendar_service):
        """Test syncing a complete trip itinerary to calendar."""
        trip_data = {
            "id": "trip123",
            "name": "NYC Business Trip",
            "start_date": datetime.now() + timedelta(days=1),
            "end_date": datetime.now() + timedelta(days=4),
            "itinerary": [
                {
                    "type": "flight",
                    "title": "Flight to NYC",
                    "start": datetime.now() + timedelta(days=1, hours=10),
                    "end": datetime.now() + timedelta(days=1, hours=13),
                    "location": "JFK Airport",
                    "booking_reference": "FL123",
                },
                {
                    "type": "hotel",
                    "title": "Marriott Downtown",
                    "start": datetime.now() + timedelta(days=1, hours=15),
                    "end": datetime.now() + timedelta(days=4, hours=11),
                    "location": "123 Broadway, NYC",
                    "booking_reference": "HT456",
                },
                {
                    "type": "activity",
                    "title": "Broadway Show",
                    "start": datetime.now() + timedelta(days=2, hours=19),
                    "end": datetime.now() + timedelta(days=2, hours=22),
                    "location": "Broadway Theatre",
                },
            ],
        }

        # Mock responses for each event creation
        mock_responses = [
            {"id": f"event{i}", "summary": item["title"]}
            for i, item in enumerate(trip_data["itinerary"])
        ]

        execute_mock = AsyncMock(
            side_effect=[
                {
                    **resp,
                    "status": "confirmed",
                    "htmlLink": f"https://calendar.google.com/event?eid={resp['id']}",
                    "created": datetime.now().isoformat() + "Z",
                    "updated": datetime.now().isoformat() + "Z",
                    "start": {"dateTime": datetime.now().isoformat() + "Z"},
                    "end": {"dateTime": datetime.now().isoformat() + "Z"},
                }
                for resp in mock_responses
            ]
        )
        calendar_service.service.events.return_value.insert.return_value.execute = (
            execute_mock
        )

        event_ids = await calendar_service.sync_trip_to_calendar("primary", trip_data)

        assert len(event_ids) == 3
        assert all(event_id.startswith("event") for event_id in event_ids)

    @pytest.mark.asyncio
    async def test_api_error_handling(self, calendar_service):
        """Test handling of Google API errors."""
        # Mock an HTTP error
        error = HttpError(
            resp=MagicMock(status=404, reason="Not Found"),
            content=b'{"error": {"message": "Event not found"}}',
        )

        calendar_service.service.events.return_value.get.return_value.execute = (
            AsyncMock(side_effect=error)
        )

        with pytest.raises(HttpError) as exc_info:
            await calendar_service.get_event("primary", "nonexistent")

        assert exc_info.value.resp.status == 404

    @pytest.mark.asyncio
    async def test_caching_behavior(self, calendar_service, mock_redis):
        """Test that caching is properly implemented."""
        # Mock calendar list response
        mock_response = {
            "items": [
                {
                    "id": "primary",
                    "summary": "My Calendar",
                    "timeZone": "America/New_York",
                    "accessRole": "owner",
                }
            ]
        }

        calendar_service.service.calendarList.return_value.list.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        # First call should hit the API
        calendars1 = await calendar_service.list_calendars()

        # Check that cache was set
        mock_redis.set.assert_called_once()
        cache_key = mock_redis.set.call_args[0][0]
        assert "calendar_list" in cache_key

        # Set up cache to return data
        mock_redis.get.return_value = json.dumps(
            [cal.model_dump() for cal in calendars1]
        )

        # Second call should use cache
        calendar_service.service.calendarList.return_value.list.return_value.execute.reset_mock()
        calendars2 = await calendar_service.list_calendars()

        # API should not be called again
        calendar_service.service.calendarList.return_value.list.return_value.execute.assert_not_called()
        assert len(calendars2) == len(calendars1)

    @pytest.mark.asyncio
    async def test_event_validation(self, calendar_service):
        """Test event validation for required fields."""
        # Test with missing required fields
        with pytest.raises(ValueError):
            await calendar_service.create_event(
                "primary",
                CreateEventRequest(
                    summary="",  # Empty summary should fail
                    start=datetime.now(),
                    end=datetime.now() - timedelta(hours=1),  # End before start
                ),
            )

    @pytest.mark.asyncio
    async def test_batch_operations(self, calendar_service):
        """Test batch event operations."""
        # Test batch delete
        event_ids = ["event1", "event2", "event3"]

        calendar_service.service.events.return_value.delete.return_value.execute = (
            AsyncMock()
        )

        # Create a simple batch delete method for testing
        async def batch_delete_events(calendar_id: str, event_ids: list):
            for event_id in event_ids:
                await calendar_service.delete_event(calendar_id, event_id)

        await batch_delete_events("primary", event_ids)

        assert calendar_service.service.events.return_value.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_timezone_handling(self, calendar_service):
        """Test proper timezone handling in events."""
        # Create event with timezone
        event_request = CreateEventRequest(
            summary="International Meeting",
            start=datetime.now() + timedelta(hours=1),
            end=datetime.now() + timedelta(hours=2),
            time_zone="Europe/London",
        )

        mock_response = {
            "id": "event123",
            "summary": "International Meeting",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event123",
            "created": datetime.now().isoformat() + "Z",
            "updated": datetime.now().isoformat() + "Z",
            "start": {
                "dateTime": event_request.start.isoformat() + "Z",
                "timeZone": "Europe/London",
            },
            "end": {
                "dateTime": event_request.end.isoformat() + "Z",
                "timeZone": "Europe/London",
            },
        }

        calendar_service.service.events.return_value.insert.return_value.execute = (
            AsyncMock(return_value=mock_response)
        )

        event = await calendar_service.create_event("primary", event_request)

        assert event.id == "event123"
        # Verify timezone was preserved
        calendar_service.service.events.return_value.insert.assert_called_once()
        call_args = calendar_service.service.events.return_value.insert.call_args[1][
            "body"
        ]
        assert call_args["start"]["timeZone"] == "Europe/London"
        assert call_args["end"]["timeZone"] == "Europe/London"
