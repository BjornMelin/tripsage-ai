# ADR: Centralized Rate Limiting in Next.js (Upstash)

Status: Accepted

Context

- Prior FastAPI SlowAPI limiter exists; dual backends cause drift and uneven limits. Next.js 16 App Router is canonical for APIs.

Decision

- Centralize rate limiting in Next.js using Upstash (`@upstash/ratelimit` + `@upstash/redis`).
- Identifier: prefer a stable **hashed** user identifier when authenticated (e.g., `user:${sha256(user.id)}`); otherwise use a **hashed** client IP derived from trusted headers. Never use raw IP/user IDs as Upstash identifiers.
- Budgets per category: chat (60/min), tools sensitive (20/min), BYOK CRUD (10/min), validation (20/min).
- Expose `Retry-After` on 429. Record counters in OTel as attributes.
- Explicit degraded-mode policy (fail-open vs fail-closed):
  - Privileged/cost-bearing endpoints must **fail closed** (`503 rate_limit_unavailable`) when rate limiting cannot be enforced.
  - Non-privileged endpoints may **fail open** for availability, but must emit a deduped operational alert (`ratelimit.degraded`).
  - Treat Upstash timeouts (`success: true`, `reason: "timeout"`) as degraded infrastructure and apply the same policy (Upstash allows-by-default on timeout).

Rationale (Decision Framework)

- Leverage (35%): 9.5 — managed service, library-first.
- Value (30%): 9.0 — consistent user experience and protection.
- Maint. (25%): 9.2 — one implementation; remove Python limiter.
- Adapt (10%): 8.8 — portable keys; Edge-safe.
- Weighted total: 9.27/10 (≥ 9.0 threshold).

Consequences

- Remove Python SlowAPI limiter and configs after migration.
- Introduce shared helper `lib/ratelimit.ts` and route wrappers.
- Add tests for headers and enforcement.

References

- Upstash template: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
- Upstash Ratelimit (TS) – Timeout behavior: <https://upstash.com/docs/redis/sdks/ratelimit-ts/features#timeout>
- Upstash Ratelimit (TS) – `limit()` response (`reason: "timeout"`): <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods#limit>
- Next.js Edge guidance: <https://nextjs.org/blog/next-16#proxyts-formerly-middlewarets>
