# pylint: disable=too-many-positional-arguments
"""LangGraph tools for TripSage using @tool decorator.

This module defines all tools using the modern LangGraph @tool pattern,
replacing the over-engineered registry system with simple, direct tool functions.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from tripsage.app_state import AppServiceContainer
from tripsage.tools.memory_tools import (
    add_conversation_memory as _add_conversation_memory_raw,
    search_user_memories as _search_user_memories_raw,
)
from tripsage.tools.models import ConversationMessage
from tripsage_core.services.airbnb_mcp import AirbnbMCP, default_airbnb_mcp
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
)
from tripsage_core.services.external_apis.weather_service import WeatherService
from tripsage_core.services.external_apis.webcrawl_service import (
    WebCrawlParams,
    WebCrawlService,
)
from tripsage_core.utils.logging_utils import get_logger


if TYPE_CHECKING:
    from tripsage.tools.models import MemorySearchQuery


logger = get_logger(__name__)

_services_container: AppServiceContainer | None = None
_default_mcp_service: Final = default_airbnb_mcp
_mcp_service: AirbnbMCP | None = None


def set_tool_services(services: AppServiceContainer) -> None:
    """Provide the lifespan-managed services to the tools module."""
    global _services_container  # pylint: disable=global-statement
    global _mcp_service  # pylint: disable=global-statement

    _services_container = services
    try:
        _mcp_service = services.get_optional_service(
            "mcp_service",
            expected_type=AirbnbMCP,
        )
    except TypeError:
        _mcp_service = None


def _require_services() -> AppServiceContainer:
    """Return the active service container or raise if missing."""
    if _services_container is None:
        raise RuntimeError(
            "AppServiceContainer not initialised for orchestration tools; "
            "set_tool_services must be called during application startup.",
        )
    return _services_container


def _get_service_from_container[ServiceT](
    service_name: str,
    expected_type: type[ServiceT],
) -> ServiceT:
    """Fetch a required service from the container with type validation."""
    services = _require_services()
    return services.get_required_service(
        service_name,
        expected_type=expected_type,
    )


def _get_mcp_service() -> AirbnbMCP:
    """Return the configured MCP service singleton."""
    return _mcp_service or _default_mcp_service


AddMemoryFn = Callable[..., Awaitable[dict[str, Any]]]
SearchMemoryFn = Callable[["MemorySearchQuery"], Awaitable[list[dict[str, Any]]]]

_add_conversation_memory: AddMemoryFn = _add_conversation_memory_raw
_search_user_memories: SearchMemoryFn = _search_user_memories_raw


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
    """Search for flights with date and passenger filters using FlightService."""
    try:
        from tripsage_core.models.schemas_common.flight_schemas import (
            FlightPassenger,
            FlightSearchRequest,
        )

        service = _get_service_from_container("flight_service", FlightService)
        pax = [FlightPassenger(type="adult") for _ in range(max(1, passengers))]  # type: ignore[call-arg]
        req = FlightSearchRequest(  # type: ignore[call-arg]
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=pax,
            cabin_class=class_preference or "economy",
        )
        resp = await service.search_flights(req)
        return resp.model_dump_json()
    except Exception as e:  # pragma: no cover - defensive
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

        result = await _get_mcp_service().invoke(
            method_name="search_listings",
            params=params,
        )

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("Accommodation search failed")
        return json.dumps({"error": f"Accommodation search failed: {e!s}"})


@tool("geocode_location", args_schema=LocationParams)
async def geocode_location(location: str) -> str:
    """Get geographic coordinates and details for a location via GoogleMapsService."""
    try:
        svc = _get_service_from_container("google_maps_service", GoogleMapsService)
        await svc.connect()
        places = await svc.geocode(location)
        return json.dumps([p.model_dump() for p in places], ensure_ascii=False)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Geocoding failed")
        return json.dumps({"error": f"Geocoding failed: {e!s}"})


@tool("get_weather", args_schema=LocationParams)
async def get_weather(location: str) -> str:
    """Get current weather information for a location using WeatherService."""
    try:
        svc = _get_service_from_container("weather_service", WeatherService)
        await svc.connect()
        # WeatherService signature may vary; pass location as a plain string
        # pylint: disable=no-value-for-parameter
        data = await svc.get_current_weather(location)  # type: ignore[call-arg]
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("Weather lookup failed")
        return json.dumps({"error": f"Weather lookup failed: {e!s}"})


@tool("web_search", args_schema=WebSearchParams)
async def web_search(query: str, location: str | None = None) -> str:
    """Search the web for travel-related information using WebCrawlService."""
    try:
        svc = _get_service_from_container("webcrawl_service", WebCrawlService)
        await svc.connect()
        params: WebCrawlParams = WebCrawlParams(
            javascript_enabled=False, extract_markdown=True, extract_html=False
        )
        # Use a generic search engine wrapper if available; else crawl query URL
        # For now, just return an empty result to satisfy interface if not implemented.
        # Some builds may not expose `search_web`; tolerate via pylint hint
        # pylint: disable=no-member
        # pyright: ignore[reportAttributeAccessIssue]
        result = await svc.search_web(query=query, location=location, params=params)  # type: ignore[attr-defined]
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:  # pragma: no cover - defensive
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
AGENT_TOOLS: dict[str, list[BaseTool]] = {
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
ALL_TOOLS: list[BaseTool] = [
    search_flights,
    search_accommodations,
    geocode_location,
    get_weather,
    web_search,
    add_memory,
    search_memories,
]


def get_tools_for_agent(agent_type: str) -> list[BaseTool]:
    """Get tools for a specific agent type."""
    return AGENT_TOOLS.get(agent_type, [])


def get_all_tools() -> list[BaseTool]:
    """Get all available tools."""
    return ALL_TOOLS


async def health_check() -> dict[str, Any]:
    """Perform basic health check on core tools."""
    healthy = []
    unhealthy = []

    try:
        status = await _get_mcp_service().health_check()
        if status.get("status") == "healthy":
            healthy.append("airbnb_mcp")
        else:
            unhealthy.append({"service": "airbnb_mcp", "error": status})
    except (ConnectionError, TimeoutError, ValueError) as exc:
        unhealthy.append({"service": "airbnb_mcp", "error": str(exc)})

    return {
        "healthy": healthy,
        "unhealthy": unhealthy,
        "total_tools": len(ALL_TOOLS),
        "timestamp": datetime.now().isoformat(),
    }


__all__ = [
    "AGENT_TOOLS",
    "ALL_TOOLS",
    "AccommodationSearchParams",
    "FlightSearchParams",
    "LocationParams",
    "MemoryParams",
    "WebSearchParams",
    "add_memory",
    "geocode_location",
    "get_all_tools",
    "get_tools_for_agent",
    "get_weather",
    "health_check",
    "search_accommodations",
    "search_flights",
    "search_memories",
    "set_tool_services",
    "web_search",
]
