"""Pydantic models for OpenWeatherMap API integration.

This module provides data models for weather operations,
including current conditions, forecasts, and travel-specific features.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter


_HTTP_URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


class TemperatureUnit(str, Enum):
    """Temperature units."""

    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"


class WindSpeedUnit(str, Enum):
    """Wind speed units."""

    METERS_PER_SECOND = "m/s"
    MILES_PER_HOUR = "mph"
    KILOMETERS_PER_HOUR = "km/h"


class PressureUnit(str, Enum):
    """Pressure units."""

    HPA = "hPa"
    INHG = "inHg"


class WeatherConditionCode(int, Enum):
    """OpenWeatherMap condition codes."""

    # Thunderstorm
    THUNDERSTORM_LIGHT_RAIN = 200
    THUNDERSTORM_RAIN = 201
    THUNDERSTORM_HEAVY_RAIN = 202
    THUNDERSTORM_LIGHT = 210
    THUNDERSTORM = 211
    THUNDERSTORM_HEAVY = 212

    # Drizzle
    DRIZZLE_LIGHT = 300
    DRIZZLE = 301
    DRIZZLE_HEAVY = 302

    # Rain
    RAIN_LIGHT = 500
    RAIN_MODERATE = 501
    RAIN_HEAVY = 502
    RAIN_EXTREME = 503
    RAIN_FREEZING = 511

    # Snow
    SNOW_LIGHT = 600
    SNOW = 601
    SNOW_HEAVY = 602
    SLEET = 611

    # Atmosphere
    MIST = 701
    SMOKE = 711
    HAZE = 721
    DUST = 731
    FOG = 741
    SAND = 751
    DUST_STORM = 761
    ASH = 762
    SQUALL = 771
    TORNADO = 781

    # Clear
    CLEAR = 800

    # Clouds
    CLOUDS_FEW = 801
    CLOUDS_SCATTERED = 802
    CLOUDS_BROKEN = 803
    CLOUDS_OVERCAST = 804


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class WeatherCondition(BaseModel):
    """Weather condition details."""

    id: int = Field(..., description="Weather condition ID")
    main: str = Field(..., description="Group of weather parameters")
    description: str = Field(..., description="Weather condition description")
    icon: str = Field(..., description="Weather icon ID")

    @property
    def icon_url(self) -> str:
        """Get the URL for the weather icon."""
        return f"https://openweathermap.org/img/wn/{self.icon}@2x.png"


class Temperature(BaseModel):
    """Temperature data with feels-like."""

    temp: float = Field(..., description="Actual temperature")
    feels_like: float = Field(..., description="Feels like temperature")
    temp_min: float | None = Field(None, description="Minimum temperature")
    temp_max: float | None = Field(None, description="Maximum temperature")
    pressure: int | None = Field(None, description="Atmospheric pressure in hPa")
    humidity: int | None = Field(None, description="Humidity percentage", ge=0, le=100)
    sea_level: int | None = Field(None, description="Sea level pressure in hPa")
    grnd_level: int | None = Field(None, description="Ground level pressure in hPa")


class Wind(BaseModel):
    """Wind information."""

    speed: float = Field(..., description="Wind speed", ge=0)
    deg: int | None = Field(None, description="Wind direction in degrees", ge=0, le=360)
    gust: float | None = Field(None, description="Wind gust speed", ge=0)

    @property
    def direction_cardinal(self) -> str | None:
        """Get cardinal direction from degrees."""
        if self.deg is None:
            return None

        directions = [
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
        ]
        index = round(self.deg / 22.5) % 16
        return directions[index]


class Clouds(BaseModel):
    """Cloud information."""

    all: int = Field(..., description="Cloudiness percentage", ge=0, le=100)


class Precipitation(BaseModel):
    """Precipitation data."""

    one_hour: float | None = Field(
        None, alias="1h", description="Rain volume for last 1 hour (mm)", ge=0
    )
    three_hours: float | None = Field(
        None, alias="3h", description="Rain volume for last 3 hours (mm)", ge=0
    )


class Snow(BaseModel):
    """Snow data."""

    one_hour: float | None = Field(
        None, alias="1h", description="Snow volume for last 1 hour (mm)", ge=0
    )
    three_hours: float | None = Field(
        None, alias="3h", description="Snow volume for last 3 hours (mm)", ge=0
    )


class CurrentWeather(BaseModel):
    """Current weather data model."""

    model_config = ConfigDict(populate_by_name=True)

    # Location
    coord: Coordinates
    name: str = Field(..., description="City name")
    country: str | None = None
    timezone: int = Field(..., description="Timezone offset in seconds")

    # Weather
    weather: list[WeatherCondition]
    main: Temperature

    # Additional conditions
    visibility: int | None = Field(None, description="Visibility in meters", ge=0)
    wind: Wind
    clouds: Clouds
    rain: Precipitation | None = None
    snow: Snow | None = None

    # Timestamps
    dt: datetime = Field(..., description="Data calculation time")
    sunrise: datetime | None = None
    sunset: datetime | None = None

    # System
    id: int = Field(..., description="City ID")
    cod: int = Field(..., description="Internal parameter")

    # TripSage extensions
    travel_rating: float | None = Field(
        None, ge=0, le=10, description="Weather rating for travel"
    )
    activity_recommendations: list[str] | None = None


class HourlyForecast(BaseModel):
    """Hourly forecast data."""

    model_config = ConfigDict(populate_by_name=True)

    dt: datetime
    temp: float
    feels_like: float
    pressure: int
    humidity: int = Field(..., ge=0, le=100)
    dew_point: float | None = None
    uvi: float | None = Field(None, ge=0)
    clouds: int = Field(..., ge=0, le=100)
    visibility: int | None = Field(None, ge=0)
    wind_speed: float = Field(..., ge=0)
    wind_deg: int = Field(..., ge=0, le=360)
    wind_gust: float | None = Field(None, ge=0)
    weather: list[WeatherCondition]
    pop: float = Field(..., ge=0, le=1, description="Probability of precipitation")
    rain: dict[str, float] | None = None
    snow: dict[str, float] | None = None


class DailyTemperature(BaseModel):
    """Daily temperature data."""

    day: float
    min: float
    max: float
    night: float
    eve: float
    morn: float


class DailyFeelsLike(BaseModel):
    """Daily feels-like temperatures."""

    day: float
    night: float
    eve: float
    morn: float


class DailyForecast(BaseModel):
    """Daily forecast data."""

    model_config = ConfigDict(populate_by_name=True)

    dt: datetime
    sunrise: datetime
    sunset: datetime
    moonrise: datetime
    moonset: datetime
    moon_phase: float = Field(..., ge=0, le=1)

    temp: DailyTemperature
    feels_like: DailyFeelsLike

    pressure: int
    humidity: int = Field(..., ge=0, le=100)
    dew_point: float
    wind_speed: float = Field(..., ge=0)
    wind_deg: int = Field(..., ge=0, le=360)
    wind_gust: float | None = Field(None, ge=0)

    weather: list[WeatherCondition]
    clouds: int = Field(..., ge=0, le=100)
    pop: float = Field(..., ge=0, le=1)
    rain: float | None = Field(None, ge=0)
    snow: float | None = Field(None, ge=0)
    uvi: float = Field(..., ge=0)

    # Travel recommendations
    summary: str | None = None


class WeatherAlert(BaseModel):
    """Weather alert model."""

    sender_name: str
    event: str
    start: datetime
    end: datetime
    description: str
    tags: list[str] = Field(default_factory=list)


class OneCallWeather(BaseModel):
    """One Call API response model."""

    model_config = ConfigDict(populate_by_name=True)

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    timezone: str
    timezone_offset: int

    current: dict[str, Any] | None = None
    minutely: list[dict[str, Any]] | None = None
    hourly: list[HourlyForecast] | None = None
    daily: list[DailyForecast] | None = None
    alerts: list[WeatherAlert] | None = None


class WeatherForecast(BaseModel):
    """5-day weather forecast model."""

    model_config = ConfigDict(populate_by_name=True)

    cod: str
    message: int | str | None = None
    cnt: int
    list: list[dict[str, Any]]
    city: dict[str, Any]


class AirPollutionComponent(BaseModel):
    """Air pollution components."""

    co: float = Field(..., description="Carbon monoxide (μg/m³)")
    no: float = Field(..., description="Nitrogen monoxide (μg/m³)")
    no2: float = Field(..., description="Nitrogen dioxide (μg/m³)")
    o3: float = Field(..., description="Ozone (μg/m³)")
    so2: float = Field(..., description="Sulphur dioxide (μg/m³)")
    pm2_5: float = Field(..., description="Fine particulate matter (μg/m³)")
    pm10: float = Field(..., description="Coarse particulate matter (μg/m³)")
    nh3: float = Field(..., description="Ammonia (μg/m³)")


class AirQualityIndex(int, Enum):
    """Air quality index values."""

    GOOD = 1
    FAIR = 2
    MODERATE = 3
    POOR = 4
    VERY_POOR = 5


class AirPollution(BaseModel):
    """Air pollution data."""

    model_config = ConfigDict(populate_by_name=True)

    dt: datetime
    main: dict[str, int]  # Contains 'aqi' field
    components: AirPollutionComponent

    @property
    def aqi(self) -> AirQualityIndex:
        """Get air quality index."""
        return AirQualityIndex(self.main.get("aqi", 3))

    @property
    def aqi_description(self) -> str:
        """Get human-readable AQI description."""
        descriptions = {
            AirQualityIndex.GOOD: "Good",
            AirQualityIndex.FAIR: "Fair",
            AirQualityIndex.MODERATE: "Moderate",
            AirQualityIndex.POOR: "Poor",
            AirQualityIndex.VERY_POOR: "Very Poor",
        }
        return descriptions.get(self.aqi, "Unknown")


class WeatherMapTile(BaseModel):
    """Weather map tile information."""

    layer: str = Field(..., description="Map layer type")
    z: int = Field(..., description="Zoom level")
    x: int = Field(..., description="X tile coordinate")
    y: int = Field(..., description="Y tile coordinate")
    tile_url: HttpUrl

    @classmethod
    def from_coordinates(
        cls, layer: str, lat: float, lon: float, zoom: int
    ) -> "WeatherMapTile":
        """Create tile from geographic coordinates."""
        # Convert lat/lon to tile coordinates
        import math

        n = 2.0**zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)

        tile_url = _HTTP_URL_ADAPTER.validate_python(
            f"https://tile.openweathermap.org/map/{layer}/{zoom}/{x}/{y}.png"
        )

        return cls(layer=layer, z=zoom, x=x, y=y, tile_url=tile_url)


class TravelWeatherSummary(BaseModel):
    """Travel-specific weather summary."""

    destination: str
    start_date: datetime
    end_date: datetime

    avg_temperature: float
    min_temperature: float
    max_temperature: float

    rain_probability: float = Field(..., ge=0, le=1)
    total_rain_mm: float = Field(..., ge=0)

    dominant_condition: str
    travel_rating: float = Field(..., ge=0, le=10)

    recommendations: list[str]
    packing_suggestions: list[str]
    activity_suitability: dict[str, str]

    daily_summaries: list[dict[str, Any]]
    alerts: list[WeatherAlert] = Field(default_factory=list)


class SeasonalWeather(BaseModel):
    """Seasonal weather patterns."""

    location: str
    season: str
    months: list[str]

    avg_temperature: float
    avg_rainfall: float
    avg_humidity: float

    typical_conditions: list[str]
    best_activities: list[str]
    travel_tips: list[str]
