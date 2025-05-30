"""
Comprehensive tests for ChatAgent.

This module provides extensive testing for the chat agent including
intent detection, agent routing, tool calling, and memory integration.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.chat import ChatAgent, ChatAgentError


class TestChatAgent:
    """Comprehensive tests for ChatAgent."""

    @pytest.fixture
    def mock_specialized_agents(self):
        """Mock all specialized agents."""
        agents = {}
        agent_types = [
            "flight",
            "accommodation",
            "budget",
            "destination",
            "itinerary",
            "travel",
        ]

        for agent_type in agent_types:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(
                return_value={
                    "content": f"Response from {agent_type} agent",
                    "status": "success",
                    "agent_type": agent_type,
                }
            )
            agents[f"{agent_type}_agent"] = mock_agent

        return agents

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager."""
        manager = MagicMock()
        manager.invoke = AsyncMock()
        return manager

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service."""
        service = MagicMock()
        service.connect = AsyncMock()
        service.get_user_context = AsyncMock(
            return_value={
                "preferences": [],
                "past_trips": [],
                "budget_patterns": [],
                "travel_style": [],
                "insights": {
                    "preferred_destinations": {"most_visited": ["Japan"]},
                    "budget_range": {"average_budget": 3000},
                    "travel_frequency": {"total_trips": 2},
                    "preferred_activities": {"preferred_activities": ["museums"]},
                    "travel_style": {"primary_style": "cultural"},
                },
                "summary": "Prefers cultural travel experiences in Japan",
            }
        )
        service.add_conversation_memory = AsyncMock(return_value={"success": True})
        return service

    @pytest.fixture
    def mock_chat_service(self):
        """Mock chat orchestration service."""
        service = MagicMock()
        service.create_chat_session = AsyncMock(
            return_value={"session_id": "session_123", "user_id": 1, "status": "active"}
        )
        service.save_message = AsyncMock(
            return_value={"message_id": "msg_123", "session_id": "session_123"}
        )
        service.execute_parallel_tools = AsyncMock(
            return_value={
                "total_calls": 1,
                "success_count": 1,
                "results": {"tool_1": {"success": True}},
            }
        )
        service.get_chat_history = AsyncMock(return_value=[])
        service.end_chat_session = AsyncMock(return_value=True)
        return service

    @pytest.fixture
    def chat_agent(
        self,
        mock_mcp_manager,
        mock_memory_service,
        mock_chat_service,
        mock_specialized_agents,
    ):
        """Create a ChatAgent instance with mocked dependencies."""
        with patch("tripsage.agents.chat.MCPManager", return_value=mock_mcp_manager):
            with patch(
                "tripsage.agents.chat.ChatOrchestrationService",
                return_value=mock_chat_service,
            ):
                with patch(
                    "tripsage.agents.chat.TripSageMemoryService",
                    return_value=mock_memory_service,
                ):
                    with patch(
                        "tripsage.agents.chat.FlightAgent",
                        return_value=mock_specialized_agents["flight_agent"],
                    ):
                        with patch(
                            "tripsage.agents.chat.AccommodationAgent",
                            return_value=mock_specialized_agents["accommodation_agent"],
                        ):
                            with patch(
                                "tripsage.agents.chat.BudgetAgent",
                                return_value=mock_specialized_agents["budget_agent"],
                            ):
                                with patch(
                                    "tripsage.agents.chat.DestinationResearchAgent",
                                    return_value=mock_specialized_agents[
                                        "destination_agent"
                                    ],
                                ):
                                    with patch(
                                        "tripsage.agents.chat.ItineraryAgent",
                                        return_value=mock_specialized_agents[
                                            "itinerary_agent"
                                        ],
                                    ):
                                        with patch(
                                            "tripsage.agents.chat.TravelAgent",
                                            return_value=mock_specialized_agents[
                                                "travel_agent"
                                            ],
                                        ):
                                            agent = ChatAgent()
                                            # Set up the specialized agents
                                            for (
                                                agent_type,
                                                mock_agent,
                                            ) in mock_specialized_agents.items():
                                                setattr(agent, agent_type, mock_agent)
                                            return agent

    def test_initialization(self, chat_agent):
        """Test ChatAgent initialization."""
        assert chat_agent.name == "TripSage Chat Assistant"
        assert "TripSage's central chat assistant" in chat_agent.instructions
        assert chat_agent.mcp_manager is not None
        assert chat_agent.chat_service is not None
        assert chat_agent.memory_service is not None
        assert not chat_agent._memory_initialized
        assert chat_agent._max_tool_calls_per_minute == 5
        assert chat_agent._tool_call_history == {}

    def test_initialization_custom_params(self):
        """Test ChatAgent initialization with custom parameters."""
        with patch("tripsage.agents.chat.MCPManager") as mock_mcp_cls:
            with patch("tripsage.agents.chat.ChatOrchestrationService"):
                with patch("tripsage.agents.chat.TripSageMemoryService"):
                    with patch("tripsage.agents.chat.FlightAgent"):
                        with patch("tripsage.agents.chat.AccommodationAgent"):
                            with patch("tripsage.agents.chat.BudgetAgent"):
                                with patch(
                                    "tripsage.agents.chat.DestinationResearchAgent"
                                ):
                                    with patch("tripsage.agents.chat.ItineraryAgent"):
                                        with patch("tripsage.agents.chat.TravelAgent"):
                                            custom_mcp = MagicMock()
                                            agent = ChatAgent(
                                                name="Custom Agent",
                                                model="gpt-3.5-turbo",
                                                temperature=0.5,
                                                mcp_manager=custom_mcp,
                                            )

                                            assert agent.name == "Custom Agent"
                                            assert agent.mcp_manager == custom_mcp
                                            mock_mcp_cls.assert_not_called()

    def test_initialize_specialized_agents_success(self, mock_specialized_agents):
        """Test successful specialized agent initialization."""
        with patch("tripsage.agents.chat.MCPManager"):
            with patch("tripsage.agents.chat.ChatOrchestrationService"):
                with patch("tripsage.agents.chat.TripSageMemoryService"):
                    with patch(
                        "tripsage.agents.chat.FlightAgent",
                        return_value=mock_specialized_agents["flight_agent"],
                    ):
                        with patch(
                            "tripsage.agents.chat.AccommodationAgent",
                            return_value=mock_specialized_agents["accommodation_agent"],
                        ):
                            with patch(
                                "tripsage.agents.chat.BudgetAgent",
                                return_value=mock_specialized_agents["budget_agent"],
                            ):
                                with patch(
                                    "tripsage.agents.chat.DestinationResearchAgent",
                                    return_value=mock_specialized_agents[
                                        "destination_agent"
                                    ],
                                ):
                                    with patch(
                                        "tripsage.agents.chat.ItineraryAgent",
                                        return_value=mock_specialized_agents[
                                            "itinerary_agent"
                                        ],
                                    ):
                                        with patch(
                                            "tripsage.agents.chat.TravelAgent",
                                            return_value=mock_specialized_agents[
                                                "travel_agent"
                                            ],
                                        ):
                                            agent = ChatAgent()

                                            assert hasattr(agent, "flight_agent")
                                            assert hasattr(agent, "accommodation_agent")
                                            assert hasattr(agent, "budget_agent")
                                            assert hasattr(agent, "destination_agent")
                                            assert hasattr(agent, "itinerary_agent")
                                            assert hasattr(agent, "travel_agent")

    def test_initialize_specialized_agents_failure(self):
        """Test specialized agent initialization failure handling."""
        with patch("tripsage.agents.chat.MCPManager"):
            with patch("tripsage.agents.chat.ChatOrchestrationService"):
                with patch("tripsage.agents.chat.TripSageMemoryService"):
                    with patch(
                        "tripsage.agents.chat.FlightAgent",
                        side_effect=Exception("Agent init failed"),
                    ):
                        with patch("tripsage.agents.chat.AccommodationAgent"):
                            with patch("tripsage.agents.chat.BudgetAgent"):
                                with patch(
                                    "tripsage.agents.chat.DestinationResearchAgent"
                                ):
                                    with patch("tripsage.agents.chat.ItineraryAgent"):
                                        with patch("tripsage.agents.chat.TravelAgent"):
                                            # Should not raise exception
                                            agent = ChatAgent()
                                            assert agent is not None

    def test_register_travel_tools(self, chat_agent):
        """Test travel tools registration."""
        with patch.object(chat_agent, "register_tool_group") as mock_register:
            chat_agent._register_travel_tools()

            # Should attempt to register all tool modules
            expected_modules = [
                "time_tools",
                "weather_tools",
                "googlemaps_tools",
                "webcrawl_tools",
                "memory_tools",
            ]

            assert mock_register.call_count == len(expected_modules)
            for module in expected_modules:
                mock_register.assert_any_call(module)

    def test_register_travel_tools_failure(self, chat_agent):
        """Test travel tools registration with failures."""
        with patch.object(
            chat_agent,
            "register_tool_group",
            side_effect=Exception("Tool registration failed"),
        ):
            # Should not raise exception
            chat_agent._register_travel_tools()

    @pytest.mark.asyncio
    async def test_ensure_memory_initialized_success(
        self, chat_agent, mock_memory_service
    ):
        """Test successful memory initialization."""
        chat_agent.memory_service = mock_memory_service
        assert not chat_agent._memory_initialized

        await chat_agent._ensure_memory_initialized()

        assert chat_agent._memory_initialized
        mock_memory_service.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_memory_initialized_already_done(
        self, chat_agent, mock_memory_service
    ):
        """Test memory initialization when already initialized."""
        chat_agent.memory_service = mock_memory_service
        chat_agent._memory_initialized = True

        await chat_agent._ensure_memory_initialized()

        mock_memory_service.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_memory_initialized_failure(
        self, chat_agent, mock_memory_service
    ):
        """Test memory initialization failure."""
        mock_memory_service.connect.side_effect = Exception("Connection failed")
        chat_agent.memory_service = mock_memory_service

        # Should not raise exception
        await chat_agent._ensure_memory_initialized()

        assert not chat_agent._memory_initialized

    @pytest.mark.asyncio
    async def test_get_user_context_success(self, chat_agent, mock_memory_service):
        """Test successful user context retrieval."""
        chat_agent.memory_service = mock_memory_service

        context = await chat_agent._get_user_context("user_123")

        assert "preferences" in context
        assert "insights" in context
        assert "summary" in context
        assert context["summary"] == "Prefers cultural travel experiences in Japan"

    @pytest.mark.asyncio
    async def test_get_user_context_failure(self, chat_agent, mock_memory_service):
        """Test user context retrieval failure."""
        mock_memory_service.get_user_context.side_effect = Exception("Context failed")
        chat_agent.memory_service = mock_memory_service

        context = await chat_agent._get_user_context("user_123")

        assert context == {}

    @pytest.mark.asyncio
    async def test_store_conversation_memory_success(
        self, chat_agent, mock_memory_service
    ):
        """Test successful conversation memory storage."""
        chat_agent.memory_service = mock_memory_service

        await chat_agent._store_conversation_memory(
            user_message="I want to visit Japan",
            assistant_response="Great choice! When would you like to visit?",
            user_id="user_123",
            session_id="session_456",
        )

        mock_memory_service.add_conversation_memory.assert_called_once()
        call_args = mock_memory_service.add_conversation_memory.call_args

        assert call_args[1]["user_id"] == "user_123"
        assert call_args[1]["session_id"] == "session_456"
        assert len(call_args[0][0]) == 2  # Two messages
        assert call_args[0][0][0].role == "user"
        assert call_args[0][0][1].role == "assistant"

    @pytest.mark.asyncio
    async def test_store_conversation_memory_failure(
        self, chat_agent, mock_memory_service
    ):
        """Test conversation memory storage failure."""
        mock_memory_service.add_conversation_memory.side_effect = Exception(
            "Storage failed"
        )
        chat_agent.memory_service = mock_memory_service

        # Should not raise exception
        await chat_agent._store_conversation_memory(
            user_message="test", assistant_response="response", user_id="user_123"
        )

    @pytest.mark.asyncio
    async def test_detect_intent_flight(self, chat_agent):
        """Test intent detection for flight queries."""
        message = "I need to book a flight from New York to Los Angeles"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "flight"
        assert intent["confidence"] > 0.7
        assert intent["requires_routing"] is True
        assert "flight" in intent["all_scores"]

    @pytest.mark.asyncio
    async def test_detect_intent_accommodation(self, chat_agent):
        """Test intent detection for accommodation queries."""
        message = "I need to find a hotel in San Francisco for my stay"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "accommodation"
        assert intent["confidence"] > 0.7
        assert intent["requires_routing"] is True

    @pytest.mark.asyncio
    async def test_detect_intent_budget(self, chat_agent):
        """Test intent detection for budget queries."""
        message = "What's the cost of traveling to Japan? I have a budget of $3000"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "budget"
        assert intent["confidence"] > 0.7
        assert intent["requires_routing"] is True

    @pytest.mark.asyncio
    async def test_detect_intent_destination(self, chat_agent):
        """Test intent detection for destination queries."""
        message = "What are the best attractions to visit in Tokyo?"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "destination"
        assert intent["confidence"] > 0.7
        assert intent["requires_routing"] is True

    @pytest.mark.asyncio
    async def test_detect_intent_itinerary(self, chat_agent):
        """Test intent detection for itinerary queries."""
        message = "Can you help me plan a day-by-day itinerary for my trip?"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "itinerary"
        assert intent["confidence"] > 0.7
        assert intent["requires_routing"] is True

    @pytest.mark.asyncio
    async def test_detect_intent_weather(self, chat_agent):
        """Test intent detection for weather queries."""
        message = "What's the weather like in Tokyo right now?"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "weather"
        assert intent["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_intent_maps(self, chat_agent):
        """Test intent detection for maps/location queries."""
        message = "How do I get from the airport to my hotel?"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "maps"
        assert intent["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_intent_general(self, chat_agent):
        """Test intent detection for general queries."""
        message = "Hello, how are you today?"

        intent = await chat_agent.detect_intent(message)

        assert intent["primary_intent"] == "general"
        assert intent["confidence"] == 0.5
        assert intent["requires_routing"] is False

    @pytest.mark.asyncio
    async def test_check_tool_rate_limit_within_limit(self, chat_agent):
        """Test tool rate limit check when within limit."""
        user_id = "user_123"

        # Add some recent calls but within limit
        current_time = time.time()
        chat_agent._tool_call_history[user_id] = [
            current_time - 30,  # 30 seconds ago
            current_time - 45,  # 45 seconds ago
        ]

        result = await chat_agent.check_tool_rate_limit(user_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_tool_rate_limit_exceeded(self, chat_agent):
        """Test tool rate limit check when limit exceeded."""
        user_id = "user_123"

        # Add calls exceeding the limit
        current_time = time.time()
        chat_agent._tool_call_history[user_id] = [
            current_time - 10,  # Within last minute
            current_time - 20,
            current_time - 30,
            current_time - 40,
            current_time - 50,  # 5 calls total
        ]

        result = await chat_agent.check_tool_rate_limit(user_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_tool_rate_limit_old_calls_cleaned(self, chat_agent):
        """Test that old tool calls are cleaned up."""
        user_id = "user_123"

        # Add old calls that should be cleaned up
        current_time = time.time()
        chat_agent._tool_call_history[user_id] = [
            current_time - 70,  # More than 1 minute ago
            current_time - 80,
            current_time - 10,  # Recent call
        ]

        result = await chat_agent.check_tool_rate_limit(user_id)
        assert result is True

        # Old calls should be removed
        assert len(chat_agent._tool_call_history[user_id]) == 1

    @pytest.mark.asyncio
    async def test_log_tool_call(self, chat_agent):
        """Test tool call logging."""
        user_id = "user_123"

        await chat_agent.log_tool_call(user_id)

        assert user_id in chat_agent._tool_call_history
        assert len(chat_agent._tool_call_history[user_id]) == 1

    @pytest.mark.asyncio
    async def test_route_to_agent_flight(self, chat_agent, mock_specialized_agents):
        """Test routing to flight agent."""
        intent = {"primary_intent": "flight", "confidence": 0.9}
        message = "Book a flight to Paris"
        context = {"user_id": "user_123"}

        result = await chat_agent.route_to_agent(intent, message, context)

        assert result["content"] == "Response from flight agent"
        assert result["agent_type"] == "flight"
        mock_specialized_agents["flight_agent"].run.assert_called_once_with(
            message, context
        )

    @pytest.mark.asyncio
    async def test_route_to_agent_accommodation(
        self, chat_agent, mock_specialized_agents
    ):
        """Test routing to accommodation agent."""
        intent = {"primary_intent": "accommodation", "confidence": 0.9}
        message = "Find a hotel in Paris"
        context = {"user_id": "user_123"}

        result = await chat_agent.route_to_agent(intent, message, context)

        assert result["content"] == "Response from accommodation agent"
        mock_specialized_agents["accommodation_agent"].run.assert_called_once_with(
            message, context
        )

    @pytest.mark.asyncio
    async def test_route_to_agent_budget(self, chat_agent, mock_specialized_agents):
        """Test routing to budget agent."""
        intent = {"primary_intent": "budget", "confidence": 0.9}
        message = "What's my budget for this trip?"
        context = {"user_id": "user_123"}

        result = await chat_agent.route_to_agent(intent, message, context)

        assert result["content"] == "Response from budget agent"
        mock_specialized_agents["budget_agent"].run.assert_called_once_with(
            message, context
        )

    @pytest.mark.asyncio
    async def test_route_to_agent_fallback_to_travel(
        self, chat_agent, mock_specialized_agents
    ):
        """Test routing fallback to travel agent."""
        intent = {"primary_intent": "unknown", "confidence": 0.9}
        message = "Help me plan my trip"
        context = {"user_id": "user_123"}

        result = await chat_agent.route_to_agent(intent, message, context)

        assert result["content"] == "Response from travel agent"
        mock_specialized_agents["travel_agent"].run.assert_called_once_with(
            message, context
        )

    @pytest.mark.asyncio
    async def test_route_to_agent_error_handling(
        self, chat_agent, mock_specialized_agents
    ):
        """Test routing error handling."""
        mock_specialized_agents["flight_agent"].run.side_effect = Exception(
            "Agent failed"
        )

        intent = {"primary_intent": "flight", "confidence": 0.9}
        message = "Book a flight"
        context = {"user_id": "user_123"}

        result = await chat_agent.route_to_agent(intent, message, context)

        assert result["status"] == "fallback"
        assert "flight specialist" in result["content"]
        assert "original_error" in result

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, chat_agent, mock_mcp_manager):
        """Test successful tool call execution."""
        mock_mcp_manager.invoke.return_value = {"temperature": 22, "condition": "sunny"}

        result = await chat_agent.execute_tool_call(
            tool_name="weather", parameters={"location": "Tokyo"}, user_id="user_123"
        )

        assert result["status"] == "success"
        assert result["result"]["temperature"] == 22
        assert result["tool_name"] == "weather"
        mock_mcp_manager.invoke.assert_called_once_with("weather", location="Tokyo")

    @pytest.mark.asyncio
    async def test_execute_tool_call_rate_limited(self, chat_agent):
        """Test tool call execution when rate limited."""
        # Set up rate limit exceeded
        user_id = "user_123"
        current_time = time.time()
        chat_agent._tool_call_history[user_id] = [current_time - i for i in range(5)]

        result = await chat_agent.execute_tool_call(
            tool_name="weather", parameters={}, user_id=user_id
        )

        assert result["status"] == "error"
        assert result["error_type"] == "RateLimitExceeded"
        assert result["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_execute_tool_call_failure(self, chat_agent, mock_mcp_manager):
        """Test tool call execution failure."""
        mock_mcp_manager.invoke.side_effect = Exception("Tool execution failed")

        result = await chat_agent.execute_tool_call(
            tool_name="weather", parameters={}, user_id="user_123"
        )

        assert result["status"] == "error"
        assert result["error_type"] == "Exception"
        assert "Tool execution failed" in result["error_message"]

    @pytest.mark.asyncio
    async def test_process_message_with_routing(
        self,
        chat_agent,
        mock_specialized_agents,
        mock_chat_service,
        mock_memory_service,
    ):
        """Test message processing with agent routing."""
        message = "I need to book a flight to Paris"
        context = {"user_id": "123", "session_id": "session_456"}

        chat_agent.memory_service = mock_memory_service
        chat_agent.chat_service = mock_chat_service

        # Mock the routing
        with patch.object(chat_agent, "detect_intent") as mock_detect:
            mock_detect.return_value = {
                "primary_intent": "flight",
                "confidence": 0.9,
                "requires_routing": True,
                "all_scores": {"flight": 3},
            }

            with patch.object(chat_agent, "route_to_agent") as mock_route:
                mock_route.return_value = {
                    "content": "Flight booked successfully",
                    "status": "success",
                }

                result = await chat_agent.process_message(message, context)

                assert "routed_to" in result
                assert "routing_confidence" in result
                assert result["routed_to"] == "flight"
                assert result["routing_confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_process_message_direct_handling(
        self, chat_agent, mock_chat_service, mock_memory_service
    ):
        """Test message processing with direct handling."""
        message = "Hello, how are you?"
        context = {"user_id": "123"}

        chat_agent.memory_service = mock_memory_service
        chat_agent.chat_service = mock_chat_service

        # Mock low confidence intent
        with patch.object(chat_agent, "detect_intent") as mock_detect:
            mock_detect.return_value = {
                "primary_intent": "general",
                "confidence": 0.3,
                "requires_routing": False,
                "all_scores": {},
            }

            # Mock the parent run method
            with patch("tripsage.agents.base.BaseAgent.run") as mock_run:
                mock_run.return_value = {
                    "content": "Hello! I'm here to help with your travel planning.",
                    "status": "success",
                }

                result = await chat_agent.process_message(message, context)

                assert "intent_detected" in result
                assert "handled_by" in result
                assert result["handled_by"] == "chat_agent"

    @pytest.mark.asyncio
    async def test_process_message_session_creation(
        self, chat_agent, mock_chat_service, mock_memory_service
    ):
        """Test message processing with automatic session creation."""
        message = "Hello"
        context = {"user_id": "123"}  # No session_id

        chat_agent.memory_service = mock_memory_service
        chat_agent.chat_service = mock_chat_service

        # Mock session creation
        mock_chat_service.create_chat_session.return_value = {
            "session_id": "new_session_123",
            "user_id": 123,
        }

        with patch.object(chat_agent, "detect_intent") as mock_detect:
            mock_detect.return_value = {
                "primary_intent": "general",
                "confidence": 0.3,
                "requires_routing": False,
                "all_scores": {},
            }

            with patch("tripsage.agents.base.BaseAgent.run") as mock_run:
                mock_run.return_value = {"content": "Hello!", "status": "success"}

                result = await chat_agent.process_message(message, context)

                assert result["session_id"] == "new_session_123"

    @pytest.mark.asyncio
    async def test_run_with_tools(self, chat_agent):
        """Test run_with_tools method."""
        message = "Test message"
        context = {"user_id": "123"}
        available_tools = ["weather", "maps"]

        with patch.object(chat_agent, "process_message") as mock_process:
            mock_process.return_value = {"content": "Response", "status": "success"}

            result = await chat_agent.run_with_tools(message, context, available_tools)

            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            call_context = call_args[1]

            assert call_context["available_tools"] == available_tools
            assert call_context["tool_calling_enabled"] is True

    @pytest.mark.asyncio
    async def test_route_request_high_confidence(self, chat_agent):
        """Test route_request with high confidence intent."""
        message = "Book a flight to Paris"
        session_id = "session_123"
        context = {"user_id": "123"}

        with patch.object(chat_agent, "detect_intent") as mock_detect:
            mock_detect.return_value = {
                "primary_intent": "flight",
                "confidence": 0.8,
                "requires_routing": True,
            }

            with patch.object(chat_agent, "_handle_mcp_routing") as mock_mcp_routing:
                mock_mcp_routing.return_value = {
                    "content": "Flight search initiated",
                    "action": "mcp_flight_search",
                }

                result = await chat_agent.route_request(message, session_id, context)

                mock_mcp_routing.assert_called_once()
                assert result["action"] == "mcp_flight_search"

    @pytest.mark.asyncio
    async def test_route_request_low_confidence(self, chat_agent):
        """Test route_request with low confidence intent."""
        message = "Hello there"
        session_id = "session_123"
        context = {"user_id": "123"}

        with patch.object(chat_agent, "detect_intent") as mock_detect:
            mock_detect.return_value = {
                "primary_intent": "general",
                "confidence": 0.3,
                "requires_routing": False,
            }

            with patch.object(chat_agent, "_handle_direct_conversation") as mock_direct:
                mock_direct.return_value = {
                    "content": "Hello! How can I help you?",
                    "status": "success",
                }

                result = await chat_agent.route_request(message, session_id, context)

                mock_direct.assert_called_once()
                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_route_request_failure(self, chat_agent):
        """Test route_request error handling."""
        message = "Test message"
        session_id = "session_123"

        with patch.object(
            chat_agent,
            "detect_intent",
            side_effect=Exception("Intent detection failed"),
        ):
            with pytest.raises(ChatAgentError, match="Request routing failed"):
                await chat_agent.route_request(message, session_id)

    @pytest.mark.asyncio
    async def test_handle_flight_request_mcp(self, chat_agent):
        """Test MCP flight request handling."""
        message = "Book a flight to Paris"
        context = {"session_id": "session_123"}

        result = await chat_agent._handle_flight_request_mcp(message, context)

        assert result["intent"] == "flight_search"
        assert result["action"] == "mcp_flight_search"
        assert result["mcp_service"] == "duffel_flights"
        assert result["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_handle_accommodation_request_mcp(self, chat_agent):
        """Test MCP accommodation request handling."""
        message = "Find a hotel in Paris"
        context = {"session_id": "session_123"}

        result = await chat_agent._handle_accommodation_request_mcp(message, context)

        assert result["intent"] == "accommodation_search"
        assert result["action"] == "mcp_accommodation_search"
        assert result["mcp_service"] == "airbnb"
        assert result["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_handle_weather_request_mcp(self, chat_agent):
        """Test MCP weather request handling."""
        message = "What's the weather in Tokyo?"
        context = {"session_id": "session_123"}

        result = await chat_agent._handle_weather_request_mcp(message, context)

        assert result["intent"] == "weather_check"
        assert result["action"] == "mcp_weather_check"
        assert result["mcp_service"] == "weather"
        assert result["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_handle_maps_request_mcp(self, chat_agent):
        """Test MCP maps request handling."""
        message = "How do I get to the airport?"
        context = {"session_id": "session_123"}

        result = await chat_agent._handle_maps_request_mcp(message, context)

        assert result["intent"] == "location_info"
        assert result["action"] == "mcp_location_lookup"
        assert result["mcp_service"] == "google_maps"
        assert result["status"] == "ready_for_tool_call"

    @pytest.mark.asyncio
    async def test_call_mcp_tools_success(self, chat_agent, mock_chat_service):
        """Test successful MCP tool calling."""
        tool_calls = [
            {"tool": "weather", "params": {"location": "Tokyo"}},
            {"tool": "maps", "params": {"query": "restaurants"}},
        ]

        chat_agent.chat_service = mock_chat_service
        mock_chat_service.execute_parallel_tools.return_value = {
            "total_calls": 2,
            "success_count": 2,
            "results": {"weather": {"temp": 22}, "maps": {"count": 5}},
        }

        result = await chat_agent.call_mcp_tools(tool_calls)

        assert result["status"] == "success"
        assert result["execution_count"] == 2
        assert "tool_call_results" in result

    @pytest.mark.asyncio
    async def test_call_mcp_tools_failure(self, chat_agent, mock_chat_service):
        """Test MCP tool calling failure."""
        tool_calls = [{"tool": "weather", "params": {}}]

        chat_agent.chat_service = mock_chat_service
        mock_chat_service.execute_parallel_tools.side_effect = Exception(
            "Tool execution failed"
        )

        with pytest.raises(ChatAgentError, match="MCP tool calling failed"):
            await chat_agent.call_mcp_tools(tool_calls)

    @pytest.mark.asyncio
    async def test_create_chat_session_mcp_success(self, chat_agent, mock_chat_service):
        """Test successful MCP chat session creation."""
        chat_agent.chat_service = mock_chat_service

        result = await chat_agent.create_chat_session_mcp(
            user_id=123, metadata={"source": "test"}
        )

        assert result["session_id"] == "session_123"
        assert result["user_id"] == 1
        mock_chat_service.create_chat_session.assert_called_once_with(
            123, {"source": "test"}
        )

    @pytest.mark.asyncio
    async def test_create_chat_session_mcp_failure(self, chat_agent, mock_chat_service):
        """Test MCP chat session creation failure."""
        chat_agent.chat_service = mock_chat_service
        mock_chat_service.create_chat_session.side_effect = Exception(
            "Session creation failed"
        )

        with pytest.raises(ChatAgentError, match="Session creation failed"):
            await chat_agent.create_chat_session_mcp(user_id=123)

    @pytest.mark.asyncio
    async def test_save_message_mcp_success(self, chat_agent, mock_chat_service):
        """Test successful MCP message saving."""
        chat_agent.chat_service = mock_chat_service

        result = await chat_agent.save_message_mcp(
            session_id="session_123",
            role="user",
            content="Hello",
            metadata={"timestamp": "2024-01-01T00:00:00Z"},
        )

        assert result["message_id"] == "msg_123"
        mock_chat_service.save_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_message_mcp_failure(self, chat_agent, mock_chat_service):
        """Test MCP message saving failure."""
        chat_agent.chat_service = mock_chat_service
        mock_chat_service.save_message.side_effect = Exception("Message save failed")

        with pytest.raises(ChatAgentError, match="Message saving failed"):
            await chat_agent.save_message_mcp(
                session_id="session_123", role="user", content="Hello"
            )

    @pytest.mark.asyncio
    async def test_get_chat_history_mcp_success(self, chat_agent, mock_chat_service):
        """Test successful MCP chat history retrieval."""
        chat_agent.chat_service = mock_chat_service
        mock_chat_service.get_chat_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        result = await chat_agent.get_chat_history_mcp(
            "session_123", limit=10, offset=0
        )

        assert len(result) == 2
        assert result[0]["role"] == "user"
        mock_chat_service.get_chat_history.assert_called_once_with("session_123", 10, 0)

    @pytest.mark.asyncio
    async def test_get_chat_history_mcp_failure(self, chat_agent, mock_chat_service):
        """Test MCP chat history retrieval failure."""
        chat_agent.chat_service = mock_chat_service
        mock_chat_service.get_chat_history.side_effect = Exception(
            "History retrieval failed"
        )

        with pytest.raises(ChatAgentError, match="History retrieval failed"):
            await chat_agent.get_chat_history_mcp("session_123")

    @pytest.mark.asyncio
    async def test_end_chat_session_mcp_success(self, chat_agent, mock_chat_service):
        """Test successful MCP chat session ending."""
        chat_agent.chat_service = mock_chat_service

        result = await chat_agent.end_chat_session_mcp("session_123")

        assert result is True
        mock_chat_service.end_chat_session.assert_called_once_with("session_123")

    @pytest.mark.asyncio
    async def test_end_chat_session_mcp_failure(self, chat_agent, mock_chat_service):
        """Test MCP chat session ending failure."""
        chat_agent.chat_service = mock_chat_service
        mock_chat_service.end_chat_session.side_effect = Exception("Session end failed")

        with pytest.raises(ChatAgentError, match="Session ending failed"):
            await chat_agent.end_chat_session_mcp("session_123")


class TestChatAgentErrorHandling:
    """Tests for ChatAgent error handling."""

    @pytest.fixture
    def minimal_chat_agent(self):
        """Create a minimal ChatAgent for error testing."""
        with patch("tripsage.agents.chat.MCPManager"):
            with patch("tripsage.agents.chat.ChatOrchestrationService"):
                with patch("tripsage.agents.chat.TripSageMemoryService"):
                    # Mock all agent initializations to avoid import errors
                    with patch(
                        "tripsage.agents.chat.FlightAgent",
                        side_effect=Exception("Agent init failed"),
                    ):
                        with patch(
                            "tripsage.agents.chat.AccommodationAgent",
                            side_effect=Exception("Agent init failed"),
                        ):
                            with patch(
                                "tripsage.agents.chat.BudgetAgent",
                                side_effect=Exception("Agent init failed"),
                            ):
                                with patch(
                                    "tripsage.agents.chat.DestinationResearchAgent",
                                    side_effect=Exception("Agent init failed"),
                                ):
                                    with patch(
                                        "tripsage.agents.chat.ItineraryAgent",
                                        side_effect=Exception("Agent init failed"),
                                    ):
                                        with patch(
                                            "tripsage.agents.chat.TravelAgent",
                                            side_effect=Exception("Agent init failed"),
                                        ):
                                            return ChatAgent()

    @pytest.mark.asyncio
    async def test_route_to_agent_missing_agent(self, minimal_chat_agent):
        """Test routing when specialized agent is missing."""
        intent = {"primary_intent": "flight", "confidence": 0.9}
        message = "Book a flight"
        context = {"user_id": "123"}

        # Agent should not have specialized agents due to initialization failures
        assert not hasattr(minimal_chat_agent, "flight_agent")

        # Should fallback to direct handling
        with patch("tripsage.agents.base.BaseAgent.run") as mock_run:
            mock_run.return_value = {
                "content": "Fallback response",
                "status": "success",
            }

            result = await minimal_chat_agent.route_to_agent(intent, message, context)

            # Should fallback since no travel agent either
            assert "status" in result

    def test_chat_agent_error_inheritance(self):
        """Test ChatAgentError inheritance."""
        error = ChatAgentError("Test error")

        assert isinstance(error, Exception)
        assert str(error) == "Test error"
