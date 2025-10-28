"""FlightAgent tests: config guard and response content typing."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.unit.orchestration.test_utils import patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.state import create_initial_state


def _make_services() -> AppServiceContainer:
    """Make services stub."""
    container = AppServiceContainer()
    container.flight_service = MagicMock()
    container.flight_service.search_flights = AsyncMock(return_value=MagicMock())
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
@patch_openai_in_module("tripsage.orchestration.nodes.flight_agent")
async def test_config_guard_and_response_content() -> None:
    """Agent config guard loads defaults; response content is a string."""
    services = _make_services()
    node = FlightAgentNode(services)
    # agent_config empty triggers load
    state = create_initial_state("u1", "find flights NYC to LAX")
    state = await node.process(state)
    # Ensure LLM is mock to avoid external calls
    from tests.unit.orchestration.test_utils import MockChatOpenAI

    node.__dict__["llm"] = cast(Any, MockChatOpenAI())
    # Generate a friendly response path
    msg = await node._handle_general_flight_inquiry("need a flight", state)  # type: ignore[reportPrivateUsage]
    assert isinstance(msg["content"], str)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.flight_agent")
async def test_fallback_config_secret_none() -> None:
    """Fallback app settings with no API key should not crash config load."""
    services = _make_services()

    class _Settings:
        openai_model = "gpt-3.5-turbo"
        model_temperature = 0.3
        openai_api_key = None

    with patch(
        "tripsage.orchestration.nodes.flight_agent.get_settings",
        return_value=_Settings(),
    ):
        node = FlightAgentNode(services)
        await node._load_configuration()  # type: ignore[reportPrivateUsage]
        assert "api_key" in node.agent_config


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.nodes.flight_agent")
async def test_handle_general_inquiry_exception_fallback() -> None:
    """Exception in ainvoke should return friendly fallback content."""
    services = _make_services()
    node = FlightAgentNode(services)
    await node._load_configuration()  # type: ignore[reportPrivateUsage]

    class _BadLLM:
        """Mock bad LLM."""

        async def ainvoke(self, *_: Any, **__: Any):
            """Always raise to simulate provider outage."""
            raise RuntimeError("api down")

    node.__dict__["llm"] = cast(Any, _BadLLM())
    state = create_initial_state("u1", "need help")
    msg = await node._handle_general_flight_inquiry("x", state)  # type: ignore[reportPrivateUsage]
    assert isinstance(msg["content"], str)
