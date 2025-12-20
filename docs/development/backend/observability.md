# Observability & Telemetry

This guide covers tracing, structured logging, and operational alerts for the Next.js app (route handlers + server utilities + client components).

## Automatic instrumentation (`@vercel/otel`)

`src/instrumentation.ts` registers `@vercel/otel` with `TELEMETRY_SERVICE_NAME` (`"tripsage-frontend"`). This enables default Next.js spans (Route Handlers, Server Components, Middleware) plus runtime instrumentations supported by the platform.

Use custom spans/events from `@/lib/telemetry/*` for application-level operations and stable naming/attributes.

## Approved Telemetry & Logging Entrypoints

Server code must use these helpers exclusively. Direct usage of `@opentelemetry/api` or `console.*` in server modules is prohibited except in:

- Test files
- Telemetry infrastructure (`src/lib/telemetry/*`, `src/lib/supabase/factory.ts`)

**Client-side exception:** Development-only `console.*` is allowed in client components (`"use client"`) when guarded by `process.env.NODE_ENV === 'development'`. Bundlers (Next.js SWC, Terser) perform dead code elimination, removing these calls from production bundles entirely.

**Server helpers (default):**

- `withTelemetrySpan()` / `withTelemetrySpanSync()` - Wrap operations with spans
- `getTelemetryTracer()` - Acquire tracer instance (prefer `withTelemetrySpan`, not direct calls)
- `recordTelemetryEvent()` - Emit a lightweight event (`event.{name}` span)
- `addEventToActiveSpan()` - Attach events to the current span
- `recordErrorOnSpan()` / `recordErrorOnActiveSpan()` - Record exception + ERROR status
- `createServerLogger()` - Structured logging (records `log.*` attributes via telemetry)
- `emitOperationalAlert()` - High-severity events intended for paging (use sparingly)

**Client helpers (`"use client"`):**

- `initTelemetry()` - Initialize OTEL Web SDK (export + fetch instrumentation)
- `withClientTelemetrySpan()` - Optional client-only spans (rare)
- `recordClientErrorOnActiveSpan()` - Attach sanitized errors to the active span

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
- **Note:** `@/lib/telemetry/span` is server-only (marked with `"server-only"`). Client-side telemetry is handled separately (see Client-side telemetry section below).

Use `withTelemetrySpanSync` for synchronous operations (e.g., client initialization).

## AI SDK telemetry (`experimental_telemetry`)

AI SDK v6 calls should set `experimental_telemetry` with a stable `functionId`. Keep `metadata` low-cardinality and avoid PII (no email/name/raw user IDs; prefer counts and booleans).

Current `functionId` values in this codebase:

| Function ID | Location | Notes |
| --- | --- | --- |
| `agent.{agentType}` | `src/ai/agents/agent-factory.ts` | ToolLoopAgent instances |
| `router.classifyUserMessage` | `src/ai/agents/router-agent.ts` | Message classification |
| `agent.memory.summarize` | `src/ai/agents/memory-agent.ts` | Memory write summary |
| `memory.insights.generate` | `src/app/api/memory/[intent]/[userId]/route.ts` | Insights generation (`intent="insights"`) |
| `ai.stream.demo` | `src/app/api/ai/stream/route.ts` | Demo streaming route (requires `ENABLE_AI_DEMO="true"`) |

## Telemetry-safe identifiers

Do not record raw user/session identifiers in telemetry spans by default.

- Use `hashTelemetryIdentifier()` from `src/lib/telemetry/identifiers.ts` to emit stable pseudonyms (e.g., `user.id_hash`, `session.id_hash`) when `TELEMETRY_HASH_SECRET` is configured (required in production).
- In non-production, if `TELEMETRY_HASH_SECRET` is unset, identifier attributes should be omitted (fail-safe).
- Policy and attribute classification: `docs/development/security/telemetry-data-classification.md`.

## Infrastructure spans (catalog)

Span names are stable. Attributes must be low-cardinality and must not contain secrets/PII.

### Supabase

**Factory spans (`src/lib/supabase/factory.ts`):**

| Span name | When |
| --- | --- |
| `supabase.init` | `createServerSupabase()` |
| `middleware.supabase.init` | `createMiddlewareSupabase()` (tracing usually disabled) |
| `supabase.auth.getUser` | `getCurrentUser()` |

