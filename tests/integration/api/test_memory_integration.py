"""Integration tests for memory conversation POST with limiter path."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


class _MemSvc:
    async def add_conversation_memory(
        self, user_id: str, payload: Any
    ) -> dict[str, object]:
        """Persist a conversation memory and echo minimal confirmation.

        Args:
            user_id: Current user identifier.
            payload: Request body accepted by the router.

        Returns:
            dict[str, object]: Minimal success response including ``user_id``.
        """
        return {"ok": True, "user_id": user_id}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_conversation_post(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient], principal: Any
) -> None:
    """POST conversation succeeds and includes user_id in response."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        return principal

    def _provide_memsvc() -> _MemSvc:
        return _MemSvc()

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_memory_service] = _provide_memsvc  # type: ignore[assignment]

    client = async_client_factory(app)
    payload = {"messages": [{"role": "user", "content": "hi"}], "session_id": "s1"}
    r = await client.post("/api/memory/conversation", json=payload)
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body.get("ok") is True and body.get("user_id") == principal.id
