"""
Unit tests for ChatAgent using proper pydantic settings isolation.

This test file demonstrates best practices for testing with pydantic settings:
1. Environment variable isolation using test fixtures
2. Proper mocking of dependencies without import-time issues
3. Clean test data and assertions
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import after environment is set up in conftest.py
from tests.test_settings import mock_settings_patch


class TestChatAgentIntentDetection:
    """Test intent detection logic in isolation."""

    def test_flight_intent_detection(self):
        """Test flight intent detection with various phrases."""

        # Test intent detection logic without importing the full ChatAgent
        def detect_intent_logic(message: str) -> dict:
            """Simplified version of ChatAgent.detect_intent logic."""
            message_lower = message.lower()

            intent_patterns = {
                "flight": {
                    "keywords": ["flight", "fly", "airline", "airport", "ticket"],
                    "patterns": [
                        r"\bfly\s+to\b",
                        r"\bflight\s+from\b",
                        r"\bbook.*flight\b",
                    ],
                    "weight": 0.0,
                }
            }

            for intent, config in intent_patterns.items():
                confidence = 0.0

                # Check keywords
                for keyword in config["keywords"]:
                    if keyword in message_lower:
                        confidence += 0.3

                # Simple pattern matching (without regex for isolation)
                if "fly to" in message_lower or "flight from" in message_lower:
                    confidence += 0.4

                if confidence > 0.5:
                    return {"intent": intent, "confidence": confidence}

            return {"intent": "general", "confidence": 0.1}

        # Test cases
        test_cases = [
            ("I want to fly to Paris", "flight"),
            ("Book a flight from NYC to LAX", "flight"),
            ("What's the weather like?", "general"),
            ("Find me airline tickets", "flight"),
            ("How are you doing?", "general"),
        ]

        for message, expected_intent in test_cases:
            result = detect_intent_logic(message)
            assert result["intent"] == expected_intent, f"Failed for message: {message}"


class TestChatAgentWithMocks:
    """Test ChatAgent with proper dependency mocking."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        with mock_settings_patch():
            yield

    def test_chat_agent_initialization(self):
        """Test ChatAgent can be initialized with mocked dependencies."""
        with patch("tripsage.agents.chat.SpecializedAgents") as mock_agents:
            with patch("tripsage.agents.chat.openai.OpenAI") as mock_openai:
                # Mock the specialized agents
                mock_flight_agent = AsyncMock()
                mock_accommodation_agent = AsyncMock()
                mock_planning_agent = AsyncMock()

                mock_agents.return_value = MagicMock(
                    flight_agent=mock_flight_agent,
                    accommodation_agent=mock_accommodation_agent,
                    planning_agent=mock_planning_agent,
                )

                # Mock OpenAI client
                mock_openai_client = AsyncMock()
                mock_openai.return_value = mock_openai_client

                # Import and initialize after mocking
                from tripsage.agents.chat import ChatAgent

                agent = ChatAgent()

                # Verify initialization
                assert agent is not None
                assert hasattr(agent, "specialized_agents")
                assert hasattr(agent, "client")

    def test_intent_detection_with_real_agent(self):
        """Test intent detection using the real ChatAgent class."""
        with patch("tripsage.agents.chat.SpecializedAgents"):
            with patch("tripsage.agents.chat.openai.OpenAI"):
                from tripsage.agents.chat import ChatAgent

                agent = ChatAgent()

                # Test flight intent
                result = agent.detect_intent("I want to book a flight to Tokyo")
                assert result["intent"] == "flight"
                assert result["confidence"] > 0.5

                # Test accommodation intent
                result = agent.detect_intent("Find me a hotel in Paris")
                assert result["intent"] == "accommodation"
                assert result["confidence"] > 0.5

                # Test general intent
                result = agent.detect_intent("Hello, how are you?")
                assert result["intent"] == "general"

    @pytest.mark.asyncio
    async def test_process_with_tool_calls(self):
        """Test processing a message that should result in tool calls."""
        with patch("tripsage.agents.chat.SpecializedAgents") as mock_agents:
            with patch("tripsage.agents.chat.openai.OpenAI") as mock_openai:
                # Mock specialized agents
                mock_flight_agent = AsyncMock()
                mock_flight_agent.handle_request.return_value = {
                    "flights": [{"from": "NYC", "to": "LAX", "price": "$200"}],
                    "message": "Found 1 flight option",
                }

                mock_agents.return_value = MagicMock(
                    flight_agent=mock_flight_agent,
                    accommodation_agent=AsyncMock(),
                    planning_agent=AsyncMock(),
                )

                # Mock OpenAI response with tool calls
                mock_response = MagicMock()
                mock_choice = MagicMock()
                mock_message = MagicMock()

                # Mock tool call
                mock_tool_call = MagicMock()
                mock_tool_call.id = "call_123"
                mock_tool_call.type = "function"
                mock_tool_call.function.name = "search_flights"
                mock_tool_call.function.arguments = (
                    '{"origin": "NYC", "destination": "LAX"}'
                )

                mock_message.tool_calls = [mock_tool_call]
                mock_message.content = None
                mock_choice.message = mock_message
                mock_response.choices = [mock_choice]

                mock_openai_client = AsyncMock()
                mock_openai_client.chat.completions.create.return_value = mock_response
                mock_openai.return_value = mock_openai_client

                from tripsage.agents.chat import ChatAgent

                agent = ChatAgent()

                # Test processing
                result = await agent.process(
                    message="Find flights from NYC to LAX",
                    user_id="test_user",
                    session_id="test_session",
                )

                # Verify result structure
                assert "response" in result
                assert "tool_calls" in result
                assert len(result["tool_calls"]) == 1

                # Verify tool call details
                tool_call = result["tool_calls"][0]
                assert tool_call["id"] == "call_123"
                assert tool_call["name"] == "search_flights"
                assert "origin" in tool_call["arguments"]
                assert tool_call["arguments"]["origin"] == "NYC"


