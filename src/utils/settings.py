"""
TripSage centralized configuration using Pydantic Settings.

This module provides a centralized configuration system for the TripSage application,
replacing scattered configuration files with a unified settings class based on Pydantic.
All application settings are loaded from environment variables or a .env file.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import (
    AmqpDsn,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisConfig(BaseSettings):
    """Redis configuration settings."""

    url: RedisDsn = Field(default="redis://localhost:6379/0")
    ttl_short: int = Field(default=300)  # 5 minutes
    ttl_medium: int = Field(default=3600)  # 1 hour
    ttl_long: int = Field(default=86400)  # 24 hours


class DatabaseConfig(BaseSettings):
    """Database configuration for PostgreSQL connections."""

    # Supabase configuration
    supabase_url: str = Field(...)
    supabase_anon_key: SecretStr = Field(...)
    supabase_service_role_key: Optional[SecretStr] = Field(default=None)
    supabase_timeout: float = Field(default=60.0)
    supabase_auto_refresh_token: bool = Field(default=True)
    supabase_persist_session: bool = Field(default=True)

    # Neon configuration
    neon_connection_string: Optional[PostgresDsn] = Field(default=None)
    neon_min_pool_size: int = Field(default=1)
    neon_max_pool_size: int = Field(default=10)
    neon_max_inactive_connection_lifetime: float = Field(default=300.0)

    # Provider selection
    db_provider: str = Field(default="supabase")  # "supabase" or "neon"


class Neo4jConfig(BaseSettings):
    """Neo4j database configuration."""

    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: SecretStr = Field(...)
    database: str = Field(default="neo4j")
    max_connection_lifetime: int = Field(default=3600)
    max_connection_pool_size: int = Field(default=50)
    connection_acquisition_timeout: int = Field(default=60)
    default_query_timeout: int = Field(default=60)


class MCPConfig(BaseSettings):
    """Base configuration for MCP servers."""

    endpoint: str
    api_key: Optional[SecretStr] = None


class WeatherMCPConfig(MCPConfig):
    """Weather MCP server configuration."""

    openweathermap_api_key: SecretStr
    visual_crossing_api_key: Optional[SecretStr] = None


class WebCrawlMCPConfig(MCPConfig):
    """Web crawling MCP server configuration."""

    crawl4ai_api_url: str = Field(default="http://localhost:8000/api")
    crawl4ai_api_key: SecretStr
    playwright_mcp_endpoint: Optional[str] = None


class BrowserMCPConfig(BaseSettings):
    """Browser automation MCP server configuration."""

    endpoint: str
    api_key: Optional[SecretStr] = None
    headless: bool = Field(default=True)
    slow_mo: int = Field(default=50)  # milliseconds
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    ignore_https_errors: bool = Field(default=False)
    default_timeout: int = Field(default=30000)  # 30 seconds
    navigation_timeout: int = Field(default=60000)  # 60 seconds
    context_max_idle_time: int = Field(default=300)  # 5 minutes
    context_cleanup_interval: int = Field(default=60)  # 1 minute
    max_contexts: int = Field(default=10)
    geolocation_enabled: bool = Field(default=False)


class FlightsMCPConfig(MCPConfig):
    """Flights MCP server configuration."""

    duffel_api_key: SecretStr


class AirbnbMCPConfig(MCPConfig):
    """Airbnb MCP server configuration."""

    endpoint: str = Field(default="http://localhost:3000")
    api_key: Optional[SecretStr] = None  # Airbnb MCP doesn't use API keys
    ignore_robots_txt: bool = Field(default=False)


class AccommodationsMCPConfig(BaseSettings):
    """Accommodations MCP server configuration."""

    airbnb: AirbnbMCPConfig = AirbnbMCPConfig()


class GoogleMapsMCPConfig(MCPConfig):
    """Google Maps MCP server configuration."""

    maps_api_key: SecretStr


class TimeMCPConfig(MCPConfig):
    """Time MCP server configuration."""

    pass


class MemoryMCPConfig(MCPConfig):
    """Memory MCP server configuration."""

    pass


class SequentialThinkingMCPConfig(MCPConfig):
    """Sequential thinking MCP server configuration."""

    pass


class CalendarMCPConfig(MCPConfig):
    """Calendar MCP server configuration."""

    google_client_id: SecretStr
    google_client_secret: SecretStr
    google_redirect_uri: str


class AgentConfig(BaseSettings):
    """Configuration settings for TripSage agents."""

    model_name: str = Field(default="gpt-4o")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.7)
    agent_timeout: int = Field(default=120)  # seconds
    max_retries: int = Field(default=3)
    agent_memory_size: int = Field(default=10)  # number of messages

    default_flight_preferences: Dict[str, Any] = Field(
        default={
            "seat_class": "economy",
            "max_stops": 1,
            "preferred_airlines": [],
            "avoid_airlines": [],
            "time_window": "flexible",
        }
    )

    default_accommodation_preferences: Dict[str, Any] = Field(
        default={
            "property_type": "hotel",
            "min_rating": 3.5,
            "amenities": ["wifi", "breakfast"],
            "location_preference": "city_center",
        }
    )


class AppSettings(BaseSettings):
    """
    Main application settings for TripSage.

    This class centralizes all configuration across the application.
    Settings are loaded from environment variables or a .env file.
    """

    # Configure the settings behavior
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application settings
    debug: bool = Field(default=False)
    environment: str = Field(default="development")
    port: int = Field(default=8000)

    # API Keys
    openai_api_key: SecretStr

    # Storage
    database: DatabaseConfig = DatabaseConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
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
    calendar_mcp: CalendarMCPConfig = CalendarMCPConfig()

    # Agent configuration
    agent: AgentConfig = AgentConfig()

    @field_validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        allowed_environments = {"development", "testing", "staging", "production"}
        if v not in allowed_environments:
            raise ValueError(
                f"Environment must be one of {allowed_environments}, got {v}"
            )
        return v


# Create singleton instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """
    Return the application settings instance.

    This function provides a clean way to access the settings
    throughout the application.

    Returns:
        The AppSettings instance
    """
    return settings