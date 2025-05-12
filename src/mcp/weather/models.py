"""
Pydantic models for Weather MCP client.

This module defines the parameter and response models for the Weather MCP Client,
providing proper validation and type safety.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class LocationParams(BaseParams):
    """Parameters for location-based weather queries."""

    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lon: Optional[float] = Field(None, description="Longitude coordinate")
    city: Optional[str] = Field(None, description="City name (e.g., 'Paris')")
    country: Optional[str] = Field(None, description="Country code (e.g., 'FR')")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_coordinates_or_city(self) -> "LocationParams":
        """Validate that either coordinates or city is provided."""
        if (self.lat is None or self.lon is None) and not self.city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        return self


class GetCurrentWeatherParams(BaseParams):
    """Parameters for the get_current_weather method."""

    location: LocationParams = Field(..., description="Location to get weather for")


class WeatherCondition(BaseModel):
    """Weather condition information."""

    id: int = Field(..., description="Weather condition ID")
    main: str = Field(..., description="Main weather condition")
    description: str = Field(..., description="Detailed weather description")
    icon: str = Field(..., description="Weather icon code")


class CurrentWeatherResponse(BaseResponse):
    """Response model for current weather information."""

    temperature: float = Field(..., description="Current temperature in Celsius")
    feels_like: float = Field(..., description="Feels-like temperature in Celsius")
    temp_min: float = Field(..., description="Minimum temperature in Celsius")
    temp_max: float = Field(..., description="Maximum temperature in Celsius")
    pressure: int = Field(..., description="Atmospheric pressure in hPa")
    humidity: int = Field(..., description="Humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_direction: int = Field(..., description="Wind direction in degrees")
    clouds: int = Field(..., description="Cloudiness percentage")
    weather: WeatherCondition = Field(..., description="Weather condition information")
    location: Dict[str, Any] = Field(..., description="Location information")
    timestamp: int = Field(..., description="Timestamp of data retrieval")


class DailyForecast(BaseModel):
    """Model for daily weather forecast data."""

    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    temp_min: float = Field(..., description="Minimum temperature in Celsius")
    temp_max: float = Field(..., description="Maximum temperature in Celsius")
    temp_avg: float = Field(..., description="Average temperature in Celsius")
    feels_like: Dict[str, float] = Field(..., description="Feels-like temperatures")
    pressure: int = Field(..., description="Atmospheric pressure in hPa")
    humidity: int = Field(..., description="Humidity percentage")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_direction: int = Field(..., description="Wind direction in degrees")
    clouds: int = Field(..., description="Cloudiness percentage")
    probability: float = Field(..., description="Precipitation probability")
    weather: WeatherCondition = Field(..., description="Weather condition information")

    model_config = ConfigDict(extra="allow")


class ForecastResponse(BaseResponse):
    """Response model for weather forecast information."""

    location: Dict[str, Any] = Field(..., description="Location information")
    current: CurrentWeatherResponse = Field(..., description="Current weather")
    daily: List[DailyForecast] = Field(..., description="Daily forecast data")


class RecommendationParams(BaseParams):
    """Parameters for the get_travel_recommendation method."""

    location: LocationParams = Field(
        ..., description="Location to get recommendations for"
    )
    start_date: Optional[str] = Field(None, description="Trip start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Trip end date (YYYY-MM-DD)")
    activities: Optional[List[str]] = Field(
        None, description="List of planned activities"
    )


class RecommendationResponse(BaseResponse):
    """Response model for travel recommendations."""

    location: Dict[str, Any] = Field(..., description="Location information")
    current_weather: CurrentWeatherResponse = Field(..., description="Current weather")
    recommendations: Dict[str, Any] = Field(..., description="Travel recommendations")


class TravelWeatherSummary(BaseModel):
    """Weather summary for a trip period."""

    destination: str = Field(..., description="Travel destination")
    start_date: str = Field(..., description="Trip start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Trip end date (YYYY-MM-DD)")
    temperature: Dict[str, Optional[float]] = Field(
        ..., description="Temperature statistics"
    )
    conditions: Dict[str, Any] = Field(..., description="Weather conditions statistics")
    days: List[Dict[str, Any]] = Field(..., description="Daily weather data")
    error: Optional[str] = Field(None, description="Error message if any")

    model_config = ConfigDict(extra="forbid", validate_default=True)


class DestinationWeatherComparison(BaseModel):
    """Weather comparison across multiple destinations."""

    destinations: List[str] = Field(..., description="List of destinations compared")
    date: str = Field(..., description="Date for comparison or 'current'")
    results: List[Dict[str, Any]] = Field(..., description="Comparison results")
    ranking: Optional[List[str]] = Field(
        None, description="Destinations ranked by weather"
    )
    error: Optional[str] = Field(None, description="Error message if any")

    model_config = ConfigDict(extra="forbid", validate_default=True)


class OptimalTravelTime(BaseModel):
    """Recommendations for optimal travel time."""

    destination: str = Field(..., description="Travel destination")
    activity_type: str = Field(..., description="Type of activity planned")
    current_weather: str = Field(..., description="Current weather conditions")
    current_temp: float = Field(..., description="Current temperature")
    activity_recommendation: str = Field(
        ..., description="Activity-specific recommendation"
    )
    good_weather_days: List[str] = Field(..., description="Days with favorable weather")
    forecast_recommendations: List[str] = Field(
        ..., description="Forecast-based recommendations"
    )
    clothing_recommendations: List[str] = Field(
        ..., description="Clothing recommendations"
    )
    error: Optional[str] = Field(None, description="Error message if any")

    model_config = ConfigDict(extra="forbid", validate_default=True)
