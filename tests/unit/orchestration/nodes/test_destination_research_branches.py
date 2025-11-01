"""DestinationResearchAgent branch coverage tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.destination_research_agent import (
    DestinationResearchAgentNode,
)


def _make_services() -> AppServiceContainer:
    """Make services stub."""
    c = AppServiceContainer()
    c.configuration_service = MagicMock()
    c.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    c.webcrawl_service = MagicMock()
    c.webcrawl_service.search_web = AsyncMock(return_value={"results": []})
    c.google_maps_service = MagicMock()
    c.google_maps_service.search_places = AsyncMock(return_value={})
    c.weather_service = MagicMock()
    c.weather_service.get_current_weather = AsyncMock(return_value={})
    return c


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.destination_research_agent")
async def test_all_branches_return_structures() -> None:
    """Each branch should return structured data or error dicts."""
    services = _make_services()
    node = DestinationResearchAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    # Provide a simple tool stub that returns empty list results
    class _Tool:
        """Tool stub."""

        async def ainvoke(self, *_: Any, **__: Any) -> Any:
            """Always return empty list."""
            return []

    node._get_tool = lambda *_a, **_k: _Tool()  # type: ignore[reportPrivateUsage]

    # Cover explicit branch methods
    assert isinstance(await node._research_overview("X"), dict)  # type: ignore[reportPrivateUsage]
    assert isinstance(await node._research_practical_info("X"), dict)  # type: ignore[reportPrivateUsage]
    assert isinstance(await node._research_cultural_info("X"), dict)  # type: ignore[reportPrivateUsage]
    assert isinstance(await node._get_location_data("X"), dict)  # type: ignore[reportPrivateUsage]
    # list-returning branches
    out_a = await node._research_attractions("X", [])  # type: ignore[reportPrivateUsage]
    out_b = await node._research_activities("X", [])  # type: ignore[reportPrivateUsage]
    assert isinstance(out_a, list) and isinstance(out_b, list)
