"""
Tests for the Weather MCP client.

This module provides tests for the WeatherMCPClient class, which
is responsible for communicating with the Weather MCP server.
"""

import os
from typing import Any, Dict
from unittest import mock

import httpx
import pytest

# Set environment variables for testing before any imports
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test-password"
os.environ["SUPABASE_URL"] = "https://test-supabase-url.com"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["OPENAI_API_KEY"] = "test-openai-key"

# Set weather MCP specific environment variables
os.environ["WEATHER_MCP_ENDPOINT"] = "http://test-weather-endpoint.com"
os.environ["WEATHER_MCP_API_KEY"] = "test-weather-api-key"
os.environ["OPENWEATHERMAP_API_KEY"] = "test-openweathermap-api-key"

# Now we can safely import the client
from tripsage.clients.weather import WeatherMCPClient
from tripsage.tools.schemas.weather import (
    CurrentWeather,
    WeatherForecast,
    WeatherRecommendation,
)
from tripsage.utils.cache import WebOperationsCache
from tripsage.utils.error_handling import MCPError


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


@pytest.fixture
def example_forecast_response() -> Dict[str, Any]:
    """Return an example forecast response."""
    return {
        "location": {
            "name": "London",
            "country": "GB",
            "lon": -0.1257,
            "lat": 51.5085,
        },
        "daily": [
            {
                "date": "2023-05-01",
                "temp_min": 14.0,
                "temp_max": 21.0,
                "temp_avg": 17.5,
                "humidity_avg": 70.0,
                "weather": {
                    "id": 800,
                    "main": "Clear",
                    "description": "clear sky",
                    "icon": "01d",
                },
                "intervals": [],
            },
            {
                "date": "2023-05-02",
                "temp_min": 15.0,
                "temp_max": 22.0,
                "temp_avg": 18.5,
                "humidity_avg": 65.0,
                "weather": {
                    "id": 801,
                    "main": "Clouds",
                    "description": "few clouds",
                    "icon": "02d",
                },
                "intervals": [],
            },
        ],
        "source": "OpenWeather API",
    }


@pytest.fixture
def example_recommendation_response() -> Dict[str, Any]:
    """Return an example recommendation response."""
    return {
        "current_weather": {
            "temperature": 18.5,
            "weather": {
                "main": "Clouds",
                "description": "scattered clouds",
            },
        },
        "forecast": {
            "daily": [
                {
                    "date": "2023-05-01",
                    "temp_min": 14.0,
                    "temp_max": 21.0,
                    "weather": {
                        "main": "Clear",
                        "description": "clear sky",
                    },
                }
            ]
        },
        "recommendations": {
            "summary": "Good weather for outdoor activities",
            "clothing": ["Light jacket", "Sunglasses"],
            "activities": ["Great for sightseeing", "Good for hiking"],
            "forecast_based": ["Good weather on Monday", "Rain expected on Tuesday"],
        },
    }


# Mock weather MCP config settings
@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with mock.patch("tripsage.config.app_settings.settings") as mock_settings:
        # Create a weather MCP config
        mock_weather_config = mock.MagicMock()
        mock_weather_config.endpoint = "http://test-endpoint.com"
        mock_weather_config.api_key = mock.MagicMock()
        mock_weather_config.api_key.get_secret_value.return_value = "test-api-key"
        mock_weather_config.openweathermap_api_key = mock.MagicMock()
        get_val = mock_weather_config.openweathermap_api_key.get_secret_value
        get_val.return_value = "test-openweathermap-api-key"

        # Assign to settings
        mock_settings.weather_mcp = mock_weather_config
        yield mock_settings


# Mock the web cache dependency
@pytest.fixture
def mock_web_cache():
    """Create a mocked web cache."""
    mock_cache = mock.MagicMock(spec=WebOperationsCache)
    mock_cache.get = mock.AsyncMock(return_value=None)
    mock_cache.set = mock.AsyncMock()
    mock_cache.generate_cache_key = mock.MagicMock(return_value="test-cache-key")
    yield mock_cache


@pytest.fixture
async def mock_client(mock_settings, mock_web_cache):
    """Create a mocked client for testing."""
    # Mock the httpx client
    mock_httpx_client = mock.MagicMock(spec=httpx.AsyncClient)
    mock_httpx_client.is_closed = False

    # Create client
    with mock.patch("httpx.AsyncClient", return_value=mock_httpx_client):
        with mock.patch("tripsage.utils.cache.web_cache", mock_web_cache):
            # Reset the singleton for this test
            WeatherMCPClient._instance = None
            WeatherMCPClient._initialized = False

            # Create a client instance
            client = WeatherMCPClient(
                endpoint="http://test-endpoint.com",
                api_key="test-api-key",
                openweathermap_api_key="test-openweathermap-api-key",
            )

            # Replace the web_cache
            client.web_cache = mock_web_cache
            client.client = mock_httpx_client

            yield client

            # Cleanup
            client.client = None