class TestChatAgentRateLimiting:
    """Test rate limiting functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        with mock_settings_patch():
            yield

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self):
        """Test that rate limiting is enforced for tool calls."""
        with patch("tripsage.agents.chat.SpecializedAgents"):
            with patch("tripsage.agents.chat.openai.OpenAI"):
                with patch("tripsage.utils.cache.web_cache") as mock_cache:
                    # Mock cache to simulate hitting rate limit
                    mock_cache.get.return_value = 6  # Over the limit of 5
                    mock_cache.set = AsyncMock()
                    mock_cache.incr = AsyncMock(return_value=6)

                    from tripsage.agents.chat import ChatAgent

                    agent = ChatAgent()

                    # Test rate limiting
                    is_allowed = await agent._check_rate_limit("test_user")
                    assert not is_allowed

                    # Test under limit
                    mock_cache.get.return_value = 3  # Under the limit
                    mock_cache.incr.return_value = 4

                    is_allowed = await agent._check_rate_limit("test_user")
                    assert is_allowed


@pytest.mark.integration
class TestChatAgentIntegration:
    """Integration tests for ChatAgent."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        with mock_settings_patch():
            yield

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow from message to response."""
        with patch("tripsage.agents.chat.SpecializedAgents") as mock_agents:
            with patch("tripsage.agents.chat.openai.OpenAI") as mock_openai:
                # Set up comprehensive mocks
                mock_flight_agent = AsyncMock()
                mock_flight_agent.handle_request.return_value = {
                    "flights": [{"id": "FL123", "price": "$200"}],
                    "message": "Found flights",
                }

                mock_agents.return_value = MagicMock(
                    flight_agent=mock_flight_agent,
                    accommodation_agent=AsyncMock(),
                    planning_agent=AsyncMock(),
                )

                # Mock OpenAI for both initial call and follow-up
                mock_openai_client = AsyncMock()

                # First call - returns tool call
                mock_tool_response = MagicMock()
                mock_tool_choice = MagicMock()
                mock_tool_message = MagicMock()
                mock_tool_call = MagicMock()
                mock_tool_call.id = "call_123"
                mock_tool_call.function.name = "search_flights"
                mock_tool_call.function.arguments = '{"origin": "NYC"}'
                mock_tool_message.tool_calls = [mock_tool_call]
                mock_tool_message.content = None
                mock_tool_choice.message = mock_tool_message
                mock_tool_response.choices = [mock_tool_choice]

                # Second call - returns final response
                mock_final_response = MagicMock()
                mock_final_choice = MagicMock()
                mock_final_message = MagicMock()
                mock_final_message.tool_calls = []
                mock_final_message.content = "I found some flights for you!"
                mock_final_choice.message = mock_final_message
                mock_final_response.choices = [mock_final_choice]

                # Set up side effect for multiple calls
                mock_openai_client.chat.completions.create.side_effect = [
                    mock_tool_response,
                    mock_final_response,
                ]
                mock_openai.return_value = mock_openai_client

                from tripsage.agents.chat import ChatAgent

                agent = ChatAgent()

                # Test full flow
                result = await agent.process(
                    message="Find me flights from NYC to Paris",
                    user_id="test_user",
                    session_id="test_session",
                )

                # Verify comprehensive result
                assert "response" in result
                assert "tool_calls" in result
                assert result["response"] == "I found some flights for you!"
                assert len(result["tool_calls"]) == 1

                # Verify tool was called
                mock_flight_agent.handle_request.assert_called_once()
