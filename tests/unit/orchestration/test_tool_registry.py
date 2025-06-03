"""
Tests for the LangGraph Tool Registry.

This module contains comprehensive tests for the centralized tool registry,
including tool registration, agent-specific tool filtering, and usage analytics.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.tools import BaseTool, ToolException

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.tools.registry import (
    LangGraphToolRegistry,
    MCPToolWrapper,
    SDKToolWrapper,
    ToolMetadata,
    get_tool_registry,
)


class TestToolMetadata:
    """Test ToolMetadata model validation and functionality."""

    def test_tool_metadata_creation(self):
        """Test creating ToolMetadata with valid data."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            tool_type="MCP",
            agent_types=["test_agent"],
            capabilities=["testing"],
            parameters={"param1": "value1"},
            dependencies=["test_service"],
        )

        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.tool_type == "MCP"
        assert metadata.agent_types == ["test_agent"]
        assert metadata.capabilities == ["testing"]
        assert metadata.parameters == {"param1": "value1"}
        assert metadata.dependencies == ["test_service"]
        assert metadata.usage_count == 0
        assert metadata.error_count == 0

    def test_tool_metadata_defaults(self):
        """Test ToolMetadata with default values."""
        metadata = ToolMetadata(
            name="test_tool", description="A test tool", tool_type="MCP"
        )

        assert metadata.agent_types == []
        assert metadata.capabilities == []
        assert metadata.parameters == {}
        assert metadata.dependencies == []
        assert metadata.usage_count == 0
        assert metadata.error_count == 0
        assert isinstance(metadata.created_at, datetime)


