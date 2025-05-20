"""Dependency injection utilities for FastAPI.

This module provides dependency functions that can be used with FastAPI's
Depends() function to inject services and components into endpoint handlers.
"""

from fastapi import Depends

from tripsage.api.core.config import get_settings
from tripsage.mcp_abstraction import get_mcp_manager


# Create function for settings dependency
def get_settings_dependency():
    """Get settings dependency without function call in default argument."""
    return get_settings()


def get_mcp_manager_dependency():
    """Get the MCP manager instance as a dependency.

    Returns:
        The singleton MCP manager instance
    """
    return get_mcp_manager()


# Create singleton dependencies
mcp_manager_dependency = Depends(get_mcp_manager_dependency)
settings_dependency = Depends(get_settings)


# Weather MCP dependency
def get_weather_mcp_dep():
    """Get the weather MCP wrapper as a dependency."""

    async def _get_weather_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("weather")

    return _get_weather_mcp


# First create the functions that will be wrapped with Depends
weather_mcp_dep_fn = get_weather_mcp_dep()

# Create MCP dependencies
weather_mcp_dependency = Depends(weather_mcp_dep_fn)


# Google Maps MCP dependency
def get_google_maps_mcp_dep():
    """Get the Google Maps MCP wrapper as a dependency."""

    async def _get_google_maps_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("googlemaps")

    return _get_google_maps_mcp


# Create the Google Maps function
google_maps_mcp_dep_fn = get_google_maps_mcp_dep()

# Create Google Maps dependency
google_maps_mcp_dependency = Depends(google_maps_mcp_dep_fn)


# Time MCP dependency
def get_time_mcp_dep():
    """Get the time MCP wrapper as a dependency."""

    async def _get_time_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("time")

    return _get_time_mcp


# Create the time function
time_mcp_dep_fn = get_time_mcp_dep()

# Create time dependency
time_mcp_dependency = Depends(time_mcp_dep_fn)


# Firecrawl MCP dependency
def get_firecrawl_mcp_dep():
    """Get the Firecrawl MCP wrapper as a dependency."""

    async def _get_firecrawl_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("firecrawl")

    return _get_firecrawl_mcp


# Create the firecrawl function
firecrawl_mcp_dep_fn = get_firecrawl_mcp_dep()

# Create firecrawl dependency
firecrawl_mcp_dependency = Depends(firecrawl_mcp_dep_fn)


# Memory MCP dependency
def get_memory_mcp_dep():
    """Get the memory MCP wrapper as a dependency."""

    async def _get_memory_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("memory")

    return _get_memory_mcp


# Create the memory function
memory_mcp_dep_fn = get_memory_mcp_dep()

# Create memory dependency
memory_mcp_dependency = Depends(memory_mcp_dep_fn)


# Redis MCP dependency
def get_redis_mcp_dep():
    """Get the Redis MCP wrapper as a dependency."""

    async def _get_redis_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("redis")

    return _get_redis_mcp


# Create the redis function
redis_mcp_dep_fn = get_redis_mcp_dep()

# Create redis dependency
redis_mcp_dependency = Depends(redis_mcp_dep_fn)
