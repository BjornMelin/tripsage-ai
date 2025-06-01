"""
Tests for the BaseAgent with dependency injection.

This module tests the refactored BaseAgent class that uses the ServiceRegistry
for dependency injection instead of direct MCP calls.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from tripsage.agents.base import BaseAgent
from tripsage.agents.service_registry import ServiceRegistry


class TestBaseAgent:
    """Tests for the BaseAgent class with dependency injection."""

    def test_initialization_with_service_registry(self):
        """Test BaseAgent initialization with ServiceRegistry."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent') as mock_agent_class:
            mock_agent_instance = MagicMock()
            mock_agent_class.return_value = mock_agent_instance
            
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            assert agent.name == "TestAgent"
            assert agent.instructions == "Test instructions"
            assert agent.service_registry is registry
            assert agent.agent is mock_agent_instance

    def test_initialization_with_custom_parameters(self):
        """Test BaseAgent initialization with custom model and temperature."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent') as mock_agent_class:
            mock_agent_instance = MagicMock()
            mock_agent_class.return_value = mock_agent_instance
            
            agent = BaseAgent(
                name="CustomAgent",
                instructions="Custom instructions",
                service_registry=registry,
                model="gpt-4",
                temperature=0.8,
                metadata={"type": "custom"}
            )
            
            assert agent.model == "gpt-4"
            assert agent.temperature == 0.8
            assert agent.metadata["type"] == "custom"

    def test_register_tool_function(self):
        """Test registering a simple tool function."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Mock tool function
            mock_tool = MagicMock()
            mock_tool.__name__ = "test_tool"
            
            agent._register_tool(mock_tool)
            
            assert mock_tool in agent._tools
            assert "test_tool" in agent._registered_tools

    def test_register_tool_duplicate_prevention(self):
        """Test that duplicate tools are not registered."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Mock tool function
            mock_tool = MagicMock()
            mock_tool.__name__ = "test_tool"
            
            # Register tool twice
            agent._register_tool(mock_tool)
            initial_count = len(agent._tools)
            
            agent._register_tool(mock_tool)
            
            # Should not add duplicate
            assert len(agent._tools) == initial_count

    def test_register_tool_group_with_service_injection(self):
        """Test registering a tool group that needs service injection."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Mock a tool module with a function that needs service registry
            mock_tool_func = MagicMock()
            mock_tool_func.__name__ = "memory_tool"
            mock_tool_func.__is_function_tool__ = True
            
            mock_module = MagicMock()
            mock_module.memory_tool = mock_tool_func
            
            with patch('importlib.import_module', return_value=mock_module):
                with patch('inspect.getmembers', return_value=[('memory_tool', mock_tool_func)]):
                    with patch('inspect.signature') as mock_signature:
                        # Mock signature to indicate service_registry parameter
                        mock_param = MagicMock()
                        mock_signature.return_value.parameters = {'service_registry': mock_param}
                        
                        count = agent.register_tool_group("memory_tools")
                        
                        assert count == 1

    def test_create_service_injected_tool(self):
        """Test creating a tool wrapper with service injection."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent", 
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Create a mock tool that accepts service_registry
            @pytest.mark.asyncio
            async def mock_tool(query: str, service_registry=None):
                return {"query": query, "registry": service_registry}
            
            mock_tool.__is_function_tool__ = True
            mock_tool.__name__ = "mock_tool"
            mock_tool.__doc__ = "Mock tool"
            
            # Create wrapped tool
            wrapped_tool = agent._create_service_injected_tool(mock_tool, registry)
            
            # Verify wrapper preserves attributes
            assert hasattr(wrapped_tool, '__is_function_tool__')
            assert wrapped_tool.__name__ == "mock_tool"
            assert wrapped_tool.__doc__ == "Mock tool"

    @pytest.mark.asyncio
    async def test_run_with_context(self):
        """Test running agent with context."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent') as mock_agent_class:
            with patch('agents.Runner') as mock_runner_class:
                # Mock the agent and runner
                mock_agent_instance = MagicMock()
                mock_agent_class.return_value = mock_agent_instance
                
                mock_result = MagicMock()
                mock_result.final_output = "Test response"
                mock_result.tool_calls = []
                mock_runner_class.run = AsyncMock(return_value=mock_result)
                
                agent = BaseAgent(
                    name="TestAgent",
                    instructions="Test instructions", 
                    service_registry=registry
                )
                
                response = await agent.run("Test input", context={"user_id": "test"})
                
                assert response["content"] == "Test response"
                assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_run_with_handoff_detection(self):
        """Test agent run with handoff detection."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent') as mock_agent_class:
            with patch('agents.Runner') as mock_runner_class:
                # Mock agent and runner
                mock_agent_instance = MagicMock()
                mock_agent_class.return_value = mock_agent_instance
                
                # Mock result with handoff
                mock_result = MagicMock()
                mock_result.final_output = "Handing off to specialist"
                mock_result.tool_calls = [{"name": "handoff_tool"}]
                mock_runner_class.run = AsyncMock(return_value=mock_result)
                
                agent = BaseAgent(
                    name="TestAgent",
                    instructions="Test instructions",
                    service_registry=registry
                )
                
                # Register a handoff tool
                agent._handoff_tools["handoff_tool"] = {
                    "target_agent": "SpecialistAgent",
                    "tool": MagicMock()
                }
                
                response = await agent.run("Test input")
                
                assert response["status"] == "handoff"
                assert response["handoff_target"] == "SpecialistAgent"
                assert response["handoff_tool"] == "handoff_tool"

    @pytest.mark.asyncio
    async def test_run_error_handling(self):
        """Test agent run with error handling."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent') as mock_agent_class:
            with patch('agents.Runner') as mock_runner_class:
                # Mock agent
                mock_agent_instance = MagicMock()
                mock_agent_class.return_value = mock_agent_instance
                
                # Mock runner to raise exception
                mock_runner_class.run = AsyncMock(side_effect=Exception("Test error"))
                
                agent = BaseAgent(
                    name="TestAgent",
                    instructions="Test instructions",
                    service_registry=registry
                )
                
                response = await agent.run("Test input")
                
                assert response["status"] == "error"
                assert "error" in response["content"].lower()

    @pytest.mark.asyncio
    async def test_initialize_session_with_user_id(self):
        """Test session initialization with user context."""
        mock_memory = MagicMock()
        mock_memory.get_user_context = AsyncMock(return_value={
            "preferences": {"budget": "mid-range"},
            "past_trips": ["Paris", "Tokyo"]
        })
        
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            session_data = await agent._initialize_session("user123")
            
            assert session_data["user_id"] == "user123"
            assert session_data["preferences"]["budget"] == "mid-range"
            assert "Paris" in session_data["past_trips"]

    @pytest.mark.asyncio
    async def test_save_session_summary(self):
        """Test saving session summary to memory."""
        mock_memory = MagicMock()
        mock_memory.add_conversation_memory = AsyncMock(return_value={"status": "success"})
        
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Add some message history
            agent.messages_history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            
            await agent._save_session_summary("user123", "Test summary")
            
            # Verify memory service was called
            mock_memory.add_conversation_memory.assert_called_once()

    def test_get_conversation_history(self):
        """Test getting conversation history."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Add test messages
            test_messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"}
            ]
            agent.messages_history = test_messages
            
            history = agent.get_conversation_history()
            
            assert history == test_messages

    @pytest.mark.asyncio
    async def test_echo_tool(self):
        """Test the built-in echo tool."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            result = await agent.echo("test message")
            
            assert result["text"] == "test message"


