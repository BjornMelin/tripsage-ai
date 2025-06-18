"""
Comprehensive tests for AccommodationAgentNode.

This module provides full test coverage for the accommodation agent node
including search parameter extraction, API integration, and response generation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.accommodation_agent import AccommodationAgentNode
from tripsage.orchestration.state import create_initial_state

class TestAccommodationAgentNode:
    """Test suite for AccommodationAgentNode."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        registry = MagicMock(spec=ServiceRegistry)

        # Mock accommodation service
        accommodation_service = AsyncMock()
        accommodation_service.search_accommodations = AsyncMock(
            return_value={
                "status": "success",
                "listings": [
                    {
                        "id": "prop-123",
                        "name": "Grand Hyatt Tokyo",
                        "property_type": "Hotel",
                        "price": {"per_night": "$250"},
                        "rating": 4.5,
                        "amenities": ["wifi", "pool", "gym"],
                    },
                    {
                        "id": "prop-456",
                        "name": "Park Hyatt Tokyo",
                        "property_type": "Hotel",
                        "price": {"per_night": "$450"},
                        "rating": 4.8,
                        "amenities": ["wifi", "spa", "restaurant"],
                    },
                ],
            }
        )

        # Mock memory service
        memory_service = AsyncMock()

        registry.get_required_service = MagicMock(
            side_effect=lambda name: {
                "accommodation_service": accommodation_service
            }.get(name)
        )

        registry.get_optional_service = MagicMock(
            side_effect=lambda name: {"memory_service": memory_service}.get(name)
        )

        return registry

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = AsyncMock()
        return llm

    @pytest.fixture
    def accommodation_node(self, mock_service_registry, mock_llm):
        """Create an accommodation agent node with mocks."""
        with patch(
            "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI",
            return_value=mock_llm,
        ):
            node = AccommodationAgentNode(mock_service_registry)
            node.llm = mock_llm
            return node

    @pytest.fixture
    def sample_state(self):
        """Create a sample state with accommodation request."""
        state = create_initial_state(
            "user-123", "I need a hotel in Tokyo for next week, preferably near Shibuya"
        )
        state["travel_dates"] = {
            "departure_date": "2024-06-15",
            "return_date": "2024-06-22",
        }
        return state

    def test_node_initialization(self, mock_service_registry):
        """Test accommodation agent node initialization."""
        with patch("tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"):
            node = AccommodationAgentNode(mock_service_registry)

            assert node.node_name == "accommodation_agent"
            assert hasattr(node, "accommodation_service")
            assert hasattr(node, "memory_service")
            assert hasattr(node, "llm")

    @pytest.mark.asyncio
    async def test_successful_accommodation_search(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test successful accommodation search flow."""
        # Mock LLM parameter extraction
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Tokyo, Shibuya",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                    "property_type": "hotel",
                }
            )
        )

        # Process the state
        result = await accommodation_node.process(sample_state)

        # Verify search was performed
        accommodation_node.accommodation_service.search_accommodations.assert_called_once()
        call_args = (
            accommodation_node.accommodation_service.search_accommodations.call_args[1]
        )
        assert call_args["location"] == "Tokyo, Shibuya"
        assert call_args["check_in_date"] == "2024-06-15"

        # Verify state updates
        assert "accommodation_searches" in result
        assert len(result["accommodation_searches"]) == 1
        search_record = result["accommodation_searches"][0]
        assert search_record["agent"] == "accommodation_agent"
        assert search_record["parameters"]["location"] == "Tokyo, Shibuya"
        assert len(search_record["results"]["listings"]) == 2

        # Verify response message
        assert len(result["messages"]) == 2  # Original + response
        response = result["messages"][-1]
        assert response["role"] == "assistant"
        assert response["agent"] == "accommodation_agent"
        assert "found 2 accommodations" in response["content"]
        assert "Grand Hyatt Tokyo" in response["content"]
        assert "Park Hyatt Tokyo" in response["content"]

    @pytest.mark.asyncio
    async def test_parameter_extraction_with_context(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test parameter extraction using conversation context."""
        # Add context to state
        sample_state["user_preferences"] = {
            "budget_total": 2000,
            "accommodation_type": "hotel",
        }
        sample_state["destination_info"] = {"destination": "Tokyo"}

        # Mock LLM response
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Tokyo",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                    "min_price": 100,
                    "max_price": 300,
                    "amenities": ["wifi", "gym"],
                }
            )
        )

        # Process the state
        await accommodation_node.process(sample_state)

        # Verify LLM was called with context
        llm_call = mock_llm.ainvoke.call_args[0][0]
        assert any("User preferences:" in msg.content for msg in llm_call)
        assert any("Tokyo" in msg.content for msg in llm_call)

    @pytest.mark.asyncio
    async def test_no_search_parameters_extracted(self, accommodation_node, mock_llm):
        """Test handling when no search parameters are extracted."""
        # Create state with vague message
        state = create_initial_state(
            "user-123", "What kind of hotels do you recommend?"
        )

        # Mock LLM returning null (no parameters)
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="null"),  # Parameter extraction
            MagicMock(
                content=(
                    "I'd be happy to help you find accommodations! To search for "
                    "the best options, I'll need to know your destination, "
                    "check-in and check-out dates, and any preferences you have "
                    "for the type of property or amenities."
                )
            ),  # General response
        ]

        # Process the state
        result = await accommodation_node.process(state)

        # Verify no search was performed
        accommodation_node.accommodation_service.search_accommodations.assert_not_called()

        # Verify helpful response was generated
        assert len(result["messages"]) == 2
        response = result["messages"][-1]
        assert response["role"] == "assistant"
        assert "help you find accommodations" in response["content"]
        assert "destination" in response["content"]
        assert "dates" in response["content"]

    @pytest.mark.asyncio
    async def test_search_error_handling(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test error handling during accommodation search."""
        # Mock successful parameter extraction
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Tokyo",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                }
            )
        )

        # Mock search failure
        accommodation_node.accommodation_service.search_accommodations.return_value = {
            "error": "API rate limit exceeded"
        }

        # Process the state
        result = await accommodation_node.process(sample_state)

        # Verify error response
        response = result["messages"][-1]
        assert "encountered an issue" in response["content"]
        assert "API rate limit exceeded" in response["content"]

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test handling of empty search results."""
        # Mock parameter extraction
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Remote Island",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                }
            )
        )

        # Mock empty results
        accommodation_node.accommodation_service.search_accommodations.return_value = {
            "status": "success",
            "listings": [],
        }

        # Process the state
        result = await accommodation_node.process(sample_state)

        # Verify response handles no results
        response = result["messages"][-1]
        assert "couldn't find any accommodations" in response["content"]
        assert "Remote Island" in response["content"]
        assert "try different dates" in response["content"]

    @pytest.mark.asyncio
    async def test_llm_parameter_extraction_error(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test handling of LLM errors during parameter extraction."""
        # Mock LLM error
        mock_llm.ainvoke.side_effect = Exception("LLM service unavailable")

        # Process should handle error gracefully
        result = await accommodation_node.process(sample_state)

        # Should fall back to general inquiry handling
        assert len(result["messages"]) == 2
        response = result["messages"][-1]
        assert response["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_invalid_json_from_llm(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test handling of invalid JSON from LLM."""
        # Mock invalid JSON response
        mock_llm.ainvoke.return_value = MagicMock(content="This is not valid JSON")

        # Process the state
        _result = await accommodation_node.process(sample_state)

        # Should handle gracefully and not perform search
        accommodation_node.accommodation_service.search_accommodations.assert_not_called()

    @pytest.mark.asyncio
    async def test_response_formatting_with_many_results(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test response formatting when many results are returned."""
        # Mock parameter extraction
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Tokyo",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                }
            )
        )

        # Mock many results
        listings = []
        for i in range(10):
            listings.append(
                {
                    "id": f"prop-{i}",
                    "name": f"Hotel {i}",
                    "property_type": "Hotel",
                    "price": {"per_night": f"${100 + i * 50}"},
                    "rating": 4.0 + i * 0.1,
                    "amenities": ["wifi", "pool"],
                }
            )

        accommodation_node.accommodation_service.search_accommodations.return_value = {
            "status": "success",
            "listings": listings,
        }

        # Process the state
        result = await accommodation_node.process(sample_state)

        # Verify response shows top 3 and mentions more
        response = result["messages"][-1]
        assert "found 10 accommodations" in response["content"]
        assert "Hotel 0" in response["content"]
        assert "Hotel 1" in response["content"]
        assert "Hotel 2" in response["content"]
        assert "Hotel 3" not in response["content"]  # Only top 3 shown
        assert "7 more options available" in response["content"]

    @pytest.mark.asyncio
    async def test_state_agent_history_update(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test that agent history is properly updated."""
        # Mock parameter extraction
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Tokyo",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                }
            )
        )

        # Process through the full node (not just process method)
        result = await accommodation_node(sample_state)

        # Verify agent history updated
        assert "accommodation_agent" in result["agent_history"]

    @pytest.mark.asyncio
    async def test_response_message_metadata(
        self, accommodation_node, sample_state, mock_llm
    ):
        """Test that response messages include proper metadata."""
        # Mock parameter extraction
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(
                {
                    "location": "Tokyo",
                    "check_in_date": "2024-06-15",
                    "check_out_date": "2024-06-22",
                    "guests": 2,
                }
            )
        )

        # Process the state
        result = await accommodation_node.process(sample_state)

        # Verify response metadata
        response = result["messages"][-1]
        assert response["agent"] == "accommodation_agent"
        assert "timestamp" in response
        assert "search_params" in response
        assert "results_count" in response
        assert response["results_count"] == 2
