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
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


class TransportType(str, Enum):
    """MCP server transport types"""

    STDIO = "stdio"
    HTTP = "http"
    HTTPSSE = "httpsse"
    WEBSOCKET = "ws"


class RuntimeType(str, Enum):
    """MCP server runtime types"""

    PYTHON = "python"
    NODE = "node"
    BINARY = "binary"


class BaseMCPConfig(BaseModel):
    """Base configuration for all MCP servers."""

    enabled: bool = True
    runtime: RuntimeType = RuntimeType.NODE
    transport: TransportType = TransportType.STDIO
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    auto_start: bool = False
    health_check_endpoint: Optional[str] = None
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

    url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://localhost:8080/")
    )
    api_key: SecretStr = Field(default=SecretStr("test-api-key"))
    headers: Dict[str, str] = Field(default_factory=dict)
    max_connections: int = Field(default=10, ge=1, le=100)
    transport: TransportType = TransportType.HTTP  # Override default

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL ends with / to prevent path joining issues."""
        if not str(v).endswith("/"):
            v = f"{v}/"
        return v


class DatabaseMCPConfig(BaseMCPConfig):
    """Configuration for database MCP servers."""

    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    username: str = Field(default="postgres")
    password: SecretStr = Field(default=SecretStr(""))
    database: str = Field(default="postgres")
    use_ssl: bool = True
    pool_size: int = Field(default=5, ge=1, le=50)
    connection_timeout: int = Field(default=10, ge=1, le=60)


class LocalMCPConfig(BaseMCPConfig):
    """Configuration for locally running MCP servers."""

    host: str = "localhost"
    port: int = Field(ge=1, le=65535)
    path: Optional[str] = None


class DomainRoutingConfig(BaseModel):
    """Configuration for domain-based routing of web crawl requests."""

    crawl4ai_domains: List[str] = Field(
        default_factory=lambda: [],
        description="Domains optimized for Crawl4AI (added to defaults)",
    )
    firecrawl_domains: List[str] = Field(
        default_factory=lambda: [],
        description="Domains optimized for Firecrawl (added to defaults)",
    )

    model_config = ConfigDict(extra="ignore")


class WebCrawlMCPConfig(RestMCPConfig):
    """Configuration for web crawling MCP servers."""

    user_agent: str = "TripSage/1.0"
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_domains: List[str] = Field(default_factory=list)
    cache_ttl: int = Field(default=3600, ge=0, description="Cache TTL in seconds")
    domain_routing: DomainRoutingConfig = Field(default_factory=DomainRoutingConfig)


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

    host: str = Field(default="localhost")
    port: int = Field(default=6379, ge=1, le=65535)
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
    """Configuration for official Redis MCP server.

    Uses the official @modelcontextprotocol/server-redis package.
    """

    # Official Redis MCP server configuration using Docker
    runtime: RuntimeType = RuntimeType.BINARY  # Use binary for Docker command
    transport: TransportType = TransportType.STDIO  # Standard MCP transport

    # Command to run the official Redis MCP server via Docker
    command: str = "docker"
    args: List[str] = Field(default_factory=lambda: ["run", "-i", "--rm", "mcp/redis"])

    # Redis connection URL - passed as environment variable to MCP server
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for the MCP server",
    )

    # Redis connection parameters for internal wrapper compatibility
    password: Optional[SecretStr] = Field(default=None)
    ssl: bool = Field(default=False, description="Enable SSL/TLS")

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_REDIS_")

    @model_validator(mode="after")
    def validate_redis_url(self) -> "RedisMCPConfig":
        """Build Redis URL from components if needed."""
        if not self.redis_url.startswith("redis://"):
            # Build URL from host/port/password components
            auth_part = ""
            if self.password:
                auth_part = f":{self.password.get_secret_value()}@"

            protocol = "rediss" if self.ssl else "redis"
            self.redis_url = (
                f"{protocol}://{auth_part}{self.host}:{self.port}/{self.db_index}"
            )

        # Add Redis URL as an argument to the Docker command
        if self.redis_url not in self.args:
            self.args.append(self.redis_url)

        return self


class Crawl4AIMCPConfig(WebCrawlMCPConfig):
    """Configuration for Crawl4AI MCP server."""

    url: AnyUrl = Field(
        default_factory=lambda: AnyUrl("ws://localhost:11235/mcp/ws"),
        description="URL of the Crawl4AI MCP server (WebSocket or SSE endpoint)",
    )
    runtime: RuntimeType = RuntimeType.PYTHON  # Override default
    transport: TransportType = TransportType.WEBSOCKET  # Override default
    rag_enabled: bool = True
    max_pages: int = Field(default=10, ge=1, le=100)
    extract_images: bool = False

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_CRAWL4AI_")


class FirecrawlMCPConfig(WebCrawlMCPConfig):
    """Configuration for Firecrawl MCP server."""

    mcp_server_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("http://localhost:4000"),
        description="URL of the Firecrawl MCP server",
    )
    js_rendering: bool = True
    wait_for_selectors: List[str] = Field(default_factory=list)
    extract_structured_data: bool = True

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_FIRECRAWL_")


class SupabaseMCPConfig(BaseMCPConfig):
    """Configuration for external Supabase MCP server."""

    # For external MCP server, we use stdio transport with npx command
    runtime: RuntimeType = RuntimeType.NODE  # Override default
    transport: TransportType = TransportType.STDIO  # Override default

    # Command to run the external Supabase MCP server
    command: str = "npx"
    args: List[str] = Field(
        default_factory=lambda: [
            "-y",
            "@supabase/mcp-server-supabase@latest",
            "--access-token",
            "${SUPABASE_ACCESS_TOKEN}",
        ]
    )

    # Configuration for connecting to Supabase
    access_token: SecretStr = Field(default=SecretStr("test-access-token"))
    project_ref: Optional[str] = Field(
        default=None, description="Optional project ref to scope operations"
    )
    read_only: bool = Field(
        default=False, description="Enable read-only mode for safety"
    )

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_SUPABASE_")

    @model_validator(mode="after")
    def update_args_with_token(self) -> "SupabaseMCPConfig":
        """Update the args to include the actual access token from env."""
        if self.access_token:
            # Replace the token placeholder in args
            updated_args = []
            for arg in self.args:
                if arg == "${SUPABASE_ACCESS_TOKEN}":
                    updated_args.append(self.access_token.get_secret_value())
                else:
                    updated_args.append(arg)
            # Use object.__setattr__ to avoid validation recursion
            object.__setattr__(self, "args", updated_args)

        # Add project ref if specified
        if self.project_ref:
            object.__setattr__(
                self, "args", self.args + ["--project-ref", self.project_ref]
            )

        # Add read-only flag if enabled
        if self.read_only:
            object.__setattr__(self, "args", self.args + ["--read-only"])

        return self


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
