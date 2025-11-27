# SPEC-0025: Trip Collaborator Notifications via QStash and Resend

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-13  
**Category**: Architecture/Platform  
**Domain**: Backend, Integrations  
**Related ADRs**: [ADR-0051](../../architecture/decisions/adr-0051-agent-router-workflows.md), [ADR-0052](../../architecture/decisions/adr-0052-agent-configuration-backend.md)  
**Related Specs**: [SPEC-0021](../active/0021-spec-supabase-webhooks-vercel-consolidation.md)

## Summary

Define the end-to-end pipeline for trip collaborator notifications triggered by
changes to `trip_collaborators` in Supabase. Use Supabase Database Webhooks to
POST events to Vercel, Upstash QStash for durable job delivery, and Resend for
emails, with an optional downstream collaborator webhook.

This spec extends [SPEC-0021](../active/0021-spec-supabase-webhooks-vercel-consolidation.md) (Supabase Database Webhooks to Vercel Route Handlers)
by specifying how `/api/hooks/trips` and `/api/jobs/notify-collaborators` work
together.

## Goals

- Ensure collaborator notifications are reliable and idempotent.
- Keep Supabase as the source of truth and entry point via Database Webhooks.
- Use managed queueing (QStash) instead of bespoke retry logic.
- Expose a clear operator runbook for configuration and troubleshooting.

## Non-goals

- Defining email content templates in detail.
- Implementing per-tenant or per-event routing policies.

## Architecture

### Event Flow

```mermaid
flowchart LR
  A[Supabase trigger on trip_collaborators] --> B[Supabase Database Webhook]
  B -->|HMAC signed JSON| C[/api/hooks/trips]
  C -->|publishJSON| Q[Upstash QStash]
  Q -->|HTTP POST + Upstash-Signature| D[/api/jobs/notify-collaborators]
  D --> E[Resend email]
  D --> F[Optional downstream webhook]
```

### /api/hooks/trips

- **Inputs**
  - Headers: `X-Signature-HMAC` (verified by shared `HMAC_SECRET`).
  - Body: `{ type, table, schema, record, old_record, occurred_at }`.

- **Behavior**
  - Validate HMAC and basic payload fields.
  - Ignore non-`trip_collaborators` tables (`{ ok: true, skipped: true }`).
  - Build `eventKey` from table, type, occurred_at, and record hash.
  - Guard with `tryReserveKey(eventKey, 300)` (Upstash Redis) to avoid duplicate work.
  - Optionally verify that `record.trip_id` points to an existing `trips` row.
  - If `QSTASH_TOKEN` is configured:
    - Publish `{ eventKey, payload }` to `/api/jobs/notify-collaborators` via QStash.
    - Return `{ ok: true, enqueued: true }`.
  - If `QSTASH_TOKEN` is not configured:
    - Use `after()` to run the notification adapter in the background.
    - Return `{ ok: true, enqueued: false, fallback: true }`.

### /api/jobs/notify-collaborators

- **Inputs**
  - Headers: `Upstash-Signature` (QStash signature).
  - Body: `{ eventKey: string; payload: WebhookPayload }` validated via Zod.

- **Behavior**
  - Verify QStash signature using `QSTASH_CURRENT_SIGNING_KEY` and
    `QSTASH_NEXT_SIGNING_KEY`.
  - Validate body with `notifyJobSchema`.
  - Guard with `tryReserveKey("notify:" + eventKey, 300)` to avoid double work
    on retries.
  - Call the notification adapter to perform side effects.
  - Return `{ ok: true, emailed, webhookPosted }`.

### Notification Adapter

- Looks up the collaborator’s email via Supabase Admin (`auth.admin.getUserById`).
- Sends a transactional email via Resend with a subject/body based on
  `INSERT`/`UPDATE`/`DELETE`.
- If `COLLAB_WEBHOOK_URL` is configured, POSTs `{ event, eventKey }` with a
  short timeout.
- Emits telemetry spans for email and webhook calls.

## Configuration

- Supabase DB
  - As defined in [SPEC-0021](../active/0021-spec-supabase-webhooks-vercel-consolidation.md) for webhooks and HMAC.

- Vercel env (server)
  - `HMAC_SECRET`
  - `QSTASH_TOKEN`
  - `QSTASH_CURRENT_SIGNING_KEY`
  - `QSTASH_NEXT_SIGNING_KEY`
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL`
  - `RESEND_FROM_NAME`
  - Optional `COLLAB_WEBHOOK_URL`

## Testing

- Unit tests
  - HMAC verification and early rejection in `/api/hooks/trips`.
  - Zod validation of job payloads in `/api/jobs/notify-collaborators`.
  - Idempotency behavior when duplicate `eventKey` events arrive.

- Integration tests
  - Simulate a `trip_collaborators` insert and verify that notification jobs are
    enqueued or executed.
  - Mock Resend and downstream webhook endpoints.

## Supersession

- This spec does **not** supersede [SPEC-0021](../active/0021-spec-supabase-webhooks-vercel-consolidation.md); it builds on the webhook
  foundation defined there.
