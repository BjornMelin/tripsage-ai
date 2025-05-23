"""
Tests for the ChatAgent class.

This module tests the ChatAgent implementation that serves as the central coordinator
for TripSage chat functionality, including intent detection, agent routing, and tool calling.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestChatAgent:
    """Tests for the ChatAgent class."""

    @pytest.fixture
    def mock_specialized_agents(self):
        """Mock all specialized agents."""
        return {
            "flight_agent": MagicMock(),
            "accommodation_agent": MagicMock(),
            "budget_agent": MagicMock(),
            "destination_agent": MagicMock(),
            "itinerary_agent": MagicMock(),
            "travel_agent": MagicMock(),
        }

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager for tool execution."""
        mock_manager = MagicMock()
        mock_manager.invoke = AsyncMock(return_value={"success": True, "data": "test result"})
        return mock_manager

    @pytest.fixture
    def chat_agent(self, mock_specialized_agents):
        """Create a ChatAgent instance with mocked dependencies."""
        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent", return_value=mock_specialized_agents["flight_agent"]),
            patch("tripsage.agents.chat.AccommodationAgent", return_value=mock_specialized_agents["accommodation_agent"]),
            patch("tripsage.agents.chat.BudgetAgent", return_value=mock_specialized_agents["budget_agent"]),
            patch("tripsage.agents.chat.DestinationResearchAgent", return_value=mock_specialized_agents["destination_agent"]),
            patch("tripsage.agents.chat.ItineraryAgent", return_value=mock_specialized_agents["itinerary_agent"]),
            patch("tripsage.agents.chat.TravelAgent", return_value=mock_specialized_agents["travel_agent"]),
            patch("tripsage.agents.chat.settings") as mock_settings,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7
            
            from tripsage.agents.chat import ChatAgent
            agent = ChatAgent()
            return agent

    def test_initialization(self, chat_agent):
        """Test that the ChatAgent initializes with proper configuration."""
        assert chat_agent.name == "TripSage Chat Assistant"
        assert "TripSage's central chat assistant" in chat_agent.instructions
        assert chat_agent.metadata["agent_type"] == "chat_coordinator"
        assert chat_agent.metadata["version"] == "1.0.0"
        assert chat_agent._max_tool_calls_per_minute == 5
        assert hasattr(chat_agent, "flight_agent")
        assert hasattr(chat_agent, "accommodation_agent")
        assert hasattr(chat_agent, "budget_agent")
        assert hasattr(chat_agent, "destination_agent")
        assert hasattr(chat_agent, "itinerary_agent")
        assert hasattr(chat_agent, "travel_agent")

    def test_initialization_with_custom_params(self):
        """Test ChatAgent initialization with custom parameters."""
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
            
            from tripsage.agents.chat import ChatAgent
            agent = ChatAgent(
                name="Custom Chat Agent",
                model="gpt-3.5-turbo",
                temperature=0.5
            )
            
            assert agent.name == "Custom Chat Agent"
            assert agent.model == "gpt-3.5-turbo"
            assert agent.temperature == 0.5

    def test_initialization_agent_failure(self):
        """Test that ChatAgent continues initialization even if specialized agents fail."""
        with (
            patch("agents.Agent"),
            patch("agents.Runner"),
            patch("tripsage.agents.chat.FlightAgent", side_effect=Exception("Agent init failed")),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
            patch("tripsage.agents.chat.settings") as mock_settings,
            patch("tripsage.agents.chat.logger") as mock_logger,
        ):
            mock_settings.agent.model_name = "gpt-4"
            mock_settings.agent.temperature = 0.7
            
            from tripsage.agents.chat import ChatAgent
            agent = ChatAgent()
            
            # Should log error but continue
            mock_logger.error.assert_called()
            assert "Failed to initialize specialized agents" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_detect_intent_flight(self, chat_agent):
        """Test intent detection for flight-related queries."""
        test_cases = [
            "I need to book a flight to Paris",
            "Find me flights from NYC to LA",
            "What airlines fly to Tokyo?",
            "Book a ticket to Berlin",
        ]
        
        for message in test_cases:
            intent = await chat_agent.detect_intent(message)
            
            assert intent["primary_intent"] == "flight"
            assert intent["confidence"] > 0.0
            assert "all_scores" in intent
            assert intent["all_scores"]["flight"] > 0

    @pytest.mark.asyncio
    async def test_detect_intent_accommodation(self, chat_agent):
        """Test intent detection for accommodation-related queries."""
        test_cases = [
            "Find me a hotel in Paris",
            "I need accommodation for my stay",
            "Book a room in downtown",
            "Looking for an Airbnb rental",
        ]
        
        for message in test_cases:
            intent = await chat_agent.detect_intent(message)
            
            assert intent["primary_intent"] == "accommodation"
            assert intent["confidence"] > 0.0
            assert intent["all_scores"]["accommodation"] > 0

    @pytest.mark.asyncio
    async def test_detect_intent_budget(self, chat_agent):
        """Test intent detection for budget-related queries."""
        test_cases = [
            "What's my budget for this trip?",
            "How much will it cost?",
            "I can afford $1000 for travel",
            "Find cheap options",
        ]
        
        for message in test_cases:
            intent = await chat_agent.detect_intent(message)
            
            assert intent["primary_intent"] == "budget"
            assert intent["confidence"] > 0.0
            assert intent["all_scores"]["budget"] > 0

    @pytest.mark.asyncio
    async def test_detect_intent_patterns(self, chat_agent):
        """Test intent detection with regex patterns."""
        test_cases = [
            ("I want to fly to Rome", "flight"),
            ("Book a flight from LAX", "flight"),
            ("Stay in a hotel downtown", "accommodation"),
            ("How much does it cost?", "budget"),
            ("Plan my trip day by day", "itinerary"),
            ("What's the weather in Tokyo?", "weather"),
            ("How to get to the airport?", "maps"),
        ]
        
        for message, expected_intent in test_cases:
            intent = await chat_agent.detect_intent(message)
            assert intent["primary_intent"] == expected_intent

    @pytest.mark.asyncio
    async def test_detect_intent_general(self, chat_agent):
        """Test intent detection for general queries."""
        intent = await chat_agent.detect_intent("Hello, how are you?")
        
        assert intent["primary_intent"] == "general"
        assert intent["confidence"] == 0.5
        assert not intent["requires_routing"]

    @pytest.mark.asyncio
    async def test_detect_intent_confidence_levels(self, chat_agent):
        """Test intent confidence calculation."""
        # High confidence case (multiple keywords + pattern)
        high_confidence_intent = await chat_agent.detect_intent("Book a flight ticket from airport")
        assert high_confidence_intent["confidence"] > 0.7
        assert high_confidence_intent["requires_routing"]
        
        # Low confidence case (single keyword)
        low_confidence_intent = await chat_agent.detect_intent("I mentioned flight in passing")
        assert low_confidence_intent["confidence"] <= 0.7

    @pytest.mark.asyncio
    async def test_check_tool_rate_limit(self, chat_agent):
        """Test tool call rate limiting functionality."""
        user_id = "test_user"
        
        # Should allow first calls
        for i in range(5):
            assert await chat_agent.check_tool_rate_limit(user_id)
            await chat_agent.log_tool_call(user_id)
        
        # Should deny 6th call
        assert not await chat_agent.check_tool_rate_limit(user_id)

    @pytest.mark.asyncio
    async def test_tool_rate_limit_expiry(self, chat_agent):
        """Test that rate limit resets after time window."""
        user_id = "test_user"
        
        # Fill up the rate limit
        for i in range(5):
            await chat_agent.log_tool_call(user_id)
        
        # Should be at limit
        assert not await chat_agent.check_tool_rate_limit(user_id)
        
        # Mock time advancing by 61 seconds
        original_time = time.time()
        with patch("time.time", return_value=original_time + 61):
            # Should allow calls again
            assert await chat_agent.check_tool_rate_limit(user_id)

    @pytest.mark.asyncio
    async def test_route_to_agent_flight(self, chat_agent, mock_specialized_agents):
        """Test routing to FlightAgent."""
        intent = {"primary_intent": "flight", "confidence": 0.8}
        message = "Find flights to Paris"
        context = {"user_id": "test_user"}
        
        mock_specialized_agents["flight_agent"].run = AsyncMock(
            return_value={"content": "Flight search results", "status": "success"}
        )
        
        result = await chat_agent.route_to_agent(intent, message, context)
        
        mock_specialized_agents["flight_agent"].run.assert_called_once_with(message, context)
        assert result["content"] == "Flight search results"

    @pytest.mark.asyncio
    async def test_route_to_agent_accommodation(self, chat_agent, mock_specialized_agents):
        """Test routing to AccommodationAgent."""
        intent = {"primary_intent": "accommodation", "confidence": 0.8}
        message = "Find hotels in Rome"
        context = {"user_id": "test_user"}
        
        mock_specialized_agents["accommodation_agent"].run = AsyncMock(
            return_value={"content": "Hotel search results", "status": "success"}
        )
        
        result = await chat_agent.route_to_agent(intent, message, context)
        
        mock_specialized_agents["accommodation_agent"].run.assert_called_once_with(message, context)
        assert result["content"] == "Hotel search results"

    @pytest.mark.asyncio
    async def test_route_to_agent_fallback(self, chat_agent, mock_specialized_agents):
        """Test fallback to TravelAgent for unknown intents."""
        intent = {"primary_intent": "unknown", "confidence": 0.8}
        message = "Plan my trip"
        context = {"user_id": "test_user"}
        
        mock_specialized_agents["travel_agent"].run = AsyncMock(
            return_value={"content": "General travel planning", "status": "success"}
        )
        
        result = await chat_agent.route_to_agent(intent, message, context)
        
        mock_specialized_agents["travel_agent"].run.assert_called_once_with(message, context)
        assert result["content"] == "General travel planning"

    @pytest.mark.asyncio
    async def test_route_to_agent_error_handling(self, chat_agent, mock_specialized_agents):
        """Test error handling in agent routing."""
        intent = {"primary_intent": "flight", "confidence": 0.8}
        message = "Find flights"
        context = {"user_id": "test_user"}
        
        mock_specialized_agents["flight_agent"].run = AsyncMock(
            side_effect=Exception("Agent error")
        )
        
        result = await chat_agent.route_to_agent(intent, message, context)
        
        assert result["status"] == "fallback"
        assert "encountered an issue" in result["content"]
        assert result["original_error"] == "Agent error"

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, chat_agent, mock_mcp_manager):
        """Test successful tool call execution."""
        with patch("tripsage.agents.chat.mcp_manager", mock_mcp_manager):
            result = await chat_agent.execute_tool_call(
                "weather_tool",
                {"location": "Paris"},
                "test_user"
            )
            
            assert result["status"] == "success"
            assert result["tool_name"] == "weather_tool"
            assert "result" in result
            assert "execution_time" in result
            
            mock_mcp_manager.invoke.assert_called_once_with("weather_tool", location="Paris")

    @pytest.mark.asyncio
    async def test_execute_tool_call_rate_limit(self, chat_agent):
        """Test tool call rate limiting."""
        user_id = "test_user"
        
        # Fill up rate limit
        for i in range(5):
            await chat_agent.log_tool_call(user_id)
        
        result = await chat_agent.execute_tool_call(
            "weather_tool",
            {"location": "Paris"},
            user_id
        )
        
        assert result["status"] == "error"
        assert result["error_type"] == "RateLimitExceeded"
        assert "Tool call limit exceeded" in result["error_message"]
        assert result["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_execute_tool_call_error(self, chat_agent, mock_mcp_manager):
        """Test tool call execution error handling."""
        mock_mcp_manager.invoke = AsyncMock(side_effect=Exception("Tool execution failed"))
        
        with patch("tripsage.agents.chat.mcp_manager", mock_mcp_manager):
            result = await chat_agent.execute_tool_call(
                "weather_tool",
                {"location": "Paris"},
                "test_user"
            )
            
            assert result["status"] == "error"
            assert result["error_type"] == "Exception"
            assert result["error_message"] == "Tool execution failed"
            assert result["tool_name"] == "weather_tool"

    @pytest.mark.asyncio
    async def test_process_message_routing(self, chat_agent, mock_specialized_agents):
        """Test message processing with routing to specialized agent."""
        message = "Find flights to Paris departure tomorrow"  # High confidence flight intent
        context = {"user_id": "test_user"}
        
        mock_specialized_agents["flight_agent"].run = AsyncMock(
            return_value={"content": "Flight results", "status": "success"}
        )
        
        result = await chat_agent.process_message(message, context)
        
        assert result["routed_to"] == "flight"
        assert result["routing_confidence"] > 0.7
        assert result["content"] == "Flight results"
        mock_specialized_agents["flight_agent"].run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_direct_handling(self, chat_agent):
        """Test message processing with direct handling."""
        message = "Hello, how are you?"  # General intent, low confidence
        context = {"user_id": "test_user"}
        
        with patch.object(chat_agent, "run", new_callable=AsyncMock) as mock_super_run:
            mock_super_run.return_value = {"content": "Hello! I'm here to help.", "status": "success"}
            
            result = await chat_agent.process_message(message, context)
            
            assert result["handled_by"] == "chat_agent"
            assert "intent_detected" in result
            assert result["intent_detected"]["primary_intent"] == "general"
            mock_super_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_context_enrichment(self, chat_agent):
        """Test that message processing enriches context properly."""
        message = "What's the weather like?"
        context = {"user_id": "test_user"}
        
        with patch.object(chat_agent, "run", new_callable=AsyncMock) as mock_super_run:
            mock_super_run.return_value = {"content": "Weather info", "status": "success"}
            
            await chat_agent.process_message(message, context)
            
            # Check that context was enriched
            call_args = mock_super_run.call_args[0]
            enriched_context = call_args[1]
            
            assert enriched_context["detected_intent"]["primary_intent"] == "weather"
            assert enriched_context["chat_agent_processed"] is True

    @pytest.mark.asyncio
    async def test_run_with_tools(self, chat_agent):
        """Test run_with_tools method."""
        message = "Check the weather in Tokyo"
        context = {"user_id": "test_user"}
        available_tools = ["weather_tool", "maps_tool"]
        
        with patch.object(chat_agent, "process_message", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"content": "Weather info", "status": "success"}
            
            result = await chat_agent.run_with_tools(message, context, available_tools)
            
            # Check that context was properly set
            call_args = mock_process.call_args[0]
            enriched_context = call_args[1]
            
            assert enriched_context["available_tools"] == available_tools
            assert enriched_context["tool_calling_enabled"] is True
            assert result["content"] == "Weather info"

    @pytest.mark.asyncio
    async def test_run_with_tools_default_params(self, chat_agent):
        """Test run_with_tools with default parameters."""
        message = "Hello"
        
        with patch.object(chat_agent, "process_message", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"content": "Response", "status": "success"}
            
            await chat_agent.run_with_tools(message)
            
            call_args = mock_process.call_args[0]
            context = call_args[1]
            
            assert context["available_tools"] == []
            assert context["tool_calling_enabled"] is True

    def test_tool_registration(self, chat_agent):
        """Test that travel tools are registered during initialization."""
        # This tests the _register_travel_tools method indirectly
        # by checking that register_tool_group was called
        with patch.object(chat_agent, "register_tool_group") as mock_register:
            chat_agent._register_travel_tools()
            
            # Should attempt to register each tool module
            expected_modules = [
                "time_tools",
                "weather_tools", 
                "googlemaps_tools",
                "webcrawl_tools",
                "memory_tools",
            ]
            
            for module in expected_modules:
                mock_register.assert_any_call(module)

    def test_tool_registration_error_handling(self, chat_agent):
        """Test that tool registration continues even if some modules fail."""
        with (
            patch.object(chat_agent, "register_tool_group", side_effect=Exception("Module not found")),
            patch("tripsage.agents.chat.logger") as mock_logger,
        ):
            chat_agent._register_travel_tools()
            
            # Should log warnings but continue
            assert mock_logger.warning.call_count >= 1