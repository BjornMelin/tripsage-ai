"""
Simplified tests for the ChatAgent class - intent detection and core logic only.

This module tests the ChatAgent implementation focusing on core functionality
without complex dependency chains.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestChatAgentCore:
    """Tests for ChatAgent core functionality without complex dependencies."""

    @pytest.mark.asyncio
    async def test_detect_intent_flight_keywords(self):
        """Test intent detection for flight-related queries using isolated logic."""
        # Import and instantiate the method logic directly
        from tripsage.agents.chat import ChatAgent

        # Create minimal mock agent with just the detect_intent method
        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()

            # Test flight intent detection
            intent = await agent.detect_intent("I need to book a flight to Paris")

            assert intent["primary_intent"] == "flight"
            assert intent["confidence"] > 0.0
            assert intent["all_scores"]["flight"] > 0

    @pytest.mark.asyncio
    async def test_detect_intent_accommodation_keywords(self):
        """Test intent detection for accommodation-related queries."""
        from tripsage.agents.chat import ChatAgent

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()

            intent = await agent.detect_intent("Find me a hotel in Rome")

            assert intent["primary_intent"] == "accommodation"
            assert intent["confidence"] > 0.0
            assert intent["all_scores"]["accommodation"] > 0

    @pytest.mark.asyncio
    async def test_detect_intent_general(self):
        """Test intent detection for general queries."""
        from tripsage.agents.chat import ChatAgent

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()

            intent = await agent.detect_intent("Hello, how are you?")

            assert intent["primary_intent"] == "general"
            assert intent["confidence"] == 0.5
            assert not intent["requires_routing"]

    @pytest.mark.asyncio
    async def test_check_tool_rate_limit(self):
        """Test tool call rate limiting functionality."""
        from tripsage.agents.chat import ChatAgent

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()
            user_id = "test_user"

            # Should allow first 5 calls
            for _i in range(5):
                assert await agent.check_tool_rate_limit(user_id)
                await agent.log_tool_call(user_id)

            # Should deny 6th call
            assert not await agent.check_tool_rate_limit(user_id)

    @pytest.mark.asyncio
    async def test_tool_rate_limit_expiry(self):
        """Test that rate limit resets after time window."""
        from tripsage.agents.chat import ChatAgent

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()
            user_id = "test_user"

            # Fill up the rate limit
            for _i in range(5):
                await agent.log_tool_call(user_id)

            # Should be at limit
            assert not await agent.check_tool_rate_limit(user_id)

            # Mock time advancing by 61 seconds
            original_time = time.time()
            with patch("time.time", return_value=original_time + 61):
                # Should allow calls again
                assert await agent.check_tool_rate_limit(user_id)

    @pytest.mark.asyncio
    async def test_execute_tool_call_rate_limit(self):
        """Test tool call rate limiting in execute_tool_call."""
        from tripsage.agents.chat import ChatAgent

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()
            user_id = "test_user"

            # Fill up rate limit
            for _i in range(5):
                await agent.log_tool_call(user_id)

            result = await agent.execute_tool_call(
                "weather_tool", {"location": "Paris"}, user_id
            )

            assert result["status"] == "error"
            assert result["error_type"] == "RateLimitExceeded"
            assert "Tool call limit exceeded" in result["error_message"]
            assert result["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self):
        """Test successful tool call execution."""
        from tripsage.agents.chat import ChatAgent

        mock_mcp_manager = MagicMock()
        mock_mcp_manager.invoke = AsyncMock(
            return_value={"success": True, "data": "test result"}
        )

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
            patch("tripsage.agents.chat.mcp_manager", mock_mcp_manager),
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()

            result = await agent.execute_tool_call(
                "weather_tool", {"location": "Paris"}, "test_user"
            )

            assert result["status"] == "success"
            assert result["tool_name"] == "weather_tool"
            assert "result" in result
            assert "execution_time" in result

            mock_mcp_manager.invoke.assert_called_once_with(
                "weather_tool", location="Paris"
            )

    def test_initialization_basic(self):
        """Test basic ChatAgent initialization."""
        from tripsage.agents.chat import ChatAgent

        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7

            agent = ChatAgent()

            assert agent.name == "TripSage Chat Assistant"
            assert "TripSage's central chat assistant" in agent.instructions
            assert agent._max_tool_calls_per_minute == 5
