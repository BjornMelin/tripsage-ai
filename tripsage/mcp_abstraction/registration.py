"""
MCP wrapper registration module.

This module handles the registration of specific MCP wrappers with the
MCPClientRegistry. Wrappers are registered lazily to avoid circular imports.
"""

from tripsage.mcp_abstraction.registry import registry
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


def register_default_wrappers():
    """
    Register the default MCP wrappers with the registry using lazy loading.
    """
    # Weather MCP
    registry.register_lazy(
        mcp_name="weather",
        loader=lambda: _import_weather_wrapper(),
        replace=True,
    )

    # Google Maps MCP
    registry.register_lazy(
        mcp_name="google_maps",
        loader=lambda: _import_googlemaps_wrapper(),
        replace=True,
    )

    # Time MCP
    registry.register_lazy(
        mcp_name="time",
        loader=lambda: _import_time_wrapper(),
        replace=True,
    )

    # Supabase MCP
    registry.register_lazy(
        mcp_name="supabase",
        loader=lambda: _import_supabase_wrapper(),
        replace=True,
    )

    # Playwright MCP wrapper
    registry.register_lazy(
        mcp_name="playwright",
        loader=lambda: _import_playwright_wrapper(),
        replace=True,
    )

    # Neo4j Memory MCP wrapper
    registry.register_lazy(
        mcp_name="neo4j_memory",
        loader=lambda: _import_neo4j_memory_wrapper(),
        replace=True,
    )

    # Duffel Flights MCP wrapper
    registry.register_lazy(
        mcp_name="duffel_flights",
        loader=lambda: _import_duffel_flights_wrapper(),
        replace=True,
    )

    # Airbnb MCP wrapper
    registry.register_lazy(
        mcp_name="airbnb",
        loader=lambda: _import_airbnb_wrapper(),
        replace=True,
    )

    # Firecrawl MCP wrapper
    registry.register_lazy(
        mcp_name="firecrawl",
        loader=lambda: _import_firecrawl_wrapper(),
        replace=True,
    )

    # Crawl4AI MCP wrapper
    registry.register_lazy(
        mcp_name="crawl4ai",
        loader=lambda: _import_crawl4ai_wrapper(),
        replace=True,
    )

    # Google Calendar MCP wrapper
    registry.register_lazy(
        mcp_name="google_calendar",
        loader=lambda: _import_google_calendar_wrapper(),
        replace=True,
    )

    # Redis MCP wrapper
    registry.register_lazy(
        mcp_name="redis",
        loader=lambda: _import_redis_wrapper(),
        replace=True,
    )

    # Web Search Tool wrapper
    registry.register_lazy(
        mcp_name="web_search",
        loader=lambda: _import_web_search_wrapper(),
        replace=True,
    )

    logger.info("Registered default MCP wrappers (lazy loading)")


# Lazy import functions
def _import_weather_wrapper():
    from tripsage.mcp_abstraction.wrappers.weather_wrapper import WeatherMCPWrapper

    return WeatherMCPWrapper


def _import_googlemaps_wrapper():
    from tripsage.mcp_abstraction.wrappers.googlemaps_wrapper import (
        GoogleMapsMCPWrapper,
    )

    return GoogleMapsMCPWrapper


def _import_time_wrapper():
    from tripsage.mcp_abstraction.wrappers.time_wrapper import TimeMCPWrapper

    return TimeMCPWrapper


def _import_supabase_wrapper():
    from tripsage.mcp_abstraction.wrappers.supabase_wrapper import SupabaseMCPWrapper

    return SupabaseMCPWrapper


def _import_playwright_wrapper():
    from tripsage.mcp_abstraction.wrappers.playwright_wrapper import (
        PlaywrightMCPWrapper,
    )

    return PlaywrightMCPWrapper


def _import_neo4j_memory_wrapper():
    from tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper import (
        Neo4jMemoryMCPWrapper,
    )

    return Neo4jMemoryMCPWrapper


def _import_duffel_flights_wrapper():
    from tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper import (
        DuffelFlightsMCPWrapper,
    )

    return DuffelFlightsMCPWrapper


def _import_airbnb_wrapper():
    from tripsage.mcp_abstraction.wrappers.airbnb_wrapper import AirbnbMCPWrapper

    return AirbnbMCPWrapper


def _import_firecrawl_wrapper():
    from tripsage.mcp_abstraction.wrappers.firecrawl_wrapper import FirecrawlMCPWrapper

    return FirecrawlMCPWrapper


def _import_crawl4ai_wrapper():
    from tripsage.mcp_abstraction.wrappers.crawl4ai_wrapper import Crawl4AIMCPWrapper

    return Crawl4AIMCPWrapper


def _import_google_calendar_wrapper():
    from tripsage.mcp_abstraction.wrappers.google_calendar_wrapper import (
        GoogleCalendarMCPWrapper,
    )

    return GoogleCalendarMCPWrapper


def _import_redis_wrapper():
    from tripsage.mcp_abstraction.wrappers.redis_wrapper import RedisMCPWrapper

    return RedisMCPWrapper


def _import_web_search_wrapper():
    from tripsage.mcp_abstraction.wrappers.web_search_wrapper import (
        CachedWebSearchToolWrapper,
    )

    return CachedWebSearchToolWrapper
