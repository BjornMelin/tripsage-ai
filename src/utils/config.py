"""
Configuration utilities for TripSage.

This module provides backward compatibility with the old configuration system.
It delegates to the new centralized settings module.
"""

import warnings
from typing import Any, Dict, Optional

from .settings import settings

# Issue deprecation warning
warnings.warn(
    "The config module is deprecated and will be removed in a future version. "
    "Use the settings module instead.",
    DeprecationWarning,
    stacklevel=2,
)


def get_config() -> Dict[str, Any]:
    """
    Get the application configuration.

    This function is provided for backward compatibility and delegates to the
    new settings module. New code should use the settings module directly.

    Returns:
        A dictionary containing the application configuration.
    """
    return {
        # Application settings
        "DEBUG": settings.debug,
        "NODE_ENV": settings.environment,
        "PORT": settings.port,
        
        # OpenAI settings
        "OPENAI_API_KEY": settings.openai_api_key.get_secret_value(),
        "MODEL_NAME": settings.agent.model_name,
        
        # Supabase
        "SUPABASE_URL": settings.database.supabase_url,
        "SUPABASE_ANON_KEY": settings.database.supabase_anon_key.get_secret_value(),
        "SUPABASE_SERVICE_ROLE_KEY": settings.database.supabase_service_role_key.get_secret_value() if settings.database.supabase_service_role_key else None,
        
        # Neo4j
        "NEO4J_URI": settings.neo4j.uri,
        "NEO4J_USER": settings.neo4j.user,
        "NEO4J_PASSWORD": settings.neo4j.password.get_secret_value(),
        "NEO4J_DATABASE": settings.neo4j.database,
        "NEO4J_MAX_CONNECTION_LIFETIME": settings.neo4j.max_connection_lifetime,
        "NEO4J_MAX_CONNECTION_POOL_SIZE": settings.neo4j.max_connection_pool_size,
        "NEO4J_CONNECTION_ACQUISITION_TIMEOUT": settings.neo4j.connection_acquisition_timeout,
        "NEO4J_DEFAULT_QUERY_TIMEOUT": settings.neo4j.default_query_timeout,
        
        # Redis
        "REDIS_URL": str(settings.redis.url),
        
        # Weather MCP
        "WEATHER_MCP_ENDPOINT": settings.weather_mcp.endpoint,
        "WEATHER_MCP_API_KEY": settings.weather_mcp.api_key.get_secret_value() if settings.weather_mcp.api_key else None,
        "OPENWEATHERMAP_API_KEY": settings.weather_mcp.openweathermap_api_key.get_secret_value(),
        "VISUAL_CROSSING_API_KEY": settings.weather_mcp.visual_crossing_api_key.get_secret_value() if settings.weather_mcp.visual_crossing_api_key else None,
        
        # Web Crawl MCP
        "WEBCRAWL_MCP_ENDPOINT": settings.webcrawl_mcp.endpoint,
        "WEBCRAWL_MCP_API_KEY": settings.webcrawl_mcp.api_key.get_secret_value() if settings.webcrawl_mcp.api_key else None,
        
        # Browser MCP
        "BROWSER_MCP_ENDPOINT": settings.browser_mcp.endpoint,
        "BROWSER_MCP_API_KEY": settings.browser_mcp.api_key.get_secret_value() if settings.browser_mcp.api_key else None,
        
        # Flights MCP
        "FLIGHTS_MCP_ENDPOINT": settings.flights_mcp.endpoint,
        "FLIGHTS_MCP_API_KEY": settings.flights_mcp.api_key.get_secret_value() if settings.flights_mcp.api_key else None,
        "DUFFEL_API_KEY": settings.flights_mcp.duffel_api_key.get_secret_value(),
        
        # Google Maps MCP
        "GOOGLE_MAPS_MCP_ENDPOINT": settings.google_maps_mcp.endpoint,
        "GOOGLE_MAPS_MCP_API_KEY": settings.google_maps_mcp.api_key.get_secret_value() if settings.google_maps_mcp.api_key else None,
        "GOOGLE_MAPS_API_KEY": settings.google_maps_mcp.maps_api_key.get_secret_value(),
        
        # Time MCP
        "TIME_MCP_ENDPOINT": settings.time_mcp.endpoint,
        "TIME_MCP_API_KEY": settings.time_mcp.api_key.get_secret_value() if settings.time_mcp.api_key else None,
        
        # Memory MCP
        "MEMORY_MCP_ENDPOINT": settings.memory_mcp.endpoint,
        "MEMORY_MCP_API_KEY": settings.memory_mcp.api_key.get_secret_value() if settings.memory_mcp.api_key else None,
        
        # Sequential Thinking MCP
        "SEQ_THINKING_MCP_ENDPOINT": settings.sequential_thinking_mcp.endpoint,
        "SEQ_THINKING_MCP_API_KEY": settings.sequential_thinking_mcp.api_key.get_secret_value() if settings.sequential_thinking_mcp.api_key else None,
    }


# Mock compatibility classes for code that expects the old config structure
class _ConfigClass:
    def __getattr__(self, name: str) -> Any:
        return get_config().get(name.upper(), None)


class _WeatherMCPConfig:
    openweathermap_api_key = settings.weather_mcp.openweathermap_api_key.get_secret_value()
    endpoint = settings.weather_mcp.endpoint
    api_key = settings.weather_mcp.api_key.get_secret_value() if settings.weather_mcp.api_key else None
    visual_crossing_api_key = settings.weather_mcp.visual_crossing_api_key.get_secret_value() if settings.weather_mcp.visual_crossing_api_key else None


# Mock the old configuration structure
config = _ConfigClass()
config.weather_mcp = _WeatherMCPConfig()