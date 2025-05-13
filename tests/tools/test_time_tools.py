"""
Tests for the time tools module.
"""

from unittest.mock import AsyncMock, patch

import pytest

from tripsage.tools.time import convert_time_tool, get_current_time_tool


@pytest.mark.asyncio
async def test_get_current_time_tool():
    """Test the get_current_time_tool function."""
    # Mock the time client
    mock_client = AsyncMock()
    mock_client.get_current_time.return_value = {
        "current_time": "2023-06-15T12:30:00Z",
        "formatted_time": "12:30 PM",
    }

    # Patch the get_time_client function to return our mock
    with patch("tripsage.tools.time.get_time_client", return_value=mock_client):
        # Call the tool
        result = await get_current_time_tool("America/New_York")

        # Check the result
        assert result["current_time"] == "2023-06-15T12:30:00Z"
        assert result["formatted_time"] == "12:30 PM"
        assert result["timezone"] == "America/New_York"

        # Verify that the client was called with the correct parameters
        mock_client.get_current_time.assert_called_once_with("America/New_York")


@pytest.mark.asyncio
async def test_convert_time_tool():
    """Test the convert_time_tool function."""
    # Mock the time client
    mock_client = AsyncMock()
    mock_client.convert_time.return_value = {
        "converted_time": "17:30:00",
    }

    # Patch the get_time_client function to return our mock
    with patch("tripsage.tools.time.get_time_client", return_value=mock_client):
        # Call the tool
        result = await convert_time_tool(
            time_str="12:30",
            from_timezone="America/New_York",
            to_timezone="Europe/London",
            format_24h=True,
        )

        # Check the result
        assert result["converted_time"] == "17:30:00"
        assert result["from_timezone"] == "America/New_York"
        assert result["to_timezone"] == "Europe/London"

        # Verify that the client was called with the correct parameters
        mock_client.convert_time.assert_called_once_with(
            time_str="12:30",
            from_timezone="America/New_York",
            to_timezone="Europe/London",
            format_24h=True,
        )
