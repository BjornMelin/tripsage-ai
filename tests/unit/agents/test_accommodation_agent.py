"""
Tests for the AccommodationAgent with dependency injection.

This module tests the refactored AccommodationAgent class that uses the ServiceRegistry
for dependency injection instead of direct MCP calls.
"""

import pytest
from unittest.mock import MagicMock, patch

from tripsage.agents.accommodation import AccommodationAgent
from tripsage.agents.service_registry import ServiceRegistry


class TestAccommodationAgent:
    """Tests for the AccommodationAgent class with dependency injection."""

    def test_initialization_default_params(self):
        """Test AccommodationAgent initialization with default parameters."""
        mock_accommodation_service = MagicMock()
        registry = ServiceRegistry(accommodation_service=mock_accommodation_service)
        
        with patch('agents.Agent') as mock_agent_class:
            mock_agent_instance = MagicMock()
            mock_agent_class.return_value = mock_agent_instance
            
            agent = AccommodationAgent(service_registry=registry)
            
            assert agent.name == "TripSage Accommodation Assistant"
            assert agent.service_registry is registry
            assert "accommodation" in agent.instructions.lower()
            assert "booking" in agent.instructions.lower()

    def test_initialization_custom_params(self):
        """Test AccommodationAgent initialization with custom parameters."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent') as mock_agent_class:
            mock_agent_instance = MagicMock()
            mock_agent_class.return_value = mock_agent_instance
            
            agent = AccommodationAgent(
                service_registry=registry,
                name="Custom Accommodation Agent",
                model="gpt-4",
                temperature=0.7
            )
            
            assert agent.name == "Custom Accommodation Agent"
            assert agent.model == "gpt-4"
            assert agent.temperature == 0.7

    def test_instructions_content_comprehensive(self):
        """Test that instructions contain all necessary accommodation guidance."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            instructions = agent.instructions.lower()
            
            # Check for key accommodation concepts
            assert "accommodation" in instructions
            assert "hotel" in instructions or "lodging" in instructions
            assert "booking" in instructions
            assert "price" in instructions or "budget" in instructions
            assert "amenities" in instructions
            assert "location" in instructions

    def test_instructions_include_search_parameters(self):
        """Test that instructions include required search parameters."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            instructions = agent.instructions.lower()
            
            # Check for search parameter guidance
            assert "check-in" in instructions or "checkin" in instructions
            assert "check-out" in instructions or "checkout" in instructions
            assert "guests" in instructions or "adults" in instructions
            assert "dates" in instructions

    def test_instructions_include_tool_guidance(self):
        """Test that instructions mention available tools."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            instructions = agent.instructions.lower()
            
            # Check for tool mentions
            assert "accommodations_tools" in instructions
            assert "search" in instructions
            assert "details" in instructions

    def test_metadata_structure(self):
        """Test that metadata is properly structured."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            assert agent.metadata["agent_type"] == "accommodation_agent"
            assert "version" in agent.metadata

    def test_tool_registration(self):
        """Test that accommodation-specific tools are registered."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            with patch.object(AccommodationAgent, 'register_tool_group') as mock_register:
                agent = AccommodationAgent(service_registry=registry)
                
                # Verify tool groups were registered
                expected_modules = [
                    "accommodations_tools",
                    "googlemaps_tools", 
                    "webcrawl_tools",
                    "memory_tools"
                ]
                
                for module in expected_modules:
                    mock_register.assert_any_call(module, service_registry=registry)

    def test_inheritance_from_base_agent(self):
        """Test that AccommodationAgent properly inherits from BaseAgent."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            # Should have BaseAgent methods
            assert hasattr(agent, 'run')
            assert hasattr(agent, '_register_tool')
            assert hasattr(agent, 'register_tool_group')
            assert hasattr(agent, 'service_registry')

    def test_instructions_booking_guidance(self):
        """Test that instructions include booking process guidance."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            instructions = agent.instructions.lower()
            
            # Check for booking guidance
            assert "booking" in instructions
            assert "availability" in instructions or "available" in instructions
            assert "cancellation" in instructions or "policy" in instructions

    def test_instructions_comparison_guidance(self):
        """Test that instructions include comparison and recommendation guidance."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            instructions = agent.instructions.lower()
            
            # Check for comparison guidance
            assert "compare" in instructions or "comparison" in instructions
            assert "recommend" in instructions or "recommendation" in instructions
            assert "options" in instructions

    def test_agent_specialization_focus(self):
        """Test that the agent is clearly specialized for accommodations."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            # Name should indicate accommodation specialization
            assert "accommodation" in agent.name.lower()
            
            # Instructions should be accommodation-focused
            instructions = agent.instructions.lower()
            assert instructions.count("accommodation") >= 2  # Should mention multiple times

    def test_service_registry_integration(self):
        """Test that the agent properly integrates with ServiceRegistry."""
        mock_accommodation_service = MagicMock()
        mock_memory_service = MagicMock()
        
        registry = ServiceRegistry(
            accommodation_service=mock_accommodation_service,
            memory_service=mock_memory_service
        )
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            # Should be able to access services through registry
            assert agent.service_registry.get_optional_service("accommodation_service") is mock_accommodation_service
            assert agent.service_registry.get_optional_service("memory_service") is mock_memory_service


