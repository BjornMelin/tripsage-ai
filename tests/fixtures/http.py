"""HTTP-related fixtures using the FastAPI app."""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from tripsage.api import main
from tripsage.api.core.dependencies import ChatServiceDep, RequiredPrincipalDep
from tripsage.api.main import create_app
from tripsage.api.schemas.chat import ChatRequest, ChatResponse


try:  # pragma: no cover - optional dependency at runtime
    from requests import Response as RequestsResponse
    from requests.adapters import HTTPAdapter as RequestsHTTPAdapter
    from requests.sessions import Session as RequestsSession
except ImportError:  # pragma: no cover - optional dependency at runtime
    RequestsResponse = None
    RequestsHTTPAdapter = None
    RequestsSession = None

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from requests import Response as RequestsResponse
    from requests.adapters import HTTPAdapter as RequestsHTTPAdapter
    from requests.sessions import Session as RequestsSession


def _patch_otlp_exporters() -> None:
    """Stub OTLP exporters to avoid network calls during tests."""
    try:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # type: ignore[import-not-found]
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.metrics.export import (  # type: ignore[import-not-found]
            MetricExportResult,
        )
        from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
            SpanExportResult,
        )
    except ImportError:
        return

    def _noop_span_export(
        self: Any, data: Any, timeout_millis: int | None = None
    ) -> SpanExportResult:
        """Stub span export to avoid network calls."""
        return SpanExportResult.SUCCESS

    def _noop_span_shutdown(self: Any, *args: Any, **kwargs: Any) -> None:
        """Stub span exporter shutdown."""
        return

    OTLPSpanExporter.export = _noop_span_export  # type: ignore[assignment]
    OTLPSpanExporter.shutdown = _noop_span_shutdown  # type: ignore[assignment]

    def _noop_metric_export(
        self: Any, data: Any, timeout_millis: int | None = None
    ) -> MetricExportResult:
        """Stub metric export to avoid network calls."""
        return MetricExportResult.SUCCESS

    def _noop_metric_shutdown(self: Any, *args: Any, **kwargs: Any) -> None:
        """Stub metric exporter shutdown."""
        return

    OTLPMetricExporter.export = _noop_metric_export  # type: ignore[assignment]
    OTLPMetricExporter.shutdown = _noop_metric_shutdown  # type: ignore[assignment]


def _patch_metric_controller() -> None:
    """Disable metric controller background threads."""
    try:
        metrics_controller = importlib.import_module(
            "opentelemetry.sdk.metrics._internal.export.controller"
        )
    except ImportError:
        return

    push_controller_cls_any = getattr(metrics_controller, "PushController", None)
    if push_controller_cls_any is None:
        return

    push_controller_cls = cast(type[Any], push_controller_cls_any)

    def _noop_push_start(self: Any) -> None:
        """Stub push controller start."""
        return

    def _noop_push_shutdown(self: Any, *args: Any, **kwargs: Any) -> None:
        """Stub push controller shutdown."""
        return

    push_controller_cls.start = _noop_push_start  # type: ignore[assignment]
    push_controller_cls.shutdown = _noop_push_shutdown  # type: ignore[assignment]


def _patch_requests_transport() -> None:
    """Stub requests transport to prevent external HTTP calls."""
    if not (RequestsSession and RequestsResponse):
        return

    session_cls = cast(type[Any], RequestsSession)
    response_cls = cast(type[Any], RequestsResponse)

    def _noop_post(
        self: Any,
        url: str,
        data: Any = None,
        json: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Stub HTTP POST request."""
        response = response_cls()
        response.status_code = 200
        response._content = b""  # type: ignore[attr-defined]
        return response

    session_cls.post = _noop_post  # type: ignore[assignment]

    if RequestsHTTPAdapter:
        adapter_cls = cast(type[Any], RequestsHTTPAdapter)

        def _noop_send(  # pylint: disable=too-many-positional-arguments
            self: Any,
            request: Any,
            stream: bool = False,
            timeout: Any = None,
            verify: Any = True,
            cert: Any = None,
            proxies: Any = None,
        ) -> Any:
            """Stub HTTP adapter send."""
            response = response_cls()
            response.status_code = 200
            response._content = b""  # type: ignore[attr-defined]
            response.request = request  # type: ignore[assignment]
            return response

        adapter_cls.send = _noop_send  # type: ignore[assignment]


_patch_otlp_exporters()
_patch_metric_controller()
_patch_requests_transport()


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Return a FastAPI application instance prepared for tests.

    Args:
        monkeypatch: Pytest monkeypatch helper for altering module attributes.

    Returns:
        FastAPI: Configured application with a stubbed lifespan and cleared overrides.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
    monkeypatch.setenv("OTEL_METRICS_EXPORTER", "none")
    monkeypatch.setenv("OTEL_LOGS_EXPORTER", "none")

    def _noop_setup_otel(**_: object) -> None:
        """Stub OpenTelemetry setup for tests."""
        return

    monkeypatch.setattr(main, "setup_otel", _noop_setup_otel)

    @asynccontextmanager
    async def _lifespan_stub(_app: FastAPI) -> AsyncIterator[None]:
        """Stub the lifespan context manager to avoid side effects.

        Args:
            _app: The FastAPI application under test.

        Yields:
            None: Indicates the lifespan context executed without side effects.
        """
        yield

    monkeypatch.setattr(main, "lifespan", _lifespan_stub)

    application = create_app()
    application.dependency_overrides.clear()

    async def _patched_chat_endpoint(
        request: ChatRequest,
        http_request: Request,
        http_response: Response,
        principal: RequiredPrincipalDep,
        chat_service: ChatServiceDep,
    ) -> ChatResponse:
        """Handle patched chat endpoint for tests."""
        raw_response = await chat_service.chat_completion(principal.user_id, request)
        if isinstance(raw_response, ChatResponse):
            return raw_response
        return ChatResponse.model_validate(raw_response)

    filtered_routes: list[Any] = []
    for route in application.router.routes:
        methods_raw = cast(Any, getattr(route, "methods", None))
        methods: set[str] = set(methods_raw or [])
        if getattr(route, "path", None) == "/api/chat/" and "POST" in methods:
            continue
        filtered_routes.append(route)
    application.router.routes = filtered_routes

    application.add_api_route(
        "/api/chat/",
        _patched_chat_endpoint,
        methods=["POST"],
        response_model=ChatResponse,
        tags=["chat"],
    )

    return application


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an HTTPX async client bound to the FastAPI test app.

    Args:
        app: FastAPI application fixture configured for tests.

    Yields:
        AsyncIterator[AsyncClient]: Async HTTP client configured with ASGITransport.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
