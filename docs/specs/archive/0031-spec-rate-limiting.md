# SPEC-0031: Rate Limiting Strategy (Frontend API routes + Backend)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-10-24

## Objective

Define and implement a simple, environment-gated rate limiting approach for Next.js Route Handlers using `@upstash/ratelimit` + `@upstash/redis`.

**Note:** Python FastAPI backend has been completely removed. All rate limiting now occurs in Next.js route handlers via the `withApiGuards` factory pattern.

## Frontend (Next.js) — Upstash Ratelimit

- Library: `@upstash/ratelimit@2.0.6`, `@upstash/redis`.
- Activation: when both `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are present.
- Pattern:
  - `const ratelimit = new Ratelimit({ redis: Redis.fromEnv(), limiter: Ratelimit.slidingWindow(20, '1 m'), prefix: 'ratelimit:attachments', analytics: true });`
  - Identifier: `${bearer || 'anon'}:${ip}` using `x-forwarded-for`/`x-real-ip` and `Authorization`.
  - On reject: 429 with `X-RateLimit-*` headers.

## Backend (FastAPI) — SlowAPI

**Note:** Python FastAPI backend has been removed. All rate limiting now occurs in Next.js route handlers using Upstash Ratelimit. This section is retained for historical reference only.

- ~~Library: `slowapi` with limits backends. Storage URI derived from env; falls back to memory.~~
- ~~Decorators used on chat endpoints (e.g., `@limiter.limit('20/minute')`).~~
- Upstash REST credentials (`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`) enable rate limiting; no TCP Redis URLs are used in the current frontend.

## Compatibility

- All rate limiting occurs in Next.js route handlers via `withApiGuards` factory pattern.
- Rate limiters are initialized per-request (not module-scope) for serverless compatibility.
- No feature flags. Limits are configured by env presence only.

## Changelog

- 1.1.0 (2025-11-24)
  - Updated to reflect Next.js-only architecture (Python FastAPI backend removed).
  - Clarified `withApiGuards` factory pattern usage.
- 1.0.0 (2025-10-24)
  - Initial rate limiting spec covering Next.js handlers and FastAPI routes.
