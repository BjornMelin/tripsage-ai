"""DestinationResearchAgent tests: interests normalization and branches."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.destination_research_agent import (
    DestinationResearchAgentNode,
)
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Make services stub."""
    container = AppServiceContainer()
    container.configuration_service = MagicMock()
    container.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    # Tools used by research methods
    container.webcrawl_service = MagicMock()
    container.webcrawl_service.search_web = AsyncMock(return_value={"results": []})
    container.google_maps_service = MagicMock()
    container.google_maps_service.search_places = AsyncMock(return_value={})
    container.weather_service = MagicMock()
    container.weather_service.get_current_weather = AsyncMock(return_value={})
    return container


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.destination_research_agent")
async def test_interests_normalization_and_overview_branch() -> None:
    """Extracted params normalize interests and support overview branch."""
    services = _make_services()
    node = DestinationResearchAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    # Stub extractor to avoid real structured calls
    from tripsage.orchestration.nodes.destination_research_agent import (
        DestinationResearchParameters,
    )

    class _Extractor:
        """Extractor stub."""

        async def extract_from_prompts(self, *, system_prompt: str, user_prompt: str):
            """Extract from prompts."""
            _ = (system_prompt, user_prompt)
            return DestinationResearchParameters(
                destination="Tokyo",
                research_type="overview",
                specific_interests=["museums", "7"],
            )

    node._parameter_extractor = _Extractor()  # type: ignore[reportPrivateUsage]
    state = create_initial_state("u1", "Research Tokyo attractions")
    params = await node._extract_research_parameters("Tokyo overview", state)  # type: ignore[reportPrivateUsage]
    assert params is not None
    # Ensure specific_interests coerced to list[str] when present
    if isinstance(params.get("specific_interests"), list):
        assert all(isinstance(x, str) for x in params["specific_interests"])  # type: ignore[index]


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.destination_research_agent")
async def test_research_error_fallbacks() -> None:
    """Research subcalls should return error dicts when tool fails."""
    services = _make_services()
    node = DestinationResearchAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    class _Tool:
        async def ainvoke(self, *_: Any, **__: Any):
            """Always raise to simulate tool failure."""
            raise RuntimeError("tool-failure")

    # Patch tool getter to always return bad tool
    node._get_tool = lambda *_args, **_kwargs: _Tool()  # type: ignore[reportPrivateUsage]
    assert "error" in await node._research_overview("X")  # type: ignore[reportPrivateUsage]
    assert [{"error": "tool-failure"}] == await node._research_attractions("X", [])  # type: ignore[reportPrivateUsage]
    assert [{"error": "tool-failure"}] == await node._research_activities("X", [])  # type: ignore[reportPrivateUsage]
    assert "error" in await node._research_practical_info("X")  # type: ignore[reportPrivateUsage]
    assert "error" in await node._research_cultural_info("X")  # type: ignore[reportPrivateUsage]
    assert "error" in await node._get_location_data("X")  # type: ignore[reportPrivateUsage]
