"""
Neon MCP client package for TripSage.

This package provides a client for interacting with the Neon PostgreSQL database
service through the MCP (Model Context Protocol) interface.
"""

from .client import NeonMCPClient, get_client
from .service import NeonService, get_service

__all__ = ["NeonMCPClient", "get_client", "NeonService", "get_service"]
