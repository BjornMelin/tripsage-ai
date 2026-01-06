# SPEC-0107: Jobs and webhooks (Supabase + QStash)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Reliable background processing for:
  - attachment ingestion
  - RAG indexing
  - enrichment tasks (places, routes)
- Secure inbound webhooks from:
  - Supabase
  - QStash

## Requirements

- Every job handler must:
  - verify signature
  - enforce idempotency
  - emit structured logs
- Job payloads validated with Zod.

## Handler contract

Webhooks (Supabase/QStash triggers):

- Implement webhook routes via `createWebhookHandler` (`src/lib/webhooks/handler.ts`), which provides:
  - rate limiting
  - body size validation
  - signature verification
  - optional table filtering
  - idempotency via Redis keys (default TTL 300s)

Jobs (QStash workers):

- Implement worker routes as `src/app/api/jobs/<job>/route.ts`.
- Verify QStash signatures with `getQstashReceiver()` + `verifyQstashRequest()` (`src/lib/qstash/receiver.ts`).
- Parse JSON and validate with Zod schemas (typically under `@schemas/webhooks`).
- Enforce idempotency with `tryReserveKey()` (`src/lib/idempotency/redis`) using a stable key like `<job>:<eventKey>` and a short TTL (e.g., 300s).
- On repeated failures, push to DLQ on the final retry attempt (`src/lib/qstash/dlq.ts`) per ADR-0048.

## Structured logging

- Use `withTelemetrySpan()` for each webhook/job route and record key attributes:
  - `event.key` (dedup key), `table`, `op`
  - `qstash.attempt`, `qstash.max_retries`, and whether it was a final attempt
- Prefer server log events with consistent keys (e.g., `job_type`, `event_key`) rather than free-form strings.

## Error handling and retries

- Validation and signature failures should return non-2xx responses with stable error codes.
- QStash retries are handled by QStash; job handlers must be safe to run multiple times (idempotent) and should fall back to DLQ on final failure.

## References

```text
Upstash QStash retries: https://upstash.com/docs/qstash/features/retries
Upstash QStash local dev: https://upstash.com/docs/qstash/howto/local-development
Supabase webhooks: https://supabase.com/docs/guides/database/webhooks
```
