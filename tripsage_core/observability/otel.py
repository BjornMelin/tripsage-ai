"""Unified OpenTelemetry setup, accessors, and decorators.

This module centralizes OTEL initialization and provides helpers for tracing
and metrics with minimal, DRY instrumentation.
"""

from __future__ import annotations

import importlib
import os
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast


# Import typing-only symbols to avoid runtime ImportError on environments
# without OpenTelemetry installed; functions lazily import runtime modules.
if TYPE_CHECKING:  # pragma: no cover - typing only
    from opentelemetry.metrics import CallbackOptions, Observation
else:  # pragma: no cover - at runtime these are resolved lazily
    CallbackOptions = Any  # type: ignore[misc,assignment]
    Observation = Any  # type: ignore[misc,assignment]


# Instrumentors are imported lazily inside setup_otel().


_SETUP_DONE = False
_P = ParamSpec("_P")
_T = TypeVar("_T")


def setup_otel(
    *,
    service_name: str,
    service_version: str,
    environment: str,
    enable_fastapi: bool = False,
    enable_asgi: bool = False,
    enable_httpx: bool = False,
    enable_redis: bool = False,
) -> None:  # pylint: disable=too-many-statements
    """Initialize OpenTelemetry tracing and metrics.

    This function is idempotent and reads standard OTEL_* environment variables
    to select exporters and endpoints.

    Args:
        service_name: Logical service name (resource attribute).
        service_version: Version string.
        environment: Deployment environment (e.g., prod, dev).
        enable_fastapi: Enable FastAPI instrumentation when available.
        enable_asgi: Enable ASGI instrumentation when available.
        enable_httpx: Enable httpx instrumentation when available.
        enable_redis: Enable Redis instrumentation when available.
    """
    # pylint: disable=too-many-statements
    global _SETUP_DONE  # pylint: disable=global-statement
    if _SETUP_DONE:  # pragma: no cover
        return

    # Lazy imports via importlib to avoid static import errors under pylint
    otel_metrics = importlib.import_module("opentelemetry.metrics")  # type: ignore
    otel_trace = importlib.import_module("opentelemetry.trace")  # type: ignore
    exp_grpc_metric = importlib.import_module(
        "opentelemetry.exporter.otlp.proto.grpc.metric_exporter"
    )
    exp_grpc_trace = importlib.import_module(
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"
    )
    exp_http_metric = importlib.import_module(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter"
    )
    exp_http_trace = importlib.import_module(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter"
    )
    sdk_metrics = importlib.import_module("opentelemetry.sdk.metrics")
    sdk_metrics_export = importlib.import_module("opentelemetry.sdk.metrics.export")
    sdk_resources = importlib.import_module("opentelemetry.sdk.resources")
    sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
    sdk_trace_export = importlib.import_module("opentelemetry.sdk.trace.export")
    semconv_inc = importlib.import_module(
        "opentelemetry.semconv._incubating.attributes"
    )
    semconv = importlib.import_module("opentelemetry.semconv.attributes")

    Resource = sdk_resources.Resource
    resource = Resource.create(
        {
            semconv.service_attributes.SERVICE_NAME: service_name,
            semconv.service_attributes.SERVICE_VERSION: service_version,
            semconv_inc.deployment_attributes.DEPLOYMENT_ENVIRONMENT: environment,
            semconv_inc.service_attributes.SERVICE_INSTANCE_ID: os.getenv(
                "HOSTNAME", "local"
            ),
        }
    )

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf").lower()

    # Traces
    if protocol.startswith("http"):
        trace_exporter = exp_http_trace.OTLPSpanExporter(endpoint=endpoint)
    else:
        # gRPC default
        addr = endpoint.replace("http://", "").replace("https://", "")
        trace_exporter = exp_grpc_trace.OTLPSpanExporter(endpoint=addr)

    TracerProvider = sdk_trace.TracerProvider
    BatchSpanProcessor = sdk_trace_export.BatchSpanProcessor
    tp = TracerProvider(resource=resource)
    tp.add_span_processor(BatchSpanProcessor(trace_exporter))
    otel_trace.set_tracer_provider(tp)

    # Metrics
    if protocol.startswith("http"):
        metric_exporter = exp_http_metric.OTLPMetricExporter(endpoint=endpoint)
    else:
        addr = endpoint.replace("http://", "").replace("https://", "")
        metric_exporter = exp_grpc_metric.OTLPMetricExporter(endpoint=addr)

    PeriodicExportingMetricReader = sdk_metrics_export.PeriodicExportingMetricReader
    MeterProvider = sdk_metrics.MeterProvider
    metric_reader = PeriodicExportingMetricReader(exporter=metric_exporter)
    mp = MeterProvider(resource=resource, metric_readers=[metric_reader])
    otel_metrics.set_meter_provider(mp)

    # Optional auto-instrumentation (lazily import each instrumentor)
    # For FastAPI, call FastAPIInstrumentor.instrument_app(app) after the app
    # instance is created (see tripsage/api/main.py).
    if enable_asgi:
        with suppress(Exception):  # pragma: no cover
            asgi_inst = importlib.import_module("opentelemetry.instrumentation.asgi")
            asgi_inst.ASGIInstrumentor().instrument()
    if enable_httpx:
        with suppress(Exception):  # pragma: no cover
            httpx_inst = importlib.import_module("opentelemetry.instrumentation.httpx")
            httpx_inst.HTTPXClientInstrumentor().instrument()
    if enable_redis:
        with suppress(Exception):  # pragma: no cover
            redis_inst = importlib.import_module("opentelemetry.instrumentation.redis")
            redis_inst.RedisInstrumentor().instrument()

    _SETUP_DONE = True


