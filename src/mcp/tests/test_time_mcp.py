"""
Unit tests for the Time MCP implementation.
"""

import pytest
import datetime
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from pydantic import ValidationError

from ..time import client
from ..time.api_client import TimeZoneDatabase, TimeFormat
from ..time.client import TimeMCPClient, TimeService


class TestTimeZoneDatabase:
    """Tests for the TimeZoneDatabase class."""
    
    @pytest.fixture
    def timezone_db(self):
        """Create a TimeZoneDatabase instance for testing."""
        return TimeZoneDatabase()
    
    @pytest.mark.asyncio
    async def test_list_timezones(self, timezone_db):
        """Test listing timezones."""
        timezones = await timezone_db.list_timezones()
        assert isinstance(timezones, list)
        assert len(timezones) > 0
        assert "UTC" in timezones
        assert "America/New_York" in timezones
    
    @pytest.mark.asyncio
    async def test_get_timezone_info(self, timezone_db):
        """Test getting timezone info."""
        info = await timezone_db.get_timezone_info("UTC")
        assert info["timezone"] == "UTC"
        assert info["abbreviation"] in ["UTC", "GMT"]
        assert info["utc_offset"] == "+00:00"
        assert info["utc_offset_seconds"] == 0
        
        # Test invalid timezone
        with pytest.raises(ValueError):
            await timezone_db.get_timezone_info("Invalid/Timezone")
    
    @pytest.mark.asyncio
    async def test_get_current_time(self, timezone_db):
        """Test getting current time."""
        result = await timezone_db.get_current_time("UTC")
        assert result["timezone"] == "UTC"
        assert "current_time" in result
        assert "current_date" in result
        assert "utc_offset" in result
        assert "unix_timestamp" in result
        
        # Test invalid timezone
        with pytest.raises(ValueError):
            await timezone_db.get_current_time("Invalid/Timezone")
    
    @pytest.mark.asyncio
    async def test_convert_time(self, timezone_db):
        """Test converting time between timezones."""
        result = await timezone_db.convert_time(
            time_str="12:00",
            source_timezone="UTC",
            target_timezone="America/New_York"
        )
        
        assert result["source_timezone"] == "UTC"
        assert result["source_time"] == "12:00"
        assert result["target_timezone"] == "America/New_York"
        assert "target_time" in result
        assert "time_difference" in result
        
        # Test invalid time format
        with pytest.raises(ValueError):
            await timezone_db.convert_time(
                time_str="25:00",  # Invalid hour
                source_timezone="UTC",
                target_timezone="America/New_York"
            )
        
        # Test invalid timezone
        with pytest.raises(ValueError):
            await timezone_db.convert_time(
                time_str="12:00",
                source_timezone="Invalid/Timezone",
                target_timezone="UTC"
            )
    
    @pytest.mark.asyncio
    async def test_calculate_travel_time(self, timezone_db):
        """Test calculating travel time."""
        result = await timezone_db.calculate_travel_time(
            departure_timezone="America/New_York",
            departure_time="08:00",
            arrival_timezone="Europe/London",
            arrival_time="20:00"
        )
        
        assert result["departure_timezone"] == "America/New_York"
        assert result["departure_time"] == "08:00"
        assert result["arrival_timezone"] == "Europe/London"
        assert result["arrival_time"] == "20:00"
        assert "travel_time_hours" in result
        assert "travel_time_formatted" in result
        
        # Test invalid time format
        with pytest.raises(ValueError):
            await timezone_db.calculate_travel_time(
                departure_timezone="America/New_York",
                departure_time="8:00",  # Missing leading zero
                arrival_timezone="Europe/London",
                arrival_time="20:00"
            )
    
    @pytest.mark.asyncio
    async def test_format_date(self, timezone_db):
        """Test formatting dates."""
        result = await timezone_db.format_date(
            date_str="2025-07-04T10:30:00",
            timezone="America/New_York",
            format_type=TimeFormat.FULL
        )
        
        assert result["original_date"] == "2025-07-04T10:30:00"
        assert result["timezone"] == "America/New_York"
        assert result["format_type"] == TimeFormat.FULL
        assert "formatted_date" in result
        
        # Test different formats
        short_result = await timezone_db.format_date(
            date_str="2025-07-04",
            timezone="America/New_York",
            format_type=TimeFormat.SHORT
        )
        
        assert short_result["format_type"] == TimeFormat.SHORT
        
        # Test invalid date format
        with pytest.raises(ValueError):
            await timezone_db.format_date(
                date_str="07/04/2025",  # Not ISO format
                timezone="America/New_York",
                format_type=TimeFormat.FULL
            )


