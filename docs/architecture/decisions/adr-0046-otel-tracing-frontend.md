# ADR-0046: OTEL Tracing for Next.js 16 Route Handlers

**Version**: 1.0.0  
**Status**: Proposed  
**Date**: 2025-11-20  
**Category**: Observability  
**Domain**: Tracing / Telemetry  
**Related ADRs**: ADR-0031, ADR-0032, ADR-0040, ADR-0041  
**Related Specs**: -

## Context

- OTEL dependencies are present (`@opentelemetry/api`, `@vercel/otel`), but no ADR defines route tracing standards.
- Project rule: server code must use `withTelemetrySpan()`/`withTelemetrySpanSync()` from `@/lib/telemetry/span` (server-only) and `createServerLogger()` from `@/lib/telemetry/logger`; `console.*` is discouraged.
- We need consistent span attributes for AI SDK routes, Supabase SSR, and Upstash/QStash calls.
- Client components use `@/lib/telemetry/client` for client-side OTEL Web initialization and no-op helpers that match the server API surface.

## Decision

- All Next.js route handlers and server utilities must wrap business logic in `withTelemetrySpan` (`withTelemetrySpanSync` for sync).  
- Standard span attributes: `svc: "frontend"`, `route`, `operation`, `provider`, `model`, `tool`, `user_tier`, `cache_hit`, `ratelimit_bucket`.
- Emit structured logs via `createServerLogger()` within spans; prohibit bare `console.*` outside client components/tests.
- Instrument external calls (Supabase, Upstash, QStash, AI Gateway) using OTEL context propagation; attach `traceparent` when supported.
- Sampling: default parent-based; allow per-route overrides for high-traffic endpoints (`ai.stream`, `chat.stream`) via config file in `src/lib/telemetry/config.ts`.

## Consequences

### Positive

- Uniform tracing across AI routes and infra calls; easier debugging and SLO tracking.  
- Standard span attributes and logging improve correlation and incident response.  
- Encourages consistent telemetry hygiene (no stray console logs).

### Negative

- Minor performance overhead from spans and logging; mitigated by sampling.  
- Requires code changes across existing handlers/tests to adopt wrappers.

### Neutral

- Does not change business logic; observational concern only.

## Alternatives Considered

### Ad-hoc per-route tracing

Rejected: leads to inconsistent attributes and gaps; higher ops burden.

### Rely solely on platform defaults (no custom spans)

Rejected: insufficient visibility into AI/tool calls, cache/ratelimit interactions.

## References

- OpenTelemetry API docs  
- Vercel OTEL runtime guidance  
- ADR-0031 (AI API), ADR-0032 (rate limiting), ADR-0040/0041 (webhooks)
