"""
Accommodations MCP clients for the TripSage travel planning system.

This package provides MCP clients for various accommodation providers,
including Airbnb, to enable searching and retrieving accommodation information.
"""

from .client import AirbnbMCPClient
from .factory import create_airbnb_client

__all__ = ["AirbnbMCPClient", "create_airbnb_client"]
