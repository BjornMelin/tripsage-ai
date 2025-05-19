"""Factory for creating clients for external services and MCPs."""

from typing import Dict, Type

from tripsage.clients.base import BaseClient, BaseMCPClient
from tripsage.config.app_settings import settings


class ClientFactory:
    """Factory for creating clients."""

    _clients: Dict[str, BaseClient] = {}

    @classmethod
    def get_client(cls, client_type: Type[BaseClient], **kwargs) -> BaseClient:
        """Get a client instance.

        Args:
            client_type: The type of client to get.
            **kwargs: Additional arguments to pass to the client constructor.

        Returns:
            A client instance.
        """
        client_key = f"{client_type.__name__}_{kwargs.get('base_url', '')}"
        if client_key not in cls._clients:
            cls._clients[client_key] = client_type(**kwargs)
        return cls._clients[client_key]


class MCPClientFactory:
    """Factory for creating MCP clients."""

    _clients: Dict[str, BaseMCPClient] = {}

    @classmethod
    def get_client(cls, client_type: Type[BaseMCPClient], **kwargs) -> BaseMCPClient:
        """Get an MCP client instance.

        Args:
            client_type: The type of MCP client to get.
            **kwargs: Additional arguments to pass to the client constructor.

        Returns:
            An MCP client instance.
        """
        client_key = f"{client_type.__name__}_{kwargs.get('base_url', '')}"
        if client_key not in cls._clients:
            cls._clients[client_key] = client_type(**kwargs)
        return cls._clients[client_key]

    @classmethod
    def get_default_client(cls, client_type: Type[BaseMCPClient]) -> BaseMCPClient:
        """Get a client instance with default settings.

        Args:
            client_type: The type of client to get.

        Returns:
            A client instance.
        """
        client_key = f"{client_type.__name__}_default"
        if client_key not in cls._clients:
            base_url = settings.get_mcp_url_for_type(client_type.__name__)
            api_key = settings.get_api_key_for_type(client_type.__name__)
            cls._clients[client_key] = client_type(base_url=base_url, api_key=api_key)
        return cls._clients[client_key]
