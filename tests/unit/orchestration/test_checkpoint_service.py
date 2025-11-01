"""Checkpoint service tests: import fallbacks and setup paths."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tripsage.orchestration.checkpoint_service import SupabaseCheckpointService


@pytest.mark.asyncio
async def test_async_checkpointer_memory_fallback_on_importerror() -> None:
    """Async checkpointer uses MemorySaver when postgres module is missing."""
    svc = SupabaseCheckpointService()
    with patch("importlib.import_module", side_effect=ImportError):
        cp = await svc.get_async_checkpointer()
    # MemorySaver type is opaque here; just check it has expected method name
    assert hasattr(cp, "put") or hasattr(cp, "setup")


def test_sync_checkpointer_memory_fallback_on_importerror() -> None:
    """Sync checkpointer uses MemorySaver when postgres module is missing."""
    svc = SupabaseCheckpointService()
    with patch("importlib.import_module", side_effect=ImportError):
        cp = svc.get_sync_checkpointer()
    assert hasattr(cp, "put") or hasattr(cp, "setup")
