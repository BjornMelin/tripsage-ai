"""
Tests for the Weather MCP client.

This module contains tests for the Weather MCP client implementation
that interfaces with the Weather MCP server.
"""

from unittest.mock import patch

import pytest

from tripsage.mcp.weather.client import WeatherMCPClient, WeatherService
from tripsage.mcp.weather.models import (
    CurrentWeatherResponse,
    DestinationWeatherComparison,
    ForecastResponse,
    OptimalTravelTime,
    RecommendationResponse,
    TravelWeatherSummary,
)
from tripsage.utils.error_handling import MCPError


@pytest.fixture
def client():
    """Create a test client instance."""
    return WeatherMCPClient(
        endpoint="http://test-endpoint",
        use_cache=False,
    )


@pytest.fixture
def mock_current_weather_response():
    """Create a mock response for get_current_weather."""
    return {
        "temperature": 22.5,
        "feels_like": 24.2,
        "temp_min": 20.1,
        "temp_max": 25.3,
        "pressure": 1012,
        "humidity": 65,
        "wind_speed": 4.2,
        "wind_direction": 180,
        "clouds": 40,
        "weather": {
            "id": 801,
            "main": "Clouds",
            "description": "few clouds",
            "icon": "02d",
        },
        "location": {"city": "Paris", "country": "FR", "lat": 48.8566, "lon": 2.3522},
        "timestamp": 1683889200,
    }


