"""
Unit tests for the Weather MCP implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from ..weather.api_client import (
    CurrentWeather,
    OpenWeatherMapClient,
    WeatherForecast,
    WeatherLocation,
)
from ..weather.client import WeatherMCPClient, WeatherService


class TestWeatherLocation:
    """Tests for the WeatherLocation model."""

    def test_with_city(self):
        """Test creating a location with city only."""
        location = WeatherLocation(city="London")
        assert location.city == "London"
        assert location.country is None
        assert location.lat is None
        assert location.lon is None

    def test_with_coordinates(self):
        """Test creating a location with coordinates."""
        location = WeatherLocation(lat=51.5074, lon=-0.1278)
        assert location.lat == 51.5074
        assert location.lon == -0.1278
        assert location.city is None
        assert location.country is None

    def test_with_city_and_country(self):
        """Test creating a location with city and country."""
        location = WeatherLocation(city="London", country="GB")
        assert location.city == "London"
        assert location.country == "GB"
        assert location.lat is None
        assert location.lon is None

    def test_with_all_fields(self):
        """Test creating a location with all fields."""
        location = WeatherLocation(
            city="London", country="GB", lat=51.5074, lon=-0.1278
        )
        assert location.city == "London"
        assert location.country == "GB"
        assert location.lat == 51.5074
        assert location.lon == -0.1278

    def test_validation_failure(self):
        """Test validation failure when neither city nor coordinates are provided."""
        with pytest.raises(ValidationError):
            WeatherLocation()

        with pytest.raises(ValidationError):
            WeatherLocation(country="GB")

        with pytest.raises(ValidationError):
            WeatherLocation(lat=51.5074)  # Missing lon


class TestOpenWeatherMapClient:
    """Tests for the OpenWeatherMapClient class."""

    @pytest.fixture
    def mock_owm_client(self):
        """Create a mock OpenWeatherMapClient for testing."""
        with patch(
            "src.mcp.weather.api_client.OpenWeatherMapClient._get_api_key",
            return_value="fake_api_key",
        ):
            client = OpenWeatherMapClient()
            client._make_request = AsyncMock()
            return client

    @pytest.mark.asyncio
    async def test_get_current_weather(self, mock_owm_client):
        """Test getting current weather."""
        # Mock the API response
        mock_owm_client._make_request.return_value = {
            "name": "London",
            "main": {
                "temp": 15.5,
                "feels_like": 14.2,
                "temp_min": 13.0,
                "temp_max": 17.0,
                "humidity": 75,
                "pressure": 1012,
            },
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "wind": {"speed": 4.1, "deg": 270},
            "clouds": {"all": 5},
            "coord": {"lat": 51.5074, "lon": -0.1278},
            "sys": {"country": "GB"},
            "dt": 1625140800,
            "timezone": 3600,
        }

        # Call the method
        location = WeatherLocation(city="London", country="GB")
        result = await mock_owm_client.get_current_weather(location)

        # Verify the API call
        mock_owm_client._make_request.assert_called_once_with(
            "weather", {"q": "London,GB"}
        )

        # Verify the result
        assert isinstance(result, CurrentWeather)
        assert result.temperature == 15.5
        assert result.feels_like == 14.2
        assert result.location["name"] == "London"
        assert result.location["country"] == "GB"
        assert result.weather.main == "Clear"
        assert result.weather.description == "clear sky"

    @pytest.mark.asyncio
    async def test_get_forecast(self, mock_owm_client):
        """Test getting weather forecast."""
        # Mock the API response with a minimal example
        mock_owm_client._make_request.return_value = {
            "city": {
                "name": "London",
                "country": "GB",
                "coord": {"lat": 51.5074, "lon": -0.1278},
                "timezone": 3600,
            },
            "list": [
                {
                    "dt": 1625140800,
                    "main": {
                        "temp": 15.5,
                        "feels_like": 14.2,
                        "temp_min": 13.0,
                        "temp_max": 17.0,
                        "humidity": 75,
                        "pressure": 1012,
                    },
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                    "wind": {"speed": 4.1, "deg": 270},
                    "clouds": {"all": 5},
                }
            ],
        }

        # Call the method
        location = WeatherLocation(lat=51.5074, lon=-0.1278)
        result = await mock_owm_client.get_forecast(location, days=1)

        # Verify the API call
        mock_owm_client._make_request.assert_called_once_with(
            "forecast", {"lat": 51.5074, "lon": -0.1278, "cnt": 8}
        )

        # Verify the result
        assert isinstance(result, WeatherForecast)
        assert result.location["name"] == "London"
        assert result.location["country"] == "GB"
        assert len(result.daily) == 1


class TestWeatherMCPClient:
    """Tests for the WeatherMCPClient class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock WeatherMCPClient for testing."""
        with patch("src.mcp.weather.client.BaseMCPClient.__init__", return_value=None):
            client = WeatherMCPClient(endpoint="http://localhost:8003")
            client.call_tool = AsyncMock()
            return client

    @pytest.mark.asyncio
    async def test_get_current_weather(self, mock_client):
        """Test getting current weather."""
        mock_response = {
            "temperature": 15.5,
            "feels_like": 14.2,
            "weather": {"main": "Clear", "description": "clear sky"},
            "location": {"name": "London", "country": "GB"},
        }
        mock_client.call_tool.return_value = mock_response

        result = await mock_client.get_current_weather(city="London", country="GB")

        mock_client.call_tool.assert_called_once_with(
            "get_current_weather", {"city": "London", "country": "GB"}, skip_cache=False
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_forecast(self, mock_client):
        """Test getting weather forecast."""
        mock_response = {
            "location": {"name": "London", "country": "GB"},
            "daily": [
                {
                    "date": "2025-05-10",
                    "temp_min": 13.0,
                    "temp_max": 17.0,
                    "temp_avg": 15.5,
                    "weather": {"main": "Clear", "description": "clear sky"},
                }
            ],
        }
        mock_client.call_tool.return_value = mock_response

        result = await mock_client.get_forecast(city="London", country="GB", days=1)

        mock_client.call_tool.assert_called_once_with(
            "get_forecast",
            {"location": {"city": "London", "country": "GB"}, "days": 1},
            skip_cache=False,
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_travel_recommendation(self, mock_client):
        """Test getting travel recommendations."""
        mock_response = {
            "current_weather": {"temperature": 15.5, "weather": {"main": "Clear"}},
            "forecast": {
                "daily": [
                    {
                        "date": "2025-05-10",
                        "temp_avg": 15.5,
                        "weather": {"main": "Clear"},
                    }
                ]
            },
            "recommendations": {
                "clothing": ["Pack a light jacket"],
                "activities": ["Good weather for outdoor activities"],
            },
        }
        mock_client.call_tool.return_value = mock_response

        result = await mock_client.get_travel_recommendation(
            city="London", country="GB", activities=["sightseeing"]
        )

        mock_client.call_tool.assert_called_once_with(
            "get_travel_recommendation",
            {
                "location": {"city": "London", "country": "GB"},
                "activities": ["sightseeing"],
            },
            skip_cache=False,
        )
        assert result == mock_response


class TestWeatherService:
    """Tests for the WeatherService class."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock WeatherService for testing."""
        mock_client = Mock()
        mock_client.get_current_weather = AsyncMock()
        mock_client.get_forecast = AsyncMock()
        mock_client.get_travel_recommendation = AsyncMock()
        return WeatherService(client=mock_client)

    @pytest.mark.asyncio
    async def test_get_destination_weather(self, mock_service):
        """Test getting weather for a destination."""
        mock_response = {
            "temperature": 15.5,
            "feels_like": 14.2,
            "weather": {"main": "Clear", "description": "clear sky"},
            "location": {"name": "London", "country": "GB"},
        }
        mock_service.client.get_current_weather.return_value = mock_response

        result = await mock_service.get_destination_weather("London, GB")

        mock_service.client.get_current_weather.assert_called_once_with(
            city="London", country="GB"
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_get_trip_weather_summary(self, mock_service):
        """Test getting weather summary for a trip."""
        # Mock the forecast response
        mock_service.client.get_forecast.return_value = {
            "location": {"name": "London", "country": "GB"},
            "daily": [
                {
                    "date": "2025-07-01",
                    "temp_min": 13.0,
                    "temp_max": 17.0,
                    "temp_avg": 15.5,
                    "humidity_avg": 75.0,
                    "weather": {
                        "main": "Clear",
                        "description": "clear sky",
                        "id": 800,
                        "icon": "01d",
                    },
                    "intervals": [],
                },
                {
                    "date": "2025-07-02",
                    "temp_min": 14.0,
                    "temp_max": 18.0,
                    "temp_avg": 16.0,
                    "humidity_avg": 70.0,
                    "weather": {
                        "main": "Clear",
                        "description": "clear sky",
                        "id": 800,
                        "icon": "01d",
                    },
                    "intervals": [],
                },
            ],
        }

        result = await mock_service.get_trip_weather_summary(
            destination="London, GB", start_date="2025-07-01", end_date="2025-07-02"
        )

        mock_service.client.get_forecast.assert_called_once_with(
            city="London", country="GB", days=16
        )

        # Check the result
        assert result.destination == "London, GB"
        assert result.start_date == "2025-07-01"
        assert result.end_date == "2025-07-02"
        assert result.temperature["average"] == 15.75  # Average of 15.5 and 16.0
        assert result.temperature["min"] == 13.0
        assert result.temperature["max"] == 18.0
        assert result.conditions["most_common"] == "Clear"
        assert len(result.days) == 2

    @pytest.mark.asyncio
    async def test_compare_destinations_weather(self, mock_service):
        """Test comparing weather across destinations."""
        # Mock the current weather responses
        mock_service.client.get_current_weather.side_effect = [
            {
                "temperature": 25.0,
                "feels_like": 24.0,
                "weather": {"main": "Clear", "description": "clear sky"},
            },
            {
                "temperature": 30.0,
                "feels_like": 32.0,
                "weather": {"main": "Clear", "description": "clear sky"},
            },
        ]

        result = await mock_service.compare_destinations_weather(
            destinations=["Miami, US", "Cancun, MX"]
        )

        # Check that the service made the expected calls
        assert mock_service.client.get_current_weather.call_count == 2

        # Check the result structure
        assert result.destinations == ["Miami, US", "Cancun, MX"]
        assert result.date == "current"
        assert len(result.results) == 2
        assert result.ranking == [
            "Cancun, MX",
            "Miami, US",
        ]  # Sorted by temperature (higher first)

    @pytest.mark.asyncio
    async def test_get_optimal_travel_time(self, mock_service):
        """Test getting optimal travel time recommendations."""
        # Mock the travel recommendation response
        mock_service.client.get_travel_recommendation.return_value = {
            "current_weather": {
                "temperature": 0.0,
                "weather": {"main": "Snow", "description": "light snow"},
            },
            "recommendations": {
                "clothing": ["Pack heavy winter clothing"],
                "activities": ["Perfect weather for skiing activities"],
                "forecast_based": ["Good outdoor weather on 2025-05-15"],
            },
        }

        result = await mock_service.get_optimal_travel_time(
            destination="Aspen, US", activity_type="skiing"
        )

        mock_service.client.get_travel_recommendation.assert_called_once_with(
            city="Aspen", country="US", activities=["skiing"]
        )

        # Check the result
        assert result.destination == "Aspen, US"
        assert result.activity_type == "skiing"
        assert result.current_weather == "Snow"
        assert result.activity_recommendation == "Perfect weather for skiing activities"
        assert len(result.clothing_recommendations) == 1
        assert result.clothing_recommendations[0] == "Pack heavy winter clothing"
