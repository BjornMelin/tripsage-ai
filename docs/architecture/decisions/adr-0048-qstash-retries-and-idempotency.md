# ADR-0048: QStash Retries and Idempotency for Webhooks/Tasks

**Version**: 1.1.0
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

- Use QStash `Upstash-Deduplication-Id` with deterministic keys derived from the business operation (e.g. `<job>:<resourceId>`). Use time bucketing only when intentional fan-out is required.  
- Handlers must be idempotent: wrap side-effecting operations in a per-business-key Upstash Redis reservation (default TTL 300s) before executing.  
- Retry policy: max 6 attempts (1 initial + 5 retries), with an explicit retry delay expression via `Upstash-Retry-Delay` (configured by `src/lib/qstash/client.ts`).  
- Dead Letter Queue (DLQ): Use QStash's native DLQ support. For non-retryable errors, return HTTP `489` and set `Upstash-NonRetryable-Error: true` so QStash forwards the message to the configured DLQ.  
- Observability: emit OTEL span attributes `qstash.attempt`, `qstash.dedup_id`, `qstash.dlq` and structured log on final failure.  
- Security:
  - Validate QStash signature on the raw request body; reject unverified requests before any side effects.
  - Enforce a hard request body size limit before verification/parsing (reject before JSON parsing). For QStash-delivered jobs, treat oversized payloads as non-retryable (`489` + header) to avoid retry loops.
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

Canonical retry/idempotency and verification are implemented in:

- `src/lib/qstash/config.ts` - Configuration constants (retry count, header names)
- `src/lib/qstash/client.ts` - Publishing helper enforcing retry policy and dedup headers
- `src/lib/qstash/receiver.ts` - Signature verification with bounded raw body reads + delivery idempotency via `Upstash-Message-Id`
- `src/app/api/jobs/**/route.ts` - Job workers using the shared QStash receiver utilities

Key implementation details:

- Max 6 total attempts (1 initial + 5 retries)
- Retry delay expression: `10000 * pow(2, retried)` (milliseconds; `retried` starts at 0 for the first retry)
- Retry attempt tracked via `Upstash-Retried` header; DLQ forwarding uses `489` + `Upstash-NonRetryable-Error: true`
- Delivery idempotency uses `Upstash-Message-Id` with an in-flight lock (default 240s) and a processed marker (default 24h). Longer-running jobs may set `lockTtlSeconds` explicitly.
- Telemetry spans emit the following attributes:
  - `qstash.attempt` - Current attempt number (1-based)
  - `qstash.max_retries` - Maximum configured retries
  - `qstash.final_attempt` - Boolean indicating if this is the last retry
  - `qstash.dlq` - Boolean indicating the response was non-retryable (eligible for DLQ forwarding)

## References

- Upstash QStash – Retry: <https://upstash.com/docs/qstash/features/retry>
- Upstash QStash – Verify signatures (raw body required): <https://upstash.com/docs/qstash/howto/signature>
- ADR-0041 (webhook notifications), ADR-0032 (rate limiting), ADR-0047 (runtime policy)
- SPEC-0021 (Supabase Webhooks Consolidation)
