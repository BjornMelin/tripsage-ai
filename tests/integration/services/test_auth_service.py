"""Auth service tests with mocked Supabase verification and admin client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from tripsage_core.services.business.auth_service import (
    TokenData,
    get_current_user,
    get_user_with_client,
)


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verified claims are mapped to TokenData."""

    async def fake_verify_and_get_claims(jwt: str) -> dict[str, Any]:
        assert jwt == "tkn"
        return {
            "sub": "user-1",
            "email": "u@example.com",
            "role": "user",
            "aud": "authenticated",
        }

    monkeypatch.setattr(
        "tripsage_core.services.business.auth_service.verify_and_get_claims",
        fake_verify_and_get_claims,
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tkn")
    td = await get_current_user(creds)
    assert td == TokenData(
        user_id="user-1", email="u@example.com", role="user", aud="authenticated"
    )


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid/failed verification yields HTTP 401."""

    async def fake_verify_and_get_claims(_: str) -> dict[str, Any]:
        """Fake verify and get claims."""
        raise RuntimeError("bad token")

    monkeypatch.setattr(
        "tripsage_core.services.business.auth_service.verify_and_get_claims",
        fake_verify_and_get_claims,
    )

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="nope")
    with pytest.raises(HTTPException) as ei:
        await get_current_user(creds)
    assert ei.value.status_code == 401


@dataclass
class _Resp:
    """Response class."""

    user: Any


@dataclass
class _User:
    """User class."""

    id: str
    email: str | None
    user_metadata: dict[str, Any] | None


class _Admin:
    """Admin class."""

    async def get_user_by_id(self, uid: str) -> _Resp:
        """Get user by ID."""
        return _Resp(
            user=_User(id=uid, email="u@example.com", user_metadata={"tier": "pro"})
        )


class _Client:
    """Client class."""

    def __init__(self) -> None:
        """Initialize client."""
        self.auth = type("A", (), {"admin": _Admin()})()


@pytest.mark.asyncio
async def test_get_user_with_client_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin client returns user; function normalizes to dict."""

    async def fake_admin_client() -> Any:
        """Fake admin client."""
        return _Client()

    monkeypatch.setattr(
        "tripsage_core.services.business.auth_service._admin",
        fake_admin_client,
    )

    # Bypass get_current_user by providing dependency directly
    user = await get_user_with_client(TokenData(user_id="user-42"), _Client())
    assert user == {
        "id": "user-42",
        "email": "u@example.com",
        "user_metadata": {"tier": "pro"},
    }


@pytest.mark.asyncio
async def test_get_user_with_client_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 404 when admin returns no user object."""

    class _AdminNF:
        """Admin not found class."""

        async def get_user_by_id(self, uid: str) -> _Resp:
            """Get user by ID."""
            return _Resp(user=None)

    class _ClientNF:
        """Client not found class."""

        def __init__(self) -> None:
            """Initialize client."""
            self.auth = type("A", (), {"admin": _AdminNF()})()

    async def fake_admin_client() -> Any:
        """Fake admin client."""
        return _ClientNF()

    monkeypatch.setattr(
        "tripsage_core.services.business.auth_service._admin",
        fake_admin_client,
    )

    with pytest.raises(HTTPException) as ei:
        await get_user_with_client(TokenData(user_id="missing"), _ClientNF())
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_with_client_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 500 when admin client raises unexpected error."""

    class _AdminErr:
        """Admin error class."""

        async def get_user_by_id(self, uid: str) -> _Resp:
            """Get user by ID."""
            raise RuntimeError("boom")

    class _ClientErr:
        """Client error class."""

        def __init__(self) -> None:
            """Initialize client."""
            self.auth = type("A", (), {"admin": _AdminErr()})()

    async def fake_admin_client() -> Any:
        """Fake admin client."""
        return _ClientErr()

    monkeypatch.setattr(
        "tripsage_core.services.business.auth_service._admin",
        fake_admin_client,
    )

    with pytest.raises(HTTPException) as ei:
        await get_user_with_client(TokenData(user_id="u1"), _ClientErr())
    assert ei.value.status_code == 500