**CRUD spans (`src/lib/supabase/typed-helpers.ts`):**

| Span name | Helper |
| --- | --- |
| `supabase.insert` | `insertSingle` |
| `supabase.update` | `updateSingle` |
| `supabase.select` | `getSingle`, `getMaybeSingle` |
| `supabase.upsert` | `upsertSingle` |
| `supabase.delete` | `deleteSingle` |

Common attributes:

- `db.system`: `"postgres"`
- `db.name`: `"tripsage"`
- `db.supabase.operation`: `"select" | "insert" | "update" | "delete" | "upsert" | "init" | "auth.getUser"`
- `db.supabase.table`: table name (typed helpers)
- `db.supabase.row_count`: result count (delete)

### Upstash Redis cache

Cache helpers in `src/lib/cache/upstash.ts` emit spans:

| Span name | Operation | Notes |
| --- | --- | --- |
| `cache.get` | get | Sets `cache.hit` and `cache.parse_error` |
| `cache.get_safe` | get | Sets `cache.status` (`hit`/`miss`/`invalid`), `cache.has_schema`, and `cache.validation_failed` |
| `cache.set` | set | Sets `cache.ttl_seconds` and `cache.value_bytes` |
| `cache.delete` | delete | Sets `cache.deleted_count` |
| `cache.delete_many` | delete | Sets `cache.key_count` and `cache.deleted_count` |

Common attributes:

- `cache.system`: `"upstash"`
- `cache.operation`: `"get" | "set" | "delete"`
- `cache.namespace`: low-cardinality namespace derived from the key
- `cache.key_length`: key length (we intentionally do not record raw keys)
- `cache.unavailable`: `true` when Redis is not configured
- `cache.has_schema`: `true` when a schema is provided (`cache.get_safe`)
- `cache.validation_failed`: `true` when schema validation fails (`cache.get_safe`)

### QStash + DLQ

QStash helpers emit spans for enqueue and DLQ operations:

| Span name | Location |
| --- | --- |
| `qstash.enqueue` | `src/lib/qstash/client.ts` |
| `qstash.dlq.push` | `src/lib/qstash/dlq.ts` |
| `qstash.dlq.list` | `src/lib/qstash/dlq.ts` |
| `qstash.dlq.remove` | `src/lib/qstash/dlq.ts` |

## Client-side telemetry

Client-side OpenTelemetry is minimal and focused on distributed tracing and error reporting:

- **Initialization:** `initTelemetry()` from `@/lib/telemetry/client` sets up WebTracerProvider and FetchInstrumentation. This is automatically called via `TelemetryProvider` in the root layout. It enables:
  - Automatic tracing of fetch requests to API routes
  - Trace context propagation via `traceparent` headers (distributed tracing from client → server)
- **Error recording:** `recordClientErrorOnActiveSpan()` from `@/lib/telemetry/client-errors` records client-side errors on active spans, linking errors to traces.

**Important:** Client-side telemetry is intentionally small. Do not import server-only helpers (`@/lib/telemetry/span`, `@/lib/telemetry/logger`) from client code. Use `recordClientErrorOnActiveSpan` to link client errors to in-flight traces; use `withClientTelemetrySpan` only for rare, client-only spans.

**Configuration:**

```bash
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

## Structured logging

### Server logger (recommended for most cases)

Use `createServerLogger` for route handlers, tools, and server utilities:

```typescript
import { createServerLogger } from "@/lib/telemetry/logger";

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

- **Logging policy by context:**
  - **Server code (route handlers, tools, shared libs):** Must use telemetry helpers (`createServerLogger`, `recordTelemetryEvent`, `withTelemetrySpan`). No `console.*`.
  - **Client-only UI (`"use client"` components/hooks):** Development-only `console.*` is permitted when guarded:

    ```typescript
    if (process.env.NODE_ENV === 'development') {
      console.log('Debug info:', data);
    }
    ```

    These calls are eliminated by Next.js compiler in production builds (dead code elimination).
  - **Zustand stores:** Use `createStoreLogger` from `@/lib/telemetry/store-logger` for error tracking. This records errors on the active OTEL span.

    ```typescript
    import { createStoreLogger } from "@/lib/telemetry/store-logger";

    // In a Zustand store - create logger once at store initialization
    const logger = createStoreLogger({ storeName: "store.my-store" });

    const store = create((set) => ({
      fetchData: async () => {
        try {
          const data = await api.getData();
          set({ data });
        } catch (error) {
          logger.error("Failed to fetch data", {
            message: error instanceof Error ? error.message : String(error),
          });
          throw error;
        }
      },
    }));
    ```

  - **Tests:** `console.*` allowed freely for debugging.
