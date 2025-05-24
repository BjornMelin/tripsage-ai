"""
Comprehensive tests for Chat Agent Phase 5 Implementation.

This test suite validates the enhanced ChatAgent with MCP integration,
intent detection, agent routing, and tool calling capabilities for Phase 5.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.agents.chat import ChatAgent, ChatAgentError
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.chat_orchestration import ChatOrchestrationService


class TestChatAgentPhase5:
    """Test suite for ChatAgent Phase 5 implementation."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager."""
        return AsyncMock(spec=MCPManager)

    @pytest.fixture
    def mock_chat_service(self):
        """Create mock chat orchestration service."""
        return AsyncMock(spec=ChatOrchestrationService)

    @pytest.fixture
    def chat_agent(self, mock_mcp_manager):
        """Create ChatAgent instance with mocked dependencies."""
        with (
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
        ):
            agent = ChatAgent(mcp_manager=mock_mcp_manager)
            # Replace chat service with mock
            agent.chat_service = AsyncMock(spec=ChatOrchestrationService)
            return agent

    @pytest.mark.asyncio
    async def test_intent_detection_flight_queries(self, chat_agent):
        """Test intent detection for flight-related queries."""
        # Test various flight queries
        flight_messages = [
            "I need to book a flight from NYC to LAX",
            "Find me flights departing tomorrow",
            "What's the cheapest airline to Paris?",
            "Book a ticket to London for next week",
            "I want to fly to Tokyo",
        ]

        for message in flight_messages:
            intent = await chat_agent.detect_intent(message)

            assert intent["primary_intent"] == "flight"
            assert intent["confidence"] > 0.5
            assert "flight" in intent["all_scores"]
            assert intent["all_scores"]["flight"] > 0

    @pytest.mark.asyncio
    async def test_intent_detection_accommodation_queries(self, chat_agent):
        """Test intent detection for accommodation-related queries."""
        # Test various accommodation queries
        accommodation_messages = [
            "Find me a hotel in downtown Seattle",
            "Book an Airbnb for my vacation",
            "I need accommodation near the airport",
            "What are the best resorts in Bali?",
            "Reserve a room for two nights",
        ]

        for message in accommodation_messages:
            intent = await chat_agent.detect_intent(message)

            assert intent["primary_intent"] == "accommodation"
            assert intent["confidence"] > 0.5
            assert intent["all_scores"]["accommodation"] > 0

    @pytest.mark.asyncio
    async def test_intent_detection_budget_queries(self, chat_agent):
        """Test intent detection for budget-related queries."""
        # Test various budget queries
        budget_messages = [
            "How much will this trip cost?",
            "I have a budget of $2000 for my vacation",
            "What's the cheapest way to travel?",
            "Can I afford a trip to Europe?",
            "Budget planning for my honeymoon",
        ]

        for message in budget_messages:
            intent = await chat_agent.detect_intent(message)

            assert intent["primary_intent"] == "budget"
            assert intent["confidence"] > 0.5
            assert intent["all_scores"]["budget"] > 0

    @pytest.mark.asyncio
    async def test_intent_detection_general_queries(self, chat_agent):
        """Test intent detection for general queries."""
        # Test various general queries
        general_messages = [
            "Hello, how are you?",
            "Can you help me?",
            "What can you do?",
            "I'm planning a trip",
            "Tell me about travel",
        ]

        for message in general_messages:
            intent = await chat_agent.detect_intent(message)

            assert intent["primary_intent"] == "general"
            assert intent["confidence"] <= 0.7  # Low confidence, no specific intent

    @pytest.mark.asyncio
    async def test_intent_detection_weather_queries(self, chat_agent):
        """Test intent detection for weather-related queries."""
        # Test weather queries
        weather_messages = [
            "What's the weather like in Paris?",
            "Check the temperature in Tokyo",
            "Will it rain tomorrow in London?",
            "Climate forecast for next week",
        ]

        for message in weather_messages:
            intent = await chat_agent.detect_intent(message)

            assert intent["primary_intent"] == "weather"
            assert intent["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_intent_detection_maps_queries(self, chat_agent):
        """Test intent detection for maps/location queries."""
        # Test maps queries
        maps_messages = [
            "How do I get to the airport?",
            "Show me directions to the hotel",
            "Where is Times Square?",
            "Find the address of this restaurant",
            "What's the distance between cities?",
        ]

        for message in maps_messages:
            intent = await chat_agent.detect_intent(message)

            assert intent["primary_intent"] == "maps"
            assert intent["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_route_request_high_confidence_flight(self, chat_agent):
        """Test request routing for high-confidence flight intent."""
        # Arrange
        message = "Book a flight from NYC to LAX departing June 1st"
        session_id = "test_session_123"

        # Act
        response = await chat_agent.route_request(message, session_id)

        # Assert
        assert response["intent"] == "flight_search"
        assert response["action"] == "mcp_flight_search"
        assert response["session_id"] == session_id
        assert response["mcp_service"] == "duffel_flights"
        assert response["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_route_request_high_confidence_accommodation(self, chat_agent):
        """Test request routing for high-confidence accommodation intent."""
        # Arrange
        message = "Find me a hotel in downtown San Francisco for 3 nights"
        session_id = "test_session_456"

        # Act
        response = await chat_agent.route_request(message, session_id)

        # Assert
        assert response["intent"] == "accommodation_search"
        assert response["action"] == "mcp_accommodation_search"
        assert response["session_id"] == session_id
        assert response["mcp_service"] == "airbnb"
        assert response["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_route_request_weather_mcp(self, chat_agent):
        """Test request routing for weather queries using MCP."""
        # Arrange
        message = "What's the weather like in Los Angeles?"
        session_id = "test_session_weather"

        # Act
        response = await chat_agent.route_request(message, session_id)

        # Assert
        assert response["intent"] == "weather_check"
        assert response["action"] == "mcp_weather_check"
        assert response["mcp_service"] == "weather"
        assert response["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_route_request_maps_mcp(self, chat_agent):
        """Test request routing for maps queries using MCP."""
        # Arrange
        message = "Where is the Statue of Liberty located?"
        session_id = "test_session_maps"

        # Act
        response = await chat_agent.route_request(message, session_id)

        # Assert
        assert response["intent"] == "location_info"
        assert response["action"] == "mcp_location_lookup"
        assert response["mcp_service"] == "google_maps"
        assert response["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_route_request_low_confidence_direct_handling(self, chat_agent):
        """Test request routing for low-confidence intents (direct handling)."""
        # Arrange
        message = "Hello, can you help me plan something?"
        session_id = "test_session_general"

        with patch.object(chat_agent, "run") as mock_run:
            mock_run.return_value = {
                "content": "I'd be happy to help!",
                "status": "success",
            }

            # Act
            response = await chat_agent.route_request(message, session_id)

            # Assert
            assert response["content"] == "I'd be happy to help!"
            assert response["status"] == "success"
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_to_agent_flight_agent(self, chat_agent):
        """Test routing to FlightAgent for flight-specific queries."""
        # Arrange
        intent = {"primary_intent": "flight", "confidence": 0.9}
        message = "Find flights from NYC to LAX"
        context = {"user_id": 123}

        mock_flight_agent = AsyncMock()
        mock_flight_agent.run.return_value = {
            "flights": ["flight_data"],
            "agent": "flight",
        }
        chat_agent.flight_agent = mock_flight_agent

        # Act
        response = await chat_agent.route_to_agent(intent, message, context)

        # Assert
        assert response["flights"] == ["flight_data"]
        assert response["agent"] == "flight"
        mock_flight_agent.run.assert_called_once_with(message, context)

    @pytest.mark.asyncio
    async def test_route_to_agent_accommodation_agent(self, chat_agent):
        """Test routing to AccommodationAgent for accommodation-specific queries."""
        # Arrange
        intent = {"primary_intent": "accommodation", "confidence": 0.8}
        message = "Find hotels in Seattle"
        context = {"user_id": 456}

        mock_accommodation_agent = AsyncMock()
        mock_accommodation_agent.run.return_value = {
            "hotels": ["hotel_data"],
            "agent": "accommodation",
        }
        chat_agent.accommodation_agent = mock_accommodation_agent

        # Act
        response = await chat_agent.route_to_agent(intent, message, context)

        # Assert
        assert response["hotels"] == ["hotel_data"]
        assert response["agent"] == "accommodation"
        mock_accommodation_agent.run.assert_called_once_with(message, context)

    @pytest.mark.asyncio
    async def test_route_to_agent_fallback_handling(self, chat_agent):
        """Test agent routing fallback when specialized agent fails."""
        # Arrange
        intent = {"primary_intent": "flight", "confidence": 0.9}
        message = "Find flights"
        context = {}

        mock_flight_agent = AsyncMock()
        mock_flight_agent.run.side_effect = Exception("Agent unavailable")
        chat_agent.flight_agent = mock_flight_agent

        # Act
        response = await chat_agent.route_to_agent(intent, message, context)

        # Assert
        assert response["status"] == "fallback"
        assert "flight specialist" in response["content"]
        assert "original_error" in response

    @pytest.mark.asyncio
    async def test_call_mcp_tools_successful_execution(self, chat_agent):
        """Test successful MCP tool calling execution."""
        # Arrange
        tool_calls = [
            {
                "id": "flight_search",
                "service": "duffel_flights",
                "method": "search_flights",
                "params": {"origin": "NYC", "destination": "LAX"},
            },
            {
                "id": "weather_check",
                "service": "weather",
                "method": "get_weather",
                "params": {"location": "Los Angeles"},
            },
        ]

        expected_results = {
            "flight_search": {"flights": ["flight1", "flight2"]},
            "weather_check": {"temperature": 75, "condition": "sunny"},
        }

        chat_agent.chat_service.execute_parallel_tools.return_value = expected_results

        # Act
        response = await chat_agent.call_mcp_tools(tool_calls)

        # Assert
        assert response["status"] == "success"
        assert response["tool_call_results"] == expected_results
        assert response["execution_count"] == 2
        assert "timestamp" in response

        chat_agent.chat_service.execute_parallel_tools.assert_called_once_with(
            tool_calls
        )

    @pytest.mark.asyncio
    async def test_call_mcp_tools_execution_failure(self, chat_agent):
        """Test MCP tool calling execution failure handling."""
        # Arrange
        tool_calls = [
            {"id": "test_call", "service": "test", "method": "test", "params": {}}
        ]

        chat_agent.chat_service.execute_parallel_tools.side_effect = Exception(
            "MCP service unavailable"
        )

        # Act & Assert
        with pytest.raises(ChatAgentError, match="MCP tool calling failed"):
            await chat_agent.call_mcp_tools(tool_calls)

    @pytest.mark.asyncio
    async def test_create_chat_session_mcp(self, chat_agent):
        """Test creating chat session using MCP database operations."""
        # Arrange
        user_id = 123
        metadata = {"client": "web", "version": "2.0"}
        expected_session_data = {
            "session_id": "session_789",
            "user_id": user_id,
            "created_at": "2025-01-23T10:00:00Z",
            "metadata": metadata,
        }

        chat_agent.chat_service.create_chat_session.return_value = expected_session_data

        # Act
        response = await chat_agent.create_chat_session_mcp(user_id, metadata)

        # Assert
        assert response == expected_session_data
        chat_agent.chat_service.create_chat_session.assert_called_once_with(
            user_id, metadata
        )

    @pytest.mark.asyncio
    async def test_create_chat_session_mcp_failure(self, chat_agent):
        """Test chat session creation failure handling."""
        # Arrange
        chat_agent.chat_service.create_chat_session.side_effect = Exception(
            "Database unavailable"
        )

        # Act & Assert
        with pytest.raises(ChatAgentError, match="Session creation failed"):
            await chat_agent.create_chat_session_mcp(123, {})

    @pytest.mark.asyncio
    async def test_save_message_mcp(self, chat_agent):
        """Test saving message using MCP database operations."""
        # Arrange
        session_id = "session_123"
        role = "user"
        content = "Hello, I need help with travel planning"
        metadata = {"timestamp": "2025-01-23T10:00:00Z"}

        expected_message_data = {
            "message_id": "msg_456",
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata,
        }

        chat_agent.chat_service.save_message.return_value = expected_message_data

        # Act
        response = await chat_agent.save_message_mcp(
            session_id, role, content, metadata
        )

        # Assert
        assert response == expected_message_data
        chat_agent.chat_service.save_message.assert_called_once_with(
            session_id, role, content, metadata
        )

    @pytest.mark.asyncio
    async def test_save_message_mcp_failure(self, chat_agent):
        """Test message saving failure handling."""
        # Arrange
        chat_agent.chat_service.save_message.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ChatAgentError, match="Message saving failed"):
            await chat_agent.save_message_mcp("session", "user", "content", {})

    @pytest.mark.asyncio
    async def test_tool_call_rate_limiting(self, chat_agent):
        """Test tool call rate limiting enforcement."""
        # Arrange
        user_id = "test_user"

        # Fill up rate limit (5 calls per minute)
        for i in range(5):
            await chat_agent.log_tool_call(user_id)

        # Act
        within_limit = await chat_agent.check_tool_rate_limit(user_id)

        # Assert
        assert within_limit is False

    @pytest.mark.asyncio
    async def test_tool_call_rate_limit_reset(self, chat_agent):
        """Test that rate limit resets over time."""
        # Arrange
        user_id = "test_user_reset"

        # Mock time to simulate calls from more than 1 minute ago
        with patch(
            "time.time", side_effect=[1000, 1000, 1000, 1000, 1000, 1070]
        ):  # 70 seconds later
            # Fill up rate limit
            for i in range(5):
                await chat_agent.log_tool_call(user_id)

            # Check if rate limit has reset
            within_limit = await chat_agent.check_tool_rate_limit(user_id)

        # Assert
        assert within_limit is True

    @pytest.mark.asyncio
    async def test_process_message_with_high_confidence_routing(self, chat_agent):
        """Test process_message with high confidence intent routing."""
        # Arrange
        message = "Find flights from New York to Los Angeles"
        context = {"user_id": 123}

        # Mock flight agent
        mock_flight_agent = AsyncMock()
        mock_flight_agent.run.return_value = {
            "flights": ["flight_data"],
            "agent": "flight",
        }
        chat_agent.flight_agent = mock_flight_agent

        # Act
        response = await chat_agent.process_message(message, context)

        # Assert
        assert "routed_to" in response
        assert response["routed_to"] == "flight"
        assert "routing_confidence" in response
        assert response["routing_confidence"] > 0.7

    @pytest.mark.asyncio
    async def test_process_message_with_direct_handling(self, chat_agent):
        """Test process_message with direct handling for low confidence."""
        # Arrange
        message = "Hello there!"
        context = {"user_id": 456}

        with patch.object(chat_agent, "run") as mock_run:
            mock_run.return_value = {
                "content": "Hello! How can I help?",
                "status": "success",
            }

            # Act
            response = await chat_agent.process_message(message, context)

            # Assert
            assert response["handled_by"] == "chat_agent"
            assert "intent_detected" in response
            assert response["content"] == "Hello! How can I help?"

    @pytest.mark.asyncio
    async def test_run_with_tools_enabled(self, chat_agent):
        """Test running agent with tool calling support enabled."""
        # Arrange
        message = "Help me plan a trip"
        context = {"user_id": 789}
        available_tools = ["weather", "maps", "flights"]

        with patch.object(chat_agent, "process_message") as mock_process:
            mock_process.return_value = {
                "content": "I can help with that!",
                "tools_enabled": True,
            }

            # Act
            response = await chat_agent.run_with_tools(
                message, context, available_tools
            )

            # Assert
            assert response["tools_enabled"] is True

            # Verify context was properly set
            call_args = mock_process.call_args[0]
            call_context = call_args[1]
            assert call_context["available_tools"] == available_tools
            assert call_context["tool_calling_enabled"] is True

    def test_chat_agent_initialization(self, mock_mcp_manager):
        """Test ChatAgent initialization with Phase 5 components."""
        # Act
        with (
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
        ):
            agent = ChatAgent(mcp_manager=mock_mcp_manager)

        # Assert
        assert agent.mcp_manager == mock_mcp_manager
        assert hasattr(agent, "chat_service")
        assert isinstance(agent.chat_service, ChatOrchestrationService)
        assert agent._max_tool_calls_per_minute == 5
        assert hasattr(agent, "_tool_call_history")

    @pytest.mark.asyncio
    async def test_specialized_agent_initialization_failure_handling(
        self, mock_mcp_manager
    ):
        """Test graceful handling of specialized agent initialization failures."""
        # Arrange - Mock one agent failing to initialize
        with (
            patch(
                "tripsage.agents.chat.FlightAgent",
                side_effect=Exception("FlightAgent init failed"),
            ),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
        ):
            # Act - Should not raise exception
            agent = ChatAgent(mcp_manager=mock_mcp_manager)

            # Assert - Agent should still be functional without flight agent
            assert not hasattr(agent, "flight_agent")
            assert hasattr(
                agent, "accommodation_agent"
            )  # Other agents should still work


class TestChatAgentIntegration:
    """Integration tests for ChatAgent Phase 5 implementation."""

    @pytest.mark.asyncio
    async def test_end_to_end_flight_search_flow(self):
        """Test complete flight search flow from intent detection to MCP execution."""
        # Arrange
        mock_manager = AsyncMock(spec=MCPManager)

        with (
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
        ):
            agent = ChatAgent(mcp_manager=mock_manager)

            # Mock chat service responses
            agent.chat_service.execute_parallel_tools.return_value = {
                "flight_search": {"offers": [{"id": "offer_1", "price": "250.00"}]}
            }

        message = "Find me flights from NYC to LAX for June 1st"
        session_id = "integration_test_session"

        # Act
        response = await agent.route_request(message, session_id)

        # Verify intent detection and routing
        assert response["intent"] == "flight_search"
        assert response["mcp_service"] == "duffel_flights"
        assert response["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_concurrent_intent_detection_performance(self):
        """Test intent detection performance under concurrent load."""
        mock_manager = AsyncMock(spec=MCPManager)

        with (
            patch("tripsage.agents.chat.FlightAgent"),
            patch("tripsage.agents.chat.AccommodationAgent"),
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
        ):
            agent = ChatAgent(mcp_manager=mock_manager)

        # Create multiple concurrent intent detection requests
        messages = [
            "Find flights to Paris",
            "Book a hotel in Rome",
            "What's my budget for this trip?",
            "Weather in London tomorrow",
            "Directions to the airport",
        ] * 10  # 50 total requests

        # Execute concurrently
        tasks = [agent.detect_intent(message) for message in messages]
        results = await asyncio.gather(*tasks)

        # Verify all completed successfully
        assert len(results) == 50
        assert all("primary_intent" in result for result in results)
        assert all("confidence" in result for result in results)

    @pytest.mark.asyncio
    async def test_mixed_intent_conversation_flow(self):
        """Test conversation flow with mixed intents and agent routing."""
        mock_manager = AsyncMock(spec=MCPManager)

        with (
            patch("tripsage.agents.chat.FlightAgent") as mock_flight_agent,
            patch(
                "tripsage.agents.chat.AccommodationAgent"
            ) as mock_accommodation_agent,
            patch("tripsage.agents.chat.BudgetAgent"),
            patch("tripsage.agents.chat.DestinationResearchAgent"),
            patch("tripsage.agents.chat.ItineraryAgent"),
            patch("tripsage.agents.chat.TravelAgent"),
        ):
            # Setup mock agents
            mock_flight_agent.return_value.run.return_value = {
                "flights": ["flight_result"]
            }
            mock_accommodation_agent.return_value.run.return_value = {
                "hotels": ["hotel_result"]
            }

            agent = ChatAgent(mcp_manager=mock_manager)

        # Simulate conversation flow
        conversation = [
            ("Hello! I'm planning a trip", "general"),
            ("Find flights from NYC to London", "flight"),
            ("Now find me hotels in London", "accommodation"),
            ("What's the weather like there?", "weather"),
        ]

        results = []
        for message, expected_intent in conversation:
            if expected_intent in ["flight", "accommodation"]:
                # These will route to agents
                intent = await agent.detect_intent(message)
                context = {"user_id": 123}
                result = await agent.route_to_agent(intent, message, context)
                results.append((message, expected_intent, result))
            elif expected_intent == "weather":
                # This will route to MCP
                result = await agent.route_request(message, "test_session")
                results.append((message, expected_intent, result))
            else:
                # General conversation
                intent = await agent.detect_intent(message)
                results.append((message, expected_intent, intent))

        # Verify conversation flow
        assert len(results) == 4

        # Check flight routing
        flight_result = results[1][2]
        assert "flights" in flight_result

        # Check accommodation routing
        accommodation_result = results[2][2]
        assert "hotels" in accommodation_result

        # Check weather MCP routing
        weather_result = results[3][2]
        assert weather_result["mcp_service"] == "weather"
