"""
MCP Client Registry for managing MCP wrapper registrations.

This module provides a singleton registry for registering and retrieving
MCP wrapper classes.
"""

import threading
from typing import Callable, Dict, Optional, Type

from tripsage.utils.logging import get_logger

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
            self._lazy_loaders: Dict[str, Callable[[], Type[BaseMCPWrapper]]] = {}
            self._initialized = True
            self._auto_register_called = False

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

    def register_lazy(
        self,
        mcp_name: str,
        loader: Callable[[], Type[BaseMCPWrapper]],
        replace: bool = False,
    ) -> None:
        """
        Register a lazy loader for an MCP wrapper class.

        Args:
            mcp_name: The name identifier for the MCP
            loader: A callable that returns the wrapper class when called
            replace: Whether to replace an existing registration
        """
        if mcp_name in self._lazy_loaders and not replace:
            raise ValueError(f"MCP '{mcp_name}' is already registered")

        self._lazy_loaders[mcp_name] = loader

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
        # First check if it's already loaded
        if mcp_name in self._registry:
            return self._registry[mcp_name]

        # Check if we have a lazy loader for it
        if mcp_name in self._lazy_loaders:
            loader = self._lazy_loaders[mcp_name]
            wrapper_class = loader()
            self._registry[mcp_name] = wrapper_class
            return wrapper_class

        # If not found, auto-register if we haven't already
        if not self._auto_register_called:
            self._auto_register()
            # Try again after auto-registration
            if mcp_name in self._registry:
                return self._registry[mcp_name]
            if mcp_name in self._lazy_loaders:
                loader = self._lazy_loaders[mcp_name]
                wrapper_class = loader()
                self._registry[mcp_name] = wrapper_class
                return wrapper_class

        # Still not found
        available_mcps = list(self._registry.keys()) + list(self._lazy_loaders.keys())
        raise KeyError(
            f"MCP '{mcp_name}' not found in registry. Available MCPs: {available_mcps}"
        )

    def _auto_register(self):
        """Auto-register default wrappers."""
        if self._auto_register_called:
            return

        self._auto_register_called = True

        # Import and run registration
        try:
            from . import registration

            registration.register_default_wrappers()
        except ImportError as e:
            # Registration module not available, skip
            import traceback

            logger = get_logger(__name__)
            logger.debug(f"Failed to auto-register: {e}")
            logger.debug(traceback.format_exc())
            pass

    def is_registered(self, mcp_name: str) -> bool:
        """
        Check if an MCP is registered.

        Args:
            mcp_name: The name of the MCP to check

        Returns:
            True if the MCP is registered, False otherwise
        """
        return mcp_name in self._registry or mcp_name in self._lazy_loaders

    def get_registered_mcps(self) -> list[str]:
        """
        Get a list of all registered MCP names.

        Returns:
            List of registered MCP names
        """
        return list(self._registry.keys()) + list(self._lazy_loaders.keys())


# Global registry instance
registry = MCPClientRegistry()
