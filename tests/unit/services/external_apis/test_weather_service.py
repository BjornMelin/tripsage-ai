"""Tests for Weather service."""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.exceptions.exceptions import CoreExternalAPIError
from tripsage_core.services.external_apis.weather_service import (
    WeatherService,
    WeatherServiceError,
)


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock environment variables to prevent Settings validation errors."""
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "testing",
            "DATABASE_URL": "https://test.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-public-key",
            "DATABASE_SERVICE_KEY": "test-service-key",
            "DATABASE_JWT_SECRET": "test-jwt-secret",
            "OPENAI_API_KEY": "test-key",
        },
    ):
        yield


class TestWeatherService:
    """Test WeatherService."""

    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx client."""
        with patch(
            "tripsage_core.services.external_apis.weather_service.httpx"
        ) as mock:
            yield mock

    @pytest.fixture
    def service(self):
        """Create WeatherService instance."""
        with patch(
            "tripsage_core.services.external_apis.weather_service.get_settings"
        ) as mock_settings:
            from pydantic import SecretStr

            mock_settings.return_value.openweathermap_api_key = SecretStr(
                "test-api-key"
            )
            return WeatherService()

    @pytest.mark.asyncio
    async def test_init_creates_client(self, mock_httpx: Any, service: Any):
        """Test service initialization creates HTTP client."""
        assert service.client is not None
        mock_httpx.AsyncClient.assert_called_once()  # type: ignore[member]

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self, mock_httpx: Any, service: Any):
        """Test successful current weather request."""
        mock_response = MagicMock()  # type: ignore[assignment]
        mock_response.json.return_value = {
            "name": "New York",
            "main": {"temp": 20.0, "humidity": 65},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 3.5},
        }
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client

        service.client = mock_client

        result = await service.get_current_weather("New York", "US")

        assert result.location == "New York"
        assert result.temperature_celsius == 20.0
        assert result.humidity == 65
        assert result.condition == "clear sky"

        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_weather_error(self, mock_httpx: Any, service: Any):
        """Test current weather error handling."""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("API Error")
        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client

        service.client = mock_client

        with pytest.raises(WeatherServiceError):
            await service.get_current_weather("invalid", "US")

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, mock_httpx: Any, service: Any):
        """Test successful forecast request."""
        mock_response = MagicMock()  # type: ignore[assignment]
        mock_response.json.return_value = {
            "list": [
                {
                    "dt": 1640995200,
                    "main": {"temp": 20.0, "humidity": 65},
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 3.5},
                    "dt_txt": "2022-01-01 00:00:00",
                }
            ]
        }
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client

        service.client = mock_client

        result = await service.get_forecast("New York", "US", days=5)

        assert len(result.forecasts) == 1
        forecast = result.forecasts[0]
        assert forecast.temperature_celsius == 20.0
        assert forecast.humidity == 65
        assert forecast.condition == "clear sky"

        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_air_quality_success(self, mock_httpx: Any, service: Any):
        """Test successful air quality request."""
        mock_response = MagicMock()  # type: ignore[assignment]
        mock_response.json.return_value = {
            "coord": {"lat": 40.7128, "lon": -74.0060},
            "list": [
                {
                    "main": {"aqi": 2},
                    "components": {
                        "co": 250,
                        "no": 10,
                        "no2": 20,
                        "o3": 30,
                        "so2": 5,
                        "pm2_5": 15,
                        "pm10": 25,
                        "nh3": 8,
                    },
                }
            ],
        }
        mock_response.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client

        service.client = mock_client

        result = await service.get_air_quality(40.7128, -74.0060)

        assert result.aqi_score == 2
        assert result.co == 250
        assert result.pm25 == 15

        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_activity_suitability(self, service: Any):
        """Test activity suitability scoring."""
        weather_data = {
            "temp": 22,
            "humidity": 60,
            "wind": 5,
            "precipitation": 0,
            "conditions": "clear",
        }

        # Test hiking suitability
        hiking_score, reasons, warnings = await service.evaluate_activity_suitability(
            activity="hiking", weather_data=weather_data, user_preferences={}
        )

        assert isinstance(hiking_score, int)
        assert isinstance(reasons, list)
        assert isinstance(warnings, list)

    @pytest.mark.asyncio
    async def test_travel_weather_summary(self, service: Any):
        """Test travel weather summary generation."""
        location = "New York"
        start_date = "2024-06-01"
        end_date = "2024-06-07"

        # No external calls required; we stub forecast below

        with patch.object(service, "get_forecast") as mock_get_forecast:
            mock_get_forecast.return_value = MagicMock(forecasts=[])

            result = await service.get_travel_weather_summary(
                location=location, start_date=start_date, end_date=end_date
            )

            assert hasattr(result, "summary")
            assert hasattr(result, "highlights")
            assert hasattr(result, "concerns")

    @pytest.mark.asyncio
    async def test_error_handling_common_patterns(self, service: Any):
        """Test common error handling patterns."""
        mock_client = MagicMock()
        service.client = mock_client

        # Test HTTP error
        mock_client.get.side_effect = Exception("HTTP Error")
        with pytest.raises(WeatherServiceError):
            await service.get_current_weather("test", "US")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_service_context_manager(self, service: Any):
        """Test service can be used as context manager."""
        with (
            patch.object(service, "connect") as mock_connect,
            patch.object(service, "disconnect") as mock_disconnect,
        ):
            async with service as s:
                assert s is service
                mock_connect.assert_called_once()

            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, service: Any):
        """Test connect and disconnect methods."""
        await service.connect()
        await service.disconnect()

        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_api_key_missing_error(self):
        """Test error when API key is missing."""
        with patch(
            "tripsage_core.services.external_apis.weather_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.openweather_api_key = None

            service = WeatherService()

            with pytest.raises(CoreExternalAPIError):
                await service.get_current_weather("test", "US")  # type: ignore[arg-type]


class TestWeatherServiceError:
    """Test WeatherServiceError."""

    def test_error_initialization(self):
        """Test error initialization with all parameters."""
        error = WeatherServiceError(
            message="Test error", original_error=Exception("Original")
        )

        assert error.message == "Test error"
        assert error.code == "WEATHER_API_ERROR"
        assert error.details.service == "WeatherService"
        assert error.details.additional_context.get("original_error") == "Original"
        assert error.original_error is not None

    def test_error_initialization_minimal(self):
        """Test error initialization with minimal parameters."""
        error = WeatherServiceError("Test error")

        assert error.message == "Test error"
        assert error.code == "WEATHER_API_ERROR"
        assert error.details.service == "WeatherService"
        assert error.details.additional_context.get("original_error") is None
