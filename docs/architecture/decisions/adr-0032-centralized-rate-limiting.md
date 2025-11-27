# ADR: Centralized Rate Limiting in Next.js (Upstash)

Status: Accepted

Context

- Prior FastAPI SlowAPI limiter exists; dual backends cause drift and uneven limits. Next.js 16 App Router is canonical for APIs.

Decision

- Centralize rate limiting in Next.js using Upstash (`@upstash/ratelimit` + `@upstash/redis`).
- Identifier: prefer `user.id` (auth) with `req.ip` fallback.
- Budgets per category: chat (60/min), tools sensitive (20/min), BYOK CRUD (10/min), validation (20/min).
- Expose `Retry-After` on 429. Record counters in OTel as attributes.

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
- Next.js Edge guidance: <https://nextjs.org/blog/next-16#proxyts-formerly-middlewarets>
