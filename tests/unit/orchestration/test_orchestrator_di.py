"""Tests for TripSageOrchestrator using AppServiceContainer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.unit.orchestration.test_utils import create_mock_services
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.state import create_initial_state


@pytest.fixture
def services() -> AppServiceContainer:
    """Provide a mock AppServiceContainer with orchestrator dependencies."""
    checkpoint_service = MagicMock()
    checkpoint_service.get_async_checkpointer = AsyncMock(
        return_value=MagicMock(name="checkpoint")
    )
    memory_bridge = MagicMock()
    return create_mock_services(
        {
            "checkpoint_service": checkpoint_service,
            "memory_bridge": memory_bridge,
        }
    )


@pytest.fixture
def orchestrator(services: AppServiceContainer) -> TripSageOrchestrator:
    """Instantiate TripSageOrchestrator with patched collaborators."""
    with (
        patch("tripsage.orchestration.graph.get_handoff_coordinator") as coord_patch,
        patch("tripsage.orchestration.graph.get_default_config", return_value={}),
    ):
        coord_patch.return_value.determine_next_agent = MagicMock(return_value=None)
        return TripSageOrchestrator(services=services)


async def test_initialize_compiles_graph(
    orchestrator: TripSageOrchestrator,
) -> None:
    """Initialize should compile the graph and mark orchestrator as ready."""
    await orchestrator.initialize()

    assert orchestrator._initialized is True
    assert orchestrator.compiled_graph is not None


def test_route_to_agent_handles_unknown(orchestrator: TripSageOrchestrator) -> None:
    """_route_to_agent should fall back to general agent on unknown types."""
    state = create_initial_state("user-123", "plan my trip")
    state["current_agent"] = "nonexistent"
    state["error_info"]["error_count"] = 0

    agent = orchestrator._route_to_agent(state)

    assert agent == "general_agent"


@pytest.mark.asyncio
async def test_get_session_state_returns_none_without_state(
    orchestrator: TripSageOrchestrator,
) -> None:
    """get_session_state should return None when the thread state is missing."""
    await orchestrator.initialize()

    result = await orchestrator.get_session_state("missing-session")

    assert result is None
