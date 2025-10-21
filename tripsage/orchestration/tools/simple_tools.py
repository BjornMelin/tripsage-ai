"""Simple LangGraph tools for TripSage using @tool decorator.

This module defines all tools using the modern LangGraph @tool pattern,
replacing the over-engineered registry system with simple, direct tool functions.
"""

import json
from datetime import datetime
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from tripsage.tools.memory_tools import (
    add_conversation_memory as _add_conversation_memory,
    search_user_memories as _search_user_memories,
)
from tripsage.tools.models import ConversationMessage
from tripsage_core.services.simple_mcp_service import mcp_manager
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


# Tool parameter schemas using Pydantic for validation
class FlightSearchParams(BaseModel):
    """Parameters for flight search."""

    origin: str = Field(description="Origin airport code or city")
    destination: str = Field(description="Destination airport code or city")
    departure_date: str = Field(description="Departure date (YYYY-MM-DD)")
    return_date: str | None = Field(
        default=None, description="Return date (YYYY-MM-DD)"
    )
    passengers: int = Field(default=1, description="Number of passengers")
    class_preference: str | None = Field(
        default="economy", description="Flight class (economy, business, first)"
    )


class AccommodationSearchParams(BaseModel):
    """Parameters for accommodation search."""

    location: str = Field(description="Location to search for accommodations")
    check_in: str = Field(description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(description="Check-out date (YYYY-MM-DD)")
    guests: int = Field(default=1, description="Number of guests")
    price_min: float | None = Field(default=None, description="Minimum price per night")
    price_max: float | None = Field(default=None, description="Maximum price per night")


class MemoryParams(BaseModel):
    """Parameters for memory operations."""

    content: str = Field(description="Information to save or search for")
    category: str | None = Field(default=None, description="Memory category")


class LocationParams(BaseModel):
    """Parameters for location operations."""

    location: str = Field(description="Location name or address")


class WebSearchParams(BaseModel):
    """Parameters for web search."""

    query: str = Field(description="Search query")
    location: str | None = Field(
        default=None, description="Location context for search"
    )


# Core Travel Tools
@tool("search_flights", args_schema=FlightSearchParams)
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    passengers: int = 1,
    class_preference: str = "economy",
) -> str:
    """Search for flights with date and passenger filters."""
    try:
        result = await mcp_manager.invoke(
            method_name="search_flights",
            params={
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "passengers": passengers,
                "class": class_preference,
            },
        )

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Flight search failed")
        return json.dumps({"error": f"Flight search failed: {e!s}"})


@tool("search_accommodations", args_schema=AccommodationSearchParams)
async def search_accommodations(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 1,
    price_min: float | None = None,
    price_max: float | None = None,
) -> str:
    """Search accommodations by location and dates."""
    try:
        params = {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
        }
        if price_min is not None:
            params["price_min"] = price_min
        if price_max is not None:
            params["price_max"] = price_max

        result = await mcp_manager.invoke(method_name="search_listings", params=params)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Accommodation search failed")
        return json.dumps({"error": f"Accommodation search failed: {e!s}"})


@tool("geocode_location", args_schema=LocationParams)
async def geocode_location(location: str) -> str:
    """Get geographic coordinates and details for a location."""
    try:
        result = await mcp_manager.invoke(
            method_name="geocode", params={"location": location}
        )

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Geocoding failed")
        return json.dumps({"error": f"Geocoding failed: {e!s}"})


@tool("get_weather", args_schema=LocationParams)
async def get_weather(location: str) -> str:
    """Get current weather information for a location."""
    try:
        result = await mcp_manager.invoke(
            method_name="get_current_weather", params={"location": location}
        )

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Weather lookup failed")
        return json.dumps({"error": f"Weather lookup failed: {e!s}"})


@tool("web_search", args_schema=WebSearchParams)
async def web_search(query: str, location: str | None = None) -> str:
    """Search the web for travel-related information."""
    try:
        params = {"query": query}
        if location:
            params["location"] = location

        result = await mcp_manager.invoke(method_name="search", params=params)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Web search failed")
        return json.dumps({"error": f"Web search failed: {e!s}"})


@tool("add_memory", args_schema=MemoryParams)
async def add_memory(content: str, category: str | None = None) -> str:
    """Save important information to user memory for future reference."""
    try:
        # Persist a simple note as a conversation memory for the current thread.
        # User identity should be supplied via graph config in production. For now,
        # we use a system user to record general notes when no principal is bound.
        messages = [
            ConversationMessage(
                role="system", content="Persist important user-facing note."
            ),
            ConversationMessage(role="user", content=content),
        ]
        meta = {"type": "note"}
        if category:
            meta["category"] = category
        result = await _add_conversation_memory(
            messages=messages, user_id="system", metadata=meta
        )

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Memory addition failed")
        return json.dumps({"error": f"Memory addition failed: {e!s}"})


@tool("search_memories", args_schema=MemoryParams)
async def search_memories(content: str, category: str | None = None) -> str:
    """Search user memories for relevant information."""
    try:
        from tripsage.tools.models import (
            MemorySearchQuery,
        )  # local import to avoid cycles

        query = MemorySearchQuery(
            query=content,
            user_id="system",
            limit=10,
            category_filter=category,
        )
        results = await _search_user_memories(query)
        return json.dumps({"results": results, "query": content}, ensure_ascii=False)
    except Exception as e:
        logger.exception("Memory search failed")
        return json.dumps({"error": f"Memory search failed: {e!s}"})


# Tool catalog for agent-specific tool access
AGENT_TOOLS = {
    "flight_agent": [
        search_flights,
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories,
    ],
    "accommodation_agent": [
        search_accommodations,
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories,
    ],
    "destination_research_agent": [
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories,
    ],
    "budget_agent": [
        search_flights,
        search_accommodations,
        web_search,
        add_memory,
        search_memories,
    ],
    "itinerary_agent": [
        search_flights,
        search_accommodations,
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories,
    ],
    "memory_update": [add_memory, search_memories],
}

# All available tools list
ALL_TOOLS = [
    search_flights,
    search_accommodations,
    geocode_location,
    get_weather,
    web_search,
    add_memory,
    search_memories,
]


def get_tools_for_agent(agent_type: str) -> list:
    """Get tools for a specific agent type."""
    return AGENT_TOOLS.get(agent_type, [])


def get_all_tools() -> list:
    """Get all available tools."""
    return ALL_TOOLS


async def health_check() -> dict[str, Any]:
    """Perform basic health check on core tools."""
    healthy = []
    unhealthy = []

    try:
        # Test basic MCP connectivity
        await mcp_manager.invoke("health_check", {})
        healthy.append("mcp_manager")
    except (ConnectionError, TimeoutError, ValueError) as e:
        unhealthy.append({"service": "mcp_manager", "error": str(e)})

    return {
        "healthy": healthy,
        "unhealthy": unhealthy,
        "total_tools": len(ALL_TOOLS),
        "timestamp": datetime.now().isoformat(),
    }
