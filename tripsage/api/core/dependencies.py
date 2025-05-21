"""Dependency injection utilities for FastAPI.

This module provides dependency functions that can be used with FastAPI's
Depends() function to inject services and components into endpoint handlers.
"""

from typing import Any, Dict

from fastapi import Depends

from tripsage.api.core.config import get_settings
from tripsage.mcp_abstraction import mcp_manager
from tripsage.utils.session_memory import initialize_session_memory


# Create function for settings dependency
def get_settings_dependency():
    """Get settings dependency without function call in default argument."""
    return get_settings()


def get_mcp_manager_dependency():
    """Get the MCP manager instance as a dependency.

    Returns:
        The singleton MCP manager instance
    """
    return mcp_manager


# Session memory dependency
_session_memory = {}


def get_session_memory() -> Dict[str, Any]:
    """Get the session memory.

    This dependency provides access to temporary memory for the current session.

    Returns:
        Dictionary with session memory data
    """
    return _session_memory


async def initialize_memory_for_user(user_id: str) -> Dict[str, Any]:
    """Initialize memory for a specific user.

    Args:
        user_id: The user ID

    Returns:
        The initialized session memory
    """
    session_data = await initialize_session_memory(user_id)
    _session_memory.update(session_data)
    return _session_memory


# Create singleton dependencies
mcp_manager_dependency = Depends(get_mcp_manager_dependency)
settings_dependency = Depends(get_settings)
session_memory_dependency = Depends(get_session_memory)


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
