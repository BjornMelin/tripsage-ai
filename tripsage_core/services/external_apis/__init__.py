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
from .duffel_http_client import DuffelHTTPClient, close_duffel_client, get_duffel_client
from .google_maps_service import (
    GoogleMapsService,
    close_google_maps_service,
    get_google_maps_service,
)
from .playwright_service import (
    PlaywrightService,
    close_playwright_service,
    get_playwright_service,
)
from .time_service import TimeService, close_time_service, get_time_service
from .weather_service import WeatherService, close_weather_service, get_weather_service
from .webcrawl_service import (
    WebCrawlService,
    close_webcrawl_service,
    get_webcrawl_service,
)


__all__ = [
    # Service classes
    "DuffelHTTPClient",
    "GoogleMapsService",
    "WeatherService",
    "GoogleCalendarService",
    "WebCrawlService",
    "PlaywrightService",
    "DocumentAnalyzer",
    "TimeService",
    # Global service getters
    "get_duffel_client",
    "get_google_maps_service",
    "get_weather_service",
    "get_calendar_service",
    "get_webcrawl_service",
    "get_playwright_service",
    "get_document_analyzer",
    "get_time_service",
    # Service closers
    "close_duffel_client",
    "close_google_maps_service",
    "close_weather_service",
    "close_calendar_service",
    "close_webcrawl_service",
    "close_playwright_service",
    "close_document_analyzer",
    "close_time_service",
]
