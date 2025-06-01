"""
Tests for the simplified Airbnb MCP bridge for LangGraph integration.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from langchain_core.tools import Tool

from tripsage.mcp_abstraction.exceptions import MCPInvocationError
from tripsage.orchestration.mcp_bridge import (
    AirbnbToolWrapper,
    LangGraphMCPBridge,
    create_airbnb_tool,
    get_airbnb_tools,
    get_mcp_bridge,
)


class TestLangGraphMCPBridge:
    """Test the LangGraph-Airbnb MCP bridge functionality."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCPManager."""
        manager = MagicMock()
        manager.initialize = AsyncMock()
        manager.invoke = AsyncMock()
        manager.get_available_methods.return_value = [
            "search_listings",
            "search_accommodations",
            "search",
            "get_listing_details",
            "get_listing",
            "check_availability",
        ]
        return manager

    @pytest.fixture
    def bridge(self, mock_mcp_manager):
        """Create a bridge instance with mock manager."""
        return LangGraphMCPBridge(mcp_manager=mock_mcp_manager)

    async def test_initialize_loads_airbnb_tools(self, bridge, mock_mcp_manager):
        """Test that initialize loads Airbnb tool metadata."""
        await bridge.initialize()

        assert bridge._initialized is True
        assert len(bridge._tool_metadata) > 0

        # Check that all method variations are loaded
        tool_names = list(bridge._tool_metadata.keys())
        assert "airbnb_search_listings" in tool_names
        assert "airbnb_search_accommodations" in tool_names
        assert "airbnb_search" in tool_names
        assert "airbnb_get_listing_details" in tool_names
        assert "airbnb_get_listing" in tool_names
        assert "airbnb_check_availability" in tool_names

        # Verify MCPManager was initialized
        mock_mcp_manager.initialize.assert_called_once()

    async def test_initialize_idempotent(self, bridge):
        """Test that initialize is idempotent."""
        await bridge.initialize()
        tool_count = len(bridge._tool_metadata)

        # Second initialize should not change anything
        await bridge.initialize()
        assert len(bridge._tool_metadata) == tool_count

    async def test_get_tools_returns_langgraph_tools(self, bridge):
        """Test that get_tools returns LangGraph Tool objects."""
        tools = await bridge.get_tools()

        assert len(tools) > 0
        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name.startswith("airbnb_")
            assert tool.description
            assert hasattr(tool, "func")

    async def test_tool_function_calls_mcp_manager(self, bridge, mock_mcp_manager):
        """Test that tool functions properly invoke the MCP manager."""
        mock_mcp_manager.invoke.return_value = {"results": ["listing1", "listing2"]}

        tools = await bridge.get_tools()
        search_tool = next(t for t in tools if t.name == "airbnb_search_listings")

        # Execute the tool
        result = await search_tool.func(location="Paris", adults=2)

        # Verify MCP manager was called correctly
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="search_listings",
            params={"location": "Paris", "adults": 2},
        )
        assert "listing1" in result
        assert "listing2" in result

    async def test_tool_function_handles_mcp_errors(self, bridge, mock_mcp_manager):
        """Test that tool functions handle MCP errors gracefully."""
        mock_mcp_manager.invoke.side_effect = MCPInvocationError(
            "API error", mcp_name="airbnb", method_name="search_listings"
        )

        tools = await bridge.get_tools()
        search_tool = next(t for t in tools if t.name == "airbnb_search_listings")

        # Execute the tool
        result = await search_tool.func(location="Paris")

        assert "Tool execution failed" in result
        assert "API error" in result

    async def test_tool_function_handles_unexpected_errors(
        self, bridge, mock_mcp_manager
    ):
        """Test that tool functions handle unexpected errors."""
        mock_mcp_manager.invoke.side_effect = Exception("Unexpected error")

        tools = await bridge.get_tools()
        search_tool = next(t for t in tools if t.name == "airbnb_search_listings")

        # Execute the tool
        result = await search_tool.func(location="Paris")

        assert "Unexpected error" in result

    async def test_invoke_tool_direct(self, bridge, mock_mcp_manager):
        """Test direct tool invocation."""
        mock_mcp_manager.invoke.return_value = {"id": "123", "name": "Cozy Apartment"}

        await bridge.initialize()
        result = await bridge.invoke_tool_direct(
            "airbnb_get_listing_details", {"listing_id": "123"}
        )

        assert result == {"id": "123", "name": "Cozy Apartment"}
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="get_listing_details",
            params={"listing_id": "123"},
        )

    async def test_invoke_tool_direct_unknown_tool(self, bridge):
        """Test invoking an unknown tool raises error."""
        await bridge.initialize()

        with pytest.raises(ValueError) as exc_info:
            await bridge.invoke_tool_direct("unknown_tool", {})

        assert "Tool unknown_tool not found" in str(exc_info.value)

    def test_get_tool_metadata(self, bridge):
        """Test getting tool metadata."""
        # Add test metadata
        test_wrapper = AirbnbToolWrapper(
            name="airbnb_test",
            description="Test tool",
            parameters={"param": {"type": "string"}},
            mcp_method="test_method",
        )
        bridge._tool_metadata["airbnb_test"] = test_wrapper

        metadata = bridge.get_tool_metadata("airbnb_test")
        assert metadata == test_wrapper

        # Non-existent tool
        assert bridge.get_tool_metadata("non_existent") is None

    def test_list_available_tools(self, bridge):
        """Test listing available tools."""
        # Add test metadata
        bridge._tool_metadata = {
            "airbnb_search": AirbnbToolWrapper(
                name="airbnb_search",
                description="Search",
                parameters={},
                mcp_method="search",
            ),
            "airbnb_details": AirbnbToolWrapper(
                name="airbnb_details",
                description="Details",
                parameters={},
                mcp_method="details",
            ),
        }

        tools = bridge.list_available_tools()
        assert set(tools) == {"airbnb_search", "airbnb_details"}

    async def test_refresh_tools(self, bridge, mock_mcp_manager):
        """Test refreshing tools clears cache and reinitializes."""
        await bridge.initialize()
        initial_tool_count = len(bridge._tool_metadata)

        # Add something to cache
        bridge._tool_cache["test"] = Mock()

        await bridge.refresh_tools()

        # Cache should be cleared
        assert len(bridge._tool_cache) == 0
        # Should reinitialize with same tools
        assert len(bridge._tool_metadata) == initial_tool_count
        # Manager should be initialized twice (once in first init, once in refresh)
        assert mock_mcp_manager.initialize.call_count == 2

    async def test_create_args_schema(self, bridge):
        """Test creating Pydantic schema from parameters."""
        parameters = {
            "location": {"type": "string", "description": "Location", "required": True},
            "adults": {"type": "integer", "description": "Adults", "required": False},
            "price_max": {
                "type": "number",
                "description": "Max price",
                "required": False,
            },
            "available": {
                "type": "boolean",
                "description": "Available",
                "required": False,
            },
        }

        schema = bridge._create_args_schema(parameters)
        assert schema is not None
        assert schema.__name__ == "AirbnbToolArgsSchema"

        # Test with empty parameters
        assert bridge._create_args_schema({}) is None
        assert bridge._create_args_schema(None) is None


