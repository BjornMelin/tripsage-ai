"""
Settings utilities for TripSage.

This module provides the main settings management for TripSage,
including environment-specific configuration and secrets handling.
"""

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseModel):
    """Base settings for MCP connections."""

    endpoint: str
    api_key: Optional[SecretStr] = None
    timeout: float = 30.0
    use_cache: bool = True
    cache_ttl: int = 3600  # 1 hour


class TimeMCPSettings(MCPSettings):
    """Time MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3000", description="Time MCP server endpoint"
    )
    cache_ttl: int = Field(1800, description="Cache TTL in seconds")  # 30 minutes


class WeatherMCPSettings(MCPSettings):
    """Weather MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3001", description="Weather MCP server endpoint"
    )
    openweathermap_api_key: Optional[SecretStr] = Field(
        None, description="OpenWeatherMap API key"
    )


class GoogleMapsMCPSettings(MCPSettings):
    """Google Maps MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3002", description="Google Maps MCP server endpoint"
    )
    google_maps_api_key: Optional[SecretStr] = Field(
        None, description="Google Maps API key"
    )


class MemoryMCPSettings(MCPSettings):
    """Memory MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3003", description="Memory MCP server endpoint"
    )


class WebCrawlMCPSettings(MCPSettings):
    """WebCrawl MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3004", description="WebCrawl MCP server endpoint"
    )
    firecrawl_api_key: Optional[SecretStr] = Field(
        None, description="FireCrawl API key"
    )


class FlightsMCPSettings(MCPSettings):
    """Flights MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3005", description="Flights MCP server endpoint"
    )
    duffel_api_key: Optional[SecretStr] = Field(None, description="Duffel API key")


class AccommodationsMCPSettings(MCPSettings):
    """Accommodations MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3006",
        description="Accommodations MCP server endpoint",
    )


class SupabaseMCPSettings(MCPSettings):
    """Supabase MCP settings."""

    endpoint: str = Field(
        default="http://localhost:3007", description="Supabase MCP server endpoint"
    )
    project_url: Optional[str] = Field(None, description="Supabase project URL")
    api_key: Optional[SecretStr] = Field(None, description="Supabase API key")


class DatabaseMCPSettings(BaseModel):
    """Database MCP settings."""

    supabase: SupabaseMCPSettings = Field(default_factory=SupabaseMCPSettings)


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__"
    )

    # Application settings
    app_name: str = "TripSage"
    debug: bool = False
    environment: str = "development"  # development, testing, staging, production
    log_level: str = "INFO"

    # MCP settings with defaults
    time_mcp: TimeMCPSettings = Field(default_factory=TimeMCPSettings)
    weather_mcp: WeatherMCPSettings = Field(default_factory=WeatherMCPSettings)
    googlemaps_mcp: GoogleMapsMCPSettings = Field(default_factory=GoogleMapsMCPSettings)
    memory_mcp: MemoryMCPSettings = Field(default_factory=MemoryMCPSettings)
    webcrawl_mcp: WebCrawlMCPSettings = Field(default_factory=WebCrawlMCPSettings)
    flights_mcp: FlightsMCPSettings = Field(default_factory=FlightsMCPSettings)
    accommodations_mcp: AccommodationsMCPSettings = Field(
        default_factory=AccommodationsMCPSettings
    )
    database: DatabaseMCPSettings = Field(default_factory=DatabaseMCPSettings)

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Cache settings
    redis_url: Optional[str] = None
    use_cache: bool = True


@lru_cache()
def get_settings() -> AppSettings:
    """Get the application settings.

    Returns:
        Application settings instance
    """
    return AppSettings()  # type: ignore


# Export settings for convenience
settings = get_settings()
