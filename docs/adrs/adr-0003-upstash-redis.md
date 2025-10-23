# ADR-0003: Use Upstash Redis (HTTP) for Caching

**Status:** Accepted
**Date:** 2025-10-22

## Context

- We deploy on Vercel (Next.js + Python Functions). A connectionless, HTTP-based cache fits serverless well.
- Upstash Redis provides REST/HTTP SDKs, Vercel marketplace integration, and per-request pricing.

## Decision

- Adopt Upstash Redis via the official Python async SDK (`upstash-redis`) for all backend caching.
- Use `Redis.from_env()` (UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN) in production.
- Replace prior Dragonfly/redis-py integration and remove pooling and TCP assumptions.

## Consequences

- Simpler runtime (no cache container to run locally); fewer ops and secrets.
- No classic Pub/Sub from Python HTTP client; for broadcasting, prefer Next.js (TS SDK) or QStash.
- Local development uses the same HTTP interface (or in-memory stubs for tests).

## Implementation Notes

- `CacheService` uses `upstash_redis.asyncio.Redis` with `set(ex=ttl)`, `get`, `mget/mset`, `expire/ttl`, `incr/decr`.
- Health via `PING`. Disabled simulation removed; errors propagate as `CoreServiceError`.
- docs/ and docker/ updated to remove Dragonfly.

## References

- [Upstash Redis Documentation](https://upstash.com/docs/redis)
- [Upstash Redis Python SDK](https://github.com/upstash/upstash-redis)
- [Upstash Redis Vercel Integration](https://vercel.com/integrations/upstash-redis)
