"""External API client services with TripSage Core integration.

This module provides direct SDK/API integrations for external services.
Each service manages its own specific client requirements while providing
consistent async lifecycle, error handling, and type safety.
"""

from .calendar_service import (
    GoogleCalendarService,
    create_calendar_service,
    create_calendar_service_with_token,
)
from .document_analyzer import (
    DocumentAnalyzer,
    close_document_analyzer,
    get_document_analyzer,
)
from .playwright_service import (
    PlaywrightService,
    close_playwright_service,
    create_playwright_service,
    get_playwright_service,
)
from .time_service import TimeService, close_time_service, get_time_service
from .webcrawl_service import (
    WebCrawlService,
)


__all__ = [
    "DocumentAnalyzer",
    "GoogleCalendarService",
    "PlaywrightService",
    "TimeService",
    "WebCrawlService",
    "close_document_analyzer",
    "close_playwright_service",
    "close_time_service",
    "create_calendar_service",
    "create_calendar_service_with_token",
    "create_playwright_service",
    "get_document_analyzer",
    "get_playwright_service",
    "get_time_service",
]
