"""
Simple LangGraph tools for TripSage using @tool decorator.

This module defines all tools using the modern LangGraph @tool pattern,
replacing the over-engineered registry system with simple, direct tool functions.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from tripsage_core.services.simple_mcp_service import mcp_manager
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


# Tool parameter schemas using Pydantic for validation
class FlightSearchParams(BaseModel):
    """Parameters for flight search."""
    origin: str = Field(description="Origin airport code or city")
    destination: str = Field(description="Destination airport code or city") 
    departure_date: str = Field(description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(default=None, description="Return date (YYYY-MM-DD)")
    passengers: int = Field(default=1, description="Number of passengers")
    class_preference: Optional[str] = Field(default="economy", description="Flight class (economy, business, first)")


class AccommodationSearchParams(BaseModel):
    """Parameters for accommodation search."""
    location: str = Field(description="Location to search for accommodations")
    check_in: str = Field(description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(description="Check-out date (YYYY-MM-DD)")
    guests: int = Field(default=1, description="Number of guests")
    price_min: Optional[float] = Field(default=None, description="Minimum price per night")
    price_max: Optional[float] = Field(default=None, description="Maximum price per night")


class MemoryParams(BaseModel):
    """Parameters for memory operations."""
    content: str = Field(description="Information to save or search for")
    category: Optional[str] = Field(default=None, description="Memory category")


class LocationParams(BaseModel):
    """Parameters for location operations."""
    location: str = Field(description="Location name or address")


class WebSearchParams(BaseModel):
    """Parameters for web search."""
    query: str = Field(description="Search query")
    location: Optional[str] = Field(default=None, description="Location context for search")


# Core Travel Tools
@tool("search_flights", args_schema=FlightSearchParams)
async def search_flights(
    origin: str,
    destination: str, 
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    class_preference: str = "economy"
) -> str:
    """Search for flights between locations with filters for dates, passengers, and preferences."""
    try:
        result = await mcp_manager.invoke(
            method_name="search_flights",
            params={
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "passengers": passengers,
                "class": class_preference
            }
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Flight search failed: {e}")
        return json.dumps({"error": f"Flight search failed: {str(e)}"})


@tool("search_accommodations", args_schema=AccommodationSearchParams)
async def search_accommodations(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 1,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None
) -> str:
    """Search for accommodations in a location with check-in/out dates and guest requirements."""
    try:
        params = {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests
        }
        if price_min is not None:
            params["price_min"] = price_min
        if price_max is not None:
            params["price_max"] = price_max
            
        result = await mcp_manager.invoke(
            method_name="search_listings",
            params=params
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Accommodation search failed: {e}")
        return json.dumps({"error": f"Accommodation search failed: {str(e)}"})


@tool("geocode_location", args_schema=LocationParams)
async def geocode_location(location: str) -> str:
    """Get geographic coordinates and details for a location."""
    try:
        result = await mcp_manager.invoke(
            method_name="geocode",
            params={"location": location}
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Geocoding failed: {e}")
        return json.dumps({"error": f"Geocoding failed: {str(e)}"})


@tool("get_weather", args_schema=LocationParams)
async def get_weather(location: str) -> str:
    """Get current weather information for a location."""
    try:
        result = await mcp_manager.invoke(
            method_name="get_current_weather",
            params={"location": location}
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Weather lookup failed: {e}")
        return json.dumps({"error": f"Weather lookup failed: {str(e)}"})


@tool("web_search", args_schema=WebSearchParams)
async def web_search(query: str, location: Optional[str] = None) -> str:
    """Search the web for travel-related information."""
    try:
        params = {"query": query}
        if location:
            params["location"] = location
            
        result = await mcp_manager.invoke(
            method_name="search",
            params=params
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return json.dumps({"error": f"Web search failed: {str(e)}"})


@tool("add_memory", args_schema=MemoryParams)
async def add_memory(content: str, category: Optional[str] = None) -> str:
    """Save important information to user memory for future reference."""
    try:
        params = {"content": content}
        if category:
            params["category"] = category
            
        result = await mcp_manager.invoke(
            method_name="add_memory",
            params=params
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Memory addition failed: {e}")
        return json.dumps({"error": f"Memory addition failed: {str(e)}"})


@tool("search_memories", args_schema=MemoryParams)
async def search_memories(content: str, category: Optional[str] = None) -> str:
    """Search user memories for relevant information."""
    try:
        params = {"query": content}
        if category:
            params["category"] = category
            
        result = await mcp_manager.invoke(
            method_name="search_memories",
            params=params
        )
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return json.dumps({"error": f"Memory search failed: {str(e)}"})


# Tool catalog for agent-specific tool access
AGENT_TOOLS = {
    "flight_agent": [
        search_flights,
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories
    ],
    "accommodation_agent": [
        search_accommodations,
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories
    ],
    "destination_research_agent": [
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories
    ],
    "budget_agent": [
        search_flights,
        search_accommodations,
        web_search,
        add_memory,
        search_memories
    ],
    "itinerary_agent": [
        search_flights,
        search_accommodations,
        geocode_location,
        get_weather,
        web_search,
        add_memory,
        search_memories
    ],
    "memory_update": [
        add_memory,
        search_memories
    ]
}

# All available tools list
ALL_TOOLS = [
    search_flights,
    search_accommodations,
    geocode_location,
    get_weather,
    web_search,
    add_memory,
    search_memories
]


def get_tools_for_agent(agent_type: str) -> List:
    """Get tools for a specific agent type."""
    return AGENT_TOOLS.get(agent_type, [])


def get_all_tools() -> List:
    """Get all available tools."""
    return ALL_TOOLS


async def health_check() -> Dict[str, Any]:
    """Perform basic health check on core tools."""
    healthy = []
    unhealthy = []
    
    try:
        # Test basic MCP connectivity
        await mcp_manager.invoke("health_check", {})
        healthy.append("mcp_manager")
    except Exception as e:
        unhealthy.append({"service": "mcp_manager", "error": str(e)})
    
    return {
        "healthy": healthy,
        "unhealthy": unhealthy,
        "total_tools": len(ALL_TOOLS),
        "timestamp": datetime.now().isoformat()
    }