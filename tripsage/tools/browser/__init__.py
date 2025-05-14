"""
Browser tools package for TripSage.

This package provides tools for browser automation using external MCPs.
"""

from .mcp_clients import BrowserError, PlaywrightMCPClient, StagehandMCPClient
from .service import BrowserService
from .tools import check_flight_status, monitor_price, verify_booking

__all__ = [
    "BrowserError",
    "BrowserService",
    "PlaywrightMCPClient",
    "StagehandMCPClient",
    "check_flight_status",
    "verify_booking",
    "monitor_price",
]
