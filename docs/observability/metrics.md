# Duration Histogram Buckets (TRIPSAGE_DURATION_BUCKETS)

The API and services emit duration metrics (for example, request and operation
histograms) via OpenTelemetry. You can tune the histogram bucket boundaries at
runtime using the `TRIPSAGE_DURATION_BUCKETS` environment variable.

## How it works

- The application reads `TRIPSAGE_DURATION_BUCKETS` during OTEL setup
  (see `tripsage_core/observability/otel.py`).
- If set, the value is parsed as a comma‑separated list of bucket boundaries in
  seconds and applied using the OTEL SDK’s explicit bucket histogram
  aggregation.
- If not set, the application uses a sensible default ([0.005s … 10s]).
- If the current OTEL SDK doesn’t expose the optional view API, the application
  falls back to the provider’s defaults (your services continue to run).

## Default buckets

```text
0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
```

## Example: override buckets

Bash:

```bash
export TRIPSAGE_DURATION_BUCKETS=0.01,0.02,0.05,0.1,0.25,0.5,1,2,5
# Restart the service so OTEL setup re-runs with new buckets
```

Docker Compose:

```yaml
services:
  api:
    environment:
      TRIPSAGE_DURATION_BUCKETS: "0.01,0.02,0.05,0.1,0.25,0.5,1,2,5"
```

Kubernetes (Deployment):

```yaml
spec:
  template:
    spec:
      containers:
        - name: api
          env:
            - name: TRIPSAGE_DURATION_BUCKETS
              value: "0.01,0.02,0.05,0.1,0.25,0.5,1,2,5"
```

## Notes

- Buckets are global for the process; keep them consistent across services to
  simplify dashboards and SLOs.
- Avoid excessive bucket counts; they increase exporter payload size and
  cardinality. Start with ≤ 10–12 buckets and adjust based on latency profiles.
- The helper applies to duration histograms created via the OTEL SDK in this
  application (for example, metrics emitted by `@record_histogram`).
