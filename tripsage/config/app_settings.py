"""
Application settings module for TripSage.

This module provides the main application settings class using Pydantic
for validation and loading from environment variables.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import (
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# MCP Configuration Classes
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


class PlaywrightMCPConfig(MCPConfig):
    """Playwright MCP server configuration."""

    headless: bool = Field(default=True)
    browser_type: str = Field(default="chromium")  # chromium, firefox, webkit
    slow_mo: int = Field(default=50)  # milliseconds
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    ignore_https_errors: bool = Field(default=False)
    timeout: int = Field(default=30000)  # 30 seconds
    navigation_timeout: int = Field(default=60000)  # 60 seconds


class FlightsMCPConfig(MCPConfig):
    """Flights MCP server configuration."""

    duffel_api_key: SecretStr
    server_type: str = Field(default="ravinahp/flights-mcp")


class AirbnbMCPConfig(MCPConfig):
    """OpenBnB Airbnb MCP server configuration."""

    endpoint: str = Field(
        default="http://localhost:3000", description="OpenBnB MCP server endpoint"
    )
    api_key: Optional[SecretStr] = None  # OpenBnB Airbnb MCP doesn't use API keys
    ignore_robots_txt: bool = Field(
        default=False, description="Whether to ignore robots.txt restrictions"
    )
    server_type: str = Field(
        default="openbnb/mcp-server-airbnb", description="Server implementation type"
    )


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


class CalendarMCPConfig(MCPConfig):
    """Calendar MCP server configuration."""

    google_client_id: SecretStr
    google_client_secret: SecretStr
    google_redirect_uri: str


# Database Configuration Classes
class WebCacheTTLConfig(BaseSettings):
    """TTL configuration for different content types in the web cache."""

    realtime: int = Field(default=100, description="TTL for real-time data (100s)")
    time_sensitive: int = Field(
        default=300, description="TTL for time-sensitive data (5m)"
    )
    daily: int = Field(default=3600, description="TTL for daily-changing data (1h)")
    semi_static: int = Field(default=28800, description="TTL for semi-static data (8h)")
    static: int = Field(default=86400, description="TTL for static data (24h)")


class RedisConfig(BaseSettings):
    """Redis configuration settings."""

    url: RedisDsn = Field(default="redis://localhost:6379/0")
    ttl_short: int = Field(default=300)  # 5 minutes
    ttl_medium: int = Field(default=3600)  # 1 hour
    ttl_long: int = Field(default=86400)  # 24 hours
    web_cache: WebCacheTTLConfig = WebCacheTTLConfig()


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


# Agent Configuration Classes
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


# Main Application Settings
class AppSettings(BaseSettings):
    """
    Main application settings for TripSage.

    This class centralizes all configuration across the application.
    Settings are loaded from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Application settings
    app_name: str = "TripSage"
    debug: bool = Field(False, description="Enable debug mode")
    environment: str = Field(
        "development",
        description="Environment (development, testing, staging, production)",
    )
    log_level: str = Field("INFO", description="Logging level")
    port: int = Field(default=8000, description="API port")
    api_host: str = Field("0.0.0.0", description="API host")

    # Base paths
    base_dir: str = Field(
        str(Path(__file__).parent.parent.parent.absolute()),
        description="Base directory of the application",
    )

    # OpenAI settings
    openai_api_key: SecretStr = Field(..., description="OpenAI API key")

    # Storage
    database: DatabaseConfig = DatabaseConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    redis: RedisConfig = RedisConfig()

    # Cache settings
    use_cache: bool = Field(True, description="Enable caching")

    # MCP Servers
    time_mcp: TimeMCPConfig = TimeMCPConfig()
    weather_mcp: WeatherMCPConfig = WeatherMCPConfig()
    googlemaps_mcp: GoogleMapsMCPConfig = GoogleMapsMCPConfig()
    memory_mcp: MemoryMCPConfig = MemoryMCPConfig()
    webcrawl_mcp: WebCrawlMCPConfig = WebCrawlMCPConfig()
    flights_mcp: FlightsMCPConfig = FlightsMCPConfig()
    accommodations_mcp: AccommodationsMCPConfig = AccommodationsMCPConfig()
    playwright_mcp: PlaywrightMCPConfig = PlaywrightMCPConfig()
    calendar_mcp: CalendarMCPConfig = CalendarMCPConfig()
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

    def get_mcp_url_for_type(self, client_type: str) -> str:
        """Get the MCP endpoint URL for a given client type.

        Args:
            client_type: The client type name (e.g., 'FlightMCPClient')

        Returns:
            The MCP endpoint URL.
        """
        client_type_lower = client_type.lower()

        # Map client types to MCP config attributes
        mcp_map = {
            "flightmcpclient": self.flights_mcp.endpoint,
            "accommodationmcpclient": self.accommodations_mcp.airbnb.endpoint,
            "googlemapsmcpclient": self.googlemaps_mcp.endpoint,
            "memorymcpclient": self.memory_mcp.endpoint,
            "webcrawlmcpclient": self.webcrawl_mcp.endpoint,
            "timemcpclient": self.time_mcp.endpoint,
            "neonmcpclient": self.neon_mcp.endpoint,
            "supabasemcpclient": self.supabase_mcp.endpoint,
            "calendarmcpclient": self.calendar_mcp.endpoint,
            "playwrightmcpclient": self.playwright_mcp.endpoint,
        }

        # Remove "client" suffix if present
        if client_type_lower.endswith("client"):
            client_type_lower = client_type_lower[:-6]

        # Remove "mcp" if present
        if client_type_lower.endswith("mcp"):
            client_type_lower = client_type_lower[:-3]

        for key, url in mcp_map.items():
            if client_type_lower in key:
                return url

        # Default fallback
        logging.warning(f"No MCP URL mapping found for client type: {client_type}")
        return "http://localhost:8000"

    def get_api_key_for_type(self, client_type: str) -> Optional[str]:
        """Get the API key for a given client type.

        Args:
            client_type: The client type name (e.g., 'FlightMCPClient')

        Returns:
            The API key or None if not available.
        """
        client_type_lower = client_type.lower()

        # Map client types to MCP config attributes for API keys
        mcp_map = {
            "flightmcpclient": getattr(self.flights_mcp, "api_key", None),
            "accommodationmcpclient": getattr(
                self.accommodations_mcp.airbnb, "api_key", None
            ),
            "googlemapsmcpclient": getattr(self.googlemaps_mcp, "api_key", None),
            "memorymcpclient": getattr(self.memory_mcp, "api_key", None),
            "webcrawlmcpclient": getattr(self.webcrawl_mcp, "api_key", None),
            "timemcpclient": getattr(self.time_mcp, "api_key", None),
            "neonmcpclient": getattr(self.neon_mcp, "api_key", None),
            "supabasemcpclient": getattr(self.supabase_mcp, "api_key", None),
            "calendarmcpclient": getattr(self.calendar_mcp, "api_key", None),
            "playwrightmcpclient": getattr(self.playwright_mcp, "api_key", None),
        }

        # Remove "client" suffix if present
        if client_type_lower.endswith("client"):
            client_type_lower = client_type_lower[:-6]

        # Remove "mcp" if present
        if client_type_lower.endswith("mcp"):
            client_type_lower = client_type_lower[:-3]

        for key, api_key in mcp_map.items():
            if client_type_lower in key and api_key is not None:
                return api_key.get_secret_value()

        # Default fallback
        return None


