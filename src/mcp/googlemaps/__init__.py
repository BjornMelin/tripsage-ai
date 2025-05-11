"""
Google Maps MCP clients for the TripSage travel planning system.

This package provides MCP clients for the Google Maps Platform APIs,
enabling geocoding, place searches, directions, and other mapping functionality.
"""

from .client import GoogleMapsMCPClient, get_client

__all__ = ["GoogleMapsMCPClient", "get_client"]
