"""TripSage MCP Abstraction Layer.

This module provides a unified abstraction layer for interacting with
various external MCP clients, serving as the primary way TripSage tools
and services interact with MCPs.
"""

from .base_wrapper import BaseMCPWrapper
from .exceptions import (
    MCPInvocationError,
    MCPManagerError,
    MCPMethodNotFoundError,
    MCPNotFoundError,
    TripSageMCPError,
)
from .manager import mcp_manager
from .registry import registry

__all__ = [
    # Manager
    "mcp_manager",
    # Registry
    "registry",
    # Base Wrapper
    "BaseMCPWrapper",
    # Exceptions
    "TripSageMCPError",
    "MCPNotFoundError",
    "MCPManagerError",
    "MCPInvocationError",
    "MCPMethodNotFoundError",
]
