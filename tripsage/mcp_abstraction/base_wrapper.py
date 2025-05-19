"""
Base wrapper interface for MCP clients.

This provides a consistent interface for all MCP clients while allowing
for client-specific implementations.
"""

import abc
from typing import Any, Dict, List


class BaseMCPWrapper(abc.ABC):
    """Abstract base class for all MCP client wrappers."""

    def __init__(self, client: Any, mcp_name: str):
        """
        Initialize the MCP wrapper.

        Args:
            client: The underlying MCP client instance
            mcp_name: Name identifier for this MCP service
        """
        self._client = client
        self._mcp_name = mcp_name
        self._method_map = self._build_method_map()

    @abc.abstractmethod
    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from high-level method names to actual MCP method names.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        pass

    @abc.abstractmethod
    def get_available_methods(self) -> List[str]:
        """
        Get list of available methods for this MCP.

        Returns:
            List of available method names
        """
        pass

    def invoke_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        Invoke a method on the underlying MCP client.

        Args:
            method_name: The high-level method name to invoke
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            The result of the method invocation

        Raises:
            ValueError: If the method_name is not available
            MCPClientError: If the method invocation fails
        """
        from .exceptions import MCPClientError

        if method_name not in self._method_map:
            available_methods = self.get_available_methods()
            raise ValueError(
                f"Method '{method_name}' not available for {self._mcp_name}. "
                f"Available methods: {available_methods}"
            )

        actual_method_name = self._method_map[method_name]

        try:
            # Get the actual method from the client
            method = getattr(self._client, actual_method_name)

            # Invoke the method
            result = method(*args, **kwargs)

            return result

        except AttributeError as e:
            raise MCPClientError(
                f"Method '{actual_method_name}' not found on {self._mcp_name} client",
                mcp_name=self._mcp_name,
                original_error=e,
            ) from e
        except Exception as e:
            raise MCPClientError(
                f"Failed to invoke method '{method_name}' on {self._mcp_name}",
                mcp_name=self._mcp_name,
                original_error=e,
            ) from e

    def get_client(self) -> Any:
        """
        Get the underlying MCP client instance.

        Returns:
            The underlying MCP client
        """
        return self._client
