"""Unit tests for Supabase async client utilities.

These tests are offline and focus on URL formation and header wiring.
"""

from __future__ import annotations

import pytest

from tripsage_core.services.infrastructure.supabase_client import (
    postgrest_for_user,
    supabase_rest_url,
)


def test_supabase_rest_url_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """supabase_rest_url returns the REST endpoint ending with /rest/v1."""

    class _Secret:
        """Secret class for testing."""

        def get_secret_value(self) -> str:  # pyright: ignore[reportUnusedFunction]
            """Get secret value."""
            return "placeholder"

    class _Svc(_Secret):
        """Service key for testing."""

        def get_secret_value(self) -> str:
            """Get secret value."""
            return "svc"

    class _Anon(_Secret):
        """Anon key for testing."""

        def get_secret_value(self) -> str:
            """Get secret value."""
            return "anon"

    class Settings:
        """Settings class for testing."""

        database_url: str = "https://project.supabase.co"
        database_service_key: _Svc = _Svc()
        database_public_key: _Anon = _Anon()

    # Patch settings used by supabase_rest_url (patch the imported symbol where used)
    import tripsage_core.services.infrastructure.supabase_client as sc

    def _settings_factory() -> Settings:
        """Return deterministic settings for the Supabase client."""
        return Settings()

    monkeypatch.setattr(sc, "get_settings", _settings_factory, raising=True)

    # Ensure cache clear before calling to avoid cross-test interference
    sc.supabase_rest_url.cache_clear()

    # First call caches via lru_cache
    url = supabase_rest_url()
    assert url.endswith("/rest/v1")
    assert url.startswith("https://project.supabase.co")


def test_postgrest_for_user_sets_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """postgrest_for_user attaches a Bearer Authorization header."""
    captured: dict[str, str] = {}

    class _ClientStub:
        """Minimal PostgREST client stub that records auth headers."""

        def __init__(self, url: str) -> None:
            """Capture initialization arguments."""
            captured["url"] = url
            self.headers: dict[str, str] = {}

        def auth(self, token: str) -> None:
            """Record the Authorization header sent by the client."""
            self.headers["Authorization"] = f"Bearer {token}"

    monkeypatch.setattr(
        "tripsage_core.services.infrastructure.supabase_client.AsyncPostgrestClient",
        _ClientStub,
    )

    token = "test-token"
    client = postgrest_for_user(token)

    assert captured["url"].endswith("/rest/v1")
    assert client.headers["Authorization"] == f"Bearer {token}"


def test_noop_placeholder_for_legacy_reset_removed() -> None:
    """Ensure legacy client reset helper is not present anymore."""
    import tripsage_core.services.infrastructure.supabase_client as sc

    assert not hasattr(sc, "_reset_clients_for_tests")