class TestTimeMCPClient:
    """Tests for the TimeMCPClient class."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock TimeMCPClient for testing."""
        with patch("src.mcp.time.client.BaseMCPClient.__init__", return_value=None):
            client = TimeMCPClient(endpoint="http://localhost:8004")
            client.call_tool = AsyncMock()
            return client
    
    @pytest.mark.asyncio
    async def test_get_current_time(self, mock_client):
        """Test getting current time."""
        mock_response = {
            "current_time": "2025-05-10 14:30:00",
            "timezone": "America/New_York",
            "utc_offset": "-04:00",
            "is_dst": True
        }
        mock_client.call_tool.return_value = mock_response
        
        result = await mock_client.get_current_time(timezone="America/New_York")
        
        mock_client.call_tool.assert_called_once_with(
            "get_current_time", 
            {"timezone": "America/New_York"}, 
            skip_cache=False
        )
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_convert_time(self, mock_client):
        """Test converting time between timezones."""
        mock_response = {
            "source_time": "14:30",
            "target_time": "19:30",
            "source_timezone": "America/New_York",
            "target_timezone": "Europe/London",
            "time_difference": "+5.0"
        }
        mock_client.call_tool.return_value = mock_response
        
        result = await mock_client.convert_time(
            time="14:30",
            source_timezone="America/New_York",
            target_timezone="Europe/London"
        )
        
        mock_client.call_tool.assert_called_once_with(
            "convert_time", 
            {
                "time": "14:30",
                "source_timezone": "America/New_York",
                "target_timezone": "Europe/London"
            }, 
            skip_cache=False
        )
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_calculate_travel_time(self, mock_client):
        """Test calculating travel time."""
        mock_response = {
            "departure": {
                "timezone": "America/New_York",
                "time": "14:30",
                "utc_time": "18:30"
            },
            "arrival": {
                "timezone": "Europe/London",
                "time": "02:30",
                "utc_time": "01:30"
            },
            "duration": {
                "hours": 7,
                "minutes": 0,
                "total_minutes": 420,
                "formatted": "7h 0m"
            }
        }
        mock_client.call_tool.return_value = mock_response
        
        result = await mock_client.calculate_travel_time(
            departure_timezone="America/New_York",
            departure_time="14:30",
            arrival_timezone="Europe/London",
            arrival_time="02:30"
        )
        
        mock_client.call_tool.assert_called_once_with(
            "calculate_travel_time", 
            {
                "departure_timezone": "America/New_York",
                "departure_time": "14:30",
                "arrival_timezone": "Europe/London",
                "arrival_time": "02:30"
            }, 
            skip_cache=False
        )
        assert result == mock_response


class TestTimeService:
    """Tests for the TimeService class."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock TimeService for testing."""
        mock_client = Mock()
        mock_client.get_current_time = AsyncMock()
        mock_client.convert_time = AsyncMock()
        return TimeService(client=mock_client)
    
    @pytest.mark.asyncio
    async def test_get_local_time(self, mock_service):
        """Test getting local time for a destination."""
        mock_response = {
            "current_time": "2025-05-10 14:30:00",
            "timezone": "Asia/Tokyo",
            "utc_offset": "+09:00",
            "is_dst": False
        }
        mock_service.client.get_current_time.return_value = mock_response
        
        result = await mock_service.get_local_time("Tokyo")
        
        mock_service.client.get_current_time.assert_called_once_with(timezone="Asia/Tokyo")
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_calculate_flight_arrival(self, mock_service):
        """Test calculating flight arrival time."""
        # Mock responses for the calls made by calculate_flight_arrival
        mock_service.client.get_current_time.return_value = {
            "current_time": "2025-05-10 08:00:00",
            "timezone": "America/New_York",
            "utc_offset": "-04:00",
            "is_dst": True
        }
        
        mock_service.client.convert_time.return_value = {
            "source_time": "15:30",
            "target_time": "21:30",
            "source_timezone": "America/New_York",
            "target_timezone": "Europe/Paris",
            "time_difference": "+6.0"
        }
        
        result = await mock_service.calculate_flight_arrival(
            departure_time="08:00",
            departure_timezone="America/New_York",
            flight_duration_hours=7.5,
            arrival_timezone="Europe/Paris"
        )
        
        # Check that the service made the expected calls
        mock_service.client.get_current_time.assert_called_once_with(timezone="America/New_York")
        mock_service.client.convert_time.assert_called_once()
        
        # Check the result structure
        assert "departure_time" in result
        assert "departure_timezone" in result
        assert "flight_duration" in result
        assert "arrival_time_departure_tz" in result
        assert "arrival_time_local" in result
        assert "arrival_timezone" in result