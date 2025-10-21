"""Unit tests for ConfigurationService (Supabase-only paths)."""

from typing import Any

import pytest

from tripsage_core.services.configuration_service import ConfigurationService


@pytest.mark.asyncio
async def test_get_agent_config_uses_db_and_overrides(monkeypatch):
    """Returns DB config merged with overrides; cache calls mocked."""
    svc = ConfigurationService()

    # Avoid real cache I/O
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(
        "tripsage_core.services.configuration_service.get_cache", _noop, raising=False
    )
    monkeypatch.setattr(
        "tripsage_core.services.configuration_service.set_cache", _noop, raising=False
    )

    async def ensure_connected() -> None:
        return None

    async def select(
        table: str, columns: str, *, filters: dict[str, Any], limit: int = 1
    ) -> list[dict[str, Any]]:
        assert table == "configuration_profiles"
        assert "agent_type" in filters and "environment" in filters
        return [
            {
                "model": "gpt-4o",
                "temperature": 0.2,
                "max_tokens": 1000,
                "top_p": 0.9,
                "timeout_seconds": 30,
                "description": "unit",
                "updated_at": "2025-01-01T00:00:00Z",
                "updated_by": "tester",
            }
        ]

    monkeypatch.setattr(svc._db, "ensure_connected", ensure_connected)  # type: ignore[attr-defined]
    monkeypatch.setattr(svc._db, "select", select)  # type: ignore[attr-defined]

    cfg = await svc.get_agent_config("agent", "test", temperature=0.3)
    assert cfg["model"] == "gpt-4o"
    assert cfg["temperature"] == 0.3  # override applied


@pytest.mark.asyncio
async def test_update_agent_config_insert_then_update(monkeypatch):
    """Inserts when missing then updates existing; clears cache."""
    svc = ConfigurationService()

    # State to switch select behavior
    state = {"have_row": False}

    async def ensure_connected() -> None:
        return None

    async def select(
        table: str, columns: str, *, filters: dict[str, Any], limit: int = 1
    ) -> list[dict[str, Any]]:
        if not state["have_row"]:
            return []
        return [
            {
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "max_tokens": 800,
                "top_p": 0.8,
                "timeout_seconds": 20,
                "description": "after",
                "updated_at": "2025-01-02T00:00:00Z",
                "updated_by": "tester",
            }
        ]

    called: dict[str, Any] = {"insert": None, "update": None}

    async def insert(table: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        called["insert"] = payload
        # After insert, pretend the row exists
        state["have_row"] = True
        return [payload]

    async def update(
        table: str, update_fields: dict[str, Any], *, filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        called["update"] = update_fields
        return [update_fields]

    # Avoid real cache I/O
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(
        "tripsage_core.services.configuration_service.delete_cache",
        _noop,
        raising=False,
    )
    monkeypatch.setattr(
        "tripsage_core.services.configuration_service.get_cache", _noop, raising=False
    )
    monkeypatch.setattr(
        "tripsage_core.services.configuration_service.set_cache", _noop, raising=False
    )
    monkeypatch.setattr(svc._db, "ensure_connected", ensure_connected)  # type: ignore[attr-defined]
    monkeypatch.setattr(svc._db, "select", select)  # type: ignore[attr-defined]
    monkeypatch.setattr(svc._db, "insert", insert)  # type: ignore[attr-defined]
    monkeypatch.setattr(svc._db, "update", update)  # type: ignore[attr-defined]

    # First call should insert
    _ = await svc.update_agent_config(
        "agent",
        config_updates={"temperature": 0.5, "max_tokens": 800, "model": "gpt-4o-mini"},
        updated_by="tester",
        environment="test",
        description="after",
    )
    assert called["insert"] is not None

    # Second call should update existing
    updated = await svc.update_agent_config(
        "agent",
        config_updates={"temperature": 0.5},
        updated_by="tester",
        environment="test",
    )
    assert called["update"] is not None
    assert updated["model"] == "gpt-4o-mini"
    assert updated["temperature"] == 0.5
