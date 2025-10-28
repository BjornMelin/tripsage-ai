"""Integration tests for API key rotation negative branches.

Covers:
- 404 when key not found
- 403 when key belongs to another user
- 400 when new key validation fails
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient


class _KeyService:
    """Key service stub for rotate endpoint negative cases."""

    def __init__(self, owner_id: str) -> None:
        """Initialize with one owned key."""
        self.owner_id = owner_id
        self._keys: dict[str, dict[str, Any]] = {
            "k1": {"id": "k1", "service": "openai", "user_id": owner_id}
        }

    async def get_key(self, key_id: str) -> dict[str, Any] | None:
        """Fetch key record by ID."""
        return self._keys.get(key_id)

    async def validate_key(
        self, key: str, service: str, user_id: str | None = None
    ) -> Any:
        """Return an invalid validation result for testing 400 branch."""

        class _Res:
            is_valid = False
            message = "Invalid"

        return _Res()

    async def rotate_key(
        self, key_id: str, new_key: str, user_id: str
    ) -> dict[str, Any]:
        """Return a minimal rotated key payload."""
        return {"id": key_id, "service": "openai", "user_id": user_id}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rotate_404_and_403_and_400(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    principal: Any,
) -> None:
    """Rotation returns 404, 403, and 400 under respective conditions."""
    from tripsage.api.core import dependencies as dep

    def _provide_principal() -> Any:
        """Provide principal instance for DI."""
        return principal

    svc = _KeyService(owner_id="owner-1")

    def _provide_key_service() -> _KeyService:
        """Provide key service stub for DI."""
        return svc

    app.dependency_overrides[dep.require_principal] = _provide_principal  # type: ignore[assignment]
    app.dependency_overrides[dep.get_api_key_service] = _provide_key_service  # type: ignore[assignment]

    client = async_client_factory(app)

    # 404: missing key
    r = await client.post(
        "/api/keys/missing/rotate",
        json={"new_key": "sk_test_new"},
    )
    assert r.status_code == status.HTTP_404_NOT_FOUND

    # 403: wrong owner
    # insert a key for a different owner to trigger 403
    svc.__dict__["_keys"]["k2"] = {  # avoid private attribute warning in type checker
        "id": "k2",
        "service": "openai",
        "user_id": "someone-else",
    }
    r = await client.post(
        "/api/keys/k2/rotate",
        json={"new_key": "sk_test_new"},
    )
    assert r.status_code == status.HTTP_403_FORBIDDEN

    # 400: invalid new key validation
    # Ensure the owned key exists and belongs to current principal
    svc.__dict__["_keys"]["k3"] = {
        "id": "k3",
        "service": "openai",
        "user_id": principal.id,
    }
    r = await client.post(
        "/api/keys/k3/rotate",
        json={"new_key": "sk_bad"},
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST
