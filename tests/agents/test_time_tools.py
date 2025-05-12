"""
Tests for the time tools used by TripSage agents.

These tests verify that the function tools for time operations
correctly interact with the Time MCP client.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.time_tools import (
    calculate_flight_arrival_tool,
    convert_timezone_tool,
    create_timezone_aware_itinerary_tool,
    find_meeting_times_tool,
    get_current_time_tool,
    get_local_time_tool,
)


@pytest.fixture
def mock_time_client():
    """Create a mock Time MCP client."""
    with patch("src.agents.time_tools.time_client") as mock:
        mock.get_current_time = AsyncMock()
        mock.convert_time = AsyncMock()
        yield mock


@pytest.fixture
def mock_time_service():
    """Create a mock Time Service."""
    with patch("src.agents.time_tools.time_service") as mock:
        mock.get_local_time = AsyncMock()
        mock.calculate_flight_arrival = AsyncMock()
        mock.create_timezone_aware_itinerary = AsyncMock()
        mock.find_meeting_times = AsyncMock()
        yield mock


class TestTimeFunctionTools:
    """Tests for the agent time function tools."""

    async def test_get_current_time_tool(self, mock_time_client):
        """Test the get_current_time_tool function."""
        mock_time_client.get_current_time.return_value = {
            "timezone": "America/New_York",
            "current_time": "14:30:00",
            "current_date": "2025-05-12",
            "utc_offset": "04:00",
            "is_dst": True,
        }

        result = await get_current_time_tool("America/New_York")

        mock_time_client.get_current_time.assert_called_once_with("America/New_York")
        assert result["current_time"] == "14:30:00"
        assert result["timezone"] == "America/New_York"
        assert "formatted" in result

    async def test_convert_timezone_tool(self, mock_time_client):
        """Test the convert_timezone_tool function."""
        mock_time_client.convert_time.return_value = {
            "source_timezone": "America/New_York",
            "source_time": "14:30",
            "target_timezone": "Europe/London",
            "target_time": "19:30",
            "time_difference": "+5h",
        }

        result = await convert_timezone_tool(
            time="14:30", from_tz="America/New_York", to_tz="Europe/London"
        )

        mock_time_client.convert_time.assert_called_once_with(
            time="14:30",
            source_timezone="America/New_York",
            target_timezone="Europe/London",
        )
        assert result["source_time"] == "14:30"
        assert result["target_time"] == "19:30"
        assert result["time_difference"] == "+5h"
        assert "formatted" in result

    async def test_get_local_time_tool(self, mock_time_service):
        """Test the get_local_time_tool function."""
        mock_time_service.get_local_time.return_value = {
            "timezone": "America/New_York",
            "current_time": "14:30:00",
            "current_date": "2025-05-12",
            "utc_offset": "04:00",
            "is_dst": True,
        }

        result = await get_local_time_tool("New York")

        mock_time_service.get_local_time.assert_called_once_with("New York")
        assert result["location"] == "New York"
        assert result["current_time"] == "14:30:00"
        assert result["timezone"] == "America/New_York"
        assert "formatted" in result

    async def test_calculate_flight_arrival_tool(self, mock_time_service):
        """Test the calculate_flight_arrival_tool function."""

        # Mock local time for both locations
        async def get_local_time_side_effect(location):
            if location == "New York":
                return {"timezone": "America/New_York"}
            elif location == "London":
                return {"timezone": "Europe/London"}
            else:
                return {"timezone": "UTC"}

        mock_time_service.get_local_time.side_effect = get_local_time_side_effect

        # Mock flight arrival calculation
        mock_time_service.calculate_flight_arrival.return_value = {
            "departure_time": "14:30",
            "departure_timezone": "America/New_York",
            "flight_duration": "7h 0m",
            "arrival_time_departure_tz": "21:30",
            "arrival_time_local": "02:30",
            "arrival_timezone": "Europe/London",
            "time_difference": "+5h",
            "day_offset": 0,
        }

        result = await calculate_flight_arrival_tool(
            departure_time="14:30",
            departure_location="New York",
            flight_duration_hours=7.0,
            arrival_location="London",
        )

        # Verify the result
        assert result["departure_location"] == "New York"
        assert result["departure_time"] == "14:30"
        assert result["flight_duration"] == "7h 0m"
        assert result["arrival_location"] == "London"
        assert result["arrival_time_local"] == "02:30"
        assert "formatted" in result

    async def test_find_meeting_times_tool(self, mock_time_service):
        """Test the find_meeting_times_tool function."""

        # Mock local time for both locations
        async def get_local_time_side_effect(location):
            if location == "New York":
                return {"timezone": "America/New_York"}
            elif location == "London":
                return {"timezone": "Europe/London"}
            else:
                return {"timezone": "UTC"}

        mock_time_service.get_local_time.side_effect = get_local_time_side_effect

        # Mock suitable meeting times
        mock_time_service.find_meeting_times.return_value = [
            {
                "first_timezone": "America/New_York",
                "first_time": "09:00",
                "second_timezone": "Europe/London",
                "second_time": "14:00",
                "time_difference": "+5h",
            },
            {
                "first_timezone": "America/New_York",
                "first_time": "09:30",
                "second_timezone": "Europe/London",
                "second_time": "14:30",
                "time_difference": "+5h",
            },
        ]

        result = await find_meeting_times_tool(
            first_location="New York",
            second_location="London",
            first_available_hours="9-17",
            second_available_hours="9-17",
        )

        # Verify the result
        assert result["first_location"] == "New York"
        assert result["second_location"] == "London"
        assert result["count"] == 2
        assert len(result["suitable_times"]) == 2
        assert "formatted" in result

    async def test_create_timezone_aware_itinerary_tool(self, mock_time_service):
        """Test the create_timezone_aware_itinerary_tool function."""
        # Create test itinerary
        itinerary = [
            {
                "day": 1,
                "location": "Tokyo",
                "description": "Visit Tokyo Tower",
                "time": "12:00",
                "time_format": "UTC",
            },
            {
                "day": 2,
                "location": "New York",
                "description": "Visit Central Park",
                "time": "14:00",
                "time_format": "local",
            },
        ]

        # Mock processed itinerary
        processed_itinerary = [
            {
                "day": 1,
                "location": "Tokyo",
                "description": "Visit Tokyo Tower",
                "time": "12:00",
                "time_format": "UTC",
                "timezone": "Asia/Tokyo",
                "local_time": "21:00",
                "utc_offset": "09:00",
            },
            {
                "day": 2,
                "location": "New York",
                "description": "Visit Central Park",
                "time": "14:00",
                "time_format": "local",
                "timezone": "America/New_York",
                "local_time": "14:00",
                "utc_offset": "04:00",
            },
        ]

        mock_time_service.create_timezone_aware_itinerary.return_value = (
            processed_itinerary
        )

        result = await create_timezone_aware_itinerary_tool(itinerary)

        # Verify the result
        mock_time_service.create_timezone_aware_itinerary.assert_called_once_with(
            itinerary
        )
        assert result["count"] == 2
        assert len(result["itinerary"]) == 2
        assert result["itinerary"][0]["timezone"] == "Asia/Tokyo"
        assert result["itinerary"][1]["timezone"] == "America/New_York"
