"""
Tests for the Time MCP client with official Time MCP server.

These tests verify that the Time MCP client correctly interacts with the
official Time MCP server and properly parses the responses.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp.time.client import TimeService, TimeMCPClient
from src.mcp.time.models import TimeResponse, TimeConversionResponse


@pytest.fixture
def mock_time_client():
    """Create a mocked TimeMCPClient for testing."""
    client = MagicMock(spec=TimeMCPClient)
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def time_service(mock_time_client):
    """Create a TimeService with a mocked TimeMCPClient."""
    return TimeService(client=mock_time_client)


@pytest.mark.asyncio
async def test_get_current_time():
    """Test that get_current_time correctly parses the official MCP Time response."""
    # Create a real client, but mock the call_tool method
    client = TimeMCPClient(endpoint="http://localhost:3000")
    
    # Mock the response from the official Time MCP server
    mock_response = {
        "timezone": "America/New_York",
        "datetime": "2025-05-10T14:30:45-04:00",
        "is_dst": True
    }
    
    with patch.object(client, 'call_tool', new=AsyncMock(return_value=mock_response)):
        result = await client.get_current_time("America/New_York")
        
        assert isinstance(result, TimeResponse)
        assert result.timezone == "America/New_York"
        assert result.current_time == "14:30:45"
        assert result.current_date == "2025-05-10"
        assert result.utc_offset == "04:00"
        assert result.is_dst is True


@pytest.mark.asyncio
async def test_convert_time():
    """Test that convert_time correctly parses the official MCP Time response."""
    # Create a real client, but mock the call_tool method
    client = TimeMCPClient(endpoint="http://localhost:3000")
    
    # Mock the response from the official Time MCP server
    mock_response = {
        "source": {
            "timezone": "America/New_York",
            "datetime": "2025-05-10T14:30:00-04:00",
            "is_dst": True
        },
        "target": {
            "timezone": "Europe/London",
            "datetime": "2025-05-10T19:30:00+01:00",
            "is_dst": True
        },
        "time_difference": "+5 hours"
    }
    
    with patch.object(client, 'call_tool', new=AsyncMock(return_value=mock_response)):
        result = await client.convert_time(
            time="14:30",
            source_timezone="America/New_York",
            target_timezone="Europe/London"
        )
        
        assert isinstance(result, TimeConversionResponse)
        assert result.source.timezone == "America/New_York"
        assert result.target.timezone == "Europe/London"
        assert result.source.datetime == "2025-05-10T14:30:00-04:00"
        assert result.target.datetime == "2025-05-10T19:30:00+01:00"
        assert result.time_difference == "+5 hours"


@pytest.mark.asyncio
async def test_calculate_flight_arrival(time_service, mock_time_client):
    """Test that calculate_flight_arrival correctly computes arrival times."""
    # First, we need to mock the get_current_time method
    mock_current_time = TimeResponse(
        timezone="America/New_York",
        current_time="14:30:45",
        current_date="2025-05-10",
        utc_offset="04:00",
        is_dst=True
    )
    mock_time_client.get_current_time.return_value = mock_current_time
    
    # Then, we need to mock the convert_time method
    mock_conversion = TimeConversionResponse(
        source={
            "timezone": "America/New_York",
            "datetime": "2025-05-10T21:30:00-04:00",
            "is_dst": True
        },
        target={
            "timezone": "Europe/London",
            "datetime": "2025-05-11T02:30:00+01:00",
            "is_dst": True
        },
        time_difference="+5 hours"
    )
    mock_time_client.convert_time.return_value = mock_conversion
    
    # Now we can test the flight arrival calculation
    result = await time_service.calculate_flight_arrival(
        departure_time="14:30",
        departure_timezone="America/New_York",
        flight_duration_hours=7.0,
        arrival_timezone="Europe/London"
    )
    
    # Verify the result
    assert result.departure_time == "14:30"
    assert result.departure_timezone == "America/New_York"
    assert result.flight_duration == "7h 0m"
    assert result.arrival_time_departure_tz == "21:30"
    assert result.arrival_time_local == "02:30:00"
    assert result.arrival_timezone == "Europe/London"
    assert result.time_difference == "+5 hours"
    assert result.day_offset == 0


@pytest.mark.asyncio
async def test_find_meeting_times(time_service, mock_time_client):
    """Test that find_meeting_times correctly identifies suitable meeting times."""
    # First, mock the get_local_time method which calls get_current_time
    mock_time_client.get_current_time.return_value = TimeResponse(
        timezone="America/New_York",
        current_time="14:30:45",
        current_date="2025-05-10",
        utc_offset="04:00",
        is_dst=True
    )
    
    # Mock several calls to convert_time with different inputs
    async def mock_convert_time(time, source_timezone, target_timezone, **kwargs):
        # Convert time from NY to London (5 hour difference)
        if source_timezone == "America/New_York" and target_timezone == "Europe/London":
            hour, minute = map(int, time.split(":"))
            target_hour = (hour + 5) % 24
            
            return TimeConversionResponse(
                source={
                    "timezone": source_timezone,
                    "datetime": f"2025-05-10T{hour:02d}:{minute:02d}:00-04:00",
                    "is_dst": True
                },
                target={
                    "timezone": target_timezone,
                    "datetime": f"2025-05-10T{target_hour:02d}:{minute:02d}:00+01:00",
                    "is_dst": True
                },
                time_difference="+5 hours"
            )
        return None
    
    mock_time_client.convert_time.side_effect = mock_convert_time
    
    # Now test the find_meeting_times method
    # For NY (9-17) and London (9-17), only 12-17 NY time will work
    # (corresponding to 17-22 London time, but we only need 17)
    result = await time_service.find_meeting_times(
        first_timezone="America/New_York",
        second_timezone="Europe/London",
        first_available_hours=(9, 17),
        second_available_hours=(9, 17)
    )
    
    # We expect to find 12:00, 12:30, 13:00, ..., 16:30 (10 times)
    assert len(result) == 10
    
    # Check the first time
    assert result[0].first_timezone == "America/New_York"
    assert result[0].first_time == "12:00"
    assert result[0].second_timezone == "Europe/London"
    assert result[0].second_time == "17:00:00"


@pytest.mark.asyncio
async def test_create_timezone_aware_itinerary(time_service, mock_time_client):
    """Test that create_timezone_aware_itinerary correctly adds timezone info to items."""
    # Mock get_local_time which uses get_current_time
    async def mock_get_local_time(location):
        location_timezone_map = {
            "new york": "America/New_York",
            "london": "Europe/London"
        }
        timezone = location_timezone_map.get(location.lower(), "UTC")
        
        return TimeResponse(
            timezone=timezone,
            current_time="14:30:45",
            current_date="2025-05-10",
            utc_offset="00:00",
            is_dst=False
        )
    
    time_service.get_local_time = AsyncMock(side_effect=mock_get_local_time)
    
    # Mock convert_time for time conversions
    mock_time_client.convert_time.return_value = TimeConversionResponse(
        source={
            "timezone": "UTC",
            "datetime": "2025-05-10T12:00:00Z",
            "is_dst": False
        },
        target={
            "timezone": "America/New_York",
            "datetime": "2025-05-10T08:00:00-04:00",
            "is_dst": True
        },
        time_difference="-4 hours"
    )
    
    # Test creating a timezone-aware itinerary
    itinerary_items = [
        {
            "location": "New York",
            "activity": "Museum visit",
            "time": "12:00",
            "time_format": "UTC"
        },
        {
            "location": "London",
            "activity": "Dinner",
            "time": "19:00",
            "time_format": "local"
        }
    ]
    
    result = await time_service.create_timezone_aware_itinerary(itinerary_items)
    
    # Check the results
    assert len(result) == 2
    
    # Check first item (New York with UTC time that was converted)
    assert result[0].location == "New York"
    assert result[0].activity == "Museum visit"
    assert result[0].time == "12:00"
    assert result[0].time_format == "UTC"
    assert result[0].timezone == "America/New_York"
    assert result[0].local_time == "08:00:00"
    
    # Check second item (London with local time that wasn't converted)
    assert result[1].location == "London"
    assert result[1].activity == "Dinner"
    assert result[1].time == "19:00"
    assert result[1].time_format == "local"
    assert result[1].timezone == "Europe/London"