class TestMCPToolWrapper:
    """Test MCP tool wrapper functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_mcp_manager = Mock()

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_mcp_tool_wrapper_creation(self, mock_mcp_manager):
        """Test creating an MCP tool wrapper."""
        mock_mcp_manager.return_value = self.mock_mcp_manager

        wrapper = MCPToolWrapper(
            service_name="test_service",
            method_name="test_method",
            description="Test MCP tool",
            parameters={"param1": {"type": "string", "description": "Test parameter"}},
            agent_types=["test_agent"],
            capabilities=["testing"],
        )

        assert wrapper.metadata.name == "test_service_test_method"
        assert wrapper.metadata.description == "Test MCP tool"
        assert wrapper.metadata.tool_type == "MCP"
        assert wrapper.metadata.agent_types == ["test_agent"]
        assert wrapper.metadata.capabilities == ["testing"]
        assert wrapper.metadata.dependencies == ["test_service"]
        assert wrapper.service_name == "test_service"
        assert wrapper.method_name == "test_method"

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    @pytest.mark.asyncio
    async def test_mcp_tool_execute_success(self, mock_mcp_manager):
        """Test successful MCP tool execution."""
        mock_mcp_manager.invoke = AsyncMock(return_value={"result": "success"})

        wrapper = MCPToolWrapper(
            service_name="test_service",
            method_name="test_method",
            description="Test MCP tool",
        )
        wrapper.mcp_manager = mock_mcp_manager

        result = await wrapper.execute(param1="value1")

        assert result == {"result": "success"}
        assert wrapper.metadata.usage_count == 1
        assert wrapper.metadata.error_count == 0
        assert wrapper.metadata.last_used is not None

        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="test_method", params={"param1": "value1"}
        )

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    @pytest.mark.asyncio
    async def test_mcp_tool_execute_error(self, mock_mcp_manager):
        """Test MCP tool execution with error."""
        mock_mcp_manager.invoke = AsyncMock(side_effect=Exception("Test error"))

        wrapper = MCPToolWrapper(
            service_name="test_service",
            method_name="test_method",
            description="Test MCP tool",
        )
        wrapper.mcp_manager = mock_mcp_manager

        with pytest.raises(ToolException) as exc_info:
            await wrapper.execute(param1="value1")

        assert "Test error" in str(exc_info.value)
        assert wrapper.metadata.usage_count == 1
        assert wrapper.metadata.error_count == 1

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_mcp_tool_langchain_tool(self, mock_mcp_manager):
        """Test getting LangChain-compatible tool."""
        wrapper = MCPToolWrapper(
            service_name="test_service",
            method_name="test_method",
            description="Test MCP tool",
        )

        langchain_tool = wrapper.get_langchain_tool()

        assert isinstance(langchain_tool, BaseTool)
        assert langchain_tool.name == "test_service_test_method"
        assert langchain_tool.description == "Test MCP tool"


class TestSDKToolWrapper:
    """Test SDK tool wrapper functionality."""

    def test_sdk_tool_wrapper_creation_sync(self):
        """Test creating an SDK tool wrapper with sync function."""

        def test_func(param1: str) -> str:
            return f"Result: {param1}"

        wrapper = SDKToolWrapper(
            name="test_sdk_tool",
            description="Test SDK tool",
            func=test_func,
            parameters={"param1": {"type": "string", "description": "Test parameter"}},
            agent_types=["test_agent"],
            capabilities=["testing"],
        )

        assert wrapper.metadata.name == "test_sdk_tool"
        assert wrapper.metadata.description == "Test SDK tool"
        assert wrapper.metadata.tool_type == "SDK"
        assert wrapper.metadata.agent_types == ["test_agent"]
        assert wrapper.metadata.capabilities == ["testing"]
        assert wrapper.func == test_func

    def test_sdk_tool_wrapper_creation_async(self):
        """Test creating an SDK tool wrapper with async function."""

        async def test_async_func(param1: str) -> str:
            return f"Async result: {param1}"

        wrapper = SDKToolWrapper(
            name="test_async_sdk_tool",
            description="Test async SDK tool",
            func=test_async_func,
            agent_types=["test_agent"],
        )

        assert wrapper.metadata.name == "test_async_sdk_tool"
        assert wrapper.func == test_async_func

    @pytest.mark.asyncio
    async def test_sdk_tool_execute_sync(self):
        """Test executing a sync SDK tool."""

        def test_func(param1: str) -> str:
            return f"Result: {param1}"

        wrapper = SDKToolWrapper(
            name="test_sdk_tool", description="Test SDK tool", func=test_func
        )

        result = await wrapper.execute(param1="test_value")

        assert result == "Result: test_value"
        assert wrapper.metadata.usage_count == 1
        assert wrapper.metadata.error_count == 0

    @pytest.mark.asyncio
    async def test_sdk_tool_execute_async(self):
        """Test executing an async SDK tool."""

        async def test_async_func(param1: str) -> str:
            return f"Async result: {param1}"

        wrapper = SDKToolWrapper(
            name="test_async_sdk_tool",
            description="Test async SDK tool",
            func=test_async_func,
        )

        result = await wrapper.execute(param1="test_value")

        assert result == "Async result: test_value"
        assert wrapper.metadata.usage_count == 1
        assert wrapper.metadata.error_count == 0

    @pytest.mark.asyncio
    async def test_sdk_tool_execute_error(self):
        """Test SDK tool execution with error."""

        def error_func(param1: str) -> str:
            raise ValueError("Test error")

        wrapper = SDKToolWrapper(
            name="test_error_tool", description="Test error tool", func=error_func
        )

        with pytest.raises(ToolException) as exc_info:
            await wrapper.execute(param1="test_value")

        assert "Test error" in str(exc_info.value)
        assert wrapper.metadata.usage_count == 1
        assert wrapper.metadata.error_count == 1


class TestLangGraphToolRegistry:
    """Test the main LangGraph tool registry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service_registry = Mock(spec=ServiceRegistry)

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_registry_initialization(self, mock_mcp_manager):
        """Test registry initialization with core tools."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        assert registry.service_registry == self.mock_service_registry
        assert isinstance(registry.tools, dict)
        assert isinstance(registry.agent_tool_mappings, dict)
        assert isinstance(registry.capability_mappings, dict)

        # Check that core MCP tools are registered
        assert len(registry.tools) > 0

        # Check specific core tools
        assert "flights_search_flights" in registry.tools
        assert "accommodations_search_listings" in registry.tools
        assert "maps_geocode" in registry.tools

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_register_tool(self, mock_mcp_manager):
        """Test registering a custom tool."""
        registry = LangGraphToolRegistry(self.mock_service_registry)
        initial_count = len(registry.tools)

        # Create a custom tool
        custom_tool = MCPToolWrapper(
            service_name="custom",
            method_name="test",
            description="Custom test tool",
            agent_types=["custom_agent"],
            capabilities=["custom_capability"],
        )

        registry.register_tool(custom_tool)

        assert len(registry.tools) == initial_count + 1
        assert "custom_test" in registry.tools
        assert "custom_agent" in registry.agent_tool_mappings
        assert "custom_test" in registry.agent_tool_mappings["custom_agent"]
        assert "custom_capability" in registry.capability_mappings
        assert "custom_test" in registry.capability_mappings["custom_capability"]

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_get_tools_for_agent(self, mock_mcp_manager):
        """Test getting tools for specific agent types."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        flight_tools = registry.get_tools_for_agent("flight_agent")
        accommodation_tools = registry.get_tools_for_agent("accommodation_agent")

        assert len(flight_tools) > 0
        assert len(accommodation_tools) > 0

        # Check that flight tools include flight-specific capabilities
        flight_tool_names = [tool.metadata.name for tool in flight_tools]
        assert "flights_search_flights" in flight_tool_names

        # Check that accommodation tools include accommodation-specific capabilities
        accommodation_tool_names = [tool.metadata.name for tool in accommodation_tools]
        assert "accommodations_search_listings" in accommodation_tool_names

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_get_tools_with_capability_filter(self, mock_mcp_manager):
        """Test getting tools with capability filtering."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        flight_tools = registry.get_tools_for_agent(
            "flight_agent", capabilities=["flight_search"]
        )

        assert len(flight_tools) > 0

        # All returned tools should have flight_search capability
        for tool in flight_tools:
            assert "flight_search" in tool.metadata.capabilities

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_get_tools_with_exclusion(self, mock_mcp_manager):
        """Test getting tools with exclusion filter."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        all_flight_tools = registry.get_tools_for_agent("flight_agent")
        excluded_tools = registry.get_tools_for_agent(
            "flight_agent", exclude_tools=["flights_search_flights"]
        )

        assert len(excluded_tools) < len(all_flight_tools)

        excluded_tool_names = [tool.metadata.name for tool in excluded_tools]
        assert "flights_search_flights" not in excluded_tool_names

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_get_langchain_tools_for_agent(self, mock_mcp_manager):
        """Test getting LangChain-compatible tools for an agent."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        langchain_tools = registry.get_langchain_tools_for_agent("flight_agent")

        assert len(langchain_tools) > 0
        assert all(isinstance(tool, BaseTool) for tool in langchain_tools)

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_get_tools_by_capability(self, mock_mcp_manager):
        """Test getting tools by specific capability."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        memory_tools = registry.get_tools_by_capability("memory")
        flight_tools = registry.get_tools_by_capability("flight_search")

        assert len(memory_tools) > 0
        assert len(flight_tools) > 0

        # Check that all memory tools have memory capability
        for tool in memory_tools:
            assert "memory" in tool.metadata.capabilities

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_get_usage_statistics(self, mock_mcp_manager):
        """Test getting usage statistics."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        # Simulate some tool usage
        tool = registry.get_tool("flights_search_flights")
        if tool:
            tool.metadata.usage_count = 5
            tool.metadata.error_count = 1
            tool.metadata.last_used = datetime.now()

        stats = registry.get_usage_statistics()

        assert "total_tools" in stats
        assert "by_type" in stats
        assert "by_agent" in stats
        assert "top_used" in stats
        assert "error_rates" in stats
        assert stats["total_tools"] > 0

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_list_available_tools(self, mock_mcp_manager):
        """Test listing all available tools."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        tools_list = registry.list_available_tools()

        assert isinstance(tools_list, dict)
        assert len(tools_list) > 0

        # Check tool information structure
        for _tool_name, tool_info in tools_list.items():
            assert "description" in tool_info
            assert "type" in tool_info
            assert "agent_types" in tool_info
            assert "capabilities" in tool_info
            assert "usage_count" in tool_info
            assert "error_count" in tool_info

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    @pytest.mark.asyncio
    async def test_health_check(self, mock_mcp_manager):
        """Test health check functionality."""
        registry = LangGraphToolRegistry(self.mock_service_registry)

        # Mock the health check method
        mock_mcp_manager.check_service_health = AsyncMock(return_value=True)

        health_status = await registry.health_check()

        assert "healthy" in health_status
        assert "unhealthy" in health_status
        assert "total_tools" in health_status
        assert "timestamp" in health_status
        assert health_status["total_tools"] > 0


