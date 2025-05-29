"""Registry for MCP client wrappers."""

from functools import lru_cache
from typing import Dict, Optional, Type

from tripsage_core.utils.logging_utils import get_module_logger

from .base_wrapper import BaseMCPWrapper
from .exceptions import MCPRegistrationError

logger = get_module_logger(__name__)


class MCPClientRegistry:
    """Registry for managing MCP client wrappers.

    This registry maintains a mapping of MCP names to their wrapper classes,
    allowing for dynamic registration and retrieval of MCP clients.
    """

    def __init__(self):
        """Initialize the MCP client registry."""
        self._wrappers: Dict[str, Type[BaseMCPWrapper]] = {}
        self._instances: Dict[str, BaseMCPWrapper] = {}

    def register(
        self, mcp_name: str, wrapper_class: Type[BaseMCPWrapper], replace: bool = False
    ) -> None:
        """Register an MCP client wrapper.

        Args:
            mcp_name: Unique identifier for the MCP
            wrapper_class: The wrapper class for this MCP
            replace: Whether to replace an existing registration

        Raises:
            MCPRegistrationError: If the MCP is already registered and replace is False
        """
        if mcp_name in self._wrappers and not replace:
            raise MCPRegistrationError(
                f"MCP '{mcp_name}' is already registered. Use replace=True to override."
            )

        self._wrappers[mcp_name] = wrapper_class
        logger.info(
            "Registered MCP wrapper: %s -> %s", mcp_name, wrapper_class.__name__
        )

        # Clear cached instance if replacing
        if mcp_name in self._instances:
            del self._instances[mcp_name]

    def unregister(self, mcp_name: str) -> None:
        """Unregister an MCP client wrapper.

        Args:
            mcp_name: The MCP identifier to unregister

        Raises:
            MCPRegistrationError: If the MCP is not registered
        """
        if mcp_name not in self._wrappers:
            raise MCPRegistrationError(f"MCP '{mcp_name}' is not registered")

        del self._wrappers[mcp_name]
        logger.info("Unregistered MCP wrapper: %s", mcp_name)

        # Clear cached instance
        if mcp_name in self._instances:
            del self._instances[mcp_name]

    def get_wrapper_class(self, mcp_name: str) -> Type[BaseMCPWrapper]:
        """Get the wrapper class for an MCP.

        Args:
            mcp_name: The MCP identifier

        Returns:
            The wrapper class for the MCP

        Raises:
            MCPRegistrationError: If the MCP is not registered
        """
        if mcp_name not in self._wrappers:
            available = ", ".join(self._wrappers.keys())
            raise MCPRegistrationError(
                f"MCP '{mcp_name}' is not registered. Available MCPs: {available}"
            )

        return self._wrappers[mcp_name]

    def is_registered(self, mcp_name: str) -> bool:
        """Check if an MCP is registered.

        Args:
            mcp_name: The MCP identifier

        Returns:
            True if the MCP is registered, False otherwise
        """
        return mcp_name in self._wrappers

    def list_registered(self) -> list[str]:
        """Get list of all registered MCP names.

        Returns:
            List of registered MCP identifiers
        """
        return list(self._wrappers.keys())

    def get_wrapper_instance(
        self, mcp_name: str, client_instance: Optional[any] = None
    ) -> BaseMCPWrapper:
        """Get or create a wrapper instance for an MCP.

        Args:
            mcp_name: The MCP identifier
            client_instance: Optional pre-existing client instance

        Returns:
            The wrapper instance for the MCP

        Raises:
            MCPRegistrationError: If the MCP is not registered
        """
        # Get wrapper class
        wrapper_class = self.get_wrapper_class(mcp_name)

        # Return cached instance if available and no client provided
        if mcp_name in self._instances and client_instance is None:
            return self._instances[mcp_name]

        # Create new wrapper instance
        if client_instance is None:
            # Wrapper will create its own client
            wrapper = wrapper_class(mcp_name=mcp_name)
        else:
            # Use provided client
            wrapper = wrapper_class(client=client_instance, mcp_name=mcp_name)

        # Cache the instance if no specific client was provided
        if client_instance is None:
            self._instances[mcp_name] = wrapper

        return wrapper


# Singleton registry instance
@lru_cache()
def get_mcp_registry() -> MCPClientRegistry:
    """Get the singleton MCP client registry.

    Returns:
        The MCP client registry instance
    """
    return MCPClientRegistry()


# Convenience access to the singleton
mcp_registry = get_mcp_registry()
