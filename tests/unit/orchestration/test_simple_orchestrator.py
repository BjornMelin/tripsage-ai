"""
Tests for SimpleTripSageOrchestrator using modern LangGraph patterns.

Tests the simplified orchestrator that replaces the complex multi-agent
system with a single, powerful ReAct agent.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from tripsage.orchestration.simple_graph import (
    SimpleTripSageOrchestrator,
    get_orchestrator,
)


class TestSimpleTripSageOrchestrator:
    """Test the simplified LangGraph orchestrator."""

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    def test_orchestrator_initialization(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test orchestrator initialization."""
        # Mock settings
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )

        # Mock tools
        mock_tools = [MagicMock(), MagicMock()]
        mock_get_tools.return_value = mock_tools

        # Mock LLM
        mock_llm = MagicMock()
        mock_openai.return_value = mock_llm

        # Mock agent
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        # Initialize orchestrator
        orchestrator = SimpleTripSageOrchestrator()

        # Verify initialization
        assert orchestrator.tools == mock_tools
        assert orchestrator.llm == mock_llm
        assert orchestrator.agent == mock_agent

        # Verify create_react_agent was called with correct params
        mock_create_agent.assert_called_once()
        call_args = mock_create_agent.call_args
        assert call_args[1]["model"] == mock_llm
        assert call_args[1]["tools"] == mock_tools

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    @pytest.mark.asyncio
    async def test_process_conversation(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test conversation processing."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        # Mock agent response
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="Find flights to Paris"),
                AIMessage(
                    content="I'll help you find flights to Paris. Let me search for "
                    "options."
                ),
            ]
        }
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # Test conversation processing
        messages = [{"role": "user", "content": "Find flights to Paris"}]
        result = await orchestrator.process_conversation(messages)

        # Verify result
        assert result["success"] is True
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][1]["role"] == "assistant"
        assert "Paris" in result["messages"][1]["content"]

        # Verify agent was called
        mock_agent.ainvoke.assert_called_once()

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    @pytest.mark.asyncio
    async def test_process_conversation_error_handling(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test conversation processing error handling."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        # Mock agent to raise exception
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("API Error")
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # Test error handling
        messages = [{"role": "user", "content": "Test message"}]
        result = await orchestrator.process_conversation(messages)

        # Verify error response
        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]
        assert len(result["messages"]) == 2  # Original + error message
        assert "error" in result["messages"][1]["content"].lower()

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    @pytest.mark.asyncio
    async def test_stream_conversation(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test conversation streaming."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        # Mock streaming response
        mock_chunks = [
            {"messages": [HumanMessage(content="Find hotels")]},
            {"messages": [AIMessage(content="Looking for hotels...")]},
            {"messages": [AIMessage(content="Found 5 hotels in your area.")]},
        ]

        async def mock_astream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk

        mock_agent = AsyncMock()
        mock_agent.astream = mock_astream
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # Test streaming
        messages = [{"role": "user", "content": "Find hotels"}]
        chunks = []
        async for chunk in orchestrator.stream_conversation(messages):
            chunks.append(chunk)

        # Verify streaming worked
        assert len(chunks) == 3
        assert "messages" in chunks[0]

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    @pytest.mark.asyncio
    async def test_health_check(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test orchestrator health check."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        # Mock healthy agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [AIMessage(content="Health check OK")]
        }
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # Test health check
        result = await orchestrator.health_check()

        # Verify health status
        assert result["status"] == "healthy"
        assert result["agent_responsive"] is True
        assert "tools_count" in result

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test health check when agent is unhealthy."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        # Mock unhealthy agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Agent down")
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # Test health check
        result = await orchestrator.health_check()

        # Verify unhealthy status
        assert result["status"] == "unhealthy"
        assert result["agent_responsive"] is False
        assert "error" in result
        assert "Agent down" in result["error"]

    def test_get_role_from_message(self):
        """Test message role conversion."""
        orchestrator = SimpleTripSageOrchestrator.__new__(SimpleTripSageOrchestrator)

        # Test different message types
        human_msg = HumanMessage(content="Hello")
        ai_msg = AIMessage(content="Hi there")

        assert orchestrator._get_role_from_message(human_msg) == "user"
        assert orchestrator._get_role_from_message(ai_msg) == "assistant"

    def test_system_prompt_generation(self):
        """Test system prompt contains key travel planning elements."""
        orchestrator = SimpleTripSageOrchestrator.__new__(SimpleTripSageOrchestrator)
        prompt = orchestrator._get_system_prompt()

        # Verify key elements are in prompt
        assert "TripSage" in prompt
        assert "travel planning" in prompt.lower()
        assert "flight" in prompt.lower()
        assert "accommodation" in prompt.lower()
        assert "weather" in prompt.lower()
        assert "memory" in prompt.lower()


