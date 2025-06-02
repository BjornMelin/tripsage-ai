"""
Tests for async MCP integration in orchestration tools.

This module tests the refactored MCP tool integration that now properly
uses async/await patterns for all I/O operations.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.tools.base import ToolException

from tripsage.orchestration.tools.mcp_integration import MCPToolWrapper, MCPToolRegistry


class TestMCPToolWrapperAsync:
    """Test async implementation of MCP tool wrapper."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager with async methods."""
        manager = MagicMock()
        manager.invoke = AsyncMock()
        return manager

    @pytest.fixture
    def tool_wrapper(self, mock_mcp_manager):
        """Create MCP tool wrapper for testing."""
        wrapper = MCPToolWrapper(
            service_name="test_service",
            method_name="test_method",
            description="Test tool",
            parameters={"test_param": {"type": "string"}}
        )
        wrapper.mcp_manager = mock_mcp_manager
        return wrapper

    @pytest.mark.asyncio
    async def test_async_tool_execution_success(self, tool_wrapper, mock_mcp_manager):
        """Test successful async tool execution."""
        # Setup
        expected_result = {"status": "success", "data": "test_data"}
        mock_mcp_manager.invoke.return_value = expected_result

        # Execute
        result = await tool_wrapper._arun(test_param="test_value")

        # Verify
        assert result == json.dumps(expected_result, ensure_ascii=False)
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="test_method",
            params={"test_param": "test_value"}
        )

    @pytest.mark.asyncio
    async def test_async_tool_execution_failure(self, tool_wrapper, mock_mcp_manager):
        """Test async tool execution with failure."""
        # Setup
        mock_mcp_manager.invoke.side_effect = Exception("MCP call failed")

        # Execute and verify exception
        with pytest.raises(ToolException) as exc_info:
            await tool_wrapper._arun(test_param="test_value")

        assert "Error executing test_service_test_method" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_tool_execution_with_complex_params(self, tool_wrapper, mock_mcp_manager):
        """Test async tool execution with complex parameters."""
        # Setup
        complex_params = {
            "location": "Paris, France",
            "dates": {"start": "2024-06-01", "end": "2024-06-05"},
            "guests": 2,
            "preferences": ["wifi", "parking"]
        }
        expected_result = {"booking_id": "123", "status": "confirmed"}
        mock_mcp_manager.invoke.return_value = expected_result

        # Execute
        result = await tool_wrapper._arun(**complex_params)

        # Verify
        assert result == json.dumps(expected_result, ensure_ascii=False)
        mock_mcp_manager.invoke.assert_called_once_with(
            method_name="test_method",
            params=complex_params
        )

    def test_sync_tool_execution_with_async_manager(self, tool_wrapper, mock_mcp_manager):
        """Test sync tool execution that should use async manager internally."""
        # Setup
        expected_result = {"status": "success", "data": "test_data"}
        mock_mcp_manager.invoke.return_value = expected_result

        # Execute - this should work in sync context by running async internally
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = expected_result
            result = tool_wrapper._run(test_param="test_value")

        # Verify
        assert result == json.dumps(expected_result, ensure_ascii=False)
        mock_asyncio_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_mcp_manager):
        """Test concurrent execution of multiple tools."""
        # Setup multiple tools
        tool1 = MCPToolWrapper("service1", "method1", "Tool 1")
        tool1.mcp_manager = mock_mcp_manager
        
        tool2 = MCPToolWrapper("service2", "method2", "Tool 2")
        tool2.mcp_manager = mock_mcp_manager

        # Setup different return values
        mock_mcp_manager.invoke.side_effect = [
            {"result": "tool1_result"},
            {"result": "tool2_result"}
        ]

        # Execute concurrently
        results = await asyncio.gather(
            tool1._arun(param1="value1"),
            tool2._arun(param2="value2")
        )

        # Verify
        assert len(results) == 2
        assert json.loads(results[0])["result"] == "tool1_result"
        assert json.loads(results[1])["result"] == "tool2_result"
        assert mock_mcp_manager.invoke.call_count == 2


