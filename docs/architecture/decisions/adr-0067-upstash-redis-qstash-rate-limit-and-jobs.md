# ADR-0067: Upstash Redis + QStash for caching, rate limits, and background jobs

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-05  
**Category**: backend + ops  
**Domain**: caching, jobs, abuse protection

## Context

TripSage needs:

- short TTL caching (search results, RAG query results)
- distributed rate limiting
- background jobs (indexing, async enrichment, webhook fanout)

## Decision

- Use Upstash Redis for:
  - ephemeral caching (TTL, namespaced keys)
  - rate limiting via `@upstash/ratelimit`
- Use Upstash QStash for:
  - reliable background job dispatch
  - retries, scheduled tasks, webhook delivery to Next.js route handlers
- Require idempotency for every job handler:
  - idempotency key required
  - “already processed” short-circuit stored in Redis or DB

## Consequences

- Minimal infrastructure, serverless-friendly.
- Built-in retry behavior and signatures for jobs.
- Requires disciplined handler verification and idempotency.

## References

```text
Upstash RateLimit docs: https://upstash.com/docs/redis/sdks/ratelimit-ts/overview
RateLimit getting started: https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted
Upstash QStash local development: https://upstash.com/docs/qstash/howto/local-development
QStash retry behavior: https://upstash.com/docs/qstash/features/retries
NPM @upstash/ratelimit: https://www.npmjs.com/package/@upstash/ratelimit
NPM @upstash/redis: https://www.npmjs.com/package/@upstash/redis
NPM @upstash/qstash: https://www.npmjs.com/package/@upstash/qstash
```
