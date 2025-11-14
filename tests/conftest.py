"""Pytest configuration and shared fixtures for API tests.

Sets testing environment, provides an async HTTP client bound to a minimal
FastAPI app instance, and reusable Principal + helpers.
"""

from __future__ import annotations

# Ensure OpenTelemetry exporters are disabled as early as possible
import os as _os


_os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")
_os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
_os.environ.setdefault("OTEL_LOGS_EXPORTER", "none")
_os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")
_os.environ.setdefault("OTEL_SDK_DISABLED", "true")


# Keep plugin autoload minimal to avoid heavy app imports during unit tests
pytest_plugins: list[str] = []

from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType, TracebackType
from typing import Any, ParamSpec, Self, TypeVar, cast

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from tripsage_core.config import Settings
from tripsage_core.models.trip import Budget, BudgetBreakdown, Trip


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
        otel_instrumentation="",
    )


@pytest.fixture(scope="session", autouse=True)
def set_testing_env() -> None:
    """Force testing settings for the duration of the pytest session.

    Ensures instrumentation and heavy services keep a light footprint.
    Uses os.environ directly to avoid monkeypatch scope issues at session level.
    """
    _os.environ["ENVIRONMENT"] = "testing"
    # Disable OpenTelemetry exporters during tests (no network, no side effects)
    _os.environ["OTEL_TRACES_EXPORTER"] = "none"
    _os.environ["OTEL_METRICS_EXPORTER"] = "none"
    _os.environ["OTEL_LOGS_EXPORTER"] = "none"
    # Ensure no implicit OTLP endpoint is used
    _os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
    _install_fake_otel()


@pytest.fixture()
def otel_inmemory(monkeypatch: pytest.MonkeyPatch):
    """Optional in-memory OTEL exporter for span assertions.

    Most tests keep instrumentation disabled via ``set_testing_env``. When a
    test needs to assert span emission, use this fixture to switch to the
    SDK's in-memory exporter for the test scope.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    # Clear spans after assertion to avoid leakage across tests
    exporter.clear()


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
    # Also patch re-exported imports used by API modules under test, but only
    # if those modules can be imported without triggering heavy side effects.
    try:
        import importlib

        trip_sec = importlib.import_module("tripsage.api.core.trip_security")
        monkeypatch.setattr(trip_sec, "audit_security_event", _noop, raising=False)
    except (ImportError, AttributeError):
        # Skip when unavailable; orchestration unit tests don't need API patches
        pass


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
def fake_redis():
    """Provide an isolated fakeredis client for tests that need cache access."""
    try:
        import fakeredis.aioredis as faredis  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        pytest.skip("fakeredis not available")
    return faredis.FakeRedis()


@pytest.fixture()
def app() -> FastAPI:
    """Return a FastAPI app with routers for integration tests."""
    app = build_minimal_app()
    # Include routers needed for integration tests
    from tripsage.api.routers import (
        attachments,
        config,
        health,
        itineraries,
        memory,
        trips,
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(config.router, prefix="/api", tags=["configuration"])
    app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
    app.include_router(memory.router, prefix="/api", tags=["memory"])
    app.include_router(
        itineraries.router, prefix="/api/itineraries", tags=["itineraries"]
    )
    app.include_router(
        attachments.router, prefix="/api/attachments", tags=["attachments"]
    )
    # Dependency overrides for health endpoints to avoid full DI container
    from tripsage.api.core import dependencies as dep

    class _DB:
        async def health_check(self) -> bool:
            """DB is healthy."""
            return True

        def get_pool_stats(self) -> dict[str, object]:
            """Return empty pool stats."""
            return {}

    class _Cache:
        async def health_check(self) -> bool:
            """Cache is healthy."""
            return True

    def _provide_db() -> _DB:
        """Provide a minimal healthy DB stub for integration tests."""
        return _DB()

    def _provide_cache() -> _Cache:
        """Provide a minimal healthy cache stub for integration tests."""
        return _Cache()

    app.dependency_overrides[dep.get_db] = _provide_db  # type: ignore[assignment]
    app.dependency_overrides[dep.get_cache_service_dep] = _provide_cache  # type: ignore[assignment]

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


@pytest.fixture
def request_builder() -> Callable[[str, str], Request]:
    """Build a synthetic FastAPI request for SlowAPI-dependent tests."""

    def _build(method: str, path: str) -> Request:
        scope: dict[str, Any] = {
            "type": "http",
            "method": method,
            "path": path,
            "scheme": "http",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "query_string": b"",
        }

        async def receive() -> dict[str, object]:
            """Receive request."""
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(scope, receive)

    return _build


@pytest.fixture()
def core_trip_response() -> Trip:
    """Return a sample Trip model instance for testing."""
    from datetime import date
    from uuid import uuid4

    return Trip(
        id=uuid4(),
        user_id=uuid4(),
        title="Test Trip",
        description="A test trip for unit tests",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 7),
        destination="Tokyo, Japan",
        budget_breakdown=Budget(
            total=2000.0, currency="USD", spent=0.0, breakdown=BudgetBreakdown()
        ),
        travelers=2,
    )


@pytest.fixture()
def unauthenticated_test_client(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
) -> AsyncClient:
    """Return an AsyncClient without authentication headers."""
    return async_client_factory(app)
