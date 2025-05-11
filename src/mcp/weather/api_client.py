"""
Weather API client implementations for TripSage.

This module provides API client implementations for weather data providers.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, model_validator

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.error_handling import APIError
from ...utils.logging import get_module_logger

logger = get_module_logger(__name__)
config = get_config()


class WeatherLocation(BaseModel):
    """Location for weather API queries."""

    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None

    model_config = ConfigDict(extra="forbid", validate_default=True)

    @model_validator(mode="after")
    def validate_coordinates_or_city(self) -> "WeatherLocation":
        """Validate that either coordinates or city is provided."""
        if (self.lat is None or self.lon is None) and not self.city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        return self


class WeatherCondition(BaseModel):
    """Weather condition details."""

    id: int
    main: str
    description: str
    icon: str


class CurrentWeather(BaseModel):
    """Current weather data."""

    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    pressure: int
    wind_speed: float
    wind_direction: float
    clouds: int
    weather: WeatherCondition
    location: Dict[str, Any]
    timestamp: int
    source: str


class ForecastInterval(BaseModel):
    """Weather forecast for a specific time interval."""

    timestamp: int
    time: str
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    pressure: int
    wind_speed: float
    wind_direction: float
    clouds: int
    weather: WeatherCondition


class DailyForecast(BaseModel):
    """Daily weather forecast aggregation."""

    date: str
    temp_min: float
    temp_max: float
    temp_avg: float
    humidity_avg: float
    weather: WeatherCondition
    intervals: List[ForecastInterval]


class WeatherForecast(BaseModel):
    """Weather forecast data."""

    location: Dict[str, Any]
    daily: List[DailyForecast]
    source: str


class OpenWeatherMapClient:
    """Client for OpenWeatherMap API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenWeatherMap API client.

        Args:
            api_key: OpenWeatherMap API key (defaults to config value)
        """
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        logger.info("Initialized OpenWeatherMap API client")

    def _get_api_key(self) -> str:
        """Get API key from configuration or environment.

        Returns:
            API key

        Raises:
            ValueError: If API key is not configured
        """
        # Try to get from config object
        if hasattr(config, "weather_mcp") and hasattr(
            config.weather_mcp, "openweathermap_api_key"
        ):
            return config.weather_mcp.openweathermap_api_key

        # Try to get from environment variable
        api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
        if api_key:
            return api_key

        # If we get here, we don't have an API key
        raise ValueError(
            "OpenWeatherMap API key not found. "
            "Set it in the config or OPENWEATHERMAP_API_KEY environment variable."
        )

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a request to the OpenWeatherMap API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data

        Raises:
            APIError: If the API request fails
        """
        # Ensure API key is included
        params["appid"] = self.api_key
        # Use metric units
        params["units"] = "metric"

        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            error_info = {}
            try:
                error_info = e.response.json()
            except Exception:
                error_info = {"message": e.response.text}

            raise APIError(
                message=(
                    f"OpenWeatherMap API error: {e.response.status_code} - "
                    f"{error_info.get('message', '')}"
                ),
                service="OpenWeatherMap",
                status_code=e.response.status_code,
                response=e.response.text,
            ) from e

        except httpx.RequestError as e:
            raise APIError(
                message=f"OpenWeatherMap API request failed: {str(e)}",
                service="OpenWeatherMap",
            ) from e

        except Exception as e:
            raise APIError(
                message=f"OpenWeatherMap API unexpected error: {str(e)}",
                service="OpenWeatherMap",
            ) from e

    @redis_cache.cached("openweathermap_current", 1800)  # Cache for 30 minutes
    async def get_current_weather(self, location: WeatherLocation) -> CurrentWeather:
        """Get current weather conditions.

        Args:
            location: Location parameters

        Returns:
            Current weather data

        Raises:
            APIError: If the API request fails
        """
        params: Dict[str, Any] = {}

        if location.lat is not None and location.lon is not None:
            params["lat"] = location.lat
            params["lon"] = location.lon
        elif location.city:
            params["q"] = (
                location.city
                if not location.country
                else f"{location.city},{location.country}"
            )
        else:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        data = await self._make_request("weather", params)

        # Transform the data to a more usable format
        return CurrentWeather(
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            temp_min=data["main"]["temp_min"],
            temp_max=data["main"]["temp_max"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            wind_speed=data["wind"]["speed"],
            wind_direction=data["wind"]["deg"],
            clouds=data["clouds"]["all"],
            weather=WeatherCondition(
                id=data["weather"][0]["id"],
                main=data["weather"][0]["main"],
                description=data["weather"][0]["description"],
                icon=data["weather"][0]["icon"],
            ),
            location={
                "name": data["name"],
                "country": data["sys"]["country"],
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
                "timezone": data["timezone"],
            },
            timestamp=data["dt"],
            source="OpenWeatherMap",
        )

    @redis_cache.cached("openweathermap_forecast", 3600)  # Cache for 1 hour
    async def get_forecast(
        self, location: WeatherLocation, days: int = 5
    ) -> WeatherForecast:
        """Get weather forecast.

        Args:
            location: Location parameters
            days: Number of forecast days

        Returns:
            Weather forecast data

        Raises:
            APIError: If the API request fails
        """
        params: Dict[str, Any] = {}

        if location.lat is not None and location.lon is not None:
            params["lat"] = location.lat
            params["lon"] = location.lon
        elif location.city:
            params["q"] = (
                location.city
                if not location.country
                else f"{location.city},{location.country}"
            )
        else:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")

        # Limit to the number of days requested (API returns in 3-hour intervals)
        params["cnt"] = min(days * 8, 40)  # 8 intervals per day, max 40 (5 days)

        data = await self._make_request("forecast", params)

        # Group forecast by day
        forecasts_by_day: Dict[str, List[ForecastInterval]] = {}

        for item in data["list"]:
            # Convert timestamp to date string
            date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")

            if date not in forecasts_by_day:
                forecasts_by_day[date] = []

            interval = ForecastInterval(
                timestamp=item["dt"],
                time=datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                temperature=item["main"]["temp"],
                feels_like=item["main"]["feels_like"],
                temp_min=item["main"]["temp_min"],
                temp_max=item["main"]["temp_max"],
                humidity=item["main"]["humidity"],
                pressure=item["main"]["pressure"],
                wind_speed=item["wind"]["speed"],
                wind_direction=item["wind"]["deg"],
                clouds=item["clouds"]["all"],
                weather=WeatherCondition(
                    id=item["weather"][0]["id"],
                    main=item["weather"][0]["main"],
                    description=item["weather"][0]["description"],
                    icon=item["weather"][0]["icon"],
                ),
            )

            forecasts_by_day[date].append(interval)

        # Calculate daily aggregates
        daily_forecast = []

        for date, intervals in forecasts_by_day.items():
            # Calculate min, max, and average values
            temps = [interval.temperature for interval in intervals]
            humidity = [interval.humidity for interval in intervals]

            # Most common weather condition
            weather_conditions = [interval.weather.main for interval in intervals]
            most_common_condition = max(
                set(weather_conditions), key=weather_conditions.count
            )

            # Find the interval with the most common condition
            for interval in intervals:
                if interval.weather.main == most_common_condition:
                    representative_weather = interval.weather
                    break
            else:
                representative_weather = intervals[0].weather

            daily_forecast.append(
                DailyForecast(
                    date=date,
                    temp_min=min(temps),
                    temp_max=max(temps),
                    temp_avg=sum(temps) / len(temps),
                    humidity_avg=sum(humidity) / len(humidity),
                    weather=representative_weather,
                    intervals=intervals,
                )
            )

        return WeatherForecast(
            location={
                "name": data["city"]["name"],
                "country": data["city"]["country"],
                "lat": data["city"]["coord"]["lat"],
                "lon": data["city"]["coord"]["lon"],
                "timezone": data["city"]["timezone"],
            },
            daily=daily_forecast,
            source="OpenWeatherMap",
        )


def get_weather_api_client() -> OpenWeatherMapClient:
    """Get an OpenWeatherMap API client instance.

    Returns:
        OpenWeatherMapClient instance
    """
    return OpenWeatherMapClient()
