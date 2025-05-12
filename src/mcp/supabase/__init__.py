"""
Supabase MCP package for TripSage.

This package provides a client and service for interacting with the Supabase MCP Server,
which offers PostgreSQL database management focused on production environments.
"""

from .client import SupabaseMCPClient, get_client
from .service import SupabaseService, get_service

__all__ = [
    "SupabaseMCPClient",
    "get_client",
    "SupabaseService",
    "get_service",
]
