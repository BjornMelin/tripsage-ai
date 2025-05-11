"""
Factory module for creating Google Maps MCP clients.

This module provides a factory function to create Google Maps MCP clients
with the appropriate configuration.
"""

from ...utils.config import get_config
from ...utils.logging import get_module_logger
from .client import GoogleMapsMCPClient

logger = get_module_logger(__name__)
config = get_config()


def create_googlemaps_client() -> GoogleMapsMCPClient:
    """Create a new Google Maps MCP client with the appropriate configuration.

    Returns:
        GoogleMapsMCPClient: A configured Google Maps MCP client
    """
    client_config = config.get("mcp.googlemaps", {})
    endpoint = client_config.get("endpoint", "http://localhost:3101")
    api_key = client_config.get("api_key")

    logger.debug("Creating Google Maps MCP client with endpoint: %s", endpoint)

    client = GoogleMapsMCPClient(
        endpoint=endpoint,
        api_key=api_key,
        use_cache=True,
        cache_ttl=config.get("redis.ttl_medium", 3600),  # 1 hour default
    )

    return client
