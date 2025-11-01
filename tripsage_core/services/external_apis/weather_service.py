"""OpenWeatherMap API service implementation with TripSage Core integration.

This module provides direct integration with the OpenWeatherMap API for weather
forecasts, current conditions, and travel-specific weather analysis.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from types import TracebackType
from typing import Any, cast

import httpx

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
    CoreServiceError,
)
from tripsage_core.services.external_apis.base_service import sanitize_response
from tripsage_core.utils.outbound import request_with_backoff


logger = logging.getLogger(__name__)


# Safe extraction helpers to reduce boilerplate
def _safe_float(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    """Safely extract float from dict."""
    val = data.get(key, default)
    return float(val) if isinstance(val, (int, float)) else default


def _safe_str(data: dict[str, Any], key: str, default: str = "") -> str:
    """Safely extract string from dict."""
    val = data.get(key, default)
    return str(val) if val is not None else default


def _safe_dict(data: Any, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Safely cast to dict."""
    return cast(dict[str, Any], data) if isinstance(data, dict) else (default or {})


def _safe_list(data: Any, default: list[Any] | None = None) -> list[Any]:
    """Safely cast to list."""
    return cast(list[Any], data) if isinstance(data, list) else (default or [])


class WeatherServiceError(CoreAPIError):
    """Exception raised for weather service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize the WeatherServiceError."""
        super().__init__(
            message=message,
            code="WEATHER_API_ERROR",
            api_service="WeatherService",
            details={
                "additional_context": {
                    "original_error": str(original_error) if original_error else None
                }
            },
        )
        self.original_error = original_error


ScoreHandler = Callable[[dict[str, Any]], tuple[int, list[str], list[str]]]
ActivitySummaryEvaluator = Callable[
    [str, dict[str, Any], int], tuple[str | None, str | None]
]