@lru_cache()
def get_settings() -> AppSettings:
    """Get the application settings.

    Returns:
        Application settings instance
    """
    return AppSettings()


# Export settings for convenience
settings = get_settings()


def init_settings() -> AppSettings:
    """
    Initialize and validate application settings.

    This function should be called at application startup to ensure
    all required settings are available and valid.

    Returns:
        The validated AppSettings instance.

    Raises:
        ValidationError: If settings are missing or invalid.
    """
    # Log settings initialization
    logging.info("Initializing application settings")

    # Check environment
    env = settings.environment
    logging.info(f"Application environment: {env}")

    # Validate critical settings
    _validate_critical_settings(settings)

    # Additional initialization for specific environments
    if env == "development":
        logging.debug("Development mode enabled")
    elif env == "testing":
        logging.debug("Test mode enabled")
    elif env == "production":
        logging.info("Production mode enabled")
        _validate_production_settings(settings)

    logging.info("Settings initialization completed successfully")
    return settings


def _validate_critical_settings(settings: AppSettings) -> None:
    """
    Validate critical settings required for the application to function.

    Args:
        settings: The AppSettings instance to validate.

    Raises:
        ValueError: If any critical setting is missing or invalid.
    """
    critical_errors: List[str] = []

    # Check OpenAI API key
    if not settings.openai_api_key.get_secret_value():
        critical_errors.append("OpenAI API key is missing")

    # Check database configuration based on provider
    if settings.database.db_provider == "supabase":
        if not settings.database.supabase_url:
            critical_errors.append("Supabase URL is missing")
        if not settings.database.supabase_anon_key.get_secret_value():
            critical_errors.append("Supabase anonymous key is missing")
    elif settings.database.db_provider == "neon":
        if not settings.database.neon_connection_string:
            critical_errors.append("Neon connection string is missing")
    else:
        critical_errors.append(
            f"Invalid database provider: {settings.database.db_provider}"
        )

    # Check Neo4j configuration
    if not settings.neo4j.password.get_secret_value():
        critical_errors.append("Neo4j password is missing")

    # Raise an error with all validation issues if any were found
    if critical_errors:
        error_message = "Critical settings validation failed:\n- " + "\n- ".join(
            critical_errors
        )
        logging.error(error_message)
        raise ValueError(error_message)


