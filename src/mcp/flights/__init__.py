"""
Flight MCP Initialization module.

This module provides initialization functions for the Flight MCP module.
"""

from .client import get_client, get_service

__all__ = ["get_client", "get_service"]
