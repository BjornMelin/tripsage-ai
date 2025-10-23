"""Unit tests for final memory tools.

These tests isolate MemoryService via monkeypatch to avoid network or DB access.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tripsage.tools.memory_tools import (
    add_conversation_memory,
    get_destination_memories,
    get_user_context,
    search_user_memories,
)
from tripsage.tools.models import ConversationMessage, MemorySearchQuery


class _DummySvc:
    """Dummy service for testing."""

    def __init__(self) -> None:
        """Initialize the dummy service."""
        self.add_args: list[Any] = []
        self.search_args: list[Any] = []
        self.ctx_calls: list[str] = []

    async def connect(self) -> None:  # pragma: no cover - not used directly
        """Connect to the dummy service."""
        return

    async def add_conversation_memory(self, user_id: str, req: Any) -> dict[str, Any]:
        """Add a conversation memory."""
        self.add_args.append((user_id, req))
        return {"results": [{"id": "m1"}], "usage": {"total_tokens": 10}}

    async def search_memories(self, user_id: str, req: Any) -> list[Any]:
        """Search for memories."""
        self.search_args.append((user_id, req))

        # Emulate pydantic model with model_dump
        class _R:
            """Search result."""

            def __init__(self, i: int) -> None:
                """Initialize the search result."""
                self.i = i

            def model_dump(self) -> dict[str, Any]:
                """Dump the search result."""
                return {"id": f"mid-{self.i}", "user_id": user_id, "memory": "x"}

        return [_R(1), _R(2)]

    async def get_user_context(self, user_id: str):  # type: ignore[override]
        """Get user context."""
        self.ctx_calls.append(user_id)

        class _Ctx:
            def model_dump(self, *, exclude_none: bool = True) -> dict[str, Any]:
                """Dump the user context."""
                return {"preferences": [], "insights": {}}

        return _Ctx()


@pytest.mark.asyncio
async def test_add_conversation_memory_monkeypatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test add conversation memory with monkeypatch."""
    dummy = _DummySvc()
    monkeypatch.setattr(
        "tripsage.tools.memory_tools.get_memory_service",
        lambda: asyncio.sleep(0, result=dummy),
    )
    res = await add_conversation_memory(
        messages=[ConversationMessage(role="user", content="hello")],
        user_id="u1",
    )
    assert res["status"] == "success"
    assert res["memories_extracted"] == 1
    assert len(dummy.add_args) == 1


@pytest.mark.asyncio
async def test_search_user_memories_builds_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test search user memories with monkeypatch."""
    dummy = _DummySvc()
    monkeypatch.setattr(
        "tripsage.tools.memory_tools.get_memory_service",
        lambda: asyncio.sleep(0, result=dummy),
    )
    results = await search_user_memories(
        MemorySearchQuery(query="paris", user_id="u1", limit=2, category_filter=None)
    )
    assert len(results) == 2
    assert dummy.search_args and dummy.search_args[0][0] == "u1"


@pytest.mark.asyncio
async def test_get_user_context_validation() -> None:
    """Test get_user_context rejects empty user ID."""
    with pytest.raises(ValueError):
        await get_user_context("")


@pytest.mark.asyncio
async def test_get_destination_memories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_destination_memories searches with user scope."""
    dummy = _DummySvc()
    monkeypatch.setattr(
        "tripsage.tools.memory_tools.get_memory_service",
        lambda: asyncio.sleep(0, result=dummy),
    )
    # Calls search via user scope
    res = await get_destination_memories("Paris", user_id="u9")
    assert res["status"] == "success"
    assert res["destination"] == "Paris"
