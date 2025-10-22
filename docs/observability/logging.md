# Logging with OTEL Trace Correlation

This project can inject OpenTelemetry `trace_id` and `span_id` into Python log records so you can correlate logs with traces in your observability backend.

## Enable correlation at startup

The application installs a small logging filter at startup (see `tripsage/api/main.py`). If you build your own service, call:

```python
from tripsage_core.observability.log_correlation import install_trace_log_correlation
install_trace_log_correlation()  # root logger
```

## Example logging formatter

Configure your logging format to include `%(trace_id)s` and `%(span_id)s`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s %(levelname)s %(trace_id)s %(span_id)s "
        "%(name)s: %(message)s"
    ),
)
```

This produces log lines like:

```text
2025-10-22 10:14:32,123 INFO f1ab... 9cde... tripsage.api.routers.trips: Creating trip for user: 123
```

If no span is active the fields are empty strings.

## Notes

- The filter is safe: if OpenTelemetry isn’t installed or a span isn’t active, logging continues normally.
- Prefer a single OTEL pipeline (OTLP) and avoid enabling multiple exporters in the same process.
