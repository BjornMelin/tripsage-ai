"""External API client services with TripSage Core integration.

This module provides direct SDK/API integrations for external services,
replacing MCP wrappers with high-performance native implementations.
"""

from .calendar_service import (
    GoogleCalendarService,
    close_calendar_service,
    get_calendar_service,
)
from .document_analyzer import (
    DocumentAnalyzer,
    close_document_analyzer,
    get_document_analyzer,
)
from .google_maps_service import GoogleMapsService
from .playwright_service import (
    PlaywrightService,
    close_playwright_service,
    get_playwright_service,
)
from .time_service import TimeService, close_time_service, get_time_service
from .weather_service import WeatherService
from .webcrawl_service import (
    WebCrawlService,
)


__all__ = [
    "DocumentAnalyzer",
    # Service classes
    "GoogleCalendarService",
    "GoogleMapsService",
    "PlaywrightService",
    "TimeService",
    "WeatherService",
    "WebCrawlService",
    "close_calendar_service",
    "close_document_analyzer",
    # Service closers
    "close_playwright_service",
    "close_time_service",
    "get_calendar_service",
    "get_document_analyzer",
    # Global service getters
    "get_playwright_service",
    "get_time_service",
]
