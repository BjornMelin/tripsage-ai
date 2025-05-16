"""
MCP wrapper registration module.

This module handles the registration of specific MCP wrappers with the
MCPClientRegistry. This code runs automatically on import.
"""

from tripsage.mcp_abstraction.registry import registry
from tripsage.mcp_abstraction.wrappers.airbnb_wrapper import AirbnbMCPWrapper
from tripsage.mcp_abstraction.wrappers.crawl4ai_wrapper import Crawl4AIMCPWrapper
from tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper import (
    DuffelFlightsMCPWrapper,
)
from tripsage.mcp_abstraction.wrappers.firecrawl_wrapper import FirecrawlMCPWrapper
from tripsage.mcp_abstraction.wrappers.google_calendar_wrapper import (
    GoogleCalendarMCPWrapper,
)
from tripsage.mcp_abstraction.wrappers.google_maps_wrapper import GoogleMapsMCPWrapper
from tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper import Neo4jMemoryMCPWrapper
from tripsage.mcp_abstraction.wrappers.playwright_wrapper import PlaywrightMCPWrapper
from tripsage.mcp_abstraction.wrappers.redis_wrapper import RedisMCPWrapper
from tripsage.mcp_abstraction.wrappers.supabase_wrapper import SupabaseMCPWrapper
from tripsage.mcp_abstraction.wrappers.time_wrapper import TimeMCPWrapper
from tripsage.mcp_abstraction.wrappers.weather_wrapper import WeatherMCPWrapper
from tripsage.mcp_abstraction.wrappers.web_search_wrapper import (
    CachedWebSearchToolWrapper,
)
from tripsage.utils.logging import get_module_logger

logger = get_module_logger(__name__)


def register_default_wrappers():
    """
    Register the default MCP wrappers with the registry.

    This function is called automatically when this module is imported.
    """
    # Register Playwright MCP wrapper
    registry.register(
        mcp_name="playwright",
        wrapper_class=PlaywrightMCPWrapper,
        replace=True,
    )

    # Register Google Maps MCP wrapper
    registry.register(
        mcp_name="google_maps",
        wrapper_class=GoogleMapsMCPWrapper,
        replace=True,
    )

    # Register Weather MCP wrapper
    registry.register(
        mcp_name="weather",
        wrapper_class=WeatherMCPWrapper,
        replace=True,
    )

    # Register Supabase MCP wrapper
    registry.register(
        mcp_name="supabase",
        wrapper_class=SupabaseMCPWrapper,
        replace=True,
    )

    # Register Neo4j Memory MCP wrapper
    registry.register(
        mcp_name="neo4j_memory",
        wrapper_class=Neo4jMemoryMCPWrapper,
        replace=True,
    )

    # Register Duffel Flights MCP wrapper
    registry.register(
        mcp_name="duffel_flights",
        wrapper_class=DuffelFlightsMCPWrapper,
        replace=True,
    )

    # Register Airbnb MCP wrapper
    registry.register(
        mcp_name="airbnb",
        wrapper_class=AirbnbMCPWrapper,
        replace=True,
    )

    # Register Firecrawl MCP wrapper
    registry.register(
        mcp_name="firecrawl",
        wrapper_class=FirecrawlMCPWrapper,
        replace=True,
    )

    # Register Crawl4AI MCP wrapper
    registry.register(
        mcp_name="crawl4ai",
        wrapper_class=Crawl4AIMCPWrapper,
        replace=True,
    )

    # Register Time MCP wrapper
    registry.register(
        mcp_name="time",
        wrapper_class=TimeMCPWrapper,
        replace=True,
    )

    # Register Google Calendar MCP wrapper
    registry.register(
        mcp_name="google_calendar",
        wrapper_class=GoogleCalendarMCPWrapper,
        replace=True,
    )

    # Register Redis MCP wrapper
    registry.register(
        mcp_name="redis",
        wrapper_class=RedisMCPWrapper,
        replace=True,
    )

    # Register Web Search Tool wrapper
    registry.register(
        mcp_name="web_search",
        wrapper_class=CachedWebSearchToolWrapper,
        replace=True,
    )

    logger.info("Registered default MCP wrappers")


# Auto-register when this module is imported
register_default_wrappers()
