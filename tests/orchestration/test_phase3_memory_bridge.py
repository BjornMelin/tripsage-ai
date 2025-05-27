"""
Test suite for Phase 3 Session Memory Bridge implementation.

This module tests the SessionMemoryBridge that integrates LangGraph state
with the existing Neo4j-based session memory utilities.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.orchestration.memory_bridge import SessionMemoryBridge, get_memory_bridge
from tripsage.orchestration.state import create_initial_state


class TestSessionMemoryBridge:
    """Test suite for the Session Memory Bridge."""

    @pytest.fixture
    def mock_session_memory(self):
        """Mock session memory utilities."""
        with patch("tripsage.utils.session_memory.SessionMemoryUtil") as mock:
            mock_instance = MagicMock()
            mock_instance.get_user_context.return_value = {
                "preferences": {"budget": "moderate", "travel_style": "leisure"},
                "history": ["Previous trip to Paris", "Likes cultural activities"],
            }
            mock_instance.update_user_context = AsyncMock()
            mock_instance.add_conversation_insight = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager for memory operations."""
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock:
            mock_instance = MagicMock()
            mock_instance.invoke = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def bridge(self, mock_session_memory, mock_mcp_manager):
        """Create test memory bridge instance."""
        return SessionMemoryBridge()

    @pytest.mark.asyncio
    async def test_bridge_initialization(self, bridge, mock_session_memory):
        """Test memory bridge initialization."""
        await bridge.initialize()

        assert bridge.session_memory is not None
        assert bridge._initialized is True

    @pytest.mark.asyncio
    async def test_state_hydration_with_user_context(self, bridge, mock_session_memory):
        """Test state hydration with user context from memory."""
        # Setup mock user context
        mock_session_memory.get_user_context.return_value = {
            "preferences": {
                "budget_range": "500-1000",
                "preferred_airlines": ["Delta", "American"],
                "accommodation_type": "hotel",
            },
            "travel_history": [
                {"destination": "Paris", "date": "2024-12-01", "rating": 5},
                {"destination": "London", "date": "2024-10-15", "rating": 4},
            ],
            "dietary_restrictions": ["vegetarian"],
            "accessibility_needs": [],
        }

        # Create initial state
        state = create_initial_state("test_user_123", "I want to plan a trip to Tokyo")

        await bridge.initialize()

        # Hydrate state
        hydrated_state = await bridge.hydrate_state(state)

        # Verify preferences were loaded
        assert hydrated_state["user_preferences"]["budget_range"] == "500-1000"
        assert "Delta" in hydrated_state["user_preferences"]["preferred_airlines"]
        assert hydrated_state["user_preferences"]["accommodation_type"] == "hotel"

        # Verify travel history was loaded
        assert len(hydrated_state["user_preferences"]["travel_history"]) == 2
        assert (
            hydrated_state["user_preferences"]["travel_history"][0]["destination"]
            == "Paris"
        )

        # Verify other preferences
        assert (
            "vegetarian" in hydrated_state["user_preferences"]["dietary_restrictions"]
        )

    @pytest.mark.asyncio
    async def test_state_hydration_with_empty_context(
        self, bridge, mock_session_memory
    ):
        """Test state hydration when user has no previous context."""
        # Mock empty user context
        mock_session_memory.get_user_context.return_value = {}

        state = create_initial_state(
            "new_user_456", "Hello, I'm new to travel planning"
        )

        await bridge.initialize()
        hydrated_state = await bridge.hydrate_state(state)

        # State should remain largely unchanged but with default preferences
        assert hydrated_state["user_id"] == "new_user_456"
        assert (
            hydrated_state["user_preferences"] == {}
        )  # Should stay empty if no context

    @pytest.mark.asyncio
    async def test_insights_extraction_from_flight_search(
        self, bridge, mock_session_memory
    ):
        """Test insight extraction from flight search activities."""
        state = create_initial_state("test_user", "Find flights from NYC to LAX")

        # Simulate state after flight search
        state["flight_searches"] = [
            {
                "origin": "NYC",
                "destination": "LAX",
                "date": "2025-07-15",
                "budget_max": 800,
                "class": "economy",
                "results": [{"airline": "Delta", "price": 650}],
            }
        ]
        state["messages"].append(
            {
                "role": "assistant",
                "content": "I found several flights for your trip to Los Angeles",
                "agent": "flight_agent",
            }
        )

        await bridge.initialize()

        # Extract insights
        insights = await bridge.extract_and_persist_insights(state)

        # Verify insights were identified
        assert "destination_preferences" in insights
        assert insights["destination_preferences"]["LAX"]["search_count"] == 1
        assert "budget_patterns" in insights
        assert insights["budget_patterns"]["flight_budget_max"] == 800

        # Verify session memory was updated
        mock_session_memory.update_user_context.assert_called()
        mock_session_memory.add_conversation_insight.assert_called()

    @pytest.mark.asyncio
    async def test_insights_extraction_from_accommodation_search(
        self, bridge, mock_session_memory
    ):
        """Test insight extraction from accommodation search activities."""
        state = create_initial_state("test_user", "Find hotels in Paris")

        # Simulate state after accommodation search
        state["accommodation_searches"] = [
            {
                "location": "Paris, France",
                "check_in": "2025-08-01",
                "check_out": "2025-08-05",
                "guests": 2,
                "budget_max": 200,
                "type": "hotel",
                "results": [{"name": "Hotel Louvre", "price": 180}],
            }
        ]

        await bridge.initialize()
        insights = await bridge.extract_and_persist_insights(state)

        # Verify accommodation insights
        assert "accommodation_preferences" in insights
        assert insights["accommodation_preferences"]["type"] == "hotel"
        assert insights["accommodation_preferences"]["budget_max"] == 200

    @pytest.mark.asyncio
    async def test_budget_constraint_extraction(self, bridge, mock_session_memory):
        """Test extraction of budget constraints from conversation."""
        state = create_initial_state(
            "test_user", "I have a budget of $2000 for this trip"
        )

        # Simulate budget information in state
        state["budget_constraints"] = {
            "total_budget": 2000,
            "currency": "USD",
            "flexibility": "strict",
        }

        await bridge.initialize()
        insights = await bridge.extract_and_persist_insights(state)

        # Verify budget insights
        assert "budget_patterns" in insights
        assert insights["budget_patterns"]["total_budget"] == 2000
        assert insights["budget_patterns"]["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_travel_dates_pattern_extraction(self, bridge, mock_session_memory):
        """Test extraction of travel date patterns."""
        state = create_initial_state("test_user", "I want to travel in July")

        # Simulate travel dates in state
        state["travel_dates"] = {
            "departure": "2025-07-15",
            "return": "2025-07-22",
            "flexibility": "moderate",
        }

        await bridge.initialize()
        insights = await bridge.extract_and_persist_insights(state)

        # Verify date insights
        assert "travel_patterns" in insights
        assert insights["travel_patterns"]["preferred_month"] == "July"
        assert insights["travel_patterns"]["typical_duration"] == 7  # 7 days

    @pytest.mark.asyncio
    async def test_error_handling_in_hydration(self, bridge, mock_session_memory):
        """Test error handling during state hydration."""
        # Mock session memory to raise exception
        mock_session_memory.get_user_context.side_effect = Exception(
            "Memory service unavailable"
        )

        state = create_initial_state("test_user", "Plan a trip")

        await bridge.initialize()

        # Should handle error gracefully and return original state
        hydrated_state = await bridge.hydrate_state(state)

        # State should be unchanged
        assert hydrated_state == state

    @pytest.mark.asyncio
    async def test_error_handling_in_insight_extraction(
        self, bridge, mock_session_memory
    ):
        """Test error handling during insight extraction."""
        # Mock session memory to raise exception
        mock_session_memory.add_conversation_insight.side_effect = Exception(
            "Memory write failed"
        )

        state = create_initial_state("test_user", "Test message")
        state["flight_searches"] = [{"origin": "NYC", "destination": "LAX"}]

        await bridge.initialize()

        # Should handle error gracefully
        insights = await bridge.extract_and_persist_insights(state)

        # Should return insights even if persistence failed
        assert isinstance(insights, dict)

    @pytest.mark.asyncio
    async def test_conversation_context_preservation(self, bridge, mock_session_memory):
        """Test preservation of conversation context across interactions."""
        state = create_initial_state("test_user", "I prefer direct flights")

        # Add conversation history
        state["messages"].extend(
            [
                {"role": "user", "content": "I prefer direct flights"},
                {
                    "role": "assistant",
                    "content": "I'll look for direct flights for you",
                },
                {
                    "role": "user",
                    "content": "Also, I don't like early morning departures",
                },
            ]
        )

        await bridge.initialize()
        insights = await bridge.extract_and_persist_insights(state)

        # Should extract conversation preferences
        assert "conversation_insights" in insights
        conversation_text = " ".join(insights["conversation_insights"]["preferences"])
        assert "direct flights" in conversation_text.lower()
        assert "early morning" in conversation_text.lower()

    @pytest.mark.asyncio
    async def test_mcp_memory_integration(self, bridge, mock_mcp_manager):
        """Test integration with MCP memory operations."""
        # Mock MCP memory responses
        mock_mcp_manager.invoke.return_value = {
            "entities": [{"name": "test_user", "type": "user"}],
            "relations": [],
        }

        state = create_initial_state("test_user", "Test message")
        assert state["user_id"] == "test_user"

        await bridge.initialize()

        # Test MCP memory operations are called
        await bridge._sync_with_mcp_memory("test_user", {"preference": "budget_travel"})

        # Verify MCP manager was called
        mock_mcp_manager.invoke.assert_called()

    def test_singleton_memory_bridge_access(self):
        """Test singleton access to memory bridge."""
        bridge1 = get_memory_bridge()
        bridge2 = get_memory_bridge()

        assert bridge1 is bridge2  # Should be same instance

    @pytest.mark.asyncio
    async def test_destination_research_insights(self, bridge, mock_session_memory):
        """Test extraction of destination research insights."""
        state = create_initial_state("test_user", "Tell me about Tokyo attractions")

        # Simulate destination research results
        state["destination_info"] = {
            "destination": "Tokyo, Japan",
            "attractions": ["Tokyo Tower", "Senso-ji Temple", "Shibuya Crossing"],
            "research_queries": ["Tokyo attractions", "best time to visit Tokyo"],
            "interests": ["culture", "food", "technology"],
        }

        await bridge.initialize()
        insights = await bridge.extract_and_persist_insights(state)

        # Verify destination insights
        assert "destination_preferences" in insights
        assert "Tokyo" in insights["destination_preferences"]
        assert "culture" in insights["interests"]["categories"]

    @pytest.mark.asyncio
    async def test_agent_usage_patterns(self, bridge, mock_session_memory):
        """Test extraction of agent usage patterns."""
        state = create_initial_state("test_user", "Test message")

        # Simulate interaction with multiple agents
        state["agent_history"] = [
            {"agent": "flight_agent", "timestamp": datetime.now().isoformat()},
            {"agent": "accommodation_agent", "timestamp": datetime.now().isoformat()},
            {
                "agent": "destination_research_agent",
                "timestamp": datetime.now().isoformat(),
            },
        ]

        await bridge.initialize()
        insights = await bridge.extract_and_persist_insights(state)

        # Verify usage patterns
        assert "usage_patterns" in insights
        assert insights["usage_patterns"]["most_used_agents"] == [
            "flight_agent",
            "accommodation_agent",
            "destination_research_agent",
        ]
        assert insights["usage_patterns"]["interaction_count"] == 3
