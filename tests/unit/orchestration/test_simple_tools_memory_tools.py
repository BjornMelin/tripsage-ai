"""Unit tests for LangGraph simple memory tools wiring.

These tests monkeypatch the memory bridge functions to avoid external deps.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from tripsage.orchestration.tools.simple_tools import add_memory, search_memories


@pytest.mark.asyncio
async def test_add_memory_invokes_facade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test add_memory tool invokes facade."""

    async def _fake_add(**kwargs):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)
        assert "messages" in kwargs
        return {"status": "success", "memories_extracted": 1}

    monkeypatch.setattr(
        "tripsage.orchestration.tools.simple_tools._add_conversation_memory",
        _fake_add,
    )
    out = await add_memory.ainvoke("Note A", None)
    payload = json.loads(out)
    assert payload["status"] == "success"


@pytest.mark.asyncio
async def test_search_memories_invokes_facade(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test search_memories tool invokes facade."""

    async def _fake_search(_query):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)
        return [{"id": "m1"}]

    monkeypatch.setattr(
        "tripsage.orchestration.tools.simple_tools._search_user_memories",
        _fake_search,
    )
    out = await search_memories.ainvoke("Paris", None)
    payload = json.loads(out)
    assert payload["results"] == [{"id": "m1"}]