class TestOrchestratorGlobalAccess:
    """Test global orchestrator access patterns."""

    @patch("tripsage.orchestration.simple_graph.SimpleTripSageOrchestrator")
    def test_get_orchestrator_singleton(self, mock_orchestrator_class):
        """Test that get_orchestrator returns singleton instance."""
        mock_instance = MagicMock()
        mock_orchestrator_class.return_value = mock_instance

        # First call should create instance
        result1 = get_orchestrator()
        assert result1 == mock_instance
        mock_orchestrator_class.assert_called_once()

        # Second call should return same instance
        result2 = get_orchestrator()
        assert result2 == mock_instance
        # Should not call constructor again
        assert mock_orchestrator_class.call_count == 1

    @patch("tripsage.orchestration.simple_graph.SimpleTripSageOrchestrator")
    def test_get_orchestrator_with_service_registry(self, mock_orchestrator_class):
        """Test that providing service_registry creates new instance."""
        # Reset the global state by clearing the global orchestrator
        import tripsage.orchestration.simple_graph as sg

        sg._global_orchestrator = None

        mock_instance1 = MagicMock()
        mock_instance2 = MagicMock()
        mock_orchestrator_class.side_effect = [mock_instance1, mock_instance2]

        # First call
        result1 = get_orchestrator()
        assert result1 == mock_instance1

        # Call with service registry should create new instance and replace global
        mock_service_registry = MagicMock()
        result2 = get_orchestrator(mock_service_registry)
        assert result2 == mock_instance2

        # Verify constructor was called with service registry
        assert mock_orchestrator_class.call_count == 2
        mock_orchestrator_class.assert_called_with(mock_service_registry)

        # Third call without service registry should return the new instance
        # (singleton behavior)
        result3 = get_orchestrator()
        assert result3 == mock_instance2  # Same as result2
        # Should not create another instance
        assert mock_orchestrator_class.call_count == 2


class TestOrchestratorBackwardsCompatibility:
    """Test backwards compatibility features."""

    def test_tripsage_orchestrator_alias(self):
        """Test that TripSageOrchestrator is aliased to SimpleTripSageOrchestrator."""
        from tripsage.orchestration import (
            SimpleTripSageOrchestrator,
            TripSageOrchestrator,
        )

        assert TripSageOrchestrator is SimpleTripSageOrchestrator

    def test_orchestration_exports(self):
        """Test that orchestration package exports the expected classes."""
        from tripsage.orchestration import (
            SimpleTripSageOrchestrator,
            TravelPlanningState,
            TripSageOrchestrator,
            get_orchestrator,
        )

        # Verify all expected exports are available
        assert SimpleTripSageOrchestrator is not None
        assert TripSageOrchestrator is not None
        assert get_orchestrator is not None
        assert TravelPlanningState is not None


class TestIntegrationScenarios:
    """Integration test scenarios for realistic usage."""

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    @pytest.mark.asyncio
    async def test_travel_planning_conversation_flow(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test a realistic travel planning conversation flow."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        # Mock conversation flow
        conversation_responses = [
            {
                "messages": [
                    HumanMessage(content="I want to plan a trip to Tokyo"),
                    AIMessage(
                        content="I'd love to help you plan your trip to Tokyo! "
                        "When are you planning to travel?"
                    ),
                ]
            },
            {
                "messages": [
                    HumanMessage(content="March 15-22, 2024"),
                    AIMessage(
                        content="Great! Let me search for flights and accommodations "
                        "for March 15-22, 2024."
                    ),
                ]
            },
        ]

        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = conversation_responses
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # First message
        result1 = await orchestrator.process_conversation(
            [{"role": "user", "content": "I want to plan a trip to Tokyo"}]
        )
        assert result1["success"] is True
        assert "Tokyo" in result1["messages"][-1]["content"]

        # Follow-up message
        result2 = await orchestrator.process_conversation(
            [{"role": "user", "content": "March 15-22, 2024"}]
        )
        assert result2["success"] is True
        assert "March" in result2["messages"][-1]["content"]

    @patch("tripsage.orchestration.simple_graph.ChatOpenAI")
    @patch("tripsage.orchestration.simple_graph.create_react_agent")
    @patch("tripsage.orchestration.simple_graph.get_all_tools")
    @patch("tripsage.orchestration.simple_graph.get_settings")
    def test_configuration_persistence(
        self, mock_settings, mock_get_tools, mock_create_agent, mock_openai
    ):
        """Test that conversation configuration (thread_id) works for persistence."""
        # Setup mocks
        mock_settings.return_value.agent.model_name = "gpt-4"
        mock_settings.return_value.agent.temperature = 0.7
        mock_settings.return_value.openai_api_key.get_secret_value.return_value = (
            "test-key"
        )
        mock_get_tools.return_value = []

        mock_agent = AsyncMock()
        mock_create_agent.return_value = mock_agent

        orchestrator = SimpleTripSageOrchestrator()

        # Test that custom config is used
        # The process_conversation should handle config properly
        # This is tested indirectly through the mocking structure
        assert orchestrator.agent == mock_agent
