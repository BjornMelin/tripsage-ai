"""
TripSage API Services Module.

This module re-exports core service functions for use in the API layer.
"""

# Re-export service functions from core modules for API compatibility
from tripsage_core.services.business.chat_service import get_chat_service

__all__ = [
    "get_chat_service",
]
