"""Additional ItineraryAgent tests: optimize and calendar branches."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.itinerary_agent import ItineraryAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Create service container for itinerary tests."""
    container = AppServiceContainer()
    container.configuration_service = MagicMock()
    container.configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-5-nano",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    return container


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.itinerary_agent")
async def test_optimize_existing_itinerary() -> None:
    """Optimize branch should reorder activities and mark optimization applied."""
    services = _make_services()
    node = ItineraryAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    # Seed state with an existing itinerary
    st = create_initial_state("u1", "")
    st["itineraries"].append(
        {
            "timestamp": "t",
            "operation": "create",
            "parameters": {},
            "result": {
                "itinerary_id": "it-1",
                "destination": "Rome",
                "daily_schedule": [
                    {
                        "day": 1,
                        "activities": [
                            {"name": "B", "time": "12:00"},
                            {"name": "A", "time": "09:00"},
                        ],
                    }
                ],
            },
            "agent": "itinerary_agent",
        }
    )

    result = await node._optimize_itinerary({"itinerary_id": "it-1"}, st)  # type: ignore[reportPrivateUsage]
    assert result.get("optimization_applied") is True
    # Activities sorted by time ascending
    acts = cast(list[dict[str, Any]], result.get("daily_schedule", [])[0]["activities"])  # type: ignore[index]
    assert [a.get("name") for a in acts] == ["A", "B"]


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.itinerary_agent")
async def test_calendar_branch_generation() -> None:
    """Calendar creation should emit events for daily activities."""
    services = _make_services()
    node = ItineraryAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    st = create_initial_state("u1", "")
    st["itineraries"].append(
        {
            "timestamp": "t",
            "operation": "create",
            "parameters": {},
            "result": {
                "itinerary_id": "it-1",
                "destination": "Paris",
                "daily_schedule": [
                    {
                        "day": 1,
                        "date": "2025-02-01",
                        "activities": [{"name": "Louvre", "time": "10:00"}],
                    }
                ],
            },
            "agent": "itinerary_agent",
        }
    )

    out = await node._create_calendar_events({"itinerary_id": "it-1"}, st)  # type: ignore[reportPrivateUsage]
    assert out.get("events_count") == 1
    ev = out.get("calendar_events", [])[0]
    assert ev.get("title") == "Louvre"
