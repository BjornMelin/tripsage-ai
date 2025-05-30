"""
Tests for the Agent Handoffs functionality.

This module tests the handoff capabilities of agents, including
both full handoffs and delegations between different agent types.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.base import BaseAgent
from tripsage.agents.travel import TravelAgent


@pytest.fixture
def mock_runner():
    """Mock for the OpenAI Agents SDK Runner."""
    mock = MagicMock()
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_agent_sdk():
    """Mock for the OpenAI Agents SDK Agent."""
    mock = MagicMock()
    return mock


@pytest.fixture
def target_agent_class():
    """Mock agent class for testing handoffs."""

    class MockTargetAgent(BaseAgent):
        """Mock target agent class."""

        def __init__(
            self,
            name="Target Agent",
            instructions="Target instructions",
            model=None,
            temperature=None,
        ):
            super().__init__(
                name=name,
                instructions=instructions,
                model=model,
                temperature=temperature,
            )

    return MockTargetAgent


class TestAgentHandoffs:
    """Tests for the agent handoffs functionality."""

    @patch("agents.Agent")
    @patch("agents.Runner")
    def test_create_handoff_tool(
        self, mock_runner_cls, mock_agent_cls, target_agent_class
    ):
        """Test creating a handoff tool that transfers control to another agent."""
        # Setup mocks
        mock_agent_cls.return_value = MagicMock()
        mock_runner_cls.return_value = MagicMock()

        # Create handoff tool
        tool_name = "test_handoff"
        description = "Test handoff description"
        handoff_tool = create_handoff_tool(
            target_agent_class,
            tool_name,
            description,
            context_filter=["user_id", "session_id"],
        )

        # Verify tool metadata
        assert handoff_tool.__name__ == tool_name
        assert handoff_tool.__doc__ == description
        assert hasattr(handoff_tool, "__is_handoff_tool__")
        assert handoff_tool.__is_handoff_tool__ is True
        assert hasattr(handoff_tool, "__target_agent__")
        assert handoff_tool.__target_agent__ == "MockTargetAgent"

    @patch("agents.Agent")
    @patch("agents.Runner")
    def test_create_delegation_tool(
        self, mock_runner_cls, mock_agent_cls, target_agent_class
    ):
        """Test creating a delegation tool that uses another agent as a tool."""
        # Setup mocks
        mock_agent_cls.return_value = MagicMock()
        mock_runner_cls.return_value = MagicMock()

        # Create delegation tool
        tool_name = "test_delegation"
        description = "Test delegation description"
        delegation_tool = create_delegation_tool(
            target_agent_class,
            tool_name,
            description,
            return_key="result",
            context_filter=["user_id", "session_id"],
        )

        # Verify tool metadata
        assert delegation_tool.__name__ == tool_name
        assert delegation_tool.__doc__ == description
        assert hasattr(delegation_tool, "__is_delegation_tool__")
        assert delegation_tool.__is_delegation_tool__ is True
        assert hasattr(delegation_tool, "__target_agent__")
        assert delegation_tool.__target_agent__ == "MockTargetAgent"

    @patch("agents.Agent")
    @patch("agents.Runner")
    def test_register_handoff_tools(
        self, mock_runner_cls, mock_agent_cls, target_agent_class
    ):
        """Test registering multiple handoff tools with an agent."""
        # Setup mocks
        mock_agent_cls.return_value = MagicMock()
        mock_runner_cls.return_value = MagicMock()

        # Create agent
        agent = BaseAgent(name="Test Agent", instructions="Test instructions")

        # Define handoff targets
        handoff_configs = {
            "test_handoff_1": {
                "agent_class": target_agent_class,
                "description": "Test handoff 1 description",
                "context_filter": ["user_id", "session_id"],
            },
            "test_handoff_2": {
                "agent_class": target_agent_class,
                "description": "Test handoff 2 description",
            },
        }

        # Register handoff tools
        count = register_handoff_tools(agent, handoff_configs)

        # Verify tools were registered
        assert count == 2
        assert len(agent._handoff_tools) == 2
        assert "test_handoff_1" in agent._handoff_tools
        assert "test_handoff_2" in agent._handoff_tools

    @patch("agents.Agent")
    @patch("agents.Runner")
    def test_register_delegation_tools(
        self, mock_runner_cls, mock_agent_cls, target_agent_class
    ):
        """Test registering multiple delegation tools with an agent."""
        # Setup mocks
        mock_agent_cls.return_value = MagicMock()
        mock_runner_cls.return_value = MagicMock()

        # Create agent
        agent = BaseAgent(name="Test Agent", instructions="Test instructions")

        # Define delegation targets
        delegation_configs = {
            "test_delegation_1": {
                "agent_class": target_agent_class,
                "description": "Test delegation 1 description",
                "return_key": "result",
                "context_filter": ["user_id", "session_id"],
            },
            "test_delegation_2": {
                "agent_class": target_agent_class,
                "description": "Test delegation 2 description",
            },
        }

        # Register delegation tools
        count = register_delegation_tools(agent, delegation_configs)

        # Verify tools were registered
        assert count == 2
        assert len(agent._delegation_tools) == 2
        assert "test_delegation_1" in agent._delegation_tools
        assert "test_delegation_2" in agent._delegation_tools


class TestHandoffExecution:
    """Tests for actual execution of handoffs between agents."""

    @patch("agents.Agent")
    @patch("agents.Runner")
    async def test_agent_handoff_detection(
        self, mock_runner_cls, mock_agent_cls, target_agent_class
    ):
        """Test that the agent correctly detects and processes handoffs."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner

        # Create a result with a handoff
        mock_result = MagicMock()
        mock_result.final_output = "Handing off to specialist agent"
        mock_result.tool_calls = [
            {
                "name": "hand_off_to_specialist",
                "arguments": {
                    "query": "Specialist query",
                    "context": {"user_id": "test_user"},
                },
            }
        ]
        mock_runner.run = AsyncMock(return_value=mock_result)

        # Create main agent
        agent = BaseAgent(name="Main Agent", instructions="Main instructions")

        # Register a handoff tool
        handoff_tool = create_handoff_tool(
            target_agent_class,
            "hand_off_to_specialist",
            "Handoff to specialist agent",
        )
        agent._register_tool(handoff_tool)

        # Run the agent
        response = await agent.run("Test input", context={"user_id": "test_user"})

        # Verify handoff was detected
        assert response["status"] == "handoff"
        assert "handoff_target" in response
        assert "handoff_tool" in response
        assert response["handoff_tool"] == "hand_off_to_specialist"

    @patch("agents.Agent")
    @patch("agents.Runner")
    async def test_travel_agent_handoff_processing(
        self, mock_runner_cls, mock_agent_cls
    ):
        """Test that TravelAgent correctly processes handoffs with specialist agents."""
        # Setup mocks for TravelAgent
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent

        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner

        # Create a result with a handoff
        mock_result = MagicMock()
        mock_result.final_output = "Let me connect you with our flight specialist."
        mock_result.tool_calls = [
            {
                "name": "hand_off_to_flight_agent",
                "arguments": {
                    "query": "Find flights from NYC to LAX",
                    "context": {"user_id": "test_user"},
                },
            }
        ]
        mock_runner.run = AsyncMock(return_value=mock_result)

        # Mock the flight agent tool
        mock_flight_result = {
            "content": "Here are the flight options...",
            "status": "success",
            "handoff_success": True,
        }

        # Create TravelAgent with mocked dependencies
        with patch("tripsage.agents.travel.FlightAgent"):
            with patch("tripsage.agents.travel.AccommodationAgent"):
                with patch("tripsage.agents.travel.BudgetAgent"):
                    with patch("tripsage.agents.travel.DestinationResearchAgent"):
                        with patch("tripsage.agents.travel.ItineraryAgent"):
                            # Mock the tool invocation
                            mock_tool = AsyncMock(return_value=mock_flight_result)

                            # Create the travel agent
                            agent = TravelAgent(
                                name="Travel Agent", instructions="Travel instructions"
                            )

                            # Replace the tool with our mock
                            agent._handoff_tools["hand_off_to_flight_agent"] = {
                                "target_agent": "FlightAgent",
                                "tool": mock_tool,
                            }

                            # Run the agent
                            response = await agent.run(
                                "I need to book a flight",
                                context={"user_id": "test_user"},
                            )

                            # Process the handoff
                            handoff_response = await agent.process_handoff_result(
                                response
                            )

                            # Verify handoff processing
                            assert (
                                handoff_response["content"]
                                == "Here are the flight options..."
                            )
                            assert handoff_response["status"] == "success"
                            assert handoff_response["handoff_success"] is True

                            # Verify the tool was called with expected arguments
                            mock_tool.assert_called_once()
                            args = mock_tool.call_args
                            assert "query" in args[1]
                            assert "context" in args[1]
                            assert args[1]["context"]["is_handoff"] is True
                            assert (
                                args[1]["context"]["handoff_source"] == "Travel Agent"
                            )
