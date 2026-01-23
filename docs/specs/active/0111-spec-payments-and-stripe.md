# SPEC-0111: Payments and Stripe (server-only + webhooks)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-19

## Goals

- Centralize Stripe client creation and payment primitives (PaymentIntents, refunds, retrieval).
- Provide a hardened webhook endpoint for Stripe event delivery.
- Keep webhook processing safe-by-default:
  - signature verification on raw request bytes
  - bounded body reads
  - idempotency and rate limiting
  - telemetry without leaking secrets

## Non-goals

- A complete payments product surface (pricing plans, invoices, subscriptions).
- Client-side Stripe secret handling (all Stripe secrets are server-only).

## Environment variables

Required for server-side payment flows:

- `STRIPE_SECRET_KEY` (`sk_test_...` / `sk_live_...`)
- `STRIPE_WEBHOOK_SECRET` (`whsec_...`) for `/api/hooks/stripe` verification

Optional for browser checkout flows:

- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` (`pk_test_...` / `pk_live_...`)

Validation is centralized in `src/domain/schemas/env.ts` and accessed via `src/lib/env/server.ts`.

## Canonical Stripe client

Stripe must be initialized in a single server-only module:

- `src/lib/payments/stripe-client.ts`
  - `getStripeClient()` returns a memoized `Stripe` client
  - payment primitives:
    - `createPaymentIntent()`
    - `refundPayment()`
    - `getPaymentIntent()`

Policy:

- Never import Stripe secret keys into client components.
- Prefer server-side actions/handlers for Stripe operations.

## Stripe webhook route (Route Handler)

Endpoint:

- `POST /api/hooks/stripe` (`src/app/api/hooks/stripe/route.ts`)

Implementation:

- `src/lib/payments/stripe-webhook.ts` exports `createStripeWebhookHandler()`

### Processing pipeline (mandatory order)

1) Rate limit (fail-closed; Stripe retries)
2) Read raw body bytes with a hard cap (reject oversize payloads)
3) Verify signature via `stripe.webhooks.constructEvent(rawBody, header, secret)`
4) Enforce idempotency using Redis reservation key `stripe:<event.id>` (24h TTL)
5) Minimal event handling + acknowledgement

### Event handling strategy

- The webhook contract is “verify + acknowledge”.
- Unknown `event.type` values must be acknowledged safely to keep the endpoint forward-compatible.
- Stripe `v2.*` event notification surfaces are treated as known-safe unknowns (telemetry records `stripe.v2_event`).

### Telemetry

- Span: `webhook.stripe` (`withTelemetrySpan`)
- Low-cardinality attributes:
  - `stripe.event_id`
  - `stripe.event_type`
  - `stripe.api_version`
  - `stripe.livemode`
- Never log:
  - raw request body
  - signature header value
  - webhook secret

## Testing

Required tests:

- Webhook signature verification and failure modes:
  - `src/app/api/hooks/stripe/__tests__/route.test.ts` (Node/API project)
- Stripe client memoization and env validation:
  - `src/lib/payments/__tests__/stripe-client.test.ts`

Test strategy:

- Use Stripe’s `generateTestHeaderString` to simulate signature headers.
- Avoid network; use deterministic fixtures and `vi.stubEnv`/`vi.unstubAllEnvs`.

## Local verification (agent-browser)

This change was validated via a local dev server + UI flows:

1) Start dev server: `pnpm dev`
2) Create a trip from the dashboard UI to confirm the app is healthy (baseline)
3) Exercise `/api/hooks/stripe` with valid/invalid signatures using the tests above

For Trips create-flow schema correctness validation details, see SPEC-0102 post-acceptance updates (2026-01-19).

## References

```text
ADR-0070: [Stripe Webhook Verification + Idempotency](../../architecture/decisions/adr-0070-stripe-webhook-verification-and-idempotency.md)
Stripe Node release v20.2.0: https://github.com/stripe/stripe-node/releases/tag/v20.2.0
Stripe webhooks: https://stripe.com/docs/webhooks
```
