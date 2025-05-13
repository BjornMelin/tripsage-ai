"""
MCP Client Factory pattern implementation for TripSage.

This module provides standardized client factory classes for all MCP
clients in the TripSage application, with a consistent interface
for creating and managing client instances.
"""

import abc
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from ..utils.logging import get_module_logger
from .base_mcp_client import BaseMCPClient
from .fastmcp import FastMCPClient

logger = get_module_logger(__name__)

# Generic type for the client class
C = TypeVar("C", bound=BaseMCPClient)
# Generic type for client configuration
ConfigT = TypeVar("ConfigT", bound=BaseModel)


class ClientConfig(BaseModel):
    """Base configuration model for MCP clients."""

    endpoint: str = Field(..., description="The MCP server endpoint URL")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    use_cache: bool = Field(True, description="Whether to use caching")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields for client-specific configs
        protected_namespaces=(),
    )


class BaseClientFactory(Generic[C, ConfigT], metaclass=abc.ABCMeta):
    """Base class for all MCP client factories in TripSage.

    This abstract base class defines the interface that all MCP client factories
    must implement, providing a consistent pattern for client creation and
    configuration validation.
    """

    def __init__(
        self,
        client_class: Type[C],
        config_class: Type[ConfigT],
        server_name: str,
        default_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the client factory.

        Args:
            client_class: The MCP client class to instantiate
            config_class: The configuration model class
            server_name: The name of the MCP server
            default_config: Optional default configuration values
        """
        self.client_class = client_class
        self.config_class = config_class
        self.server_name = server_name
        self.default_config = default_config or {}
        self._instance: Optional[C] = None

        logger.debug(
            "Initialized %s factory for %s MCP", self.__class__.__name__, server_name
        )

    @abc.abstractmethod
    def _load_config_from_settings(self) -> Dict[str, Any]:
        """Load configuration from settings or environment.

        This method must be implemented by subclasses to load
        configuration values from the appropriate source.

        Returns:
            Dictionary containing configuration values
        """
        pass

    def _validate_config(self, config: Dict[str, Any]) -> ConfigT:
        """Validate configuration using the config model.

        Args:
            config: Configuration dictionary

        Returns:
            Validated configuration model instance

        Raises:
            ValueError: If configuration validation fails
        """
        try:
            # Use Pydantic v2 model_validate
            return self.config_class.model_validate(config)
        except Exception as e:
            logger.error(
                "Configuration validation failed for %s MCP: %s",
                self.server_name,
                str(e),
            )
            raise ValueError(
                f"Invalid configuration for {self.server_name} MCP: {str(e)}"
            ) from e

    def create_client(self, **override_config) -> C:
        """Create a new client instance with the given configuration.

        Args:
            **override_config: Configuration values to override defaults

        Returns:
            New client instance

        Raises:
            ValueError: If configuration validation fails
        """
        # Combine default, settings, and override configs
        base_config = self.default_config.copy()
        settings_config = self._load_config_from_settings()
        base_config.update(settings_config)
        base_config.update(override_config)

        # Validate the combined configuration
        validated_config = self._validate_config(base_config)

        # Create and return the client instance
        client_kwargs = validated_config.model_dump()

        # Add server_name for FastMCPClient instances
        if issubclass(self.client_class, FastMCPClient):
            client_kwargs["server_name"] = self.server_name

        logger.debug("Creating new %s MCP client instance", self.server_name)

        return self.client_class(**client_kwargs)

    def get_client(self, **override_config) -> C:
        """Get or create a client instance.

        This method returns the existing instance if available,
        or creates a new one if needed.

        Args:
            **override_config: Configuration values to override defaults

        Returns:
            Client instance
        """
        if self._instance is None or override_config:
            self._instance = self.create_client(**override_config)

        return self._instance

    def reset_client(self) -> None:
        """Reset the client instance.

        This method clears the existing client instance,
        forcing a new one to be created on the next get_client call.
        """
        self._instance = None
        logger.debug("Reset %s MCP client instance", self.server_name)
