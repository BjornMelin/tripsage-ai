"""OpenWeatherMap API service implementation.

This module provides direct integration with the OpenWeatherMap API for weather
forecasts, current conditions, and travel-specific weather analysis.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from tripsage.core.config import settings
from tripsage.models.api.weather_models import (
    AirPollution,
    AirQualityIndex,
    CurrentWeather,
    DailyForecast,
    HourlyForecast,
    TravelWeatherSummary,
    UVIndex,
    WeatherAlert,
    WeatherCondition,
    WeatherUnits,
)
from tripsage.services.base import BaseService
from tripsage.utils.cache_tools import cached
from tripsage.utils.decorators import with_retry
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class OpenWeatherMapService(BaseService):
    """Service for interacting with OpenWeatherMap API."""

    def __init__(self):
        """Initialize the OpenWeatherMap service."""
        super().__init__()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.base_url_v3 = "https://api.openweathermap.org/data/3.0"
        self.api_key = settings.OPENWEATHERMAP_API_KEY

        if not self.api_key:
            raise ValueError("OPENWEATHERMAP_API_KEY not configured")

        # Configure HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "User-Agent": "TripSage/1.0",
            },
            timeout=15.0,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    @with_retry(max_attempts=3, backoff_factor=2)
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_v3: bool = False,
    ) -> Dict[str, Any]:
        """Make a request to the OpenWeatherMap API.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_v3: Use v3 API endpoint

        Returns:
            API response data

        Raises:
            httpx.HTTPError: If the request fails
        """
        base_url = self.base_url_v3 if use_v3 else self.base_url
        url = f"{base_url}/{endpoint}"

        # Add API key to params
        if params is None:
            params = {}
        params["appid"] = self.api_key

        response = await self.client.get(url, params=params)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            logger.error(f"OpenWeatherMap API error: {error_data}")
            raise

        return response.json()

    @cached(ttl=600)  # Cache for 10 minutes
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        units: WeatherUnits = WeatherUnits.metric,
        lang: str = "en",
    ) -> CurrentWeather:
        """Get current weather conditions.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            units: Temperature units
            lang: Language code

        Returns:
            Current weather data
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "units": units.value,
            "lang": lang,
        }

        data = await self._make_request("weather", params)

        # Parse response
        weather = CurrentWeather(
            temperature=data["main"]["temp"],
            feels_like=data["main"]["feels_like"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            visibility=data.get("visibility", 10000),
            wind_speed=data["wind"]["speed"],
            wind_direction=data["wind"].get("deg"),
            clouds=data["clouds"]["all"],
            condition=WeatherCondition(
                id=data["weather"][0]["id"],
                main=data["weather"][0]["main"],
                description=data["weather"][0]["description"],
                icon=data["weather"][0]["icon"],
            ),
            dt=datetime.fromtimestamp(data["dt"]),
            sunrise=datetime.fromtimestamp(data["sys"]["sunrise"]),
            sunset=datetime.fromtimestamp(data["sys"]["sunset"]),
            timezone_offset=data.get("timezone", 0),
            location_name=data.get("name"),
            country=data["sys"].get("country"),
        )

        # Add rain/snow data if present
        if "rain" in data:
            weather.rain_1h = data["rain"].get("1h")
            weather.rain_3h = data["rain"].get("3h")
        if "snow" in data:
            weather.snow_1h = data["snow"].get("1h")
            weather.snow_3h = data["snow"].get("3h")

        return weather

    @cached(ttl=1800)  # Cache for 30 minutes
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        include_hourly: bool = True,
        units: WeatherUnits = WeatherUnits.metric,
        lang: str = "en",
    ) -> Tuple[List[DailyForecast], Optional[List[HourlyForecast]]]:
        """Get weather forecast.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast (max 7)
            include_hourly: Include hourly forecast
            units: Temperature units
            lang: Language code

        Returns:
            Tuple of (daily forecasts, hourly forecasts)
        """
        # Use One Call API for comprehensive forecast
        params = {
            "lat": latitude,
            "lon": longitude,
            "units": units.value,
            "lang": lang,
            "exclude": "minutely,alerts"
            if not include_hourly
            else "minutely,hourly,alerts",
        }

        data = await self._make_request("onecall", params, use_v3=True)

        # Parse daily forecast
        daily_forecasts = []
        for day_data in data.get("daily", [])[:days]:
            daily = DailyForecast(
                dt=datetime.fromtimestamp(day_data["dt"]),
                sunrise=datetime.fromtimestamp(day_data["sunrise"]),
                sunset=datetime.fromtimestamp(day_data["sunset"]),
                moonrise=datetime.fromtimestamp(day_data["moonrise"]),
                moonset=datetime.fromtimestamp(day_data["moonset"]),
                moon_phase=day_data["moon_phase"],
                temp_min=day_data["temp"]["min"],
                temp_max=day_data["temp"]["max"],
                temp_morn=day_data["temp"]["morn"],
                temp_day=day_data["temp"]["day"],
                temp_eve=day_data["temp"]["eve"],
                temp_night=day_data["temp"]["night"],
                feels_like_morn=day_data["feels_like"]["morn"],
                feels_like_day=day_data["feels_like"]["day"],
                feels_like_eve=day_data["feels_like"]["eve"],
                feels_like_night=day_data["feels_like"]["night"],
                humidity=day_data["humidity"],
                pressure=day_data["pressure"],
                wind_speed=day_data["wind_speed"],
                wind_direction=day_data.get("wind_deg"),
                wind_gust=day_data.get("wind_gust"),
                clouds=day_data["clouds"],
                precipitation_probability=day_data.get("pop", 0) * 100,
                rain=day_data.get("rain"),
                snow=day_data.get("snow"),
                uvi=day_data.get("uvi", 0),
                condition=WeatherCondition(
                    id=day_data["weather"][0]["id"],
                    main=day_data["weather"][0]["main"],
                    description=day_data["weather"][0]["description"],
                    icon=day_data["weather"][0]["icon"],
                ),
            )
            daily_forecasts.append(daily)

        # Parse hourly forecast if requested
        hourly_forecasts = None
        if include_hourly and "hourly" in data:
            hourly_forecasts = []
            for hour_data in data["hourly"][:48]:  # 48 hours
                hourly = HourlyForecast(
                    dt=datetime.fromtimestamp(hour_data["dt"]),
                    temperature=hour_data["temp"],
                    feels_like=hour_data["feels_like"],
                    humidity=hour_data["humidity"],
                    pressure=hour_data["pressure"],
                    visibility=hour_data.get("visibility", 10000),
                    wind_speed=hour_data["wind_speed"],
                    wind_direction=hour_data.get("wind_deg"),
                    wind_gust=hour_data.get("wind_gust"),
                    clouds=hour_data["clouds"],
                    precipitation_probability=hour_data.get("pop", 0) * 100,
                    rain_1h=hour_data.get("rain", {}).get("1h"),
                    snow_1h=hour_data.get("snow", {}).get("1h"),
                    condition=WeatherCondition(
                        id=hour_data["weather"][0]["id"],
                        main=hour_data["weather"][0]["main"],
                        description=hour_data["weather"][0]["description"],
                        icon=hour_data["weather"][0]["icon"],
                    ),
                )
                hourly_forecasts.append(hourly)

        return daily_forecasts, hourly_forecasts

    @cached(ttl=3600)  # Cache for 1 hour
    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
    ) -> AirPollution:
        """Get air quality data.

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

        # Parse components
        components = data["list"][0]["components"]
        main = data["list"][0]["main"]

        return AirPollution(
            aqi=AirQualityIndex(main["aqi"]),
            co=components["co"],
            no=components["no"],
            no2=components["no2"],
            o3=components["o3"],
            so2=components["so2"],
            pm2_5=components["pm2_5"],
            pm10=components["pm10"],
            nh3=components["nh3"],
            dt=datetime.fromtimestamp(data["list"][0]["dt"]),
        )

    async def get_weather_alerts(
        self,
        latitude: float,
        longitude: float,
    ) -> List[WeatherAlert]:
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

        alerts = []
        for alert_data in data.get("alerts", []):
            alert = WeatherAlert(
                sender_name=alert_data["sender_name"],
                event=alert_data["event"],
                start=datetime.fromtimestamp(alert_data["start"]),
                end=datetime.fromtimestamp(alert_data["end"]),
                description=alert_data["description"],
                tags=alert_data.get("tags", []),
            )
            alerts.append(alert)

        return alerts

    async def get_uv_index(
        self,
        latitude: float,
        longitude: float,
        dt: Optional[datetime] = None,
    ) -> UVIndex:
        """Get UV index data.

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

        return UVIndex(
            value=data["value"],
            dt=datetime.fromtimestamp(data["date"])
            if "date" in data
            else datetime.now(),
        )

    # Travel-specific methods

    async def get_travel_weather_summary(
        self,
        latitude: float,
        longitude: float,
        arrival_date: datetime,
        departure_date: datetime,
        activities: Optional[List[str]] = None,
        units: WeatherUnits = WeatherUnits.metric,
    ) -> TravelWeatherSummary:
        """Get comprehensive weather summary for travel planning.

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
        daily_forecasts, hourly_forecasts = await self.get_forecast(
            latitude=latitude,
            longitude=longitude,
            days=min(trip_duration, 7),
            include_hourly=True,
            units=units,
        )

        # Get air quality
        air_quality = await self.get_air_quality(latitude, longitude)

        # Get weather alerts
        alerts = await self.get_weather_alerts(latitude, longitude)

        # Calculate statistics
        temps = []
        rain_days = 0
        snow_days = 0
        clear_days = 0

        for forecast in daily_forecasts:
            temps.extend([forecast.temp_min, forecast.temp_max])

            # Count weather conditions
            if forecast.rain and forecast.rain > 0:
                rain_days += 1
            if forecast.snow and forecast.snow > 0:
                snow_days += 1
            if forecast.condition.main.lower() in ["clear", "sunny"]:
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
        if any(f.uvi > 6 for f in daily_forecasts):
            packing_suggestions.append("High SPF sunscreen")

        # Best/worst days
        best_days = []
        worst_days = []

        for _i, forecast in enumerate(daily_forecasts):
            day_score = 0

            # Score based on conditions
            if forecast.condition.main.lower() in ["clear", "sunny"]:
                day_score += 2
            if 18 <= forecast.temp_day <= 25:  # Comfortable temperature
                day_score += 1
            if forecast.precipitation_probability < 20:
                day_score += 1
            if forecast.wind_speed < 20:  # km/h
                day_score += 1

            if day_score >= 4:
                best_days.append(forecast.dt)
            elif day_score <= 1:
                worst_days.append(forecast.dt)

        return TravelWeatherSummary(
            average_temperature=avg_temp,
            temperature_range=temp_range,
            total_rain_days=rain_days,
            total_snow_days=snow_days,
            total_clear_days=clear_days,
            precipitation_chance=sum(
                f.precipitation_probability for f in daily_forecasts
            )
            / len(daily_forecasts),
            activity_recommendations=recommendations,
            weather_warnings=warnings,
            packing_suggestions=packing_suggestions,
            best_weather_days=best_days[:3],  # Top 3 days
            worst_weather_days=worst_days[:3],  # Bottom 3 days
            air_quality_forecast=air_quality.aqi.name,
            uv_index_range=(
                min(f.uvi for f in daily_forecasts),
                max(f.uvi for f in daily_forecasts),
            ),
            alerts=alerts,
        )

    async def get_multi_city_weather(
        self,
        cities: List[Tuple[float, float, str]],
        date: Optional[datetime] = None,
        units: WeatherUnits = WeatherUnits.metric,
    ) -> Dict[str, CurrentWeather]:
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
            tasks = []
            for lat, lon, _name in cities:
                tasks.append(self.get_forecast(lat, lon, 1, False, units))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            weather_data = {}
            for (_lat, _lon, name), result in zip(cities, results, strict=False):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to get weather for {name}: {result}")
                    continue

                # Convert forecast to current weather format
                daily_forecast = result[0][0] if result[0] else None
                if daily_forecast:
                    weather_data[name] = CurrentWeather(
                        temperature=daily_forecast.temp_day,
                        feels_like=daily_forecast.feels_like_day,
                        humidity=daily_forecast.humidity,
                        pressure=daily_forecast.pressure,
                        visibility=10000,  # Not available in forecast
                        wind_speed=daily_forecast.wind_speed,
                        wind_direction=daily_forecast.wind_direction,
                        clouds=daily_forecast.clouds,
                        condition=daily_forecast.condition,
                        dt=daily_forecast.dt,
                        sunrise=daily_forecast.sunrise,
                        sunset=daily_forecast.sunset,
                        timezone_offset=0,
                        location_name=name,
                    )
        else:
            # Current weather
            tasks = []
            for lat, lon, _name in cities:
                tasks.append(self.get_current_weather(lat, lon, units))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            weather_data = {}
            for (_lat, _lon, name), result in zip(cities, results, strict=False):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to get weather for {name}: {result}")
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
        """Check if weather conditions are suitable for specific activities.

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

        daily_forecasts, _ = await self.get_forecast(
            latitude=latitude,
            longitude=longitude,
            days=days_ahead + 1,
            include_hourly=False,
        )

        # Find forecast for specific date
        target_forecast = None
        for forecast in daily_forecasts:
            if forecast.dt.date() == travel_date.date():
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

        if "beach" in activity_lower or "swimming" in activity_lower:
            # Ideal: warm, sunny, low wind
            if 25 <= target_forecast.temp_day <= 32:
                score += 3
            elif 20 <= target_forecast.temp_day <= 35:
                score += 2
            else:
                warnings.append("Temperature may not be ideal for beach activities")

            if target_forecast.condition.main.lower() in ["clear", "sunny"]:
                score += 2
            elif target_forecast.condition.main.lower() == "clouds":
                score += 1
            else:
                warnings.append("Weather conditions may not be ideal")

            if target_forecast.wind_speed < 20:
                score += 1
            else:
                warnings.append("High winds expected")

            if target_forecast.precipitation_probability < 20:
                score += 1
            else:
                warnings.append(
                    f"{target_forecast.precipitation_probability}% chance of rain"
                )

        elif "hiking" in activity_lower or "trekking" in activity_lower:
            # Ideal: moderate temp, no rain, good visibility
            if 10 <= target_forecast.temp_day <= 25:
                score += 3
            elif 5 <= target_forecast.temp_day <= 30:
                score += 2
            else:
                warnings.append("Temperature may be challenging for hiking")

            if target_forecast.precipitation_probability < 30:
                score += 2
            else:
                warnings.append("High chance of precipitation - pack rain gear")

            if target_forecast.wind_speed < 30:
                score += 1
            else:
                warnings.append("Strong winds expected")

            if target_forecast.condition.main.lower() not in ["thunderstorm", "snow"]:
                score += 1
            else:
                warnings.append("Potentially dangerous conditions")

        elif "sightseeing" in activity_lower or "city" in activity_lower:
            # More flexible conditions
            if 5 <= target_forecast.temp_day <= 30:
                score += 2
            else:
                recommendations.append("Dress appropriately for the temperature")

            if target_forecast.precipitation_probability < 50:
                score += 2
            else:
                recommendations.append("Bring an umbrella")

            if target_forecast.condition.main.lower() != "thunderstorm":
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
            "temperature": target_forecast.temp_day,
            "condition": target_forecast.condition.description,
            "precipitation_chance": target_forecast.precipitation_probability,
            "recommendations": recommendations,
            "warnings": warnings,
            "forecast": target_forecast,
        }
