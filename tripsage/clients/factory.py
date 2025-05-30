"""Factory for creating MCP clients (Airbnb only after SDK migration).

After the MCP to SDK migration, this factory only handles Airbnb accommodations
since it's the only service remaining on MCP due to unofficial API constraints.
All other services have been migrated to direct SDK integration.
"""

from typing import Dict, Type

from tripsage.clients.base import BaseMCPClient
from tripsage_core.config.base_app_settings import settings


class MCPClientFactory:
    """Factory for creating MCP clients (Airbnb only post-migration)."""

    _clients: Dict[str, BaseMCPClient] = {}

    @classmethod
    def get_airbnb_client(
        cls, client_type: Type[BaseMCPClient], **kwargs
    ) -> BaseMCPClient:
        """Get Airbnb MCP client instance.

        Args:
            client_type: The type of MCP client to get (AccommodationMCPClient).
            **kwargs: Additional arguments to pass to the client constructor.

        Returns:
            An MCP client instance.

        Note:
            Only Airbnb accommodations remain on MCP after the SDK migration.
            All other services use direct SDK integration.
        """
        client_key = f"{client_type.__name__}_{kwargs.get('base_url', '')}"
        if client_key not in cls._clients:
            cls._clients[client_key] = client_type(**kwargs)
        return cls._clients[client_key]

    @classmethod
    def get_default_airbnb_client(
        cls, client_type: Type[BaseMCPClient]
    ) -> BaseMCPClient:
        """Get Airbnb client instance with default settings.

        Args:
            client_type: The type of client to get (AccommodationMCPClient).

        Returns:
            An Airbnb MCP client instance.
        """
        client_key = f"{client_type.__name__}_default"
        if client_key not in cls._clients:
            base_url = settings.get_mcp_url_for_type("accommodations")
            api_key = settings.get_api_key_for_type("accommodations")
            cls._clients[client_key] = client_type(base_url=base_url, api_key=api_key)
        return cls._clients[client_key]

    # Legacy method for backward compatibility during transition
    @classmethod
    def get_client(cls, client_type: Type[BaseMCPClient], **kwargs) -> BaseMCPClient:
        """Legacy method - delegates to get_airbnb_client."""
        return cls.get_airbnb_client(client_type, **kwargs)

    @classmethod
    def get_default_client(cls, client_type: Type[BaseMCPClient]) -> BaseMCPClient:
        """Legacy method - delegates to get_default_airbnb_client."""
        return cls.get_default_airbnb_client(client_type)
