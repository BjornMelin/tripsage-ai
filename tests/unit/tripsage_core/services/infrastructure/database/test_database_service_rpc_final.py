"""RPC-based tests for DatabaseService.execute_sql in Supabase-only mode.

These tests stub the Supabase client to avoid network and SQLAlchemy.
"""

from __future__ import annotations

from typing import Any

import pytest

from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.services.infrastructure.database_service import DatabaseService


class _DummyResult:
    def __init__(self, data: Any):
        """Initialize the DummyResult."""
        self.data = data


class _DummyRPC:
    def __init__(self, payload: dict[str, Any]):
        """Initialize the DummyRPC."""
        self._payload = payload

    def execute(self) -> _DummyResult:
        """Execute the DummyRPC."""
        # Echo back payload to simulate RPC behavior
        return _DummyResult([{"echo": self._payload}])


class _DummyClient:
    def __init__(self):
        """Initialize the DummyClient."""
        self._last = None  # type: ignore[assignment]
        self.raise_error = False

    def rpc(self, fn: str, params: dict[str, Any]) -> _DummyRPC:
        """RPC the DummyClient."""
        if self.raise_error:
            raise RuntimeError("rpc failure")
        self._last = {"fn": fn, "params": params}
        return _DummyRPC(params)

    # Table used by health_check() and other code paths we don't exercise here
    def table(self, name: str):  # pragma: no cover - not used in these tests
        """Table the DummyClient."""
        raise NotImplementedError


@pytest.mark.anyio
async def test_execute_sql_rpc_roundtrip() -> None:
    """Test execute_sql RPC roundtrip."""
    svc = DatabaseService()
    svc._connected = True  # type: ignore[attr-defined]
    dummy = _DummyClient()
    svc._supabase_client = dummy  # type: ignore[attr-defined]

    result = await svc.execute_sql("SELECT 1", {"a": 1})
    assert result == [{"echo": {"sql": "SELECT 1", "params": {"a": 1}}}]


@pytest.mark.anyio
async def test_execute_sql_rpc_error_maps_to_coredberror() -> None:
    """Test execute_sql RPC error maps to CoreDatabaseError."""
    svc = DatabaseService()
    svc._connected = True  # type: ignore[attr-defined]
    dummy = _DummyClient()
    dummy.raise_error = True
    svc._supabase_client = dummy  # type: ignore[attr-defined]

    with pytest.raises(CoreDatabaseError) as ei:
        await svc.execute_sql("BAD", None)
    assert ei.value.code == "SQL_EXECUTION_FAILED"
