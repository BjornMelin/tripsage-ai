"""
Weather-related schemas for TripSage tools.

This module provides Pydantic models for validating weather-related data
when interacting with the Weather MCP server.
"""

from typing import Any, Dict, List, Optional

from pydantic import Field, model_validator

from tripsage.models.base import TripSageBaseResponse, TripSageModel


class WeatherLocation(TripSageModel):
    """Location for weather API queries."""

    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lon: Optional[float] = Field(None, description="Longitude coordinate")
    city: Optional[str] = Field(None, description="City name (e.g., 'Paris')")
    country: Optional[str] = Field(None, description="Country code (e.g., 'FR')")

    @model_validator(mode="after")
    def validate_coordinates_or_city(self) -> "WeatherLocation":
        """Validate that either coordinates or city is provided."""
        if (self.lat is None or self.lon is None) and not self.city:
            raise ValueError("Either coordinates (lat, lon) or city must be provided")
        return self


class WeatherCondition(TripSageModel):
    """Weather condition details."""

    id: int = Field(..., description="Condition ID")
    main: str = Field(..., description="Main condition category")
    description: str = Field(..., description="Detailed condition description")
    icon: str = Field(..., description="Icon code")


class CurrentWeather(TripSageBaseResponse):
    """Current weather data."""

    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature in Celsius")
    temp_min: float = Field(..., description="Minimum temperature in Celsius")
    temp_max: float = Field(..., description="Maximum temperature in Celsius")
    humidity: int = Field(..., description="Humidity percentage")
    pressure: int = Field(..., description="Atmospheric pressure in hPa")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_direction: float = Field(..., description="Wind direction in degrees")
    clouds: int = Field(..., description="Cloud coverage percentage")
    weather: WeatherCondition = Field(..., description="Weather condition")
    location: Dict[str, Any] = Field(..., description="Location information")
    timestamp: int = Field(..., description="Timestamp in seconds")
    source: str = Field(..., description="Data source")


class ForecastInterval(TripSageModel):
    """Weather forecast for a specific time interval."""

    timestamp: int = Field(..., description="Timestamp in seconds")
    time: str = Field(..., description="Time (HH:MM)")
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature in Celsius")
    temp_min: float = Field(..., description="Minimum temperature in Celsius")
    temp_max: float = Field(..., description="Maximum temperature in Celsius")
    humidity: int = Field(..., description="Humidity percentage")
    pressure: int = Field(..., description="Atmospheric pressure in hPa")
    wind_speed: float = Field(..., description="Wind speed in m/s")
    wind_direction: float = Field(..., description="Wind direction in degrees")
    clouds: int = Field(..., description="Cloud coverage percentage")
    weather: WeatherCondition = Field(..., description="Weather condition")


class DailyForecast(TripSageModel):
    """Daily weather forecast aggregation."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    temp_min: float = Field(..., description="Minimum temperature in Celsius")
    temp_max: float = Field(..., description="Maximum temperature in Celsius")
    temp_avg: float = Field(..., description="Average temperature in Celsius")
    humidity_avg: float = Field(..., description="Average humidity percentage")
    weather: WeatherCondition = Field(
        ..., description="Representative weather condition"
    )
    intervals: List[ForecastInterval] = Field(
        ..., description="Forecast intervals for the day"
    )


class WeatherForecast(TripSageBaseResponse):
    """Weather forecast data."""

    location: Dict[str, Any] = Field(..., description="Location information")
    daily: List[DailyForecast] = Field(..., description="Daily forecasts")
    source: str = Field(..., description="Data source")


class WeatherRecommendation(TripSageBaseResponse):
    """Travel recommendations based on weather conditions."""

    current_weather: Dict[str, Any] = Field(
        ..., description="Current weather information"
    )
    forecast: Dict[str, Any] = Field(..., description="Weather forecast information")
    recommendations: Dict[str, Any] = Field(..., description="Travel recommendations")


class TravelWeatherSummary(TripSageBaseResponse):
    """Weather summary for a travel period."""

    destination: str = Field(..., description="Travel destination")
    start_date: str = Field(..., description="Trip start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Trip end date (YYYY-MM-DD)")
    temperature: Dict[str, Optional[float]] = Field(
        ..., description="Temperature statistics"
    )
    conditions: Dict[str, Any] = Field(..., description="Weather conditions statistics")
    days: List[Dict[str, Any]] = Field(..., description="Daily weather data")
    error: Optional[str] = Field(None, description="Error message if any")


class DestinationWeatherComparison(TripSageBaseResponse):
    """Weather comparison across multiple destinations."""

    destinations: List[str] = Field(..., description="List of destinations compared")
    date: str = Field(..., description="Date for comparison or 'current'")
    results: List[Dict[str, Any]] = Field(..., description="Comparison results")
    ranking: Optional[List[str]] = Field(
        None, description="Destinations ranked by weather"
    )
    error: Optional[str] = Field(None, description="Error message if any")


class OptimalTravelTime(TripSageBaseResponse):
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
