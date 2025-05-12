"""
Tests for the Time MCP client.

This module contains tests for the Time MCP client implementation
that interfaces with the official MCP Time server.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.mcp.time.client import TimeMCPClient, TimeService
from src.utils.error_handling import MCPError


@pytest.fixture
def client():
    """Create a test client instance."""
    return TimeMCPClient(
        endpoint="http://test-endpoint",
        use_cache=False,
    )


@pytest.fixture
def mock_get_current_time_response():
    """Create a mock response for get_current_time."""
    return json.dumps({
        "timezone": "America/New_York",
        "datetime": "2025-05-12T14:30:00-04:00",
        "is_dst": True
    })


@pytest.fixture
def mock_convert_time_response():
    """Create a mock response for convert_time."""
    return json.dumps({
        "source": {
            "timezone": "America/New_York",
            "datetime": "2025-05-12T14:30:00-04:00",
            "is_dst": True
        },
        "target": {
            "timezone": "Europe/London",
            "datetime": "2025-05-12T19:30:00+01:00",
            "is_dst": True
        },
        "time_difference": "+5h"
    })


class TestTimeMCPClient:
    """Tests for the TimeMCPClient class."""

    @patch("src.mcp.time.client.BaseMCPClient.call_tool")
    async def test_get_current_time(self, mock_call_tool, client, mock_get_current_time_response):
        """Test getting current time for a timezone."""
        mock_call_tool.return_value = mock_get_current_time_response

        result = await client.get_current_time("America/New_York")

        mock_call_tool.assert_called_once_with(
            "get_current_time", {"timezone": "America/New_York"}, False
        )

        assert result["timezone"] == "America/New_York"
        assert result["current_time"] == "14:30:00"
        assert result["current_date"] == "2025-05-12"
        assert result["is_dst"] is True

    @patch("src.mcp.time.client.BaseMCPClient.call_tool")
    async def test_convert_time(self, mock_call_tool, client, mock_convert_time_response):
        """Test converting time between timezones."""
        mock_call_tool.return_value = mock_convert_time_response

        result = await client.convert_time(
            time="14:30",
            source_timezone="America/New_York",
            target_timezone="Europe/London"
        )

        mock_call_tool.assert_called_once_with(
            "convert_time",
            {
                "source_timezone": "America/New_York",
                "time": "14:30",
                "target_timezone": "Europe/London"
            },
            False
        )

        assert result["source_timezone"] == "America/New_York"
        assert result["source_time"] == "14:30"
        assert result["target_timezone"] == "Europe/London"
        assert result["target_time"] == "19:30:00"
        assert result["time_difference"] == "+5h"

    @patch("src.mcp.time.client.BaseMCPClient.call_tool")
    async def test_get_current_time_error(self, mock_call_tool, client):
        """Test error handling for get_current_time."""
        mock_call_tool.side_effect = Exception("API error")

        with pytest.raises(MCPError):
            await client.get_current_time("Invalid/Timezone")

    @patch("src.mcp.time.client.BaseMCPClient.call_tool")
    async def test_convert_time_error(self, mock_call_tool, client):
        """Test error handling for convert_time."""
        mock_call_tool.side_effect = Exception("API error")

        with pytest.raises(MCPError):
            await client.convert_time(
                time="14:30",
                source_timezone="America/New_York",
                target_timezone="Invalid/Timezone"
            )


class TestTimeService:
    """Tests for the TimeService class."""

    @patch("src.mcp.time.client.TimeMCPClient.get_current_time")
    async def test_get_local_time(self, mock_get_current_time):
        """Test getting local time for a location."""
        mock_response = {
            "timezone": "America/New_York",
            "current_time": "14:30:00",
            "current_date": "2025-05-12",
            "utc_offset": "04:00",
            "is_dst": True
        }
        mock_get_current_time.return_value = mock_response

        # Create client and service
        client = TimeMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = TimeService(client)

        # Test with known location
        result = await service.get_local_time("New York")
        mock_get_current_time.assert_called_once_with("America/New_York")
        assert result == mock_response

        # Reset mock
        mock_get_current_time.reset_mock()

        # Test with unknown location (should use UTC)
        result = await service.get_local_time("Unknown Location")
        mock_get_current_time.assert_called_once_with("UTC")

    @patch("src.mcp.time.client.TimeMCPClient.get_current_time")
    @patch("src.mcp.time.client.TimeMCPClient.convert_time")
    async def test_calculate_flight_arrival(self, mock_convert_time, mock_get_current_time):
        """Test calculating flight arrival time."""
        # Mock the get_current_time response
        mock_get_current_time.return_value = {
            "timezone": "America/New_York",
            "current_time": "14:30:00",
            "current_date": "2025-05-12",
            "utc_offset": "04:00",
            "is_dst": True
        }

        # Mock the convert_time response
        mock_convert_time.return_value = {
            "source_timezone": "America/New_York",
            "source_time": "19:30",
            "target_timezone": "Europe/London",
            "target_time": "00:30",
            "time_difference": "+5h"
        }

        # Create client and service
        client = TimeMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = TimeService(client)

        # Test flight arrival calculation
        result = await service.calculate_flight_arrival(
            departure_time="14:30",
            departure_timezone="America/New_York",
            flight_duration_hours=5.0,
            arrival_timezone="Europe/London"
        )

        # Verify the result
        assert result["departure_time"] == "14:30"
        assert result["departure_timezone"] == "America/New_York"
        assert result["flight_duration"] == "5h 0m"
        assert result["arrival_time_departure_tz"] == "19:30"
        assert result["arrival_time_local"] == "00:30"
        assert result["arrival_timezone"] == "Europe/London"
        assert result["time_difference"] == "+5h"
        assert result["day_offset"] == 0

    @patch("src.mcp.time.client.TimeMCPClient.get_current_time")
    @patch("src.mcp.time.client.TimeMCPClient.convert_time")
    async def test_calculate_flight_arrival_with_day_offset(self, mock_convert_time, mock_get_current_time):
        """Test calculating flight arrival time with day offset."""
        # Mock the get_current_time response
        mock_get_current_time.return_value = {
            "timezone": "America/New_York",
            "current_time": "14:30:00",
            "current_date": "2025-05-12",
            "utc_offset": "04:00",
            "is_dst": True
        }

        # Mock the convert_time response
        mock_convert_time.return_value = {
            "source_timezone": "America/New_York",
            "source_time": "02:30",
            "target_timezone": "Europe/London",
            "target_time": "07:30",
            "time_difference": "+5h"
        }

        # Create client and service
        client = TimeMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = TimeService(client)

        # Test flight arrival calculation with longer duration
        result = await service.calculate_flight_arrival(
            departure_time="14:30",
            departure_timezone="America/New_York",
            flight_duration_hours=12.0,
            arrival_timezone="Europe/London"
        )

        # Verify the result
        assert result["departure_time"] == "14:30"
        assert result["flight_duration"] == "12h 0m"
        assert result["arrival_time_departure_tz"] == "02:30"
        assert result["arrival_time_local"] == "07:30"
        assert result["day_offset"] == 1

    @patch("src.mcp.time.client.TimeService.get_local_time")
    @patch("src.mcp.time.client.TimeMCPClient.convert_time")
    async def test_create_timezone_aware_itinerary(self, mock_convert_time, mock_get_local_time):
        """Test creating timezone-aware itinerary."""
        # Mock the get_local_time responses
        tokyo_response = {
            "timezone": "Asia/Tokyo",
            "current_time": "03:30:00",
            "current_date": "2025-05-13",
            "utc_offset": "09:00",
            "is_dst": False
        }
        nyc_response = {
            "timezone": "America/New_York",
            "current_time": "14:30:00",
            "current_date": "2025-05-12",
            "utc_offset": "04:00",
            "is_dst": True
        }
        
        # Set up the mock to return different responses based on the location
        async def get_local_time_side_effect(location):
            if location.lower() == "tokyo":
                return tokyo_response
            elif location.lower() == "new york":
                return nyc_response
            else:
                return {
                    "timezone": "UTC",
                    "current_time": "18:30:00",
                    "current_date": "2025-05-12",
                    "utc_offset": "00:00",
                    "is_dst": False
                }
        
        mock_get_local_time.side_effect = get_local_time_side_effect
        
        # Mock convert_time
        mock_convert_time.return_value = {
            "source_timezone": "UTC",
            "source_time": "12:00",
            "target_timezone": "Asia/Tokyo",
            "target_time": "21:00",
            "time_difference": "+9h"
        }

        # Create client and service
        client = TimeMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = TimeService(client)

        # Create test itinerary
        itinerary = [
            {
                "day": 1,
                "location": "Tokyo",
                "description": "Visit Tokyo Tower",
                "time": "12:00",
                "time_format": "UTC"
            },
            {
                "day": 2,
                "location": "New York",
                "description": "Visit Central Park",
                "time": "14:00",
                "time_format": "local"
            }
        ]

        # Test creating timezone-aware itinerary
        result = await service.create_timezone_aware_itinerary(itinerary)

        # Verify the result
        assert len(result) == 2
        assert result[0]["location"] == "Tokyo"
        assert result[0]["timezone"] == "Asia/Tokyo"
        assert result[0]["local_time"] == "21:00"
        assert result[0]["utc_offset"] == "09:00"
        
        assert result[1]["location"] == "New York"
        assert result[1]["timezone"] == "America/New_York"
        assert result[1]["local_time"] == "14:00"  # Unchanged since it's already local
        assert result[1]["utc_offset"] == "04:00"

    @patch("src.mcp.time.client.TimeMCPClient.convert_time")
    async def test_find_meeting_times(self, mock_convert_time):
        """Test finding suitable meeting times."""
        # Set up convert_time mock with variable responses
        def convert_side_effect(time, source_timezone, target_timezone, skip_cache=False):
            hour, minute = map(int, time.split(":"))
            # For simplicity, assume 5 hour difference between NYC and London
            if source_timezone == "America/New_York" and target_timezone == "Europe/London":
                target_hour = (hour + 5) % 24
                return {
                    "source_timezone": source_timezone,
                    "source_time": time,
                    "target_timezone": target_timezone,
                    "target_time": f"{target_hour:02d}:{minute:02d}",
                    "time_difference": "+5h"
                }
            else:
                raise ValueError(f"Unexpected timezone conversion: {source_timezone} to {target_timezone}")
        
        mock_convert_time.side_effect = convert_side_effect

        # Create client and service
        client = TimeMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = TimeService(client)

        # Test finding meeting times
        result = await service.find_meeting_times(
            first_timezone="America/New_York",
            second_timezone="Europe/London",
            first_available_hours=(9, 17),
            second_available_hours=(9, 17)
        )

        # Verify the result
        # NYC 9-12 maps to London 14-17, which is within London's 9-17 range
        assert len(result) > 0
        assert all(9 <= int(time["first_time"].split(":")[0]) < 12 for time in result)
        assert all(14 <= int(time["second_time"].split(":")[0]) < 17 for time in result)
        assert all(time["time_difference"] == "+5h" for time in result)