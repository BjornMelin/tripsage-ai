"""Settings fixtures used across tests."""

from __future__ import annotations

import pytest

from tripsage_core.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Return a Settings instance tuned for tests."""
    return Settings(environment="testing", debug=True)


@pytest.fixture(autouse=True)
def override_settings(monkeypatch: pytest.MonkeyPatch, test_settings: Settings) -> None:
    """Ensure both backend and API layers share the same test settings."""
    monkeypatch.setattr("tripsage_core.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("tripsage.api.core.config.get_settings", lambda: test_settings)
