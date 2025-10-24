"""Tests for BaseAgent interacting with AppServiceContainer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import create_mock_services
from tripsage.agents.base import BaseAgent
from tripsage.app_state import AppServiceContainer


class TestAgent(BaseAgent):
    """Concrete BaseAgent subclass for testing DI wiring."""

    def _create_llm(self) -> MagicMock:
        """Return a minimal Chat model stub."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=MagicMock(content="fallback"))
        return llm


@pytest.fixture
def services() -> AppServiceContainer:
    """Provide services container with memory support."""
    container = create_mock_services()
    container.memory_service = MagicMock()
    return container


@pytest.fixture
def orchestrator() -> MagicMock:
    """Return orchestrator stub for BaseAgent interactions."""
    orchestrator = MagicMock()
    orchestrator.process_message = AsyncMock(
        return_value={
            "response": "orchestrated",
            "session_id": "session-1",
            "agent_used": "test_agent",
        }
    )
    orchestrator.initialize = AsyncMock()
    return orchestrator


@pytest.mark.asyncio
async def test_run_delegates_to_orchestrator(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """Run should delegate to orchestrator and capture responses."""
    agent = TestAgent(
        name="test_agent",
        services=services,
        orchestrator=orchestrator,
    )

    result = await agent.run("hello", user_id="user-1")

    orchestrator.process_message.assert_awaited_once()
    assert result["response"] == "orchestrated"
    assert agent.messages_history[-1]["content"] == "orchestrated"


@pytest.mark.asyncio
async def test_run_fallback_on_orchestrator_error(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """Run should fall back to LLM when orchestrator raises."""
    agent = TestAgent(
        name="test_agent",
        services=services,
        orchestrator=orchestrator,
    )
    orchestrator.process_message.side_effect = RuntimeError("boom")

    result = await agent.run("hello", user_id="user-1")

    assert result["response"] == "fallback"
    assert result["error"] == "Orchestration unavailable; responded with fallback LLM."
    assert agent.messages_history[-1]["fallback"] is True
