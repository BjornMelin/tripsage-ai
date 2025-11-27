# ADR-0003: Use Upstash Redis (HTTP) for Caching

**Version**: 1.1.0
**Status**: Accepted
**Date**: 2025-10-22
**Category**: platform
**Domain**: Upstash Redis

## Context

- We deploy on Vercel (Next.js App Router). A connectionless, HTTP-based cache fits serverless well.
- Upstash Redis provides REST/HTTP SDKs, Vercel marketplace integration, and per-request pricing.

## Decision

- Adopt Upstash Redis via the official TypeScript SDK (`@upstash/redis`) for all caching.
- Use `Redis.fromEnv()` (UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN) in production.
- Replace prior Dragonfly/redis-py integration and remove pooling and TCP assumptions.

## Consequences

- Simpler runtime (no cache container to run locally); fewer ops and secrets.
- Rate limiting via `@upstash/ratelimit` integrated with Next.js route handlers.
- Local development uses the same HTTP interface (or in-memory stubs for tests).

## Implementation Notes

- `@upstash/redis` provides `set`, `get`, `mget/mset`, `expire/ttl`, `incr/decr`.
- Rate limiting via `Ratelimit.slidingWindow()` from `@upstash/ratelimit`.
- Health via `ping()`. Errors propagate as service errors.
- docs/ and docker/ updated to remove Dragonfly.

## References

- [Upstash Redis Documentation](https://upstash.com/docs/redis)
- [Upstash Redis TypeScript SDK](https://github.com/upstash/upstash-redis)
- [Upstash Ratelimit](https://github.com/upstash/ratelimit)
- [Upstash Redis Vercel Integration](https://vercel.com/integrations/upstash-redis)

## Changelog

- 1.1.0 (2025-11-18) — Updated for TypeScript-only implementation; removed Python SDK references.
- 1.0.0 (2025-10-24) — Standardized metadata and formatting; added version and changelog.