def get_tracer(name: str):
    """Return a tracer for the given name.

    Works even if setup_otel() was not called; returns a no-op provider when
    OpenTelemetry is unavailable.
    """
    try:  # Lazy import to avoid hard dependency at import time
        from opentelemetry import trace as otel_trace  # type: ignore

        return otel_trace.get_tracer(name)
    except ImportError:  # pragma: no cover - fallback when OTEL missing

        class _NoopSpan:
            """No-op span with attribute/exception stubs."""

            def __enter__(self):
                """Enter no-op span."""
                return self

            def __exit__(self, *_exc):
                """Exit no-op span."""
                return False

            def set_attribute(self, *_a: Any, **_k: Any) -> None:
                """Ignore attribute set."""

            def record_exception(self, *_a: Any, **_k: Any) -> None:
                """Ignore exception record."""

        class _NoopTracer:
            """Factory for no-op span context manager."""

            def start_as_current_span(self, *_a: Any, **_k: Any):
                """Return a no-op span context manager."""
                return _NoopSpan()

        return _NoopTracer()


def get_meter(name: str):
    """Return a meter for the given name.

    Falls back to a no-op meter if OpenTelemetry metrics are unavailable.
    """
    try:  # Lazy import at call time
        from opentelemetry import metrics as otel_metrics  # type: ignore

        return otel_metrics.get_meter(name)
    except ImportError:  # pragma: no cover - fallback when OTEL missing

        class _NoopHistogram:
            """No-op histogram instrument."""

            def record(self, *_a: Any, **_k: Any) -> None:
                """Ignore histogram record."""

        class _NoopMeter:
            """No-op meter with histogram and gauge factories."""

            def create_histogram(self, *_a: Any, **_k: Any) -> _NoopHistogram:
                """Return a no-op histogram."""
                return _NoopHistogram()

            def create_observable_gauge(self, *_a: Any, **_k: Any) -> None:
                """Ignore observable gauge creation."""

            class _NoopCounter:
                def add(self, *_a: Any, **_k: Any) -> None:
                    """Ignore counter add."""

            def create_counter(self, *_a: Any, **_k: Any) -> _NoopCounter:
                """Return a no-op counter."""
                return _NoopMeter._NoopCounter()

        return _NoopMeter()


