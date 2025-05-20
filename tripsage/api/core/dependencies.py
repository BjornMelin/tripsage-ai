"""Dependency injection utilities for FastAPI.

This module provides dependency functions that can be used with FastAPI's
Depends() function to inject services and components into endpoint handlers.
"""

from fastapi import Depends

from tripsage.api.core.config import Settings, get_settings
from tripsage.mcp_abstraction import get_mcp_manager


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


# Create MCP dependencies
weather_mcp_dependency = Depends(get_weather_mcp_dep())


# Google Maps MCP dependency
def get_google_maps_mcp_dep():
    """Get the Google Maps MCP wrapper as a dependency."""
    
    async def _get_google_maps_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("googlemaps")
    
    return _get_google_maps_mcp


# Create Google Maps dependency
google_maps_mcp_dependency = Depends(get_google_maps_mcp_dep())


# Time MCP dependency
def get_time_mcp_dep():
    """Get the time MCP wrapper as a dependency."""
    
    async def _get_time_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("time")
    
    return _get_time_mcp


# Create time dependency
time_mcp_dependency = Depends(get_time_mcp_dep())


# Firecrawl MCP dependency
def get_firecrawl_mcp_dep():
    """Get the Firecrawl MCP wrapper as a dependency."""
    
    async def _get_firecrawl_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("firecrawl")
    
    return _get_firecrawl_mcp


# Create firecrawl dependency
firecrawl_mcp_dependency = Depends(get_firecrawl_mcp_dep())


# Memory MCP dependency
def get_memory_mcp_dep():
    """Get the memory MCP wrapper as a dependency."""
    
    async def _get_memory_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("memory")
    
    return _get_memory_mcp


# Create memory dependency
memory_mcp_dependency = Depends(get_memory_mcp_dep())


# Redis MCP dependency
def get_redis_mcp_dep():
    """Get the Redis MCP wrapper as a dependency."""
    
    async def _get_redis_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("redis")
    
    return _get_redis_mcp


# Create redis dependency
redis_mcp_dependency = Depends(get_redis_mcp_dep())