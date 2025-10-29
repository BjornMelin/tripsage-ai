"""Logging utilities for OTEL trace/span correlation.

Provides a minimal filter to inject trace_id/span_id into log records when a
current span exists. Optional and safe: never breaks logging.
"""

from __future__ import annotations

import logging


try:
    from opentelemetry import trace as otel_trace  # type: ignore
except Exception:  # noqa: BLE001 - optional dependency at runtime
    otel_trace = None  # type: ignore[assignment]


class _TraceContextFilter(logging.Filter):
    """Inject `trace_id` and `span_id` attributes when a current span exists."""

    def filter(self, record: logging.LogRecord) -> bool:
        if otel_trace is None:
            return True
        try:
            span = otel_trace.get_current_span()
            ctx = span.get_span_context()
            if span.is_recording() and getattr(ctx, "is_valid", lambda: False)():
                record.trace_id = f"{ctx.trace_id:032x}"
                record.span_id = f"{ctx.span_id:016x}"
            else:
                record.trace_id = ""
                record.span_id = ""
        except Exception:  # noqa: BLE001 - logging must not fail
            record.trace_id = ""
            record.span_id = ""
        return True


def install_trace_log_correlation(logger: logging.Logger | None = None) -> None:
    """Install a filter on the given logger to add trace/span ids."""
    target = logger or logging.getLogger()
    for f in target.filters:
        if isinstance(f, _TraceContextFilter):
            return
    target.addFilter(_TraceContextFilter())
