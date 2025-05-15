"""Dependency injection for TripSage API.

This module provides FastAPI dependencies for injecting
MCP services and other components.
"""

from fastapi import APIRouter, Depends

from tripsage.mcp_abstraction import get_mcp_manager

# Router for API endpoints
router = APIRouter()


# Create dependency functions
def get_mcp_manager_dep():
    """Get the MCP manager instance as a dependency.

    Returns:
        The singleton MCP manager instance
    """
    return get_mcp_manager()


# Create singleton dependencies
mcp_manager_dependency = Depends(get_mcp_manager_dep)


# Weather MCP dependency
def get_weather_mcp_dep():
    """Get the weather MCP wrapper as a dependency."""

    async def _get_weather_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("weather")

    return _get_weather_mcp


# Create weather dependency singleton
weather_mcp_dependency = Depends(get_weather_mcp_dep())


# Example of using the MCP manager in an endpoint
@router.get("/weather/{city}")
async def get_weather(city: str, mcp_manager=mcp_manager_dependency):
    """Get weather for a city using dependency injection.

    Args:
        city: Name of the city
        mcp_manager: Injected MCP manager instance

    Returns:
        Weather data for the city
    """
    result = await mcp_manager.invoke(
        mcp_name="weather", method_name="get_current_weather", params={"city": city}
    )

    return {
        "city": city,
        "temperature": result.temperature,
        "description": result.description,
        "humidity": result.humidity,
    }


# Using specific MCP in endpoint
@router.get("/weather/{city}/detailed")
async def get_detailed_weather(city: str, weather_mcp=weather_mcp_dependency):
    """Get detailed weather using specific MCP wrapper.

    Args:
        city: Name of the city
        weather_mcp: Injected weather MCP wrapper

    Returns:
        Detailed weather data
    """
    # Direct wrapper access for more control
    current = await weather_mcp.invoke_method(
        "get_current_weather", params={"city": city}
    )

    forecast = await weather_mcp.invoke_method(
        "get_forecast", params={"city": city, "days": 3}
    )

    return {"current": current, "forecast": forecast}


# Example of initialization on startup
async def startup_event():
    """Initialize all enabled MCPs on startup."""
    mcp_manager = get_mcp_manager_dep()
    await mcp_manager.initialize_all_enabled()

    # Log available MCPs
    available = mcp_manager.get_available_mcps()
    enabled = mcp_manager.get_enabled_mcps()

    print(f"Available MCPs: {available}")
    print(f"Enabled MCPs: {enabled}")


# Example of cleanup on shutdown
async def shutdown_event():
    """Cleanup MCP connections on shutdown."""
    mcp_manager = get_mcp_manager_dep()
    await mcp_manager.shutdown()
