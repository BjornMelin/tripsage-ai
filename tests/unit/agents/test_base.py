"""Unit tests for :mod:`tripsage.agents.base`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage.agents.base import BaseAgent
from tripsage.agents.service_registry import ServiceRegistry


@pytest.fixture()
def mock_service_registry() -> ServiceRegistry:
    """Create a mock service registry for testing."""
    return MagicMock(spec=ServiceRegistry)


@pytest.fixture()
def mock_llm() -> MagicMock:
    """Create a mock LLM for testing."""
    return MagicMock(ainvoke=AsyncMock(return_value=MagicMock(content="Mock response")))


@pytest.mark.asyncio
async def test_base_agent_initialization(
    mock_service_registry: ServiceRegistry,
) -> None:
    """BaseAgent initializes with correct defaults."""
    agent = BaseAgent("test_agent", mock_service_registry)

    assert agent.name == "test_agent"
    assert agent.service_registry == mock_service_registry
    assert agent.instructions == (
        "You are TripSage, an expert travel planning assistant. Coordinate the "
        "specialized trip-planning agents, incorporate persisted user memories, "
        "and provide concise next steps for the traveller."
    )
    assert agent._summary_interval == 10  # type: ignore[reportPrivateUsage]
    assert agent._last_summary_index == 0  # type: ignore[reportPrivateUsage]
    assert agent._orchestrator is None  # type: ignore[reportPrivateUsage]
    assert not agent.messages_history
    assert isinstance(agent.session_id, str)
    assert not agent.session_data


@pytest.mark.asyncio
async def test_base_agent_custom_instructions(
    mock_service_registry: ServiceRegistry,
) -> None:
    """BaseAgent accepts custom instructions."""
    custom_instructions = "Custom test instructions"
    agent = BaseAgent(
        "test_agent", mock_service_registry, instructions=custom_instructions
    )

    assert agent.instructions == custom_instructions


@pytest.mark.asyncio
async def test_base_agent_custom_llm(
    mock_service_registry: ServiceRegistry, mock_llm: MagicMock
) -> None:
    """BaseAgent accepts custom LLM."""
    agent = BaseAgent("test_agent", mock_service_registry, llm=mock_llm)

    assert agent.llm == mock_llm


@pytest.mark.asyncio
async def test_base_agent_custom_summary_interval(
    mock_service_registry: ServiceRegistry,
) -> None:
    """BaseAgent accepts custom summary interval."""
    agent = BaseAgent("test_agent", mock_service_registry, summary_interval=5)

    assert agent._summary_interval == 5  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_base_agent_run_with_orchestrator_success(
    mock_service_registry: ServiceRegistry,
) -> None:
    """BaseAgent run method succeeds with orchestrator."""
    # Mock orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.process_message = AsyncMock(
        return_value={
            "response": "Test response",
            "session_id": "test-session",
            "agent_used": "test_agent",
        }
    )

    agent = BaseAgent("test_agent", mock_service_registry)
    agent._ensure_orchestrator = AsyncMock(return_value=mock_orchestrator)  # type: ignore[reportPrivateUsage]
    agent._hydrate_session = AsyncMock()  # type: ignore[reportPrivateUsage]
    agent._should_summarize = MagicMock(return_value=False)  # type: ignore[reportPrivateUsage]

    result = await agent.run("Test input", user_id="user123")

    assert result["response"] == "Test response"
    assert result["session_id"] == "test-session"
    assert result["agent_used"] == "test_agent"
    assert len(agent.messages_history) == 2  # user + assistant
    assert agent.messages_history[0]["role"] == "user"
    assert agent.messages_history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_base_agent_run_fallback_on_orchestrator_failure(
    mock_service_registry: ServiceRegistry,
    mock_llm: MagicMock,
) -> None:
    """BaseAgent falls back to direct LLM when orchestrator fails."""
    agent = BaseAgent("test_agent", mock_service_registry, llm=mock_llm)
    agent._ensure_orchestrator = AsyncMock(side_effect=Exception("Orchestrator error"))  # type: ignore[reportPrivateUsage]
    agent._hydrate_session = AsyncMock()  # type: ignore[reportPrivateUsage]
    agent._generate_fallback_response = AsyncMock(return_value="Fallback response")  # type: ignore[reportPrivateUsage]

    result = await agent.run("Test input", user_id="user123")

    assert result["response"] == "Fallback response"
    assert result["agent_used"] == "test_agent"
    assert "error" in result
    assert len(agent.messages_history) == 2


@pytest.mark.asyncio
async def test_base_agent_should_summarize() -> None:
    """BaseAgent summarizes when message count reaches interval."""
    mock_service_registry = MagicMock()
    agent = BaseAgent("test_agent", mock_service_registry, summary_interval=3)

    # Initially should not summarize
    assert not agent._should_summarize()  # type: ignore[reportPrivateUsage]

    # Add messages
    agent.messages_history = [{"role": "user"}, {"role": "assistant"}, {"role": "user"}]
    assert agent._should_summarize()  # type: ignore[reportPrivateUsage]

    # After summary, should reset
    agent._last_summary_index = len(agent.messages_history)  # type: ignore[reportPrivateUsage]
    assert not agent._should_summarize()  # type: ignore[reportPrivateUsage]


def test_base_agent_now() -> None:
    """BaseAgent _now method returns current timestamp."""
    mock_service_registry = MagicMock()
    agent = BaseAgent("test_agent", mock_service_registry)

    timestamp = agent._now()  # type: ignore[reportPrivateUsage]
    assert isinstance(timestamp, str)
    # Should be ISO format
    assert "T" in timestamp
