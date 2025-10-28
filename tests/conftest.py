"""Pytest configuration and shared fixtures for API tests.

Sets testing environment, provides an async HTTP client bound to a minimal
FastAPI app instance, and reusable Principal + helpers.
"""

from __future__ import annotations


# Keep plugin autoload minimal to avoid heavy app imports during unit tests
pytest_plugins: list[str] = []

from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType, TracebackType
from typing import Any, ParamSpec, Self, TypeVar, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tripsage_core.config import Settings


_P = ParamSpec("_P")
_R = TypeVar("_R")


def _install_fake_otel() -> None:
    """Install a lightweight OTEL shim so router decorators are no-ops.

    This avoids altering source modules while ensuring FastAPI sees real
    endpoint signatures (no synthetic '_' query params).
    """
    import sys

    if "tripsage_core.observability.otel" in sys.modules:
        return

    def _identity_decorator(
        *_args: Any, **_kwargs: Any
    ) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
        def _wrapper(func: Callable[_P, _R]) -> Callable[_P, _R]:
            return func

        return _wrapper

    def _http_route_attrs(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {}

    fake = ModuleType("tripsage_core.observability.otel")
    fake_attrs = cast(Any, fake)
    fake_attrs.trace_span = _identity_decorator
    fake_attrs.record_histogram = _identity_decorator
    fake_attrs.http_route_attr_fn = _http_route_attrs

    class _Span:
        """Minimal context manager representing a tracing span."""

        def __enter__(self) -> Self:
            """Enter span."""
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> bool:
            """Exit span."""
            return False

        def set_attribute(self, key: str, value: Any) -> None:
            """Set attribute."""
            return

        def record_exception(self, exc: BaseException, **_kwargs: Any) -> None:
            """Record exception."""
            return

    class _Tracer:
        """Tracer returning context managers without side effects."""

        def start_as_current_span(self, *_args: Any, **_kwargs: Any) -> _Span:
            """Start as current span."""
            return _Span()

    def get_tracer(_name: str) -> _Tracer:
        """Get tracer."""
        return _Tracer()

    class _Histogram:
        """Histogram."""

        def record(
            self,
            *_record_args: Any,
            **_record_kwargs: Any,
        ) -> None:
            """Record."""
            return

    class _Meter:
        """Meter."""

        def create_histogram(self, *_args: Any, **_kwargs: Any) -> _Histogram:
            """Create histogram."""
            return _Histogram()

    def get_meter(_name: str) -> _Meter:
        """Get meter."""
        return _Meter()

    fake_attrs.get_tracer = get_tracer
    fake_attrs.get_meter = get_meter
    sys.modules["tripsage_core.observability.otel"] = fake


@dataclass(slots=True)
class Principal:
    """Lightweight principal stub for tests (avoids heavy imports).

    Matches the attributes accessed by the routers: id/type/auth_method/scopes/
    metadata and the convenience property `user_id`.
    """

    id: str
    type: str
    email: str | None
    auth_method: str
    scopes: list[str]
    metadata: dict[str, str]

    @property
    def user_id(self) -> str:
        """Return the canonical user id string."""
        return self.id


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
        otel_instrumentation="",
    )


@pytest.fixture()
def dummy_api_key_service() -> object:
    """Provide a dummy API key service for middleware tests."""
    # Simple mock object - middleware tests don't seem to call methods on it
    return object()


@pytest.fixture(scope="session", autouse=True)
def set_testing_env() -> None:
    """Force testing settings for the duration of the pytest session.

    Ensures instrumentation and heavy services keep a light footprint.
    Uses os.environ directly to avoid monkeypatch scope issues at session level.
    """
    import os

    os.environ["ENVIRONMENT"] = "testing"
    _install_fake_otel()


@pytest.fixture(autouse=True)
def disable_auth_audit_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Silence audit logging during tests.

    Replaces audit helpers with async no-ops so tests can assert behavior
    without touching real log directories (e.g., /var/log/tripsage).
    """

    async def _noop(**_kwargs: Any) -> None:
        return

    # Patch the audit functions
    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.audit_security_event",
        _noop,
        raising=False,
    )
    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.audit_authentication",
        _noop,
        raising=False,
    )
    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.audit_api_key",
        _noop,
        raising=False,
    )

    # Also patch the logger creation to prevent file system access
    async def _mock_get_audit_logger() -> Any:
        """Mock audit logger."""

        class MockLogger:
            """Mock logger."""

            async def log_event(self, *args: Any, **kwargs: Any) -> None:
                """Log event."""
                return

            async def log_authentication_event(self, *args: Any, **kwargs: Any) -> None:
                """Log authentication event."""
                return

            async def log_security_event(self, *args: Any, **kwargs: Any) -> None:
                """Log security event."""
                return

            async def log_api_key_event(self, *args: Any, **kwargs: Any) -> None:
                """Log API key event."""
                return

        return MockLogger()

    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.get_audit_logger",
        _mock_get_audit_logger,
        raising=False,
    )
    # Also patch re-exported imports used by API modules under test
    monkeypatch.setattr(
        "tripsage.api.core.trip_security.audit_security_event",
        _noop,
        raising=False,
    )
    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.audit_authentication",
        _noop,
        raising=False,
    )
    monkeypatch.setattr(
        "tripsage_core.services.business.audit_logging_service.audit_api_key",
        _noop,
        raising=False,
    )


@pytest.fixture()
def principal() -> Principal:
    """Return a deterministic fake user principal.

    Returns:
        Principal: A user principal with fixed id/email.
    """
    return Principal(
        id="00000000-0000-0000-0000-0000000000aa",
        type="user",
        email="user@example.com",
        auth_method="jwt",
        scopes=["read", "write"],
        metadata={"ip_address": "127.0.0.1"},
    )


@pytest.fixture()
def async_client_factory() -> Callable[[FastAPI], AsyncClient]:
    """Return a factory that builds an AsyncClient for a given app."""

    def _factory(app: FastAPI) -> AsyncClient:
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _factory


@pytest.fixture()
def app() -> FastAPI:
    """Return a FastAPI app with routers for integration tests."""
    app = build_minimal_app()
    # Include routers needed for integration tests
    from tripsage.api.routers import (
        attachments,
        chat,
        config,
        health,
        keys,
        trips,
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(config.router, prefix="/api", tags=["configuration"])
    app.include_router(keys.router, prefix="/api/keys", tags=["api_keys"])
    app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(
        attachments.router, prefix="/api/attachments", tags=["attachments"]
    )
    return app


@pytest.fixture()
def async_client(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> AsyncClient:
    """Return an AsyncClient bound to the test app."""
    return async_client_factory(app)


def build_minimal_app() -> FastAPI:
    """Create a minimal FastAPI app for router-focused tests.

    Returns:
        FastAPI: Empty app ready to include target routers.
    """
    return FastAPI()
