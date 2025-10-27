"""Unit tests for Supabase async client utilities."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from supabase.lib.client_options import AsyncClientOptions

import tripsage_core.services.infrastructure.supabase_client as sc


class _Secret:
    """Minimal secret stub providing get_secret_value for Supabase keys."""

    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        """Return the stored secret string."""
        return self._value


class _Settings:
    """Lightweight settings object returned by get_settings in tests."""

    database_url: str = "https://project.supabase.co"
    database_service_key: _Secret = _Secret("service-key")
    database_public_key: _Secret = _Secret("public-key")


@pytest.fixture
def fake_settings() -> _Settings:
    """Provide configurable settings instance for each test."""
    return _Settings()


@pytest.fixture(autouse=True, name="_reset_state")
def reset_supabase_client_state(
    monkeypatch: pytest.MonkeyPatch, fake_settings: _Settings
) -> Generator[None]:
    """Reset module-level state and patch get_settings around each test."""
    sc._admin_client = None  # type: ignore[attr-defined]
    sc._public_client = None  # type: ignore[attr-defined]
    sc.supabase_rest_url.cache_clear()
    monkeypatch.setattr(sc, "get_settings", lambda: fake_settings, raising=True)
    yield
    sc._admin_client = None  # type: ignore[attr-defined]
    sc._public_client = None  # type: ignore[attr-defined]
    sc.supabase_rest_url.cache_clear()


def test_supabase_rest_url_shape(fake_settings: _Settings) -> None:
    """supabase_rest_url appends /rest/v1 and preserves project host."""
    url = sc.supabase_rest_url()
    assert url == f"{fake_settings.database_url}/rest/v1"


def test_postgrest_for_user_sets_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """postgrest_for_user attaches the expected Bearer token header."""
    captured: dict[str, Any] = {}

    class _ClientStub:
        """Stub PostgREST client for capturing initialization and auth calls."""

        def __init__(self, url: str) -> None:
            """Initialize stub client with URL."""
            captured["url"] = url
            self.headers: dict[str, str] = {}

        def auth(self, token: str) -> None:
            """Record the authorization header issued by the client."""
            self.headers["Authorization"] = f"Bearer {token}"

    monkeypatch.setattr(
        "tripsage_core.services.infrastructure.supabase_client.AsyncPostgrestClient",
        _ClientStub,
        raising=True,
    )

    token = "test-token"
    client = sc.postgrest_for_user(token)

    assert captured["url"] == "https://project.supabase.co/rest/v1"
    assert client.headers["Authorization"] == f"Bearer {token}"


@pytest.mark.asyncio
async def test_get_admin_client_creates_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_admin_client invokes Supabase factory once and caches the instance."""
    created_clients: list[tuple[str, str, AsyncClientOptions | None]] = []
    returned_client = object()

    async def _fake_create_client(
        url: str,
        key: str,
        *,
        options: AsyncClientOptions | None = None,
    ) -> object:
        """Capture client creation arguments and return stubbed client."""
        created_clients.append((url, key, options))
        return returned_client

    monkeypatch.setattr(sc, "acreate_client", _fake_create_client, raising=True)

    first = await sc.get_admin_client()
    second = await sc.get_admin_client()

    assert first is second is returned_client
    assert len(created_clients) == 1
    url, key, options = created_clients[0]
    assert url == "https://project.supabase.co"
    assert key == "service-key"
    assert isinstance(options, AsyncClientOptions)
    assert options.auto_refresh_token is False
    assert options.persist_session is False


@pytest.mark.asyncio
async def test_get_public_client_creates_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_public_client reuses cached client and passes anon key."""
    created_clients: list[tuple[str, str, AsyncClientOptions | None]] = []
    returned_client = object()

    async def _fake_create_client(
        url: str,
        key: str,
        *,
        options: AsyncClientOptions | None = None,
    ) -> object:
        """Capture client creation arguments and return stubbed client."""
        created_clients.append((url, key, options))
        return returned_client

    monkeypatch.setattr(sc, "acreate_client", _fake_create_client, raising=True)

    first = await sc.get_public_client()
    second = await sc.get_public_client()

    assert first is second is returned_client
    assert len(created_clients) == 1
    url, key, options = created_clients[0]
    assert url == "https://project.supabase.co"
    assert key == "public-key"
    assert isinstance(options, AsyncClientOptions)
    assert options.auto_refresh_token is False
    assert options.persist_session is False


@pytest.mark.asyncio
async def test_verify_and_get_claims_returns_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verify_and_get_claims returns the JWKS-backed claim set."""
    token = "jwt-token"
    expected_claims = {"sub": "user", "role": "authenticated"}

    class _AuthStub:
        async def get_claims(self, *, jwt: str) -> dict[str, Any]:
            """Return deterministic claims used by the verifier under test."""
            assert jwt == token
            return expected_claims

    class _ClientStub:
        """Stub Supabase client with auth mock."""

        def __init__(self) -> None:
            """Initialize stub client with auth."""
            self.auth = _AuthStub()

    async def _fake_get_public_client() -> _ClientStub:
        """Return stubbed public client."""
        return _ClientStub()

    monkeypatch.setattr(sc, "get_public_client", _fake_get_public_client, raising=True)

    claims = await sc.verify_and_get_claims(token)

    assert claims is expected_claims


@pytest.mark.asyncio
async def test_verify_and_get_claims_raises_when_sub_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verify_and_get_claims raises ValueError when `sub` claim is absent."""

    class _AuthStub:
        async def get_claims(self, *, jwt: str) -> dict[str, Any]:
            """Return a partial claim set lacking the subject."""
            return {"role": "anonymous"}

    class _ClientStub:
        """Stub Supabase client with auth mock."""

        def __init__(self) -> None:
            """Initialize stub client with auth."""
            self.auth = _AuthStub()

    async def _fake_get_public_client() -> _ClientStub:
        """Return stubbed public client."""
        return _ClientStub()

    monkeypatch.setattr(sc, "get_public_client", _fake_get_public_client, raising=True)

    with pytest.raises(ValueError):
        await sc.verify_and_get_claims("jwt-token")


def test_noop_placeholder_for_legacy_reset_removed() -> None:
    """Ensure legacy client reset helper is not present anymore."""
    assert not hasattr(sc, "_reset_clients_for_tests")
