"""Maps MCP clients for TripSage.

This package contains client implementations for interacting with
various map-related MCP servers, including Google Maps.
"""

from .google_maps_mcp_client import GoogleMapsMCPClient

__all__ = ["GoogleMapsMCPClient"]
