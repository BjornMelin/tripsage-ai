# ADR-0067: Upstash Redis + QStash for caching, rate limits, and background jobs

**Version**: 1.1.0
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

- QStash, Redis, and Ratelimit remain the canonical production stack for this
  release. Do not introduce `@upstash/workflow`, `@vercel/queue`, or another
  durable execution layer until production telemetry proves it removes more
  custom orchestration than it adds.
- Use Upstash Redis for:
  - ephemeral caching (TTL, namespaced keys)
  - rate limiting via `@upstash/ratelimit`
- Use Upstash QStash for:
  - reliable background job dispatch
  - retries, scheduled tasks, webhook delivery to Next.js route handlers
- Require idempotency for every job handler:
  - idempotency key required
  - “already processed” short-circuit stored in Redis or DB
- Build all `@upstash/ratelimit` instances through `src/lib/ratelimit/upstash.ts`.
  Surfaces keep their own degraded-mode policy:
  - API routes: `withApiGuards({ degradedMode })`, defaulting high-cost and
    security-sensitive routes to fail closed.
  - Webhooks and jobs: fail closed by default.
  - AI tools: fail open on unavailable limiter infrastructure but emit telemetry.
- Publish all QStash jobs through `src/lib/qstash/client.ts` with:
  - deterministic `deduplicationId`
  - canonical `label` from `QSTASH_JOB_LABELS`
  - explicit retry count and retry delay expression
  - optional flow control and failure callback where the job owner needs them

## Decision Matrix

| Option | Solution leverage (35%) | App value (30%) | Maintenance (25%) | Adaptability (10%) | Weighted |
| --- | ---: | ---: | ---: | ---: | ---: |
| Keep Upstash Redis + QStash + Ratelimit and harden contracts | 9.4 | 9.1 | 9.2 | 8.8 | 9.2 |
| Adopt Upstash Workflow for this release | 8.4 | 7.6 | 6.8 | 8.5 | 7.7 |
| Adopt Vercel Queues/Workflow now | 8.0 | 7.4 | 6.5 | 8.8 | 7.5 |
| Custom Redis queues | 4.5 | 5.0 | 3.0 | 4.0 | 4.2 |

The hardened-current-stack option wins because it preserves the serverless
provider fit while deleting duplicate rate-limit construction and tightening
publish contracts. Workflow products stay viable future options, but they are
not a net simplification for the current job graph.

## Consequences

- Minimal infrastructure, serverless-friendly.
- Built-in retry behavior and signatures for jobs.
- Requires disciplined implementation of handler verification and idempotency.
- Production webhook/job paths cannot silently downgrade critical background
  work to in-process best-effort execution.

## References

```text
Upstash RateLimit docs: https://upstash.com/docs/redis/sdks/ratelimit-ts/overview
RateLimit getting started: https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted
Upstash QStash local development: https://upstash.com/docs/qstash/howto/local-development
QStash retry behavior: https://upstash.com/docs/qstash/features/retry
QStash deduplication: https://upstash.com/docs/qstash/features/deduplication
QStash flow control: https://upstash.com/docs/qstash/features/flowcontrol
QStash DLQ operations: https://upstash.com/docs/qstash/api-reference/dlq/bulk-retry-dlq-messages
NPM @upstash/ratelimit: https://www.npmjs.com/package/@upstash/ratelimit
NPM @upstash/redis: https://www.npmjs.com/package/@upstash/redis
NPM @upstash/qstash: https://www.npmjs.com/package/@upstash/qstash
```
