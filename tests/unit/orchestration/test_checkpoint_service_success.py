"""Checkpoint service success-path tests with importlib stubs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.orchestration.checkpoint_service import SupabaseCheckpointService


def _patch_settings(url: str = "postgresql://user:pass@host:5432/db"):
    """Patch get_settings to provide required database fields."""

    class _Settings:
        database_url = url
        database_service_key = MagicMock()
        database_service_key.get_secret_value = MagicMock(return_value="svc-key")

    return patch(
        "tripsage.orchestration.checkpoint_service.get_settings",
        return_value=_Settings(),
    )


@pytest.mark.asyncio
async def test_async_checkpointer_success_path() -> None:
    """Async saver stub is built via importlib; setup() awaited."""
    svc = SupabaseCheckpointService()

    class _AsyncSaver:
        """Async Postgres saver stub with setup()."""

        def __init__(self) -> None:
            """Initialize the class."""
            self.setup = AsyncMock(return_value=None)

        @classmethod
        async def from_conn_string(cls, _cs: str) -> object:
            """Return a new instance of the class."""
            return cls()

    with (
        _patch_settings(),
        patch(
            "tripsage.orchestration.checkpoint_service.importlib.import_module"
        ) as imp,
    ):
        mod = MagicMock()
        mod.AsyncPostgresSaver = _AsyncSaver
        imp.return_value = mod
        checkp = await svc.get_async_checkpointer()
        # Should be our async saver instance and setup called
        assert hasattr(checkp, "setup")
        checkp.setup.assert_awaited()  # type: ignore[attr-defined]


def test_sync_checkpointer_success_path() -> None:
    """Sync saver stub is built via importlib; setup() called once."""
    svc = SupabaseCheckpointService()

    class _SyncSaver:
        """Sync Postgres saver stub with setup()."""

        def __init__(self) -> None:
            """Initialize the class."""
            self.setup = MagicMock(return_value=None)

        @classmethod
        def from_conn_string(cls, _cs: str) -> object:
            """Return a new instance of the class."""
            return cls()

    with (
        _patch_settings(),
        patch(
            "tripsage.orchestration.checkpoint_service.importlib.import_module"
        ) as imp,
    ):
        mod = MagicMock()
        mod.PostgresSaver = _SyncSaver
        imp.return_value = mod
        checkp = svc.get_sync_checkpointer()
        assert hasattr(checkp, "setup")
        checkp.setup.assert_called_once()  # type: ignore[attr-defined]
