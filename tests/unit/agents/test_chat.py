"""Unit tests for :mod:`tripsage.agents.chat`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage.agents.chat import ChatAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.services.business.chat_service import ChatService


@pytest.fixture()
def mock_service_registry() -> ServiceRegistry:
    """Create a mock service registry for testing."""
    return MagicMock(spec=ServiceRegistry)


@pytest.fixture()
def mock_chat_service() -> ChatService:
    """Create a mock chat service for testing."""
    return MagicMock(spec=ChatService)


@pytest.fixture()
def chat_agent(mock_service_registry: ServiceRegistry) -> ChatAgent:
    """Create a ChatAgent instance for testing."""
    return ChatAgent(mock_service_registry)


def test_chat_agent_initialization(
    chat_agent: ChatAgent, mock_service_registry: ServiceRegistry
) -> None:
    """ChatAgent initializes with correct defaults."""
    assert chat_agent.name == "chat_agent"
    assert chat_agent.service_registry == mock_service_registry
    assert chat_agent.instructions == (
        "You are the TripSage chat coordinator. Greet the traveller, determine their "
        "goal, and delegate to the appropriate specialized agents when needed. "
        "Keep responses friendly, actionable, and under 120 words."
    )
    assert chat_agent._summary_interval == 8  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_process_message(chat_agent: ChatAgent) -> None:
    """process_message delegates to run method."""
    chat_agent.run = AsyncMock(return_value={"response": "test", "session_id": "123"})

    result = await chat_agent.process_message(
        user_id="user123",
        message="Hello",
        session_id="session123",
        context={"key": "value"},
    )

    chat_agent.run.assert_called_once_with(
        "Hello", user_id="user123", session_id="session123", context={"key": "value"}
    )
    assert result == {"response": "test", "session_id": "123"}


@pytest.mark.asyncio
async def test_fetch_conversation_history_with_chat_service(
    chat_agent: ChatAgent, mock_chat_service: ChatService
) -> None:
    """fetch_conversation_history uses chat service when available."""
    mock_messages = [MagicMock(), MagicMock()]
    mock_messages[0].model_dump.return_value = {"role": "user", "content": "Hello"}
    mock_messages[1].model_dump.return_value = {"role": "assistant", "content": "Hi"}

    mock_chat_service.get_messages = AsyncMock(return_value=mock_messages)
    chat_agent.service_registry.get_optional_service = MagicMock(
        return_value=mock_chat_service
    )

    result = await chat_agent.fetch_conversation_history(
        "user123", "session123", limit=10
    )

    chat_agent.service_registry.get_optional_service.assert_called_once_with(
        "chat_service", expected_type=ChatService
    )
    mock_chat_service.get_messages.assert_called_once_with("session123", "user123", 10)
    assert result == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]


@pytest.mark.asyncio
async def test_fetch_conversation_history_without_chat_service(
    chat_agent: ChatAgent,
) -> None:
    """Test fetch_conversation_history falls back.

    Falls back to local history when chat service unavailable.
    """
    chat_agent.service_registry.get_optional_service = MagicMock(return_value=None)
    chat_agent.messages_history = [{"role": "user", "content": "Hello"}]
    chat_agent._local_history = MagicMock(  # type: ignore[reportPrivateUsage]
        return_value=[{"role": "user", "content": "Hello"}]
    )

    result = await chat_agent.fetch_conversation_history(
        "user123", "session123", limit=5
    )

    assert result == [{"role": "user", "content": "Hello"}]


@pytest.mark.asyncio
async def test_fetch_conversation_history_with_exception(chat_agent: ChatAgent) -> None:
    """fetch_conversation_history handles exceptions gracefully."""
    chat_agent.service_registry.get_optional_service = MagicMock(
        side_effect=Exception("Service error")
    )
    chat_agent._local_history = MagicMock(  # type: ignore[reportPrivateUsage]
        return_value=[{"role": "user", "content": "Hello"}]
    )

    result = await chat_agent.fetch_conversation_history("user123", "session123")

    assert result == [{"role": "user", "content": "Hello"}]


@pytest.mark.asyncio
async def test_clear_conversation_history_with_chat_service(
    chat_agent: ChatAgent, mock_chat_service: ChatService
) -> None:
    """clear_conversation_history uses chat service when available."""
    mock_chat_service.end_session = AsyncMock(return_value=True)
    chat_agent.service_registry.get_optional_service = MagicMock(
        return_value=mock_chat_service
    )
    chat_agent.reset_session = MagicMock()

    result = await chat_agent.clear_conversation_history("user123", "session123")

    chat_agent.service_registry.get_optional_service.assert_called_once_with(
        "chat_service", expected_type=ChatService
    )
    mock_chat_service.end_session.assert_called_once_with("session123", "user123")
    chat_agent.reset_session.assert_called_once()
    assert result is True


@pytest.mark.asyncio
async def test_clear_conversation_history_without_chat_service(
    chat_agent: ChatAgent,
) -> None:
    """clear_conversation_history resets local session when chat service unavailable."""
    chat_agent.service_registry.get_optional_service = MagicMock(return_value=None)
    chat_agent.reset_session = MagicMock()

    result = await chat_agent.clear_conversation_history("user123", "session123")

    chat_agent.reset_session.assert_called_once()
    assert result is True


@pytest.mark.asyncio
async def test_clear_conversation_history_with_exception(chat_agent: ChatAgent) -> None:
    """clear_conversation_history handles exceptions gracefully."""
    chat_agent.service_registry.get_optional_service = MagicMock(
        side_effect=Exception("Service error")
    )

    result = await chat_agent.clear_conversation_history("user123", "session123")

    assert result is False


def test_local_history(chat_agent: ChatAgent) -> None:
    """_local_history returns messages respecting limit."""
    chat_agent.messages_history = [
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
    ]

    # Test with limit
    result = chat_agent._local_history(2)  # type: ignore[reportPrivateUsage]
    assert result == [
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
    ]

    # Test without limit
    result = chat_agent._local_history(None)  # type: ignore[reportPrivateUsage]
    assert result == chat_agent.messages_history


def test_get_available_agents(chat_agent: ChatAgent) -> None:
    """get_available_agents returns list of specialized agents."""
    agents = chat_agent.get_available_agents()
    expected = [
        "flight_agent",
        "accommodation_agent",
        "budget_agent",
        "destination_research_agent",
        "itinerary_agent",
    ]
    assert agents == expected


def test_get_agent_capabilities(chat_agent: ChatAgent) -> None:
    """get_agent_capabilities returns capabilities dictionary."""
    capabilities = chat_agent.get_agent_capabilities()

    assert "flight_agent" in capabilities
    assert "accommodation_agent" in capabilities
    assert "budget_agent" in capabilities
    assert "destination_research_agent" in capabilities
    assert "itinerary_agent" in capabilities

    # Check some specific capabilities
    assert "Search flights" in capabilities["flight_agent"]
    assert "Search hotels and accommodations" in capabilities["accommodation_agent"]
    assert "Budget planning and optimization" in capabilities["budget_agent"]
    assert "Destination research" in capabilities["destination_research_agent"]
    assert "Create detailed itineraries" in capabilities["itinerary_agent"]
