"""
Comprehensive tests for BaseAgent.

This module provides extensive testing for the base agent functionality
including initialization, tool registration, and core agent operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.base import BaseAgent


class TestBaseAgent:
    """Comprehensive tests for BaseAgent."""

    @pytest.fixture
    def mock_openai_agent(self):
        """Mock OpenAI Agent SDK."""
        mock_agent = MagicMock()
        mock_agent.instructions = "Test instructions"
        mock_agent.model = "gpt-4"
        mock_agent.temperature = 0.7
        return mock_agent

    @pytest.fixture
    def mock_openai_runner(self):
        """Mock OpenAI Runner SDK."""
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock()
        return mock_runner

    @pytest.fixture
    def base_agent(self, mock_openai_agent, mock_openai_runner):
        """Create a BaseAgent instance with mocked dependencies."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = BaseAgent(
                    name="Test Agent",
                    instructions="Test instructions for the agent",
                    model="gpt-4",
                    temperature=0.7,
                )
                return agent

    def test_initialization_basic(self, mock_openai_agent, mock_openai_runner):
        """Test basic BaseAgent initialization."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = BaseAgent(name="Test Agent", instructions="Test instructions")

                assert agent.name == "Test Agent"
                assert agent.instructions == "Test instructions"
                assert agent.model is not None
                assert agent.temperature is not None
                assert agent.metadata == {}
                assert agent._tools == []
                assert agent._handoff_tools == {}
                assert agent._delegation_tools == {}

    def test_initialization_with_metadata(self, mock_openai_agent, mock_openai_runner):
        """Test BaseAgent initialization with metadata."""
        metadata = {"agent_type": "test", "version": "1.0"}

        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = BaseAgent(
                    name="Test Agent",
                    instructions="Test instructions",
                    metadata=metadata,
                )

                assert agent.metadata == metadata

    def test_initialization_openai_sdk_failure(self):
        """Test BaseAgent initialization when OpenAI SDK fails."""
        with patch("agents.Agent", side_effect=ImportError("OpenAI SDK not available")):
            agent = BaseAgent(name="Test Agent", instructions="Test instructions")

            # Should continue without OpenAI SDK
            assert agent.name == "Test Agent"
            assert agent.agent is None
            assert agent.runner is None

    def test_str_representation(self, base_agent):
        """Test string representation of BaseAgent."""
        str_repr = str(base_agent)
        assert "Test Agent" in str_repr
        assert "gpt-4" in str_repr

    def test_repr_representation(self, base_agent):
        """Test repr representation of BaseAgent."""
        repr_str = repr(base_agent)
        assert "BaseAgent" in repr_str
        assert "Test Agent" in repr_str

    def test_register_tool_function(self, base_agent):
        """Test registering a function as a tool."""

        def test_tool(param1: str, param2: int = 10) -> str:
            """Test tool function."""
            return f"Result: {param1} {param2}"

        base_agent.register_tool(test_tool)

        assert len(base_agent._tools) == 1
        assert base_agent._tools[0] == test_tool

    def test_register_tool_object(self, base_agent):
        """Test registering an object as a tool."""
        tool_object = {
            "name": "custom_tool",
            "function": lambda x: f"Custom: {x}",
            "description": "A custom tool",
        }

        base_agent.register_tool(tool_object)

        assert len(base_agent._tools) == 1
        assert base_agent._tools[0] == tool_object

    def test_register_multiple_tools(self, base_agent):
        """Test registering multiple tools."""

        def tool1() -> str:
            return "tool1"

        def tool2() -> str:
            return "tool2"

        base_agent.register_tool(tool1)
        base_agent.register_tool(tool2)

        assert len(base_agent._tools) == 2
        assert tool1 in base_agent._tools
        assert tool2 in base_agent._tools

    def test_register_tool_group_success(self, base_agent):
        """Test successful tool group registration."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.get_tools.return_value = [lambda: "tool1", lambda: "tool2"]
            mock_import.return_value = mock_module

            base_agent.register_tool_group("test_tools")

            assert len(base_agent._tools) == 2
            mock_import.assert_called_once_with("tripsage.tools.test_tools")

    def test_register_tool_group_no_get_tools(self, base_agent):
        """Test tool group registration when module has no get_tools function."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            del mock_module.get_tools  # Remove get_tools attribute
            mock_import.return_value = mock_module

            # Should not raise error
            base_agent.register_tool_group("test_tools")

            assert len(base_agent._tools) == 0

    def test_register_tool_group_import_error(self, base_agent):
        """Test tool group registration with import error."""
        with patch(
            "importlib.import_module", side_effect=ImportError("Module not found")
        ):
            # Should not raise error
            base_agent.register_tool_group("nonexistent_tools")

            assert len(base_agent._tools) == 0

    def test_register_tool_group_get_tools_error(self, base_agent):
        """Test tool group registration when get_tools raises error."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.get_tools.side_effect = Exception("Tool retrieval failed")
            mock_import.return_value = mock_module

            # Should not raise error
            base_agent.register_tool_group("test_tools")

            assert len(base_agent._tools) == 0

    def test_get_tools_list(self, base_agent):
        """Test getting the tools list."""

        def tool1() -> str:
            return "tool1"

        tool2_obj = {"name": "tool2", "function": lambda: "tool2"}

        base_agent.register_tool(tool1)
        base_agent.register_tool(tool2_obj)

        tools = base_agent.get_tools()

        assert len(tools) == 2
        assert tool1 in tools
        assert tool2_obj in tools

    def test_clear_tools(self, base_agent):
        """Test clearing all registered tools."""

        def tool1() -> str:
            return "tool1"

        base_agent.register_tool(tool1)
        assert len(base_agent._tools) == 1

        base_agent.clear_tools()
        assert len(base_agent._tools) == 0

    @pytest.mark.asyncio
    async def test_run_with_openai_sdk(self, base_agent, mock_openai_runner):
        """Test running agent with OpenAI SDK."""
        mock_result = MagicMock()
        mock_result.final_output = "Test response from agent"
        mock_result.tool_calls = []
        mock_openai_runner.run.return_value = mock_result

        base_agent.runner = mock_openai_runner

        context = {"user_id": "123", "session_id": "session_456"}
        result = await base_agent.run("Test message", context)

        assert result["content"] == "Test response from agent"
        assert result["status"] == "success"
        assert result["context"] == context
        mock_openai_runner.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_tool_calls(self, base_agent, mock_openai_runner):
        """Test running agent with tool calls."""
        mock_result = MagicMock()
        mock_result.final_output = "Response with tool calls"
        mock_result.tool_calls = [
            {"name": "test_tool", "arguments": {"param": "value"}}
        ]
        mock_openai_runner.run.return_value = mock_result

        base_agent.runner = mock_openai_runner

        result = await base_agent.run("Test message")

        assert result["content"] == "Response with tool calls"
        assert result["tool_calls"] == mock_result.tool_calls
        assert len(result["tool_calls"]) == 1

    @pytest.mark.asyncio
    async def test_run_without_openai_sdk(self):
        """Test running agent without OpenAI SDK."""
        agent = BaseAgent(name="Test Agent", instructions="Test instructions")

        # Agent and runner should be None when OpenAI SDK is not available
        assert agent.agent is None
        assert agent.runner is None

        result = await agent.run("Test message")

        assert result["status"] == "error"
        assert "OpenAI SDK not available" in result["error"]

    @pytest.mark.asyncio
    async def test_run_with_exception(self, base_agent, mock_openai_runner):
        """Test running agent when runner raises exception."""
        mock_openai_runner.run.side_effect = Exception("Agent execution failed")
        base_agent.runner = mock_openai_runner

        result = await base_agent.run("Test message")

        assert result["status"] == "error"
        assert "Agent execution failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_with_empty_context(self, base_agent, mock_openai_runner):
        """Test running agent with empty context."""
        mock_result = MagicMock()
        mock_result.final_output = "Test response"
        mock_result.tool_calls = []
        mock_openai_runner.run.return_value = mock_result

        base_agent.runner = mock_openai_runner

        result = await base_agent.run("Test message", {})

        assert result["context"] == {}
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_run_with_none_context(self, base_agent, mock_openai_runner):
        """Test running agent with None context."""
        mock_result = MagicMock()
        mock_result.final_output = "Test response"
        mock_result.tool_calls = []
        mock_openai_runner.run.return_value = mock_result

        base_agent.runner = mock_openai_runner

        result = await base_agent.run("Test message", None)

        assert result["context"] == {}
        assert result["status"] == "success"

    def test_register_handoff_tool(self, base_agent):
        """Test registering a handoff tool."""
        tool_name = "handoff_to_specialist"
        tool_config = {
            "target_agent": "SpecialistAgent",
            "description": "Handoff to specialist agent",
        }

        base_agent._register_handoff_tool(tool_name, tool_config)

        assert tool_name in base_agent._handoff_tools
        assert base_agent._handoff_tools[tool_name] == tool_config

    def test_register_delegation_tool(self, base_agent):
        """Test registering a delegation tool."""
        tool_name = "delegate_to_specialist"
        tool_config = {
            "target_agent": "SpecialistAgent",
            "description": "Delegate to specialist agent",
        }

        base_agent._register_delegation_tool(tool_name, tool_config)

        assert tool_name in base_agent._delegation_tools
        assert base_agent._delegation_tools[tool_name] == tool_config

    def test_get_handoff_tools(self, base_agent):
        """Test getting handoff tools."""
        tool_config = {"target_agent": "TestAgent"}
        base_agent._register_handoff_tool("test_handoff", tool_config)

        handoff_tools = base_agent.get_handoff_tools()

        assert "test_handoff" in handoff_tools
        assert handoff_tools["test_handoff"] == tool_config

    def test_get_delegation_tools(self, base_agent):
        """Test getting delegation tools."""
        tool_config = {"target_agent": "TestAgent"}
        base_agent._register_delegation_tool("test_delegation", tool_config)

        delegation_tools = base_agent.get_delegation_tools()

        assert "test_delegation" in delegation_tools
        assert delegation_tools["test_delegation"] == tool_config

    def test_has_tools_with_tools(self, base_agent):
        """Test has_tools when agent has tools."""

        def test_tool() -> str:
            return "test"

        base_agent.register_tool(test_tool)

        assert base_agent.has_tools() is True

    def test_has_tools_without_tools(self, base_agent):
        """Test has_tools when agent has no tools."""
        assert base_agent.has_tools() is False

    def test_tool_count(self, base_agent):
        """Test getting tool count."""
        assert base_agent.tool_count() == 0

        def tool1() -> str:
            return "tool1"

        def tool2() -> str:
            return "tool2"

        base_agent.register_tool(tool1)
        assert base_agent.tool_count() == 1

        base_agent.register_tool(tool2)
        assert base_agent.tool_count() == 2

    def test_get_tool_names(self, base_agent):
        """Test getting tool names."""

        def named_tool() -> str:
            """Named tool function."""
            return "named"

        tool_obj = {"name": "custom_tool", "function": lambda: "custom"}

        base_agent.register_tool(named_tool)
        base_agent.register_tool(tool_obj)

        tool_names = base_agent.get_tool_names()

        assert "named_tool" in tool_names
        assert "custom_tool" in tool_names

    def test_get_tool_names_empty(self, base_agent):
        """Test getting tool names when no tools registered."""
        tool_names = base_agent.get_tool_names()

        assert tool_names == []

    @pytest.mark.asyncio
    async def test_process_tool_call_result(self, base_agent):
        """Test processing tool call results."""
        tool_result = {
            "name": "test_tool",
            "result": {"success": True, "data": "test_data"},
            "execution_time": 0.5,
        }

        processed = await base_agent._process_tool_call_result(tool_result)

        assert processed["tool_name"] == "test_tool"
        assert processed["success"] is True
        assert processed["data"] == "test_data"
        assert processed["execution_time"] == 0.5

    @pytest.mark.asyncio
    async def test_process_tool_call_result_with_error(self, base_agent):
        """Test processing tool call results with error."""
        tool_result = {
            "name": "test_tool",
            "error": "Tool execution failed",
            "execution_time": 0.1,
        }

        processed = await base_agent._process_tool_call_result(tool_result)

        assert processed["tool_name"] == "test_tool"
        assert processed["success"] is False
        assert processed["error"] == "Tool execution failed"

    def test_validate_tool_registration_valid_function(self, base_agent):
        """Test tool registration validation with valid function."""

        def valid_tool(param: str) -> str:
            """A valid tool function."""
            return f"Result: {param}"

        # Should not raise exception
        is_valid = base_agent._validate_tool_registration(valid_tool)
        assert is_valid is True

    def test_validate_tool_registration_valid_object(self, base_agent):
        """Test tool registration validation with valid object."""
        valid_tool_obj = {
            "name": "test_tool",
            "function": lambda x: x,
            "description": "Test tool",
        }

        # Should not raise exception
        is_valid = base_agent._validate_tool_registration(valid_tool_obj)
        assert is_valid is True

    def test_validate_tool_registration_invalid_object(self, base_agent):
        """Test tool registration validation with invalid object."""
        invalid_tool_obj = {
            "name": "test_tool"
            # Missing required 'function' key
        }

        is_valid = base_agent._validate_tool_registration(invalid_tool_obj)
        assert is_valid is False

    def test_validate_tool_registration_invalid_type(self, base_agent):
        """Test tool registration validation with invalid type."""
        invalid_tool = "not_a_tool"

        is_valid = base_agent._validate_tool_registration(invalid_tool)
        assert is_valid is False

    def test_update_agent_config(self, base_agent, mock_openai_agent):
        """Test updating agent configuration."""
        new_config = {"temperature": 0.9, "max_tokens": 2000}

        base_agent.agent = mock_openai_agent
        base_agent.update_agent_config(new_config)

        # Should update temperature
        assert mock_openai_agent.temperature == 0.9

    def test_update_agent_config_no_agent(self, base_agent):
        """Test updating agent configuration when no agent exists."""
        new_config = {"temperature": 0.9}

        # Should not raise exception
        base_agent.update_agent_config(new_config)

    def test_clone_agent(self, base_agent):
        """Test cloning an agent."""

        # Add some tools to the original
        def test_tool() -> str:
            return "test"

        base_agent.register_tool(test_tool)

        with patch("agents.Agent") as mock_agent_cls:
            with patch("agents.Runner") as mock_runner_cls:
                mock_agent_cls.return_value = MagicMock()
                mock_runner_cls.return_value = MagicMock()

                cloned = base_agent.clone("Cloned Agent")

                assert cloned.name == "Cloned Agent"
                assert cloned.instructions == base_agent.instructions
                assert cloned.model == base_agent.model
                assert cloned.temperature == base_agent.temperature
                # Tools should be copied
                assert len(cloned._tools) == len(base_agent._tools)

    def test_clone_agent_no_openai_sdk(self):
        """Test cloning an agent without OpenAI SDK."""
        with patch("agents.Agent", side_effect=ImportError("OpenAI SDK not available")):
            original = BaseAgent(
                name="Original Agent", instructions="Original instructions"
            )

            cloned = original.clone("Cloned Agent")

            assert cloned.name == "Cloned Agent"
            assert cloned.instructions == "Original instructions"
            assert cloned.agent is None
            assert cloned.runner is None

    @pytest.mark.asyncio
    async def test_run_with_context_inheritance(self, base_agent, mock_openai_runner):
        """Test that context is properly inherited in runs."""
        mock_result = MagicMock()
        mock_result.final_output = "Context test response"
        mock_result.tool_calls = []
        mock_openai_runner.run.return_value = mock_result

        base_agent.runner = mock_openai_runner

        original_context = {"user_id": "123", "session_data": {"key": "value"}}

        result = await base_agent.run("Test message", original_context)

        # Context should be preserved in result
        assert result["context"] == original_context
        assert result["context"]["user_id"] == "123"
        assert result["context"]["session_data"]["key"] == "value"

    def test_metadata_management(self, base_agent):
        """Test metadata management functionality."""
        # Initial metadata
        assert base_agent.metadata == {}

        # Update metadata
        base_agent.metadata["version"] = "1.0"
        base_agent.metadata["features"] = ["tool_calling", "handoffs"]

        assert base_agent.metadata["version"] == "1.0"
        assert "tool_calling" in base_agent.metadata["features"]

    def test_agent_properties(self, base_agent):
        """Test agent property access."""
        assert base_agent.name == "Test Agent"
        assert "Test instructions" in base_agent.instructions
        assert base_agent.model == "gpt-4"
        assert base_agent.temperature == 0.7

    @pytest.mark.asyncio
    async def test_run_performance_tracking(self, base_agent, mock_openai_runner):
        """Test that run performance is tracked."""
        mock_result = MagicMock()
        mock_result.final_output = "Performance test response"
        mock_result.tool_calls = []
        mock_openai_runner.run.return_value = mock_result

        base_agent.runner = mock_openai_runner

        result = await base_agent.run("Test message")

        # Should include timing information
        assert "timestamp" in result
        assert isinstance(result["timestamp"], (int, float))

    def test_tool_registration_edge_cases(self, base_agent):
        """Test edge cases in tool registration."""
        # Test registering None
        base_agent.register_tool(None)
        assert len(base_agent._tools) == 0

        # Test registering empty dict
        base_agent.register_tool({})
        assert len(base_agent._tools) == 0

        # Test registering lambda
        lambda_tool = lambda x: x * 2
        lambda_tool.__name__ = "lambda_tool"
        base_agent.register_tool(lambda_tool)
        assert len(base_agent._tools) == 1


