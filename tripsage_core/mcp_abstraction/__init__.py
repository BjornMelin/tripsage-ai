"""
TripSage MCP Abstraction Layer for Airbnb.

This module provides a simplified abstraction layer for the Airbnb MCP client,
which is the only remaining MCP integration in TripSage.
"""

from .base_wrapper import BaseMCPWrapper
from .exceptions import (
    MCPAuthenticationError,
    MCPClientError,
    MCPInvocationError,
    MCPMethodNotFoundError,
    MCPRateLimitError,
    MCPRegistrationError,
    MCPTimeoutError,
    TripSageMCPError,
)
from .manager import MCPManager, mcp_manager
from .registry import registry
from .wrappers import AirbnbMCPWrapper

__all__ = [
    # Manager
    "MCPManager",
    "mcp_manager",
    # Registry
    "registry",
    # Wrappers
    "BaseMCPWrapper",
    "AirbnbMCPWrapper",
    # Exceptions
    "TripSageMCPError",
    "MCPClientError",
    "MCPRegistrationError",
    "MCPInvocationError",
    "MCPMethodNotFoundError",
    "MCPTimeoutError",
    "MCPAuthenticationError",
    "MCPRateLimitError",
]
