"""
Tests for simplified LangGraph tools using @tool decorator.

Tests the modern, simple tool implementation that replaces the over-engineered
registry system with direct tool functions.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.orchestration.tools import (
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
    web_search,
)


class TestSimpleTools:
    """Test the simple tool implementations."""

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_search_flights_tool(self, mock_mcp_manager):
        """Test the search_flights tool function."""
        # Mock MCP manager response
        mock_result = {
            "flights": [
                {"airline": "Delta", "price": 299, "departure": "2024-03-15 10:00"}
            ]
        }
        mock_mcp_manager.invoke = AsyncMock(return_value=mock_result)

        # Test the tool
        result = await search_flights.ainvoke(
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
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_search_accommodations_tool(self, mock_mcp_manager):
        """Test the search_accommodations tool function."""
        mock_result = {
            "accommodations": [
                {"name": "Hotel California", "price": 150, "rating": 4.5}
            ]
        }
        mock_mcp_manager.invoke = AsyncMock(return_value=mock_result)

        result = await search_accommodations.ainvoke(
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
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_geocode_location_tool(self, mock_mcp_manager):
        """Test the geocode_location tool function."""
        mock_result = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "San Francisco, CA",
        }
        mock_mcp_manager.invoke = AsyncMock(return_value=mock_result)

        result = await geocode_location.ainvoke({"location": "San Francisco"})

        parsed_result = json.loads(result)
        assert parsed_result["latitude"] == 37.7749
        assert parsed_result["longitude"] == -122.4194

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_get_weather_tool(self, mock_mcp_manager):
        """Test the get_weather tool function."""
        mock_result = {"temperature": 68, "condition": "Sunny", "humidity": 45}
        mock_mcp_manager.invoke = AsyncMock(return_value=mock_result)

        result = await get_weather.ainvoke({"location": "San Francisco"})

        parsed_result = json.loads(result)
        assert parsed_result["temperature"] == 68
        assert parsed_result["condition"] == "Sunny"

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_web_search_tool(self, mock_mcp_manager):
        """Test the web_search tool function."""
        mock_result = {
            "results": [{"title": "Best time to visit Paris", "url": "example.com"}]
        }
        mock_mcp_manager.invoke = AsyncMock(return_value=mock_result)

        result = await web_search.ainvoke(
            {"query": "best time to visit Paris", "location": "Paris"}
        )

        parsed_result = json.loads(result)
        assert "results" in parsed_result
        assert len(parsed_result["results"]) == 1

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_memory_tools(self, mock_mcp_manager):
        """Test the memory add and search tools."""
        # Test add_memory
        mock_mcp_manager.invoke = AsyncMock(
            return_value={"success": True, "id": "mem_123"}
        )

        result = await add_memory.ainvoke(
            {"content": "User prefers window seats", "category": "preferences"}
        )

        parsed_result = json.loads(result)
        assert parsed_result["success"] is True

        # Test search_memories
        mock_mcp_manager.invoke = AsyncMock(
            return_value={
                "memories": [
                    {"content": "User prefers window seats", "category": "preferences"}
                ]
            }
        )

        result = await search_memories.ainvoke({"content": "seat preferences"})

        parsed_result = json.loads(result)
        assert "memories" in parsed_result
        assert len(parsed_result["memories"]) == 1

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_tool_error_handling(self, mock_mcp_manager):
        """Test tool error handling."""
        # Mock MCP manager to raise an exception
        mock_mcp_manager.invoke = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        result = await search_flights.ainvoke(
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
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_health_check(self, mock_mcp_manager):
        """Test the health check function."""
        # Mock successful health check
        mock_mcp_manager.invoke = AsyncMock(return_value={"status": "healthy"})

        result = await health_check()

        assert "healthy" in result
        assert "unhealthy" in result
        assert result["total_tools"] == len(ALL_TOOLS)
        assert "timestamp" in result

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_health_check_failure(self, mock_mcp_manager):
        """Test health check when service is unavailable."""
        mock_mcp_manager.invoke = AsyncMock(side_effect=Exception("Connection failed"))

        result = await health_check()

        assert len(result["unhealthy"]) > 0
        assert result["unhealthy"][0]["service"] == "mcp_manager"
        assert "Connection failed" in result["unhealthy"][0]["error"]


class TestToolSchemaValidation:
    """Test tool parameter schema validation."""

    def test_flight_search_params_schema(self):
        """Test FlightSearchParams schema validation."""
        from tripsage.orchestration.tools.simple_tools import FlightSearchParams

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
        from tripsage.orchestration.tools.simple_tools import AccommodationSearchParams

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
        from tripsage.orchestration.tools.simple_tools import MemoryParams

        valid_params = MemoryParams(
            content="User prefers aisle seats", category="preferences"
        )
        assert valid_params.content == "User prefers aisle seats"
        assert valid_params.category == "preferences"


class TestToolIntegration:
    """Integration tests for tool functionality."""

    @pytest.mark.asyncio
    @patch("tripsage.orchestration.tools.simple_tools.mcp_manager")
    async def test_tool_chain_execution(self, mock_mcp_manager):
        """Test chaining multiple tools together."""
        # Mock responses for different tools
        mock_responses = {
            "geocode": {"latitude": 37.7749, "longitude": -122.4194},
            "get_current_weather": {"temperature": 68, "condition": "Sunny"},
            "search_flights": {"flights": [{"airline": "United", "price": 299}]},
        }

        def mock_invoke(method_name, params):
            return mock_responses.get(method_name, {})

        mock_mcp_manager.invoke = AsyncMock(side_effect=mock_invoke)

        # Execute a chain of tools
        # 1. Geocode location
        geocode_result = await geocode_location.ainvoke({"location": "San Francisco"})
        geocode_data = json.loads(geocode_result)
        assert geocode_data["latitude"] == 37.7749

        # 2. Get weather
        weather_result = await get_weather.ainvoke({"location": "San Francisco"})
        weather_data = json.loads(weather_result)
        assert weather_data["temperature"] == 68

        # 3. Search flights
        flight_result = await search_flights.ainvoke(
            {
                "origin": "NYC",
                "destination": "San Francisco",
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
            # Memory tools should mention memory, other tools should mention travel or location
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