class TestMCPToolRegistryAsync:
    """Test MCP tool registry with async operations."""

    @pytest.fixture
    def registry(self):
        """Create MCP tool registry."""
        return MCPToolRegistry()

    def test_registry_initialization(self, registry):
        """Test registry initializes with expected tools."""
        assert len(registry.tools) > 0
        assert "search_flights" in registry.tools
        assert "search_accommodations" in registry.tools
        assert "get_weather" in registry.tools

    def test_get_tool_by_name(self, registry):
        """Test retrieving specific tool by name."""
        flight_tool = registry.get_tool("search_flights")
        assert flight_tool is not None
        assert flight_tool.name == "search_flights"
        assert "search for flights" in flight_tool.description.lower()

    def test_get_nonexistent_tool(self, registry):
        """Test retrieving non-existent tool returns None."""
        tool = registry.get_tool("nonexistent_tool")
        assert tool is None

    def test_get_tools_for_agent(self, registry):
        """Test getting tools filtered by agent type."""
        flight_tools = registry.get_tools_for_agent("flight_agent")
        tool_names = [tool.name for tool in flight_tools]
        
        assert "search_flights" in tool_names
        assert "geocode_location" in tool_names
        assert "get_weather" in tool_names

    def test_get_tools_for_unknown_agent(self, registry):
        """Test getting tools for unknown agent returns empty list."""
        tools = registry.get_tools_for_agent("unknown_agent")
        assert tools == []

    def test_register_custom_tool(self, registry):
        """Test registering a custom tool."""
        custom_tool = MCPToolWrapper(
            "custom_service", 
            "custom_method", 
            "Custom test tool"
        )
        
        registry.register_custom_tool(custom_tool)
        
        assert "custom_service_custom_method" in registry.tools
        retrieved_tool = registry.get_tool("custom_service_custom_method")
        assert retrieved_tool == custom_tool

    def test_list_available_tools(self, registry):
        """Test listing all available tools with descriptions."""
        tools_list = registry.list_available_tools()
        
        assert isinstance(tools_list, dict)
        assert len(tools_list) > 0
        assert "search_flights" in tools_list
        assert isinstance(tools_list["search_flights"], str)

    @pytest.mark.asyncio
    async def test_agent_tool_async_execution(self, registry):
        """Test that agent tools can execute asynchronously."""
        flight_tool = registry.get_tool("search_flights")
        assert flight_tool is not None
        
        # Mock the MCP manager
        with patch.object(flight_tool, 'mcp_manager') as mock_manager:
            mock_manager.invoke = AsyncMock(return_value={"flights": []})
            
            result = await flight_tool._arun(
                origin="NYC",
                destination="LAX",
                departure_date="2024-06-01"
            )
            
            assert result is not None
            mock_manager.invoke.assert_called_once()


class TestMCPIntegrationErrorHandling:
    """Test error handling in MCP integration."""

    @pytest.mark.asyncio
    async def test_mcp_timeout_handling(self):
        """Test handling of MCP operation timeouts."""
        tool = MCPToolWrapper("slow_service", "slow_method", "Slow tool")
        
        # Mock a timeout scenario
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(1)  # Simulate slow operation
            return {"result": "success"}
        
        tool.mcp_manager.invoke = slow_invoke
        
        # This should complete normally (no timeout set in tool)
        result = await tool._arun(test_param="value")
        assert "success" in result

    @pytest.mark.asyncio
    async def test_mcp_connection_error(self):
        """Test handling of MCP connection errors."""
        tool = MCPToolWrapper("failing_service", "failing_method", "Failing tool")
        tool.mcp_manager.invoke = AsyncMock(
            side_effect=ConnectionError("MCP server unavailable")
        )
        
        with pytest.raises(ToolException) as exc_info:
            await tool._arun(test_param="value")
        
        assert "MCP server unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mcp_invalid_response(self):
        """Test handling of invalid MCP responses."""
        tool = MCPToolWrapper("invalid_service", "invalid_method", "Invalid tool")
        
        # Return non-serializable object
        class NonSerializable:
            pass
        
        tool.mcp_manager.invoke = AsyncMock(return_value=NonSerializable())
        
        with pytest.raises(ToolException):
            await tool._arun(test_param="value")


@pytest.mark.integration
class TestMCPIntegrationReal:
    """Integration tests with real-like MCP scenarios."""

    @pytest.mark.asyncio
    async def test_flight_search_integration(self):
        """Test flight search tool integration pattern."""
        registry = MCPToolRegistry()
        flight_tool = registry.get_tool("search_flights")
        
        with patch.object(flight_tool, 'mcp_manager') as mock_manager:
            mock_manager.invoke = AsyncMock(return_value={
                "flights": [
                    {
                        "id": "flight_123",
                        "airline": "Test Airlines",
                        "price": 299.99,
                        "duration": "5h 30m"
                    }
                ],
                "total_count": 1
            })
            
            result = await flight_tool._arun(
                origin="JFK",
                destination="LAX",
                departure_date="2024-06-15",
                passengers=2
            )
            
            result_data = json.loads(result)
            assert result_data["total_count"] == 1
            assert result_data["flights"][0]["airline"] == "Test Airlines"

    @pytest.mark.asyncio
    async def test_accommodation_search_integration(self):
        """Test accommodation search tool integration pattern."""
        registry = MCPToolRegistry()
        accommodation_tool = registry.get_tool("search_accommodations")
        
        with patch.object(accommodation_tool, 'mcp_manager') as mock_manager:
            mock_manager.invoke = AsyncMock(return_value={
                "accommodations": [
                    {
                        "id": "hotel_456",
                        "name": "Test Hotel",
                        "price_per_night": 150.00,
                        "rating": 4.5
                    }
                ],
                "total_count": 1
            })
            
            result = await accommodation_tool._arun(
                location="Paris",
                check_in="2024-06-01",
                check_out="2024-06-05",
                guests=2
            )
            
            result_data = json.loads(result)
            assert result_data["total_count"] == 1
            assert result_data["accommodations"][0]["name"] == "Test Hotel"