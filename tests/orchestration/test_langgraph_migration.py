"""
Comprehensive tests for LangGraph migration implementation.

This module tests the core functionality of the LangGraph-based orchestration
system to ensure it works correctly and provides the expected performance improvements.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state
from tripsage.orchestration.tools.mcp_integration import MCPToolRegistry, MCPToolWrapper


class TestLangGraphMigration:
    """Comprehensive tests for LangGraph migration functionality."""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager for testing."""
        with patch('tripsage.orchestration.tools.mcp_integration.MCPManager') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def orchestrator(self, mock_mcp_manager):
        """Create test orchestrator instance."""
        return TripSageOrchestrator()
    
    @pytest.mark.asyncio
    async def test_state_creation(self):
        """Test creation of initial state."""
        user_id = "test_user_123"
        message = "I need a flight from NYC to LAX"
        
        state = create_initial_state(user_id, message)
        
        assert state["user_id"] == user_id
        assert state["messages"][0]["content"] == message
        assert state["messages"][0]["role"] == "user"
        assert state["session_id"].startswith("session_test_user_123")
        assert state["error_count"] == 0
        assert state["flight_searches"] == []
        assert state["agent_history"] == []
    
    @pytest.mark.asyncio
    async def test_router_node_classification(self):
        """Test router node intent classification."""
        router = RouterNode()
        
        # Mock the ChatOpenAI response
        with patch.object(router, 'classifier') as mock_classifier:
            mock_response = MagicMock()
            mock_response.content = '{"agent": "flight_agent", "confidence": 0.9, "reasoning": "User is asking about flights"}'
            mock_classifier.ainvoke = AsyncMock(return_value=mock_response)
            
            state = create_initial_state("test_user", "I need flights from New York to Los Angeles")
            
            updated_state = await router.process(state)
            
            assert updated_state["current_agent"] == "flight_agent"
            assert updated_state["handoff_context"]["routing_confidence"] == 0.9
            assert "flight" in updated_state["handoff_context"]["routing_reasoning"].lower()
    
    @pytest.mark.asyncio
    async def test_router_node_fallback(self):
        """Test router node fallback behavior on errors."""
        router = RouterNode()
        
        # Mock the ChatOpenAI to raise an exception
        with patch.object(router, 'classifier') as mock_classifier:
            mock_classifier.ainvoke = AsyncMock(side_effect=Exception("API Error"))
            
            state = create_initial_state("test_user", "I need help with travel")
            
            updated_state = await router.process(state)
            
            # Should fallback to travel_agent
            assert updated_state["current_agent"] == "travel_agent"
            assert updated_state["handoff_context"]["confidence"] == 0.3
    
    @pytest.mark.asyncio
    async def test_basic_orchestrator_flow(self, orchestrator):
        """Test basic orchestrator message processing flow."""
        user_id = "test_user"
        message = "Hello, I need help planning a trip"
        
        result = await orchestrator.process_message(user_id, message)
        
        assert "response" in result
        assert "session_id" in result
        assert result["session_id"].startswith("session_test_user")
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
    
    @pytest.mark.asyncio
    async def test_session_continuity(self, orchestrator):
        """Test session state continuity across multiple messages."""
        user_id = "test_user"
        session_id = "test_session_123"
        
        # First message
        result1 = await orchestrator.process_message(
            user_id, 
            "I want to plan a trip to Paris",
            session_id
        )
        
        # Second message in same session
        result2 = await orchestrator.process_message(
            user_id,
            "What's the weather like there?", 
            session_id
        )
        
        assert result1["session_id"] == session_id
        assert result2["session_id"] == session_id
        # Both should be successful
        assert "response" in result1
        assert "response" in result2
    
    @pytest.mark.asyncio
    async def test_error_handling_in_base_node(self):
        """Test error handling in BaseAgentNode."""
        
        class TestNode(BaseAgentNode):
            def _initialize_tools(self):
                pass
            
            async def process(self, state: TravelPlanningState) -> TravelPlanningState:
                raise ValueError("Test error")
        
        node = TestNode("test_node")
        state = create_initial_state("test_user", "test message")
        
        result = await node(state)
        
        assert result["error_count"] == 1
        assert result["last_error"] == "Test error"
        assert result["retry_attempts"]["test_node"] == 1
        assert len(result["messages"]) == 2  # Original + error message
    
    def test_mcp_tool_registry_initialization(self, mock_mcp_manager):
        """Test MCP tool registry initialization."""
        registry = MCPToolRegistry()
        
        # Should have flight tools
        assert "search_flights" in registry.tools
        assert "search_accommodations" in registry.tools
        assert "geocode_location" in registry.tools
        
        # Should have correct number of tools
        assert len(registry.tools) > 5
    
    def test_mcp_tool_agent_mapping(self, mock_mcp_manager):
        """Test MCP tool agent-specific tool mapping."""
        registry = MCPToolRegistry()
        
        flight_tools = registry.get_tools_for_agent("flight_agent")
        accommodation_tools = registry.get_tools_for_agent("accommodation_agent")
        
        # Flight agent should have flight-related tools
        flight_tool_names = [tool.name for tool in flight_tools]
        assert "search_flights" in flight_tool_names
        assert "geocode_location" in flight_tool_names
        
        # Accommodation agent should have accommodation-related tools
        accommodation_tool_names = [tool.name for tool in accommodation_tools]
        assert "search_accommodations" in accommodation_tool_names
        assert "geocode_location" in accommodation_tool_names
    
    @pytest.mark.asyncio
    async def test_mcp_tool_wrapper_execution(self, mock_mcp_manager):
        """Test MCP tool wrapper execution."""
        # Mock successful MCP response
        mock_mcp_manager.invoke.return_value = {"result": "success", "data": []}
        
        tool = MCPToolWrapper(
            "test_service", 
            "test_method", 
            "Test tool description"
        )
        
        result = await tool._arun(param1="value1", param2="value2")
        
        # Should call MCP manager with correct parameters
        mock_mcp_manager.invoke.assert_called_once_with(
            "test_service",
            "test_method", 
            {"param1": "value1", "param2": "value2"}
        )
        
        # Should return JSON string
        assert isinstance(result, str)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_routing_decision_logic(self, orchestrator):
        """Test routing decision logic in orchestrator."""
        # Test flight routing
        state = create_initial_state("test_user", "test")
        state["current_agent"] = "flight_agent"
        
        route = orchestrator._route_to_agent(state)
        assert route == "flight_agent"
        
        # Test error recovery routing
        state["current_agent"] = "unknown_agent"
        state["error_count"] = 3
        
        route = orchestrator._route_to_agent(state)
        assert route == "error_recovery"
        
        # Test default routing
        state["current_agent"] = None
        state["error_count"] = 0
        
        route = orchestrator._route_to_agent(state)
        assert route == "travel_agent"
    
    @pytest.mark.asyncio
    async def test_next_step_determination(self, orchestrator):
        """Test next step determination logic."""
        state = create_initial_state("test_user", "test")
        
        # Test error case
        state["error_count"] = 1
        next_step = orchestrator._determine_next_step(state)
        assert next_step == "error"
        
        # Test memory update case
        state["error_count"] = 0
        state["user_preferences"] = {"budget": "moderate"}
        next_step = orchestrator._determine_next_step(state)
        assert next_step == "memory"
        
        # Test end case
        state["user_preferences"] = None
        state["messages"] = [{"role": "assistant", "content": "Response"}]
        next_step = orchestrator._determine_next_step(state)
        assert next_step == "end"
    
    @pytest.mark.asyncio
    async def test_state_persistence_structure(self, orchestrator):
        """Test that state has correct structure for persistence."""
        state = create_initial_state("test_user", "test message")
        
        # Verify all required fields exist
        required_fields = [
            "messages", "user_id", "session_id", "user_preferences", 
            "budget_constraints", "travel_dates", "destination_info",
            "flight_searches", "accommodation_searches", "activity_searches",
            "booking_progress", "current_agent", "agent_history", 
            "handoff_context", "error_count", "last_error", "retry_attempts",
            "active_tool_calls", "completed_tool_calls", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in state, f"Required field '{field}' missing from state"
        
        # Verify types
        assert isinstance(state["messages"], list)
        assert isinstance(state["flight_searches"], list)
        assert isinstance(state["retry_attempts"], dict)
    
    @pytest.mark.asyncio
    async def test_performance_improvement_indicators(self, orchestrator):
        """Test indicators that performance improvements are achieved."""
        import time
        
        start_time = time.time()
        
        # Process multiple messages to test performance
        tasks = []
        for i in range(5):
            task = orchestrator.process_message(f"user_{i}", f"Message {i}")
            tasks.append(task)
        
        # All should complete relatively quickly
        results = []
        for task in tasks:
            result = await task
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 5 messages in reasonable time (< 10 seconds for stub implementation)
        assert total_time < 10, f"Performance test took too long: {total_time}s"
        
        # All messages should be processed successfully
        assert len(results) == 5
        for result in results:
            assert "response" in result
            assert "session_id" in result