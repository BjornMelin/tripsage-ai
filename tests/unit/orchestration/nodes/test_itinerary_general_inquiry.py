"""ItineraryAgent general inquiry handling tests (LLM mocked)."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import MockChatOpenAI, patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.itinerary_agent import ItineraryAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Create service container for itinerary tests."""
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
    return c


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.itinerary_agent")
async def test_handle_general_itinerary_inquiry_content_is_string() -> None:
    """General inquiry responds with string content (offline mock LLM)."""
    node = ItineraryAgentNode(_make_services())
    await node._load_configuration()  # type: ignore[reportPrivateUsage]
    node.__dict__["llm"] = cast(Any, MockChatOpenAI())
    st = create_initial_state("u", "plan a trip")
    msg = await node._handle_general_itinerary_inquiry("need ideas", st)  # type: ignore[reportPrivateUsage]
    assert isinstance(msg["content"], str)
