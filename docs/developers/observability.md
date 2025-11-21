# Frontend Observability & Telemetry

This note explains how frontend code emits telemetry for monitoring and debugging.

## Approved Telemetry & Logging Entrypoints

Server code must use these helpers exclusively. Direct usage of `@opentelemetry/api` or `console.*` in server modules is prohibited except in:

- Test files
- Telemetry infrastructure (`lib/telemetry/*`, `lib/supabase/factory.ts`)
- Operational alert sinks (`lib/telemetry/alerts.ts`)

**Core helpers:**

- `getTelemetryTracer()` - Acquire tracer instance (use via `withTelemetrySpan`, not directly)
- `withTelemetrySpan()` - Wrap async operations with spans
- `recordTelemetryEvent()` - Emit structured events without full operation tracing
- `createServerLogger()` - Structured logging for route handlers and tools
- `emitOperationalAlert()` - Critical alerts for paging (use sparingly)

## OpenTelemetry spans

Use `withTelemetrySpan` from `@/lib/telemetry/span` (server-only) for async operations:

```typescript
import { withTelemetrySpan } from "@/lib/telemetry/span";

// Wrap a Supabase operation
const result = await withTelemetrySpan(
  "supabase.auth.getUser",
  {
    attributes: {
      "db.name": "tripsage",
      "db.system": "postgres",
    },
    redactKeys: ["user.id"], // Optional: redact sensitive attributes
  },
  async (span) => {
    // Set additional attributes during execution
    span.setAttribute("user.authenticated", true);
    return await supabase.auth.getUser();
  }
);
```

- The helper automatically handles `SpanStatusCode.OK/ERROR`, exception recording, and span cleanup.
- All spans share the tracer exported by `getTelemetryTracer()` and group under the `tripsage-frontend` service name.
- If you call `span.recordException()` or `span.setStatus({ code: SpanStatusCode.ERROR })` inside the callback, `withTelemetrySpan` will preserve that status instead of overwriting it with OK.
- **Note:** `@/lib/telemetry/span` is server-only (marked with `"server-only"`). Client components should use `@/lib/telemetry/client` for client-side telemetry initialization and no-op helpers that match the server API surface.

## Structured logging

### Server logger (recommended for most cases)

Use `createServerLogger` for route handlers, tools, and server utilities:

```typescript
import { createServerLogger } from "@/lib/logging/server";

const logger = createServerLogger("api.keys", {
  redactKeys: ["apiKey"], // Optional: redact sensitive metadata keys
});

// In a route handler
logger.info("Key stored", { userId: "123", apiKey: "sk-..." }); // apiKey redacted
logger.error("Validation failed", { field: "email", message: "Invalid format" });
logger.warn("Rate limit approaching", { remaining: 5 });
```

- Automatically encodes metadata with `log.*` attribute prefixes
- Supports redaction of sensitive keys
- Uses `recordTelemetryEvent` under the hood

### Telemetry events (for lightweight events)

For structured logging without full operation tracing, use `recordTelemetryEvent`:

```typescript
import { recordTelemetryEvent } from "@/lib/telemetry/span";

// Log API errors with context
recordTelemetryEvent("api.keys.parse_error", {
  attributes: { message: "Invalid JSON", operation: "json_parse" },
  level: "error",
});

// Log validation warnings
recordTelemetryEvent("api.keys.validation_error", {
  attributes: { field: "email", message: "Invalid format" },
  level: "warning",
});
```

**When to use what:**

- `createServerLogger` - Route handlers, tools, utilities (most common)
- `recordTelemetryEvent` - Lightweight events without full context (less common)
- `withTelemetrySpan` - Full operation tracing with timing and error handling
- `emitOperationalAlert` - Critical failures requiring paging (rare)

**Guidelines:**

- **Logging split:** Production/server code must emit telemetry (spans/events or `createServerLogger`). Use `console.*` only in tests and client-only UI to aid local debugging; never ship console logging in backend routes, tools, or shared libs.
- Use concise event names: `api.{module}.{action}_error`
- Include relevant context in attributes (no secrets)
- Use appropriate severity levels: "error", "warning", "info"
- Prefer `createServerLogger` over `recordTelemetryEvent` for most logging needs

