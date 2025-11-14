# Frontend Observability & Operational Alerts

This note explains how frontend code emits telemetry so engineers can add spans,
logs, and alerts consistently.

## OpenTelemetry spans

- Use `withTelemetrySpan` (`frontend/src/lib/telemetry/span.ts`) for async work.
- The helper already redacts attributes you mark via `redactKeys`.
- All spans share the tracer exported by `getTelemetryTracer()` so traces group
  under the `tripsage-frontend` service name.

## Operational alerts (log-based)

Some failures degrade gracefully (e.g., Redis unavailable) but still need paging.
To keep things lightweight we ship structured JSON logs that observability drains
convert into alerts.

- Call `emitOperationalAlert(event, { severity, attributes })`.
- Logs are emitted as:

```text
[operational-alert] {"event":"webhook.verification_failed","severity":"error","attributes":{"reason":"invalid_signature"},"source":"tripsage-frontend","timestamp":"2025-11-14T00:00:00.000Z"}
```

- `severity` defaults to `"error"` (uses `console.error`); `"warning"` routes to
  `console.warn`. Keep attributes low-cardinality and avoid secrets.

### Current events

| Event                      | Severity | Attributes                | Trigger                                                   |
|----------------------------|----------|---------------------------|-----------------------------------------------------------|
| `redis.unavailable`        | error    | `feature` (cache module)  | `warnRedisUnavailable` when Upstash credentials missing   |
| `webhook.verification_failed` | error | `reason` (`missing_secret_env`, `invalid_signature`, `invalid_json`, `invalid_payload_shape`) | `parseAndVerify` failures prior to processing payloads |

### Adding a new alert

1. Decide if the condition truly needs paging. Prefer spans or metrics for noisy cases.
2. Call `emitOperationalAlert` near the existing error handling path.
3. Update this document and the relevant runbooks (operator docs) with the new event name and attributes.
4. If applicable, add a unit test that stubs `console.error`/`console.warn` to verify the payload.

## Integration with runbooks

- Operator docs already mention watching for `redis.unavailable` and
  `webhook.verification_failed` alerts when diagnosing cache/webhook issues.
- Deployment guides include steps to check `.github/workflows/deploy.yml` and
  `scripts/operators/verify_webhook_secret.sh`, so keep those docs in sync when
  adding future alerts or telemetry changes.
