"""
Simplified MCP Registry for Airbnb wrapper.

This module provides a lightweight registry that only handles the Airbnb
MCP wrapper, since all other services use direct SDK integration.
"""

from typing import Optional

from tripsage_core.utils.logging_utils import get_logger

from .base_wrapper import BaseMCPWrapper
from .exceptions import MCPRegistrationError

logger = get_logger(__name__)


class MCPRegistry:
    """Simple registry for the Airbnb MCP wrapper."""

    def __init__(self):
        """Initialize the MCP registry."""
        self._wrapper_class: Optional[type[BaseMCPWrapper]] = None
        self._wrapper_instance: Optional[BaseMCPWrapper] = None

    def register_airbnb(self, wrapper_class: type[BaseMCPWrapper]) -> None:
        """
        Register the Airbnb wrapper class.

        Args:
            wrapper_class: The Airbnb wrapper class

        Raises:
            MCPRegistrationError: If wrapper class is invalid
        """
        if not issubclass(wrapper_class, BaseMCPWrapper):
            raise MCPRegistrationError("Wrapper class must inherit from BaseMCPWrapper")

        self._wrapper_class = wrapper_class
        logger.info("Registered Airbnb MCP wrapper")

    def get_airbnb_wrapper(self) -> type[BaseMCPWrapper]:
        """
        Get the Airbnb wrapper class.

        Returns:
            The Airbnb wrapper class

        Raises:
            MCPRegistrationError: If wrapper is not registered
        """
        if self._wrapper_class is None:
            # Auto-register if not already done
            self._auto_register()

        if self._wrapper_class is None:
            raise MCPRegistrationError("Airbnb MCP wrapper not registered")

        return self._wrapper_class

    def _auto_register(self) -> None:
        """Auto-register the Airbnb wrapper."""
        try:
            from .wrappers import AirbnbMCPWrapper

            self.register_airbnb(AirbnbMCPWrapper)
        except ImportError as e:
            logger.error(f"Failed to auto-register Airbnb wrapper: {e}")

    def get_registered_mcps(self) -> list[str]:
        """
        Get list of registered MCP names.

        For backward compatibility, returns only 'airbnb' since
        all other services have been migrated to direct SDK.

        Returns:
            List containing only 'airbnb'
        """
        return ["airbnb"] if self._wrapper_class else []

    def get_wrapper_class(self, mcp_name: str) -> type[BaseMCPWrapper]:
        """
        Get wrapper class by MCP name.

        For backward compatibility. Only supports 'airbnb'.

        Args:
            mcp_name: MCP name (must be 'airbnb')

        Returns:
            The Airbnb wrapper class

        Raises:
            MCPRegistrationError: If mcp_name is not 'airbnb'
        """
        if mcp_name != "airbnb":
            raise MCPRegistrationError(
                f"MCP '{mcp_name}' is not supported. "
                "Only 'airbnb' remains after SDK migration."
            )
        return self.get_airbnb_wrapper()


# Global registry instance
registry = MCPRegistry()
