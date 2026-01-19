# ADR-0032: Centralized rate limiting (Next.js + Upstash)

**Version**: 1.1.0  
**Status**: Accepted  
**Date**: 2025-11-02  
**Category**: Platform / Security  
**Domain**: Rate limiting / Abuse controls  
**Related ADRs**: ADR-0046, ADR-0047, ADR-0062, ADR-0067, ADR-0068  
**Related Specs**: SPEC-0108, SPEC-0109, SPEC-0110

## Context

- TripSage previously had multiple rate-limiting strategies across runtimes, which creates drift and uneven enforcement.
- Next.js App Router (Route Handlers + Server Actions) is the canonical runtime for APIs.
- Rate limiting must be:
  - centralized and consistent
  - request-scoped (no module-scope clients in Route Handlers)
  - safe (hashed identifiers; no raw IPs/user IDs)
  - observable (headers + telemetry)
  - resilient (explicit degraded-mode policy)

## Decision

- Centralize all server-side rate limiting in Next.js using Upstash:
  - `@upstash/ratelimit` for algorithms and counters
  - `@upstash/redis` for backing storage (HTTP client)
- Canonical configuration lives in `src/lib/ratelimit/routes.ts` and is consumed by:
  - API routes: `src/lib/api/factory.ts` (`withApiGuards({ rateLimit: ... })`)
  - Webhooks: `src/lib/webhooks/rate-limit.ts`
  - AI tools: `src/ai/lib/tool-factory.ts`

### Identifier policy (mandatory)

- Prefer a stable **hashed** user identifier when authenticated (e.g., `user:${sha256(user.id)}`).
- Otherwise use a **hashed** client IP derived from trusted headers.
- Never pass raw IPs or raw user IDs to Upstash.
- Canonical identifier helpers:
  - `src/lib/ratelimit/identifier.ts`
  - `src/lib/http/ip.ts`

### Response headers (HTTP)

- Attach standard headers on 429 responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset` (milliseconds)
  - `Retry-After` (seconds)
- Canonical helpers: `src/lib/ratelimit/headers.ts`

### Degraded-mode policy (fail-open vs fail-closed)

Privileged/cost-bearing endpoints must **fail closed** (`503 rate_limit_unavailable`) when rate limiting cannot be enforced (missing Redis config, Redis unavailable, enforcement errors).

Non-privileged endpoints may **fail open** for availability, but must emit a deduped operational alert (`ratelimit.degraded`).

Upstash timeout behavior is treated as degraded infrastructure: `success: true` with `reason: "timeout"` still triggers the same degraded-mode policy.

## Rationale (Decision Framework)

- Leverage (35%): 9.5 — managed service, library-first.
- Value (30%): 9.0 — consistent user experience and protection.
- Maint. (25%): 9.2 — one implementation; remove Python limiter.
- Adapt (10%): 8.8 — portable keys; Edge-safe.
- Weighted total: 9.27/10 (≥ 9.0 threshold).

## Consequences

### Positive

- One enforcement policy and one set of helpers across API routes, webhooks, and tools.
- Explicit degraded-mode behavior reduces ambiguity during Upstash outages/timeouts.
- Consistent telemetry and headers improve operability.

### Negative

- Adds a hard dependency on Upstash for strict enforcement on privileged routes.

### Neutral

- Rate limiting remains an application-layer guard; database policies (RLS) remain the source of truth for authorization.

## Post-acceptance updates (2026-01-19)

- Enabled Upstash “global dynamic limit” support by setting `dynamicLimits: true` in all `Ratelimit` constructors used by the app (API routes, webhooks, AI tools). This keeps steady-state behavior unchanged while allowing operators to set a global limit at runtime via Upstash dynamic limit methods (`setDynamicLimit` / `getDynamicLimit`).

## References

- Upstash Next.js template: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
- Upstash Ratelimit (TS) – Timeout behavior: <https://upstash.com/docs/redis/sdks/ratelimit-ts/features#timeout>
- Upstash Ratelimit (TS) – `limit()` response (`reason: "timeout"`): <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods#limit>
- Upstash Ratelimit (TS) – Dynamic limit methods: <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods>
- ADR-0067 (Upstash Redis/QStash), ADR-0068 (abuse controls), ADR-0047 (runtime policy)
