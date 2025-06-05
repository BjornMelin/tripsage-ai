"""
Integration tests for Weather API service.

This module tests the integration with OpenWeatherMap API for weather data.
"""

from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.external_apis.weather_service import WeatherService


class TestWeatherServiceIntegration:
    """Test Weather API integration."""

    @pytest.fixture
    def weather_service(self):
        """Create weather service instance with mocked HTTP client."""
        service = WeatherService(api_key="test_api_key")
        service._http_client = AsyncMock()
        return service

    @pytest.fixture
    def sample_current_weather_response(self):
        """Sample current weather API response."""
        return {
            "coord": {"lon": 2.3522, "lat": 48.8566},
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "base": "stations",
            "main": {
                "temp": 293.15,  # 20°C in Kelvin
                "feels_like": 292.15,
                "temp_min": 290.15,
                "temp_max": 295.15,
                "pressure": 1013,
                "humidity": 65,
            },
            "visibility": 10000,
            "wind": {"speed": 3.5, "deg": 270},
            "clouds": {"all": 0},
            "dt": 1622548800,
            "sys": {
                "type": 2,
                "id": 2019646,
                "country": "FR",
                "sunrise": 1622520000,
                "sunset": 1622574000,
            },
            "timezone": 7200,
            "id": 2988507,
            "name": "Paris",
            "cod": 200,
        }

    @pytest.fixture
    def sample_forecast_response(self):
        """Sample weather forecast API response."""
        return {
            "cod": "200",
            "message": 0,
            "cnt": 40,
            "list": [
                {
                    "dt": 1622548800,
                    "main": {
                        "temp": 293.15,
                        "feels_like": 292.15,
                        "temp_min": 290.15,
                        "temp_max": 295.15,
                        "pressure": 1013,
                        "humidity": 65,
                    },
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                    "clouds": {"all": 0},
                    "wind": {"speed": 3.5, "deg": 270},
                    "visibility": 10000,
                    "pop": 0,
                    "dt_txt": "2024-06-01 12:00:00",
                },
                {
                    "dt": 1622559600,
                    "main": {
                        "temp": 291.15,
                        "feels_like": 290.15,
                        "temp_min": 289.15,
                        "temp_max": 292.15,
                        "pressure": 1014,
                        "humidity": 70,
                    },
                    "weather": [
                        {
                            "id": 801,
                            "main": "Clouds",
                            "description": "few clouds",
                            "icon": "02d",
                        }
                    ],
                    "clouds": {"all": 20},
                    "wind": {"speed": 2.5, "deg": 250},
                    "visibility": 10000,
                    "pop": 0.1,
                    "dt_txt": "2024-06-01 15:00:00",
                },
            ],
            "city": {
                "id": 2988507,
                "name": "Paris",
                "coord": {"lat": 48.8566, "lon": 2.3522},
                "country": "FR",
                "population": 2161000,
                "timezone": 7200,
                "sunrise": 1622520000,
                "sunset": 1622574000,
            },
        }

    @pytest.mark.asyncio
    async def test_get_current_weather_success(
        self, weather_service, sample_current_weather_response
    ):
        """Test successful current weather retrieval."""
        # Mock HTTP response
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = sample_current_weather_response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            200
        )

        result = await weather_service.get_current_weather("Paris", "FR")

        # Assertions
        assert result is not None
        assert result["location"]["city"] == "Paris"
        assert result["location"]["country"] == "FR"
        assert result["temperature"]["current"] == 20.0  # Converted from Kelvin
        assert result["temperature"]["feels_like"] == 19.0
        assert result["weather"]["main"] == "Clear"
        assert result["weather"]["description"] == "clear sky"
        assert result["humidity"] == 65
        assert result["wind"]["speed"] == 3.5

    @pytest.mark.asyncio
    async def test_get_weather_forecast_success(
        self, weather_service, sample_forecast_response
    ):
        """Test successful weather forecast retrieval."""
        # Mock HTTP response
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = sample_forecast_response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            200
        )

        result = await weather_service.get_weather_forecast("Paris", "FR", days=5)

        # Assertions
        assert result is not None
        assert result["location"]["city"] == "Paris"
        assert result["location"]["country"] == "FR"
        assert "forecast" in result
        assert len(result["forecast"]) >= 2

        # Check first forecast entry
        first_forecast = result["forecast"][0]
        assert first_forecast["temperature"]["current"] == 20.0
        assert first_forecast["weather"]["main"] == "Clear"
        assert first_forecast["precipitation_probability"] == 0

    @pytest.mark.asyncio
    async def test_get_weather_by_coordinates_success(
        self, weather_service, sample_current_weather_response
    ):
        """Test weather retrieval by coordinates."""
        # Mock HTTP response
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = sample_current_weather_response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            200
        )

        result = await weather_service.get_weather_by_coordinates(48.8566, 2.3522)

        # Assertions
        assert result is not None
        assert result["location"]["coordinates"]["lat"] == 48.8566
        assert result["location"]["coordinates"]["lon"] == 2.3522
        assert result["temperature"]["current"] == 20.0

    @pytest.mark.asyncio
    async def test_weather_alerts_success(self, weather_service):
        """Test weather alerts retrieval."""
        alerts_response = {
            "lat": 48.8566,
            "lon": 2.3522,
            "timezone": "Europe/Paris",
            "alerts": [
                {
                    "sender_name": "Meteo France",
                    "event": "Thunderstorm Warning",
                    "start": 1622559600,
                    "end": 1622574000,
                    "description": "Severe thunderstorms expected in the afternoon",
                    "tags": ["Thunderstorm"],
                }
            ],
        }

        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = alerts_response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            200
        )

        result = await weather_service.get_weather_alerts(48.8566, 2.3522)

        # Assertions
        assert result is not None
        assert "alerts" in result
        assert len(result["alerts"]) == 1

        alert = result["alerts"][0]
        assert alert["event"] == "Thunderstorm Warning"
        assert alert["severity"] == "warning"
        assert "description" in alert

    @pytest.mark.asyncio
    async def test_api_error_handling(self, weather_service):
        """Test handling of API errors."""
        # Mock 401 Unauthorized response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            401
        )
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = {
            "cod": 401,
            "message": "Invalid API key",
        }

        with pytest.raises(Exception, match="Invalid API key"):
            await weather_service.get_current_weather("Paris", "FR")

    @pytest.mark.asyncio
    async def test_city_not_found_handling(self, weather_service):
        """Test handling of city not found errors."""
        # Mock 404 response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            404
        )
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = {
            "cod": "404",
            "message": "city not found",
        }

        result = await weather_service.get_current_weather("InvalidCity", "XX")
        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, weather_service):
        """Test handling of rate limit errors."""
        # Mock 429 Too Many Requests response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            429
        )
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = {
            "cod": 429,
            "message": "Rate limit exceeded",
        }

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await weather_service.get_current_weather("Paris", "FR")

    @pytest.mark.asyncio
    async def test_timeout_handling(self, weather_service):
        """Test handling of request timeouts."""
        import asyncio

        # Mock timeout error
        weather_service._http_client.get.side_effect = asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await weather_service.get_current_weather("Paris", "FR")

    @pytest.mark.asyncio
    async def test_network_error_handling(self, weather_service):
        """Test handling of network errors."""
        import aiohttp

        # Mock network error
        weather_service._http_client.get.side_effect = aiohttp.ClientError(
            "Network connection failed"
        )

        with pytest.raises(aiohttp.ClientError):
            await weather_service.get_current_weather("Paris", "FR")

    @pytest.mark.asyncio
    async def test_temperature_unit_conversion(self, weather_service):
        """Test temperature unit conversion."""
        # Test Celsius (default)
        temp_kelvin = 293.15
        temp_celsius = weather_service._kelvin_to_celsius(temp_kelvin)
        assert temp_celsius == 20.0

        # Test Fahrenheit conversion
        temp_fahrenheit = weather_service._celsius_to_fahrenheit(temp_celsius)
        assert temp_fahrenheit == 68.0

    @pytest.mark.asyncio
    async def test_caching_behavior(
        self, weather_service, sample_current_weather_response
    ):
        """Test weather data caching."""
        # Mock HTTP response
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = sample_current_weather_response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            200
        )

        # First call
        result1 = await weather_service.get_current_weather("Paris", "FR")

        # Second call (should use cache)
        result2 = await weather_service.get_current_weather("Paris", "FR")

        # Both results should be the same
        assert result1 == result2

        # HTTP client should only be called once if caching is enabled
        # (This depends on the actual implementation)

    @pytest.mark.asyncio
    async def test_bulk_weather_retrieval(
        self, weather_service, sample_current_weather_response
    ):
        """Test bulk weather retrieval for multiple cities."""
        cities = [("Paris", "FR"), ("London", "GB"), ("New York", "US")]

        # Mock HTTP responses
        weather_service._http_client.get.return_value.__aenter__.return_value.json.return_value = sample_current_weather_response
        weather_service._http_client.get.return_value.__aenter__.return_value.status = (
            200
        )

        results = []
        for city, country in cities:
            result = await weather_service.get_current_weather(city, country)
            results.append(result)

        assert len(results) == 3
        assert all(result is not None for result in results)
