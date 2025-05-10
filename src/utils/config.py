"""
Configuration utilities for TripSage.

This module provides functions to load and manage application configuration
from environment variables and configuration files.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class RedisConfig(BaseModel):
    """Redis configuration settings."""
    url: str = Field(env="REDIS_URL", default="redis://localhost:6379/0")
    ttl_short: int = 300  # 5 minutes
    ttl_medium: int = 3600  # 1 hour
    ttl_long: int = 86400  # 24 hours


class SupabaseConfig(BaseModel):
    """Supabase configuration settings."""
    url: str = Field(env="SUPABASE_URL")
    anon_key: str = Field(env="SUPABASE_ANON_KEY") 
    service_role_key: str = Field(env="SUPABASE_SERVICE_ROLE_KEY")


class MCPConfig(BaseModel):
    """Base class for MCP server configuration."""
    endpoint: str
    api_key: str


class WeatherMCPConfig(MCPConfig):
    """Weather MCP server configuration."""
    endpoint: str = Field(env="WEATHER_MCP_ENDPOINT")
    api_key: str = Field(env="WEATHER_MCP_API_KEY")
    openweathermap_api_key: str = Field(env="OPENWEATHERMAP_API_KEY")
    visual_crossing_api_key: Optional[str] = Field(env="VISUAL_CROSSING_API_KEY", default=None)


class WebCrawlMCPConfig(MCPConfig):
    """Web crawling MCP server configuration."""
    endpoint: str = Field(env="WEBCRAWL_MCP_ENDPOINT")
    api_key: str = Field(env="WEBCRAWL_MCP_API_KEY")


class BrowserMCPConfig(MCPConfig):
    """Browser automation MCP server configuration."""
    endpoint: str = Field(env="BROWSER_MCP_ENDPOINT")
    api_key: str = Field(env="BROWSER_MCP_API_KEY")


class FlightsMCPConfig(MCPConfig):
    """Flights MCP server configuration."""
    endpoint: str = Field(env="FLIGHTS_MCP_ENDPOINT")
    api_key: str = Field(env="FLIGHTS_MCP_API_KEY")
    duffel_api_key: str = Field(env="DUFFEL_API_KEY")


class AccommodationsMCPConfig(MCPConfig):
    """Accommodations MCP server configuration."""
    endpoint: str = Field(env="AIRBNB_MCP_ENDPOINT")
    api_key: str = Field(env="AIRBNB_MCP_API_KEY")


class GoogleMapsMCPConfig(MCPConfig):
    """Google Maps MCP server configuration."""
    endpoint: str = Field(env="GOOGLE_MAPS_MCP_ENDPOINT")
    api_key: str = Field(env="GOOGLE_MAPS_MCP_API_KEY")
    maps_api_key: str = Field(env="GOOGLE_MAPS_API_KEY")


class TimeMCPConfig(MCPConfig):
    """Time MCP server configuration."""
    endpoint: str = Field(env="TIME_MCP_ENDPOINT")
    api_key: str = Field(env="TIME_MCP_API_KEY")


class MemoryMCPConfig(MCPConfig):
    """Memory MCP server configuration."""
    endpoint: str = Field(env="MEMORY_MCP_ENDPOINT")
    api_key: str = Field(env="MEMORY_MCP_API_KEY")


class SequentialThinkingMCPConfig(MCPConfig):
    """Sequential thinking MCP server configuration."""
    endpoint: str = Field(env="SEQ_THINKING_MCP_ENDPOINT")
    api_key: str = Field(env="SEQ_THINKING_MCP_API_KEY")


class ApplicationConfig(BaseModel):
    """Main application configuration."""
    # Application settings
    debug: bool = Field(env="DEBUG", default=False)
    environment: str = Field(env="NODE_ENV", default="development")
    port: int = Field(env="PORT", default=8000)
    
    # API Keys
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    
    # Model Configuration
    model_name: str = Field(env="MODEL_NAME", default="gpt-4")
    
    # Supabase
    supabase: SupabaseConfig = SupabaseConfig()
    
    # Redis
    redis: RedisConfig = RedisConfig()
    
    # MCP Servers
    weather_mcp: WeatherMCPConfig = WeatherMCPConfig()
    webcrawl_mcp: WebCrawlMCPConfig = WebCrawlMCPConfig()
    browser_mcp: BrowserMCPConfig = BrowserMCPConfig()
    flights_mcp: FlightsMCPConfig = FlightsMCPConfig()
    accommodations_mcp: AccommodationsMCPConfig = AccommodationsMCPConfig()
    google_maps_mcp: GoogleMapsMCPConfig = GoogleMapsMCPConfig()
    time_mcp: TimeMCPConfig = TimeMCPConfig()
    memory_mcp: MemoryMCPConfig = MemoryMCPConfig()
    sequential_thinking_mcp: SequentialThinkingMCPConfig = SequentialThinkingMCPConfig()


# Create global application config
config = ApplicationConfig()


def get_config() -> ApplicationConfig:
    """Get the application configuration.
    
    Returns:
        The application configuration instance
    """
    return config