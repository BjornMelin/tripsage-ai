"""
Comprehensive tests for the enhanced LangGraphToolRegistry.

This module tests the centralized tool management system with enhanced
async patterns, batch operations, and tool lifecycle management.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.tools.registry import (
    LangGraphToolRegistry,
    MCPToolWrapper,
    SDKToolWrapper,
    ToolMetadata,
    get_tool_registry,
)
from tripsage_core.mcp_abstraction.manager import mcp_manager


class TestLangGraphToolRegistry:
    """Test cases for the enhanced LangGraphToolRegistry."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        registry = MagicMock(spec=ServiceRegistry)
        registry.google_maps_service = AsyncMock()
        registry.webcrawl_service = AsyncMock()
        return registry

    @pytest.fixture
    def tool_registry(self, mock_service_registry):
        """Create a tool registry instance."""
        return LangGraphToolRegistry(mock_service_registry)

    @pytest.mark.asyncio
    async def test_tool_registry_initialization(self, tool_registry):
        """Test tool registry initializes with core tools."""
        assert len(tool_registry.tools) > 0
        assert "flights_search_flights" in tool_registry.tools
        assert "accommodations_search_listings" in tool_registry.tools
        assert "memory_add_memory" in tool_registry.tools

    def test_agent_tool_mappings(self, tool_registry):
        """Test agent-specific tool mappings are created correctly."""
        flight_tools = tool_registry.get_tools_for_agent("flight_agent")
        assert len(flight_tools) > 0
        
        # Verify flight agent gets flight-related tools
        flight_tool_names = [tool.metadata.name for tool in flight_tools]
        assert any("flight" in name for name in flight_tool_names)

    def test_capability_based_tool_filtering(self, tool_registry):
        """Test tools can be filtered by capabilities."""
        flight_tools = tool_registry.get_tools_for_agent(
            "flight_agent", capabilities=["flight_search"]
        )
        geocoding_tools = tool_registry.get_tools_for_agent(
            "destination_research_agent", capabilities=["geocoding"]
        )
        
        assert len(flight_tools) > 0
        assert len(geocoding_tools) > 0

    @pytest.mark.asyncio
    async def test_batch_tool_execution(self, tool_registry):
        """Test concurrent batch tool execution."""
        # Mock tool execution
        mock_tool = AsyncMock()
        mock_tool.execute.return_value = {"status": "success", "data": "test"}
        tool_registry.tools["test_tool"] = mock_tool
        
        tool_executions = [
            {"tool_name": "test_tool", "params": {"param1": "value1"}},
            {"tool_name": "test_tool", "params": {"param2": "value2"}},
        ]
        
        results = await tool_registry.batch_execute_tools(tool_executions)
        
        assert len(results) == 2
        assert all(result["status"] == "success" for result in results)
        assert mock_tool.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_execution_with_failures(self, tool_registry):
        """Test batch execution handles failures gracefully."""
        # Mock tool that fails
        mock_tool = AsyncMock()
        mock_tool.execute.side_effect = Exception("Tool failed")
        tool_registry.tools["failing_tool"] = mock_tool
        
        tool_executions = [
            {"tool_name": "failing_tool", "params": {}},
            {"tool_name": "nonexistent_tool", "params": {}},
        ]
        
        results = await tool_registry.batch_execute_tools(tool_executions)
        
        assert len(results) == 2
        assert all(result["status"] == "error" for result in results)

    @pytest.mark.asyncio
    async def test_concurrency_limiting(self, tool_registry):
        """Test batch execution respects concurrency limits."""
        # Mock slow tool with actual async delay
        async def slow_execute(**kwargs):
            await asyncio.sleep(0.1)
            return {"result": "slow"}
        
        mock_tool = AsyncMock()
        mock_tool.execute = slow_execute
        tool_registry.tools["slow_tool"] = mock_tool
        
        tool_executions = [
            {"tool_name": "slow_tool", "params": {}} for _ in range(9)  # Use 9 to ensure 3 batches
        ]
        
        # Test with max_concurrent=3 (should take ~0.3s for 3 batches)
        start_time = asyncio.get_event_loop().time()
        await tool_registry.batch_execute_tools(tool_executions, max_concurrent=3)
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 0.25s (allowing some margin for execution overhead)
        execution_time = end_time - start_time
        assert execution_time >= 0.25

    def test_tool_usage_statistics(self, tool_registry):
        """Test tool usage statistics tracking."""
        # Simulate tool usage
        for tool in tool_registry.tools.values():
            tool.metadata.usage_count = 5
            tool.metadata.error_count = 1
        
        stats = tool_registry.get_usage_statistics()
        
        assert stats["total_tools"] == len(tool_registry.tools)
        assert "by_type" in stats
        assert "by_agent" in stats
        assert "top_used" in stats
        assert "error_rates" in stats

    @pytest.mark.asyncio
    async def test_health_check(self, tool_registry):
        """Test tool health checking."""
        with patch.object(mcp_manager, 'check_service_health', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            
            health_status = await tool_registry.health_check()
            
            assert "healthy" in health_status
            assert "unhealthy" in health_status
            assert "total_tools" in health_status
            assert health_status["total_tools"] == len(tool_registry.tools)


class TestMCPToolWrapper:
    """Test cases for MCPToolWrapper async improvements."""

    @pytest.fixture
    def mcp_tool(self):
        """Create an MCP tool wrapper."""
        return MCPToolWrapper(
            service_name="test_service",
            method_name="test_method",
            description="Test tool",
            parameters={"param1": {"type": "string", "required": True}},
        )

    @pytest.mark.asyncio
    async def test_async_execution(self, mcp_tool):
        """Test async tool execution."""
        with patch.object(mcp_tool.mcp_manager, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"result": "test"}
            
            result = await mcp_tool.execute(param1="value1")
            
            assert result == {"result": "test"}
            mock_invoke.assert_called_once_with(
                method_name="test_method", params={"param1": "value1"}
            )

    def test_sync_execution_in_async_context_raises_error(self, mcp_tool):
        """Test sync execution detects async context and raises error."""
        async def test_sync_in_async():
            # This should raise an error because we're in an async context
            with pytest.raises(Exception) as exc_info:
                mcp_tool._run(param1="value1")
            
            assert "async context" in str(exc_info.value)
        
        # Run the test in an async context
        asyncio.run(test_sync_in_async())

    @pytest.mark.asyncio
    async def test_usage_statistics_tracking(self, mcp_tool):
        """Test that usage statistics are tracked correctly."""
        initial_usage = mcp_tool.metadata.usage_count
        initial_errors = mcp_tool.metadata.error_count
        
        with patch.object(mcp_tool.mcp_manager, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"result": "test"}
            
            await mcp_tool.execute(param1="value1")
            
            assert mcp_tool.metadata.usage_count == initial_usage + 1
            assert mcp_tool.metadata.error_count == initial_errors
            assert mcp_tool.metadata.last_used is not None

    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, mcp_tool):
        """Test that error statistics are tracked correctly."""
        initial_usage = mcp_tool.metadata.usage_count
        initial_errors = mcp_tool.metadata.error_count
        
        with patch.object(mcp_tool.mcp_manager, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = Exception("Test error")
            
            with pytest.raises(Exception):
                await mcp_tool.execute(param1="value1")
            
            assert mcp_tool.metadata.usage_count == initial_usage + 1
            assert mcp_tool.metadata.error_count == initial_errors + 1


class TestSDKToolWrapper:
    """Test cases for SDKToolWrapper enhancements."""

    @pytest.fixture
    def async_sdk_tool(self):
        """Create an SDK tool wrapper with async function."""
        async def async_func(param1: str) -> dict:
            return {"result": param1}
        
        return SDKToolWrapper(
            name="async_test_tool",
            description="Async test tool",
            func=async_func,
            parameters={"param1": {"type": "string", "required": True}},
        )

    @pytest.fixture
    def sync_sdk_tool(self):
        """Create an SDK tool wrapper with sync function."""
        def sync_func(param1: str) -> dict:
            return {"result": param1}
        
        return SDKToolWrapper(
            name="sync_test_tool",
            description="Sync test tool",
            func=sync_func,
            parameters={"param1": {"type": "string", "required": True}},
        )

    @pytest.mark.asyncio
    async def test_async_sdk_tool_execution(self, async_sdk_tool):
        """Test async SDK tool execution."""
        result = await async_sdk_tool.execute(param1="test_value")
        assert result == {"result": "test_value"}

    @pytest.mark.asyncio
    async def test_sync_sdk_tool_execution(self, sync_sdk_tool):
        """Test sync SDK tool execution."""
        result = await sync_sdk_tool.execute(param1="test_value")
        assert result == {"result": "test_value"}

    def test_langchain_tool_creation(self, async_sdk_tool, sync_sdk_tool):
        """Test LangChain tool creation for both async and sync functions."""
        async_lc_tool = async_sdk_tool.get_langchain_tool()
        sync_lc_tool = sync_sdk_tool.get_langchain_tool()
        
        assert async_lc_tool.name == "async_test_tool"
        assert sync_lc_tool.name == "sync_test_tool"


class TestToolRegistryIntegration:
    """Integration tests for the enhanced tool registry system."""

    @pytest.mark.asyncio
    async def test_global_registry_singleton(self):
        """Test global registry singleton behavior."""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is registry2
        assert len(registry1.tools) > 0

    @pytest.mark.asyncio
    async def test_service_registry_integration(self):
        """Test tool registry integration with service registry."""
        mock_service_registry = MagicMock(spec=ServiceRegistry)
        mock_service_registry.google_maps_service = AsyncMock()
        
        registry = LangGraphToolRegistry(mock_service_registry)
        
        # Test that SDK tools are created with service registry
        google_maps_tool = registry.get_tool("google_maps_geocode")
        assert google_maps_tool is not None

    def test_tool_metadata_validation(self):
        """Test tool metadata validation and structure."""
        registry = LangGraphToolRegistry()
        
        for tool_name, tool in registry.tools.items():
            assert isinstance(tool.metadata, ToolMetadata)
            assert tool.metadata.name == tool_name
            assert tool.metadata.description
            assert tool.metadata.tool_type in ["MCP", "SDK"]
            assert isinstance(tool.metadata.agent_types, list)
            assert isinstance(tool.metadata.capabilities, list)

    @pytest.mark.asyncio
    async def test_end_to_end_tool_execution(self):
        """Test end-to-end tool execution flow."""
        registry = LangGraphToolRegistry()
        
        # Test MCP tool execution (mocked)
        with patch.object(mcp_manager, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = {"flights": [{"id": "test"}]}
            
            flight_tool = registry.get_tool("flights_search_flights")
            if flight_tool:
                result = await flight_tool.execute(
                    origin="NYC", destination="LAX", departure_date="2024-03-15"
                )
                assert "flights" in result

    def test_agent_tool_isolation(self):
        """Test that agents only get their designated tools."""
        registry = LangGraphToolRegistry()
        
        flight_tools = registry.get_tools_for_agent("flight_agent")
        accommodation_tools = registry.get_tools_for_agent("accommodation_agent")
        
        flight_tool_names = {tool.metadata.name for tool in flight_tools}
        accommodation_tool_names = {tool.metadata.name for tool in accommodation_tools}
        
        # Flight agent should have flight-specific tools
        assert any("flight" in name for name in flight_tool_names)
        # Accommodation agent should have accommodation-specific tools
        assert any("accommodation" in name for name in accommodation_tool_names)