"""Unified OpenTelemetry setup, accessors, and decorators.

This module centralizes OTEL initialization and provides helpers for tracing
and metrics with minimal, DRY instrumentation.
"""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from opentelemetry import metrics as otel_metrics, trace as otel_trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as OTLPMetricExporterGrpc,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterGrpc,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as OTLPMetricExporterHttp,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterHttp,
)
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv._incubating.attributes import (
    deployment_attributes,
    service_attributes as incubating_service_attributes,
)
from opentelemetry.semconv.attributes import service_attributes


try:
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor,  # type: ignore
    )
except ImportError:  # pragma: no cover - optional
    FastAPIInstrumentor = None  # type: ignore[assignment]

try:
    from opentelemetry.instrumentation.asgi import ASGIInstrumentor  # type: ignore
except ImportError:  # pragma: no cover - optional
    ASGIInstrumentor = None  # type: ignore[assignment]

try:
    from opentelemetry.instrumentation.httpx import (
        HTTPXClientInstrumentor,  # type: ignore
    )
except ImportError:  # pragma: no cover - optional
    HTTPXClientInstrumentor = None  # type: ignore[assignment]

try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor  # type: ignore
except ImportError:  # pragma: no cover - optional
    RedisInstrumentor = None  # type: ignore[assignment]


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
) -> None:
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
    global _SETUP_DONE  # pylint: disable=global-statement
    if _SETUP_DONE:  # pragma: no cover
        return

    resource = Resource.create(
        {
            service_attributes.SERVICE_NAME: service_name,
            service_attributes.SERVICE_VERSION: service_version,
            deployment_attributes.DEPLOYMENT_ENVIRONMENT: environment,
            incubating_service_attributes.SERVICE_INSTANCE_ID: os.getenv(
                "HOSTNAME", "local"
            ),
        }
    )

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf").lower()

    # Traces
    if protocol.startswith("http"):
        trace_exporter = OTLPSpanExporterHttp(endpoint=endpoint)
    else:
        # gRPC default
        addr = endpoint.replace("http://", "").replace("https://", "")
        trace_exporter = OTLPSpanExporterGrpc(endpoint=addr)

    tp = TracerProvider(resource=resource)
    tp.add_span_processor(BatchSpanProcessor(trace_exporter))
    otel_trace.set_tracer_provider(tp)

    # Metrics
    if protocol.startswith("http"):
        metric_exporter = OTLPMetricExporterHttp(endpoint=endpoint)
    else:
        addr = endpoint.replace("http://", "").replace("https://", "")
        metric_exporter = OTLPMetricExporterGrpc(endpoint=addr)

    metric_reader = PeriodicExportingMetricReader(exporter=metric_exporter)
    mp = MeterProvider(resource=resource, metric_readers=[metric_reader])
    otel_metrics.set_meter_provider(mp)

    # Optional auto-instrumentation
    if enable_fastapi and FastAPIInstrumentor is not None:
        with suppress(Exception):  # pragma: no cover
            FastAPIInstrumentor().instrument()
    if enable_asgi and ASGIInstrumentor is not None:
        with suppress(Exception):  # pragma: no cover
            ASGIInstrumentor().instrument()
    if enable_httpx and HTTPXClientInstrumentor is not None:
        with suppress(Exception):  # pragma: no cover
            HTTPXClientInstrumentor().instrument()
    if enable_redis and RedisInstrumentor is not None:
        with suppress(Exception):  # pragma: no cover
            RedisInstrumentor().instrument()

    _SETUP_DONE = True


def get_tracer(name: str):
    """Return a tracer for the given name.

    Returns a valid tracer even if setup_otel() was not called; the tracer will
    be a no-op provider in that case.
    """
    return otel_trace.get_tracer(name)


def get_meter(name: str):
    """Return a meter for the given name."""
    return otel_metrics.get_meter(name)


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
        func: Callable[_P, _T | Awaitable[_T]]
    ) -> Callable[_P, _T | Awaitable[_T]]:
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
        async def _async(*args: _P.args, **kwargs: _P.kwargs) -> _T:  # type: ignore[misc]
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

        return _async if _is_coroutine(func) else _sync

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

    def _decorator(func: Callable[_P, _T | Awaitable[_T]]) -> Callable[_P, Any]:
        meter = get_meter(func.__module__)
        hist = meter.create_histogram(name, unit=unit, description=description)

        @wraps(func)
        def _sync(*args: _P.args, **kwargs: _P.kwargs) -> Any:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                dur = time.perf_counter() - start
                attributes = attr_fn(args, kwargs) if attr_fn else {}
                hist.record(dur, attributes)

        @wraps(func)
        async def _async(*args: _P.args, **kwargs: _P.kwargs) -> Any:  # type: ignore[misc]
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)  # type: ignore[func-returns-value]
            finally:
                dur = time.perf_counter() - start
                attributes = attr_fn(args, kwargs) if attr_fn else {}
                hist.record(dur, attributes)

        return _async if _is_coroutine(func) else _sync

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