class TestBaseAgentEdgeCases:
    """Edge case tests for BaseAgent."""

    def test_initialization_without_openai_sdk(self):
        """Test BaseAgent initialization when OpenAI SDK is not available."""
        registry = ServiceRegistry()
        
        # The BaseAgent should handle missing SDK gracefully due to try/except
        with patch('agents.Agent', side_effect=ImportError("agents not available")):
            # This should not raise an exception due to the mock fallback
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            assert agent.name == "TestAgent"
            assert agent.service_registry is registry

    def test_tool_registration_missing_module(self):
        """Test tool registration when module doesn't exist."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Try to register tools from non-existent module
            count = agent.register_tool_group("nonexistent_tools")
            
            # Should return 0 and not crash
            assert count == 0

    def test_service_injection_without_parameter(self):
        """Test tool that doesn't need service injection."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = BaseAgent(
                name="TestAgent",
                instructions="Test instructions",
                service_registry=registry
            )
            
            # Mock a tool that doesn't need service registry
            mock_tool = MagicMock()
            mock_tool.__name__ = "simple_tool"
            mock_tool.__is_function_tool__ = True
            
            mock_module = MagicMock()
            mock_module.simple_tool = mock_tool
            
            with patch('importlib.import_module', return_value=mock_module):
                with patch('inspect.getmembers', return_value=[('simple_tool', mock_tool)]):
                    with patch('inspect.signature') as mock_signature:
                        # Mock signature without service_registry parameter
                        mock_signature.return_value.parameters = {}
                        
                        count = agent.register_tool_group("simple_tools")
                        
                        assert count == 1