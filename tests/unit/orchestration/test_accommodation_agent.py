"""Unit tests for the final accommodation agent implementation."""

from __future__ import annotations

from datetime import date
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.accommodation_agent import (
    AccommodationAgentNode,
    AccommodationSearchParameters,
)
from tripsage.orchestration.state import create_initial_state
from tripsage_core.services.business.accommodation_service import (
    AccommodationListing,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    PropertyType,
)


@pytest.fixture
def sample_listing() -> AccommodationListing:
    """Build a representative accommodation listing."""
    return AccommodationListing.model_validate(
        {
            "id": "prop-123",
            "name": "Skyline Hotel",
            "description": "Modern hotel in Shibuya.",
            "property_type": PropertyType.HOTEL,
            "location": {
                "address": "1-1 Shibuya",
                "city": "Tokyo",
                "country": "Japan",
            },
            "price_per_night": 250.0,
            "currency": "USD",
            "rating": 4.6,
            "review_count": 128,
            "max_guests": 2,
            "amenities": [
                {"name": "WiFi"},
                {"name": "Pool"},
                {"name": "Fitness Center"},
            ],
            "images": [],
            "cancellation_policy": None,
            "total_price": 1750.0,
            "bedrooms": 1,
            "beds": 2,
            "bathrooms": 1,
            "host": {
                "id": "host-123",
                "name": "Skyline Hotel Management",
            },
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "source": "test_provider",
            "source_listing_id": "ext-123",
            "listing_url": "https://example.com/listing/123",
            "nights": 7,
            "score": 0.92,
            "price_score": 0.84,
            "location_score": 0.96,
        }
    )


@pytest.fixture
def sample_response(
    sample_listing: AccommodationListing,
) -> AccommodationSearchResponse:
    """Return a search response containing the sample listing."""
    return AccommodationSearchResponse.model_validate(
        {
            "search_id": "search-001",
            "listings": [sample_listing.model_dump()],
            "search_parameters": {
                "location": "Tokyo, Shibuya",
                "check_in": date(2024, 6, 15),
                "check_out": date(2024, 6, 22),
                "guests": 2,
            },
            "total_results": 1,
            "results_returned": 1,
            "min_price": 200.0,
            "max_price": 400.0,
            "avg_price": 275.0,
            "search_duration_ms": 120,
            "cached": False,
        }
    )


@pytest.fixture
def mock_registry(sample_response: AccommodationSearchResponse) -> MagicMock:
    """Create a service registry stub with accommodation and memory services."""
    registry = MagicMock(spec=ServiceRegistry)
    accommodation_service = AsyncMock()
    accommodation_service.search_accommodations = AsyncMock(
        return_value=sample_response
    )
    registry.get_required_service = MagicMock(
        side_effect=lambda name: {
            "accommodation_service": accommodation_service,
        }[name]
    )
    registry.get_optional_service = MagicMock(return_value=AsyncMock())
    return registry


@pytest.fixture
def mock_llm() -> MagicMock:
    """Provide a mock ChatOpenAI instance with structured support."""
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock()
    structured_runnable = MagicMock()
    structured_runnable.ainvoke = AsyncMock()
    llm.with_structured_output = MagicMock(return_value=structured_runnable)
    return llm


@pytest.fixture
def agent(mock_registry: MagicMock, mock_llm: MagicMock) -> AccommodationAgentNode:
    """Instantiate the accommodation agent under test."""
    with patch(
        "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI",
        return_value=mock_llm,
    ):
        return AccommodationAgentNode(mock_registry)


@pytest.mark.asyncio
async def test_process_success(agent: AccommodationAgentNode, mock_llm: MagicMock):
    """Agent should perform search, update state, and produce assistant message."""
    structured = mock_llm.with_structured_output.return_value
    structured.ainvoke.return_value = AccommodationSearchParameters.model_validate(
        {
            "location": "Tokyo, Shibuya",
            "check_in_date": date(2024, 6, 15),
            "check_out_date": date(2024, 6, 22),
            "guests": 2,
        }
    )
    state = create_initial_state(
        "user-123",
        "Find me a hotel in Tokyo, ideally around Shibuya between June 15 and 22.",
    )

    updated = await agent(state)

    mock_search = cast(AsyncMock, agent.accommodation_service.search_accommodations)
    await_call = mock_search.await_args_list[0]
    request = await_call.args[0]
    assert isinstance(request, AccommodationSearchRequest)
    assert request.location == "Tokyo, Shibuya"
    assert len(updated["accommodation_searches"]) == 1
    assert "I found 1 accommodations" in updated["messages"][-1]["content"]
    assert updated["agent_history"][-1] == "accommodation_agent"


@pytest.mark.asyncio
async def test_process_with_missing_parameters(
    agent: AccommodationAgentNode, mock_llm: MagicMock
):
    """Agent should fall back to guidance when extraction fails."""
    structured = mock_llm.with_structured_output.return_value
    structured.ainvoke.side_effect = RuntimeError("no parse")
    mock_llm.ainvoke.return_value = MagicMock(
        content="Please share your travel details so I can help."
    )
    state = create_initial_state("user-321", "Can you help me find a place to stay?")

    updated = await agent(state)

    mock_search = cast(AsyncMock, agent.accommodation_service.search_accommodations)
    assert not mock_search.await_args_list
    assert "travel details" in updated["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_process_handles_service_error(
    agent: AccommodationAgentNode,
    mock_registry: MagicMock,
    mock_llm: MagicMock,
):
    """Agent should surface a graceful message when the service raises."""
    failing_service = AsyncMock()
    failing_service.search_accommodations = AsyncMock(side_effect=RuntimeError("boom"))
    mock_registry.get_required_service = MagicMock(
        side_effect=lambda name: {
            "accommodation_service": failing_service,
        }[name]
    )

    # Recreate agent with failing service registry
    with patch(
        "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI",
        return_value=mock_llm,
    ):
        failing_agent = AccommodationAgentNode(mock_registry)

    structured = mock_llm.with_structured_output.return_value
    structured.ainvoke.return_value = AccommodationSearchParameters.model_validate(
        {
            "location": "Tokyo, Shibuya",
            "check_in_date": date(2024, 6, 15),
            "check_out_date": date(2024, 6, 22),
            "guests": 2,
        }
    )
    state = create_initial_state(
        "user-234",
        "Find a Shibuya hotel for June 15-22.",
    )

    updated = await failing_agent(state)

    assert updated["messages"][-1]["error"] is True
    assert updated["error_info"]["error_count"] == 1