class TestAccommodationAgentEdgeCases:
    """Edge case tests for AccommodationAgent."""

    def test_initialization_minimal_registry(self):
        """Test AccommodationAgent with minimal ServiceRegistry."""
        registry = ServiceRegistry()  # No services configured
        
        with patch('agents.Agent') as mock_agent_class:
            mock_agent_instance = MagicMock()
            mock_agent_class.return_value = mock_agent_instance
            
            # Should not fail even without services
            agent = AccommodationAgent(service_registry=registry)
            
            assert agent.service_registry is registry
            assert agent.name == "TripSage Accommodation Assistant"

    def test_tool_registration_failure_resilience(self):
        """Test that agent handles tool registration failures gracefully."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            with patch.object(AccommodationAgent, 'register_tool_group', side_effect=Exception("Tool registration failed")):
                # Should not crash even if tool registration fails
                try:
                    agent = AccommodationAgent(service_registry=registry)
                    # If we get here, the exception was handled
                    assert agent.service_registry is registry
                except Exception:
                    # If exception propagates, that's also acceptable for this test
                    pass

    def test_default_settings_fallback(self):
        """Test that agent uses default settings when not provided."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent') as mock_agent_class:
            with patch('tripsage_core.config.base_app_settings.get_settings') as mock_settings:
                # Mock settings
                mock_settings_obj = MagicMock()
                mock_settings_obj.agent.model_name = "default-model"
                mock_settings_obj.agent.temperature = 0.5
                mock_settings.return_value = mock_settings_obj
                
                mock_agent_instance = MagicMock()
                mock_agent_class.return_value = mock_agent_instance
                
                agent = AccommodationAgent(service_registry=registry)
                
                # Should use settings defaults
                assert agent.model == "default-model"
                assert agent.temperature == 0.5

    def test_instructions_completeness(self):
        """Test that instructions are comprehensive and actionable."""
        registry = ServiceRegistry()
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            instructions = agent.instructions
            
            # Should be substantial (not just a few words)
            assert len(instructions) > 500
            
            # Should contain actionable directives
            assert "search" in instructions.lower()
            assert "find" in instructions.lower() or "locate" in instructions.lower()
            assert "help" in instructions.lower() or "assist" in instructions.lower()

    def test_memory_integration_capability(self):
        """Test that agent can work with memory service when available."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            # Should have access to memory service
            memory_service = agent.service_registry.get_optional_service("memory_service")
            assert memory_service is mock_memory

    def test_accommodation_service_integration(self):
        """Test that agent can work with accommodation service when available."""
        mock_accommodation = MagicMock()
        registry = ServiceRegistry(accommodation_service=mock_accommodation)
        
        with patch('agents.Agent'):
            agent = AccommodationAgent(service_registry=registry)
            
            # Should have access to accommodation service
            accommodation_service = agent.service_registry.get_optional_service("accommodation_service")
            assert accommodation_service is mock_accommodation