def _validate_production_settings(settings: AppSettings) -> None:
    """
    Validate additional settings required for production environments.

    Args:
        settings: The AppSettings instance to validate.

    Raises:
        ValueError: If any production-required setting is missing or invalid.
    """
    production_errors: List[str] = []

    # Debug mode should be disabled in production
    if settings.debug:
        production_errors.append("Debug mode should be disabled in production")

    # In production, most MCP servers should have API keys configured
    for server_name in [
        "weather_mcp",
        "webcrawl_mcp",
        "flights_mcp",
        "googlemaps_mcp",
        "playwright_mcp",
        "time_mcp",
    ]:
        server_config = getattr(settings, server_name)
        if hasattr(server_config, "api_key") and server_config.api_key is None:
            production_errors.append(f"{server_name.upper()} API key is missing")

    # Validate Airbnb MCP configuration
    if settings.accommodations_mcp.airbnb.endpoint == "http://localhost:3000":
        production_errors.append(
            "DEFAULT_AIRBNB_MCP_ENDPOINT is using localhost in production. "
            "Should be set to deployed OpenBnB MCP server URL."
        )

    # Validate Calendar MCP configuration
    if settings.calendar_mcp.endpoint == "http://localhost:3003":
        production_errors.append(
            "DEFAULT_CALENDAR_MCP_ENDPOINT is using localhost in production. "
            "Should be set to deployed Google Calendar MCP server URL."
        )

    # Validate Google Calendar credentials
    if not settings.calendar_mcp.google_client_id.get_secret_value():
        production_errors.append("GOOGLE_CLIENT_ID is missing for calendar_mcp")

    if not settings.calendar_mcp.google_client_secret.get_secret_value():
        production_errors.append("GOOGLE_CLIENT_SECRET is missing for calendar_mcp")

    if not settings.calendar_mcp.google_redirect_uri:
        production_errors.append("GOOGLE_REDIRECT_URI is missing for calendar_mcp")

    # Validate Duffel API key for Flights MCP
    if not settings.flights_mcp.duffel_api_key.get_secret_value():
        production_errors.append("DUFFEL_API_KEY is missing for flights_mcp")

    # Validate Crawl4AI API key for WebCrawl MCP
    if not settings.webcrawl_mcp.crawl4ai_api_key.get_secret_value():
        production_errors.append("CRAWL4AI_API_KEY is missing for webcrawl_mcp")

    # Additional production-specific validations
    if production_errors:
        warning_message = "Production settings validation warnings:\n- " + "\n- ".join(
            production_errors
        )
        logging.warning(warning_message)


def get_settings_dict() -> Dict[str, Any]:
    """
    Get a dictionary representation of the application settings.

    This function returns a sanitized dictionary with all settings,
    masking sensitive values like API keys and passwords.

    Returns:
        A dictionary representation of the settings.
    """
    settings_dict = settings.model_dump()

    # Sanitize sensitive fields
    _sanitize_sensitive_data(settings_dict)

    return settings_dict


def _sanitize_sensitive_data(data: Dict[str, Any], path: str = "") -> None:
    """
    Recursively sanitize sensitive data in a dictionary.

    Args:
        data: The dictionary to sanitize.
        path: The current path in the dictionary (for nested dicts).
    """
    sensitive_keywords = {"password", "api_key", "secret", "key", "token"}

    for key, value in list(data.items()):
        current_path = f"{path}.{key}" if path else key

        # Check if this is a sensitive field
        is_sensitive = any(keyword in key.lower() for keyword in sensitive_keywords)

        if isinstance(value, dict):
            _sanitize_sensitive_data(value, current_path)
        elif is_sensitive and value:
            data[key] = "********" if value else None
