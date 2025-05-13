"""
Unit tests for Google Calendar MCP client.
"""

import unittest
from unittest.mock import AsyncMock

import pytest

from src.mcp.calendar.client import CalendarMCPClient
from src.mcp.calendar.models import (
    CalendarListResponse,
    Event,
    EventListResponse,
    EventSearchResponse,
)


class TestCalendarMCPClient(unittest.TestCase):
    """Test Google Calendar MCP client functionality."""

    def setUp(self):
        """Set up the test environment."""
        self.client = CalendarMCPClient(endpoint="http://test-endpoint")
        self.client.call_tool = AsyncMock()

    @pytest.mark.asyncio
    async def test_get_calendars(self):
        """Test the get_calendars method."""
        # Mock response
        mock_calendars = [
            {
                "id": "calendar1",
                "summary": "Primary Calendar",
                "primary": True,
                "time_zone": "America/New_York",
            },
            {
                "id": "calendar2",
                "summary": "Work Calendar",
                "primary": False,
                "time_zone": "America/New_York",
            },
        ]
        mock_response = {"calendars": mock_calendars}

        self.client.call_tool.return_value = mock_response

        # Call the method
        result = await self.client.get_calendars()

        # Verify call
        self.client.call_tool.assert_called_once_with(
            "list-calendars", {}, skip_cache=False
        )

        # Verify result
        self.assertIsInstance(result, CalendarListResponse)
        self.assertEqual(len(result.calendars), 2)
        self.assertEqual(result.calendars[0].id, "calendar1")
        self.assertEqual(result.calendars[0].summary, "Primary Calendar")
        self.assertTrue(result.calendars[0].primary)
        self.assertEqual(result.calendars[1].id, "calendar2")
        self.assertEqual(result.calendars[1].summary, "Work Calendar")
        self.assertFalse(result.calendars[1].primary)

    @pytest.mark.asyncio
    async def test_get_events(self):
        """Test the get_events method."""
        # Mock response
        mock_events = [
            {
                "id": "event1",
                "calendar_id": "calendar1",
                "summary": "Team Meeting",
                "description": "Weekly team sync",
                "location": "Conference Room A",
                "start": {"date_time": "2025-05-20T10:00:00Z"},
                "end": {"date_time": "2025-05-20T11:00:00Z"},
            },
            {
                "id": "event2",
                "calendar_id": "calendar1",
                "summary": "Lunch",
                "start": {"date_time": "2025-05-20T12:00:00Z"},
                "end": {"date_time": "2025-05-20T13:00:00Z"},
            },
        ]
        mock_response = {"events": mock_events}

        self.client.call_tool.return_value = mock_response

        # Call the method
        result = await self.client.get_events(
            calendar_id="calendar1",
            time_min="2025-05-20T00:00:00Z",
            time_max="2025-05-20T23:59:59Z",
        )

        # Verify call
        self.client.call_tool.assert_called_once()
        call_args = self.client.call_tool.call_args[0][1]
        self.assertEqual(call_args["calendar_id"], "calendar1")
        self.assertEqual(call_args["time_min"], "2025-05-20T00:00:00Z")
        self.assertEqual(call_args["time_max"], "2025-05-20T23:59:59Z")

        # Verify result
        self.assertIsInstance(result, EventListResponse)
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].id, "event1")
        self.assertEqual(result.events[0].summary, "Team Meeting")
        self.assertEqual(result.events[0].description, "Weekly team sync")
        self.assertEqual(result.events[0].location, "Conference Room A")
        self.assertEqual(result.events[1].id, "event2")
        self.assertEqual(result.events[1].summary, "Lunch")

    @pytest.mark.asyncio
    async def test_search_events(self):
        """Test the search_events method."""
        # Mock response
        mock_events = [
            {
                "id": "event1",
                "calendar_id": "calendar1",
                "summary": "Team Meeting",
                "description": "Weekly team sync",
                "start": {"date_time": "2025-05-20T10:00:00Z"},
                "end": {"date_time": "2025-05-20T11:00:00Z"},
            },
        ]
        mock_response = {"events": mock_events}

        self.client.call_tool.return_value = mock_response

        # Call the method
        result = await self.client.search_events(
            calendar_id="calendar1",
            query="team",
        )

        # Verify call
        self.client.call_tool.assert_called_once()
        call_args = self.client.call_tool.call_args[0][1]
        self.assertEqual(call_args["calendar_id"], "calendar1")
        self.assertEqual(call_args["query"], "team")

        # Verify result
        self.assertIsInstance(result, EventSearchResponse)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].id, "event1")
        self.assertEqual(result.events[0].summary, "Team Meeting")

    @pytest.mark.asyncio
    async def test_create_event(self):
        """Test the create_event method."""
        # Mock response
        mock_event = {
            "id": "new_event",
            "calendar_id": "calendar1",
            "summary": "New Meeting",
            "description": "Project kickoff",
            "location": "Conference Room B",
            "start": {"date_time": "2025-05-25T14:00:00Z"},
            "end": {"date_time": "2025-05-25T15:00:00Z"},
        }

        self.client.call_tool.return_value = mock_event

        # Call the method
        result = await self.client.create_event(
            calendar_id="calendar1",
            summary="New Meeting",
            description="Project kickoff",
            location="Conference Room B",
            start={"date_time": "2025-05-25T14:00:00Z"},
            end={"date_time": "2025-05-25T15:00:00Z"},
        )

        # Verify call
        self.client.call_tool.assert_called_once()
        call_args = self.client.call_tool.call_args[0][1]
        self.assertEqual(call_args["calendar_id"], "calendar1")
        self.assertEqual(call_args["summary"], "New Meeting")
        self.assertEqual(call_args["description"], "Project kickoff")
        self.assertEqual(call_args["location"], "Conference Room B")

        # Verify result
        self.assertIsInstance(result, Event)
        self.assertEqual(result.id, "new_event")
        self.assertEqual(result.summary, "New Meeting")
        self.assertEqual(result.description, "Project kickoff")
        self.assertEqual(result.location, "Conference Room B")

    @pytest.mark.asyncio
    async def test_update_event(self):
        """Test the update_event method."""
        # Mock response
        mock_event = {
            "id": "event1",
            "calendar_id": "calendar1",
            "summary": "Updated Meeting",
            "description": "Updated description",
            "location": "Conference Room C",
            "start": {"date_time": "2025-05-25T16:00:00Z"},
            "end": {"date_time": "2025-05-25T17:00:00Z"},
        }

        self.client.call_tool.return_value = mock_event

        # Call the method
        result = await self.client.update_event(
            calendar_id="calendar1",
            event_id="event1",
            summary="Updated Meeting",
            description="Updated description",
            location="Conference Room C",
            start={"date_time": "2025-05-25T16:00:00Z"},
            end={"date_time": "2025-05-25T17:00:00Z"},
        )

        # Verify call
        self.client.call_tool.assert_called_once()
        call_args = self.client.call_tool.call_args[0][1]
        self.assertEqual(call_args["calendar_id"], "calendar1")
        self.assertEqual(call_args["event_id"], "event1")
        self.assertEqual(call_args["summary"], "Updated Meeting")
        self.assertEqual(call_args["description"], "Updated description")
        self.assertEqual(call_args["location"], "Conference Room C")

        # Verify result
        self.assertIsInstance(result, Event)
        self.assertEqual(result.id, "event1")
        self.assertEqual(result.summary, "Updated Meeting")
        self.assertEqual(result.description, "Updated description")
        self.assertEqual(result.location, "Conference Room C")

    @pytest.mark.asyncio
    async def test_delete_event(self):
        """Test the delete_event method."""
        # Mock response
        mock_response = {"success": True, "deleted": True}

        self.client.call_tool.return_value = mock_response

        # Call the method
        result = await self.client.delete_event(
            calendar_id="calendar1",
            event_id="event1",
        )

        # Verify call
        self.client.call_tool.assert_called_once()
        call_args = self.client.call_tool.call_args[0][1]
        self.assertEqual(call_args["calendar_id"], "calendar1")
        self.assertEqual(call_args["event_id"], "event1")

        # Verify result
        self.assertTrue(result["success"])
        self.assertTrue(result["deleted"])


if __name__ == "__main__":
    unittest.main()
