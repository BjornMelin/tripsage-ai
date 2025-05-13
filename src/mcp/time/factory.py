"""
Time MCP Client Factory implementation for TripSage.

This module provides a factory for creating and managing Time MCP Client instances
in the TripSage application, with configuration validation and caching.
"""

from typing import Dict, Any, Optional

from pydantic import Field, model_validator

from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..client_factory import BaseClientFactory, ClientConfig
from .client import TimeMCPClient

logger = get_module_logger(__name__)


class TimeMCPConfig(ClientConfig):
    """Configuration model for Time MCP client."""
    
    endpoint: str = Field(
        ..., 
        description="The Time MCP server endpoint URL"
    )
    api_key: Optional[str] = Field(
        None, 
        description="API key for Time MCP server authentication"
    )
    timeout: float = Field(
        30.0, 
        description="Request timeout in seconds",
        ge=1.0,
        le=120.0
    )
    use_cache: bool = Field(
        True, 
        description="Whether to use caching for Time MCP requests"
    )
    cache_ttl: int = Field(
        1800,  # 30 minutes default for time data
        description="Cache TTL in seconds for Time MCP responses"
    )
    
    @model_validator(mode='after')
    def validate_endpoint(self) -> 'TimeMCPConfig':
        """Validate that the endpoint is properly formatted."""
        endpoint = self.endpoint
        
        # Ensure endpoint has correct protocol
        if not endpoint.startswith(('http://', 'https://')):
            self.endpoint = f"https://{endpoint}"
            logger.warning(
                "Endpoint URL didn't include protocol, assuming HTTPS: %s",
                self.endpoint
            )
        
        # Ensure endpoint doesn't end with a slash
        if self.endpoint.endswith('/'):
            self.endpoint = self.endpoint[:-1]
            logger.warning(
                "Removing trailing slash from endpoint URL: %s",
                self.endpoint
            )
        
        return self


class TimeMCPClientFactory(BaseClientFactory[TimeMCPClient, TimeMCPConfig]):
    """Factory for creating and managing Time MCP Client instances."""
    
    def __init__(self):
        """Initialize the Time MCP Client Factory."""
        super().__init__(
            client_class=TimeMCPClient,
            config_class=TimeMCPConfig,
            server_name="Time",
            default_config={
                "timeout": 30.0,
                "use_cache": True,
                "cache_ttl": 1800,  # 30 minutes
            }
        )
    
    def _load_config_from_settings(self) -> Dict[str, Any]:
        """Load Time MCP configuration from application settings.
        
        Returns:
            Dictionary containing configuration values
        """
        # Check if time_mcp settings are available
        if hasattr(settings, "time_mcp"):
            time_config = settings.time_mcp
            
            # Extract config attributes from settings
            config = {
                "endpoint": getattr(time_config, "endpoint", "http://localhost:3000"),
                "api_key": getattr(time_config, "api_key", None),
                "timeout": getattr(time_config, "timeout", 30.0),
                "use_cache": getattr(time_config, "use_cache", True),
                "cache_ttl": getattr(time_config, "cache_ttl", 1800),
            }
            
            # If api_key is a SecretStr, get its value
            if hasattr(config["api_key"], "get_secret_value"):
                config["api_key"] = config["api_key"].get_secret_value()
                
            return config
        
        # Default values if time_mcp settings not found
        return {
            "endpoint": "http://localhost:3000",
            "api_key": None,
            "timeout": 30.0,
            "use_cache": True,
            "cache_ttl": 1800,
        }


# Create global factory instance
time_factory = TimeMCPClientFactory()


def get_client(**override_config) -> TimeMCPClient:
    """Get a Time MCP Client instance.
    
    Args:
        **override_config: Configuration values to override defaults
        
    Returns:
        TimeMCPClient instance
    """
    return time_factory.get_client(**override_config)


def get_service():
    """Get a Time Service instance.
    
    Returns:
        TimeService instance
    """
    from .client import TimeService
    return TimeService(get_client())