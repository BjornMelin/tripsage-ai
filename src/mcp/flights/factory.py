"""
Flights MCP Client Factory implementation for TripSage.

This module provides a factory for creating and managing Flights MCP Client instances
in the TripSage application, with configuration validation and caching.
"""

from typing import Any, Dict, Optional

from pydantic import Field, model_validator

from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..client_factory import BaseClientFactory, ClientConfig
from .client import FlightsMCPClient

logger = get_module_logger(__name__)


class FlightsMCPConfig(ClientConfig):
    """Configuration model for Flights MCP client."""

    endpoint: str = Field(..., description="The Flights MCP server endpoint URL")
    api_key: Optional[str] = Field(
        None, description="Duffel API key for authentication"
    )
    timeout: float = Field(
        30.0,
        description="Request timeout in seconds",
        ge=5.0,  # Higher minimum due to flight search complexity
        le=120.0,
    )
    use_cache: bool = Field(
        True, description="Whether to use caching for Flights MCP requests"
    )
    cache_ttl: int = Field(
        1800,  # 30 minutes default
        description="Cache TTL in seconds for Flights MCP responses",
    )

    @model_validator(mode="after")
    def validate_endpoint(self) -> "FlightsMCPConfig":
        """Validate that the endpoint is properly formatted."""
        endpoint = self.endpoint

        # Ensure endpoint has correct protocol
        if not endpoint.startswith(("http://", "https://")):
            self.endpoint = f"https://{endpoint}"
            logger.warning(
                "Endpoint URL didn't include protocol, assuming HTTPS: %s",
                self.endpoint,
            )

        # Ensure endpoint doesn't end with a slash
        if self.endpoint.endswith("/"):
            self.endpoint = self.endpoint[:-1]
            logger.warning(
                "Removing trailing slash from endpoint URL: %s", self.endpoint
            )

        return self


class FlightsMCPClientFactory(BaseClientFactory[FlightsMCPClient, FlightsMCPConfig]):
    """Factory for creating and managing Flights MCP Client instances."""

    def __init__(self):
        """Initialize the Flights MCP Client Factory."""
        super().__init__(
            client_class=FlightsMCPClient,
            config_class=FlightsMCPConfig,
            server_name="Flights",
            default_config={
                "timeout": 30.0,
                "use_cache": True,
                "cache_ttl": 1800,  # 30 minutes
            },
        )

    def _load_config_from_settings(self) -> Dict[str, Any]:
        """Load Flights MCP configuration from application settings.

        Returns:
            Dictionary containing configuration values
        """
        # Check if flights_mcp settings are available
        if hasattr(settings, "flights_mcp"):
            flights_config = settings.flights_mcp

            # Extract config attributes from settings
            config = {
                "endpoint": getattr(
                    flights_config, "endpoint", "http://localhost:3000"
                ),
            }

            # Handle API key as SecretStr or normal string
            api_key = getattr(flights_config, "api_key", None)
            if api_key is not None:
                if hasattr(api_key, "get_secret_value"):
                    config["api_key"] = api_key.get_secret_value()
                else:
                    config["api_key"] = api_key
            else:
                config["api_key"] = None

            # Extract other configuration options
            config.update(
                {
                    "timeout": getattr(flights_config, "timeout", 30.0),
                    "use_cache": getattr(flights_config, "use_cache", True),
                    "cache_ttl": getattr(flights_config, "cache_ttl", 1800),
                }
            )

            return config

        # Default values if flights_mcp settings not found
        return {
            "endpoint": "http://localhost:3000",
            "api_key": None,
            "timeout": 30.0,
            "use_cache": True,
            "cache_ttl": 1800,
        }


# Create global factory instance
flights_factory = FlightsMCPClientFactory()


def get_client(**override_config) -> FlightsMCPClient:
    """Get a Flights MCP Client instance.

    Args:
        **override_config: Configuration values to override defaults

    Returns:
        FlightsMCPClient instance
    """
    return flights_factory.get_client(**override_config)
