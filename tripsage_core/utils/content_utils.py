"""
Content type definitions for TripSage Core caching utilities.

This module provides content type enums without dependencies on settings
or other complex modules to avoid circular import issues.
"""

from enum import Enum

class ContentType(str, Enum):
    """Content types for web operations with different TTL requirements."""

    # Real-time data that should never be cached for long periods
    # (weather, stock prices)
    REALTIME = "realtime"
    # Time-sensitive information that changes frequently (news, social media)
    TIME_SENSITIVE = "time_sensitive"
    # Information that changes daily but remains relevant (flight prices, events)
    DAILY = "daily"
    # Information that changes infrequently (restaurant menus, business details)
    SEMI_STATIC = "semi_static"
    # Information that rarely changes (historical data, documentation)
    STATIC = "static"
    # Structured data (JSON, XML)
    JSON = "json"
    # Markdown formatted text
    MARKDOWN = "markdown"
    # HTML formatted text
    HTML = "html"
    # Binary data (images, PDFs, etc.)
    BINARY = "binary"

def get_ttl_for_content_type(content_type: ContentType) -> int:
    """Get the appropriate TTL for a content type."""
    ttl_map = {
        ContentType.REALTIME: 60,  # 1 minute
        ContentType.TIME_SENSITIVE: 300,  # 5 minutes
        ContentType.DAILY: 3600,  # 1 hour
        ContentType.SEMI_STATIC: 28800,  # 8 hours
        ContentType.STATIC: 86400,  # 24 hours
    }
    return ttl_map.get(content_type, 3600)  # Default 1 hour
