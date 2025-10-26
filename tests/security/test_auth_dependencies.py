"""Security-focused tests for authentication helpers (Supabase-backed)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException, status as http_status

import tripsage.api.core.auth as auth_dep


class _User:
    """Mock Supabase user."""

    def __init__(self, user_id: str, email: str | None = None):
        """Initialize the user."""
        self.id = user_id
        self.email = email
        self.user_metadata: dict[str, Any] = {}


class _Auth:
    """Mock Supabase auth."""

    def __init__(self, user: _User | None, error: Exception | None = None):
        """Initialize the auth."""
        self._user = user
        self._error = error

    def get_user(self, _token: str):
        """Get the user from the token."""

        class _Resp:
            def __init__(self, user: _User | None):
                """Initialize the response."""
                self.user = user

        if self._error:
            raise self._error
        return _Resp(self._user)


class _Client:
    """Mock Supabase client."""

    def __init__(self, user: _User | None, error: Exception | None = None):
        """Initialize the client."""
        self.auth = _Auth(user=user, error=error)


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
    # Patch client factory to raise from SDK
    monkeypatch.setattr(auth_dep, "_supabase_client", lambda: _Client(user=None))

    with pytest.raises(HTTPException):
        await auth_dep.get_current_user_id(authorization="Bearer invalid")


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_returns_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return the Supabase user id when the token is valid."""
    user = _User("user-123", email="u@example.com")
    monkeypatch.setattr(auth_dep, "_supabase_client", lambda: _Client(user=user))

    user_id = await auth_dep.get_current_user_id(authorization="Bearer test-token")
    assert user_id == "user-123"


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_user_id_handles_supabase_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supabase SDK exceptions should be translated into HTTP 401 responses."""
    monkeypatch.setattr(
        auth_dep,
        "_supabase_client",
        lambda: _Client(user=None, error=RuntimeError("network error")),
    )

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
    user = _User("optional-999", email="opt@example.com")
    monkeypatch.setattr(auth_dep, "_supabase_client", lambda: _Client(user=user))

    result = await auth_dep.get_optional_user_id(authorization="Bearer ok")
    assert result == "optional-999"