class TestGlobalRegistry:
    """Test global registry singleton functionality."""

    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns the same instance."""
        with patch("tripsage.orchestration.tools.registry.mcp_manager"):
            registry1 = get_tool_registry()
            registry2 = get_tool_registry()

            assert registry1 is registry2

    def test_get_tool_registry_with_service_registry(self):
        """Test get_tool_registry with service registry parameter."""
        mock_service_registry = Mock(spec=ServiceRegistry)

        with patch("tripsage.orchestration.tools.registry.mcp_manager"):
            registry = get_tool_registry(mock_service_registry)

            assert registry.service_registry == mock_service_registry


@pytest.fixture
def sample_tool_wrapper():
    """Fixture providing a sample tool wrapper for testing."""

    def sample_func(param: str) -> str:
        return f"Sample result: {param}"

    return SDKToolWrapper(
        name="sample_tool",
        description="Sample tool for testing",
        func=sample_func,
        agent_types=["test_agent"],
        capabilities=["testing"],
    )


class TestIntegration:
    """Integration tests for tool registry functionality."""

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_mcp_manager):
        """Test a full workflow from registration to execution."""
        # Mock MCP manager for the test
        mock_mcp_manager.invoke = AsyncMock(return_value={"flights": []})

        # Create registry
        service_registry = Mock(spec=ServiceRegistry)
        registry = LangGraphToolRegistry(service_registry)

        # Get tools for flight agent
        flight_tools = registry.get_tools_for_agent("flight_agent")
        assert len(flight_tools) > 0

        # Execute a flight search tool
        flight_search_tool = registry.get_tool("flights_search_flights")
        assert flight_search_tool is not None

        # Mock the mcp_manager for the tool
        flight_search_tool.mcp_manager = mock_mcp_manager

        result = await flight_search_tool.execute(
            origin="NYC", destination="LAX", departure_date="2024-06-01"
        )

        assert result == {"flights": []}
        assert flight_search_tool.metadata.usage_count == 1
        assert flight_search_tool.metadata.error_count == 0

    @patch("tripsage.orchestration.tools.registry.mcp_manager")
    def test_agent_tool_isolation(self, mock_mcp_manager):
        """Test that different agents get appropriate tools."""
        registry = LangGraphToolRegistry()

        flight_tools = registry.get_tools_for_agent("flight_agent")
        accommodation_tools = registry.get_tools_for_agent("accommodation_agent")
        budget_tools = registry.get_tools_for_agent("budget_agent")

        flight_tool_names = {tool.metadata.name for tool in flight_tools}
        accommodation_tool_names = {tool.metadata.name for tool in accommodation_tools}
        budget_tool_names = {tool.metadata.name for tool in budget_tools}

        # Flight agent should have flight search
        assert "flights_search_flights" in flight_tool_names

        # Accommodation agent should have accommodation search
        assert "accommodations_search_listings" in accommodation_tool_names

        # Budget agent should have both flight and accommodation tools
        assert "flights_search_flights" in budget_tool_names
        assert "accommodations_search_listings" in budget_tool_names

        # All should have memory tools
        memory_tool_names = {"memory_add_memory", "memory_search_memories"}
        assert memory_tool_names.issubset(flight_tool_names)
        assert memory_tool_names.issubset(accommodation_tool_names)
        assert memory_tool_names.issubset(budget_tool_names)
