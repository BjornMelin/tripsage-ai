"""External API client services with TripSage Core integration.

This module provides direct SDK/API integrations for external services.
Each service manages its own specific client requirements while providing
consistent async lifecycle, error handling, and type safety.
"""

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


__all__ = [
    "DocumentAnalyzer",
    "PlaywrightService",
    "close_document_analyzer",
    "close_playwright_service",
    "create_playwright_service",
    "get_document_analyzer",
    "get_playwright_service",
]