class TestBaseAgentIntegration:
    """Integration tests for BaseAgent functionality."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_tools(self):
        """Test complete workflow with tool registration and execution."""
        with patch("agents.Agent") as mock_agent_cls:
            with patch("agents.Runner") as mock_runner_cls:
                # Setup mocks
                mock_agent = MagicMock()
                mock_runner = MagicMock()
                mock_agent_cls.return_value = mock_agent
                mock_runner_cls.return_value = mock_runner

                # Create agent
                agent = BaseAgent(
                    name="Integration Test Agent",
                    instructions="Agent for integration testing",
                )

                # Register tools
                def calculation_tool(a: int, b: int) -> int:
                    """Add two numbers."""
                    return a + b

                def string_tool(text: str) -> str:
                    """Process text."""
                    return text.upper()

                agent.register_tool(calculation_tool)
                agent.register_tool(string_tool)

                # Verify tools registered
                assert agent.tool_count() == 2
                assert agent.has_tools() is True

                tool_names = agent.get_tool_names()
                assert "calculation_tool" in tool_names
                assert "string_tool" in tool_names

                # Setup mock runner response
                mock_result = MagicMock()
                mock_result.final_output = "Integration test complete"
                mock_result.tool_calls = [
                    {"name": "calculation_tool", "arguments": {"a": 5, "b": 3}}
                ]
                mock_runner.run.return_value = mock_result

                # Run agent
                context = {"test_mode": True, "user_id": "integration_test"}
                result = await agent.run("Test integration", context)

                # Verify results
                assert result["status"] == "success"
                assert result["content"] == "Integration test complete"
                assert result["context"]["test_mode"] is True
                assert len(result["tool_calls"]) == 1

                # Verify runner was called with correct parameters
                mock_runner.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery in agent workflow."""
        with patch("agents.Agent", side_effect=ImportError("OpenAI SDK not available")):
            agent = BaseAgent(
                name="Error Recovery Agent",
                instructions="Agent for error recovery testing",
            )

            # Should handle missing OpenAI SDK gracefully
            assert agent.agent is None
            assert agent.runner is None

            # Should still allow tool registration
            def recovery_tool() -> str:
                return "recovery successful"

            agent.register_tool(recovery_tool)
            assert agent.tool_count() == 1

            # Run should return error but not crash
            result = await agent.run("Test error recovery")

            assert result["status"] == "error"
            assert "OpenAI SDK not available" in result["error"]
