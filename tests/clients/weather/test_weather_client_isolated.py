"""
Isolated tests for the Weather MCP client.

This module provides isolated tests that don't trigger full app settings loading.
"""

from typing import Any, Dict
from unittest import mock

import pytest


@pytest.fixture
def example_weather_response() -> Dict[str, Any]:
    """Return an example weather response."""
    return {
        "temperature": 18.5,
        "feels_like": 17.2,
        "temp_min": 16.0,
        "temp_max": 20.5,
        "humidity": 70,
        "pressure": 1012,
        "wind_speed": 4.5,
        "wind_direction": 180.0,
        "clouds": 40,
        "weather": {
            "id": 802,
            "main": "Clouds",
            "description": "scattered clouds",
            "icon": "03d",
        },
        "location": {
            "name": "London",
            "country": "GB",
            "lon": -0.1257,
            "lat": 51.5085,
        },
        "timestamp": 1683000000,
        "source": "OpenWeather API",
    }


@pytest.mark.asyncio
async def test_weather_client_creation():
    """Test the WeatherMCPClient can be created with mocked dependencies."""
    # Mock all the dependencies
    with mock.patch.dict(
        "sys.modules",
        {
            "tripsage.config.app_settings": mock.MagicMock(),
            "tripsage.utils.cache": mock.MagicMock(),
            "tripsage.utils.client_utils": mock.MagicMock(),
            "tripsage.utils.error_handling": mock.MagicMock(),
            "tripsage.utils.logging": mock.MagicMock(),
        },
    ):
        # Create mock settings
        from tripsage.config.app_settings import settings

        settings.weather_mcp = mock.MagicMock()
        settings.weather_mcp.endpoint = "http://test-endpoint.com"
        settings.weather_mcp.api_key = mock.MagicMock()
        settings.weather_mcp.api_key.get_secret_value.return_value = "test-api-key"
        settings.weather_mcp.openweathermap_api_key = mock.MagicMock()
        settings.weather_mcp.openweathermap_api_key.get_secret_value.return_value = (
            "test-openweathermap-api-key"
        )

        # Create mock cache
        from tripsage.utils.cache import web_cache

        web_cache.get = mock.AsyncMock(return_value=None)
        web_cache.set = mock.AsyncMock()
        web_cache.generate_cache_key = mock.MagicMock(return_value="test-cache-key")

        # Create mock error handling
        from tripsage.utils.error_handling import with_error_handling

        # Pass-through decorator function instead of lambda
        def with_error_handling(f):  # noqa: F811
            return f

        # Now import and test the client
        from tripsage.clients.weather import WeatherMCPClient

        # Create a client instance
        client = WeatherMCPClient(
            endpoint="http://test-endpoint.com",
            api_key="test-api-key",
            openweathermap_api_key="test-openweathermap-api-key",
        )

        # Verify the instance was created
        assert client.endpoint == "http://test-endpoint.com"
        assert client.api_key == "test-api-key"
        assert client.openweathermap_api_key == "test-openweathermap-api-key"


@pytest.mark.asyncio
async def test_weather_client_singleton():
    """Test the singleton pattern works correctly."""
    # Mock all the dependencies
    with mock.patch.dict(
        "sys.modules",
        {
            "tripsage.config.app_settings": mock.MagicMock(),
            "tripsage.utils.cache": mock.MagicMock(),
            "tripsage.utils.client_utils": mock.MagicMock(),
            "tripsage.utils.error_handling": mock.MagicMock(),
            "tripsage.utils.logging": mock.MagicMock(),
        },
    ):
        from tripsage.clients.weather import WeatherMCPClient

        # Reset the singleton state
        WeatherMCPClient._instance = None
        WeatherMCPClient._initialized = False

        # Create the first instance
        client1 = WeatherMCPClient(
            endpoint="http://test-endpoint1.com",
            api_key="test-api-key-1",
        )

        # Create the second instance
        client2 = WeatherMCPClient(
            endpoint="http://test-endpoint2.com",
            api_key="test-api-key-2",
        )

        # Verify they are the same instance
        assert client1 is client2
        # Verify the first set of parameters is retained
        assert client1.endpoint == "http://test-endpoint1.com"