| Event                      | Severity | Attributes                | Trigger                                                   |
|----------------------------|----------|---------------------------|-----------------------------------------------------------|
| `api.keys.parse_error`     | error    | `message`, `operation`    | JSON parsing failures in keys API                        |
| `api.keys.auth_error`      | error    | `message`, `operation`    | Authentication failures in keys API                      |
| `api.keys.validation_error`| warning  | `field`, `message`        | Zod validation failures in keys API                      |
| `api.keys.size_limit`      | warning  | `size_bytes`, `limit_bytes`| Request size limit exceeded                              |
| `api.keys.post_error`      | error    | `message`, `operation`    | General POST errors in keys API                          |
| `api.keys.get_error`       | error    | `message`, `operation`    | GET errors in keys API                                   |
| `api.keys.rate_limit_config_error` | error | `hasToken`, `hasUrl`, `message` | Rate limiter configuration missing in production        |
| `api.keys.delete_error`    | error    | `message`, `service`, `operation` | Key deletion failures                                    |
| `api.keys.validate_provider_error` | error | `message`, `provider`, `reason` | Provider key validation failures                         |
| `api.keys.validate.parse_error` | error | `message` | JSON parsing in validate API                             |
| `api.keys.validate.post_error` | error | `message` | General errors in validate API                           |

## Operational alerts (log-based)

Critical failures that need paging use structured JSON alerts via `emitOperationalAlert`.
These are separate from regular telemetry and use console output for log aggregation.

**Use sparingly** - only for conditions that require immediate operator attention. Prefer `createServerLogger` or `recordTelemetryEvent` for normal error logging.

```typescript
import { emitOperationalAlert } from "@/lib/telemetry/alerts";

// Critical infrastructure failure
emitOperationalAlert("redis.unavailable", {
  severity: "error",
  attributes: { feature: "cache.tags" },
});

// Webhook verification failure (security-critical)
emitOperationalAlert("webhook.verification_failed", {
  severity: "error",
  attributes: { reason: "invalid_signature" },
});
```

- Logs are emitted as structured JSON:

```text
[operational-alert] {"event":"webhook.verification_failed","severity":"error","attributes":{"reason":"invalid_signature"},"source":"tripsage-frontend","timestamp":"2025-11-14T00:00:00.000Z"}
```

- `severity` defaults to `"error"` (uses `console.error`); `"warning"` routes to `console.warn`.
- Keep attributes low-cardinality and avoid secrets.
- Do not route normal logs through this channel.

### Operational alerts

| Event                      | Severity | Attributes                | Trigger                                                   |
|----------------------------|----------|---------------------------|-----------------------------------------------------------|
| `redis.unavailable`        | error    | `feature` (cache module)  | `warnRedisUnavailable` when Upstash credentials missing   |
| `webhook.verification_failed` | error | `reason` (`missing_secret_env`, `invalid_signature`, `invalid_json`, `invalid_payload_shape`) | `parseAndVerify` failures prior to processing payloads |

### Adding telemetry events

1. Use `recordTelemetryEvent` for structured logging that doesn't need full operation tracing.
2. Choose concise event names following `api.{module}.{action}_error` pattern.
3. Include relevant context in attributes (avoid secrets, keep low-cardinality).
4. Use appropriate severity levels: "error" for failures, "warning" for validation issues, "info" for notable events.
5. Update this document with the new event name, attributes, and trigger conditions.

### Adding operational alerts

1. Decide if the condition truly needs paging. Prefer telemetry events or metrics for noisy cases.
2. Call `emitOperationalAlert` near the existing error handling path.
3. Update this document and the relevant runbooks (operator docs) with the new event name and attributes.
4. If applicable, add a unit test that stubs `console.error`/`console.warn` to verify the payload.

## Integration with runbooks

- Operator docs already mention watching for `redis.unavailable` and
  `webhook.verification_failed` alerts when diagnosing cache/webhook issues.
- Keys API telemetry events help diagnose BYOK (Bring Your Own Key) issues:
  - `api.keys.rate_limit_config_error`: Indicates missing Upstash configuration in production
  - `api.keys.auth_error`: Authentication failures when storing/retrieving keys
  - `api.keys.parse_error` / `api.keys.validation_error`: Request format issues
- Deployment guides include steps to check `.github/workflows/deploy.yml` and
  `scripts/operators/verify_webhook_secret.sh`, so keep those docs in sync when
  adding future alerts or telemetry changes.
