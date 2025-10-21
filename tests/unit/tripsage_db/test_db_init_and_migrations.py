"""Unit tests for tripsage.db final implementation.

These tests validate local logic without hitting external services.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from tripsage.db.initialize import (
    create_sample_data,
    initialize_databases,
    verify_database_schema,
)
from tripsage.db.migrations.runner import MIGRATIONS_DIR


class _RPCResult:
    def __init__(self, data: Any):
        self.data = data

    def execute(self) -> "_RPCResult":
        return self


class _StubClient:
    def __init__(self, tables: list[str] | None = None):
        self._tables = tables or []

    def rpc(self, _name: str, _payload: dict[str, Any] | None = None) -> _RPCResult:
        # Minimal stub: when called by verify_database_schema, return rows
        rows = [{"tablename": t} for t in self._tables]
        # When called by initialize_databases(version) return a dummy string
        if _name == "version":
            return _RPCResult("14.10")
        return _RPCResult(rows)

    # The sample_data path uses .table(...).upsert(...).execute()
    def table(self, _name: str) -> "_StubClient":
        return self

    def upsert(self, _payload: dict[str, Any]) -> "_StubClient":
        return self

    def execute(self) -> SimpleNamespace:  # pragma: no cover - trivial
        return SimpleNamespace(data=[{"ok": True}])


@pytest.mark.asyncio
async def test_initialize_databases_no_verify_no_migrate(
    monkeypatch: pytest.MonkeyPatch,
):
    """initialize_databases returns True when no verification/migrations requested."""
    # Ensure get_supabase_client would not be used (verify=False), but keep stub ready
    monkeypatch.setattr(
        "tripsage.db.initialize.get_supabase_client",
        lambda: _StubClient(),
        raising=True,
    )

    ok = await initialize_databases(
        run_migrations_on_startup=False, verify_connections=False
    )
    assert ok is True


@pytest.mark.asyncio
async def test_verify_database_schema_parses_tables(monkeypatch: pytest.MonkeyPatch):
    """verify_database_schema parses RPC rows into table lists."""
    stub = _StubClient(["users", "trips"])  # migrations table intentionally missing
    monkeypatch.setattr(
        "tripsage.db.initialize.get_supabase_client", lambda: stub, raising=True
    )

    result = await verify_database_schema()
    assert sorted(result["sql"]["tables"]) == ["trips", "users"]
    assert "migrations" in result["sql"]["missing_tables"]


def test_migrations_dir_points_to_supabase():
    """MIGRATIONS_DIR points to the canonical supabase/migrations directory."""
    assert MIGRATIONS_DIR.name == "migrations"
    assert MIGRATIONS_DIR.parent.name == "supabase"
    assert MIGRATIONS_DIR.exists() and MIGRATIONS_DIR.is_dir()


@pytest.mark.asyncio
async def test_create_sample_data_uses_client(monkeypatch: pytest.MonkeyPatch):
    """create_sample_data returns True when client operations succeed."""
    monkeypatch.setattr(
        "tripsage.db.initialize.get_supabase_client",
        lambda: _StubClient(),
        raising=True,
    )
    ok = await create_sample_data()
    assert ok is True
