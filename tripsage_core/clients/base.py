"""Base client implementations for external services and MCPs."""

from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


class BaseClient:
    """Base client for all service integrations."""

    def __init__(self, base_url: str, api_key: str | None = None):
        """Initialize the base client.

        Args:
            base_url: The base URL for the service.
            api_key: Optional API key for authentication.
        """
        self.base_url = base_url
        self.api_key = api_key


class BaseMCPClient[T: BaseModel, R: BaseModel]:
    """Base client for MCP service integrations."""

    def __init__(self, base_url: str, api_key: str | None = None):
        """Initialize the base MCP client.

        Args:
            base_url: The base URL for the MCP service.
            api_key: Optional API key for authentication.
        """
        self.base_url = base_url
        self.api_key = api_key

    async def call_mcp(self, endpoint: str, request_model: T) -> R:
        """Call an MCP endpoint.

        Args:
            endpoint: The endpoint to call.
            request_model: The request model to send.

        Returns:
            The response model.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement call_mcp")
