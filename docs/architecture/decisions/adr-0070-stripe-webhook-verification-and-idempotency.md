# ADR-0070: Stripe webhook verification and idempotency (Next.js Route Handlers)

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-19  
**Category**: Security / Reliability  
**Domain**: Payments / Webhooks  
**Related ADRs**: ADR-0032, ADR-0046, ADR-0047, ADR-0048, ADR-0050, ADR-0062, ADR-0063  
**Related Specs**: SPEC-0107, SPEC-0111

## Context

- TripSage accepts third-party webhooks (Stripe, Supabase, QStash) and must treat them as untrusted inputs.
- Stripe retries aggressively on non-2xx responses and expects signature verification on the **raw request body**.
- Next.js Route Handlers run within the App Router runtime constraints (Cache Components enabled) and must avoid module-scope request state.
- Webhook handlers must be safe by default:
  - signature verification before parsing
  - bounded request body reads
  - idempotency to prevent duplicate side effects
  - rate limiting to control abuse and accidental retry storms
  - telemetry for operability without logging secrets

## Decision

We implement Stripe webhook handling as a first-class Next.js Route Handler with standardized guardrails:

1) **Canonical Stripe server client**
   - Stripe initialization is centralized in `src/lib/payments/stripe-client.ts` (`"server-only"`, memoized per-process).
   - Secrets are accessed via the canonical env boundary (`getServerEnvVar()`), validated by `src/domain/schemas/env.ts`.

2) **Canonical Stripe webhook handler**
   - A shared handler factory `createStripeWebhookHandler()` is implemented in `src/lib/payments/stripe-webhook.ts` and mounted at `POST /api/hooks/stripe` (`src/app/api/hooks/stripe/route.ts`).
   - The handler enforces, in-order:
     - fail-closed rate limiting via `src/lib/webhooks/rate-limit.ts`
     - bounded raw body reads (`readRequestBodyBytesWithLimit`) with a hard cap
     - signature verification using `stripe.webhooks.constructEvent(rawBody, signature, webhookSecret)`
     - event-level idempotency using Upstash Redis reservation keys with a 24h TTL (`stripe:<event.id>`)
     - minimal event handling (telemetry + acknowledgement); unknown event types are accepted safely

3) **Unknown event types are safe**
   - The webhook contract is “verify + acknowledge”; downstream handlers may add per-event-type behavior, but unknown types (including Stripe `v2.*` event notification surfaces) must not break the endpoint.

4) **Telemetry**
   - Each webhook request is wrapped in `withTelemetrySpan("webhook.stripe", …)`.
   - Telemetry records low-cardinality attributes (`stripe.event_id`, `stripe.event_type`, `stripe.livemode`, `stripe.api_version`) and avoids logging signature headers or raw bodies.

## Consequences

### Positive

- Stripe webhooks are hardened against replay and duplicate deliveries via Redis idempotency keys.
- Webhook processing is bounded and safe (raw body cap, early rejection paths).
- Stripe retries become an operational tool rather than a source of duplicate side effects.
- The webhook shape matches the existing webhook/job posture (ADR-0048, SPEC-0107).

### Negative

- Requires Upstash Redis to be available for strict idempotency; webhook routes fail closed when idempotency cannot be enforced.
- Adds minor runtime overhead (rate limiting + idempotency reservation) per webhook call.

### Neutral

- Current event handling is intentionally minimal (acknowledge after verification); business behavior is expected to grow as payment flows expand.

## Alternatives Considered

### Treat Stripe webhooks as “best effort” (no idempotency)

Rejected: Stripe retries and at-least-once delivery semantics make duplicates likely; duplicate side effects are unacceptable for payments.

### Parse JSON before verifying the signature

Rejected: signature verification must be performed on the raw bytes to be robust and to match Stripe’s signing model.

### Implement webhooks in Edge runtime

Rejected: payment/webhook code is privileged and must integrate with server-only secrets and Upstash/Supabase patterns; Node runtime is the canonical default (ADR-0047).

## References

- Stripe Node v20.2.0 release: <https://github.com/stripe/stripe-node/releases/tag/v20.2.0>
- Stripe webhooks (signatures): <https://stripe.com/docs/webhooks>
- Upstash idempotency patterns: `src/lib/idempotency/redis.ts` and ADR-0048