def trace_span(
    name: str | None = None,
    attrs: dict[str, Any]
    | Callable[[tuple[Any, ...], dict[str, Any]], dict[str, Any]]
    | None = None,
):
    """Decorator to trace a function as a span.

    Args:
        name: Optional span name; defaults to function qualname.
        attrs: Optional static attributes or a callable producing attributes.
    """

    def _decorator(
        func: Callable[_P, _T] | Callable[_P, Awaitable[_T]],
    ) -> Callable[_P, _T] | Callable[_P, Awaitable[_T]]:
        tracer = get_tracer(func.__module__)
        span_name = name or func.__qualname__

        @wraps(func)
        def _sync(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            with tracer.start_as_current_span(span_name) as span:
                if attrs:
                    a = attrs(args, kwargs) if callable(attrs) else attrs
                    for k, v in a.items():
                        span.set_attribute(k, v)
                try:
                    result = func(*args, **kwargs)
                    return cast(_T, result)
                except Exception as e:  # pragma: no cover
                    span.record_exception(e)
                    raise

        @wraps(func)
        async def _async(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            with tracer.start_as_current_span(span_name) as span:
                if attrs:
                    a = attrs(args, kwargs) if callable(attrs) else attrs
                    for k, v in a.items():
                        span.set_attribute(k, v)
                try:
                    return await func(*args, **kwargs)  # type: ignore[func-returns-value]
                except Exception as e:  # pragma: no cover
                    span.record_exception(e)
                    raise

        if _is_coroutine(func):
            return cast(Callable[_P, Awaitable[_T]], _async)
        return cast(Callable[_P, _T], _sync)

    return _decorator


def record_histogram(
    name: str,
    *,
    unit: str = "s",
    description: str = "Function duration in seconds",
    attr_fn: Callable[[tuple[Any, ...], dict[str, Any]], dict[str, Any]] | None = None,
):
    """Decorator to record function duration into a histogram.

    Args:
        name: Histogram instrument name.
        unit: Measurement unit.
        description: Instrument description.
        attr_fn: Optional callable computing attributes from args/kwargs.
    """

    def _decorator(
        func: Callable[_P, _T] | Callable[_P, Awaitable[_T]],
    ) -> Callable[_P, _T] | Callable[_P, Awaitable[_T]]:
        meter = get_meter(func.__module__)
        hist = meter.create_histogram(name, unit=unit, description=description)

        @wraps(func)
        def _sync(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            start = time.perf_counter()
            try:
                return cast(_T, func(*args, **kwargs))
            finally:
                dur = time.perf_counter() - start
                attributes = attr_fn(args, kwargs) if attr_fn else {}
                hist.record(dur, attributes)

        @wraps(func)
        async def _async(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            start = time.perf_counter()
            try:
                return await cast(  # type: ignore[func-returns-value]
                    Awaitable[_T], func(*args, **kwargs)
                )
            finally:
                dur = time.perf_counter() - start
                attributes = attr_fn(args, kwargs) if attr_fn else {}
                hist.record(dur, attributes)

        if _is_coroutine(func):
            return cast(Callable[_P, Awaitable[_T]], _async)
        return cast(Callable[_P, _T], _sync)

    return _decorator


def create_observable_gauge(
    name: str,
    callback: Callable[[CallbackOptions], list[Observation]],
    *,
    unit: str = "1",
    description: str = "",
) -> None:
    """Register an asynchronous observable gauge.

    Args:
        name: Instrument name.
        callback: Observation callback.
        unit: Unit string (e.g., "1").
        description: Instrument description.
    """
    meter = get_meter("observability")
    meter.create_observable_gauge(name, [callback], unit=unit, description=description)


def _is_coroutine(func: Callable[..., Any]) -> bool:
    """Return True if the function is a coroutine function."""
    return getattr(func, "__code__", None) and bool(func.__code__.co_flags & 0x80)  # type: ignore[union-attr]