class WeatherService:
    """Service for interacting with OpenWeatherMap API."""

    def __init__(self, settings: Settings | None = None):
        """Initialize the OpenWeatherMap service.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.base_url_v3 = "https://api.openweathermap.org/data/3.0"

        # Get API key (optional for tests that mock client calls)
        # Prefer explicit alias if provided; treat explicit None as missing
        _alias_sentinel = object()
        alias_val = getattr(self.settings, "openweather_api_key", _alias_sentinel)
        if alias_val is None:
            self.api_key: str | None = None
        elif alias_val is not _alias_sentinel:
            try:
                # Pydantic SecretStr exposes get_secret_value()
                self.api_key = alias_val.get_secret_value()  # type: ignore[attr-defined]
            except AttributeError:
                self.api_key = str(alias_val)
        else:
            weather_key = getattr(self.settings, "openweathermap_api_key", None)
            self.api_key = (
                weather_key.get_secret_value() if weather_key is not None else None
            )
        self._client: Any | None = None
        self._connected = False

    # Back-compat property expected by some tests/callers
    @property
    def client(self) -> Any:
        """Get or create a configured HTTP client."""
        if not self._client:
            # Lazily initialize a minimal client; connect() sets headers/timeouts
            self._client = httpx.AsyncClient()
            self._connected = True
        return self._client

    @client.setter
    def client(self, value: Any) -> None:  # pragma: no cover - test utility
        """Set the HTTP client."""
        self._client = value
        self._connected = value is not None

    async def connect(self) -> None:
        """Initialize HTTP client."""
        if self._connected:
            return

        try:
            self._client = httpx.AsyncClient(
                headers={
                    "Accept": "application/json",
                    "User-Agent": "TripSage-Core/1.0",
                },
                timeout=15.0,
            )
            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to connect to OpenWeatherMap API: {e!s}",
                code="CONNECTION_FAILED",
                service="WeatherService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            try:
                await self._client.aclose()
            except CoreServiceError as close_error:
                logger.warning(
                    "Error closing weather service HTTP client: %s", close_error
                )
            finally:
                self._client = None
                self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    def _build_location_params(
        self,
        latitude: float,
        longitude: float,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Assemble latitude/longitude params with optional extras."""
        params = {"lat": latitude, "lon": longitude}
        if extra_params:
            params.update(extra_params)
        return params

    async def _request_onecall(
        self,
        latitude: float,
        longitude: float,
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a One Call API request with shared coordinate params."""
        params = self._build_location_params(latitude, longitude, extra_params)
        return await self._make_request("onecall", params, use_v3=True)

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        use_v3: bool = False,
    ) -> dict[str, Any]:
        """Make a request to the OpenWeatherMap API.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_v3: Use v3 API endpoint

        Returns:
            API response data

        Raises:
            WeatherServiceError: If the request fails
        """
        await self.ensure_connected()
        assert self._client is not None

        base_url = self.base_url_v3 if use_v3 else self.base_url
        url = f"{base_url}/{endpoint}"

        # Add API key to params
        if params is None:
            params = {}
        params["appid"] = self.api_key

        try:
            resp = await request_with_backoff(self._client, "GET", url, params=params)
            resp.raise_for_status()
            body_any = sanitize_response(resp.content)
            return body_any if isinstance(body_any, dict) else {}
        except httpx.HTTPStatusError as e:
            error_data: dict[str, Any] = {}
            try:
                if e.response and e.response.content:
                    any_err = sanitize_response(e.response.content)
                    error_data = any_err if isinstance(any_err, dict) else {}
                else:
                    error_data = {}
            except ValueError as parse_error:  # pragma: no cover - debug only
                logger.debug(
                    "Failed to parse weather API error response: %s", parse_error
                )
            raise WeatherServiceError(
                (f"OpenWeatherMap API error: {error_data.get('message', str(e))}"),
                original_error=e,
            ) from e

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        units: str = "metric",
        lang: str = "en",
    ) -> dict[str, Any]:
        """Get current weather conditions.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            units: Temperature units (metric, imperial, kelvin)
            lang: Language code

        Returns:
            Current weather data from OpenWeatherMap API
        """
        params = {"lat": latitude, "lon": longitude, "units": units, "lang": lang}
        return await self._make_request("weather", params)

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        *,
        days: int = 7,
        include_hourly: bool = True,
        units: str = "metric",
        lang: str = "en",
    ) -> dict[str, Any]:
        """Get weather forecast.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast (max 7)
            include_hourly: Include hourly forecast
            units: Temperature units (metric, imperial, kelvin)
            lang: Language code

        Returns:
            Weather forecast data from OpenWeatherMap OneCall API
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "units": units,
            "lang": lang,
            "exclude": (
                "minutely,alerts" if include_hourly else "minutely,hourly,alerts"
            ),
        }
        return await self._make_request("onecall", params, use_v3=True)

    async def get_air_quality(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        """Get air quality data.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Air pollution data from OpenWeatherMap API
        """
        params = {"lat": latitude, "lon": longitude}
        return await self._make_request("air_pollution", params)

    async def get_weather_alerts(
        self,
        latitude: float,
        longitude: float,
    ) -> list[dict[str, Any]]:
        """Get weather alerts for a location.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            List of weather alerts
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "exclude": "current,minutely,hourly,daily",
        }

        data = await self._make_request("onecall", params, use_v3=True)
        return data.get("alerts", [])

    async def get_uv_index(
        self,
        latitude: float,
        longitude: float,
        dt: datetime | None = None,
    ) -> dict[str, Any]:
        """Get UV index data.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            dt: Date/time for UV index (current if None)

        Returns:
            UV index data
        """
        endpoint = "uvi" if dt else "uvi/current"
        params = {"lat": latitude, "lon": longitude}

        if dt:
            params["dt"] = int(dt.timestamp())

        return await self._make_request(endpoint, params)

    async def get_travel_weather_summary(
        self,
        latitude: float,
        longitude: float,
        arrival_date: datetime,
        departure_date: datetime,
        *,
        activities: list[str] | None = None,
        units: str = "metric",
    ) -> dict[str, Any]:
        """Get weather summary for travel planning.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            arrival_date: Trip arrival date
            departure_date: Trip departure date
            activities: List of planned activities
            units: Temperature units (metric, imperial, kelvin)

        Returns:
            Comprehensive weather analysis with recommendations and warnings
        """
        trip_duration = (departure_date - arrival_date).days + 1
        weather_data = await self._gather_travel_weather_data(
            float(latitude), float(longitude), int(trip_duration), str(units)
        )
        weather_stats = self._analyze_weather_patterns(weather_data["forecast_data"])
        activity_info = self._generate_activity_recommendations(
            activities, weather_stats, trip_duration
        )
        packing_suggestions = self._generate_packing_suggestions(weather_stats)
        return {
            **weather_stats,
            **activity_info,
            "packing_suggestions": packing_suggestions,
            "air_quality_forecast": weather_data["air_quality_aqi"],
            "alerts": weather_data["alerts"],
            "forecast_data": weather_data["forecast_data"],
        }

    async def _gather_travel_weather_data(
        self, latitude: float, longitude: float, trip_duration: int, units: str
    ) -> dict[str, Any]:
        """Gather all required weather data for travel summary."""
        forecast_data = await self.get_forecast(
            latitude=latitude,
            longitude=longitude,
            days=min(trip_duration, 7),
            include_hourly=True,
            units=units,
        )

        air_quality_data = await self.get_air_quality(latitude, longitude)
        alerts = await self.get_weather_alerts(latitude, longitude)

        return {
            "forecast_data": forecast_data,
            "air_quality_aqi": (
                air_quality_data.get("list", [{}])[0].get("main", {}).get("aqi", 0)
            ),
            "alerts": alerts,
        }

    def _analyze_weather_patterns(
        self, forecast_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze weather patterns from forecast data."""
        daily_forecasts = _safe_list(forecast_data.get("daily", []))
        temps: list[float] = []
        rain_days = snow_days = clear_days = 0
        uv_min = uv_max = pop_sum = 0.0

        forecast_dicts: list[dict[str, Any]] = [
            f for f in daily_forecasts if isinstance(f, dict)
        ]
        for forecast in forecast_dicts:
            fc = _safe_dict(forecast)
            temp_data = _safe_dict(fc.get("temp"))

            # Collect temperatures
            if (tmin := _safe_float(temp_data, "min")) > 0:
                temps.append(tmin)
            if (tmax := _safe_float(temp_data, "max")) > 0:
                temps.append(tmax)

            # Count conditions
            rain_days += 1 if _safe_float(fc, "rain") > 0 else 0
            snow_days += 1 if _safe_float(fc, "snow") > 0 else 0

            # Check weather main
            wx_list = _safe_list(fc.get("weather", []))
            if wx_list and isinstance(wx_list[0], dict):
                weather_main = _safe_str(_safe_dict(wx_list[0]), "main").lower()
                clear_days += 1 if weather_main in ["clear", "sunny"] else 0

            # Track UV range
            if (uvi := _safe_float(fc, "uvi")) > 0:
                uv_min = min(uv_min, uvi) if uv_min else uvi
                uv_max = max(uv_max, uvi)

            # Sum precipitation probability
            pop_sum += _safe_float(fc, "pop")

        avg_temp = sum(temps) / len(temps) if temps else 0.0
        temp_range = (min(temps), max(temps)) if temps else (0.0, 0.0)
        precip_chance = (
            (pop_sum / len(daily_forecasts) * 100.0) if daily_forecasts else 0.0
        )

        return {
            "average_temperature": avg_temp,
            "temperature_range": temp_range,
            "total_rain_days": rain_days,
            "total_snow_days": snow_days,
            "total_clear_days": clear_days,
            "precipitation_chance": precip_chance,
            "uv_index_range": (uv_min, uv_max),
        }

    def _generate_activity_recommendations(
        self,
        activities: list[str] | None,
        weather_stats: dict[str, Any],
        trip_duration: int,
    ) -> dict[str, list[str]]:
        """Generate activity recommendations and warnings."""
        recommendations: list[str] = []
        warnings: list[str] = []

        if not activities:
            return {
                "activity_recommendations": recommendations,
                "weather_warnings": warnings,
            }

        avg_temp = weather_stats["average_temperature"]
        rain_days = weather_stats["total_rain_days"]
        snow_days = weather_stats["total_snow_days"]

        for activity in activities:
            activity_lower = activity.lower()

            # Beach activities
            if "beach" in activity_lower or "swimming" in activity_lower:
                if avg_temp < 20:
                    warnings.append(
                        f"Cool temperatures for {activity} (avg {avg_temp:.1f}°)"
                    )
                elif rain_days > trip_duration * 0.3:
                    warnings.append(f"Frequent rain may affect {activity}")
                else:
                    recommendations.append(f"Good weather expected for {activity}")

            # Hiking/outdoor activities
            elif "hiking" in activity_lower or "outdoor" in activity_lower:
                if rain_days > trip_duration * 0.5:
                    warnings.append(f"Pack rain gear for {activity}")
                elif avg_temp > 30:
                    warnings.append(
                        f"High temperatures - plan {activity} for early morning"
                    )
                else:
                    recommendations.append(f"Pleasant conditions for {activity}")

            # Snow activities
            elif "skiing" in activity_lower or "snow" in activity_lower:
                if snow_days == 0:
                    warnings.append(f"No snow forecast for {activity}")
                else:
                    recommendations.append(f"Snow conditions expected for {activity}")

        return {
            "activity_recommendations": recommendations,
            "weather_warnings": warnings,
        }

    def _generate_packing_suggestions(self, weather_stats: dict[str, Any]) -> list[str]:
        """Generate packing suggestions based on weather."""
        suggestions: list[str] = []

        rain_days = weather_stats["total_rain_days"]
        snow_days = weather_stats["total_snow_days"]
        temp_range = weather_stats["temperature_range"]
        uv_range = weather_stats["uv_index_range"]

        if rain_days > 0:
            suggestions.append("Rain jacket or umbrella")
        if snow_days > 0:
            suggestions.append("Warm clothing and snow gear")
        if temp_range[1] > 25:
            suggestions.append("Sun protection (hat, sunscreen)")
        if temp_range[0] < 10:
            suggestions.append("Warm layers for cool evenings")
        if uv_range[1] > 6:
            suggestions.append("High SPF sunscreen")

        return suggestions

    async def get_multi_city_weather(
        self,
        cities: list[tuple[float, float, str]],
        date: datetime | None = None,
        units: str = "metric",
    ) -> dict[str, dict[str, Any]]:
        """Get weather for multiple cities (useful for trip planning).

        Args:
            cities: List of (latitude, longitude, name) tuples
            date: Date for weather (current if None)
            units: Temperature units

        Returns:
            Dictionary mapping city names to weather data
        """
        if date and date > datetime.now():
            # Future date - use forecast
            tasks: list[asyncio.Task[dict[str, Any]]] = []
            for lat, lon, _name in cities:
                tasks.append(
                    asyncio.create_task(
                        self.get_forecast(
                            lat, lon, days=1, include_hourly=False, units=units
                        )
                    )
                )
        else:
            # Current weather
            tasks = []
            for lat, lon, _name in cities:
                tasks.append(
                    asyncio.create_task(self.get_current_weather(lat, lon, units))
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        weather_data: dict[str, dict[str, Any]] = {}
        for (_lat, _lon, name), result in zip(cities, results, strict=False):
            if isinstance(result, Exception):
                continue
            weather_data[name] = cast(dict[str, Any], result)

        return weather_data

    async def check_travel_weather_conditions(
        self,
        latitude: float,
        longitude: float,
        travel_date: datetime,
        activity_type: str,
    ) -> dict[str, Any]:
        """Check if weather conditions are suitable for specific activities.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            travel_date: Date of travel
            activity_type: Type of activity (beach, hiking, sightseeing, etc.)

        Returns:
            Dictionary with suitability score and recommendations
        """
        # Validate date range
        days_ahead = (travel_date - datetime.now()).days
        if days_ahead > 7:
            return {
                "suitable": None,
                "score": 0,
                "message": "Weather forecast not available for dates beyond 7 days",
            }

        # Get target forecast
        target_forecast = await self._get_target_date_forecast(
            latitude, longitude, travel_date, days_ahead
        )

        if not target_forecast:
            return {
                "suitable": None,
                "score": 0,
                "message": "No forecast available for this date",
            }

        # Evaluate activity suitability
        return self._evaluate_activity_suitability(target_forecast, activity_type)

    async def _get_target_date_forecast(
        self, latitude: float, longitude: float, travel_date: datetime, days_ahead: int
    ) -> dict[str, Any] | None:
        """Get forecast for target date."""
        forecast_data = await self.get_forecast(
            latitude=latitude,
            longitude=longitude,
            days=days_ahead + 1,
            include_hourly=False,
        )

        daily_forecasts = forecast_data.get("daily", [])

        for forecast in daily_forecasts:
            forecast_date = datetime.fromtimestamp(forecast.get("dt", 0))
            if forecast_date.date() == travel_date.date():
                return forecast

        return None

    def _evaluate_activity_suitability(
        self, target_forecast: dict[str, Any], activity_type: str
    ) -> dict[str, Any]:
        """Evaluate weather suitability for specific activity."""
        weather_conditions = self._extract_weather_conditions(target_forecast)
        score, recommendations, warnings = self._calculate_activity_score(
            weather_conditions, activity_type.lower()
        )

        max_score = 7
        suitability_percentage = (score / max_score) * 100
        suitable = suitability_percentage >= 60

        return {
            "suitable": suitable,
            "score": suitability_percentage,
            "temperature": weather_conditions["temp_day"],
            "condition": target_forecast.get("weather", [{}])[0].get("description", ""),
            "precipitation_chance": weather_conditions["pop"],
            "recommendations": recommendations,
            "warnings": warnings,
            "forecast": target_forecast,
        }

    def _extract_weather_conditions(self, forecast: dict[str, Any]) -> dict[str, Any]:
        """Extract relevant weather conditions from forecast."""
        return {
            "temp_day": forecast.get("temp", {}).get("day", 0),
            "weather_main": forecast.get("weather", [{}])[0].get("main", "").lower(),
            "pop": forecast.get("pop", 0) * 100,
            "wind_speed": forecast.get("wind_speed", 0),
        }

    def _calculate_activity_score(
        self, conditions: dict[str, Any], activity: str
    ) -> tuple[int, list[str], list[str]]:
        """Calculate suitability score for activity based on conditions."""
        return self._score_activity(conditions, activity.lower())

    def _score_activity(
        self, conditions: dict[str, Any], activity: str
    ) -> tuple[int, list[str], list[str]]:
        """Unified activity scoring with activity-specific rules."""
        score = 0
        recommendations: list[str] = []
        warnings: list[str] = []

        temp = conditions["temp_day"]
        weather = conditions["weather_main"]
        pop = conditions["pop"]
        wind = conditions.get("wind_speed", 0)

        # Activity-specific scoring rules
        if "beach" in activity or "swimming" in activity:
            score += 3 if 25 <= temp <= 32 else 2 if 20 <= temp <= 35 else 0
            if score < 2:
                warnings.append("Temperature may not be ideal for beach activities")
            score += (
                2 if weather in ["clear", "sunny"] else 1 if weather == "clouds" else 0
            )
            if weather not in ["clear", "sunny", "clouds"]:
                warnings.append("Weather conditions may not be ideal")
            score += 1 if wind < 20 else 0
            if wind >= 20:
                warnings.append("High winds expected")
            score += 1 if pop < 20 else 0
            if pop >= 20:
                warnings.append(f"{pop}% chance of rain")
        elif "hiking" in activity or "outdoor" in activity:
            score += 3 if 10 <= temp <= 25 else 2 if 5 <= temp <= 30 else 0
            if score < 2:
                warnings.append("Temperature may be challenging for hiking")
            score += 2 if pop < 30 else 0
            if pop >= 30:
                warnings.append("High chance of precipitation - pack rain gear")
            score += 1 if wind < 30 else 0
            if wind >= 30:
                warnings.append("Strong winds expected")
            score += 1 if weather not in ["thunderstorm", "snow"] else 0
            if weather in ["thunderstorm", "snow"]:
                warnings.append("Potentially dangerous conditions")
        else:  # sightseeing/city
            score += 2 if 5 <= temp <= 30 else 0
            if temp < 5 or temp > 30:
                recommendations.append("Dress appropriately for the temperature")
            score += 2 if pop < 50 else 0
            if pop >= 50:
                recommendations.append("Bring an umbrella")
            score += 2 if weather != "thunderstorm" else 0
            if weather == "thunderstorm":
                warnings.append("Thunderstorms expected - plan indoor activities")

        return score, recommendations, warnings

    async def health_check(self) -> bool:
        """Check if the OpenWeatherMap API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self.ensure_connected()
            # Simple test request (coordinates path)
            await self.get_current_weather(40.7128, -74.0060)
            return True
        except CoreServiceError:
            return False

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.disconnect()

    async def __aenter__(self) -> "WeatherService":
        """Enter the async context manager and connect the service."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close the service."""
        await self.close()
