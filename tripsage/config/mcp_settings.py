"""MCP Configuration Management System for TripSage.

This module provides a centralized configuration system for all Model Context
Protocol (MCP) servers that TripSage integrates with. It completely replaces
the previous configuration approach with a more structured and extensible
system using Pydantic V2.

The configuration hierarchy is:
1. BaseMCPConfig - Common settings for all MCPs
2. Specialized config types (RestMCPConfig, DatabaseMCPConfig, etc.)
3. Specific MCP configs (PlaywrightMCPConfig, GoogleMapsMCPConfig, etc.)

All MCP configurations use environment variables with the prefix TRIPSAGE_MCP_*
and support nested configuration settings.

Usage:
    from tripsage.config.mcp_settings import mcp_settings

    # Access a specific MCP configuration
    playwright_config = mcp_settings.playwright

    # Use in client initialization
    client = PlaywrightClient(
        url=str(playwright_config.url),
        api_key=(
            playwright_config.api_key.get_secret_value()
            if playwright_config.api_key else None
        ),
        browser_type=playwright_config.browser_type,
        headless=playwright_config.headless
    )

    # Check if an MCP is enabled
    if mcp_settings.neo4j_memory.enabled:
        # Use Neo4j Memory MCP
"""

import logging
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


class BaseMCPConfig(BaseModel):
    """Base configuration for all MCP servers."""

    enabled: bool = True
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_backoff: float = Field(default=1.0, ge=0.1, le=10.0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    model_config = ConfigDict(
        env_prefix="TRIPSAGE_MCP_",
        extra="ignore",
        validate_assignment=True,
    )


class RestMCPConfig(BaseMCPConfig):
    """Configuration for REST API based MCP servers."""

    url: AnyHttpUrl
    api_key: SecretStr
    headers: Dict[str, str] = Field(default_factory=dict)
    max_connections: int = Field(default=10, ge=1, le=100)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL ends with / to prevent path joining issues."""
        if not str(v).endswith("/"):
            v = f"{v}/"
        return v


class DatabaseMCPConfig(BaseMCPConfig):
    """Configuration for database MCP servers."""

    host: str
    port: int = Field(ge=1, le=65535)
    username: str
    password: SecretStr
    database: str
    use_ssl: bool = True
    pool_size: int = Field(default=5, ge=1, le=50)
    connection_timeout: int = Field(default=10, ge=1, le=60)


class LocalMCPConfig(BaseMCPConfig):
    """Configuration for locally running MCP servers."""

    host: str = "localhost"
    port: int = Field(ge=1, le=65535)
    path: Optional[str] = None


class WebCrawlMCPConfig(RestMCPConfig):
    """Configuration for web crawling MCP servers."""

    user_agent: str = "TripSage/1.0"
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_domains: List[str] = Field(default_factory=list)
    cache_ttl: int = Field(default=3600, ge=0, description="Cache TTL in seconds")


class BrowserMCPConfig(RestMCPConfig):
    """Configuration for browser automation MCP servers."""

    headless: bool = True
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    screenshot_dir: Optional[str] = None
    timeout_page: int = Field(default=60, ge=1, le=300)
    timeout_navigation: int = Field(default=30, ge=1, le=120)
    session_persistence: bool = True


class CacheMCPConfig(BaseMCPConfig):
    """Configuration for caching MCP servers."""

    host: str
    port: int = Field(ge=1, le=65535)
    db_index: int = Field(default=0, ge=0, le=15)
    default_ttl: int = Field(default=3600, ge=0, description="Default TTL in seconds")
    namespace: str = "tripsage"
    max_memory: Optional[str] = None  # Example: "100mb"


# Specific MCP Configurations


class PlaywrightMCPConfig(BrowserMCPConfig):
    """Configuration for Playwright MCP server."""

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_PLAYWRIGHT_")


class GoogleMapsMCPConfig(RestMCPConfig):
    """Configuration for Google Maps MCP server."""

    map_type: Literal["roadmap", "satellite", "hybrid", "terrain"] = "roadmap"
    language: str = "en"
    region: str = "US"

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_GOOGLEMAPS_")


class WeatherMCPConfig(RestMCPConfig):
    """Configuration for Weather MCP server."""

    temperature_unit: Literal["celsius", "fahrenheit"] = "celsius"
    forecast_days: int = Field(default=7, ge=1, le=16)

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_WEATHER_")


class TimeMCPConfig(RestMCPConfig):
    """Configuration for Time MCP server."""

    default_timezone: str = "UTC"

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_TIME_")


class RedisMCPConfig(CacheMCPConfig):
    """Configuration for Redis MCP server."""

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_REDIS_")


class Crawl4AIMCPConfig(WebCrawlMCPConfig):
    """Configuration for Crawl4AI MCP server."""

    rag_enabled: bool = True
    max_pages: int = Field(default=10, ge=1, le=100)
    extract_images: bool = False

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_CRAWL4AI_")


class FirecrawlMCPConfig(WebCrawlMCPConfig):
    """Configuration for Firecrawl MCP server."""

    js_rendering: bool = True
    wait_for_selectors: List[str] = Field(default_factory=list)
    extract_structured_data: bool = True

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_FIRECRAWL_")


class SupabaseMCPConfig(DatabaseMCPConfig):
    """Configuration for Supabase MCP server."""

    project_ref: str
    anon_key: SecretStr
    service_key: SecretStr

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_SUPABASE_")


class Neo4jMemoryMCPConfig(DatabaseMCPConfig):
    """Configuration for Neo4j Memory MCP server."""

    scheme: Literal["neo4j", "neo4j+s", "neo4j+ssc", "bolt", "bolt+s"] = "neo4j"
    graph_name: str = "knowledge"

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_NEO4J_")


class DuffelFlightsMCPConfig(RestMCPConfig):
    """Configuration for Duffel Flights MCP server."""

    default_currency: str = "USD"
    default_market: str = "US"
    default_locale: str = "en-US"

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_DUFFEL_")


class AirbnbMCPConfig(RestMCPConfig):
    """Configuration for Airbnb MCP server."""

    default_currency: str = "USD"
    default_locale: str = "en-US"

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_AIRBNB_")


class GoogleCalendarMCPConfig(RestMCPConfig):
    """Configuration for Google Calendar MCP server."""

    auth_mode: Literal["oauth", "service_account"] = "oauth"
    scopes: List[str] = Field(default=["https://www.googleapis.com/auth/calendar"])
    credentials_path: Optional[str] = None

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_GOOGLECALENDAR_")


class MCPSettings(BaseModel):
    """Main MCP Settings container for all MCP configurations."""

    # Database MCPs
    supabase: SupabaseMCPConfig = Field(default_factory=SupabaseMCPConfig)
    neo4j_memory: Neo4jMemoryMCPConfig = Field(default_factory=Neo4jMemoryMCPConfig)

    # Travel Data MCPs
    duffel_flights: DuffelFlightsMCPConfig = Field(
        default_factory=DuffelFlightsMCPConfig
    )
    airbnb: AirbnbMCPConfig = Field(default_factory=AirbnbMCPConfig)

    # Browser & Web Crawling MCPs
    playwright: PlaywrightMCPConfig = Field(default_factory=PlaywrightMCPConfig)
    crawl4ai: Crawl4AIMCPConfig = Field(default_factory=Crawl4AIMCPConfig)
    firecrawl: FirecrawlMCPConfig = Field(default_factory=FirecrawlMCPConfig)

    # Utility MCPs
    google_maps: GoogleMapsMCPConfig = Field(default_factory=GoogleMapsMCPConfig)
    time: TimeMCPConfig = Field(default_factory=TimeMCPConfig)
    weather: WeatherMCPConfig = Field(default_factory=WeatherMCPConfig)
    google_calendar: GoogleCalendarMCPConfig = Field(
        default_factory=GoogleCalendarMCPConfig
    )
    redis: RedisMCPConfig = Field(default_factory=RedisMCPConfig)

    model_config = ConfigDict(
        env_nested_delimiter="__",
        validate_assignment=True,
        protected_namespaces=(),
    )

    @model_validator(mode="after")
    def validate_settings(self) -> "MCPSettings":
        """Perform cross-field validation."""
        # Example: Ensure at least one web crawling MCP is enabled if we're using them
        if not (self.crawl4ai.enabled or self.firecrawl.enabled):
            logger.warning(
                "No web crawling MCP is enabled. "
                "Web crawling functionality will be limited."
            )

        # Example: Ensure we have a database MCP for persistence
        if not (self.supabase.enabled or self.neo4j_memory.enabled):
            logger.warning(
                "No database MCP is enabled. Persistence functionality will be limited."
            )

        return self

    def get_enabled_mcps(self) -> Dict[str, Any]:
        """Returns a dictionary of enabled MCP configs."""
        return {
            name: config
            for name, config in self.model_dump().items()
            if config.get("enabled", False)
        }


@lru_cache()
def get_mcp_settings() -> MCPSettings:
    """Returns a singleton instance of the MCPSettings."""
    try:
        settings = MCPSettings()
        logger.info(
            f"Successfully loaded MCP settings with "
            f"{len(settings.get_enabled_mcps())} enabled MCPs"
        )
        return settings
    except Exception as e:
        logger.error(f"Failed to load MCP settings: {e}")
        # Return default settings as fallback
        return MCPSettings()


# Singleton instance to be imported by other modules
mcp_settings = get_mcp_settings()
