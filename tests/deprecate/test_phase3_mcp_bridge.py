"""
Test suite for Phase 3 LangGraph-MCP Bridge implementation.

This module tests the LangGraphMCPBridge that integrates the existing MCP abstraction
layer with LangGraph's tool system while preserving all existing functionality.
"""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.prebuilt import ToolNode

from tripsage.orchestration.mcp_bridge import LangGraphMCPBridge, get_mcp_bridge


class TestLangGraphMCPBridge:
    """Test suite for the LangGraph-MCP Bridge."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager for testing."""
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock:
            mock_instance = MagicMock()
            mock_instance.services = {
                "flights": MagicMock(),
                "accommodations": MagicMock(),
                "google_maps": MagicMock(),
                "weather": MagicMock(),
                "time": MagicMock(),
                "webcrawl": MagicMock(),
                "memory": MagicMock(),
            }
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def bridge(self, mock_mcp_manager):
        """Create test bridge instance."""
        return LangGraphMCPBridge()

    @pytest.mark.asyncio
    async def test_bridge_initialization(self, bridge, mock_mcp_manager):
        """Test bridge initialization with MCP manager."""
        await bridge.initialize()

        assert bridge.mcp_manager is not None
        assert bridge._tool_cache == {}  # Should start empty
        assert bridge._initialized is True

    @pytest.mark.asyncio
    async def test_get_tools_with_caching(self, bridge, mock_mcp_manager):
        """Test tool retrieval with caching mechanism."""
        # Mock service tools
        mock_mcp_manager.services["flights"].get_tools.return_value = [
            {"name": "search_flights", "description": "Search for flights"}
        ]
        mock_mcp_manager.services["accommodations"].get_tools.return_value = [
            {"name": "search_accommodations", "description": "Search accommodations"}
        ]

        await bridge.initialize()

        # First call should populate cache
        tools_1 = await bridge.get_tools()
        assert len(tools_1) >= 2
        assert bridge._tool_cache  # Cache should be populated

        # Second call should use cache
        tools_2 = await bridge.get_tools()
        assert tools_1 == tools_2

        # Verify tools have correct structure
        for tool in tools_1:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert callable(tool.func)

    @pytest.mark.asyncio
    async def test_filtered_tools_for_agent(self, bridge, mock_mcp_manager):
        """Test filtered tool retrieval for specific agents."""
        # Mock different services returning tools
        mock_mcp_manager.services["flights"].get_tools.return_value = [
            {"name": "search_flights", "description": "Search for flights"},
            {"name": "book_flight", "description": "Book a flight"},
        ]
        mock_mcp_manager.services["accommodations"].get_tools.return_value = [
            {"name": "search_accommodations", "description": "Search accommodations"}
        ]

        await bridge.initialize()

        # Flight agent should get flight tools + common tools
        flight_tools = await bridge.get_tools_for_agent("flight_agent")
        flight_tool_names = [tool.name for tool in flight_tools]
        assert "flights_search_flights" in flight_tool_names
        assert "flights_book_flight" in flight_tool_names

        # Accommodation agent should get accommodation tools + common tools
        accommodation_tools = await bridge.get_tools_for_agent("accommodation_agent")
        accommodation_tool_names = [tool.name for tool in accommodation_tools]
        assert "accommodations_search_accommodations" in accommodation_tool_names

    @pytest.mark.asyncio
    async def test_direct_tool_invocation(self, bridge, mock_mcp_manager):
        """Test direct tool invocation through MCP manager."""
        # Mock successful MCP response
        expected_result = {"flights": [{"id": "FL123", "price": "$500"}]}
        mock_mcp_manager.invoke.return_value = expected_result

        await bridge.initialize()

        # Test direct invocation
        result = await bridge.invoke_tool_direct(
            "flights_search_flights",
            {"origin": "NYC", "destination": "LAX", "date": "2025-06-01"},
        )

        assert result == expected_result
        mock_mcp_manager.invoke.assert_called_once_with(
            "flights",
            "search_flights",
            {"origin": "NYC", "destination": "LAX", "date": "2025-06-01"},
        )

    @pytest.mark.asyncio
    async def test_tool_invocation_error_handling(self, bridge, mock_mcp_manager):
        """Test error handling in tool invocation."""
        # Mock MCP manager to raise exception
        mock_mcp_manager.invoke.side_effect = Exception("MCP service unavailable")

        await bridge.initialize()

        # Direct invocation should handle errors gracefully
        with pytest.raises(Exception) as exc_info:
            await bridge.invoke_tool_direct("flights_search_flights", {})

        assert "MCP service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_node_creation(self, bridge, mock_mcp_manager):
        """Test creation of LangGraph ToolNode from MCP tools."""
        mock_mcp_manager.services["flights"].get_tools.return_value = [
            {"name": "search_flights", "description": "Search for flights"}
        ]

        await bridge.initialize()

        # Create tool node for specific agent
        tool_node = await bridge.create_tool_node("flight_agent")

        assert isinstance(tool_node, ToolNode)
        # Tool node should have the agent's tools
        assert len(tool_node.tools_by_name) > 0

    @pytest.mark.asyncio
    async def test_service_availability_check(self, bridge, mock_mcp_manager):
        """Test service availability checking."""
        # Mock some services as available, others not
        mock_mcp_manager.is_service_available.side_effect = lambda service: service in [
            "flights",
            "accommodations",
        ]

        await bridge.initialize()

        # Should only get tools from available services
        tools = await bridge.get_tools()
        assert isinstance(tools, list)

        # Verify calls were made to check availability
        assert mock_mcp_manager.is_service_available.call_count >= 1

    @pytest.mark.asyncio
    async def test_tool_name_conversion(self, bridge, mock_mcp_manager):
        """Test proper tool name conversion from MCP format to LangGraph format."""
        mock_mcp_manager.services["flights"].get_tools.return_value = [
            {"name": "search_flights", "description": "Search for flights"}
        ]

        await bridge.initialize()
        tools = await bridge.get_tools()

        # Tool names should be prefixed with service name
        tool_names = [tool.name for tool in tools]
        assert any("flights_search_flights" in name for name in tool_names)

    @pytest.mark.asyncio
    async def test_concurrent_tool_access(self, bridge, mock_mcp_manager):
        """Test concurrent access to tools."""
        import asyncio

        mock_mcp_manager.services["flights"].get_tools.return_value = [
            {"name": "search_flights", "description": "Search for flights"}
        ]

        await bridge.initialize()

        # Multiple concurrent calls should work correctly
        tasks = [
            bridge.get_tools(),
            bridge.get_tools(),
            bridge.get_tools_for_agent("flight_agent"),
            bridge.get_tools_for_agent("accommodation_agent"),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 4
        for result in results:
            assert isinstance(result, list)

    def test_singleton_bridge_access(self):
        """Test singleton access to bridge."""
        bridge1 = get_mcp_bridge()
        bridge2 = get_mcp_bridge()

        assert bridge1 is bridge2  # Should be same instance

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self, bridge, mock_mcp_manager):
        """Test tool parameter validation and conversion."""
        # Mock tool with specific parameters
        mock_mcp_manager.services["flights"].get_tools.return_value = [
            {
                "name": "search_flights",
                "description": "Search for flights",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "destination": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                    },
                    "required": ["origin", "destination"],
                },
            }
        ]

        await bridge.initialize()
        tools = await bridge.get_tools()

        # Should have proper parameter schema
        flight_tool = next(t for t in tools if "search_flights" in t.name)
        assert flight_tool.description
        # Tool should be callable
        assert callable(flight_tool.func)

    @pytest.mark.asyncio
    async def test_memory_integration(self, bridge, mock_mcp_manager):
        """Test integration with memory tools."""
        mock_mcp_manager.services["memory"].get_tools.return_value = [
            {"name": "create_entities", "description": "Create memory entities"},
            {"name": "search_nodes", "description": "Search memory nodes"},
        ]

        await bridge.initialize()
        tools = await bridge.get_tools()

        # Should include memory tools
        tool_names = [tool.name for tool in tools]
        assert any("memory_create_entities" in name for name in tool_names)
        assert any("memory_search_nodes" in name for name in tool_names)
