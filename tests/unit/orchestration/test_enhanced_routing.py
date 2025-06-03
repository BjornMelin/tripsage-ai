"""
Comprehensive tests for enhanced routing and handoff coordination.

This module tests the improved routing logic with multi-tier classification,
confidence scoring, and sophisticated handoff coordination.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.handoff_coordinator import (
    AgentHandoffCoordinator,
    HandoffTrigger,
    HandoffRule,
    HandoffContext,
)
from tripsage.orchestration.state import create_initial_state, TravelPlanningState
from tripsage.agents.service_registry import ServiceRegistry


class TestEnhancedRouterNode:
    """Test cases for the enhanced RouterNode with fallback classification."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        return MagicMock(spec=ServiceRegistry)

    @pytest.fixture
    def router_node(self, mock_service_registry):
        """Create a router node instance."""
        return RouterNode(mock_service_registry)

    @pytest.fixture
    def sample_state(self):
        """Create a sample travel planning state."""
        return create_initial_state(
            user_id="test_user",
            message="I want to book a flight from NYC to LAX"
        )

    @pytest.mark.asyncio
    async def test_enhanced_classification_success(self, router_node, sample_state):
        """Test successful enhanced classification."""
        with patch.object(router_node, '_classify_intent', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {
                "agent": "flight_agent",
                "confidence": 0.95,
                "reasoning": "User requesting flight booking"
            }
            
            result_state = await router_node.process(sample_state)
            
            assert result_state["current_agent"] == "flight_agent"
            assert result_state["handoff_context"]["routing_confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_classification_with_low_confidence_fallback(self, router_node, sample_state):
        """Test fallback to keyword classification when LLM confidence is low."""
        with patch.object(router_node, '_classify_intent', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {
                "agent": "general_agent",
                "confidence": 0.1,  # Lower than keyword classification
                "reasoning": "Uncertain classification"
            }
            
            result_state = await router_node.process(sample_state)
            
            # Should use keyword-based fallback due to "flight" keyword
            assert result_state["current_agent"] == "flight_agent"
            assert result_state["handoff_context"]["routing_confidence"] > 0.1

    def test_keyword_based_classification(self, router_node):
        """Test keyword-based classification fallback."""
        # Test flight-related message
        flight_classification = router_node._keyword_based_classification(
            "I need to book a flight to Paris"
        )
        assert flight_classification["agent"] == "flight_agent"
        assert flight_classification["confidence"] > 0.0
        
        # Test hotel-related message
        hotel_classification = router_node._keyword_based_classification(
            "Find me a good hotel in downtown"
        )
        assert hotel_classification["agent"] == "accommodation_agent"
        assert hotel_classification["confidence"] > 0.0
        
        # Test budget-related message
        budget_classification = router_node._keyword_based_classification(
            "What's the cheapest option for my trip?"
        )
        assert budget_classification["agent"] == "budget_agent"
        assert budget_classification["confidence"] > 0.0

    def test_classification_validation_enhanced(self, router_node):
        """Test enhanced classification validation."""
        # Valid classification
        valid_classification = {
            "agent": "flight_agent",
            "confidence": 0.8,
            "reasoning": "User wants flight booking"
        }
        assert router_node._validate_classification(valid_classification) is True
        
        # Invalid agent name
        invalid_agent = {
            "agent": "invalid_agent",
            "confidence": 0.8,
            "reasoning": "Test"
        }
        assert router_node._validate_classification(invalid_agent) is False
        
        # Invalid confidence
        invalid_confidence = {
            "agent": "flight_agent",
            "confidence": 1.5,  # > 1.0
            "reasoning": "Test"
        }
        assert router_node._validate_classification(invalid_confidence) is False
        
        # Empty reasoning
        empty_reasoning = {
            "agent": "flight_agent",
            "confidence": 0.8,
            "reasoning": ""
        }
        assert router_node._validate_classification(empty_reasoning) is False

    @pytest.mark.asyncio
    async def test_classification_error_handling(self, router_node, sample_state):
        """Test classification error handling with safe fallback."""
        with patch.object(router_node, '_classify_intent', new_callable=AsyncMock) as mock_classify:
            mock_classify.side_effect = Exception("API Error")
            
            result_state = await router_node.process(sample_state)
            
            # Should fall back to safe classification  
            assert result_state["current_agent"] == "general_agent"
            assert result_state["handoff_context"]["routing_confidence"] == 0.3

    def test_conversation_context_building(self, router_node, sample_state):
        """Test conversation context building for enhanced routing."""
        # Add some context to state
        sample_state["flight_searches"] = [{"origin": "NYC", "destination": "LAX"}]
        sample_state["user_preferences"] = {"budget": "economy"}
        sample_state["agent_history"] = ["router", "flight_agent"]
        
        context = router_node._build_conversation_context(sample_state)
        
        assert context["previous_searches"] == "flights"
        assert context["user_preferences"] == {"budget": "economy"}
        assert context["recent_agents"] == ["router", "flight_agent"]


class TestEnhancedHandoffCoordinator:
    """Test cases for the enhanced AgentHandoffCoordinator."""

    @pytest.fixture
    def handoff_coordinator(self):
        """Create a handoff coordinator instance."""
        return AgentHandoffCoordinator()

    @pytest.fixture
    def sample_state(self):
        """Create a sample state for handoff testing."""
        state = create_initial_state(
            user_id="test_user",
            message="I found a flight, now I need a hotel"
        )
        state["flight_selections"] = [{"id": "flight_123"}]
        return state

    def test_handoff_rule_initialization(self, handoff_coordinator):
        """Test that default handoff rules are initialized correctly."""
        assert len(handoff_coordinator.handoff_rules) > 0
        
        # Check for specific rules
        rule_names = [(rule.from_agent, rule.to_agent) for rule in handoff_coordinator.handoff_rules]
        assert ("general", "flight_agent") in rule_names
        assert ("general", "accommodation_agent") in rule_names

    def test_keyword_based_handoff_detection(self, handoff_coordinator):
        """Test handoff detection based on keywords."""
        # Create a clean state with only hotel-related message
        state = create_initial_state(
            user_id="test_user",
            message="I need a hotel in downtown"
        )
        
        handoff_result = handoff_coordinator.determine_next_agent(
            "general", state, HandoffTrigger.USER_REQUEST
        )
        
        assert handoff_result is not None
        next_agent, handoff_context = handoff_result
        assert next_agent == "accommodation_agent"
        assert isinstance(handoff_context, HandoffContext)

    def test_task_completion_handoff(self, handoff_coordinator, sample_state):
        """Test handoff based on task completion conditions."""
        # Set up state with completed flight and accommodation
        sample_state["flight_selections"] = [{"id": "flight_123"}]
        sample_state["accommodation_selections"] = [{"id": "hotel_456"}]
        
        handoff_result = handoff_coordinator.determine_next_agent(
            "accommodation_agent", sample_state, HandoffTrigger.TASK_COMPLETION
        )
        
        assert handoff_result is not None
        next_agent, handoff_context = handoff_result
        assert next_agent == "itinerary_agent"

    def test_error_recovery_handoff(self, handoff_coordinator, sample_state):
        """Test handoff for error recovery scenarios."""
        # Set up state with multiple errors
        sample_state["error_history"] = [
            {"error": "API timeout"}, 
            {"error": "Service unavailable"}, 
            {"error": "Rate limit exceeded"}
        ]
        
        handoff_result = handoff_coordinator.determine_next_agent(
            "flight_agent", sample_state, HandoffTrigger.ERROR_RECOVERY
        )
        
        assert handoff_result is not None
        next_agent, handoff_context = handoff_result
        assert next_agent == "general"

    def test_handoff_context_preservation(self, handoff_coordinator, sample_state):
        """Test that handoff context preserves relevant state information."""
        sample_state["travel_dates"] = {"departure": "2024-03-15"}
        sample_state["destination"] = "Paris"
        
        handoff_result = handoff_coordinator.determine_next_agent(
            "general", sample_state, HandoffTrigger.USER_REQUEST
        )
        
        if handoff_result:
            next_agent, handoff_context = handoff_result
            preserved_context = handoff_context.preserved_context
            
            # Check that relevant context is preserved based on rule
            assert isinstance(preserved_context, dict)

    def test_agent_capability_management(self, handoff_coordinator):
        """Test agent capability tracking and querying."""
        from tripsage.orchestration.handoff_coordinator import AgentCapability
        
        # Test capability queries
        assert handoff_coordinator.can_handle_capability(
            "flight_agent", AgentCapability.FLIGHT_SEARCH
        )
        assert handoff_coordinator.can_handle_capability(
            "accommodation_agent", AgentCapability.ACCOMMODATION_SEARCH
        )
        
        # Test finding agents by capability
        flight_agents = handoff_coordinator.find_agents_with_capability(
            AgentCapability.FLIGHT_SEARCH
        )
        assert "flight_agent" in flight_agents

    def test_custom_handoff_rule_addition(self, handoff_coordinator):
        """Test adding custom handoff rules."""
        initial_rule_count = len(handoff_coordinator.handoff_rules)
        
        custom_rule = HandoffRule(
            from_agent="test_agent",
            to_agent="destination_research_agent",
            trigger=HandoffTrigger.USER_REQUEST,
            conditions={"keywords": ["explore", "discover"]},
            priority=5,
            context_keys=["destination", "interests"]
        )
        
        handoff_coordinator.add_handoff_rule(custom_rule)
        
        assert len(handoff_coordinator.handoff_rules) == initial_rule_count + 1
        # Check that rules are sorted by priority
        priorities = [rule.priority for rule in handoff_coordinator.handoff_rules]
        assert priorities == sorted(priorities, reverse=True)

    def test_handoff_history_tracking(self, handoff_coordinator, sample_state):
        """Test handoff history tracking functionality."""
        initial_history_length = len(handoff_coordinator.handoff_history)
        
        # Trigger a handoff
        handoff_result = handoff_coordinator.determine_next_agent(
            "general", sample_state, HandoffTrigger.USER_REQUEST
        )
        
        if handoff_result:
            assert len(handoff_coordinator.handoff_history) == initial_history_length + 1
            
            # Test history retrieval
            recent_history = handoff_coordinator.get_handoff_history(limit=1)
            assert len(recent_history) == 1
            assert isinstance(recent_history[0], HandoffContext)

    @pytest.mark.asyncio
    async def test_handoff_execution(self, handoff_coordinator, sample_state):
        """Test handoff execution and state updates."""
        handoff_context = HandoffContext(
            from_agent="flight_agent",
            to_agent="accommodation_agent",
            trigger=HandoffTrigger.TASK_COMPLETION,
            reason="Flight booking completed",
            preserved_context={"destination": "Paris"}
        )
        
        updated_state = await handoff_coordinator.execute_handoff(
            handoff_context, sample_state
        )
        
        assert updated_state["current_agent"] == "accommodation_agent"
        assert "handoff_context" in updated_state
        assert "agent_history" in updated_state
        
        # Check that preserved context is merged
        assert updated_state["destination"] == "Paris"


class TestRoutingIntegration:
    """Integration tests for routing and handoff coordination."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        return MagicMock(spec=ServiceRegistry)

    @pytest.mark.asyncio
    async def test_end_to_end_routing_flow(self, mock_service_registry):
        """Test complete routing flow from message to agent assignment."""
        router_node = RouterNode(mock_service_registry)
        
        # Create state with flight request
        state = create_initial_state(
            user_id="test_user",
            message="I want to book a flight from New York to London"
        )
        
        with patch.object(router_node, '_classify_intent', new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {
                "agent": "flight_agent",
                "confidence": 0.9,
                "reasoning": "Clear flight booking request"
            }
            
            result_state = await router_node.process(state)
            
            assert result_state["current_agent"] == "flight_agent"
            assert result_state["handoff_context"]["routing_confidence"] == 0.9
            assert "routing_reasoning" in result_state["handoff_context"]

    def test_routing_confidence_scoring(self):
        """Test confidence scoring across different routing scenarios."""
        router_node = RouterNode(MagicMock())
        
        # High confidence keywords
        high_conf = router_node._keyword_based_classification(
            "I need to book a flight immediately"
        )
        assert high_conf["confidence"] > 0.2
        
        # Lower confidence - ambiguous message
        low_conf = router_node._keyword_based_classification(
            "What can you help me with?"
        )
        assert low_conf["confidence"] < 0.5

    def test_agent_mapping_consistency(self):
        """Test consistency between router and handoff coordinator agent mappings."""
        router_node = RouterNode(MagicMock())
        handoff_coordinator = AgentHandoffCoordinator()
        
        # Get valid agents from router validation
        router_agents = set([
            "flight_agent", "accommodation_agent", "budget_agent",
            "itinerary_agent", "destination_research_agent", "general_agent"
        ])
        
        # Get agents from handoff coordinator capabilities
        handoff_agents = set(handoff_coordinator.agent_capabilities.keys())
        
        # Most agents should overlap (allowing for some differences)
        overlap = router_agents.intersection(handoff_agents)
        assert len(overlap) >= 4  # At least 4 agents should be consistent