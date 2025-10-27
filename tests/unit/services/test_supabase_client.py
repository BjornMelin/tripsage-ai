"""Unit tests for Supabase client utilities."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tripsage_core.services.infrastructure import supabase_client


@pytest.fixture(autouse=True)
def reset_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure Supabase client caches are reset between tests."""
    monkeypatch.setattr(supabase_client, "_admin_client", None, raising=False)
    monkeypatch.setattr(supabase_client, "_public_client", None, raising=False)
    supabase_client.supabase_rest_url.cache_clear()

    def _fake_settings() -> Any:
        return SimpleNamespace(
            database_url="https://example.supabase.co",
            database_service_key=SimpleNamespace(get_secret_value=lambda: "service"),
            database_public_key=SimpleNamespace(get_secret_value=lambda: "public"),
        )

    monkeypatch.setattr(supabase_client, "get_settings", _fake_settings)


@pytest.mark.asyncio
async def test_get_admin_client_caches_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin client creation should occur only once across multiple calls."""
    created: list[tuple[Any, ...]] = []

    async def _create_client(*args: Any, **kwargs: Any) -> dict[str, str]:
        created.append((args, kwargs))
        return {"client": "admin"}

    monkeypatch.setattr(supabase_client, "acreate_client", _create_client)

    client_one = await supabase_client.get_admin_client()
    client_two = await supabase_client.get_admin_client()

    assert client_one is client_two
    assert len(created) == 1


@pytest.mark.asyncio
async def test_get_public_client_caches_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public client should also be cached after first creation."""
    created: list[tuple[Any, ...]] = []

    async def _create_client(*args: Any, **kwargs: Any) -> dict[str, str]:
        created.append((args, kwargs))
        return {"client": "public"}

    monkeypatch.setattr(supabase_client, "acreate_client", _create_client)

    client_one = await supabase_client.get_public_client()
    client_two = await supabase_client.get_public_client()

    assert client_one is client_two
    assert len(created) == 1


@pytest.mark.asyncio
async def test_verify_and_get_claims_returns_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifying a valid token should return the decoded claims."""

    class _Auth:
        """Stub auth interface exposing get_claims."""

        async def get_claims(self, *, jwt: str) -> dict[str, Any]:
            """Return synthetic claims for the provided JWT."""
            return {"sub": jwt, "email": "user@example.com"}

    class _Client:
        """Stub Supabase client providing auth accessor."""

        def __init__(self) -> None:
            self.auth = _Auth()

    async def _public_client() -> _Client:
        """Return a stub public client."""
        return _Client()

    monkeypatch.setattr(supabase_client, "get_public_client", _public_client)

    claims = await supabase_client.verify_and_get_claims("user-123")

    assert claims["sub"] == "user-123"
    assert claims["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_verify_and_get_claims_rejects_missing_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing subject in Supabase claims should raise a validation error."""

    class _Auth:
        """Stub auth returning claims without subject."""

        async def get_claims(self, *, jwt: str) -> dict[str, Any]:
            """Return claims missing a subject to trigger validation failure."""
            return {"email": "user@example.com", "jwt": jwt}

    class _Client:
        """Stub Supabase client lacking subject claim."""

        def __init__(self) -> None:
            self.auth = _Auth()

    async def _public_client() -> _Client:
        """Return a stub public client lacking a subject claim."""
        return _Client()

    monkeypatch.setattr(supabase_client, "get_public_client", _public_client)

    with pytest.raises(ValueError):
        await supabase_client.verify_and_get_claims("token-without-sub")


def test_postgrest_for_user_sets_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """PostgREST helper should authorize the returned client with bearer token."""
    captured: dict[str, Any] = {}

    class _Client:
        """Minimal PostgREST client capturing auth invocations."""

        def __init__(self, url: str) -> None:
            captured["url"] = url

        def auth(self, token: str) -> None:
            """Capture the supplied bearer token."""
            captured["token"] = token

    monkeypatch.setattr(
        supabase_client,
        "AsyncPostgrestClient",
        cast(Callable[[str], _Client], _Client),
    )

    client = supabase_client.postgrest_for_user("jwt-token")

    assert captured["url"].endswith("/rest/v1")
    assert captured["token"] == "jwt-token"
    assert isinstance(client, _Client)


def test_supabase_rest_url_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """supabase_rest_url should reuse cached value across calls."""
    calls = 0

    def _settings() -> Any:
        """Return stub settings for rest URL generation."""
        nonlocal calls
        calls += 1
        return SimpleNamespace(database_url="https://cache.supabase.co")

    monkeypatch.setattr(supabase_client, "get_settings", _settings)
    supabase_client.supabase_rest_url.cache_clear()

    first = supabase_client.supabase_rest_url()
    second = supabase_client.supabase_rest_url()

    assert first == "https://cache.supabase.co/rest/v1"
    assert first == second
    assert calls == 1
