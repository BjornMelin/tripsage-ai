"""
Unit tests for agent calendar tools.

This module tests the refactored calendar tools that use the error handling decorator.
"""

import unittest
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.agents.calendar_tools import (
    create_event_tool,
    create_itinerary_events_tool,
    delete_event_tool,
    list_calendars_tool,
    list_events_tool,
    search_events_tool,
)
from tripsage.mcp.calendar.models import (
    Calendar,
    CalendarListResponse,
    CreateItineraryEventsResponse,
    Event,
    EventListResponse,
    EventSearchResponse,
    EventTime,
)


class TestCalendarTools(unittest.TestCase):
    """Test calendar tools for agents."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the calendar client for each tool
        self.mock_calendar_client_patcher = patch(
            "src.agents.calendar_tools.calendar_client"
        )
        self.mock_calendar_client = self.mock_calendar_client_patcher.start()

        # Mock the calendar service
        self.mock_calendar_service_patcher = patch(
            "src.agents.calendar_tools.calendar_service"
        )
        self.mock_calendar_service = self.mock_calendar_service_patcher.start()

    def tearDown(self):
        """Tear down test fixtures."""
        self.mock_calendar_client_patcher.stop()
        self.mock_calendar_service_patcher.stop()

    @pytest.mark.asyncio
    async def test_list_calendars_tool(self):
        """Test list_calendars_tool."""
        # Mock client response
        mock_calendars = [
            Calendar(
                id="calendar1",
                summary="Primary Calendar",
                primary=True,
                time_zone="America/New_York",
                description=None,
            ),
            Calendar(
                id="calendar2",
                summary="Work Calendar",
                primary=False,
                time_zone="America/New_York",
                description=None,
            ),
        ]
        mock_response = CalendarListResponse(
            calendars=mock_calendars,
            next_page_token=None,
        )
        self.mock_calendar_client.get_calendars = AsyncMock(return_value=mock_response)

        # Call the tool
        result = await list_calendars_tool()

        # Verify call
        self.mock_calendar_client.get_calendars.assert_called_once()

        # Verify result
        self.assertEqual(len(result["calendars"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["calendars"][0]["id"], "calendar1")
        self.assertEqual(result["calendars"][0]["name"], "Primary Calendar")
        self.assertTrue(result["calendars"][0]["is_primary"])
        self.assertEqual(result["calendars"][1]["id"], "calendar2")
        self.assertEqual(result["calendars"][1]["name"], "Work Calendar")
        self.assertFalse(result["calendars"][1]["is_primary"])

        # Verify formatted output
        self.assertIn("Primary Calendar (Primary)", result["formatted"])
        self.assertIn("Work Calendar", result["formatted"])

    @pytest.mark.asyncio
    async def test_list_events_tool(self):
        """Test list_events_tool."""
        # Mock client response
        mock_events = [
            Event(
                id="event1",
                calendar_id="calendar1",
                summary="Team Meeting",
                description="Weekly team sync",
                location="Conference Room A",
                start=EventTime(date_time="2025-05-20T10:00:00Z", time_zone="UTC"),
                end=EventTime(date_time="2025-05-20T11:00:00Z", time_zone="UTC"),
                status=None,
                html_link=None,
                created=None,
                updated=None,
                attendees=None,
                reminders=None,
                recurrence=None,
                visibility=None,
                conference_data=None,
            ),
            Event(
                id="event2",
                calendar_id="calendar1",
                summary="Lunch",
                description=None,
                location=None,
                start=EventTime(date_time="2025-05-20T12:00:00Z", time_zone="UTC"),
                end=EventTime(date_time="2025-05-20T13:00:00Z", time_zone="UTC"),
                status=None,
                html_link=None,
                created=None,
                updated=None,
                attendees=None,
                reminders=None,
                recurrence=None,
                visibility=None,
                conference_data=None,
            ),
        ]
        mock_response = EventListResponse(
            events=mock_events,
            next_page_token=None,
        )
        self.mock_calendar_client.get_events = AsyncMock(return_value=mock_response)

        # Call the tool
        result = await list_events_tool(
            calendar_id="calendar1",
            start_date="2025-05-20",
            end_date="2025-05-21",
        )

        # Verify call
        self.mock_calendar_client.get_events.assert_called_once()

        # Verify result
        self.assertEqual(len(result["events"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["events"][0]["id"], "event1")
        self.assertEqual(result["events"][0]["title"], "Team Meeting")
        self.assertEqual(result["events"][0]["description"], "Weekly team sync")
        self.assertEqual(result["events"][0]["location"], "Conference Room A")
        self.assertEqual(result["events"][1]["id"], "event2")
        self.assertEqual(result["events"][1]["title"], "Lunch")

        # Verify formatted output
        self.assertIn("Team Meeting", result["formatted"])
        self.assertIn("Conference Room A", result["formatted"])
        self.assertIn("Lunch", result["formatted"])

    @pytest.mark.asyncio
    async def test_search_events_tool(self):
        """Test search_events_tool."""
        # Mock client response
        mock_events = [
            Event(
                id="event1",
                calendar_id="calendar1",
                summary="Team Meeting",
                description="Weekly team sync",
                location="Conference Room A",
                start=EventTime(date_time="2025-05-20T10:00:00Z", time_zone="UTC"),
                end=EventTime(date_time="2025-05-20T11:00:00Z", time_zone="UTC"),
                status=None,
                html_link=None,
                created=None,
                updated=None,
                attendees=None,
                reminders=None,
                recurrence=None,
                visibility=None,
                conference_data=None,
            ),
        ]
        mock_response = EventSearchResponse(
            events=mock_events,
            next_page_token=None,
        )
        self.mock_calendar_client.search_events = AsyncMock(return_value=mock_response)

        # Call the tool
        result = await search_events_tool(
            query="team",
            calendar_id="calendar1",
        )

        # Verify call
        self.mock_calendar_client.search_events.assert_called_once()

        # Verify result
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["events"][0]["id"], "event1")
        self.assertEqual(result["events"][0]["title"], "Team Meeting")
        self.assertEqual(result["events"][0]["description"], "Weekly team sync")
        self.assertEqual(result["events"][0]["location"], "Conference Room A")

        # Verify formatted output
        self.assertIn("Team Meeting", result["formatted"])
        self.assertIn("Conference Room A", result["formatted"])

    @pytest.mark.asyncio
    async def test_create_event_tool(self):
        """Test create_event_tool."""
        # Mock client response
        mock_event = Event(
            id="new_event",
            calendar_id="calendar1",
            summary="New Meeting",
            description="Project kickoff",
            location="Conference Room B",
            start=EventTime(date_time="2025-05-25T14:00:00Z", time_zone="UTC"),
            end=EventTime(date_time="2025-05-25T15:00:00Z", time_zone="UTC"),
            status=None,
            html_link=None,
            created=None,
            updated=None,
            attendees=None,
            reminders=None,
            recurrence=None,
            visibility=None,
            conference_data=None,
        )
        self.mock_calendar_client.create_event = AsyncMock(return_value=mock_event)

        # Call the tool
        result = await create_event_tool(
            calendar_id="calendar1",
            summary="New Meeting",
            description="Project kickoff",
            location="Conference Room B",
            start_time="2025-05-25T14:00:00Z",
            end_time="2025-05-25T15:00:00Z",
            time_zone="UTC",
        )

        # Verify call
        self.mock_calendar_client.create_event.assert_called_once()

        # Verify result
        self.assertEqual(result["id"], "new_event")
        self.assertEqual(result["title"], "New Meeting")
        self.assertEqual(result["description"], "Project kickoff")
        self.assertEqual(result["location"], "Conference Room B")

        # Verify formatted output
        self.assertIn("Event created: New Meeting", result["formatted"])
        self.assertIn("Conference Room B", result["formatted"])

    @pytest.mark.asyncio
    async def test_create_itinerary_events_tool(self):
        """Test create_itinerary_events_tool."""
        # Mock service response
        mock_event = Event(
            id="new_event",
            calendar_id="calendar1",
            summary="Flight to New York",
            description="Trip: Summer Vacation\n\nAirline: Delta\nFlight: DL123",
            location="JFK Airport",
            start=EventTime(date_time="2025-06-15T10:00:00Z", time_zone="UTC"),
            end=EventTime(date_time="2025-06-15T14:00:00Z", time_zone="UTC"),
            status=None,
            html_link=None,
            created=None,
            updated=None,
            attendees=None,
            reminders=None,
            recurrence=None,
            visibility=None,
            conference_data=None,
        )
        mock_response = CreateItineraryEventsResponse(
            created_events=[mock_event],
            failed_items=[],
            trip_name="Summer Vacation",
        )
        self.mock_calendar_service.create_itinerary_events = AsyncMock(
            return_value=mock_response
        )

        # Test data
        itinerary_items = [
            {
                "type": "flight",
                "title": "Flight to New York",
                "description": "Delta Airlines Flight DL123",
                "location": "JFK Airport",
                "start_time": "2025-06-15T10:00:00Z",
                "end_time": "2025-06-15T14:00:00Z",
                "time_zone": "UTC",
                "confirmation_number": "ABC123",
                "details": {
                    "airline": "Delta",
                    "flight_number": "DL123",
                },
            }
        ]

        # Call the tool
        result = await create_itinerary_events_tool(
            calendar_id="calendar1",
            itinerary_items=itinerary_items,
            trip_name="Summer Vacation",
        )

        # Verify call
        self.mock_calendar_service.create_itinerary_events.assert_called_once()

        # Verify result
        self.assertEqual(len(result["created_events"]), 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["total_items"], 1)
        self.assertEqual(result["created_events"][0]["id"], "new_event")
        self.assertEqual(result["created_events"][0]["title"], "Flight to New York")
        self.assertEqual(result["created_events"][0]["location"], "JFK Airport")

        # Verify formatted output
        self.assertIn("Created 1 events for trip: Summer Vacation", result["formatted"])
        self.assertIn("Flight to New York", result["formatted"])

    @pytest.mark.asyncio
    async def test_error_handling_decorator_in_list_calendars(self):
        """Test that error handling decorator works properly."""
        # Mock client to raise an exception
        self.mock_calendar_client.get_calendars = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        # Call the tool
        result = await list_calendars_tool()

        # Verify call was attempted
        self.mock_calendar_client.get_calendars.assert_called_once()

        # Verify error handling worked properly
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API rate limit exceeded")
        self.assertNotIn("calendars", result)

    @pytest.mark.asyncio
    async def test_error_handling_decorator_in_create_event(self):
        """Test that error handling decorator works properly in create_event_tool."""
        # Mock client to raise an exception with specific error messages
        self.mock_calendar_client.create_event = AsyncMock(
            side_effect=ValueError("Invalid time format")
        )

        # Call the tool
        result = await create_event_tool(
            calendar_id="calendar1",
            summary="Test Event",
            start_time="invalid-time",  # This would normally cause an error
            end_time="invalid-time",
        )

        # Verify call was attempted
        self.mock_calendar_client.create_event.assert_called_once()

        # Verify error handling worked properly
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Invalid time format")

    @pytest.mark.asyncio
    async def test_error_handling_decorator_in_delete_event(self):
        """Test that error handling decorator works properly in delete_event_tool."""
        # Mock client to raise an exception
        self.mock_calendar_client.delete_event = AsyncMock(
            side_effect=Exception("Event not found")
        )

        # Call the tool
        result = await delete_event_tool(
            calendar_id="calendar1",
            event_id="nonexistent-event",
        )

        # Verify call was attempted
        self.mock_calendar_client.delete_event.assert_called_once()

        # Verify error handling worked properly
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Event not found")
        self.assertNotIn("success", result)


if __name__ == "__main__":
    unittest.main()
