"""
Comprehensive tests for AccommodationAgent.

This module provides extensive testing for the accommodation agent including
initialization, tool registration, and accommodation-specific functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from tripsage.agents.accommodation import AccommodationAgent


class TestAccommodationAgent:
    """Comprehensive tests for AccommodationAgent."""

    @pytest.fixture
    def mock_openai_agent(self):
        """Mock OpenAI Agent SDK."""
        mock_agent = MagicMock()
        mock_agent.instructions = "Accommodation instructions"
        mock_agent.model = "gpt-4"
        mock_agent.temperature = 0.7
        return mock_agent

    @pytest.fixture
    def mock_openai_runner(self):
        """Mock OpenAI Runner SDK."""
        mock_runner = MagicMock()
        return mock_runner

    @pytest.fixture
    def accommodation_agent(self, mock_openai_agent, mock_openai_runner):
        """Create an AccommodationAgent instance with mocked dependencies."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = AccommodationAgent()
                return agent

    def test_initialization_default_params(self, mock_openai_agent, mock_openai_runner):
        """Test AccommodationAgent initialization with default parameters."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = AccommodationAgent()

                assert agent.name == "TripSage Accommodation Assistant"
                assert "accommodation assistant" in agent.instructions.lower()
                assert "lodging" in agent.instructions.lower()
                assert agent.metadata["agent_type"] == "accommodation_agent"
                assert agent.metadata["version"] == "1.0.0"

    def test_initialization_custom_params(self, mock_openai_agent, mock_openai_runner):
        """Test AccommodationAgent initialization with custom parameters."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = AccommodationAgent(
                    name="Custom Accommodation Agent",
                    model="gpt-3.5-turbo",
                    temperature=0.5,
                )

                assert agent.name == "Custom Accommodation Agent"
                assert agent.model == "gpt-3.5-turbo"
                assert agent.temperature == 0.5

    def test_instructions_content(self, accommodation_agent):
        """Test that instructions contain accommodation-specific guidance."""
        instructions = accommodation_agent.instructions.lower()

        # Check for key accommodation concepts
        assert "accommodation" in instructions
        assert "lodging" in instructions or "hotel" in instructions
        assert "booking" in instructions
        assert "search" in instructions
        assert "preferences" in instructions

        # Check for specific accommodation features
        assert "check-in" in instructions or "checkin" in instructions
        assert "amenities" in instructions
        assert "ratings" in instructions or "rating" in instructions
        assert "price" in instructions or "budget" in instructions

        # Check for tool mentions
        assert "accommodations_tools" in instructions
        assert "googlemaps_tools" in instructions
        assert "memory_tools" in instructions

    def test_register_accommodation_tools_success(self, accommodation_agent):
        """Test successful accommodation tools registration."""
        with patch.object(accommodation_agent, "register_tool_group") as mock_register:
            accommodation_agent._register_accommodation_tools()

            # Should register all expected tool modules
            expected_modules = [
                "accommodations_tools",
                "googlemaps_tools",
                "webcrawl_tools",
                "memory_tools",
            ]

            assert mock_register.call_count == len(expected_modules)
            for module in expected_modules:
                mock_register.assert_any_call(module)

    def test_register_accommodation_tools_partial_failure(self, accommodation_agent):
        """Test accommodation tools registration with partial failures."""

        def mock_register_side_effect(module):
            if module == "accommodations_tools":
                raise Exception("Tool registration failed")
            return None

        with patch.object(
            accommodation_agent,
            "register_tool_group",
            side_effect=mock_register_side_effect,
        ):
            # Should not raise exception, continue with other tools
            accommodation_agent._register_accommodation_tools()

    def test_metadata_structure(self, accommodation_agent):
        """Test that metadata contains expected structure."""
        metadata = accommodation_agent.metadata

        assert "agent_type" in metadata
        assert "version" in metadata
        assert metadata["agent_type"] == "accommodation_agent"
        assert isinstance(metadata["version"], str)

    def test_instructions_include_search_parameters(self, accommodation_agent):
        """Test that instructions include guidance on search parameters."""
        instructions = accommodation_agent.instructions.lower()

        # Key search parameters should be mentioned
        search_params = [
            "location",
            "check-in",
            "check-out",
            "guests",
            "budget",
            "property type",
            "amenities",
        ]

        for param in search_params:
            assert param in instructions, (
                f"Search parameter '{param}' not found in instructions"
            )

    def test_instructions_include_presentation_format(self, accommodation_agent):
        """Test that instructions include guidance on how to present results."""
        instructions = accommodation_agent.instructions.lower()

        # Result presentation elements should be mentioned
        presentation_elements = [
            "property name",
            "location",
            "price",
            "rating",
            "amenities",
            "cancellation",
        ]

        for element in presentation_elements:
            assert element in instructions, (
                f"Presentation element '{element}' not found in instructions"
            )

    def test_instructions_include_booking_guidance(self, accommodation_agent):
        """Test that instructions include booking process guidance."""
        instructions = accommodation_agent.instructions.lower()

        booking_concepts = ["booking", "availability", "reservation", "policies"]

        for concept in booking_concepts:
            assert concept in instructions, (
                f"Booking concept '{concept}' not found in instructions"
            )

    def test_agent_specialization_focus(self, accommodation_agent):
        """Test that agent is properly specialized for accommodations."""
        instructions = accommodation_agent.instructions

        # Should focus on accommodations, not other travel aspects
        assert instructions.count("accommodation") > instructions.count("flight")
        assert instructions.count("lodging") + instructions.count("hotel") > 0

        # Should mention different types of accommodations
        accommodation_types = ["hotel", "apartment", "house", "rental"]
        found_types = sum(
            1 for acc_type in accommodation_types if acc_type in instructions.lower()
        )
        assert found_types >= 2, "Should mention multiple accommodation types"

    def test_tool_module_coverage(self, accommodation_agent):
        """Test that all necessary tool modules are covered."""
        # Get the tool modules from the agent
        expected_modules = [
            "accommodations_tools",  # Core accommodation functionality
            "googlemaps_tools",  # Location and mapping
            "webcrawl_tools",  # Research and reviews
            "memory_tools",  # User preferences and history
        ]

        with patch.object(accommodation_agent, "register_tool_group") as mock_register:
            accommodation_agent._register_accommodation_tools()

            registered_modules = [call[0][0] for call in mock_register.call_args_list]

            for module in expected_modules:
                assert module in registered_modules, (
                    f"Tool module '{module}' not registered"
                )

    def test_instructions_practical_guidance(self, accommodation_agent):
        """Test that instructions provide practical, actionable guidance."""
        instructions = accommodation_agent.instructions.lower()

        # Should include actionable verbs and guidance
        actionable_terms = [
            "search",
            "recommend",
            "provide",
            "compare",
            "guide",
            "help",
            "ask",
            "present",
            "include",
            "verify",
        ]

        found_terms = sum(1 for term in actionable_terms if term in instructions)
        assert found_terms >= 6, "Should include sufficient actionable guidance"

    def test_agent_inheritance(self, accommodation_agent):
        """Test that AccommodationAgent properly inherits from BaseAgent."""
        from tripsage.agents.base import BaseAgent

        assert isinstance(accommodation_agent, BaseAgent)
        assert hasattr(accommodation_agent, "register_tool")
        assert hasattr(accommodation_agent, "register_tool_group")
        assert hasattr(accommodation_agent, "run")
        assert hasattr(accommodation_agent, "get_tools")

    def test_initialization_without_openai_sdk(self):
        """Test initialization when OpenAI SDK is not available."""
        with patch("agents.Agent", side_effect=ImportError("OpenAI SDK not available")):
            agent = AccommodationAgent()

            # Should still initialize properly
            assert agent.name == "TripSage Accommodation Assistant"
            assert "accommodation" in agent.instructions.lower()
            assert agent.agent is None
            assert agent.runner is None

    def test_settings_integration(self, mock_openai_agent, mock_openai_runner):
        """Test integration with settings for default values."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                # Mock settings
                with patch("tripsage.agents.accommodation.settings") as mock_settings:
                    mock_settings.agent.model_name = "test-model"
                    mock_settings.agent.temperature = 0.8

                    agent = AccommodationAgent()

                    # Should use settings values when not provided
                    assert agent.model == "test-model"
                    assert agent.temperature == 0.8

    def test_instructions_completeness(self, accommodation_agent):
        """Test that instructions are comprehensive and well-structured."""
        instructions = accommodation_agent.instructions

        # Should have substantial content
        assert len(instructions) > 1000, "Instructions should be comprehensive"

        # Should have clear sections
        assert (
            "responsibilities" in instructions.lower()
            or "guidelines" in instructions.lower()
        )
        assert "tools" in instructions.lower()
        assert "parameters" in instructions.lower()

        # Should include examples or specific guidance
        assert "e.g." in instructions or "example" in instructions.lower()

    def test_agent_name_consistency(self, accommodation_agent):
        """Test that agent name is consistent with its purpose."""
        name = accommodation_agent.name.lower()

        assert "accommodation" in name or "hotel" in name or "lodging" in name
        assert "tripsage" in name
        assert "assistant" in name

    def test_metadata_completeness(self, accommodation_agent):
        """Test that metadata provides complete agent information."""
        metadata = accommodation_agent.metadata

        # Required metadata fields
        assert "agent_type" in metadata
        assert "version" in metadata

        # Values should be meaningful
        assert metadata["agent_type"] == "accommodation_agent"
        assert "." in metadata["version"]  # Should be version format like "1.0.0"

    @pytest.mark.asyncio
    async def test_accommodation_workflow_simulation(
        self, accommodation_agent, mock_openai_runner
    ):
        """Test simulated accommodation workflow."""
        # Mock a typical accommodation search response
        mock_result = MagicMock()
        mock_result.final_output = (
            "I found several great accommodation options for your stay in "
            "San Francisco. Here are the top recommendations based on your "
            "preferences for a hotel under $200/night:"
        )
        mock_result.tool_calls = [
            {
                "name": "search_accommodations",
                "arguments": {
                    "location": "San Francisco, CA",
                    "check_in": "2024-06-01",
                    "check_out": "2024-06-05",
                    "guests": 2,
                    "max_price": 200,
                    "property_type": "hotel",
                },
            }
        ]

        mock_openai_runner.run.return_value = mock_result
        accommodation_agent.runner = mock_openai_runner

        # Simulate accommodation search request
        message = (
            "Find me a hotel in San Francisco for June 1-5 for 2 guests under "
            "$200/night"
        )
        context = {"user_id": "test_user", "preferences": {"property_type": "hotel"}}

        result = await accommodation_agent.run(message, context)

        # Verify response structure
        assert result["status"] == "success"
        assert (
            "accommodation" in result["content"].lower()
            or "hotel" in result["content"].lower()
        )
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "search_accommodations"

        # Verify tool call parameters
        tool_args = result["tool_calls"][0]["arguments"]
        assert "location" in tool_args
        assert "check_in" in tool_args
        assert "check_out" in tool_args
        assert "guests" in tool_args


class TestAccommodationAgentEdgeCases:
    """Tests for AccommodationAgent edge cases and error handling."""

    def test_initialization_edge_cases(self):
        """Test initialization with edge case parameters."""
        with patch("agents.Agent") as mock_agent_cls:
            with patch("agents.Runner") as mock_runner_cls:
                mock_agent_cls.return_value = MagicMock()
                mock_runner_cls.return_value = MagicMock()

                # Test with empty string name
                agent = AccommodationAgent(name="")
                assert agent.name == ""

                # Test with None model (should use default)
                agent = AccommodationAgent(model=None)
                assert agent.model is not None

                # Test with extreme temperature values
                agent = AccommodationAgent(temperature=0.0)
                assert agent.temperature == 0.0

                agent = AccommodationAgent(temperature=1.0)
                assert agent.temperature == 1.0

    def test_tool_registration_resilience(self):
        """Test that agent handles tool registration failures gracefully."""
        with patch("agents.Agent") as mock_agent_cls:
            with patch("agents.Runner") as mock_runner_cls:
                mock_agent = MagicMock()
                mock_runner = MagicMock()
                mock_agent_cls.return_value = mock_agent
                mock_runner_cls.return_value = mock_runner

                # Create agent and simulate tool registration failure
                agent = AccommodationAgent()

                with patch.object(
                    agent,
                    "register_tool_group",
                    side_effect=Exception("Tool registration failed"),
                ):
                    # Should not raise exception
                    agent._register_accommodation_tools()

                    # Agent should still be functional
                    assert agent.name == "TripSage Accommodation Assistant"

    def test_settings_fallback(self, mock_openai_agent, mock_openai_runner):
        """Test fallback behavior when settings are unavailable."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                # Simulate settings failure
                with patch(
                    "tripsage.agents.accommodation.settings",
                    side_effect=AttributeError("Settings not available"),
                ):
                    # Should still initialize without error
                    agent = AccommodationAgent()
                    assert agent.name == "TripSage Accommodation Assistant"

    def test_instructions_robustness(self, mock_openai_agent, mock_openai_runner):
        """Test that instructions are robust and well-formed."""
        with patch("agents.Agent", return_value=mock_openai_agent):
            with patch("agents.Runner", return_value=mock_openai_runner):
                agent = AccommodationAgent()

                # Instructions should not be empty or None
                assert agent.instructions
                assert len(agent.instructions.strip()) > 0

                # Should not have obvious formatting issues
                assert not agent.instructions.startswith(" ")
                assert not agent.instructions.endswith(" ")

                # Should be properly structured text
                assert "\n" in agent.instructions  # Should have line breaks
                lines = agent.instructions.split("\n")
                non_empty_lines = [line for line in lines if line.strip()]
                assert len(non_empty_lines) > 10  # Should have substantial content
