"""Tests for the create_agent factory relying on app.state singletons."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.unit.orchestration.test_utils import create_mock_services
from tripsage.agents import BaseAgent, ChatAgent, create_agent
from tripsage.app_state import AppServiceContainer


def _make_request(
    services: AppServiceContainer,
    orchestrator: MagicMock,
) -> MagicMock:
    """Construct a minimal FastAPI request stub exposing app.state."""
    state = SimpleNamespace(services=services, orchestrator=orchestrator)
    app = SimpleNamespace(state=state)
    request = MagicMock()
    request.app = app
    return request


@pytest.fixture
def orchestrator() -> MagicMock:
    """Provide an orchestrator stub for agent creation."""
    return MagicMock()


@pytest.fixture
def services() -> AppServiceContainer:
    """Provide a populated AppServiceContainer for agent factory tests."""
    container = create_mock_services()
    # Ensure minimal services used by BaseAgent and ChatAgent exist.
    container.memory_service = MagicMock()
    container.chat_service = MagicMock()
    return container


def test_create_agent_returns_base_agent(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """Factory should produce BaseAgent using app.state singletons."""
    request = _make_request(services, orchestrator)

    agent = create_agent(request, agent_type="base", name="Test")

    assert isinstance(agent, BaseAgent)
    assert agent.services is services
    assert agent.name == "Test"


def test_create_agent_returns_chat_agent(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """Factory should produce ChatAgent using app.state singletons."""
    request = _make_request(services, orchestrator)

    agent = create_agent(request, agent_type="chat")

    assert isinstance(agent, ChatAgent)
    assert agent.services is services


def test_create_agent_raises_when_services_missing() -> None:
    """Factory should fail fast when app.state lacks required singletons."""
    state = SimpleNamespace(services=None, orchestrator=None)
    app = SimpleNamespace(state=state)
    request = MagicMock()
    request.app = app

    with pytest.raises(ValueError, match="Application services are not initialised"):
        create_agent(request, agent_type="base")
