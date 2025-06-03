"""
Base wrapper for the Airbnb MCP client.

This provides a minimal interface for the Airbnb MCP client wrapper.
"""

from abc import ABC, abstractmethod
from typing import Any, List


class BaseMCPWrapper(ABC):
    """Base class for the Airbnb MCP wrapper."""

    def __init__(self, client: Any, mcp_name: str = "airbnb"):
        """
        Initialize the MCP wrapper.

        Args:
            client: The underlying MCP client instance
            mcp_name: Name identifier for this MCP service
        """
        self._client = client
        self._mcp_name = mcp_name

    @abstractmethod
    def get_available_methods(self) -> List[str]:
        """
        Get list of available methods for this MCP.

        Returns:
            List of available method names
        """
        pass

    async def invoke_method(self, method_name: str, **kwargs) -> Any:
        """
        Invoke a method on the underlying MCP client.

        Args:
            method_name: The method name to invoke
            **kwargs: Keyword arguments for the method

        Returns:
            The result of the method invocation

        Raises:
            ValueError: If the method_name is not available
            MCPClientError: If the method invocation fails
        """
        from .exceptions import MCPClientError, MCPMethodNotFoundError

        # Check if method is available
        available_methods = self.get_available_methods()
        if method_name not in available_methods:
            raise MCPMethodNotFoundError(
                f"Method '{method_name}' not available for {self._mcp_name}. "
                f"Available methods: {available_methods}",
                mcp_name=self._mcp_name,
                method_name=method_name,
            )

        try:
            # For Airbnb, we map certain method names to the actual client methods
            if method_name in ["search_listings", "search_accommodations", "search"]:
                actual_method = "search_accommodations"
            elif method_name in [
                "get_listing_details",
                "get_listing",
                "get_details",
                "get_accommodation_details",
                "check_availability",
                "check_listing_availability",
            ]:
                actual_method = "get_listing_details"
            else:
                actual_method = method_name

            # Get the actual method from the client
            method = getattr(self._client, actual_method)

            # Invoke the method
            result = await method(**kwargs)

            return result

        except AttributeError as e:
            raise MCPClientError(
                f"Method '{actual_method}' not found on {self._mcp_name} client",
                mcp_name=self._mcp_name,
                original_error=e,
            ) from e
        except Exception as e:
            raise MCPClientError(
                f"Failed to invoke method '{method_name}' on {self._mcp_name}",
                mcp_name=self._mcp_name,
                original_error=e,
            ) from e
