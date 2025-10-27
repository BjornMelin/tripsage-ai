"""Security-focused tests for authentication helpers (Supabase-backed)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException, status as http_status

import tripsage.api.core.auth as auth_dep


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_requires_bearer_header() -> None:
    """Reject requests missing the required Bearer token header."""
    with pytest.raises(HTTPException) as exc:
        await auth_dep.get_current_user_id(authorization=None)

    assert exc.value.status_code == http_status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure invalid tokens raise authentication errors via Supabase SDK."""

    async def _raise_error(_token: str) -> dict[str, Any]:
        raise RuntimeError("invalid token")

    monkeypatch.setattr(auth_dep, "verify_and_get_claims", _raise_error)

    with pytest.raises(HTTPException):
        await auth_dep.get_current_user_id(authorization="Bearer invalid")


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_returns_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the Supabase user id when the token is valid."""

    async def _return_claims(_token: str) -> dict[str, Any]:
        return {"sub": "user-123", "email": "u@example.com"}

    monkeypatch.setattr(auth_dep, "verify_and_get_claims", _return_claims)

    user_id = await auth_dep.get_current_user_id(authorization="Bearer test-token")
    assert user_id == "user-123"


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_handles_supabase_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supabase SDK exceptions should be translated into HTTP 401 responses."""

    async def _raise_network(_token: str) -> dict[str, Any]:
        raise RuntimeError("network error")

    monkeypatch.setattr(auth_dep, "verify_and_get_claims", _raise_network)

    with pytest.raises(HTTPException) as exc:
        await auth_dep.get_current_user_id(authorization="Bearer bad-token")

    assert exc.value.status_code == http_status.HTTP_401_UNAUTHORIZED


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_optional_user_id_gracefully_handles_missing_header() -> None:
    """Optional dependency should return None when Authorization is absent."""
    result = await auth_dep.get_optional_user_id(authorization=None)
    assert result is None


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_optional_user_id_returns_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional dependency should reuse the core helper when token valid."""

    async def _claims(_token: str) -> dict[str, Any]:
        return {"sub": "optional-999"}

    monkeypatch.setattr(auth_dep, "verify_and_get_claims", _claims)

    result = await auth_dep.get_optional_user_id(authorization="Bearer ok")
    assert result == "optional-999"
