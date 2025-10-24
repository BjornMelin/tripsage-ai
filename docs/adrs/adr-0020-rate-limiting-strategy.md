# ADR-0020: Rate Limiting Strategy (Frontend @upstash/ratelimit + Backend SlowAPI)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-24
**Category**: security
**Domain**: Rate Limiting (Upstash/SlowAPI)

## Context

We need deterministic, low-overhead limits for user-facing endpoints:

- Next.js Route Handlers (attachments upload) should be protected at the edge without requiring TCP Redis.
- FastAPI services already use SlowAPI; when a TCP Redis URL is available, we want shared limits across workers, else memory fallback.

## Decision

- Frontend: adopt `@upstash/ratelimit@2.0.6` with `@upstash/redis`, enabled when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set.
  - Use `slidingWindow(20, '1 m')` for `POST /api/chat/attachments`.
  - Identifier: `${bearer || 'anon'}:${ip}` from `x-forwarded-for|x-real-ip` and `Authorization`.
  - On reject: return 429 with `X-RateLimit-*` headers.
- Backend: keep SlowAPI decorators (e.g., `@limiter.limit('20/minute')`). Resolve storage URI from env to enable async Redis; fallback to memory.
  - Do not attempt to share counters between TS (@upstash REST) and Python (TCP limits) layers.

## Consequences

Positive

- Predictable request ceilings near the ingress for expensive routes.
- Works in serverless environments without TCP.

Negative

- Separate counters across layers; not globally unified. Acceptable for now.

## Alternatives Considered

- Global gateway-level limiter: out of scope.
- Using only SlowAPI: does not protect Next edge routes.

## References

- Frontend code: `frontend/src/app/api/chat/attachments/route.ts`
- Backend code: `tripsage/api/limiting.py`, `tripsage/api/routers/chat.py`

## Changelog

- 1.0.0 (2025-10-24) — Initial decision and implementation notes.