@pytest.mark.asyncio
async def test_get_current_weather(
    mock_client: WeatherMCPClient, example_weather_response: Dict[str, Any]
):
    """Test the get_current_weather method."""
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        return_value=CurrentWeather.model_validate(example_weather_response),
    ) as mock_call_mcp:
        result = await mock_client.get_current_weather(city="London", country="GB")

        # Verify the request
        mock_call_mcp.assert_called_once()
        call_args = mock_call_mcp.call_args[1]
        assert call_args["endpoint"] == "http://test-endpoint.com"
        assert call_args["tool_name"] == "get_current_weather"
        assert call_args["params"]["city"] == "London"
        assert call_args["params"]["country"] == "GB"
        assert (
            call_args["params"]["openweathermap_api_key"]
            == "test-openweathermap-api-key"
        )

        # Verify the result
        assert isinstance(result, CurrentWeather)
        assert result.temperature == 18.5
        assert result.weather.main == "Clouds"
        assert result.weather.description == "scattered clouds"
        assert result.location["name"] == "London"
        assert result.location["country"] == "GB"
        assert result.source == "OpenWeather API"


@pytest.mark.asyncio
async def test_get_current_weather_with_coordinates(
    mock_client: WeatherMCPClient, example_weather_response: Dict[str, Any]
):
    """Test the get_current_weather method with coordinates."""
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        return_value=CurrentWeather.model_validate(example_weather_response),
    ) as mock_call_mcp:
        result = await mock_client.get_current_weather(lat=51.5085, lon=-0.1257)

        # Verify the request
        mock_call_mcp.assert_called_once()
        call_args = mock_call_mcp.call_args[1]
        assert call_args["endpoint"] == "http://test-endpoint.com"
        assert call_args["tool_name"] == "get_current_weather"
        assert call_args["params"]["lat"] == 51.5085
        assert call_args["params"]["lon"] == -0.1257

        # Verify the result
        assert isinstance(result, CurrentWeather)
        assert result.temperature == 18.5


@pytest.mark.asyncio
async def test_get_current_weather_missing_location(mock_client: WeatherMCPClient):
    """Test the get_current_weather method with missing location."""
    with pytest.raises(MCPError) as exc_info:
        await mock_client.get_current_weather()

    assert "Either city or coordinates (lat, lon) must be provided" in str(
        exc_info.value
    )


@pytest.mark.asyncio
async def test_get_forecast(
    mock_client: WeatherMCPClient, example_forecast_response: Dict[str, Any]
):
    """Test the get_forecast method."""
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        return_value=WeatherForecast.model_validate(example_forecast_response),
    ) as mock_call_mcp:
        result = await mock_client.get_forecast(city="London", country="GB", days=7)

        # Verify the request
        mock_call_mcp.assert_called_once()
        call_args = mock_call_mcp.call_args[1]
        assert call_args["endpoint"] == "http://test-endpoint.com"
        assert call_args["tool_name"] == "get_forecast"
        assert call_args["params"]["city"] == "London"
        assert call_args["params"]["country"] == "GB"
        assert call_args["params"]["days"] == 7

        # Verify the result
        assert isinstance(result, WeatherForecast)
        assert len(result.daily) == 2
        assert result.daily[0].date == "2023-05-01"
        assert result.daily[0].temp_min == 14.0
        assert result.daily[0].temp_max == 21.0
        assert result.daily[0].weather.main == "Clear"
        assert result.location["name"] == "London"
        assert result.location["country"] == "GB"
        assert result.source == "OpenWeather API"


@pytest.mark.asyncio
async def test_get_forecast_days_validation(
    mock_client: WeatherMCPClient, example_forecast_response: Dict[str, Any]
):
    """Test the get_forecast method with days validation."""
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        return_value=WeatherForecast.model_validate(example_forecast_response),
    ) as mock_call_mcp:
        # Test with days too low (should be set to 1)
        await mock_client.get_forecast(city="London", country="GB", days=-5)
        assert mock_call_mcp.call_args[1]["params"]["days"] == 1

        # Test with days too high (should be set to 16)
        await mock_client.get_forecast(city="London", country="GB", days=30)
        assert mock_call_mcp.call_args[1]["params"]["days"] == 16


