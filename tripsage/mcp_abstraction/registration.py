"""
MCP wrapper registration module.

This module handles the registration of specific MCP wrappers with the
MCPClientRegistry. This code runs automatically on import.
"""

from tripsage.mcp_abstraction.registry import registry
from tripsage.mcp_abstraction.wrappers.airbnb_wrapper import AirbnbMCPWrapper
from tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper import DuffelFlightsMCPWrapper
from tripsage.mcp_abstraction.wrappers.google_maps_wrapper import GoogleMapsMCPWrapper
from tripsage.mcp_abstraction.wrappers.neo4j_memory_wrapper import Neo4jMemoryMCPWrapper
from tripsage.mcp_abstraction.wrappers.playwright_wrapper import PlaywrightMCPWrapper
from tripsage.mcp_abstraction.wrappers.supabase_wrapper import SupabaseMCPWrapper
from tripsage.mcp_abstraction.wrappers.weather_wrapper import WeatherMCPWrapper
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

    logger.info("Registered default MCP wrappers")


# Auto-register when this module is imported
register_default_wrappers()
