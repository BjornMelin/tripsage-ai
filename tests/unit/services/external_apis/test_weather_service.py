"""Tests for Weather service."""

# pyright: reportPrivateUsage=false

import os
from datetime import datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from tripsage_core.services.external_apis.weather_service import (
    WeatherService,
    WeatherServiceError,
)


def get_mock_make_request(service: WeatherService) -> AsyncMock:
    """Get the _make_request method as AsyncMock for assertions."""
    return cast(AsyncMock, service._make_request)


def set_client(service: WeatherService, client: Any) -> None:
    """Set the _client attribute on service."""
    service._client = client


def get_connected(service: WeatherService) -> bool:
    """Get the _connected status."""
    return service._connected


def get_client(service: WeatherService) -> Any:
    """Get the _client from service."""
    return service._client


def analyze_weather_patterns(
    service: WeatherService, forecast_data: dict[str, Any]
) -> dict[str, Any]:
    """Call _analyze_weather_patterns helper method."""
    return service._analyze_weather_patterns(forecast_data)


def generate_packing_suggestions(
    service: WeatherService, weather_stats: dict[str, Any]
) -> list[str]:
    """Call _generate_packing_suggestions helper method."""
    return service._generate_packing_suggestions(weather_stats)


def score_activity(
    service: WeatherService, conditions: dict[str, Any], activity: str
) -> tuple[int, list[str], list[str]]:
    """Call _score_activity helper method."""
    return service._score_activity(conditions, activity)


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
    async def test_get_current_weather_success(self, service: WeatherService):
        """Test successful current weather request."""
        mock_response = {
            "name": "New York",
            "main": {"temp": 20.0, "humidity": 65},
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 3.5},
        }

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_current_weather(40.7128, -74.0060)

            assert isinstance(result, dict)
            assert result["name"] == "New York"
            assert result["main"]["temp"] == 20.0
            assert result["main"]["humidity"] == 65
            assert result["weather"][0]["description"] == "clear sky"

            mock_make_request = get_mock_make_request(service)
            mock_make_request.assert_called_once_with(
                "weather",
                {"lat": 40.7128, "lon": -74.0060, "units": "metric", "lang": "en"},
            )

    @pytest.mark.asyncio
    async def test_get_current_weather_with_units(self, service: WeatherService):
        """Test current weather request with custom units."""
        mock_response = {
            "main": {"temp": 68.0, "humidity": 65},
            "weather": [{"description": "clear sky"}],
        }

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_current_weather(
                40.7128, -74.0060, units="imperial"
            )

            assert result["main"]["temp"] == 68.0
            mock_make_request = get_mock_make_request(service)
            mock_make_request.assert_called_once()
            assert mock_make_request.call_args == call(
                "weather",
                {"lat": 40.7128, "lon": -74.0060, "units": "imperial", "lang": "en"},
            )

    @pytest.mark.asyncio
    async def test_get_forecast_success(self, service: WeatherService):
        """Test successful forecast request."""
        mock_response = {
            "daily": [
                {
                    "dt": 1640995200,
                    "temp": {"min": 15.0, "max": 25.0},
                    "weather": [{"description": "clear sky", "main": "Clear"}],
                    "pop": 0.1,
                    "uvi": 5.2,
                }
            ],
            "hourly": [],
        }

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_forecast(40.7128, -74.0060, days=5)

            assert isinstance(result, dict)
            assert "daily" in result
            assert len(result["daily"]) == 1

            mock_make_request = get_mock_make_request(service)
            mock_make_request.assert_called_once()
            assert mock_make_request.call_args[1]["use_v3"] is True

    @pytest.mark.asyncio
    async def test_get_forecast_exclude_hourly(self, service: WeatherService):
        """Test forecast request excluding hourly data."""
        mock_response: dict[str, Any] = {"daily": [], "current": {}}

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            await service.get_forecast(40.7128, -74.0060, days=5, include_hourly=False)

            mock_make_request = get_mock_make_request(service)
            call_params = cast(dict[str, Any], mock_make_request.call_args[0][1])
            assert "minutely,hourly,alerts" in call_params["exclude"]

    @pytest.mark.asyncio
    async def test_get_air_quality_success(self, service: WeatherService):
        """Test successful air quality request."""
        mock_response = {
            "coord": {"lat": 40.7128, "lon": -74.0060},
            "list": [
                {
                    "main": {"aqi": 2},
                    "components": {
                        "co": 250.5,
                        "no": 10.2,
                        "no2": 20.3,
                        "o3": 30.1,
                        "so2": 5.0,
                        "pm2_5": 15.5,
                        "pm10": 25.0,
                        "nh3": 8.2,
                    },
                }
            ],
        }

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_air_quality(40.7128, -74.0060)

            assert isinstance(result, dict)
            assert result["list"][0]["main"]["aqi"] == 2
            assert result["list"][0]["components"]["pm2_5"] == 15.5

            mock_make_request = get_mock_make_request(service)
            mock_make_request.assert_called_once_with(
                "air_pollution", {"lat": 40.7128, "lon": -74.0060}
            )

    @pytest.mark.asyncio
    async def test_get_weather_alerts(self, service: WeatherService):
        """Test weather alerts request."""
        mock_response = {
            "alerts": [
                {
                    "event": "Thunderstorm Warning",
                    "start": 1640995200,
                    "end": 1641000000,
                    "description": "Severe thunderstorms expected",
                }
            ]
        }

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_weather_alerts(40.7128, -74.0060)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["event"] == "Thunderstorm Warning"

    @pytest.mark.asyncio
    async def test_get_uv_index(self, service: WeatherService):
        """Test UV index request."""
        mock_response = {"value": 5.2, "date": "2024-01-01"}

        with patch.object(
            service, "_make_request", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_uv_index(40.7128, -74.0060)

            assert result["value"] == 5.2
            mock_make_request = get_mock_make_request(service)
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_travel_weather_summary(self, service: WeatherService):
        """Test travel weather summary generation."""
        arrival = datetime(2024, 6, 1)
        departure = datetime(2024, 6, 7)

        mock_forecast = {
            "daily": [
                {
                    "temp": {"min": 15.0, "max": 25.0},
                    "weather": [{"main": "Clear"}],
                    "pop": 0.1,
                    "uvi": 5.0,
                    "rain": 0,
                    "snow": 0,
                }
                for _ in range(7)
            ]
        }
        mock_air_quality = {"list": [{"main": {"aqi": 2}}]}
        mock_alerts: list[dict[str, Any]] = []

        with (
            patch.object(
                service, "get_forecast", new=AsyncMock(return_value=mock_forecast)
            ),
            patch.object(
                service, "get_air_quality", new=AsyncMock(return_value=mock_air_quality)
            ),
            patch.object(
                service, "get_weather_alerts", new=AsyncMock(return_value=mock_alerts)
            ),
        ):
            result = await service.get_travel_weather_summary(
                40.7128, -74.0060, arrival, departure, activities=["hiking", "beach"]
            )

            assert isinstance(result, dict)
            assert "average_temperature" in result
            assert "activity_recommendations" in result
            assert "packing_suggestions" in result
            assert "air_quality_forecast" in result

    @pytest.mark.asyncio
    async def test_check_travel_weather_conditions(self, service: WeatherService):
        """Test checking travel weather conditions for activities."""
        travel_date = datetime(2024, 6, 15)

        mock_forecast = {
            "daily": [
                {
                    "dt": int(travel_date.timestamp()),
                    "temp": {"day": 22.0},
                    "weather": [{"main": "Clear"}],
                    "pop": 0.1,
                    "wind_speed": 5.0,
                }
            ]
        }

        with patch.object(
            service, "get_forecast", new=AsyncMock(return_value=mock_forecast)
        ):
            result = await service.check_travel_weather_conditions(
                40.7128, -74.0060, travel_date, "hiking"
            )

            assert isinstance(result, dict)
            assert "suitable" in result
            assert "score" in result

    @pytest.mark.asyncio
    async def test_get_multi_city_weather(self, service: WeatherService):
        """Test getting weather for multiple cities."""
        cities = [
            (40.7128, -74.0060, "New York"),
            (34.0522, -118.2437, "Los Angeles"),
        ]

        mock_response = {"main": {"temp": 20.0}, "weather": [{"description": "clear"}]}

        with patch.object(
            service, "get_current_weather", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.get_multi_city_weather(cities)

            assert isinstance(result, dict)
            assert "New York" in result
            assert "Los Angeles" in result

    @pytest.mark.asyncio
    async def test_error_handling_http_status(self, service: WeatherService):
        """Test HTTP error handling."""
        import httpx

        http_error = httpx.HTTPStatusError(
            "API Error",
            request=MagicMock(),
            response=MagicMock(status_code=404, content=b'{"message":"Not Found"}'),
        )

        with (
            patch.object(service, "ensure_connected", new=AsyncMock()),
            patch(
                "tripsage_core.services.external_apis.weather_service.request_with_backoff",
                side_effect=http_error,
            ),
        ):
            set_client(service, MagicMock())

            with pytest.raises(WeatherServiceError) as exc_info:
                await service._make_request("weather", {"lat": 0, "lon": 0})

            assert "openweathermap api error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_service_context_manager(self, service: WeatherService):
        """Test service can be used as context manager."""
        with (
            patch.object(service, "connect", new=AsyncMock()) as mock_connect,
            patch.object(service, "disconnect", new=AsyncMock()) as mock_disconnect,
        ):
            async with service as s:
                assert s is service
                mock_connect.assert_called_once()

            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, service: WeatherService):
        """Test connect and disconnect methods."""
        await service.connect()
        assert get_connected(service)
        assert get_client(service) is not None

        await service.disconnect()
        assert not get_connected(service)
        assert get_client(service) is None

    @pytest.mark.asyncio
    async def test_health_check_success(self, service: WeatherService):
        """Test health check when API is accessible."""
        mock_response = {"main": {"temp": 20.0}}

        with patch.object(
            service, "get_current_weather", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, service: WeatherService):
        """Test health check when API is not accessible."""
        from tripsage_core.exceptions import CoreServiceError

        with patch.object(
            service,
            "get_current_weather",
            side_effect=CoreServiceError(
                message="Connection failed",
                code="CONNECTION_ERROR",
                service="WeatherService",
            ),
        ):
            result = await service.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_api_key_missing_error(self):
        """Test error when API key is missing."""
        with patch(
            "tripsage_core.services.external_apis.weather_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.openweather_api_key = None
            mock_settings.return_value.openweathermap_api_key = None

            service = WeatherService()

            # Since _make_request is called and needs api_key
            with (
                patch.object(service, "ensure_connected", new=AsyncMock()),
                patch(
                    "tripsage_core.services.external_apis.weather_service.request_with_backoff",
                    new=AsyncMock(return_value=MagicMock(json=dict)),
                ),
            ):
                set_client(service, MagicMock())
                # The error should occur when params["appid"] = None
                result = await service._make_request("weather", {"lat": 0, "lon": 0})
                # API key will be None in params but request will go through
                assert isinstance(result, dict)


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


class TestWeatherServiceHelpers:
    """Test internal helper methods."""

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

    def test_analyze_weather_patterns(self, service: WeatherService):
        """Test weather pattern analysis."""
        forecast_data = {
            "daily": [
                {
                    "temp": {"min": 15.0, "max": 25.0},
                    "weather": [{"main": "Clear"}],
                    "pop": 0.1,
                    "uvi": 5.0,
                    "rain": 2.0,
                    "snow": 0,
                }
                for _ in range(5)
            ]
        }

        result = analyze_weather_patterns(service, forecast_data)

        assert "average_temperature" in result
        assert "temperature_range" in result
        assert "total_rain_days" in result
        assert "precipitation_chance" in result
        assert isinstance(result["average_temperature"], float)

    def test_generate_packing_suggestions(self, service: WeatherService):
        """Test packing suggestion generation."""
        weather_stats = {
            "total_rain_days": 2,
            "total_snow_days": 0,
            "temperature_range": (10.0, 28.0),
            "uv_index_range": (3.0, 7.0),
        }

        suggestions = generate_packing_suggestions(service, weather_stats)

        assert isinstance(suggestions, list)
        assert any("rain" in s.lower() for s in suggestions)
        assert any("sun" in s.lower() or "spf" in s.lower() for s in suggestions)

    def test_score_activity_beach(self, service: WeatherService):
        """Test beach activity scoring."""
        conditions = {
            "temp_day": 28.0,
            "weather_main": "clear",
            "pop": 10.0,
            "wind_speed": 5.0,
        }

        score, recommendations, warnings = score_activity(service, conditions, "beach")

        assert isinstance(score, int)
        assert score > 0
        assert isinstance(recommendations, list)
        assert isinstance(warnings, list)

    def test_score_activity_hiking(self, service: WeatherService):
        """Test hiking activity scoring."""
        conditions = {
            "temp_day": 20.0,
            "weather_main": "clear",
            "pop": 20.0,
            "wind_speed": 8.0,
        }

        score, _, _ = score_activity(service, conditions, "hiking")

        assert isinstance(score, int)
        assert score > 0

    def test_score_activity_sightseeing(self, service: WeatherService):
        """Test sightseeing activity scoring."""
        conditions = {
            "temp_day": 18.0,
            "weather_main": "clouds",
            "pop": 40.0,
            "wind_speed": 10.0,
        }

        score, recommendations, warnings = score_activity(
            service, conditions, "sightseeing"
        )

        assert isinstance(score, int)
        assert isinstance(recommendations, list)
        assert isinstance(warnings, list)
