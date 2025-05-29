"""
OpenWeatherMap API service implementation with TripSage Core integration.

This module provides direct integration with the OpenWeatherMap API for weather
forecasts, current conditions, and travel-specific weather analysis.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from tripsage_core.config.base_app_settings import CoreAppSettings, get_settings
from tripsage_core.exceptions.exceptions import CoreAPIError, CoreServiceError


class WeatherServiceError(CoreAPIError):
    """Exception raised for weather service errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="WEATHER_API_ERROR",
            service="WeatherService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class WeatherService:
    """Service for interacting with OpenWeatherMap API."""

    def __init__(self, settings: Optional[CoreAppSettings] = None):
        """
        Initialize the OpenWeatherMap service.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.base_url_v3 = "https://api.openweathermap.org/data/3.0"

        # Get API key from core settings
        weather_key = getattr(self.settings, "openweathermap_api_key", None)
        if not weather_key:
            raise CoreServiceError(
                message="OpenWeatherMap API key not configured in settings",
                code="MISSING_API_KEY",
                service="WeatherService",
            )

        self.api_key = weather_key.get_secret_value()
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False

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
                message=f"Failed to connect to OpenWeatherMap API: {str(e)}",
                code="CONNECTION_FAILED",
                service="WeatherService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass  # Ignore cleanup errors
            finally:
                self._client = None
                self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_v3: bool = False,
    ) -> Dict[str, Any]:
        """
        Make a request to the OpenWeatherMap API.

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

        base_url = self.base_url_v3 if use_v3 else self.base_url
        url = f"{base_url}/{endpoint}"

        # Add API key to params
        if params is None:
            params = {}
        params["appid"] = self.api_key

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json() if e.response.content else {}
            except Exception:
                pass

            raise WeatherServiceError(
                f"OpenWeatherMap API error: {error_data.get('message', str(e))}",
                original_error=e,
            ) from e

        except Exception as e:
            raise WeatherServiceError(
                f"Request failed: {str(e)}", original_error=e
            ) from e

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        units: str = "metric",
        lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Get current weather conditions.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            units: Temperature units (metric, imperial, kelvin)
            lang: Language code

        Returns:
            Current weather data
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "units": units,
            "lang": lang,
        }

        data = await self._make_request("weather", params)
        return data

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        include_hourly: bool = True,
        units: str = "metric",
        lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Get weather forecast.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast (max 7)
            include_hourly: Include hourly forecast
            units: Temperature units (metric, imperial, kelvin)
            lang: Language code

        Returns:
            Weather forecast data
        """
        # Use One Call API for comprehensive forecast
        params = {
            "lat": latitude,
            "lon": longitude,
            "units": units,
            "lang": lang,
            "exclude": "minutely,alerts" if not include_hourly else "minutely,alerts",
        }

        data = await self._make_request("onecall", params, use_v3=True)
        return data

    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
    ) -> Dict[str, Any]:
        """
        Get air quality data.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Air pollution data
        """
        params = {
            "lat": latitude,
            "lon": longitude,
        }

        data = await self._make_request("air_pollution", params)
        return data

    async def get_weather_alerts(
        self,
        latitude: float,
        longitude: float,
    ) -> List[Dict[str, Any]]:
        """
        Get weather alerts for a location.

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
        dt: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get UV index data.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            dt: Date/time for UV index (current if None)

        Returns:
            UV index data
        """
        endpoint = "uvi" if dt else "uvi/current"
        params = {
            "lat": latitude,
            "lon": longitude,
        }

        if dt:
            params["dt"] = int(dt.timestamp())

        data = await self._make_request(endpoint, params)
        return data

    async def get_travel_weather_summary(
        self,
        latitude: float,
        longitude: float,
        arrival_date: datetime,
        departure_date: datetime,
        activities: Optional[List[str]] = None,
        units: str = "metric",
    ) -> Dict[str, Any]:
        """
        Get comprehensive weather summary for travel planning.

        Args:
            latitude: Destination latitude
            longitude: Destination longitude
            arrival_date: Travel start date
            departure_date: Travel end date
            activities: Planned activities (beach, hiking, etc.)
            units: Temperature units

        Returns:
            Travel weather summary
        """
        # Calculate trip duration
        trip_duration = (departure_date - arrival_date).days + 1

        # Get forecasts
        forecast_data = await self.get_forecast(
            latitude=latitude,
            longitude=longitude,
            days=min(trip_duration, 7),
            include_hourly=True,
            units=units,
        )

        # Get air quality
        air_quality_data = await self.get_air_quality(latitude, longitude)

        # Get weather alerts
        alerts = await self.get_weather_alerts(latitude, longitude)

        # Calculate statistics from forecast data
        daily_forecasts = forecast_data.get("daily", [])

        temps = []
        rain_days = 0
        snow_days = 0
        clear_days = 0

        for forecast in daily_forecasts:
            temp_data = forecast.get("temp", {})
            temps.extend([temp_data.get("min", 0), temp_data.get("max", 0)])

            # Count weather conditions
            if forecast.get("rain", 0) > 0:
                rain_days += 1
            if forecast.get("snow", 0) > 0:
                snow_days += 1

            weather_main = forecast.get("weather", [{}])[0].get("main", "").lower()
            if weather_main in ["clear", "sunny"]:
                clear_days += 1

        avg_temp = sum(temps) / len(temps) if temps else 0
        temp_range = (min(temps), max(temps)) if temps else (0, 0)

        # Activity recommendations
        recommendations = []
        warnings = []

        if activities:
            for activity in activities:
                activity_lower = activity.lower()

                if "beach" in activity_lower or "swimming" in activity_lower:
                    if avg_temp < 20:  # Celsius
                        warnings.append(
                            f"Cool temperatures for {activity} (avg {avg_temp:.1f}°)"
                        )
                    if rain_days > trip_duration * 0.3:
                        warnings.append(f"Frequent rain may affect {activity}")
                    else:
                        recommendations.append(f"Good weather expected for {activity}")

                elif "hiking" in activity_lower or "outdoor" in activity_lower:
                    if rain_days > trip_duration * 0.5:
                        warnings.append(f"Pack rain gear for {activity}")
                    if avg_temp > 30:  # Celsius
                        warnings.append(
                            f"High temperatures - plan {activity} for early morning"
                        )
                    else:
                        recommendations.append(f"Pleasant conditions for {activity}")

                elif "skiing" in activity_lower or "snow" in activity_lower:
                    if snow_days == 0:
                        warnings.append(f"No snow forecast for {activity}")
                    else:
                        recommendations.append(
                            f"Snow conditions expected for {activity}"
                        )

        # Packing suggestions
        packing_suggestions = []

        if rain_days > 0:
            packing_suggestions.append("Rain jacket or umbrella")
        if snow_days > 0:
            packing_suggestions.append("Warm clothing and snow gear")
        if temp_range[1] > 25:
            packing_suggestions.append("Sun protection (hat, sunscreen)")
        if temp_range[0] < 10:
            packing_suggestions.append("Warm layers for cool evenings")

        # Calculate UV index range
        uv_range = (0, 0)
        try:
            for forecast in daily_forecasts:
                uvi = forecast.get("uvi", 0)
                if uvi > 6:
                    packing_suggestions.append("High SPF sunscreen")
                uv_range = (min(uv_range[0], uvi), max(uv_range[1], uvi))
        except Exception:
            pass

        return {
            "average_temperature": avg_temp,
            "temperature_range": temp_range,
            "total_rain_days": rain_days,
            "total_snow_days": snow_days,
            "total_clear_days": clear_days,
            "precipitation_chance": sum(f.get("pop", 0) for f in daily_forecasts)
            / len(daily_forecasts)
            * 100
            if daily_forecasts
            else 0,
            "activity_recommendations": recommendations,
            "weather_warnings": warnings,
            "packing_suggestions": packing_suggestions,
            "air_quality_forecast": air_quality_data.get("list", [{}])[0]
            .get("main", {})
            .get("aqi", 0),
            "uv_index_range": uv_range,
            "alerts": alerts,
            "forecast_data": forecast_data,
        }

    async def get_multi_city_weather(
        self,
        cities: List[Tuple[float, float, str]],
        date: Optional[datetime] = None,
        units: str = "metric",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get weather for multiple cities (useful for trip planning).

        Args:
            cities: List of (latitude, longitude, name) tuples
            date: Date for weather (current if None)
            units: Temperature units

        Returns:
            Dictionary mapping city names to weather data
        """
        if date and date > datetime.now():
            # Future date - use forecast
            tasks = []
            for lat, lon, _name in cities:
                tasks.append(self.get_forecast(lat, lon, 1, False, units))
        else:
            # Current weather
            tasks = []
            for lat, lon, _name in cities:
                tasks.append(self.get_current_weather(lat, lon, units))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        weather_data = {}
        for (_lat, _lon, name), result in zip(cities, results, strict=False):
            if isinstance(result, Exception):
                continue
            weather_data[name] = result

        return weather_data

    async def check_travel_weather_conditions(
        self,
        latitude: float,
        longitude: float,
        travel_date: datetime,
        activity_type: str,
    ) -> Dict[str, Any]:
        """
        Check if weather conditions are suitable for specific activities.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            travel_date: Date of travel
            activity_type: Type of activity (beach, hiking, sightseeing, etc.)

        Returns:
            Dictionary with suitability score and recommendations
        """
        # Get forecast for the date
        days_ahead = (travel_date - datetime.now()).days
        if days_ahead > 7:
            return {
                "suitable": None,
                "score": 0,
                "message": "Weather forecast not available for dates beyond 7 days",
            }

        forecast_data = await self.get_forecast(
            latitude=latitude,
            longitude=longitude,
            days=days_ahead + 1,
            include_hourly=False,
        )

        # Find forecast for specific date
        daily_forecasts = forecast_data.get("daily", [])
        target_forecast = None

        for forecast in daily_forecasts:
            forecast_date = datetime.fromtimestamp(forecast.get("dt", 0))
            if forecast_date.date() == travel_date.date():
                target_forecast = forecast
                break

        if not target_forecast:
            return {
                "suitable": None,
                "score": 0,
                "message": "No forecast available for this date",
            }

        # Evaluate conditions based on activity
        score = 0
        recommendations = []
        warnings = []

        activity_lower = activity_type.lower()
        temp_day = target_forecast.get("temp", {}).get("day", 0)
        weather_main = target_forecast.get("weather", [{}])[0].get("main", "").lower()
        pop = target_forecast.get("pop", 0) * 100  # Precipitation probability
        wind_speed = target_forecast.get("wind_speed", 0)

        if "beach" in activity_lower or "swimming" in activity_lower:
            # Ideal: warm, sunny, low wind
            if 25 <= temp_day <= 32:
                score += 3
            elif 20 <= temp_day <= 35:
                score += 2
            else:
                warnings.append("Temperature may not be ideal for beach activities")

            if weather_main in ["clear", "sunny"]:
                score += 2
            elif weather_main == "clouds":
                score += 1
            else:
                warnings.append("Weather conditions may not be ideal")

            if wind_speed < 20:
                score += 1
            else:
                warnings.append("High winds expected")

            if pop < 20:
                score += 1
            else:
                warnings.append(f"{pop}% chance of rain")

        elif "hiking" in activity_lower or "trekking" in activity_lower:
            # Ideal: moderate temp, no rain, good visibility
            if 10 <= temp_day <= 25:
                score += 3
            elif 5 <= temp_day <= 30:
                score += 2
            else:
                warnings.append("Temperature may be challenging for hiking")

            if pop < 30:
                score += 2
            else:
                warnings.append("High chance of precipitation - pack rain gear")

            if wind_speed < 30:
                score += 1
            else:
                warnings.append("Strong winds expected")

            if weather_main not in ["thunderstorm", "snow"]:
                score += 1
            else:
                warnings.append("Potentially dangerous conditions")

        elif "sightseeing" in activity_lower or "city" in activity_lower:
            # More flexible conditions
            if 5 <= temp_day <= 30:
                score += 2
            else:
                recommendations.append("Dress appropriately for the temperature")

            if pop < 50:
                score += 2
            else:
                recommendations.append("Bring an umbrella")

            if weather_main != "thunderstorm":
                score += 2
            else:
                warnings.append("Thunderstorms expected - plan indoor activities")

        # Generate overall recommendation
        max_score = 7  # Adjust based on criteria above
        suitability_percentage = (score / max_score) * 100

        suitable = suitability_percentage >= 60

        return {
            "suitable": suitable,
            "score": suitability_percentage,
            "temperature": temp_day,
            "condition": target_forecast.get("weather", [{}])[0].get("description", ""),
            "precipitation_chance": pop,
            "recommendations": recommendations,
            "warnings": warnings,
            "forecast": target_forecast,
        }

    async def health_check(self) -> bool:
        """
        Check if the OpenWeatherMap API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self.ensure_connected()
            # Simple test request
            await self.get_current_weather(40.7128, -74.0060)  # New York
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global service instance
_weather_service: Optional[WeatherService] = None


async def get_weather_service() -> WeatherService:
    """
    Get the global weather service instance.

    Returns:
        WeatherService instance
    """
    global _weather_service

    if _weather_service is None:
        _weather_service = WeatherService()
        await _weather_service.connect()

    return _weather_service


async def close_weather_service() -> None:
    """Close the global weather service instance."""
    global _weather_service

    if _weather_service:
        await _weather_service.close()
        _weather_service = None
