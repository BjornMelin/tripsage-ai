"""
Factory module for creating Airbnb MCP clients.

This module provides a factory function to create Airbnb MCP clients
with the appropriate configuration.
"""

from ...utils.config import config
from ...utils.logging import get_module_logger
from .client import AirbnbMCPClient

logger = get_module_logger(__name__)


def create_airbnb_client() -> AirbnbMCPClient:
    """Create a new Airbnb MCP client with the appropriate configuration.

    Returns:
        AirbnbMCPClient: A configured Airbnb MCP client
    """
    client_config = config.accommodations_mcp.airbnb

    logger.debug("Creating Airbnb MCP client with endpoint: %s", client_config.endpoint)

    client = AirbnbMCPClient(
        endpoint=client_config.endpoint,
        use_cache=True,
        cache_ttl=config.redis.ttl_medium,  # 1 hour default
    )

    return client
