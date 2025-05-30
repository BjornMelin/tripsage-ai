"""Tests for OpenWeatherMap service implementation."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from tripsage.models.api.weather_models import (
    AirQualityIndex,
    WeatherUnits,
)
from tripsage_core.services.api.weather_service import OpenWeatherMapService


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.OPENWEATHERMAP_API_KEY = "test_api_key"
    return settings


@pytest.fixture
def mock_redis():
    """Mock Redis service."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest_asyncio.fixture
async def weather_service(mock_settings, mock_redis):
    """Create weather service instance for testing."""
    with patch("tripsage.services.api.weather_service.settings", mock_settings):
        service = OpenWeatherMapService()
        service.redis = mock_redis
        return service


@pytest.mark.asyncio
async def test_weather_service_context_manager(weather_service):
    """Test async context manager functionality."""
    async with weather_service as service:
        assert service is not None
        assert hasattr(service, "client")


class TestOpenWeatherMapService:
    """Test cases for OpenWeatherMap service."""

    @pytest.mark.asyncio
    async def test_init_with_api_key(self, mock_settings):
        """Test service initialization with API key."""
        with patch("tripsage.services.api.weather_service.settings", mock_settings):
            service = OpenWeatherMapService()
            assert service.api_key == "test_api_key"
            assert service.base_url == "https://api.openweathermap.org/data/2.5"
            assert service.base_url_v3 == "https://api.openweathermap.org/data/3.0"

    @pytest.mark.asyncio
    async def test_init_without_api_key(self):
        """Test service initialization without API key."""
        with patch("tripsage.services.api.weather_service.settings") as mock_settings:
            mock_settings.OPENWEATHERMAP_API_KEY = None
            with pytest.raises(
                ValueError, match="OPENWEATHERMAP_API_KEY not configured"
            ):
                OpenWeatherMapService()

    @pytest.mark.asyncio
    async def test_get_current_weather(self, weather_service, httpx_mock):
        """Test getting current weather conditions."""
        # Mock API response
        mock_response = {
            "coord": {"lon": -73.9352, "lat": 40.7306},
            "weather": [
                {
                    "id": 800,
                    "main": "Clear",
                    "description": "clear sky",
                    "icon": "01d",
                }
            ],
            "main": {
                "temp": 20.5,
                "feels_like": 19.8,
                "humidity": 65,
                "pressure": 1013,
            },
            "visibility": 10000,
            "wind": {"speed": 5.2, "deg": 180},
            "clouds": {"all": 0},
            "dt": 1640000000,
            "sys": {
                "country": "US",
                "sunrise": 1639990000,
                "sunset": 1640030000,
            },
            "timezone": -18000,
            "name": "New York",
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": "40.7306",
                    "lon": "-73.9352",
                    "units": "metric",
                    "lang": "en",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        weather = await weather_service.get_current_weather(
            latitude=40.7306,
            longitude=-73.9352,
        )

        assert weather.temperature == 20.5
        assert weather.feels_like == 19.8
        assert weather.humidity == 65
        assert weather.condition.main == "Clear"
        assert weather.location_name == "New York"
        assert weather.country == "US"

    @pytest.mark.asyncio
    async def test_get_current_weather_with_rain(self, weather_service, httpx_mock):
        """Test getting current weather with rain data."""
        mock_response = {
            "weather": [
                {"id": 500, "main": "Rain", "description": "light rain", "icon": "10d"}
            ],
            "main": {
                "temp": 15.0,
                "feels_like": 14.0,
                "humidity": 80,
                "pressure": 1010,
            },
            "wind": {"speed": 3.5, "deg": 90},
            "clouds": {"all": 75},
            "rain": {"1h": 0.5, "3h": 1.2},
            "dt": 1640000000,
            "sys": {"sunrise": 1639990000, "sunset": 1640030000},
            "visibility": 8000,
            "name": "London",
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": "51.5074",
                    "lon": "-0.1278",
                    "units": "metric",
                    "lang": "en",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        weather = await weather_service.get_current_weather(51.5074, -0.1278)

        assert weather.rain_1h == 0.5
        assert weather.rain_3h == 1.2
        assert weather.condition.main == "Rain"

    @pytest.mark.asyncio
    async def test_get_forecast(self, weather_service, httpx_mock):
        """Test getting weather forecast."""
        # Mock One Call API response
        mock_response = {
            "current": {
                "dt": 1640000000,
                "temp": 20.0,
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
            },
            "daily": [
                {
                    "dt": 1640000000,
                    "sunrise": 1639990000,
                    "sunset": 1640030000,
                    "moonrise": 1640010000,
                    "moonset": 1640050000,
                    "moon_phase": 0.5,
                    "temp": {
                        "min": 15.0,
                        "max": 25.0,
                        "morn": 16.0,
                        "day": 22.0,
                        "eve": 20.0,
                        "night": 17.0,
                    },
                    "feels_like": {
                        "morn": 15.0,
                        "day": 21.0,
                        "eve": 19.0,
                        "night": 16.0,
                    },
                    "humidity": 60,
                    "pressure": 1015,
                    "wind_speed": 5.0,
                    "wind_deg": 180,
                    "clouds": 20,
                    "pop": 0.1,
                    "uvi": 6.5,
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                },
                {
                    "dt": 1640086400,
                    "sunrise": 1640076400,
                    "sunset": 1640116400,
                    "moonrise": 1640096400,
                    "moonset": 1640136400,
                    "moon_phase": 0.55,
                    "temp": {
                        "min": 14.0,
                        "max": 23.0,
                        "morn": 15.0,
                        "day": 21.0,
                        "eve": 19.0,
                        "night": 16.0,
                    },
                    "feels_like": {
                        "morn": 14.0,
                        "day": 20.0,
                        "eve": 18.0,
                        "night": 15.0,
                    },
                    "humidity": 65,
                    "pressure": 1013,
                    "wind_speed": 6.0,
                    "wind_deg": 200,
                    "clouds": 40,
                    "pop": 0.3,
                    "rain": 2.5,
                    "uvi": 5.0,
                    "weather": [
                        {
                            "id": 500,
                            "main": "Rain",
                            "description": "light rain",
                            "icon": "10d",
                        }
                    ],
                },
            ],
            "hourly": [
                {
                    "dt": 1640000000,
                    "temp": 20.0,
                    "feels_like": 19.0,
                    "humidity": 60,
                    "pressure": 1015,
                    "visibility": 10000,
                    "wind_speed": 5.0,
                    "wind_deg": 180,
                    "clouds": 20,
                    "pop": 0.1,
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                },
            ],
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={
                    "lat": "40.7306",
                    "lon": "-73.9352",
                    "units": "metric",
                    "lang": "en",
                    "exclude": "minutely,alerts",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        daily_forecasts, hourly_forecasts = await weather_service.get_forecast(
            latitude=40.7306,
            longitude=-73.9352,
            days=2,
            include_hourly=True,
        )

        # Check daily forecasts
        assert len(daily_forecasts) == 2
        assert daily_forecasts[0].temp_min == 15.0
        assert daily_forecasts[0].temp_max == 25.0
        assert daily_forecasts[0].condition.main == "Clear"
        assert daily_forecasts[0].uvi == 6.5

        assert daily_forecasts[1].rain == 2.5
        assert daily_forecasts[1].precipitation_probability == 30.0  # 0.3 * 100

        # Check hourly forecasts
        assert len(hourly_forecasts) == 1
        assert hourly_forecasts[0].temperature == 20.0

    @pytest.mark.asyncio
    async def test_get_air_quality(self, weather_service, httpx_mock):
        """Test getting air quality data."""
        mock_response = {
            "list": [
                {
                    "dt": 1640000000,
                    "main": {"aqi": 2},
                    "components": {
                        "co": 201.94,
                        "no": 0.01,
                        "no2": 0.77,
                        "o3": 75.1,
                        "so2": 0.64,
                        "pm2_5": 10.5,
                        "pm10": 15.2,
                        "nh3": 0.74,
                    },
                }
            ]
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={
                    "lat": "40.7306",
                    "lon": "-73.9352",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        air_quality = await weather_service.get_air_quality(40.7306, -73.9352)

        assert air_quality.aqi == AirQualityIndex(2)
        assert air_quality.pm2_5 == 10.5
        assert air_quality.pm10 == 15.2
        assert air_quality.o3 == 75.1

    @pytest.mark.asyncio
    async def test_get_weather_alerts(self, weather_service, httpx_mock):
        """Test getting weather alerts."""
        mock_response = {
            "alerts": [
                {
                    "sender_name": "NWS",
                    "event": "Thunderstorm Warning",
                    "start": 1640000000,
                    "end": 1640010000,
                    "description": "Severe thunderstorms expected",
                    "tags": ["extreme weather", "thunderstorm"],
                },
                {
                    "sender_name": "NWS",
                    "event": "Heat Advisory",
                    "start": 1640086400,
                    "end": 1640172800,
                    "description": "High temperatures expected",
                    "tags": ["heat"],
                },
            ]
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={
                    "lat": "40.7306",
                    "lon": "-73.9352",
                    "exclude": "current,minutely,hourly,daily",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        alerts = await weather_service.get_weather_alerts(40.7306, -73.9352)

        assert len(alerts) == 2
        assert alerts[0].event == "Thunderstorm Warning"
        assert alerts[0].sender_name == "NWS"
        assert alerts[1].event == "Heat Advisory"

    @pytest.mark.asyncio
    async def test_get_uv_index(self, weather_service, httpx_mock):
        """Test getting UV index data."""
        mock_response = {
            "value": 7.5,
            "date": 1640000000,
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/uvi/current",
                params={
                    "lat": "40.7306",
                    "lon": "-73.9352",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        uv_index = await weather_service.get_uv_index(40.7306, -73.9352)

        assert uv_index.value == 7.5
        assert isinstance(uv_index.dt, datetime)

    @pytest.mark.asyncio
    async def test_get_travel_weather_summary(self, weather_service, httpx_mock):
        """Test getting comprehensive travel weather summary."""
        # Mock forecast response
        forecast_response = {
            "daily": [
                {
                    "dt": 1640000000,
                    "sunrise": 1639990000,
                    "sunset": 1640030000,
                    "moonrise": 1640010000,
                    "moonset": 1640050000,
                    "moon_phase": 0.5,
                    "temp": {
                        "min": 20.0,
                        "max": 30.0,
                        "morn": 22.0,
                        "day": 28.0,
                        "eve": 25.0,
                        "night": 21.0,
                    },
                    "feels_like": {
                        "morn": 21.0,
                        "day": 27.0,
                        "eve": 24.0,
                        "night": 20.0,
                    },
                    "humidity": 45,
                    "pressure": 1015,
                    "wind_speed": 8.0,
                    "clouds": 10,
                    "pop": 0.05,
                    "uvi": 8.0,
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                },
                {
                    "dt": 1640086400,
                    "sunrise": 1640076400,
                    "sunset": 1640116400,
                    "moonrise": 1640096400,
                    "moonset": 1640136400,
                    "moon_phase": 0.55,
                    "temp": {
                        "min": 18.0,
                        "max": 25.0,
                        "morn": 19.0,
                        "day": 23.0,
                        "eve": 21.0,
                        "night": 18.0,
                    },
                    "feels_like": {
                        "morn": 18.0,
                        "day": 22.0,
                        "eve": 20.0,
                        "night": 17.0,
                    },
                    "humidity": 70,
                    "pressure": 1012,
                    "wind_speed": 12.0,
                    "clouds": 60,
                    "pop": 0.4,
                    "rain": 5.0,
                    "uvi": 4.0,
                    "weather": [
                        {
                            "id": 500,
                            "main": "Rain",
                            "description": "light rain",
                            "icon": "10d",
                        }
                    ],
                },
            ],
            "hourly": [],
        }

        # Mock air quality response
        air_quality_response = {
            "list": [
                {
                    "dt": 1640000000,
                    "main": {"aqi": 2},
                    "components": {
                        "co": 201.94,
                        "no": 0.01,
                        "no2": 0.77,
                        "o3": 75.1,
                        "so2": 0.64,
                        "pm2_5": 10.5,
                        "pm10": 15.2,
                        "nh3": 0.74,
                    },
                }
            ]
        }

        # Mock weather alerts response
        alerts_response = {"alerts": []}

        # Set up mock responses
        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={
                    "lat": "25.0343",
                    "lon": "-77.3963",
                    "units": "metric",
                    "lang": "en",
                    "exclude": "minutely,alerts",
                    "appid": "test_api_key",
                },
            ),
            json=forecast_response,
        )

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={
                    "lat": "25.0343",
                    "lon": "-77.3963",
                    "appid": "test_api_key",
                },
            ),
            json=air_quality_response,
        )

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={
                    "lat": "25.0343",
                    "lon": "-77.3963",
                    "exclude": "current,minutely,hourly,daily",
                    "appid": "test_api_key",
                },
            ),
            json=alerts_response,
        )

        summary = await weather_service.get_travel_weather_summary(
            latitude=25.0343,
            longitude=-77.3963,
            arrival_date=datetime.now(),
            departure_date=datetime.now() + timedelta(days=2),
            activities=["beach", "swimming"],
        )

        # Check summary data
        assert summary.average_temperature == 23.0  # (20+30+18+25)/4
        assert summary.temperature_range == (18.0, 30.0)
        assert summary.total_rain_days == 1
        assert summary.total_clear_days == 1
        assert summary.air_quality_forecast == "Fair"
        assert summary.uv_index_range == (4.0, 8.0)

        # Check recommendations
        assert any(
            "Good weather expected" in rec for rec in summary.activity_recommendations
        )
        assert any("SPF" in sug for sug in summary.packing_suggestions)

    @pytest.mark.asyncio
    async def test_get_multi_city_weather(self, weather_service, httpx_mock):
        """Test getting weather for multiple cities."""
        cities = [
            (40.7306, -73.9352, "New York"),
            (51.5074, -0.1278, "London"),
            (35.6762, 139.6503, "Tokyo"),
        ]

        # Mock responses for each city
        responses = [
            {
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
                "main": {
                    "temp": 20.0,
                    "feels_like": 19.0,
                    "humidity": 60,
                    "pressure": 1015,
                },
                "wind": {"speed": 5.0, "deg": 180},
                "clouds": {"all": 10},
                "dt": 1640000000,
                "sys": {"sunrise": 1639990000, "sunset": 1640030000},
                "visibility": 10000,
                "name": "New York",
            },
            {
                "weather": [
                    {
                        "id": 803,
                        "main": "Clouds",
                        "description": "broken clouds",
                        "icon": "04d",
                    }
                ],
                "main": {
                    "temp": 12.0,
                    "feels_like": 11.0,
                    "humidity": 75,
                    "pressure": 1010,
                },
                "wind": {"speed": 7.0, "deg": 270},
                "clouds": {"all": 70},
                "dt": 1640000000,
                "sys": {"sunrise": 1639990000, "sunset": 1640030000},
                "visibility": 8000,
                "name": "London",
            },
            {
                "weather": [
                    {
                        "id": 500,
                        "main": "Rain",
                        "description": "light rain",
                        "icon": "10n",
                    }
                ],
                "main": {
                    "temp": 8.0,
                    "feels_like": 6.0,
                    "humidity": 85,
                    "pressure": 1008,
                },
                "wind": {"speed": 9.0, "deg": 90},
                "clouds": {"all": 90},
                "rain": {"1h": 0.8},
                "dt": 1640000000,
                "sys": {"sunrise": 1639990000, "sunset": 1640030000},
                "visibility": 6000,
                "name": "Tokyo",
            },
        ]

        for i, (lat, lon, _name) in enumerate(cities):
            httpx_mock.add_response(
                url=httpx.URL(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "lat": str(lat),
                        "lon": str(lon),
                        "units": "metric",
                        "lang": "en",
                        "appid": "test_api_key",
                    },
                ),
                json=responses[i],
            )

        weather_data = await weather_service.get_multi_city_weather(cities)

        assert len(weather_data) == 3
        assert weather_data["New York"].temperature == 20.0
        assert weather_data["London"].temperature == 12.0
        assert weather_data["Tokyo"].temperature == 8.0
        assert weather_data["Tokyo"].rain_1h == 0.8

    @pytest.mark.asyncio
    async def test_check_travel_weather_conditions_beach(
        self, weather_service, httpx_mock
    ):
        """Test checking weather suitability for beach activities."""
        # Mock good beach weather
        mock_response = {
            "daily": [
                {
                    "dt": 1640000000,
                    "sunrise": 1639990000,
                    "sunset": 1640030000,
                    "moonrise": 1640010000,
                    "moonset": 1640050000,
                    "moon_phase": 0.5,
                    "temp": {
                        "min": 24.0,
                        "max": 32.0,
                        "morn": 25.0,
                        "day": 30.0,
                        "eve": 28.0,
                        "night": 25.0,
                    },
                    "feels_like": {
                        "morn": 24.0,
                        "day": 29.0,
                        "eve": 27.0,
                        "night": 24.0,
                    },
                    "humidity": 60,
                    "pressure": 1015,
                    "wind_speed": 15.0,
                    "clouds": 20,
                    "pop": 0.1,
                    "uvi": 9.0,
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                },
            ],
            "hourly": [],
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={
                    "lat": "25.0343",
                    "lon": "-77.3963",
                    "units": "metric",
                    "lang": "en",
                    "exclude": "minutely,hourly,alerts",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        result = await weather_service.check_travel_weather_conditions(
            latitude=25.0343,
            longitude=-77.3963,
            travel_date=datetime.now() + timedelta(hours=12),
            activity_type="beach",
        )

        assert result["suitable"] is True
        assert result["score"] > 60
        assert result["temperature"] == 30.0
        assert result["condition"] == "clear sky"
        assert result["precipitation_chance"] == 10.0

    @pytest.mark.asyncio
    async def test_check_travel_weather_conditions_hiking(
        self, weather_service, httpx_mock
    ):
        """Test checking weather suitability for hiking activities."""
        # Mock moderate hiking weather
        mock_response = {
            "daily": [
                {
                    "dt": 1640000000,
                    "sunrise": 1639990000,
                    "sunset": 1640030000,
                    "moonrise": 1640010000,
                    "moonset": 1640050000,
                    "moon_phase": 0.5,
                    "temp": {
                        "min": 12.0,
                        "max": 22.0,
                        "morn": 14.0,
                        "day": 20.0,
                        "eve": 18.0,
                        "night": 15.0,
                    },
                    "feels_like": {
                        "morn": 13.0,
                        "day": 19.0,
                        "eve": 17.0,
                        "night": 14.0,
                    },
                    "humidity": 55,
                    "pressure": 1018,
                    "wind_speed": 10.0,
                    "clouds": 30,
                    "pop": 0.2,
                    "uvi": 5.0,
                    "weather": [
                        {
                            "id": 802,
                            "main": "Clouds",
                            "description": "scattered clouds",
                            "icon": "03d",
                        }
                    ],
                },
            ],
            "hourly": [],
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/3.0/onecall",
                params={
                    "lat": "39.7392",
                    "lon": "-104.9903",
                    "units": "metric",
                    "lang": "en",
                    "exclude": "minutely,hourly,alerts",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        result = await weather_service.check_travel_weather_conditions(
            latitude=39.7392,
            longitude=-104.9903,
            travel_date=datetime.now() + timedelta(hours=12),
            activity_type="hiking",
        )

        assert result["suitable"] is True
        assert result["score"] > 60
        assert result["temperature"] == 20.0
        assert result["condition"] == "scattered clouds"
        assert result["precipitation_chance"] == 20.0

    @pytest.mark.asyncio
    async def test_error_handling(self, weather_service, httpx_mock):
        """Test error handling for API failures."""
        # Test 401 unauthorized error
        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": "40.0",
                    "lon": "-74.0",
                    "units": "metric",
                    "lang": "en",
                    "appid": "test_api_key",
                },
            ),
            status_code=401,
            json={
                "cod": 401,
                "message": (
                    "Invalid API key. Please see "
                    "https://openweathermap.org/faq#error401 for more info."
                ),
            },
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await weather_service.get_current_weather(40.0, -74.0)

        assert exc_info.value.response.status_code == 401

    @pytest.mark.asyncio
    async def test_caching_behavior(self, weather_service, mock_redis, httpx_mock):
        """Test caching for weather data."""
        mock_response = {
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "main": {
                "temp": 25.0,
                "feels_like": 24.0,
                "humidity": 50,
                "pressure": 1013,
            },
            "wind": {"speed": 5.0, "deg": 180},
            "clouds": {"all": 0},
            "dt": 1640000000,
            "sys": {"sunrise": 1639990000, "sunset": 1640030000},
            "visibility": 10000,
            "name": "Test City",
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": "30.0",
                    "lon": "-90.0",
                    "units": "metric",
                    "lang": "en",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        # First call should hit the API
        weather1 = await weather_service.get_current_weather(30.0, -90.0)

        # Check that cache was set
        mock_redis.set.assert_called()

        # Set up cache to return data
        mock_redis.get.return_value = json.dumps(weather1.model_dump())

        # Clear httpx mock to ensure no more requests
        httpx_mock.reset()

        # Second call should use cache
        weather2 = await weather_service.get_current_weather(30.0, -90.0)

        # Should get same results from cache
        assert weather2.temperature == weather1.temperature
        assert weather2.location_name == weather1.location_name

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, weather_service, httpx_mock):
        """Test retry mechanism for failed requests."""
        url = httpx.URL(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": "40.0",
                "lon": "-74.0",
                "units": "metric",
                "lang": "en",
                "appid": "test_api_key",
            },
        )

        # First two attempts fail, third succeeds
        httpx_mock.add_response(url=url, status_code=500)
        httpx_mock.add_response(url=url, status_code=500)
        httpx_mock.add_response(
            url=url,
            json={
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
                "main": {
                    "temp": 20.0,
                    "feels_like": 19.0,
                    "humidity": 60,
                    "pressure": 1015,
                },
                "wind": {"speed": 5.0},
                "clouds": {"all": 10},
                "dt": 1640000000,
                "sys": {"sunrise": 1639990000, "sunset": 1640030000},
                "visibility": 10000,
                "name": "Success City",
            },
        )

        # Should succeed after retries
        weather = await weather_service.get_current_weather(40.0, -74.0)
        assert weather.location_name == "Success City"

    @pytest.mark.asyncio
    async def test_unit_conversion(self, weather_service, httpx_mock):
        """Test different unit systems."""
        # Test imperial units
        mock_response = {
            "weather": [
                {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
            ],
            "main": {
                "temp": 68.0,
                "feels_like": 66.0,
                "humidity": 50,
                "pressure": 1013,
            },
            "wind": {"speed": 11.2},  # mph
            "clouds": {"all": 0},
            "dt": 1640000000,
            "sys": {"sunrise": 1639990000, "sunset": 1640030000},
            "visibility": 10000,
            "name": "Imperial City",
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": "40.0",
                    "lon": "-74.0",
                    "units": "imperial",
                    "lang": "en",
                    "appid": "test_api_key",
                },
            ),
            json=mock_response,
        )

        weather = await weather_service.get_current_weather(
            40.0, -74.0, units=WeatherUnits.imperial
        )

        assert weather.temperature == 68.0  # Fahrenheit
        assert weather.wind_speed == 11.2  # mph

    @pytest.mark.asyncio
    async def test_future_date_error(self, weather_service):
        """Test error when checking weather for dates beyond forecast range."""
        result = await weather_service.check_travel_weather_conditions(
            latitude=40.0,
            longitude=-74.0,
            travel_date=datetime.now() + timedelta(days=10),
            activity_type="hiking",
        )

        assert result["suitable"] is None
        assert result["score"] == 0
        assert "beyond 7 days" in result["message"]

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, weather_service, httpx_mock):
        """Test handling of concurrent requests."""
        import asyncio

        # Mock multiple different city responses
        cities = [
            (40.7128, -74.0060, "NYC"),
            (34.0522, -118.2437, "LA"),
            (41.8781, -87.6298, "Chicago"),
            (25.7617, -80.1918, "Miami"),
            (47.6062, -122.3321, "Seattle"),
        ]

        for lat, lon, name in cities:
            httpx_mock.add_response(
                url=httpx.URL(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "lat": str(lat),
                        "lon": str(lon),
                        "units": "metric",
                        "lang": "en",
                        "appid": "test_api_key",
                    },
                ),
                json={
                    "weather": [
                        {
                            "id": 800,
                            "main": "Clear",
                            "description": "clear sky",
                            "icon": "01d",
                        }
                    ],
                    "main": {
                        "temp": 20.0 + lat / 10,
                        "feels_like": 19.0,
                        "humidity": 60,
                        "pressure": 1015,
                    },
                    "wind": {"speed": 5.0},
                    "clouds": {"all": 10},
                    "dt": 1640000000,
                    "sys": {"sunrise": 1639990000, "sunset": 1640030000},
                    "visibility": 10000,
                    "name": name,
                },
            )

        # Make concurrent requests
        tasks = [
            weather_service.get_current_weather(lat, lon) for lat, lon, _ in cities
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, weather in enumerate(results):
            assert weather.location_name == cities[i][2]