@pytest.fixture
def mock_forecast_response():
    """Create a mock response for get_forecast."""
    return {
        "location": {"city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278},
        "current": {
            "temperature": 18.3,
            "feels_like": 19.1,
            "temp_min": 16.2,
            "temp_max": 21.5,
            "pressure": 1010,
            "humidity": 75,
            "wind_speed": 5.1,
            "wind_direction": 220,
            "clouds": 60,
            "weather": {
                "id": 500,
                "main": "Rain",
                "description": "light rain",
                "icon": "10d",
            },
            "location": {
                "city": "London",
                "country": "GB",
                "lat": 51.5074,
                "lon": -0.1278,
            },
            "timestamp": 1683889200,
        },
        "daily": [
            {
                "date": "2025-05-12",
                "temp_min": 15.8,
                "temp_max": 21.5,
                "temp_avg": 18.7,
                "feels_like": {"day": 19.2, "night": 16.1, "eve": 18.4, "morn": 16.5},
                "pressure": 1010,
                "humidity": 75,
                "wind_speed": 5.1,
                "wind_direction": 220,
                "clouds": 60,
                "probability": 0.7,
                "weather": {
                    "id": 500,
                    "main": "Rain",
                    "description": "light rain",
                    "icon": "10d",
                },
            },
            {
                "date": "2025-05-13",
                "temp_min": 14.2,
                "temp_max": 19.8,
                "temp_avg": 17.0,
                "feels_like": {"day": 17.5, "night": 14.8, "eve": 16.2, "morn": 15.1},
                "pressure": 1012,
                "humidity": 70,
                "wind_speed": 4.2,
                "wind_direction": 200,
                "clouds": 30,
                "probability": 0.4,
                "weather": {
                    "id": 802,
                    "main": "Clouds",
                    "description": "scattered clouds",
                    "icon": "03d",
                },
            },
            {
                "date": "2025-05-14",
                "temp_min": 16.1,
                "temp_max": 22.3,
                "temp_avg": 19.2,
                "feels_like": {"day": 20.1, "night": 17.2, "eve": 19.5, "morn": 16.8},
                "pressure": 1015,
                "humidity": 65,
                "wind_speed": 3.8,
                "wind_direction": 190,
                "clouds": 20,
                "probability": 0.2,
                "weather": {
                    "id": 800,
                    "main": "Clear",
                    "description": "clear sky",
                    "icon": "01d",
                },
            },
        ],
    }


@pytest.fixture
def mock_travel_recommendation_response():
    """Create a mock response for get_travel_recommendation."""
    return {
        "location": {
            "city": "Barcelona",
            "country": "ES",
            "lat": 41.3851,
            "lon": 2.1734,
        },
        "current_weather": {
            "temperature": 26.8,
            "feels_like": 28.3,
            "temp_min": 24.5,
            "temp_max": 28.9,
            "pressure": 1014,
            "humidity": 55,
            "wind_speed": 3.2,
            "wind_direction": 140,
            "clouds": 10,
            "weather": {
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d",
            },
            "location": {
                "city": "Barcelona",
                "country": "ES",
                "lat": 41.3851,
                "lon": 2.1734,
            },
            "timestamp": 1683889200,
        },
        "recommendations": {
            "clothing": [
                "Light clothing suitable for warm weather",
                "Sun hat and sunglasses",
                "Comfortable walking shoes for sightseeing",
                "Swimwear for beach activities",
            ],
            "activities": [
                "Beach conditions are excellent for swimming and sunbathing",
                "Great weather for outdoor sightseeing of Barcelona's attractions",
                "Consider visiting Sagrada Familia and Park Güell in the morning "
                "to avoid afternoon heat",
            ],
            "forecast_based": [
                "Good weather expected for the next 5 days",
                "Best beach days will be Wednesday and Thursday",
                "Chance of light rain on Friday afternoon, plan indoor activities",
            ],
        },
    }


class TestWeatherMCPClient:
    """Tests for the WeatherMCPClient class."""

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_current_weather(
        self, mock_call_tool, client, mock_current_weather_response
    ):
        """Test getting current weather for a location."""
        mock_call_tool.return_value = mock_current_weather_response

        result = await client.get_current_weather(city="Paris", country="FR")

        mock_call_tool.assert_called_once_with(
            "get_current_weather", {"city": "Paris", "country": "FR"}, False
        )

        assert isinstance(result, CurrentWeatherResponse)
        assert result.temperature == 22.5
        assert result.feels_like == 24.2
        assert result.weather.main == "Clouds"
        assert result.location["city"] == "Paris"

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_current_weather_with_coordinates(
        self, mock_call_tool, client, mock_current_weather_response
    ):
        """Test getting current weather using coordinates."""
        mock_call_tool.return_value = mock_current_weather_response

        result = await client.get_current_weather(lat=48.8566, lon=2.3522)

        mock_call_tool.assert_called_once_with(
            "get_current_weather", {"lat": 48.8566, "lon": 2.3522}, False
        )

        assert isinstance(result, CurrentWeatherResponse)
        assert result.temperature == 22.5
        assert result.location["lat"] == 48.8566

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_current_weather_error(self, mock_call_tool, client):
        """Test error handling for get_current_weather."""
        mock_call_tool.side_effect = Exception("API error")

        with pytest.raises(MCPError):
            await client.get_current_weather(city="InvalidCity")

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_forecast(self, mock_call_tool, client, mock_forecast_response):
        """Test getting weather forecast for a location."""
        mock_call_tool.return_value = mock_forecast_response

        result = await client.get_forecast(city="London", country="GB", days=3)

        mock_call_tool.assert_called_once_with(
            "get_forecast",
            {"location": {"city": "London", "country": "GB"}, "days": 3},
            False,
        )

        assert isinstance(result, ForecastResponse)
        assert result.location["city"] == "London"
        assert len(result.daily) == 3
        assert result.daily[0].date == "2025-05-12"
        assert result.daily[0].weather.main == "Rain"
        assert result.daily[2].weather.main == "Clear"

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_forecast_validates_days(
        self, mock_call_tool, client, mock_forecast_response
    ):
        """Test days parameter is constrained to valid range."""
        mock_call_tool.return_value = mock_forecast_response

        # Test with days too low
        await client.get_forecast(city="London", days=0)
        assert mock_call_tool.call_args[0][1]["days"] == 1

        # Reset mock
        mock_call_tool.reset_mock()

        # Test with days too high
        await client.get_forecast(city="London", days=20)
        assert mock_call_tool.call_args[0][1]["days"] == 16

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_forecast_error(self, mock_call_tool, client):
        """Test error handling for get_forecast."""
        mock_call_tool.side_effect = Exception("API error")

        with pytest.raises(MCPError):
            await client.get_forecast(city="InvalidCity")

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_travel_recommendation(
        self, mock_call_tool, client, mock_travel_recommendation_response
    ):
        """Test getting travel recommendations for a location."""
        mock_call_tool.return_value = mock_travel_recommendation_response

        activities = ["beach", "sightseeing"]
        result = await client.get_travel_recommendation(
            city="Barcelona", country="ES", activities=activities
        )

        mock_call_tool.assert_called_once_with(
            "get_travel_recommendation",
            {
                "location": {"city": "Barcelona", "country": "ES"},
                "activities": activities,
            },
            False,
        )

        assert isinstance(result, RecommendationResponse)
        assert result.location["city"] == "Barcelona"
        assert result.current_weather.temperature == 26.8
        assert len(result.recommendations["clothing"]) == 4
        assert len(result.recommendations["activities"]) == 3
        assert len(result.recommendations["forecast_based"]) == 3

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_travel_recommendation_with_dates(
        self, mock_call_tool, client, mock_travel_recommendation_response
    ):
        """Test getting travel recommendations with date parameters."""
        mock_call_tool.return_value = mock_travel_recommendation_response

        start_date = "2025-06-01"
        end_date = "2025-06-07"
        result = await client.get_travel_recommendation(
            city="Barcelona", start_date=start_date, end_date=end_date
        )

        mock_call_tool.assert_called_once_with(
            "get_travel_recommendation",
            {
                "location": {"city": "Barcelona"},
                "start_date": start_date,
                "end_date": end_date,
            },
            False,
        )

        assert isinstance(result, RecommendationResponse)
        assert result.location["city"] == "Barcelona"

    @patch("src.mcp.weather.client.BaseMCPClient.call_tool")
    async def test_get_travel_recommendation_error(self, mock_call_tool, client):
        """Test error handling for get_travel_recommendation."""
        mock_call_tool.side_effect = Exception("API error")

        with pytest.raises(MCPError):
            await client.get_travel_recommendation(city="InvalidCity")


class TestWeatherService:
    """Tests for the WeatherService class."""

    @patch("src.mcp.weather.client.WeatherMCPClient.get_current_weather")
    async def test_get_destination_weather(self, mock_get_current_weather):
        """Test getting weather for a travel destination."""
        # Setup mock response
        mock_response = CurrentWeatherResponse(
            temperature=25.0,
            feels_like=26.5,
            temp_min=23.0,
            temp_max=28.0,
            pressure=1015,
            humidity=60,
            wind_speed=3.5,
            wind_direction=150,
            clouds=20,
            weather={
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d",
            },
            location={"city": "Tokyo", "country": "JP"},
            timestamp=1683889200,
        )
        mock_get_current_weather.return_value = mock_response

        # Create client and service
        client = WeatherMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = WeatherService(client)

        # Test with known location
        result = await service.get_destination_weather("Tokyo, JP")
        mock_get_current_weather.assert_called_once_with(city="Tokyo", country="JP")

        assert result["temperature"] == 25.0
        assert result["weather"]["main"] == "Clear"
        assert result["location"]["city"] == "Tokyo"

        # Test error handling
        mock_get_current_weather.reset_mock()
        mock_get_current_weather.side_effect = Exception("API error")

        error_result = await service.get_destination_weather("Invalid City")
        assert "error" in error_result
        assert "Invalid City" in error_result["error"]

    @patch("src.mcp.weather.client.WeatherMCPClient.get_forecast")
    async def test_get_trip_weather_summary(self, mock_get_forecast):
        """Test getting weather summary for a trip period."""
        # Setup mock response with data matching the forecast fixture
        mock_response = ForecastResponse.model_validate(
            {
                "location": {"city": "New York", "country": "US"},
                "current": {
                    "temperature": 20.0,
                    "feels_like": 21.5,
                    "temp_min": 18.0,
                    "temp_max": 23.0,
                    "pressure": 1010,
                    "humidity": 70,
                    "wind_speed": 4.0,
                    "wind_direction": 180,
                    "clouds": 30,
                    "weather": {
                        "id": 802,
                        "main": "Clouds",
                        "description": "scattered clouds",
                        "icon": "03d",
                    },
                    "location": {"city": "New York", "country": "US"},
                    "timestamp": 1683889200,
                },
                "daily": [
                    {
                        "date": "2025-07-01",
                        "temp_min": 19.0,
                        "temp_max": 24.0,
                        "temp_avg": 21.5,
                        "feels_like": {
                            "day": 22.0,
                            "night": 19.5,
                            "eve": 21.0,
                            "morn": 20.0,
                        },
                        "pressure": 1010,
                        "humidity": 70,
                        "wind_speed": 4.0,
                        "wind_direction": 180,
                        "clouds": 30,
                        "probability": 0.3,
                        "weather": {
                            "id": 802,
                            "main": "Clouds",
                            "description": "scattered clouds",
                            "icon": "03d",
                        },
                    },
                    {
                        "date": "2025-07-02",
                        "temp_min": 20.0,
                        "temp_max": 25.0,
                        "temp_avg": 22.5,
                        "feels_like": {
                            "day": 23.0,
                            "night": 20.5,
                            "eve": 22.0,
                            "morn": 21.0,
                        },
                        "pressure": 1012,
                        "humidity": 65,
                        "wind_speed": 3.5,
                        "wind_direction": 170,
                        "clouds": 20,
                        "probability": 0.2,
                        "weather": {
                            "id": 801,
                            "main": "Clouds",
                            "description": "few clouds",
                            "icon": "02d",
                        },
                    },
                    {
                        "date": "2025-07-03",
                        "temp_min": 21.0,
                        "temp_max": 26.0,
                        "temp_avg": 23.5,
                        "feels_like": {
                            "day": 24.0,
                            "night": 21.5,
                            "eve": 23.0,
                            "morn": 22.0,
                        },
                        "pressure": 1015,
                        "humidity": 60,
                        "wind_speed": 3.0,
                        "wind_direction": 160,
                        "clouds": 10,
                        "probability": 0.1,
                        "weather": {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        },
                    },
                ],
            }
        )
        mock_get_forecast.return_value = mock_response

        # Create client and service
        client = WeatherMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = WeatherService(client)

        # Test trip weather summary
        result = await service.get_trip_weather_summary(
            destination="New York, US", start_date="2025-07-01", end_date="2025-07-03"
        )

        mock_get_forecast.assert_called_once_with(
            city="New York", country="US", days=16
        )

        assert isinstance(result, TravelWeatherSummary)
        assert result.destination == "New York, US"
        assert result.start_date == "2025-07-01"
        assert result.end_date == "2025-07-03"
        assert result.temperature["average"] == 22.5  # Average of 21.5, 22.5, 23.5
        assert result.temperature["min"] == 19.0
        assert result.temperature["max"] == 26.0
        assert result.conditions["most_common"] == "Clouds"
        assert len(result.days) == 3

        # Test error handling
        mock_get_forecast.reset_mock()
        mock_get_forecast.side_effect = Exception("API error")

        error_result = await service.get_trip_weather_summary(
            destination="Invalid City", start_date="2025-07-01", end_date="2025-07-03"
        )
        assert error_result.error is not None
        assert "API error" in error_result.error

    @patch("src.mcp.weather.client.WeatherMCPClient.get_current_weather")
    @patch("src.mcp.weather.client.WeatherMCPClient.get_forecast")
    async def test_compare_destinations_weather(
        self, mock_get_forecast, mock_get_current_weather
    ):
        """Test comparing weather across multiple destinations."""

        # Setup mock responses for current weather
        def mock_current_weather_side_effect(city, country=None, **kwargs):
            if city == "Miami":
                return CurrentWeatherResponse.model_validate(
                    {
                        "temperature": 30.0,
                        "feels_like": 32.0,
                        "temp_min": 28.0,
                        "temp_max": 32.0,
                        "pressure": 1010,
                        "humidity": 80,
                        "wind_speed": 3.0,
                        "wind_direction": 160,
                        "clouds": 20,
                        "weather": {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        },
                        "location": {"city": "Miami", "country": "US"},
                        "timestamp": 1683889200,
                    }
                )
            elif city == "Cancun":
                return CurrentWeatherResponse.model_validate(
                    {
                        "temperature": 28.0,
                        "feels_like": 30.0,
                        "temp_min": 26.0,
                        "temp_max": 30.0,
                        "pressure": 1012,
                        "humidity": 75,
                        "wind_speed": 4.0,
                        "wind_direction": 170,
                        "clouds": 30,
                        "weather": {
                            "id": 801,
                            "main": "Clouds",
                            "description": "few clouds",
                            "icon": "02d",
                        },
                        "location": {"city": "Cancun", "country": "MX"},
                        "timestamp": 1683889200,
                    }
                )
            else:
                return CurrentWeatherResponse.model_validate(
                    {
                        "temperature": 32.0,
                        "feels_like": 34.0,
                        "temp_min": 30.0,
                        "temp_max": 34.0,
                        "pressure": 1008,
                        "humidity": 85,
                        "wind_speed": 2.0,
                        "wind_direction": 150,
                        "clouds": 10,
                        "weather": {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        },
                        "location": {"city": "Phuket", "country": "TH"},
                        "timestamp": 1683889200,
                    }
                )

        mock_get_current_weather.side_effect = mock_current_weather_side_effect

        # Setup mock response for forecast (simplified for test)
        mock_get_forecast.return_value = ForecastResponse.model_validate(
            {
                "location": {},
                "current": {},  # Simplified for test
                "daily": [
                    {
                        "date": "2025-08-15",
                        "temp_min": 25.0,
                        "temp_max": 30.0,
                        "temp_avg": 27.5,
                        "feels_like": {},
                        "pressure": 1010,
                        "humidity": 70,
                        "wind_speed": 3.0,
                        "wind_direction": 160,
                        "clouds": 20,
                        "probability": 0.2,
                        "weather": {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        },
                    }
                ],
            }
        )

        # Create client and service
        client = WeatherMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = WeatherService(client)

        # Test comparing current weather
        result = await service.compare_destinations_weather(
            destinations=["Miami, US", "Cancun, MX", "Phuket, TH"]
        )

        assert isinstance(result, DestinationWeatherComparison)
        assert len(result.destinations) == 3
        assert len(result.results) == 3
        assert result.date == "current"
        assert len(result.ranking) == 3
        # Phuket should be first due to highest temperature in mock data
        assert result.ranking[0] == "Phuket, TH"

        # Test comparing with specific date
        mock_get_current_weather.reset_mock()
        mock_get_forecast.reset_mock()

        result = await service.compare_destinations_weather(
            destinations=["Miami, US", "Cancun, MX", "Phuket, TH"], date="2025-08-15"
        )

        assert mock_get_forecast.call_count == 3
        assert result.date == "2025-08-15"

        # Test error handling for one destination
        mock_get_current_weather.reset_mock()
        mock_get_current_weather.side_effect = [
            CurrentWeatherResponse.model_validate(
                {
                    "temperature": 30.0,
                    "feels_like": 32.0,
                    "temp_min": 28.0,
                    "temp_max": 32.0,
                    "pressure": 1010,
                    "humidity": 80,
                    "wind_speed": 3.0,
                    "wind_direction": 160,
                    "clouds": 20,
                    "weather": {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    },
                    "location": {"city": "Miami", "country": "US"},
                    "timestamp": 1683889200,
                }
            ),
            Exception("API error"),
            CurrentWeatherResponse.model_validate(
                {
                    "temperature": 32.0,
                    "feels_like": 34.0,
                    "temp_min": 30.0,
                    "temp_max": 34.0,
                    "pressure": 1008,
                    "humidity": 85,
                    "wind_speed": 2.0,
                    "wind_direction": 150,
                    "clouds": 10,
                    "weather": {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    },
                    "location": {"city": "Phuket", "country": "TH"},
                    "timestamp": 1683889200,
                }
            ),
        ]

        result = await service.compare_destinations_weather(
            destinations=["Miami, US", "Invalid City", "Phuket, TH"]
        )
        assert len(result.results) == 3
        assert "error" in result.results[1]
        assert len(result.ranking) == 2  # Only valid destinations are ranked

    @patch("src.mcp.weather.client.WeatherMCPClient.get_travel_recommendation")
    async def test_get_optimal_travel_time(self, mock_get_travel_recommendation):
        """Test getting optimal travel time recommendations."""
        # Setup mock response
        mock_response = RecommendationResponse.model_validate(
            {
                "location": {"city": "Aspen", "country": "US"},
                "current_weather": {
                    "temperature": 5.0,
                    "feels_like": 2.0,
                    "temp_min": 2.0,
                    "temp_max": 8.0,
                    "pressure": 1020,
                    "humidity": 70,
                    "wind_speed": 2.0,
                    "wind_direction": 180,
                    "clouds": 30,
                    "weather": {
                        "id": 801,
                        "main": "Snow",
                        "description": "light snow",
                        "icon": "13d",
                    },
                    "location": {"city": "Aspen", "country": "US"},
                    "timestamp": 1683889200,
                },
                "recommendations": {
                    "clothing": [
                        "Warm winter clothing",
                        "Waterproof jacket and pants",
                        "Thermal layers",
                        "Ski gloves and hat",
                    ],
                    "activities": [
                        "Skiing conditions are excellent with fresh powder",
                        "Consider indoor activities in the afternoon "
                        "due to cold temperatures",
                    ],
                    "forecast_based": [
                        "Good skiing conditions expected for the next 3 days",
                        "Best ski days will be Thursday and Friday with fresh snow",
                        "Warmer temperatures expected next week",
                    ],
                },
            }
        )
        mock_get_travel_recommendation.return_value = mock_response

        # Create client and service
        client = WeatherMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = WeatherService(client)

        # Test optimal travel time for skiing
        result = await service.get_optimal_travel_time(
            destination="Aspen, US", activity_type="skiing"
        )

        mock_get_travel_recommendation.assert_called_once_with(
            city="Aspen", country="US", activities=["skiing"]
        )

        assert isinstance(result, OptimalTravelTime)
        assert result.destination == "Aspen, US"
        assert result.activity_type == "skiing"
        assert result.current_weather == "Snow"
        assert result.current_temp == 5.0
        assert "Skiing conditions are excellent" in result.activity_recommendation
        assert len(result.good_weather_days) == 2
        assert len(result.clothing_recommendations) == 4

        # Test error handling
        mock_get_travel_recommendation.reset_mock()
        mock_get_travel_recommendation.side_effect = Exception("API error")

        error_result = await service.get_optimal_travel_time(
            destination="Invalid City", activity_type="skiing"
        )
        assert error_result.error is not None
        assert "API error" in error_result.error
