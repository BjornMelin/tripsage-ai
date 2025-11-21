# ADR-0048: QStash Retries and Idempotency for Webhooks/Tasks

**Version**: 1.0.0  
**Status**: Proposed  
**Date**: 2025-11-20  
**Category**: Reliability  
**Domain**: QStash / Webhooks  
**Related ADRs**: ADR-0032, ADR-0040, ADR-0041, ADR-0047  
**Related Specs**: -

## Context

- QStash is used for webhook notifications and background tasks (ADR-0041), but retry/idempotency strategy is not formalized.  
- We must avoid duplicate side effects (emails, DB writes) and provide deterministic replays.

## Decision

- Use QStash `deduplication-id` with deterministic keys: `${route}:${resourceId}:${eventName}:${timestampBucket}`.  
- Handlers must be idempotent: wrap side-effecting operations in a per-idempotency-key Upstash Redis lock (TTL 2 minutes) before executing.  
- Retry policy: max 6 attempts, exponential backoff starting at 10s; mark dead-letter to `qstash-dlq` Redis list with payload + attempt count.  
- Observability: emit OTEL span attributes `qstash.attempt`, `qstash.dedup_id`, `qstash.dlq` and structured log on final failure.  
- Security: validate QStash signature per official middleware; reject unverified requests before any side effects.  
- Storage writes must be transactional (Supabase RPC or single statement) to keep idempotency guarantees.

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

## References

- Upstash QStash retry docs  
- ADR-0041 (webhook notifications), ADR-0032 (rate limiting), ADR-0047 (runtime policy)
