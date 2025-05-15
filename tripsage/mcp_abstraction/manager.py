"""
MCP Manager for orchestrating all MCP operations.

This module provides a singleton manager that handles configuration loading,
client initialization, and method routing for all MCP clients.
"""

import threading
from typing import Any, Dict, Optional

from .base_wrapper import BaseMCPWrapper
from .exceptions import MCPManagerError, MCPNotFoundError
from .registry import registry


class MCPManager:
    """Singleton manager for all MCP operations."""

    _instance: Optional["MCPManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MCPManager":
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the manager."""
        # Ensure initialization only happens once
        if not self._initialized:
            self._wrappers: Dict[str, BaseMCPWrapper] = {}
            self._configs: Dict[str, Dict[str, Any]] = {}
            self._initialized = True

    def load_configurations(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Load MCP configurations.

        Args:
            configs: Dictionary of MCP configurations
        """
        self._configs = configs

    async def initialize_mcp(self, mcp_name: str) -> BaseMCPWrapper:
        """
        Initialize an MCP wrapper instance.

        Args:
            mcp_name: The name of the MCP to initialize

        Returns:
            The initialized MCP wrapper

        Raises:
            MCPNotFoundError: If the MCP is not registered
            MCPManagerError: If initialization fails
        """
        # Check if already initialized
        if mcp_name in self._wrappers:
            return self._wrappers[mcp_name]

        try:
            # Get the wrapper class from registry
            wrapper_class = registry.get_wrapper_class(mcp_name)

            # Create client and wrapper
            # Note: The actual client initialization will depend on
            # the specific MCP implementation
            wrapper = wrapper_class(client=None, mcp_name=mcp_name)

            # Store the wrapper
            self._wrappers[mcp_name] = wrapper

            return wrapper

        except KeyError as e:
            raise MCPNotFoundError(
                f"MCP '{mcp_name}' not found in registry", mcp_name=mcp_name
            ) from e
        except Exception as e:
            raise MCPManagerError(
                f"Failed to initialize MCP '{mcp_name}': {str(e)}"
            ) from e

    async def initialize_all_enabled(self) -> None:
        """
        Initialize all enabled MCPs based on configuration.

        This method will initialize all MCPs that have configurations loaded.
        """
        for mcp_name in self._configs:
            try:
                await self.initialize_mcp(mcp_name)
            except Exception as e:
                # Log the error but continue with other MCPs
                print(f"Failed to initialize MCP '{mcp_name}': {e}")

    async def invoke(
        self,
        mcp_name: str,
        method_name: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke a method on an MCP.

        Args:
            mcp_name: The name of the MCP to use
            method_name: The method to invoke
            params: Method parameters as a dictionary
            **kwargs: Additional keyword arguments

        Returns:
            The result from the MCP method call

        Raises:
            MCPNotFoundError: If the MCP is not found
            MCPManagerError: If the invocation fails
        """
        try:
            # Initialize the MCP if not already done
            wrapper = await self.initialize_mcp(mcp_name)

            # Prepare parameters
            call_params = params or {}
            call_params.update(kwargs)

            # Invoke the method
            return wrapper.invoke_method(method_name, **call_params)

        except Exception as e:
            raise MCPManagerError(
                f"Failed to invoke {mcp_name}.{method_name}: {str(e)}"
            ) from e

    def get_available_mcps(self) -> list[str]:
        """
        Get a list of available (registered) MCPs.

        Returns:
            List of available MCP names
        """
        return registry.get_registered_mcps()

    def get_initialized_mcps(self) -> list[str]:
        """
        Get a list of initialized MCPs.

        Returns:
            List of initialized MCP names
        """
        return list(self._wrappers.keys())


# Global manager instance
mcp_manager = MCPManager()
