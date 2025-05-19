"""Tests for TimeMCPWrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import (
    MCPClientError,
    MCPInvocationError,
    MCPTimeoutError,
    TripSageMCPError,
)
from tripsage.mcp_abstraction.wrappers.time_wrapper import TimeMCPWrapper


class TestTimeMCPWrapper:
    """Test cases for TimeMCPWrapper."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock TimeMCPClient."""
        client = MagicMock()
        # Setup common methods
        client.get_current_time = AsyncMock(
            return_value={"time": "2023-01-15T10:30:00Z", "timezone": "UTC"}
        )
        client.convert_time = AsyncMock(
            return_value={"converted_time": "2023-01-15T05:30:00", "timezone": "EST"}
        )
        client.calculate_flight_arrival_time = AsyncMock(
            return_value={"arrival_time": "2023-01-15T20:45:00Z"}
        )
        client.find_optimal_meeting_time = AsyncMock(
            return_value={"optimal_time": "2023-01-15T15:00:00Z"}
        )
        client.process_itinerary_timezones = AsyncMock(
            return_value={
                "processed_events": [{"event": "Meeting", "local_time": "10:00 AM"}]
            }
        )
        return client

    @pytest.fixture
    def wrapper(self, mock_client):
        """Create a TimeMCPWrapper with mocked client."""
        return TimeMCPWrapper(client=mock_client, mcp_name="time-test")

    def test_initialization_with_client(self, mock_client):
        """Test wrapper initialization with provided client."""
        wrapper = TimeMCPWrapper(client=mock_client, mcp_name="time-test")
        assert wrapper.client == mock_client
        assert wrapper.mcp_name == "time-test"

    @patch("tripsage.mcp_abstraction.wrappers.time_wrapper.get_client")
    def test_initialization_without_client(self, mock_get_client):
        """Test wrapper initialization without provided client."""
        mock_client_instance = MagicMock()
        mock_get_client.return_value = mock_client_instance

        wrapper = TimeMCPWrapper()

        mock_get_client.assert_called_once()
        assert wrapper.client == mock_client_instance
        assert wrapper.mcp_name == "time"

    def test_method_map(self, wrapper):
        """Test method mapping is correctly built."""
        method_map = wrapper._method_map

        # Test time operations aliases
        assert method_map["get_current_time"] == "get_current_time"
        assert method_map["get_time"] == "get_current_time"
        assert method_map["current_time"] == "get_current_time"
        assert method_map["now"] == "get_current_time"

        # Test timezone conversion aliases
        assert method_map["convert_time"] == "convert_time"
        assert method_map["convert_timezone"] == "convert_time"
        assert method_map["timezone_convert"] == "convert_time"

        # Test flight calculations
        assert method_map["calculate_arrival_time"] == "calculate_flight_arrival_time"
        assert method_map["flight_arrival_time"] == "calculate_flight_arrival_time"

        # Test meeting time aliases
        assert method_map["find_meeting_time"] == "find_optimal_meeting_time"
        assert method_map["optimize_meeting_time"] == "find_optimal_meeting_time"
        assert method_map["suggest_meeting_time"] == "find_optimal_meeting_time"

        # Test itinerary processing
        assert method_map["process_itinerary"] == "process_itinerary_timezones"
        assert method_map["itinerary_timezones"] == "process_itinerary_timezones"

    def test_get_available_methods(self, wrapper):
        """Test getting available methods."""
        methods = wrapper.get_available_methods()

        # Check that all aliases are included
        expected_methods = {
            "get_current_time",
            "get_time",
            "current_time",
            "now",
            "convert_time",
            "convert_timezone",
            "timezone_convert",
            "calculate_arrival_time",
            "flight_arrival_time",
            "find_meeting_time",
            "optimize_meeting_time",
            "suggest_meeting_time",
            "process_itinerary",
            "itinerary_timezones",
        }
        assert set(methods) == expected_methods

    @pytest.mark.asyncio
    async def test_invoke_current_time_aliases(self, wrapper):
        """Test invoking current time with different aliases."""
        # Test different aliases all map to same method
        for alias in ["get_current_time", "get_time", "current_time", "now"]:
            result = await wrapper.invoke_method(alias, timezone="UTC")
            assert result == {"time": "2023-01-15T10:30:00Z", "timezone": "UTC"}
            wrapper.client.get_current_time.assert_called_with(timezone="UTC")
            wrapper.client.get_current_time.reset_mock()

    @pytest.mark.asyncio
    async def test_invoke_convert_time(self, wrapper):
        """Test invoking timezone conversion."""
        result = await wrapper.invoke_method(
            "convert_timezone",
            time="2023-01-15T10:30:00Z",
            from_timezone="UTC",
            to_timezone="EST",
        )
        assert result == {"converted_time": "2023-01-15T05:30:00", "timezone": "EST"}
        wrapper.client.convert_time.assert_called_once_with(
            time="2023-01-15T10:30:00Z", from_timezone="UTC", to_timezone="EST"
        )

    @pytest.mark.asyncio
    async def test_invoke_flight_arrival_time(self, wrapper):
        """Test invoking flight arrival time calculation."""
        result = await wrapper.invoke_method(
            "calculate_arrival_time",
            departure_time="2023-01-15T18:00:00Z",
            flight_duration_minutes=165,
        )
        assert result == {"arrival_time": "2023-01-15T20:45:00Z"}
        wrapper.client.calculate_flight_arrival_time.assert_called_once_with(
            departure_time="2023-01-15T18:00:00Z", flight_duration_minutes=165
        )

    @pytest.mark.asyncio
    async def test_invoke_meeting_time_optimization(self, wrapper):
        """Test invoking meeting time optimization."""
        result = await wrapper.invoke_method(
            "suggest_meeting_time",
            participants=["user1", "user2"],
            duration_minutes=60,
            timezone_preferences={"user1": "EST", "user2": "PST"},
        )
        assert result == {"optimal_time": "2023-01-15T15:00:00Z"}
        wrapper.client.find_optimal_meeting_time.assert_called_once_with(
            participants=["user1", "user2"],
            duration_minutes=60,
            timezone_preferences={"user1": "EST", "user2": "PST"},
        )

    @pytest.mark.asyncio
    async def test_invoke_itinerary_processing(self, wrapper):
        """Test invoking itinerary timezone processing."""
        itinerary = [{"event": "Meeting", "time": "2023-01-15T15:00:00Z"}]
        result = await wrapper.invoke_method(
            "process_itinerary", itinerary=itinerary, user_timezone="EST"
        )
        assert result == {
            "processed_events": [{"event": "Meeting", "local_time": "10:00 AM"}]
        }
        wrapper.client.process_itinerary_timezones.assert_called_once_with(
            itinerary=itinerary, user_timezone="EST"
        )

    @pytest.mark.asyncio
    async def test_invoke_unknown_method(self, wrapper):
        """Test invoking unknown method raises error."""
        with pytest.raises(MCPInvocationError, match="Method unknown_method not found"):
            await wrapper.invoke_method("unknown_method")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, wrapper):
        """Test connection error handling."""
        wrapper.client.get_current_time.side_effect = ConnectionError("Network error")

        with pytest.raises(MCPClientError):
            await wrapper.invoke_method("now", timezone="UTC")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, wrapper):
        """Test timeout error handling."""
        wrapper.client.get_current_time.side_effect = TimeoutError("Request timed out")

        with pytest.raises(MCPTimeoutError):
            await wrapper.invoke_method("now", timezone="UTC")

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, wrapper):
        """Test generic error handling."""
        wrapper.client.get_current_time.side_effect = Exception("Something went wrong")

        with pytest.raises(TripSageMCPError):
            await wrapper.invoke_method("now", timezone="UTC")

    def test_context_manager(self, wrapper):
        """Test wrapper can be used as context manager."""
        with wrapper as w:
            assert w == wrapper

        # Verify no errors are raised
        assert True

    def test_repr(self, wrapper):
        """Test string representation."""
        assert repr(wrapper) == "<TimeMCPWrapper(mcp_name='time-test')>"
