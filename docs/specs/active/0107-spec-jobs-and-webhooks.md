# SPEC-0107: Jobs and webhooks (Supabase + QStash)

**Version**: 1.1.0  
**Status**: Final  
**Date**: 2026-01-19

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

- Implement worker routes as `src/app/api/jobs/<job>/route.ts` with a pure `_handler.ts` implementation.
- Verify QStash signatures with `getQstashReceiver()` + `verifyQstashRequest()` (`src/lib/qstash/receiver.ts`) **using the raw request body** before parsing JSON.
- Parse JSON and validate with Zod schemas (typically under `@schemas/webhooks`).
- Enforce idempotency in two layers:
  1) **Delivery idempotency** via `Upstash-Message-Id` header (stable across retries). Store a processed marker in Redis with TTL (default: 24h). If a message is in-flight, return a retryable non-2xx (e.g., 409) to let QStash retry. If already processed, return 2xx quickly.
  2) **Business idempotency** via `tryReserveKey()` (`src/lib/idempotency/redis`) using a stable key like `<job>:<resourceId>` and a short TTL (e.g., 300s) to prevent double side effects when re-publishing or fan-out occurs.

## Structured logging

- Use `withTelemetrySpan()` for each webhook/job route and record key attributes:
  - `event.key` (dedup key), `table`, `op`
  - `qstash.message_id`, `qstash.attempt` (derived from `Upstash-Retried`)
- Prefer server log events with consistent keys (e.g., `job_type`, `event_key`) rather than free-form strings.

## Error handling and retries

- QStash retries are handled by QStash:
  - **Any non-2xx** response triggers retries (until retry limit is reached).
  - For **non-retryable** errors (invalid payloads, permanently missing references), return:
    - HTTP `489`
    - Header `Upstash-NonRetryable-Error: true`
    - This disables retries and forwards the message to the configured DLQ.

- When publishing jobs, set an explicit retry delay expression (via `Upstash-Retry-Delay`) so failures reach DLQ promptly instead of waiting hours/days on the QStash default backoff.

## Deduplication (publishing)

- Prefer explicit deduplication keys when publishing jobs:
  - `Upstash-Deduplication-Id` (stable key derived from the business operation).
- Optionally enable content-based deduplication for idempotent bodies:
  - `Upstash-Content-Based-Deduplication: true`

## Dead Letter Queue (DLQ)

- Configure a QStash DLQ for your topic/endpoint to retain failed messages after retries.
- Operators can **republish** or **delete** DLQ messages from the Upstash Console.

## Third-party webhooks (Stripe)

Stripe webhooks follow the same guardrail posture (bounded raw body reads, signature verification, idempotency, rate limiting, telemetry), but are documented separately as payments infrastructure:

- SPEC-0111: [Payments and Stripe](0111-spec-payments-and-stripe.md#spec-0111-payments-and-stripe-server-only--webhooks)
- ADR-0070: [Stripe Webhook Verification + Idempotency](../../architecture/decisions/adr-0070-stripe-webhook-verification-and-idempotency.md)

## References

```text
Upstash QStash retry: https://upstash.com/docs/qstash/features/retry
Upstash QStash receiving: https://upstash.com/docs/qstash/howto/receiving
Upstash QStash local dev: https://upstash.com/docs/qstash/howto/local-development
Supabase webhooks: https://supabase.com/docs/guides/database/webhooks
```
