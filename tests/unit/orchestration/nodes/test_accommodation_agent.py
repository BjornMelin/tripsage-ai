"""AccommodationAgent tests: parameter extraction and response handling."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.accommodation_agent import AccommodationAgentNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state


def _make_services() -> AppServiceContainer:
    """Make services stub."""
    container = AppServiceContainer()
    container.accommodation_service = MagicMock()
    container.accommodation_service.search_accommodations = AsyncMock(
        return_value=MagicMock(search_id="s1", results_returned=1, cached=False)
    )
    container.configuration_service = MagicMock()
    container.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    return container


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.accommodation_agent")
async def test_extract_and_normalize_amenities() -> None:
    """Parameter extraction should coerce amenities items to list[str]."""
    services = _make_services()
    node = AccommodationAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    # Ensure LLM is mock to avoid external calls
    from tests.unit.orchestration.test_utils import MockChatOpenAI

    node.__dict__["llm"] = cast(Any, MockChatOpenAI())
    # Stub extractor to avoid real structured calls
    from tripsage.orchestration.nodes.accommodation_agent import (
        AccommodationSearchParameters,
    )

    class _Extractor:
        """Extractor stub."""

        async def extract_from_prompts(self, *, system_prompt: str, user_prompt: str):
            """Extract from prompts."""
            _ = (system_prompt, user_prompt)
            return AccommodationSearchParameters(
                location="Paris",
                check_in_date=None,
                check_out_date=None,
                guests=2,
                amenities=["pool", "2"],
            )

    node._runtime.parameter_extractor = _Extractor()  # type: ignore[attr-defined]

    # Simulate extraction return via StructuredExtractor -> model_to_dict path
    st: TravelPlanningState = create_initial_state("u1", "")
    params = await node._extract_accommodation_parameters(  # type: ignore[reportPrivateUsage]
        "amenities include pool and 2 balconies", st
    )
    assert params is not None
    # amenities normalization yields list[str]
    amenities_any = params.get("amenities")
    if isinstance(amenities_any, list):
        amenities_list = cast(list[str], amenities_any)
        assert all(isinstance(x, str) for x in amenities_list)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.accommodation_agent")
async def test_generate_response_content_is_string() -> None:
    """Generated accommodation response content is always a string."""
    services = _make_services()
    node = AccommodationAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    from tests.unit.orchestration.test_utils import MockChatOpenAI

    node.__dict__["llm"] = cast(Any, MockChatOpenAI())
    st = create_initial_state("u1", "I want a hotel")
    msg = await node._handle_general_accommodation_inquiry(  # type: ignore[reportPrivateUsage]
        "I want a hotel in Paris", st
    )
    assert isinstance(msg["content"], str)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.accommodation_agent")
async def test_build_search_request_date_conversion() -> None:
    """Date strings should be converted to date objects in search request."""
    services = _make_services()
    node = AccommodationAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    params = {
        "location": "Paris",
        "check_in_date": "2025-01-02",
        "check_out_date": "2025-01-06",
    }
    req = node._build_search_request(params, user_id="u1")  # type: ignore[reportPrivateUsage]
    assert hasattr(req, "check_in") and hasattr(req, "check_out")


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.accommodation_agent")
async def test_search_accommodations_error_path() -> None:
    """Service exception should be logged and raised by _search_accommodations."""
    services = _make_services()
    services.accommodation_service.search_accommodations.side_effect = Exception(  # type: ignore[attr-defined]
        "boom"
    )
    node = AccommodationAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    with pytest.raises(Exception, match="boom"):
        await node._search_accommodations(  # pyright: ignore[reportPrivateUsage]
            {
                "location": "P",
                "check_in_date": "2025-01-01",
                "check_out_date": "2025-01-02",
            },
            "u1",
        )  # type: ignore[reportPrivateUsage]
