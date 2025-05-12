"""
Factory module for creating Airbnb MCP clients.

This module provides a factory function to create Airbnb MCP clients
with the appropriate configuration and a client selector function
that can create clients for different accommodation sources.
"""

from typing import Dict, Union

from ...utils.config import config
from ...utils.logging import get_module_logger
from ..base_mcp_client import BaseMCPClient
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


def create_accommodation_client(
    source: str = "airbnb",
) -> Union[AirbnbMCPClient, BaseMCPClient]:
    """Create an appropriate accommodation client based on the source.

    This factory function creates and returns a client for the
    specified accommodation source.

    Args:
        source: Accommodation source (airbnb, booking, etc.)

    Returns:
        An MCP client for the specified source

    Raises:
        ValueError: If the source is not supported
    """
    sources: Dict[str, callable] = {
        "airbnb": create_airbnb_client,
        # Add more sources here as they become available
        # "booking": create_booking_client,
        # "hotels": create_hotels_client,
    }

    if source.lower() not in sources:
        supported = ", ".join(list(sources.keys()))
        logger.error(
            "Unsupported accommodation source: %s (supported: %s)",
            source,
            supported,
        )
        raise ValueError(f"Unsupported accommodation source: {source}")

    logger.debug("Creating %s accommodation client", source)
    return sources[source.lower()]()


# Create a singleton instance of the Airbnb client
airbnb_client = create_airbnb_client()
