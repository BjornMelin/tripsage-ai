"""Dependency injection for TripSage API.

This module provides FastAPI dependencies for injecting
MCP services and other components.
"""

from fastapi import Depends

from tripsage.mcp_abstraction import MCPManager, get_mcp_manager


# Dependency for MCP manager
async def get_mcp_manager_dep() -> MCPManager:
    """Get the MCP manager instance as a dependency.

    Returns:
        The singleton MCP manager instance
    """
    return get_mcp_manager()


# Example of using the MCP manager in an endpoint
from fastapi import APIRouter

router = APIRouter()


@router.get("/weather/{city}")
async def get_weather(
    city: str, mcp_manager: MCPManager = Depends(get_mcp_manager_dep)
):
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


# Example of specific MCP client dependency
async def get_weather_mcp(mcp_manager: MCPManager = Depends(get_mcp_manager_dep)):
    """Get the weather MCP wrapper as a dependency.

    Args:
        mcp_manager: Injected MCP manager instance

    Returns:
        The weather MCP wrapper
    """
    return await mcp_manager.initialize_mcp("weather")


# Using specific MCP in endpoint
@router.get("/weather/{city}/detailed")
async def get_detailed_weather(city: str, weather_mcp=Depends(get_weather_mcp)):
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
async def startup_event(mcp_manager: MCPManager = Depends(get_mcp_manager_dep)):
    """Initialize all enabled MCPs on startup.

    Args:
        mcp_manager: Injected MCP manager instance
    """
    await mcp_manager.initialize_all_enabled()

    # Log available MCPs
    available = mcp_manager.get_available_mcps()
    enabled = mcp_manager.get_enabled_mcps()

    print(f"Available MCPs: {available}")
    print(f"Enabled MCPs: {enabled}")


# Example of cleanup on shutdown
async def shutdown_event(mcp_manager: MCPManager = Depends(get_mcp_manager_dep)):
    """Cleanup MCP connections on shutdown.

    Args:
        mcp_manager: Injected MCP manager instance
    """
    await mcp_manager.shutdown()
