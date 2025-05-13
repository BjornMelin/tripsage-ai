"""
Unit tests for Google Calendar MCP models.
"""

import unittest

from pydantic import ValidationError

from src.mcp.calendar.models import (
    Calendar,
    CreateEventParams,
    CreateItineraryEventsParams,
    DeleteEventParams,
    Event,
    EventAttendee,
    EventStatus,
    EventTime,
    EventVisibility,
    ItineraryItem,
    ItineraryItemType,
    ListCalendarsParams,
    ListEventsParams,
    UpdateEventParams,
)


class TestCalendarModels(unittest.TestCase):
    """Test Google Calendar MCP model classes."""

    def test_event_time_validation(self):
        """Test validation of EventTime model."""
        # Valid with date_time
        event_time = EventTime(date_time="2025-05-15T10:00:00Z", time_zone="UTC")
        self.assertEqual(event_time.date_time, "2025-05-15T10:00:00Z")
        self.assertEqual(event_time.time_zone, "UTC")

        # Valid with date
        event_time = EventTime(date="2025-05-15")
        self.assertEqual(event_time.date, "2025-05-15")

        # Invalid with neither
        with self.assertRaises(ValidationError):
            EventTime()

        # Invalid with both
        with self.assertRaises(ValidationError):
            EventTime(date_time="2025-05-15T10:00:00Z", date="2025-05-15")

    def test_calendar_model(self):
        """Test Calendar model."""
        # Create a calendar
        calendar = Calendar(
            id="calendar1",
            summary="Primary Calendar",
            description="My main calendar",
            time_zone="America/New_York",
            primary=True,
        )

        # Verify properties
        self.assertEqual(calendar.id, "calendar1")
        self.assertEqual(calendar.summary, "Primary Calendar")
        self.assertEqual(calendar.description, "My main calendar")
        self.assertEqual(calendar.time_zone, "America/New_York")
        self.assertTrue(calendar.primary)

        # Test serialization
        calendar_dict = calendar.model_dump()
        self.assertEqual(calendar_dict["id"], "calendar1")
        self.assertEqual(calendar_dict["summary"], "Primary Calendar")
        self.assertEqual(calendar_dict["description"], "My main calendar")
        self.assertEqual(calendar_dict["time_zone"], "America/New_York")
        self.assertTrue(calendar_dict["primary"])

    def test_event_model(self):
        """Test Event model."""
        # Create an event
        event = Event(
            id="event1",
            calendar_id="calendar1",
            summary="Team Meeting",
            description="Weekly team sync",
            location="Conference Room A",
            start=EventTime(date_time="2025-05-20T10:00:00Z", time_zone="UTC"),
            end=EventTime(date_time="2025-05-20T11:00:00Z", time_zone="UTC"),
            status=EventStatus.CONFIRMED,
            attendees=[
                EventAttendee(
                    email="user1@example.com",
                    display_name="User One",
                    response_status="accepted",
                )
            ],
            visibility=EventVisibility.DEFAULT,
        )

        # Verify properties
        self.assertEqual(event.id, "event1")
        self.assertEqual(event.calendar_id, "calendar1")
        self.assertEqual(event.summary, "Team Meeting")
        self.assertEqual(event.description, "Weekly team sync")
        self.assertEqual(event.location, "Conference Room A")
        self.assertEqual(event.start.date_time, "2025-05-20T10:00:00Z")
        self.assertEqual(event.end.date_time, "2025-05-20T11:00:00Z")
        self.assertEqual(event.status, EventStatus.CONFIRMED)
        self.assertEqual(len(event.attendees), 1)
        self.assertEqual(event.attendees[0].email, "user1@example.com")
        self.assertEqual(event.visibility, EventVisibility.DEFAULT)

        # Test serialization
        event_dict = event.model_dump()
        self.assertEqual(event_dict["id"], "event1")
        self.assertEqual(event_dict["summary"], "Team Meeting")
        self.assertEqual(event_dict["start"]["date_time"], "2025-05-20T10:00:00Z")
        self.assertEqual(event_dict["attendees"][0]["email"], "user1@example.com")

    def test_list_calendars_params(self):
        """Test ListCalendarsParams model."""
        # Default parameters
        params = ListCalendarsParams()
        self.assertIsNone(params.max_results)

        # With max_results
        params = ListCalendarsParams(max_results=10)
        self.assertEqual(params.max_results, 10)

    def test_list_events_params(self):
        """Test ListEventsParams model."""
        # Required parameters
        params = ListEventsParams(calendar_id="calendar1")
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertIsNone(params.time_min)
        self.assertIsNone(params.time_max)

        # All parameters
        params = ListEventsParams(
            calendar_id="calendar1",
            time_min="2025-05-01T00:00:00Z",
            time_max="2025-05-31T23:59:59Z",
            max_results=50,
            single_events=True,
            order_by="startTime",
        )
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(params.time_min, "2025-05-01T00:00:00Z")
        self.assertEqual(params.time_max, "2025-05-31T23:59:59Z")
        self.assertEqual(params.max_results, 50)
        self.assertTrue(params.single_events)
        self.assertEqual(params.order_by, "startTime")

    def test_create_event_params(self):
        """Test CreateEventParams model."""
        # Required parameters
        params = CreateEventParams(
            calendar_id="calendar1",
            summary="New Event",
            start={"date_time": "2025-05-15T10:00:00Z"},
            end={"date_time": "2025-05-15T11:00:00Z"},
        )
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(params.summary, "New Event")
        self.assertEqual(params.start.date_time, "2025-05-15T10:00:00Z")
        self.assertEqual(params.end.date_time, "2025-05-15T11:00:00Z")

        # With optional parameters
        params = CreateEventParams(
            calendar_id="calendar1",
            summary="New Event",
            description="Event description",
            location="Conference Room",
            start={"date_time": "2025-05-15T10:00:00Z", "time_zone": "UTC"},
            end={"date_time": "2025-05-15T11:00:00Z", "time_zone": "UTC"},
            attendees=[{"email": "user@example.com", "display_name": "User"}],
            visibility=EventVisibility.PUBLIC,
        )
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(params.summary, "New Event")
        self.assertEqual(params.description, "Event description")
        self.assertEqual(params.location, "Conference Room")
        self.assertEqual(params.start.date_time, "2025-05-15T10:00:00Z")
        self.assertEqual(params.start.time_zone, "UTC")
        self.assertEqual(params.attendees[0].email, "user@example.com")
        self.assertEqual(params.visibility, EventVisibility.PUBLIC)

    def test_update_event_params(self):
        """Test UpdateEventParams model."""
        # Required parameters
        params = UpdateEventParams(
            calendar_id="calendar1",
            event_id="event1",
        )
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(params.event_id, "event1")

        # With updates
        params = UpdateEventParams(
            calendar_id="calendar1",
            event_id="event1",
            summary="Updated Event",
            description="Updated description",
            location="New Location",
            start={"date_time": "2025-05-16T10:00:00Z"},
            end={"date_time": "2025-05-16T11:00:00Z"},
        )
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(params.event_id, "event1")
        self.assertEqual(params.summary, "Updated Event")
        self.assertEqual(params.description, "Updated description")
        self.assertEqual(params.location, "New Location")
        self.assertEqual(params.start.date_time, "2025-05-16T10:00:00Z")
        self.assertEqual(params.end.date_time, "2025-05-16T11:00:00Z")

    def test_delete_event_params(self):
        """Test DeleteEventParams model."""
        params = DeleteEventParams(
            calendar_id="calendar1",
            event_id="event1",
        )
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(params.event_id, "event1")

    def test_itinerary_item(self):
        """Test ItineraryItem model."""
        # With end_time
        item = ItineraryItem(
            type=ItineraryItemType.FLIGHT,
            title="Flight to New York",
            description="Delta Airlines Flight DL123",
            location="JFK Airport",
            start_time="2025-06-15T10:00:00Z",
            end_time="2025-06-15T14:00:00Z",
            time_zone="UTC",
        )
        self.assertEqual(item.type, ItineraryItemType.FLIGHT)
        self.assertEqual(item.title, "Flight to New York")
        self.assertEqual(item.location, "JFK Airport")
        self.assertEqual(item.start_time, "2025-06-15T10:00:00Z")
        self.assertEqual(item.end_time, "2025-06-15T14:00:00Z")

        # With duration instead of end_time
        item = ItineraryItem(
            type=ItineraryItemType.ACTIVITY,
            title="Museum Visit",
            description="Visit to the Natural History Museum",
            location="Natural History Museum",
            start_time="2025-06-16T09:00:00Z",
            duration_minutes=180,  # 3 hours
            time_zone="America/New_York",
        )
        self.assertEqual(item.type, ItineraryItemType.ACTIVITY)
        self.assertEqual(item.title, "Museum Visit")
        self.assertEqual(item.duration_minutes, 180)

        # Invalid without end_time or duration
        with self.assertRaises(ValidationError):
            ItineraryItem(
                type=ItineraryItemType.ACTIVITY,
                title="Museum Visit",
                start_time="2025-06-16T09:00:00Z",
            )

    def test_create_itinerary_events_params(self):
        """Test CreateItineraryEventsParams model."""
        # Create itinerary items
        items = [
            ItineraryItem(
                type=ItineraryItemType.FLIGHT,
                title="Flight to New York",
                start_time="2025-06-15T10:00:00Z",
                end_time="2025-06-15T14:00:00Z",
                time_zone="UTC",
            ),
            ItineraryItem(
                type=ItineraryItemType.ACCOMMODATION,
                title="Hotel Check-in",
                location="Grand Hyatt New York",
                start_time="2025-06-15T15:00:00Z",
                duration_minutes=30,
                time_zone="America/New_York",
            ),
        ]

        # Create parameters
        params = CreateItineraryEventsParams(
            calendar_id="calendar1",
            itinerary_items=items,
            trip_name="Summer Vacation",
        )

        # Verify properties
        self.assertEqual(params.calendar_id, "calendar1")
        self.assertEqual(len(params.itinerary_items), 2)
        self.assertEqual(params.itinerary_items[0].title, "Flight to New York")
        self.assertEqual(params.itinerary_items[1].title, "Hotel Check-in")
        self.assertEqual(params.trip_name, "Summer Vacation")


if __name__ == "__main__":
    unittest.main()
