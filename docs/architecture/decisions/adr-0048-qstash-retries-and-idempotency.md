# ADR-0048: QStash Retries and Idempotency for Webhooks/Tasks

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-12-10
**Category**: Reliability
**Domain**: QStash / Webhooks
**Related ADRs**: ADR-0032, ADR-0040, ADR-0041, ADR-0047
**Related Specs**: SPEC-0021

## Context

- QStash is used for webhook notifications and background tasks (ADR-0041), but retry/idempotency strategy is not formalized.  
- We must avoid duplicate side effects (emails, DB writes) and provide deterministic replays.

## Decision

- Use QStash `deduplication-id` with deterministic keys: `${route}:${resourceId}:${eventName}:${timestampBucket}`.  
- Handlers must be idempotent: wrap side-effecting operations in a per-idempotency-key Upstash Redis lock (TTL 2 minutes) before executing.  
- Retry policy: max 6 attempts, exponential backoff starting at 10s; mark dead-letter to `qstash-dlq` Redis list with payload + attempt count.  
- Observability: emit OTEL span attributes `qstash.attempt`, `qstash.dedup_id`, `qstash.dlq` and structured log on final failure.  
- Security:
  - Validate QStash signature on the raw request body; reject unverified requests before any side effects.
  - Enforce a hard request body size limit before verification/parsing (return `413 Payload Too Large`).
  - Never log raw signature headers; if correlation is required, log a short hash prefix only.  
- Storage writes must be transactional (Supabase RPC or single statement) to keep idempotency guarantees.
- Degraded-mode policy: job endpoints are privileged; idempotency must fail closed when Redis is unavailable.

## Consequences

### Positive

- Reduced risk of duplicate notifications/bookings; deterministic replays.  
- DLQ and telemetry improve operability and incident handling.

### Negative

- Adds Redis lock + signature check overhead to each QStash call.  
- Implementation work required across all QStash handlers.

### Neutral

- Delivery semantics remain at-least-once; idempotency enforces safety rather than changing semantics.

## Alternatives Considered

### Rely on QStash defaults (no dedup/lock)

Rejected: higher risk of duplicate side effects and hard-to-debug retries.

### Per-handler custom strategies

Rejected: inconsistent policies and repeated logic across handlers.

## Implementation

The DLQ and retry handling is implemented in:

- `src/lib/qstash/config.ts` - Configuration constants (retry count, DLQ TTL, key prefixes)
- `src/lib/qstash/dlq.ts` - Dead Letter Queue operations (push, list, remove, count)
- `src/lib/qstash/receiver.ts` - Signature verification with bounded raw body reads
- `src/app/api/jobs/notify-collaborators/route.ts` - Worker with DLQ integration

Key implementation details:

- Max 6 total attempts (1 initial + 5 retries) with exponential backoff starting at 10s
- DLQ entries stored in Redis with 7-day TTL and max 1000 entries per job type
- Retry attempt tracked via `Upstash-Retried` header; DLQ push on final failure
- Telemetry spans emit the following attributes:
  - `qstash.attempt` - Current attempt number (1-based)
  - `qstash.max_retries` - Maximum configured retries
  - `qstash.final_attempt` - Boolean indicating if this is the last retry
  - `qstash.dlq` - Boolean indicating entry was pushed to DLQ
  - `qstash.dlq_entry_id` - Unique ID of the DLQ entry (if pushed)

## References

- Upstash QStash – Retry: <https://upstash.com/docs/qstash/features/retry>
- Upstash QStash – Verify signatures (raw body required): <https://upstash.com/docs/qstash/howto/signature>
- ADR-0041 (webhook notifications), ADR-0032 (rate limiting), ADR-0047 (runtime policy)
- SPEC-0021 (Supabase Webhooks Consolidation)
