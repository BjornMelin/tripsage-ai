"""
TripSage centralized configuration using Pydantic Settings.

This module provides a centralized configuration system for the TripSage application,
replacing scattered configuration files with a unified settings class based on Pydantic.
All application settings are loaded from environment variables or a .env file.
"""

from typing import Any, Dict, Optional

from pydantic import (
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


class NeonMCPConfig(MCPConfig):
    """Neon MCP server configuration."""

    # Whether to use this MCP in development environment only
    dev_only: bool = Field(default=True)
    # Default project ID for operations (optional)
    default_project_id: Optional[str] = None


class SupabaseMCPConfig(MCPConfig):
    """Supabase MCP server configuration."""

    # Whether to use this MCP in production environment only
    prod_only: bool = Field(default=True)
    # Default project ID for operations (optional)
    default_project_id: Optional[str] = None
    # Default organization ID (optional)
    default_organization_id: Optional[str] = None


class WeatherMCPConfig(MCPConfig):
    """Weather MCP server configuration."""

    openweathermap_api_key: SecretStr
    visual_crossing_api_key: Optional[SecretStr] = None


class WebCrawlMCPConfig(MCPConfig):
    """Web crawling MCP server configuration."""

    # Crawl4AI configuration
    crawl4ai_api_url: str = Field(default="http://localhost:8000/api")
    crawl4ai_api_key: SecretStr
    crawl4ai_auth_token: Optional[SecretStr] = None
    crawl4ai_timeout: int = Field(default=30000)  # 30 seconds
    crawl4ai_max_depth: int = Field(default=3)
    crawl4ai_default_format: str = Field(default="markdown")

    # FireCrawl configuration
    firecrawl_api_url: str = Field(default="https://api.firecrawl.dev/v1")
    firecrawl_api_key: SecretStr

    # Legacy fields
    playwright_mcp_endpoint: Optional[str] = None
    redis_url: Optional[str] = None


class PlaywrightMCPConfig(MCPConfig):
    """Playwright MCP server configuration from ExecuteAutomation."""

    headless: bool = Field(default=True)
    browser_type: str = Field(default="chromium")  # chromium, firefox, webkit
    slow_mo: int = Field(default=50)  # milliseconds
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    ignore_https_errors: bool = Field(default=False)
    timeout: int = Field(default=30000)  # 30 seconds
    navigation_timeout: int = Field(default=60000)  # 60 seconds
    record_video: bool = Field(default=False)
    record_har: bool = Field(default=False)
    trace: bool = Field(default=False)


class StagehandMCPConfig(MCPConfig):
    """Stagehand MCP server configuration from Browserbase."""

    browserbase_api_key: SecretStr
    browserbase_project_id: str
    stagehand_openai_api_key: Optional[SecretStr] = None
    headless: bool = Field(default=True)
    recovery_enabled: bool = Field(default=True)
    timeout: int = Field(default=30000)  # 30 seconds
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    local_cdp_url: Optional[str] = None  # For local browser connection


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
    """Flights MCP server configuration for ravinahp/flights-mcp.

    This configuration is used to connect to the ravinahp/flights-mcp server,
    which provides flight search functionality through the Duffel API.
    The server is read-only and does not support booking operations.
    """

    duffel_api_key: SecretStr
    server_type: str = Field(default="ravinahp/flights-mcp")


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

    default_timezone: Optional[str] = None  # IANA timezone name (e.g., "America/LA")
    use_system_timezone: bool = Field(default=True)
    format_24_hour: bool = Field(default=False)


class MemoryMCPConfig(MCPConfig):
    """Memory MCP server configuration."""

    pass


class SequentialThinkingMCPConfig(MCPConfig):
    """Sequential thinking MCP server configuration."""

    pass


class DockerMCPConfig(MCPConfig):
    """Docker MCP server configuration."""

    image_registry: Optional[str] = None
    default_timeout: int = Field(default=60000)  # 60 seconds
    socket_path: str = Field(default="/var/run/docker.sock")
    max_container_count: int = Field(default=10)
    privileged_mode: bool = Field(default=False)
    network_mode: str = Field(default="bridge")


class OpenAPIMCPConfig(MCPConfig):
    """OpenAPI MCP server configuration."""

    schema_url: Optional[str] = None
    authentication_type: str = Field(default="bearer")
    default_timeout: int = Field(default=30000)  # 30 seconds
    retry_count: int = Field(default=3)
    cache_schema: bool = Field(default=True)


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
    playwright_mcp: PlaywrightMCPConfig = PlaywrightMCPConfig()
    stagehand_mcp: StagehandMCPConfig = StagehandMCPConfig()
    flights_mcp: FlightsMCPConfig = FlightsMCPConfig()
    accommodations_mcp: AccommodationsMCPConfig = AccommodationsMCPConfig()
    google_maps_mcp: GoogleMapsMCPConfig = GoogleMapsMCPConfig()
    time_mcp: TimeMCPConfig = TimeMCPConfig()
    memory_mcp: MemoryMCPConfig = MemoryMCPConfig()
    sequential_thinking_mcp: SequentialThinkingMCPConfig = SequentialThinkingMCPConfig()
    calendar_mcp: CalendarMCPConfig = CalendarMCPConfig()
    docker_mcp: DockerMCPConfig = DockerMCPConfig()
    openapi_mcp: OpenAPIMCPConfig = OpenAPIMCPConfig()
    neon_mcp: NeonMCPConfig = NeonMCPConfig()
    supabase_mcp: SupabaseMCPConfig = SupabaseMCPConfig()

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
