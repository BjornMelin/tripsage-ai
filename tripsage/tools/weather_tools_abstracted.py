"""Weather tool implementations using the MCP abstraction layer.

This is an example of how to use the unified MCP abstraction layer
to interact with weather services.
"""

from typing import Optional

from agents import function_tool
from pydantic import BaseModel, Field

from tripsage.mcp_abstraction import mcp_manager
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class WeatherRequest(BaseModel):
    """Standard weather request parameters."""

    city: str = Field(..., description="City name for weather data")
    country_code: Optional[str] = Field(None, description="Country code (e.g., US, UK)")
    units: str = Field("metric", description="Temperature units (metric or imperial)")


class WeatherResponse(BaseModel):
    """Standard weather response."""

    temperature: float
    feels_like: float
    description: str
    humidity: int
    wind_speed: float
    units: str


@function_tool
@with_error_handling(operation="get_current_weather")
async def get_current_weather_abstracted(
    city: str, country_code: Optional[str] = None, units: str = "metric"
) -> WeatherResponse:
    """Get current weather conditions for a city using the abstraction layer.

    Args:
        city: Name of the city
        country_code: Optional country code (e.g., 'US', 'GB')
        units: Temperature units ('metric' or 'imperial')

    Returns:
        WeatherResponse with current weather conditions
    """
    # Use the MCP manager to invoke the weather service
    result = await mcp_manager.invoke(
        mcp_name="weather",
        method_name="get_current_weather",
        params={"city": city, "country_code": country_code, "units": units},
    )

    # The result is already validated by the MCP client
    return WeatherResponse(
        temperature=result.temperature,
        feels_like=result.feels_like,
        description=result.description,
        humidity=result.humidity,
        wind_speed=result.wind_speed,
        units=units,
    )


@function_tool
@with_error_handling(operation="get_weather_forecast")
async def get_weather_forecast_abstracted(
    city: str, days: int = 7, country_code: Optional[str] = None, units: str = "metric"
) -> list[dict]:
    """Get weather forecast for a city using the abstraction layer.

    Args:
        city: Name of the city
        days: Number of days to forecast (1-7)
        country_code: Optional country code
        units: Temperature units

    Returns:
        List of daily forecasts
    """
    # Use the MCP manager to invoke the weather service
    result = await mcp_manager.invoke(
        mcp_name="weather",
        method_name="get_daily_forecast",
        params={
            "city": city,
            "days": days,
            "country_code": country_code,
            "units": units,
        },
    )

    # Convert to standard format
    forecasts = []
    for day in result.daily:
        forecasts.append(
            {
                "date": day.date,
                "temp_min": day.temp_min,
                "temp_max": day.temp_max,
                "description": day.description,
                "precipitation": day.precipitation,
                "humidity": day.humidity,
            }
        )

    return forecasts


# Example of checking available methods
async def check_weather_capabilities() -> list[str]:
    """Check what weather capabilities are available.

    Returns:
        List of available weather method names
    """
    wrapper = await mcp_manager.initialize_mcp("weather")
    return wrapper.get_available_methods()


# Example of direct wrapper access for advanced usage
async def get_weather_wrapper():
    """Get direct access to the weather wrapper.

    Returns:
        The weather MCP wrapper instance
    """
    return await mcp_manager.initialize_mcp("weather")
