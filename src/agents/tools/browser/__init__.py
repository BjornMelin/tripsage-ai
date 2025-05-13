"""
Browser tools for TripSage agents.

This module contains tools for browser automation using external MCPs:
- Playwright MCP for precise browser control
- Stagehand MCP for AI-driven browser interactions
"""

from .tools import (
    check_flight_status,
    check_flight_status_sync,
    get_browser_tool_definitions,
    monitor_price,
    monitor_price_sync,
    verify_booking,
    verify_booking_sync,
)

__all__ = [
    "check_flight_status",
    "check_flight_status_sync",
    "get_browser_tool_definitions",
    "monitor_price",
    "monitor_price_sync",
    "verify_booking",
    "verify_booking_sync",
]
