"""Tests for simplified LangGraph tools using @tool decorator.

Tests the modern, simple tool implementation that replaces the over-engineered
registry system with direct tool functions.
"""

import json
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.unit.orchestration.test_utils import create_mock_services
from tripsage.orchestration.tools.tools import (
    AGENT_TOOLS,
    ALL_TOOLS,
    add_memory,
    geocode_location,
    get_all_tools,
    get_tools_for_agent,
    get_weather,
    health_check,
    search_accommodations,
    search_flights,
    search_memories,
    set_tool_services,
    web_search,
)
from tripsage_core.services.business.flight_service import FlightService


@pytest.fixture(autouse=True)
def services() -> Any:
    """Configure tool services container for each test."""
    container = create_mock_services()
    set_tool_services(container)
    return container


class _FlightResponse:
    """Simple stub representing a flight search response."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def model_dump_json(self) -> str:
        """Return JSON representation matching FlightService output."""
        return json.dumps(self._data)


class TestTools:
    """Test the simple tool implementations."""

    @pytest.mark.asyncio
    async def test_search_flights_tool(self, services: Any):
        """Test the search_flights tool function."""
        mock_result = {
            "flights": [
                {"airline": "Delta", "price": 299, "departure": "2024-03-15 10:00"}
            ]
        }
        flight_service = MagicMock(spec=FlightService)
        flight_service.search_flights = AsyncMock(
            return_value=_FlightResponse(mock_result)
        )
        services.flight_service = flight_service
        set_tool_services(services)

        # Test the tool
        result = await cast(Any, search_flights).ainvoke(
            {
                "origin": "NYC",
                "destination": "LAX",
                "departure_date": "2024-03-15",
                "passengers": 1,
            }
        )

        # Verify result
        assert isinstance(result, str)
        parsed_result = json.loads(result)
        assert "flights" in parsed_result
        assert len(parsed_result["flights"]) == 1
        assert parsed_result["flights"][0]["airline"] == "Delta"

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.tools._default_mcp_service")
    async def test_search_accommodations_tool(self, mock_mcp_service: Any):
        """Test the search_accommodations tool function."""
        mock_mcp_service.invoke = AsyncMock()
        mock_result = {
            "accommodations": [
                {"name": "Hotel California", "price": 150, "rating": 4.5}
            ]
        }
        mock_mcp_service.invoke.return_value = mock_result

        result = await cast(Any, search_accommodations).ainvoke(
            {
                "location": "San Francisco",
                "check_in": "2024-03-15",
                "check_out": "2024-03-17",
                "guests": 2,
            }
        )

        parsed_result = json.loads(result)
        assert "accommodations" in parsed_result
        assert parsed_result["accommodations"][0]["name"] == "Hotel California"

    @pytest.mark.asyncio
    async def test_geocode_location_tool(self, services: Any):
        """Test the geocode_location tool function."""
        place = MagicMock()
        place.model_dump.return_value = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "San Francisco, CA",
        }
        services.google_maps_service.connect = AsyncMock(return_value=None)
        services.google_maps_service.geocode = AsyncMock(return_value=[place])
        set_tool_services(services)

        result = await cast(Any, geocode_location).ainvoke(
            {"location": "San Francisco"}
        )

        parsed_result = json.loads(result)[0]
        assert parsed_result["latitude"] == 37.7749
        assert parsed_result["longitude"] == -122.4194

    @pytest.mark.asyncio
    async def test_get_weather_tool(self, services: Any):
        """Test the get_weather tool function."""
        weather_payload = {"temperature": 68, "condition": "Sunny", "humidity": 45}
        services.weather_service.connect = AsyncMock(return_value=None)
        services.weather_service.get_current_weather = AsyncMock(
            return_value=weather_payload
        )
        set_tool_services(services)

        result = await cast(Any, get_weather).ainvoke({"location": "San Francisco"})

        parsed_result = json.loads(result)
        assert parsed_result["temperature"] == 68
        assert parsed_result["condition"] == "Sunny"

    @pytest.mark.asyncio
    async def test_web_search_tool(self, services: Any):
        """Test the web_search tool function."""
        mock_result = {
            "results": [{"title": "Best time to visit Paris", "url": "example.com"}]
        }
        services.webcrawl_service.connect = AsyncMock(return_value=None)
        services.webcrawl_service.search_web = AsyncMock(return_value=mock_result)
        set_tool_services(services)

        result = await cast(Any, web_search).ainvoke(
            {"query": "best time to visit Paris", "location": "Paris"}
        )

        parsed_result = json.loads(result)
        assert "results" in parsed_result
        assert len(parsed_result["results"]) == 1

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.tools._search_user_memories")
    @patch("tripsage.orchestration.tools.tools._add_conversation_memory")
    @patch("tripsage.orchestration.tools.tools._default_mcp_service")
    async def test_memory_tools(
        self,
        mock_mcp_service: Any,
        mock_add_conversation_memory: Any,
        mock_search_user_memories: Any,
    ) -> None:
        """Test the memory add and search tools."""
        # Test add_memory
        mock_mcp_service.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_add_conversation_memory.return_value = {
            "success": True,
            "id": "mem_123",
        }

        result = await cast(Any, add_memory).ainvoke(
            {"content": "User prefers window seats", "category": "preferences"}
        )

        parsed_result = json.loads(result)
        assert parsed_result["success"] is True

        # Test search_memories
        mock_search_user_memories.return_value = [
            {"content": "User prefers window seats", "category": "preferences"}
        ]

        result = await cast(Any, search_memories).ainvoke(
            {"content": "seat preferences"}
        )

        parsed_result = json.loads(result)
        assert "results" in parsed_result
        assert len(parsed_result["results"]) == 1

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, services: Any):
        """Test tool error handling."""
        failing_flight_service = MagicMock(spec=FlightService)
        failing_flight_service.search_flights = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        services.flight_service = failing_flight_service
        set_tool_services(services)

        result = await cast(Any, search_flights).ainvoke(
            {"origin": "NYC", "destination": "LAX", "departure_date": "2024-03-15"}
        )

        parsed_result = json.loads(result)
        assert "error" in parsed_result
        assert "Service unavailable" in parsed_result["error"]

    def test_get_tools_for_agent(self):
        """Test getting tools for specific agent types."""
        # Test flight agent tools
        flight_tools = get_tools_for_agent("flight_agent")
        assert len(flight_tools) > 0
        assert search_flights in flight_tools
        assert geocode_location in flight_tools

        # Test accommodation agent tools
        accommodation_tools = get_tools_for_agent("accommodation_agent")
        assert search_accommodations in accommodation_tools

        # Test unknown agent type
        unknown_tools = get_tools_for_agent("unknown_agent")
        assert len(unknown_tools) == 0

    def test_get_all_tools(self):
        """Test getting all available tools."""
        all_tools = get_all_tools()
        assert len(all_tools) == len(ALL_TOOLS)
        assert search_flights in all_tools
        assert search_accommodations in all_tools
        assert geocode_location in all_tools

    def test_agent_tools_catalog(self):
        """Test the AGENT_TOOLS catalog structure."""
        # Verify all expected agent types are present
        expected_agents = [
            "flight_agent",
            "accommodation_agent",
            "destination_research_agent",
            "budget_agent",
            "itinerary_agent",
            "memory_update",
        ]

        for agent in expected_agents:
            assert agent in AGENT_TOOLS
            assert len(AGENT_TOOLS[agent]) > 0

        # Verify flight agent has flight tools
        assert search_flights in AGENT_TOOLS["flight_agent"]

        # Verify accommodation agent has accommodation tools
        assert search_accommodations in AGENT_TOOLS["accommodation_agent"]

        # Verify memory agent has memory tools
        assert add_memory in AGENT_TOOLS["memory_update"]
        assert search_memories in AGENT_TOOLS["memory_update"]

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.tools._get_mcp_service")
    async def test_health_check(self, mock_get_mcp_service: Any):
        """Test the health check function."""
        # Mock successful health check
        mock_mcp_service = MagicMock()
        mock_get_mcp_service.return_value = mock_mcp_service
        mock_mcp_service.health_check = AsyncMock(
            return_value={"status": "healthy", "service": "airbnb"}
        )

        result = await health_check()

        assert "healthy" in result
        assert "unhealthy" in result
        assert result["total_tools"] == len(ALL_TOOLS)
        assert "timestamp" in result

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.tools._get_mcp_service")
    async def test_health_check_failure(self, mock_get_mcp_service: Any):
        """Test health check when service is unavailable."""
        mock_mcp_service = MagicMock()
        mock_get_mcp_service.return_value = mock_mcp_service
        mock_mcp_service.health_check = AsyncMock(
            return_value={"status": "error", "error": "Connection failed"}
        )

        result = await health_check()

        assert len(result["unhealthy"]) > 0
        assert result["unhealthy"][0]["service"] == "airbnb_mcp"
        assert result["unhealthy"][0]["error"]["error"] == "Connection failed"


class TestToolSchemaValidation:
    """Test tool parameter schema validation."""

    def test_flight_search_params_schema(self):
        """Test FlightSearchParams schema validation."""
        from tripsage.orchestration.tools.tools import FlightSearchParams

        # Valid params
        valid_params = FlightSearchParams(
            origin="NYC", destination="LAX", departure_date="2024-03-15", passengers=2
        )
        assert valid_params.origin == "NYC"
        assert valid_params.passengers == 2

        # Test defaults
        assert valid_params.class_preference == "economy"

    def test_accommodation_search_params_schema(self):
        """Test AccommodationSearchParams schema validation."""
        from tripsage.orchestration.tools.tools import AccommodationSearchParams

        valid_params = AccommodationSearchParams(
            location="San Francisco",
            check_in="2024-03-15",
            check_out="2024-03-17",
            guests=2,
            price_max=200.0,
        )
        assert valid_params.location == "San Francisco"
        assert valid_params.guests == 2
        assert valid_params.price_max == 200.0

    def test_memory_params_schema(self):
        """Test MemoryParams schema validation."""
        from tripsage.orchestration.tools.tools import MemoryParams

        valid_params = MemoryParams(
            content="User prefers aisle seats", category="preferences"
        )
        assert valid_params.content == "User prefers aisle seats"
        assert valid_params.category == "preferences"


class TestToolIntegration:
    """Integration tests for tool functionality."""

    @pytest.mark.asyncio
    async def test_tool_chain_execution(self, services: Any):
        """Test chaining multiple tools together."""
        place = MagicMock()
        place.model_dump.return_value = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "San Francisco, CA",
        }
        services.google_maps_service.connect = AsyncMock(return_value=None)
        services.google_maps_service.geocode = AsyncMock(return_value=[place])

        services.weather_service.connect = AsyncMock(return_value=None)
        services.weather_service.get_current_weather = AsyncMock(
            return_value={"temperature": 68, "condition": "Sunny"}
        )

        flight_service = MagicMock(spec=FlightService)
        flight_service.search_flights = AsyncMock(
            return_value=_FlightResponse(
                {
                    "flights": [
                        {
                            "airline": "United",
                            "price": 299,
                            "departure": "2024-03-15",
                        }
                    ]
                }
            )
        )
        services.flight_service = flight_service
        set_tool_services(services)

        # Execute a chain of tools
        # 1. Geocode location
        geocode_result = await cast(Any, geocode_location).ainvoke(
            {"location": "San Francisco"}
        )
        geocode_data = json.loads(geocode_result)[0]
        assert geocode_data["latitude"] == 37.7749

        # 2. Get weather
        weather_result = await cast(Any, get_weather).ainvoke(
            {"location": "San Francisco"}
        )
        weather_data = json.loads(weather_result)
        assert weather_data["temperature"] == 68

        # 3. Search flights
        flight_result = await cast(Any, search_flights).ainvoke(
            {
                "origin": "NYC",
                "destination": "SFO",
                "departure_date": "2024-03-15",
            }
        )
        flight_data = json.loads(flight_result)
        assert len(flight_data["flights"]) == 1
        assert flight_data["flights"][0]["airline"] == "United"

    def test_tool_name_uniqueness(self):
        """Test that all tools have unique names."""
        tool_names = [tool.name for tool in ALL_TOOLS]
        assert len(tool_names) == len(set(tool_names)), "Tool names must be unique"

    def test_tool_descriptions(self):
        """Test that all tools have meaningful descriptions."""
        for tool in ALL_TOOLS:
            assert tool.description is not None
            assert len(tool.description) > 10, (
                f"Tool {tool.name} needs a better description"
            )
            # Memory tools should mention memory, other tools should mention
            # travel or location
            if "memory" in tool.name:
                assert "memory" in tool.description.lower()
            else:
                assert (
                    "travel" in tool.description.lower()
                    or "location" in tool.description.lower()
                    or "weather" in tool.description.lower()
                    or "search" in tool.description.lower()
                    or "accommodation" in tool.description.lower()
                    or "flight" in tool.description.lower()
                )
