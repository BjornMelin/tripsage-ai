"""MCP Configuration Management System for TripSage.

This module provides a centralized configuration system for the single remaining
Model Context Protocol (MCP) server that TripSage integrates with: Airbnb.

As part of the MCP-to-SDK migration plan, all other services have been migrated
to direct SDK integration for improved performance and reduced complexity.
Only the Airbnb MCP server remains as an external MCP integration.

The configuration hierarchy is:
1. BaseMCPConfig - Common settings for MCP servers
2. RestMCPConfig - REST API based MCP servers
3. AirbnbMCPConfig - Specific Airbnb MCP configuration

All MCP configurations use environment variables with the prefix TRIPSAGE_MCP_*
and support nested configuration settings.

Usage:
    from tripsage.config.mcp_settings import mcp_settings

    # Access the Airbnb MCP configuration
    airbnb_config = mcp_settings.airbnb

    # Use in client initialization
    client = AirbnbClient(
        url=str(airbnb_config.url),
        api_key=(
            airbnb_config.api_key.get_secret_value()
            if airbnb_config.api_key else None
        ),
        default_currency=airbnb_config.default_currency,
        default_locale=airbnb_config.default_locale
    )

    # Check if the MCP is enabled
    if mcp_settings.airbnb.enabled:
        # Use Airbnb MCP
"""

import logging
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
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
    """Base configuration for MCP servers."""

    enabled: bool = True
    runtime: RuntimeType = RuntimeType.NODE
    transport: TransportType = TransportType.STDIO
    command: str = Field(default="", description="Command to run the MCP server")
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    auto_start: bool = False
    health_check_endpoint: str = Field(default="", description="Health check endpoint")
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


class AirbnbMCPConfig(RestMCPConfig):
    """Configuration for Airbnb MCP server."""

    default_currency: str = "USD"
    default_locale: str = "en-US"

    model_config = ConfigDict(env_prefix="TRIPSAGE_MCP_AIRBNB_")


class MCPSettings(BaseModel):
    """Main MCP Settings container for the remaining MCP configuration.

    As part of the MCP-to-SDK migration, this now only contains the Airbnb MCP
    configuration. All other services have been migrated to direct SDK integration.
    """

    # Travel Data MCP - The only remaining external MCP integration
    airbnb: AirbnbMCPConfig = Field(default_factory=AirbnbMCPConfig)

    model_config = ConfigDict(
        env_nested_delimiter="__",
        validate_assignment=True,
        protected_namespaces=(),
    )

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
        enabled_count = len(settings.get_enabled_mcps())
        logger.info(
            f"Successfully loaded MCP settings with {enabled_count} enabled MCP"
            f"{'s' if enabled_count != 1 else ''}"
        )
        return settings
    except Exception as e:
        logger.error(f"Failed to load MCP settings: {e}")
        # Return default settings as fallback
        return MCPSettings()


# Singleton instance to be imported by other modules
mcp_settings = get_mcp_settings()
