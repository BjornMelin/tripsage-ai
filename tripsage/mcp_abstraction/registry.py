"""
MCP Client Registry for managing MCP wrapper registrations.

This module provides a singleton registry for registering and retrieving
MCP wrapper classes.
"""

import threading
from typing import Dict, Optional, Type

from .base_wrapper import BaseMCPWrapper


class MCPClientRegistry:
    """Singleton registry for MCP client wrappers."""

    _instance: Optional["MCPClientRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MCPClientRegistry":
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the registry."""
        # Ensure initialization only happens once
        if not self._initialized:
            self._registry: Dict[str, Type[BaseMCPWrapper]] = {}
            self._initialized = True

    def register(
        self, mcp_name: str, wrapper_class: Type[BaseMCPWrapper], replace: bool = False
    ) -> None:
        """
        Register an MCP wrapper class.

        Args:
            mcp_name: The name identifier for the MCP
            wrapper_class: The wrapper class to register
            replace: Whether to replace an existing registration

        Raises:
            ValueError: If mcp_name is already registered and replace is False
        """
        if mcp_name in self._registry and not replace:
            raise ValueError(f"MCP '{mcp_name}' is already registered")

        if not issubclass(wrapper_class, BaseMCPWrapper):
            raise TypeError(
                f"Wrapper class must inherit from BaseMCPWrapper, got {wrapper_class}"
            )

        self._registry[mcp_name] = wrapper_class

    def get_wrapper_class(self, mcp_name: str) -> Type[BaseMCPWrapper]:
        """
        Get a registered wrapper class by name.

        Args:
            mcp_name: The name of the MCP to retrieve

        Returns:
            The registered wrapper class

        Raises:
            KeyError: If the MCP is not registered
        """
        if mcp_name not in self._registry:
            available_mcps = list(self._registry.keys())
            raise KeyError(
                f"MCP '{mcp_name}' not found in registry. "
                f"Available MCPs: {available_mcps}"
            )

        return self._registry[mcp_name]

    def is_registered(self, mcp_name: str) -> bool:
        """
        Check if an MCP is registered.

        Args:
            mcp_name: The name of the MCP to check

        Returns:
            True if the MCP is registered, False otherwise
        """
        return mcp_name in self._registry

    def get_registered_mcps(self) -> list[str]:
        """
        Get a list of all registered MCP names.

        Returns:
            List of registered MCP names
        """
        return list(self._registry.keys())


# Global registry instance
registry = MCPClientRegistry()
