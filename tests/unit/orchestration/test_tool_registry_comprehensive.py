"""
Comprehensive tests for the LangGraph tool registry implementation.

Tests the centralized tool management system that integrates MCP and SDK tools
for LangGraph-based agent orchestration.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.tools.registry import (
    LangGraphToolRegistry,
    MCPToolWrapper,
    SDKToolWrapper,
    ToolMetadata,
    get_tool_registry,
)


class TestToolMetadata:
    """Test tool metadata management."""

    def test_tool_metadata_creation(self):
        """Test creating tool metadata with all fields."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            tool_type="mcp",
            capabilities=["search", "fetch"],
            agent_types=["flight_agent", "accommodation_agent"],
            parameters={"param1": "string", "param2": "integer"},
            dependencies=["test_service"],
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.tool_type == "mcp"
        assert metadata.capabilities == ["search", "fetch"]
        assert metadata.agent_types == ["flight_agent", "accommodation_agent"]
        assert metadata.parameters == {"param1": "string", "param2": "integer"}
        assert metadata.dependencies == ["test_service"]
        assert metadata.usage_count == 0
        assert metadata.error_count == 0

    def test_tool_metadata_defaults(self):
        """Test tool metadata with minimal required fields."""
        metadata = ToolMetadata(
            name="minimal_tool", description="Minimal tool", tool_type="sdk"
        )

        assert metadata.name == "minimal_tool"
        assert metadata.capabilities == []
        assert metadata.agent_types == []
        assert metadata.parameters == {}
        assert metadata.dependencies == []
        assert metadata.usage_count == 0
        assert metadata.error_count == 0
        assert metadata.last_used is None


class TestMCPToolWrapper:
    """Test MCP tool wrapper functionality."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCP manager."""
        manager = Mock()
        manager.invoke = AsyncMock(return_value={"result": "success"})
        return manager

    @pytest.fixture
    def mcp_tool_wrapper(self, mock_mcp_manager):
        """Create an MCP tool wrapper for testing."""
        with patch(
            "tripsage.orchestration.tools.registry.mcp_manager", mock_mcp_manager
        ):
            wrapper = MCPToolWrapper(
                service_name="test_service",
                method_name="test_method",
                description="Test MCP tool",
                capabilities=["search", "fetch"],
            )
            return wrapper

    @pytest.mark.asyncio
    async def test_mcp_tool_execute_success(self, mcp_tool_wrapper, mock_mcp_manager):
        """Test successful MCP tool execution."""
        result = await mcp_tool_wrapper.execute(param1="value1", param2="value2")

        assert result == {"result": "success"}
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="test_method", params={"param1": "value1", "param2": "value2"}
        )

    @pytest.mark.asyncio
    async def test_mcp_tool_execute_error(self, mcp_tool_wrapper, mock_mcp_manager):
        """Test MCP tool execution with error handling."""
        mock_mcp_manager.invoke.side_effect = Exception("MCP error")

        with pytest.raises(Exception) as exc_info:
            await mcp_tool_wrapper.execute(param1="value1")

        assert "MCP error" in str(exc_info.value)

    def test_mcp_tool_to_langchain(self, mcp_tool_wrapper):
        """Test converting MCP tool to LangChain tool."""
        langchain_tool = mcp_tool_wrapper.get_langchain_tool()

        assert langchain_tool.name == "test_service_test_method"
        assert langchain_tool.description == "Test MCP tool"
        assert callable(langchain_tool.func)


