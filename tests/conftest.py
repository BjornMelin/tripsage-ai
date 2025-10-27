"""Root pytest configuration for TripSage."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest

import tests.factories  # noqa: F401  # pylint: disable=unused-import  # pyright: ignore[reportUnusedImport]


pytest_plugins = ["tests.fixtures"]

_MARKERS: tuple[str, ...] = (
    "unit: Unit tests for individual components",
    "integration: Service and API integration tests",
    "e2e: End-to-end API flows",
    "performance: Quick performance smoke checks",
    "security: Security-critical validation tests",
    "docker: Docker configuration tests",
    "perf: Performance guard tests",
    "timeout: Tests asserting execution time thresholds",
    "slow: Tests exceeding default runtime expectations",
)

_ENVIRONMENT_OVERRIDES: Mapping[str, str] = {
    "ENVIRONMENT": "testing",
    "DEBUG": "True",
    "SECRET_KEY": "test-secret-key",
    "OPENAI_API_KEY": "sk-test-1234567890",
    "WEATHER_API_KEY": "test-weather-key",
    "GOOGLE_MAPS_API_KEY": "test-maps-key",
    "DUFFEL_API_KEY": "test-duffel-key",
}


def pytest_configure(config: pytest.Config) -> None:
    """Register canonical markers for the suite."""
    for marker in _MARKERS:
        config.addinivalue_line("markers", marker)


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment() -> Iterator[None]:
    """Apply baseline environment overrides for tests."""
    original_values: dict[str, str | None] = {}
    for key, value in _ENVIRONMENT_OVERRIDES.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        yield
    finally:
        for key, previous in original_values.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


@pytest.fixture
def disable_auth_audit_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace audit logging hooks with async no-ops for auth middleware tests."""

    async def _noop(*args: Any, **kwargs: Any) -> None:
        return None

    for module_path in (
        "tripsage_core.services.business.audit_logging_service",
        "tripsage.api.middlewares.authentication",
    ):
        module = import_module(module_path)
        for attribute in (
            "audit_security_event",
            "audit_authentication",
            "audit_api_key",
        ):
            if hasattr(module, attribute):
                monkeypatch.setattr(module, attribute, _noop, raising=False)


class _DummyApiKeyService:
    """Minimal API key service stub for authentication middleware tests."""

    async def validate_api_key(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        """Return an invalid key response with structured payload."""
        return SimpleNamespace(is_valid=False, message=None, details={})


@pytest.fixture
def dummy_api_key_service() -> _DummyApiKeyService:
    """Provide a fresh API key service stub per test to avoid shared state."""
    return _DummyApiKeyService()