- **Optional:** Configure `compiler.removeConsole` in `next.config.ts` for additional safety:

  ```ts
  import type { NextConfig } from "next";

  const nextConfig: NextConfig = {
    compiler: {
      removeConsole: process.env.NODE_ENV === "production",
      // Or keep console.error: removeConsole: { exclude: ["error"] }
    },
  };

  export default nextConfig;
  ```

- Use concise event names: `api.{module}.{action}_error`
- Include relevant context in attributes (no secrets)
- Use appropriate severity levels: "error", "warning", "info"
- Prefer `createServerLogger` over `recordTelemetryEvent` for most logging needs

| Event                      | Severity | Attributes                | Trigger                                                   |
|----------------------------|----------|---------------------------|-----------------------------------------------------------|
| `api.keys.parse_error`     | error    | `message`, `operation`    | JSON parsing failures in keys API                        |
| `api.keys.auth_error`      | error    | `message`, `operation`    | Authentication failures in keys API                      |
| `api.keys.validation_error`| warning  | `field`, `message`        | Zod validation failures in keys API                      |
| `api.keys.post_error`      | error    | `message`, `operation`    | General POST errors in keys API                          |
| `api.keys.get_error`       | error    | `message`, `operation`    | GET errors in keys API                                   |
| `api.keys.rate_limit_config_error` | error | `hasToken`, `hasUrl`, `message` | Rate limiter configuration missing in production        |
| `api.keys.delete_error`    | error    | `message`, `service`, `operation` | Key deletion failures                                    |
| `api.keys.validate_provider_error` | error | `message`, `provider`, `reason` | Provider key validation failures                         |
| `api.keys.validate.parse_error` | error | `message` | JSON parsing in validate API                             |
| `api.keys.validate.post_error` | error | `message` | General errors in validate API                           |

## Operational alerts (paging)

Use `emitOperationalAlert` for conditions that require operator attention.

Alerts are recorded via telemetry as `alert.{event}` (for example, `alert.redis.unavailable`) with `alert.*` attributes. They do not rely on server `console.*` logging.

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

- `severity` defaults to `"error"`.
- Keep attributes low-cardinality and avoid secrets.
- Do not route normal logs through this channel.

### Operational alerts

| Event                      | Severity | Attributes                | Trigger                                                   |
|----------------------------|----------|---------------------------|-----------------------------------------------------------|
| `redis.unavailable`        | error    | `feature` (cache module)  | `warnRedisUnavailable` when Upstash credentials missing   |
| `webhook.verification_failed` | warning | `reason` (`missing_secret_env`, `missing_signature`, `body_read_error`, `invalid_signature`, `invalid_json`, `invalid_payload_shape`, `payload_too_large`) | `parseAndVerify` failures before processing payloads |
| `ratelimit.degraded`       | error    | `reason`, `degradedMode`, plus `rateLimitKey` (API) or `feature` + `route` (webhooks) | Fail-open fallback when rate limiting cannot be enforced |
| `idempotency.degraded`     | error    | `namespace`, `reason`, `degradedMode` | Fail-open fallback when idempotency cannot be enforced |
| `ai_demo.stream`           | info     | `status`, `has_detail`, `detail_length`, optional HMAC `detail_hash` | Privileged AI demo alert emission (gated) |

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
4. If applicable, add a unit test that asserts the emitted `alert.{event}` telemetry attributes.

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

## References

- `docs/architecture/decisions/adr-0046-otel-tracing-frontend.md`
- Vercel OTEL: <https://vercel.com/docs/observability/otel-overview>
- AI SDK telemetry: <https://v6.ai-sdk.dev/docs/ai-sdk-core/telemetry>
- OpenTelemetry JS: <https://opentelemetry.io/docs/languages/js/>
