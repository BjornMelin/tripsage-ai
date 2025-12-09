# ADR-0049: Expedia Rapid Integration Research

**Version**: 1.0  
**Status**: Superseded  
**Date**: 2025-11-19  
**Category**: Architecture  
**Domain**: Travel Supply Integrations  
**Superseded By**: ADR-0050  

## Architecture Snapshot (2025-11-19)

- **Provider adapter:** `src/domain/accommodations/providers/expedia-adapter.ts` adds retry + jitter backoff and an in-memory circuit breaker (default 4 failures, 30s cool-down). All Rapid calls flow through here and normalize errors to domain codes.
- **Service layer:** `src/domain/accommodations/service.ts` owns search, details, availability, and booking orchestration wiring (RAG property resolution, cache-aside via Upstash, rate limiting via Upstash Ratelimit, Supabase persistence).
- **Booking orchestrator:** `src/domain/accommodations/booking-orchestrator.ts` sequences approval → payment → provider booking → Supabase persist, with refund on provider failure and operational alert on persistence failure.
- **AI tool surface unchanged:** `src/ai/tools/server/accommodations.ts` delegates to the service/orchestrator; cache/rate-limit moved out of tool guardrails.
- **Payment:** `src/lib/payments/booking-payment.ts` now solely handles Stripe payment intent creation/refund (no provider calls).

Telemetry: all service/provider/orchestrator calls are wrapped with `withTelemetrySpan`; PII keys are redacted; operational alerts emitted on persistence/refund failures.

## Internal References

- `docs/prompts/tools/accommodation-details-tool-migration.md` (line 263) lists Expedia as an alternative accommodation detail provider beside Airbnb MCP and Booking.com; no dedicated ADR/SPEC currently defines an Expedia implementation.
- AGENTS.md + ADR-0020/0024/0026/0031/0036 and SPEC-001/010/015 still govern cross-cutting concerns (telemetry, cache/layout, BYOK, AI SDK v6), so a future Expedia ADR must inherit those constraints.
- Current implementation homes: schemas consolidated in `src/domain/schemas/expedia.ts`; Rapid client under `src/domain/expedia/client.ts`; consumers: `src/ai/tools/server/accommodations.ts` and `src/lib/payments/booking-payment.ts`.

## External References

- Expedia Group Rapid developer hub: <https://developers.expediagroup.com/rapid> (entry point for Lodging Content, Shopping, Booking APIs, and SDKs).
- Rapid setup + launch requirements: <https://developers.expediagroup.com/rapid/setup> (covers partner onboarding, API key/secret issuance, sandbox vs production flow, B2B/B2C compliance checklists, Vrbo requirements, and optimization tips).
- Rapid Content API reference: <https://developers.expediagroup.com/rapid/lodging/content> (property metadata, descriptions, amenities, sustainability, pagination, guest reviews).
- Rapid Shopping API reference: <https://developers.expediagroup.com/rapid/lodging/shopping> (live availability, rate plans, payment types, test request catalog, filtering/options).
- Rapid Booking API reference: <https://developers.expediagroup.com/rapid/lodging/booking> (reservation workflow, guest/PII payload schema, confirmation/cancellation endpoints, error taxonomy).

## Authentication & Configuration

**Rapid Authentication:** Rapid uses SHA-512 signature authentication (not Basic auth or HMAC). The signature is computed as:

- `SHA512(apiKey + secret + timestamp)` encoded as hexadecimal
- Authorization header format: `EAN APIKey={apiKey},Signature={sha512Hash},timestamp={timestamp}`
- Timestamp must be UNIX seconds (same value used in signature calculation)
- Reference: <https://developers.expediagroup.com/rapid/resources/reference/signature-authentication>

**Base URLs:**

- Production: `https://api.ean.com/v3` (default when `EPS_BASE_URL` is unset)
- Sandbox: `https://test.ean.com/v3` (set explicitly via `EPS_BASE_URL` for testing)

**Environment Variables:**

- `EPS_API_KEY` (required): Rapid API key from EPS Portal
- `EPS_API_SECRET` (required): Shared secret from EPS Portal
- `EPS_BASE_URL` (optional): Override base URL (defaults to production)
- `EPS_DEFAULT_CUSTOMER_IP` (optional): Default customer IP for requests (defaults to "0.0.0.0")
- `EPS_DEFAULT_USER_AGENT` (optional): Default user agent (defaults to "TripSage/1.0 (+<https://tripsage.ai>)")

## Open Questions / To-Do

1. ~~Confirm Rapid authentication mode~~ → **RESOLVED**: SHA-512 signature authentication implemented
2. Determine caching strategy for Content API (Supabase tables vs Upstash). Identify data freshness SLAs.
3. Map payment + booking flow: Stripe charge first vs Rapid booking hold; align with ADR-0031 payment guardrails.
4. Capture rate-limit quotas + recommended retries for Shopping/Booking to size Upstash limits.
5. ~~Draft ADR describing Expedia integration scope~~ → **RESOLVED**: ADR-0043 created
