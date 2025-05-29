"""Wrapper implementation for Airbnb MCP client.

Only the Airbnb wrapper remains as it has no official SDK.
All other services have been migrated to direct SDK integration.
"""

from .airbnb_wrapper import AirbnbMCPWrapper

__all__ = ["AirbnbMCPWrapper"]
