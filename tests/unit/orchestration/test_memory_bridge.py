"""SessionMemoryBridge tests: hydrate/map/checkpoint/restore."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from tripsage.orchestration.memory_bridge import SessionMemoryBridge
from tripsage.orchestration.state import create_initial_state


class _MemoryService:
    """Memory service stub."""

    def __init__(self, context: dict[str, Any]):
        """Initialize memory service stub."""
        self._context = context
        self.connect = AsyncMock(return_value=None)
        self.get_user_context = AsyncMock(return_value=self._context)
        self.add_conversation_memory = AsyncMock(return_value={"ok": True})


@pytest.mark.asyncio
async def test_hydrate_state_and_checkpoint_roundtrip() -> None:
    """Hydrate maps user context; checkpoint+restore preserves essentials."""
    context = {
        "preferences": ["window seat"],
        "past_trips": [{"destination": "Paris"}],
        "insights": {"likes": ["museums"]},
        "summary": "enjoys city breaks",
    }
    svc = _MemoryService(context)
    bridge = SessionMemoryBridge(cast(Any, svc))
    state = create_initial_state("u1", "hello")

    # Hydrate should map preferences/past_trips/insights/summary
    state = await bridge.hydrate_state(state)
    assert state.get("user_preferences")
    assert state.get("destination_info")
    assert state.get("conversation_summary")

    # Checkpoint format should include summaries but not full results
    ckpt = bridge.state_to_checkpoint_format(state)
    assert "flight_search_summary" not in ckpt

    # Restore should rehydrate (calls hydrate again under the hood)
    restored = await bridge.restore_from_checkpoint(ckpt)
    assert restored.get("user_id")
