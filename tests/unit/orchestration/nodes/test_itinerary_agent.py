"""ItineraryAgent tests: parameter extraction branches and responses."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.itinerary_agent import ItineraryAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Create service container stub for itinerary agent tests."""
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
    return container


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.itinerary_agent")
async def test_extract_and_create_itinerary() -> None:
    """Extractor stub returns params and process creates itinerary record."""
    services = _make_services()
    node = ItineraryAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    # Stub parameter extractor
    from tripsage.orchestration.nodes.itinerary_agent import ItineraryParameters

    class _Extractor:
        """Extractor stub."""

        async def extract_from_prompts(self, *, system_prompt: str, user_prompt: str):
            """Return a minimal create-itinerary payload."""
            _ = (system_prompt, user_prompt)
            return ItineraryParameters(
                operation="create",
                destination="Rome",
                start_date="2025-02-01",
                end_date="2025-02-03",
            )

    node._parameter_extractor = cast(Any, _Extractor())  # type: ignore[reportPrivateUsage]

    state = create_initial_state("u1", "Plan Rome itinerary")
    out = await node.process(state)
    assert out["itineraries"]
    first_params = out["itineraries"][0]["parameters"]
    assert first_params["destination"] == "Rome"
    assert isinstance(out["messages"][-1]["content"], str)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.itinerary_agent")
async def test_modify_itinerary_add_activity() -> None:
    """_modify_itinerary should add an activity to an existing record."""
    services = _make_services()
    node = ItineraryAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    # Seed state with an existing itinerary having one day
    state = create_initial_state("u1", "")
    result: dict[str, Any] = {
        "itinerary_id": "it-1",
        "daily_schedule": [{"day": 1, "activities": []}],
    }
    state["itineraries"].append(
        {
            "timestamp": "t",
            "operation": "create",
            "parameters": {},
            "result": result,
            "agent": "itinerary_agent",
        }
    )

    modified = await node._modify_itinerary(  # type: ignore[reportPrivateUsage]
        {
            "itinerary_id": "it-1",
            "modification_type": "add",
            "activity_details": {"day": 1, "name": "Colosseum", "time": "09:00"},
        },
        state,
    )
    day0 = modified["daily_schedule"][0]
    names = [a.get("name") for a in day0.get("activities", [])]
    assert "Colosseum" in names  # type: ignore[index]
