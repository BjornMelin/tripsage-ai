"""Unit tests for :mod:`tripsage.agents.base`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.unit.orchestration.test_utils import create_mock_services
from tripsage.agents.base import BaseAgent
from tripsage.app_state import AppServiceContainer


class DummyAgent(BaseAgent):
    """BaseAgent variant that injects a lightweight mock LLM."""

    def _create_llm(self) -> MagicMock:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=MagicMock(content="fallback"))
        return llm


@pytest.fixture()
def services() -> AppServiceContainer:
    """Provide an app service container populated with minimal mocks."""
    container = create_mock_services()
    container.memory_service = MagicMock()
    return container


@pytest.fixture()
def orchestrator() -> MagicMock:
    """Return an orchestrator stub wired for BaseAgent interactions."""
    orchestrator = MagicMock()
    orchestrator.process_message = AsyncMock(
        return_value={
            "response": "Test response",
            "session_id": "session-123",
            "agent_used": "test_agent",
        }
    )
    orchestrator.initialize = AsyncMock()
    return orchestrator


@pytest.fixture()
def mock_llm() -> MagicMock:
    """Return a chat model stub with an async invoke method."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="Mock response"))
    return llm


@pytest.mark.asyncio
async def test_base_agent_initialization(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """BaseAgent initializes with correct defaults."""
    agent = DummyAgent("test_agent", services, orchestrator)

    assert agent.name == "test_agent"
    assert agent.services is services
    assert agent.instructions.startswith("You are TripSage")
    assert agent._summary_interval == 10  # type: ignore[reportPrivateUsage]
    assert agent._last_summary_index == 0  # type: ignore[reportPrivateUsage]
    assert agent.messages_history == []
    assert isinstance(agent.session_id, str)
    assert agent.session_data == {}


@pytest.mark.asyncio
async def test_base_agent_custom_instructions(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """BaseAgent accepts custom instructions."""
    custom_instructions = "Custom test instructions"
    agent = DummyAgent(
        "test_agent",
        services,
        orchestrator,
        instructions=custom_instructions,
    )

    assert agent.instructions == custom_instructions


@pytest.mark.asyncio
async def test_base_agent_custom_llm(
    services: AppServiceContainer,
    orchestrator: MagicMock,
    mock_llm: MagicMock,
) -> None:
    """BaseAgent accepts custom LLM."""
    agent = BaseAgent(
        "test_agent",
        services,
        orchestrator,
        llm=mock_llm,
    )

    assert agent.llm is mock_llm


@pytest.mark.asyncio
async def test_base_agent_custom_summary_interval(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """BaseAgent accepts custom summary interval."""
    agent = DummyAgent(
        "test_agent",
        services,
        orchestrator,
        summary_interval=5,
    )

    assert agent._summary_interval == 5  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_base_agent_run_with_orchestrator_success(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """BaseAgent run method succeeds with orchestrator."""
    agent = DummyAgent("test_agent", services, orchestrator)

    result = await agent.run("Test input", user_id="user123")

    orchestrator.process_message.assert_awaited_once()
    assert result["response"] == "Test response"
    assert result["session_id"] == "session-123"
    assert result["agent_used"] == "test_agent"
    assert len(agent.messages_history) == 2
    assert agent.messages_history[0]["role"] == "user"
    assert agent.messages_history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_base_agent_run_fallback_on_orchestrator_failure(
    services: AppServiceContainer,
    orchestrator: MagicMock,
    mock_llm: MagicMock,
) -> None:
    """BaseAgent falls back to direct LLM when orchestrator fails."""
    agent = BaseAgent(
        "test_agent",
        services,
        orchestrator,
        llm=mock_llm,
    )
    orchestrator.process_message.side_effect = RuntimeError("Orchestrator error")

    result = await agent.run("Test input", user_id="user123")

    assert result["response"] == "Mock response"
    assert result["agent_used"] == "test_agent"
    assert "error" in result
    assert len(agent.messages_history) == 2


@pytest.mark.asyncio
async def test_base_agent_should_summarize(
    services: AppServiceContainer, orchestrator: MagicMock
) -> None:
    """BaseAgent summarizes when message count reaches interval."""
    agent = DummyAgent("test_agent", services, orchestrator, summary_interval=3)

    assert not agent._should_summarize()  # type: ignore[reportPrivateUsage]

    agent.messages_history = [
        {"role": "user"},
        {"role": "assistant"},
        {"role": "user"},
    ]
    assert agent._should_summarize()  # type: ignore[reportPrivateUsage]

    agent._last_summary_index = len(agent.messages_history)  # type: ignore[reportPrivateUsage]
    assert not agent._should_summarize()  # type: ignore[reportPrivateUsage]


def test_base_agent_now(services: AppServiceContainer, orchestrator: MagicMock) -> None:
    """BaseAgent _now method returns current timestamp."""
    agent = DummyAgent("test_agent", services, orchestrator)

    timestamp = agent._now()  # type: ignore[reportPrivateUsage]
    assert isinstance(timestamp, str)
    assert "T" in timestamp
