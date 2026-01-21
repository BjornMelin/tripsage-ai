# ADR-0046: OTEL Tracing for Next.js 16 Route Handlers

**Version**: 1.1.0  
**Status**: Accepted  
**Date**: 2026-01-21  
**Category**: Observability  
**Domain**: Tracing / Telemetry  
**Related ADRs**: ADR-0031, ADR-0032, ADR-0040, ADR-0041  
**Related Specs**: -

## Context

- The app runs on Next.js App Router (Node 24.x) and deploys to Vercel, where server-side tracing must remain compatible with Vercel features (Session Tracing / Trace Drains).
- We need consistent server-side span/event patterns for route handlers, server actions, AI SDK calls, Supabase SSR, and Upstash/QStash.
- We also want optional client-side tracing to correlate browser actions to server route spans via `traceparent`, without impacting UX or leaking PII.

## Decision

We adopt a Vercel-first server setup + a minimal, standards-based browser setup:

### Server (Vercel / Next.js)

- Use `@vercel/otel` via the Next.js instrumentation hook at `src/instrumentation.ts`.
- Keep server code free of direct OpenTelemetry API calls except in telemetry infrastructure (`src/lib/telemetry/*` and `src/lib/supabase/factory.ts`).
- Server spans/events/logs are emitted through the repository helpers:
  - `withTelemetrySpan()` / `withTelemetrySpanSync()` (`src/lib/telemetry/span.ts`)
  - `recordTelemetryEvent()` and error helpers
  - `createServerLogger()` (`src/lib/telemetry/logger.ts`)

### Client (Browser)

- Initialize OpenTelemetry Web tracing via `initTelemetry()` (`src/lib/telemetry/client.ts`), invoked from `TelemetryProvider` (`src/components/providers/telemetry-provider.tsx`) in the root layout.
- Use `WebTracerProvider({ spanProcessors: [...] })` with `BatchSpanProcessor` and `OTLPTraceExporter` for browser traces.
- Normalize `NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` to ensure the exporter URL ends with `/v1/traces`.
- Prevent self-instrumentation by adding the exporter URL to `FetchInstrumentation.ignoreUrls`.
- Propagate `traceparent` only for same-origin requests to enable browser → server trace correlation.
- Use `ZoneContextManager` (via `zone.js`) to improve async context propagation in the browser.
- Use `semconvStabilityOptIn: "http/dup"` for safer HTTP semantic convention migration (emit stable + legacy attributes).

## Consequences

### Positive

- Uniform tracing across AI routes and infra calls; easier debugging and incident response.
- Vercel-native server tracing (Trace Drains / Session Tracing) stays supported.
- Client → server correlation works for same-origin fetches via `traceparent`.

### Negative

- Minor overhead from spans and logging; mitigated by upstream sampling and batching.
- Client bundle cost for `zone.js` is paid only when client telemetry is initialized (loaded outside the critical bundle via `TelemetryProvider`).

### Neutral

- Observability is additive; it does not change business logic.

## Alternatives Considered

### Ad-hoc per-route tracing

Rejected: leads to inconsistent attributes and gaps; higher ops burden.

### Rely solely on platform defaults (no custom spans)

Rejected: insufficient visibility into AI/tool calls, cache/ratelimit interactions.

## References

- Next.js OpenTelemetry guide: <https://nextjs.org/docs/app/building-your-application/optimizing/open-telemetry>
- Next.js instrumentation hook: <https://nextjs.org/docs/app/guides/instrumentation>
- Vercel instrumentation: <https://vercel.com/docs/tracing/instrumentation>
- OpenTelemetry JS browser setup: <https://opentelemetry.io/docs/languages/js/getting-started/browser/>
- OpenTelemetry JS manual instrumentation: <https://opentelemetry.io/docs/languages/js/instrumentation/>
- OpenTelemetry JS releases: <https://github.com/open-telemetry/opentelemetry-js/releases>
