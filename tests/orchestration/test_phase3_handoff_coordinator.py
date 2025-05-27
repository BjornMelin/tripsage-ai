"""
Test suite for Phase 3 Agent Handoff Coordinator implementation.

This module tests the AgentHandoffCoordinator that manages intelligent
transitions between specialized agents based on conversation context.
"""

from datetime import datetime

import pytest

from tripsage.orchestration.handoff_coordinator import (
    AgentHandoffCoordinator,
    HandoffContext,
    HandoffRule,
    HandoffTrigger,
    get_handoff_coordinator,
)
from tripsage.orchestration.state import create_initial_state


class TestAgentHandoffCoordinator:
    """Test suite for the Agent Handoff Coordinator."""

    @pytest.fixture
    def coordinator(self):
        """Create test handoff coordinator instance."""
        return AgentHandoffCoordinator()

    @pytest.fixture
    def sample_state(self):
        """Create sample travel planning state."""
        state = create_initial_state("test_user", "I want to plan a trip to Paris")
        state["current_agent"] = "destination_research_agent"
        state["destination_info"] = {
            "destination": "Paris, France",
            "research_complete": True,
        }
        return state

    def test_coordinator_initialization(self, coordinator):
        """Test coordinator initialization with default rules."""
        assert coordinator.rules is not None
        assert len(coordinator.rules) > 0

        # Verify essential handoff rules exist
        rule_patterns = [rule.from_agent for rule in coordinator.rules]
        assert "destination_research_agent" in rule_patterns
        assert "flight_agent" in rule_patterns
        assert "accommodation_agent" in rule_patterns

    def test_handoff_rule_creation(self):
        """Test creation of handoff rules."""
        rule = HandoffRule(
            from_agent="destination_research_agent",
            to_agent="flight_agent",
            trigger=HandoffTrigger.TASK_COMPLETION,
            condition=lambda state: state.get("destination_info", {}).get(
                "research_complete", False
            ),
            priority=1,
            context_fields=["destination_info"],
        )

        assert rule.from_agent == "destination_research_agent"
        assert rule.to_agent == "flight_agent"
        assert rule.trigger == HandoffTrigger.TASK_COMPLETION
        assert rule.priority == 1
        assert "destination_info" in rule.context_fields

    def test_task_completion_handoff(self, coordinator, sample_state):
        """Test handoff on task completion."""
        result = coordinator.determine_next_agent(
            "destination_research_agent", sample_state, HandoffTrigger.TASK_COMPLETION
        )

        assert result is not None
        next_agent, handoff_context = result

        # Should suggest flight agent after destination research
        assert next_agent == "flight_agent"
        assert isinstance(handoff_context, HandoffContext)
        assert handoff_context.trigger == HandoffTrigger.TASK_COMPLETION
        assert handoff_context.context["destination_info"]

    def test_user_intent_handoff(self, coordinator):
        """Test handoff based on user intent change."""
        state = create_initial_state("test_user", "Now I need to find hotels")
        state["current_agent"] = "flight_agent"
        state["messages"].append(
            {"role": "user", "content": "Now I need to find hotels"}
        )

        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        assert result is not None
        next_agent, handoff_context = result

        # Should suggest accommodation agent for hotel requests
        assert next_agent == "accommodation_agent"
        assert handoff_context.trigger == HandoffTrigger.USER_INTENT_CHANGE

    def test_expertise_requirement_handoff(self, coordinator):
        """Test handoff based on expertise requirements."""
        state = create_initial_state("test_user", "What's my total budget allocation?")
        state["current_agent"] = "flight_agent"
        state["budget_constraints"] = {"total_budget": 2000}

        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.EXPERTISE_REQUIRED
        )

        assert result is not None
        next_agent, handoff_context = result

        # Should suggest budget agent for budget-related queries
        assert next_agent == "budget_agent"
        assert handoff_context.trigger == HandoffTrigger.EXPERTISE_REQUIRED

    def test_error_recovery_handoff(self, coordinator):
        """Test handoff for error recovery."""
        state = create_initial_state("test_user", "Help with my trip")
        state["current_agent"] = "flight_agent"
        state["error_count"] = 2
        state["last_error"] = "Flight search API unavailable"

        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.ERROR_RECOVERY
        )

        assert result is not None
        next_agent, handoff_context = result

        # Should suggest general agent for error recovery
        assert next_agent == "general_agent"
        assert handoff_context.trigger == HandoffTrigger.ERROR_RECOVERY

    def test_no_handoff_needed(self, coordinator):
        """Test when no handoff is needed."""
        state = create_initial_state("test_user", "Tell me more about flights")
        state["current_agent"] = "flight_agent"

        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.TASK_COMPLETION
        )

        # No handoff should be suggested for continuing flight conversation
        assert result is None

    def test_priority_based_rule_selection(self, coordinator):
        """Test that rules are selected based on priority."""
        state = create_initial_state("test_user", "I need budget help and flight info")
        state["current_agent"] = "general_agent"
        state["budget_constraints"] = {"total_budget": 1000}
        state["travel_dates"] = {"departure": "2025-07-01"}

        # Multiple rules might match, should select highest priority
        result = coordinator.determine_next_agent(
            "general_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        assert result is not None
        next_agent, handoff_context = result

        # Should choose based on rule priority
        assert next_agent in ["budget_agent", "flight_agent"]

    def test_context_preservation_in_handoff(self, coordinator, sample_state):
        """Test that relevant context is preserved during handoff."""
        result = coordinator.determine_next_agent(
            "destination_research_agent", sample_state, HandoffTrigger.TASK_COMPLETION
        )

        assert result is not None
        next_agent, handoff_context = result

        # Context should include relevant information
        assert "destination_info" in handoff_context.context
        assert (
            handoff_context.context["destination_info"]["destination"]
            == "Paris, France"
        )
        assert handoff_context.from_agent == "destination_research_agent"
        assert handoff_context.to_agent == next_agent

    def test_condition_function_evaluation(self, coordinator):
        """Test proper evaluation of rule conditions."""
        # Create rule with specific condition
        test_rule = HandoffRule(
            from_agent="test_agent",
            to_agent="target_agent",
            trigger=HandoffTrigger.TASK_COMPLETION,
            condition=lambda state: state.get("test_flag", False) is True,
            priority=1,
            context_fields=["test_data"],
        )

        # Test with condition not met
        state1 = create_initial_state("test_user", "test")
        state1["test_flag"] = False
        assert not test_rule.condition(state1)

        # Test with condition met
        state2 = create_initial_state("test_user", "test")
        state2["test_flag"] = True
        assert test_rule.condition(state2)

    def test_handoff_context_creation(self, coordinator):
        """Test proper creation of handoff context."""
        state = create_initial_state("test_user", "Plan my itinerary")
        state["destination_info"] = {"destination": "Tokyo"}
        state["flight_searches"] = [{"origin": "NYC", "destination": "NRT"}]

        context = coordinator._create_handoff_context(
            "flight_agent",
            "itinerary_agent",
            HandoffTrigger.TASK_COMPLETION,
            state,
            ["destination_info", "flight_searches"],
        )

        assert context.from_agent == "flight_agent"
        assert context.to_agent == "itinerary_agent"
        assert context.trigger == HandoffTrigger.TASK_COMPLETION
        assert context.context["destination_info"]["destination"] == "Tokyo"
        assert len(context.context["flight_searches"]) == 1
        assert context.timestamp is not None

    def test_circular_handoff_prevention(self, coordinator):
        """Test prevention of circular handoffs."""
        state = create_initial_state("test_user", "Help with flights")
        state["current_agent"] = "flight_agent"
        state["agent_history"] = [
            {"agent": "flight_agent", "timestamp": datetime.now().isoformat()},
            {"agent": "accommodation_agent", "timestamp": datetime.now().isoformat()},
            {"agent": "flight_agent", "timestamp": datetime.now().isoformat()},
        ]

        # Should avoid circular handoffs
        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        # Should either return None or suggest a different agent path
        if result:
            next_agent, _ = result
            # Should not immediately return to previous agent in chain
            recent_agents = [entry["agent"] for entry in state["agent_history"][-2:]]
            assert next_agent not in recent_agents or len(recent_agents) < 2

    def test_complex_decision_logic(self, coordinator):
        """Test complex decision logic with multiple factors."""
        state = create_initial_state(
            "test_user", "I found flights but need help with budget"
        )
        state["current_agent"] = "flight_agent"
        state["flight_searches"] = [
            {"origin": "NYC", "destination": "LAX", "price": 600},
            {"origin": "NYC", "destination": "LAX", "price": 800},
        ]
        state["budget_constraints"] = {"total_budget": 1500, "flight_budget": 700}
        state["messages"].append(
            {"role": "user", "content": "I found flights but need help with budget"}
        )

        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        assert result is not None
        next_agent, handoff_context = result

        # Should recognize budget expertise need
        assert next_agent == "budget_agent"
        assert "flight_searches" in handoff_context.context
        assert "budget_constraints" in handoff_context.context

    def test_handoff_trigger_specificity(self, coordinator):
        """Test that different triggers produce different outcomes."""
        state = create_initial_state("test_user", "Travel planning help")
        state["current_agent"] = "general_agent"
        state["user_preferences"] = {"destination": "Paris"}

        # Test different triggers
        result_completion = coordinator.determine_next_agent(
            "general_agent", state, HandoffTrigger.TASK_COMPLETION
        )

        result_intent = coordinator.determine_next_agent(
            "general_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        # Results might differ based on trigger
        if result_completion and result_intent:
            _, context_completion = result_completion
            _, context_intent = result_intent

            assert context_completion.trigger != context_intent.trigger

    def test_state_mutation_prevention(self, coordinator, sample_state):
        """Test that handoff determination doesn't mutate state."""
        original_state = dict(sample_state)

        coordinator.determine_next_agent(
            "destination_research_agent", sample_state, HandoffTrigger.TASK_COMPLETION
        )

        # State should remain unchanged
        assert sample_state == original_state

    def test_edge_case_handling(self, coordinator):
        """Test handling of edge cases and invalid states."""
        # Test with minimal state
        minimal_state = {"user_id": "test", "messages": []}

        result = coordinator.determine_next_agent(
            "unknown_agent", minimal_state, HandoffTrigger.TASK_COMPLETION
        )

        # Should handle gracefully
        assert result is None or isinstance(result, tuple)

    def test_message_analysis_for_handoff(self, coordinator):
        """Test message content analysis for handoff decisions."""
        state = create_initial_state("test_user", "Now I want to book accommodations")
        state["current_agent"] = "flight_agent"
        state["messages"].extend(
            [
                {"role": "assistant", "content": "I found great flights for you"},
                {"role": "user", "content": "Now I want to book accommodations"},
            ]
        )

        result = coordinator.determine_next_agent(
            "flight_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        assert result is not None
        next_agent, _ = result
        assert next_agent == "accommodation_agent"

    def test_singleton_coordinator_access(self):
        """Test singleton access to handoff coordinator."""
        coordinator1 = get_handoff_coordinator()
        coordinator2 = get_handoff_coordinator()

        assert coordinator1 is coordinator2  # Should be same instance

    def test_performance_with_large_state(self, coordinator):
        """Test performance with large state objects."""
        # Create large state
        large_state = create_initial_state("test_user", "Large state test")
        large_state["flight_searches"] = [{"id": f"flight_{i}"} for i in range(100)]
        large_state["accommodation_searches"] = [
            {"id": f"hotel_{i}"} for i in range(50)
        ]
        large_state["messages"] = [
            {"role": "user", "content": f"Message {i}"} for i in range(200)
        ]

        import time

        start_time = time.time()

        result = coordinator.determine_next_agent(
            "general_agent", large_state, HandoffTrigger.TASK_COMPLETION
        )

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete quickly even with large state
        assert execution_time < 1.0  # Less than 1 second
        assert result is None or isinstance(result, tuple)

    def test_rule_ordering_and_precedence(self, coordinator):
        """Test that rules are properly ordered and precedence is maintained."""
        # Verify rules are sorted by priority
        priorities = [rule.priority for rule in coordinator.rules]
        assert priorities == sorted(priorities, reverse=True)  # Higher priority first

        # Test with conflicting rules (if any)
        state = create_initial_state("test_user", "Complex request")
        state["current_agent"] = "general_agent"

        result = coordinator.determine_next_agent(
            "general_agent", state, HandoffTrigger.USER_INTENT_CHANGE
        )

        # Should return consistent result based on rule priority
        if result:
            next_agent, _ = result
            assert isinstance(next_agent, str)
            assert len(next_agent) > 0
