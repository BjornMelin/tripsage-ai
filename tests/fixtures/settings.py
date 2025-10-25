"""Settings fixtures used across tests."""

from __future__ import annotations

import pytest

from tripsage_core.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create application settings tailored for tests.

    Returns:
        Settings: Configuration object with monitoring and instrumentation disabled.
    """
    return Settings(
        environment="testing",
        debug=True,
        rate_limit_enabled=False,
        rate_limit_enable_monitoring=False,
        enable_database_monitoring=False,
        enable_security_monitoring=False,
        enable_auto_recovery=False,
        enable_websockets=False,
        enable_fastapi_instrumentation=False,
        enable_asgi_instrumentation=False,
        enable_httpx_instrumentation=False,
        enable_redis_instrumentation=False,
    )


@pytest.fixture(autouse=True)
def override_settings(monkeypatch: pytest.MonkeyPatch, test_settings: Settings) -> None:
    """Ensure both backend and API layers use shared test settings.

    Args:
        monkeypatch: Pytest monkeypatch helper.
        test_settings: Shared test configuration instance.
    """
    monkeypatch.setattr("tripsage_core.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("tripsage.api.core.config.get_settings", lambda: test_settings)
