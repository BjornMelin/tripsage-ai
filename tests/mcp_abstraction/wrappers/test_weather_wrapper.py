"""Tests for WeatherMCPWrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import (
    MCPConnectionError,
    MCPError,
    MCPInvocationError,
    MCPTimeoutError,
)
from tripsage.mcp_abstraction.wrappers.weather_wrapper import WeatherMCPWrapper


class TestWeatherMCPWrapper:
    """Test cases for WeatherMCPWrapper."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock WeatherMCPClient."""
        client = MagicMock()
        client.get_current_weather = AsyncMock(
            return_value={"temp": 72, "conditions": "Sunny"}
        )
        client.get_forecast = AsyncMock(return_value={"forecast": "Partly cloudy"})
        return client

    @pytest.fixture
    def wrapper(self, mock_client):
        """Create a WeatherMCPWrapper with mocked client."""
        return WeatherMCPWrapper(client=mock_client, mcp_name="weather-test")

    def test_initialization_with_client(self, mock_client):
        """Test wrapper initialization with provided client."""
        wrapper = WeatherMCPWrapper(client=mock_client, mcp_name="weather-test")
        assert wrapper.client == mock_client
        assert wrapper.mcp_name == "weather-test"

    @patch("tripsage.mcp_abstraction.wrappers.weather_wrapper.WeatherMCPClient")
    @patch("tripsage.mcp_abstraction.wrappers.weather_wrapper.mcp_settings")
    def test_initialization_without_client(self, mock_settings, MockWeatherClient):
        """Test wrapper initialization without provided client."""
        # Setup mock settings
        mock_settings.weather.url = "https://weather.example.com"
        mock_settings.weather.api_key.get_secret_value.return_value = "test-key"

        # Setup mock client class
        mock_client_instance = MagicMock()
        MockWeatherClient.return_value = mock_client_instance

        # Create wrapper
        wrapper = WeatherMCPWrapper()

        # Verify client creation
        MockWeatherClient.assert_called_once_with(
            endpoint="https://weather.example.com", api_key="test-key"
        )
        assert wrapper.client == mock_client_instance
        assert wrapper.mcp_name == "weather"

    def test_method_map(self, wrapper):
        """Test method mapping is correctly built."""
        expected_map = {
            "get_current_weather": "get_current_weather",
            "get_forecast": "get_forecast",
        }
        assert wrapper._method_map == expected_map

    def test_get_available_methods(self, wrapper):
        """Test getting available methods."""
        methods = wrapper.get_available_methods()
        assert set(methods) == {"get_current_weather", "get_forecast"}

    @pytest.mark.asyncio
    async def test_invoke_current_weather(self, wrapper):
        """Test invoking get_current_weather method."""
        result = await wrapper.invoke_method(
            "get_current_weather", location="New York, NY"
        )
        assert result == {"temp": 72, "conditions": "Sunny"}
        wrapper.client.get_current_weather.assert_called_once_with(
            location="New York, NY"
        )

    @pytest.mark.asyncio
    async def test_invoke_forecast(self, wrapper):
        """Test invoking get_forecast method."""
        result = await wrapper.invoke_method(
            "get_forecast", location="San Francisco, CA", days=5
        )
        assert result == {"forecast": "Partly cloudy"}
        wrapper.client.get_forecast.assert_called_once_with(
            location="San Francisco, CA", days=5
        )

    @pytest.mark.asyncio
    async def test_invoke_unknown_method(self, wrapper):
        """Test invoking unknown method raises error."""
        with pytest.raises(MCPInvocationError, match="Method unknown_method not found"):
            await wrapper.invoke_method("unknown_method")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, wrapper):
        """Test connection error handling."""
        wrapper.client.get_current_weather.side_effect = ConnectionError(
            "Network error"
        )

        with pytest.raises(MCPConnectionError):
            await wrapper.invoke_method("get_current_weather", location="Chicago")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, wrapper):
        """Test timeout error handling."""
        wrapper.client.get_current_weather.side_effect = TimeoutError(
            "Request timed out"
        )

        with pytest.raises(MCPTimeoutError):
            await wrapper.invoke_method("get_current_weather", location="Chicago")

    @pytest.mark.asyncio
    async def test_generic_error_handling(self, wrapper):
        """Test generic error handling."""
        wrapper.client.get_current_weather.side_effect = Exception(
            "Something went wrong"
        )

        with pytest.raises(MCPError):
            await wrapper.invoke_method("get_current_weather", location="Chicago")

    def test_context_manager(self, wrapper):
        """Test wrapper can be used as context manager."""
        with wrapper as w:
            assert w == wrapper

        # Verify no errors are raised
        assert True

    def test_repr(self, wrapper):
        """Test string representation."""
        assert repr(wrapper) == "<WeatherMCPWrapper(mcp_name='weather-test')>"