@pytest.mark.asyncio
async def test_get_travel_recommendation(
    mock_client: WeatherMCPClient, example_recommendation_response: Dict[str, Any]
):
    """Test the get_travel_recommendation method."""
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        return_value=WeatherRecommendation.model_validate(
            example_recommendation_response
        ),
    ) as mock_call_mcp:
        result = await mock_client.get_travel_recommendation(
            city="London",
            country="GB",
            start_date="2023-05-01",
            end_date="2023-05-07",
            activities=["hiking", "sightseeing"],
        )

        # Verify the request
        mock_call_mcp.assert_called_once()
        call_args = mock_call_mcp.call_args[1]
        assert call_args["endpoint"] == "http://test-endpoint.com"
        assert call_args["tool_name"] == "get_travel_recommendation"
        assert call_args["params"]["city"] == "London"
        assert call_args["params"]["country"] == "GB"
        assert call_args["params"]["start_date"] == "2023-05-01"
        assert call_args["params"]["end_date"] == "2023-05-07"
        assert call_args["params"]["activities"] == ["hiking", "sightseeing"]

        # Verify the result
        assert isinstance(result, WeatherRecommendation)
        assert result.current_weather["temperature"] == 18.5
        assert result.current_weather["weather"]["main"] == "Clouds"
        assert "Light jacket" in result.recommendations["clothing"]
        assert "Great for sightseeing" in result.recommendations["activities"]
        assert "Good weather on Monday" in result.recommendations["forecast_based"]


@pytest.mark.asyncio
async def test_singleton_pattern(mock_web_cache):
    """Test the singleton pattern of the client."""
    # Reset the singleton instance for this test
    WeatherMCPClient._instance = None
    WeatherMCPClient._initialized = False

    # Mock settings
    with mock.patch("tripsage.config.app_settings.settings") as mock_settings:
        mock_settings.weather_mcp.endpoint = "http://test-endpoint.com"
        mock_settings.weather_mcp.api_key = mock.MagicMock()
        mock_settings.weather_mcp.api_key.get_secret_value.return_value = "test-api-key"
        mock_settings.weather_mcp.openweathermap_api_key = mock.MagicMock()
        get_val = mock_settings.weather_mcp.openweathermap_api_key.get_secret_value
        get_val.return_value = "test-openweathermap-api-key"

        # Mock web cache
        with mock.patch("tripsage.utils.cache.web_cache", mock_web_cache):
            # Create the first instance
            client1 = await WeatherMCPClient.get_instance(
                endpoint="http://test-endpoint.com",
                api_key="test-api-key",
            )

            # Create the second instance with different parameters
            client2 = await WeatherMCPClient.get_instance(
                endpoint="http://another-endpoint.com",
                api_key="another-api-key",
            )

            # Verify that both instances are the same object
            assert client1 is client2
            # Verify that the parameters of the first initialization are used
            assert client1.endpoint == "http://test-endpoint.com"
            assert client1.api_key == "test-api-key"

            # Clean up
            await client1.disconnect()


@pytest.mark.asyncio
async def test_caching(
    mock_client: WeatherMCPClient, example_weather_response: Dict[str, Any]
):
    """Test that the client uses caching properly."""
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        return_value=CurrentWeather.model_validate(example_weather_response),
    ):
        # First call should check cache and miss
        await mock_client.get_current_weather(city="London")
        mock_client.web_cache.get.assert_called_once()
        mock_client.web_cache.set.assert_called_once()

        # Reset mocks
        mock_client.web_cache.get.reset_mock()
        mock_client.web_cache.set.reset_mock()

        # Simulate cache hit
        mock_client.web_cache.get.return_value = example_weather_response

        # Second call should check cache and hit
        await mock_client.get_current_weather(city="London")
        mock_client.web_cache.get.assert_called_once()
        mock_client.web_cache.set.assert_not_called()

        # Reset mocks
        mock_client.web_cache.get.reset_mock()

        # Test skip_cache
        await mock_client.get_current_weather(city="London", skip_cache=True)
        mock_client.web_cache.get.assert_not_called()


@pytest.mark.asyncio
async def test_error_handling(mock_client: WeatherMCPClient):
    """Test that errors are handled properly."""
    # Test network error
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        side_effect=httpx.ConnectError("Connection error"),
    ):
        with pytest.raises(Exception) as exc_info:
            await mock_client.get_current_weather(city="London")
        assert "Connection error" in str(exc_info.value)

    # Test validation error
    with mock.patch(
        "tripsage.utils.client_utils.validate_and_call_mcp_tool",
        side_effect=ValueError("Validation error"),
    ):
        with pytest.raises(Exception) as exc_info:
            await mock_client.get_current_weather(city="London")
        assert "Validation error" in str(exc_info.value)
