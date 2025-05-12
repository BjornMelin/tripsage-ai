"""
Factory module for creating Google Maps MCP clients.

This module provides a factory function to create Google Maps MCP clients
with the appropriate configuration for the official Google Maps MCP server.
"""

import os
from typing import Optional

from ...utils.config import get_config
from ...utils.logging import get_module_logger
from .client import GoogleMapsMCPClient

logger = get_module_logger(__name__)
config = get_config()


def create_googlemaps_client(api_key: Optional[str] = None) -> GoogleMapsMCPClient:
    """Create a new Google Maps MCP client with the appropriate configuration.

    Args:
        api_key: Optional API key to override the one from config

    Returns:
        GoogleMapsMCPClient: A configured Google Maps MCP client
    """
    google_maps_config = config.google_maps_mcp

    # Use provided API key, or config.maps_api_key, or environment variable
    if api_key is None:
        api_key = google_maps_config.maps_api_key or os.environ.get(
            "GOOGLE_MAPS_API_KEY"
        )

    # Get MCP endpoint
    endpoint = google_maps_config.endpoint

    logger.debug("Creating Google Maps MCP client with endpoint: %s", endpoint)
    logger.debug("Google Maps API Key available: %s", "Yes" if api_key else "No")

    client = GoogleMapsMCPClient(
        endpoint=endpoint,
        api_key=api_key,
        use_cache=True,
        cache_ttl=config.redis.ttl_medium,  # 1 hour default from config
    )

    return client
