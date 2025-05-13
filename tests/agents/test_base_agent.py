"""
Tests for the BaseAgent class.

This module tests the BaseAgent implementation that serves as the foundation
for all TripSage agents, including its integration with the OpenAI Agents SDK.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import RunContext, RunResult
from src.agents.base_agent import BaseAgent


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
def mock_memory_tools():
    """Mock for the memory tools module."""
    mock = MagicMock()
    # Create mock tool functions
    mock.get_knowledge_graph = MagicMock()
    mock.search_knowledge_graph = MagicMock()
    mock.get_entity_details = MagicMock()
    mock.create_knowledge_entities = MagicMock()
    mock.create_knowledge_relations = MagicMock()
    mock.add_entity_observations = MagicMock()
    mock.delete_knowledge_entities = MagicMock()
    mock.delete_knowledge_relations = MagicMock()
    mock.delete_entity_observations = MagicMock()
    mock.initialize_agent_memory = MagicMock()
    mock.update_agent_memory = MagicMock()
    mock.save_session_summary = MagicMock()
    return mock


@pytest.fixture
def mock_mcp_client():
    """Mock for an MCP client."""
    mock = MagicMock()
    mock.server_name = "TestMCP"
    mock.list_tools_sync = MagicMock(return_value=["tool1", "tool2"])
    mock.get_tool_metadata_sync = MagicMock(
        return_value={"description": "Test tool description"}
    )
    mock.call_tool = AsyncMock(return_value={"result": "success"})
    return mock


class TestBaseAgent:
    """Tests for the BaseAgent class."""

    @patch("src.agents.base_agent.Agent")
    @patch("src.agents.base_agent.Runner")
    def test_agent_initialization(
        self, mock_runner_cls, mock_agent_cls, mock_memory_tools
    ):
        """Test that the agent initializes with proper configuration."""
        # Setup mocks
        with patch("src.agents.base_agent.memory_tools", mock_memory_tools):
            mock_agent_cls.return_value = MagicMock()
            mock_runner_cls.return_value = MagicMock()

            # Define test parameters
            name = "Test Agent"
            instructions = "Test instructions"
            model = "gpt-4"
            temperature = 0.3
            metadata = {"agent_type": "test_agent", "version": "1.0.0"}

            # Create agent
            agent = BaseAgent(
                name=name,
                instructions=instructions,
                model=model,
                temperature=temperature,
                metadata=metadata,
            )

            # Verify agent has expected configuration
            assert agent.name == name
            assert agent.instructions == instructions
            assert agent.model == model
            assert agent.temperature == temperature
            assert agent.metadata == metadata

            # Verify OpenAI Agent was created with correct parameters
            mock_agent_cls.assert_called_once()
            args = mock_agent_cls.call_args
            assert args[1]["name"] == name
            assert args[1]["instructions"] == instructions
            assert args[1]["model"] == model
            assert args[1]["temperature"] == temperature
            assert len(args[1]["tools"]) > 0  # Default tools should be registered

            # Verify Runner was created
            mock_runner_cls.assert_called_once()
            assert hasattr(agent, "runner")

    @patch("src.agents.base_agent.Agent")
    @patch("src.agents.base_agent.Runner")
    async def test_agent_run(
        self, mock_runner_cls, mock_agent_cls, mock_runner, mock_memory_tools
    ):
        """Test that the agent run method correctly uses the Runner."""
        # Setup mocks
        with patch("src.agents.base_agent.memory_tools", mock_memory_tools):
            mock_agent = MagicMock()
            mock_agent_cls.return_value = mock_agent
            mock_runner_cls.return_value = mock_runner

            # Mock runner response
            mock_result = MagicMock(spec=RunResult)
            mock_result.output = "Test response"
            mock_result.tool_calls = []
            mock_result.handoffs = {}
            mock_runner.run.return_value = mock_result

            # Create agent
            agent = BaseAgent(name="Test Agent", instructions="Test instructions")

            # Mock session memory functions
            with (
                patch("src.agents.base_agent.initialize_session_memory"),
                patch("src.agents.base_agent.store_session_summary"),
            ):
                # Execute run
                user_input = "Test input"
                context = {"key": "value"}
                result = await agent.run(user_input, context=context)

                # Verify runner was called with correct parameters
                mock_runner.run.assert_called_once()
                args = mock_runner.run.call_args
                assert args[1]["agent"] == mock_agent
                assert args[1]["input"] == user_input
                assert isinstance(args[1]["context"], RunContext)

                # Verify context was passed correctly
                run_context = args[1]["context"]
                assert run_context.key == "value"

                # Verify result
                assert result["content"] == "Test response"
                assert result["status"] == "success"
                assert "tool_calls" in result
                assert "handoffs" in result

    @patch("src.agents.base_agent.Agent")
    @patch("src.agents.base_agent.Runner")
    def test_register_tool(self, mock_runner_cls, mock_agent_cls, mock_memory_tools):
        """Test registering custom tools."""
        # Setup mocks
        with patch("src.agents.base_agent.memory_tools", mock_memory_tools):
            mock_agent_cls.return_value = MagicMock()
            mock_runner_cls.return_value = MagicMock()

            # Create agent
            agent = BaseAgent(name="Test Agent", instructions="Test instructions")

            # Create a custom tool
            def custom_tool():
                """Custom tool for testing."""
                return {"result": "success"}

            # Register the tool
            agent._register_tool(custom_tool)

            # Verify tool was added to tools list
            assert custom_tool in agent._tools

    @patch("src.agents.base_agent.Agent")
    @patch("src.agents.base_agent.Runner")
    def test_register_mcp_client_tools(
        self, mock_runner_cls, mock_agent_cls, mock_memory_tools, mock_mcp_client
    ):
        """Test registering tools from an MCP client."""
        # Setup mocks
        with patch("src.agents.base_agent.memory_tools", mock_memory_tools):
            mock_agent_cls.return_value = MagicMock()
            mock_runner_cls.return_value = MagicMock()

            # Create agent
            agent = BaseAgent(name="Test Agent", instructions="Test instructions")

            # Register MCP client tools
            agent._register_mcp_client_tools(mock_mcp_client, prefix="test_")

            # Verify client tools were queried
            mock_mcp_client.list_tools_sync.assert_called_once()
            assert (
                mock_mcp_client.get_tool_metadata_sync.call_count == 2
            )  # For tool1 and tool2

            # Verify tools were added
            # We can't directly access the wrapped functions, but check the length
            # 13 default tools (including echo) + 2 MCP tools = 15 total
            assert len(agent._tools) == 15

    @patch("src.agents.base_agent.Agent")
    @patch("src.agents.base_agent.Runner")
    async def test_echo_tool(self, mock_runner_cls, mock_agent_cls, mock_memory_tools):
        """Test the echo tool functionality."""
        # Setup mocks
        with patch("src.agents.base_agent.memory_tools", mock_memory_tools):
            mock_agent_cls.return_value = MagicMock()
            mock_runner_cls.return_value = MagicMock()

            # Create agent
            agent = BaseAgent(name="Test Agent", instructions="Test instructions")

            # Test echo tool
            message = "This is a test message"
            result = await agent.echo({"message": message})

            # Verify echo result
            assert "content" in result
            assert result["content"] == message
            assert "timestamp" in result
