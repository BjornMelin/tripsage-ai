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


@pytest.mark.asyncio
async def test_hydrate_failure_logs_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hydrate should handle service errors without crashing."""

    class _BadService:
        """Bad service stub."""

        async def connect(self):
            """Simulate failing connection for memory service."""
            raise RuntimeError("down")

    bridge = SessionMemoryBridge(cast(Any, _BadService()))
    state = create_initial_state("u1", "hi")
    out = await bridge.hydrate_state(state)
    assert out is state


@pytest.mark.asyncio
async def test_no_insights_returns_empty() -> None:
    """No insights should return {} from extract_and_persist_insights."""
    svc = _MemoryService({})
    bridge = SessionMemoryBridge(cast(Any, svc))
    state = create_initial_state("u1", "hi")
    result = await bridge.extract_and_persist_insights(state)
    assert result == {}


@pytest.mark.asyncio
async def test_store_checkpoint_reference_error_safe() -> None:
    """Store should swallow errors; errors only logged, not raised."""

    class _S(_MemoryService):
        """Test subclass of _MemoryService."""

        def __init__(self):
            """Initialize test subclass of _MemoryService."""
            super().__init__({})
            self.add_conversation_memory.side_effect = Exception("boom")  # type: ignore[attr-defined]

    svc = _S()
    bridge = SessionMemoryBridge(cast(Any, svc))
    # Should not raise
    await bridge.store_session_checkpoint_reference("u1", "s1", "ck1", {})
