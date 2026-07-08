# ADR-0067: Upstash Redis + QStash for caching, rate limits, and background jobs

**Version**: 1.2.0
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
  - API routes: `ROUTE_RATE_LIMITS` owns per-key `degradedMode`; missing
    `degradedMode` means intentional fail-open, and `withApiGuards({ degradedMode })`
    remains an exceptional route-local override.
  - Webhooks and jobs: fail closed by default.
  - AI tools: fail open on unavailable limiter infrastructure but emit telemetry.
- Publish all QStash jobs through `src/lib/qstash/client.ts` with:
  - deterministic `deduplicationId`
  - canonical `label` from `QSTASH_JOB_LABELS`
  - explicit retry count and retry delay expression
  - optional flow control and failure callback where the job owner needs them
- Keep the expensive attachment ingest and RAG index path bounded before any
  workflow SDK rewrite:
  - `vercel.json` caps API route execution at 60 seconds.
  - RAG QStash delivery timeout is 55 seconds.
  - RAG embedding abort timeout is 50 seconds so workers can finish cleanup
    before QStash gives up on delivery.
  - RAG QStash request bodies are capped at 512 KiB, below the documented 1 MiB
    default QStash message-size limit.
  - Attachment downloads are capped at 10 MiB.
  - Extracted text/RAG content is capped at 250,000 characters.
  - RAG jobs accept at most 100 documents and 1,200 embedding chunks per batch.
  - RAG chunk overlap must be smaller than chunk size.
- Record redacted job telemetry for duration, estimated chunk count, document
  count, embedding calls/tokens/warnings, DB upsert count/rows, provider failure
  class, retry outcome, and QStash payload bytes. Never record raw attachment
  filenames, storage paths, extracted text, document content, embedding values,
  provider payloads, or user/trip/chat identifiers.
- Treat attachment-to-RAG QStash message bodies as a raw user-content processor
  boundary. They carry extracted document content and attachment metadata for
  asynchronous indexing, and retryable failures can leave those bodies in
  QStash retry/DLQ storage. The publisher requests provider-side request-body
  log redaction for this path. Operator access to QStash payloads/DLQs is
  sensitive production data access; telemetry must remain aggregate and redacted.

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

## Workflow pilot thresholds

Do not add `@upstash/workflow`, Vercel Workflow, or Vercel Queues for the
attachment/RAG path until telemetry from the bounded QStash implementation shows
one or more of:

- sustained P95 job duration above 45 seconds or recurring 60-second Vercel
  function timeouts;
- repeated QStash delivery timeouts, retries, or DLQ entries after the payload
  and chunk budgets are enforced;
- multi-step checkpoint/state code that a workflow SDK would delete more than it
  adds;
- embedding or retry volume that remains cost-excessive after tightening
  content, chunk, and batch limits.

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
QStash message size and timeout: https://upstash.com/docs/qstash
Vercel Functions duration: https://vercel.com/docs/functions/configuring-functions/duration
Vercel AI SDK embedMany: https://ai-sdk.dev/docs/reference/ai-sdk-core/embed-many
QStash DLQ operations: https://upstash.com/docs/qstash/api-reference/dlq/bulk-retry-dlq-messages
NPM @upstash/ratelimit: https://www.npmjs.com/package/@upstash/ratelimit
NPM @upstash/redis: https://www.npmjs.com/package/@upstash/redis
NPM @upstash/qstash: https://www.npmjs.com/package/@upstash/qstash
```
