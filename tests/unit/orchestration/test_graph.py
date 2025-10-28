"""Graph/orchestrator behavior tests: init fallback and branch decisions."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from tests.unit.orchestration.test_utils import (
    create_mock_services,
    patch_openai_in_module,
)
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.state import TravelPlanningState, create_initial_state


def _make_services(checkpoint: Any | None = None) -> AppServiceContainer:
    """Create DI container with checkpoint and memory bridge services."""
    checkpoint_service = MagicMock()
    if checkpoint is None:
        checkpoint_service.get_async_checkpointer = AsyncMock(
            side_effect=RuntimeError("db down")
        )
    else:
        checkpoint_service.get_async_checkpointer = AsyncMock(return_value=checkpoint)
    memory_bridge = MagicMock()
    memory_bridge.hydrate_state = AsyncMock(side_effect=RuntimeError("mem fail"))
    memory_bridge.extract_and_persist_insights = AsyncMock(return_value={"ok": True})
    configuration_service = MagicMock()
    configuration_service.get_agent_config = AsyncMock(
        return_value={
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "top_p": 1.0,
            "api_key": "test",
        }
    )
    return create_mock_services(
        {
            "checkpoint_service": checkpoint_service,
            "memory_bridge": memory_bridge,
            "configuration_service": configuration_service,
        }
    )


def _make_orchestrator(services: AppServiceContainer) -> TripSageOrchestrator:
    """Build orchestrator with patched coordinator and config."""
    with (
        patch("tripsage.orchestration.graph.get_handoff_coordinator") as coord_patch,
        patch("tripsage.orchestration.graph.get_default_config", return_value={}),
    ):
        coord_patch.return_value.determine_next_agent = MagicMock(return_value=None)
        return TripSageOrchestrator(services=services)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.routing")
async def test_initialize_fallback_to_memory_saver() -> None:
    """When checkpoint service fails, initialize should use MemorySaver fallback."""
    services = _make_services(checkpoint=None)
    orch = _make_orchestrator(services)

    await orch.initialize()

    # Compiled and using MemorySaver fallback
    assert orch.compiled_graph is not None  # type: ignore[reportPrivateUsage]
    assert isinstance(orch.checkpointer, MemorySaver)  # type: ignore[attr-defined]


def test_determine_next_step_error_memory_end_continue() -> None:
    """_determine_next_step returns expected branch keys for common cases."""
    services = _make_services(checkpoint=MagicMock())
    orch = _make_orchestrator(services)

    # Error path
    st: TravelPlanningState = create_initial_state("u", "hi")
    st["error_info"]["error_count"] = 1
    assert orch._determine_next_step(st) == "error"  # type: ignore[reportPrivateUsage]

    # Memory path
    st = create_initial_state("u", "hi")
    st["user_preferences"] = {"items": ["window seat"]}
    assert orch._determine_next_step(st) == "memory"  # type: ignore[reportPrivateUsage]

    # Assistant asked a question → end
    st = create_initial_state("u", "hi")
    st["messages"].append({"role": "assistant", "content": "Would you like more?"})
    assert orch._determine_next_step(st) == "end"  # type: ignore[reportPrivateUsage]

    # Default continue when last message not assistant and no other signals
    st = create_initial_state("u", "hi")
    assert orch._determine_next_step(st) == "continue"  # type: ignore[reportPrivateUsage]


def test_handle_recovery_thresholds() -> None:
    """_handle_recovery retries below threshold, ends otherwise."""
    services = _make_services(checkpoint=MagicMock())
    orch = _make_orchestrator(services)

    st = create_initial_state("u", "hi")
    st["error_info"]["error_count"] = 2
    assert orch._handle_recovery(st) == "retry"  # type: ignore[reportPrivateUsage]
    st["error_info"]["error_count"] = 3
    assert orch._handle_recovery(st) == "end"  # type: ignore[reportPrivateUsage]


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.routing")
async def test_process_message_hydration_error_and_response_pick() -> None:
    """process_message should handle hydration errors and return assistant reply."""
    services = _make_services(checkpoint=MagicMock())
    orch = _make_orchestrator(services)
    await orch.initialize()

    result = await orch.process_message("user-1", "hello")
    assert isinstance(result["response"], str)
    assert result["session_id"]