class TestGlobalFunctions:
    """Test global helper functions."""

    @patch("tripsage.orchestration.mcp_bridge._global_bridge", None)
    async def test_get_mcp_bridge_creates_singleton(self):
        """Test get_mcp_bridge creates and returns singleton."""
        with patch(
            "tripsage.orchestration.mcp_bridge.LangGraphMCPBridge"
        ) as mock_bridge_class:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock()
            mock_bridge_class.return_value = mock_instance

            bridge1 = await get_mcp_bridge()
            bridge2 = await get_mcp_bridge()

            assert bridge1 is bridge2
            mock_bridge_class.assert_called_once()
            mock_instance.initialize.assert_called_once()

    async def test_get_airbnb_tools(self):
        """Test get_airbnb_tools returns tools from bridge."""
        mock_tools = [Mock(spec=Tool), Mock(spec=Tool)]

        with patch(
            "tripsage.orchestration.mcp_bridge.get_mcp_bridge"
        ) as mock_get_bridge:
            mock_bridge = MagicMock()
            mock_bridge.get_tools = AsyncMock(return_value=mock_tools)
            mock_get_bridge.return_value = mock_bridge

            tools = await get_airbnb_tools()

            assert tools == mock_tools
            mock_bridge.get_tools.assert_called_once()

    def test_create_airbnb_tool_decorator(self):
        """Test create_airbnb_tool decorator."""

        @create_airbnb_tool("test_search", "Test search tool", "search_listings")
        async def test_search_tool(location: str) -> str:
            pass

        # Check the created tool has correct attributes
        assert hasattr(test_search_tool, "name")
        assert test_search_tool.name == "test_search"
        assert hasattr(test_search_tool, "description")
        assert test_search_tool.description == "Test search tool"


class TestAirbnbToolWrapper:
    """Test the AirbnbToolWrapper model."""

    def test_airbnb_tool_wrapper_creation(self):
        """Test creating an AirbnbToolWrapper."""
        wrapper = AirbnbToolWrapper(
            name="airbnb_search",
            description="Search Airbnb listings",
            parameters={
                "location": {"type": "string", "required": True},
                "adults": {"type": "integer", "required": False},
            },
            mcp_method="search_listings",
        )

        assert wrapper.name == "airbnb_search"
        assert wrapper.description == "Search Airbnb listings"
        assert wrapper.parameters["location"]["type"] == "string"
        assert wrapper.mcp_method == "search_listings"

    def test_airbnb_tool_wrapper_validation(self):
        """Test AirbnbToolWrapper validation."""
        # Should require all fields
        with pytest.raises(ValueError):
            AirbnbToolWrapper(
                name="test",
                description="test",
                # Missing parameters and mcp_method
            )