class TestSDKToolWrapper:
    """Test SDK tool wrapper functionality."""

    def test_sdk_tool_sync_function(self):
        """Test SDK tool wrapper with synchronous function."""

        def sync_func(a: int, b: int) -> int:
            return a + b

        wrapper = SDKToolWrapper(
            name="sync_tool", description="Sync tool", func=sync_func
        )

        assert wrapper.metadata.name == "sync_tool"
        assert wrapper.metadata.tool_type == "SDK"

    def test_sdk_tool_async_function(self):
        """Test SDK tool wrapper with asynchronous function."""

        async def async_func(x: str) -> str:
            return f"processed_{x}"

        wrapper = SDKToolWrapper(
            name="async_tool", description="Async tool", func=async_func
        )

        assert wrapper.metadata.name == "async_tool"
        assert wrapper.metadata.tool_type == "SDK"

    @pytest.mark.asyncio
    async def test_sdk_tool_execute_sync(self):
        """Test executing synchronous SDK tool."""

        def add_func(a: int, b: int) -> int:
            return a + b

        wrapper = SDKToolWrapper(name="add", description="Add", func=add_func)

        result = await wrapper.execute(a=5, b=3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_sdk_tool_execute_async(self):
        """Test executing asynchronous SDK tool."""

        async def process_func(text: str) -> str:
            return f"processed_{text}"

        wrapper = SDKToolWrapper(
            name="process", description="Process", func=process_func
        )

        result = await wrapper.execute(text="hello")
        assert result == "processed_hello"

    @pytest.mark.asyncio
    async def test_sdk_tool_execute_error(self):
        """Test SDK tool execution with error handling."""

        def error_func():
            raise ValueError("Test error")

        wrapper = SDKToolWrapper(
            name="error_tool", description="Error", func=error_func
        )

        with pytest.raises(Exception) as exc_info:
            await wrapper.execute()

        assert "Test error" in str(exc_info.value)


class TestLangGraphToolRegistry:
    """Test the comprehensive tool registry."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        return Mock(spec=ServiceRegistry)

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCP manager."""
        manager = Mock()
        manager.invoke = AsyncMock(return_value={"success": True})
        manager.check_service_health = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def tool_registry(self, mock_service_registry, mock_mcp_manager):
        """Create a tool registry for testing."""
        with patch(
            "tripsage.orchestration.tools.registry.mcp_manager", mock_mcp_manager
        ):
            return LangGraphToolRegistry(mock_service_registry)

    def test_registry_initialization(self, tool_registry):
        """Test registry initializes with core tools."""
        # Check that core MCP tools are registered
        assert "flights_search_flights" in tool_registry.tools
        assert "accommodations_search_listings" in tool_registry.tools
        assert "maps_geocode" in tool_registry.tools
        assert "weather_get_current_weather" in tool_registry.tools
        assert "web_search" in tool_registry.tools
        assert "memory_add_memory" in tool_registry.tools
        assert "memory_search_memories" in tool_registry.tools

    def test_register_mcp_tool(self, tool_registry, mock_mcp_manager):
        """Test registering a new MCP tool."""
        with patch(
            "tripsage.orchestration.tools.registry.mcp_manager", mock_mcp_manager
        ):
            mcp_tool = MCPToolWrapper(
                service_name="search",
                method_name="custom_search",
                description="Custom search tool",
                capabilities=["search"],
                agent_types=["general_agent"],
            )
            tool_registry.register_tool(mcp_tool)

        assert "search_custom_search" in tool_registry.tools
        tool = tool_registry.get_tool("search_custom_search")
        assert isinstance(tool, MCPToolWrapper)
        assert tool.metadata.tool_type == "MCP"

    def test_register_sdk_tool(self, tool_registry):
        """Test registering a new SDK tool."""

        def custom_func(x: int) -> int:
            return x * 2

        sdk_tool = SDKToolWrapper(
            name="double",
            func=custom_func,
            description="Double a number",
            capabilities=["math"],
            agent_types=["general_agent"],
        )
        tool_registry.register_tool(sdk_tool)

        assert "double" in tool_registry.tools
        tool = tool_registry.get_tool("double")
        assert isinstance(tool, SDKToolWrapper)
        assert tool.metadata.tool_type == "SDK"

    def test_get_tools_for_agent(self, tool_registry):
        """Test filtering tools by agent type."""
        flight_tools = tool_registry.get_tools_for_agent("flight_agent")

        # Should include flight, geocoding, web search, and memory tools
        tool_names = [tool.metadata.name for tool in flight_tools]
        assert "flights_search_flights" in tool_names
        assert "maps_geocode" in tool_names
        assert "web_search" in tool_names
        assert "memory_add_memory" in tool_names
        assert "memory_search_memories" in tool_names

    def test_get_tools_by_capability(self, tool_registry):
        """Test filtering tools by capability."""
        flight_tools = tool_registry.get_tools_by_capability("flight_search")

        # Should only include flight-related tools
        assert len(flight_tools) >= 1
        assert any("flight" in tool.metadata.name for tool in flight_tools)

    def test_get_langchain_tools_for_agent(self, tool_registry):
        """Test getting LangChain-compatible tools for an agent."""
        langchain_tools = tool_registry.get_langchain_tools_for_agent(
            "accommodation_agent"
        )

        # Should return LangChain Tool instances
        assert len(langchain_tools) > 0
        for tool in langchain_tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert callable(tool.func)

    def test_tool_metadata_retrieval(self, tool_registry):
        """Test retrieving tool metadata."""
        metadata = tool_registry.get_tool_metadata("flights_search_flights")

        assert metadata is not None
        assert metadata.name == "flights_search_flights"
        assert metadata.tool_type == "MCP"
        assert "flight_search" in metadata.capabilities

    def test_usage_statistics(self, tool_registry):
        """Test usage statistics generation."""
        stats = tool_registry.get_usage_statistics()

        assert "total_tools" in stats
        assert "by_type" in stats
        assert "by_agent" in stats
        assert stats["total_tools"] > 0
        assert "MCP" in stats["by_type"]

    @pytest.mark.asyncio
    async def test_tool_execution_integration(self, tool_registry):
        """Test executing tools through the registry."""

        # Register a test tool
        def test_func(value: str) -> str:
            return f"processed_{value}"

        sdk_tool = SDKToolWrapper(
            name="test_processor", func=test_func, description="Test processor"
        )
        tool_registry.register_tool(sdk_tool)

        # Get and execute the tool
        tool = tool_registry.get_tool("test_processor")
        result = await tool.execute(value="test")

        assert result == "processed_test"


class TestGlobalRegistry:
    """Test global registry functionality."""

    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns singleton instance."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2

    def test_get_tool_registry_with_service_registry(self):
        """Test get_tool_registry with service registry parameter."""
        mock_service_registry = Mock(spec=ServiceRegistry)
        registry = get_tool_registry(mock_service_registry)

        assert registry.service_registry == mock_service_registry


class TestIntegration:
    """Integration tests for the tool registry system."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry with services."""
        registry = Mock(spec=ServiceRegistry)
        registry.flight_service = Mock()
        registry.accommodation_service = Mock()
        registry.memory_service = Mock()
        return registry

    def test_agent_tool_isolation(self, mock_service_registry):
        """Test that different agents get appropriate tool sets."""
        with patch("tripsage.orchestration.tools.registry.mcp_manager"):
            registry = LangGraphToolRegistry(mock_service_registry)

        # Flight agent should get flight-related tools
        flight_tools = registry.get_tools_for_agent("flight_agent")
        flight_tool_names = [tool.metadata.name for tool in flight_tools]
        assert "flights_search_flights" in flight_tool_names

        # Accommodation agent should get accommodation-related tools
        accommodation_tools = registry.get_tools_for_agent("accommodation_agent")
        accommodation_tool_names = [tool.metadata.name for tool in accommodation_tools]
        assert "accommodations_search_listings" in accommodation_tool_names

        # Both should have common tools like memory and web search
        assert "memory_add_memory" in flight_tool_names
        assert "memory_add_memory" in accommodation_tool_names
        assert "web_search" in flight_tool_names
        assert "web_search" in accommodation_tool_names

    @pytest.mark.asyncio
    async def test_end_to_end_tool_execution(self, mock_service_registry):
        """Test complete tool registration and execution flow."""
        with patch("tripsage.orchestration.tools.registry.mcp_manager") as mock_mcp:
            mock_mcp.invoke = AsyncMock(return_value={"flights": ["mock_flight"]})

            registry = LangGraphToolRegistry(mock_service_registry)

            # Get a flight search tool
            tool = registry.get_tool("flights_search_flights")
            assert tool is not None

            # Execute the tool
            result = await tool.execute(origin="NYC", destination="LAX")

            # Verify the result
            assert "flights" in result
            assert result["flights"] == ["mock_flight"]

            # Verify MCP was called correctly
            mock_mcp.invoke.assert_called_once_with(
                method_name="search_flights",
                params={"origin": "NYC", "destination": "LAX"},
            )
