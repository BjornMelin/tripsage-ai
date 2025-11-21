# Migration Checklist: Expedia Rapid → Amadeus + Google Places + Stripe

**Version**: 1.0  
**Status**: Accepted  
**Date**: 2025-11-21  
**Category**: Architecture  
**Domain**: Travel Supply Integrations  
**Related ADRs**: ADR-0050  
**Related Specs**: SPEC-0027  

Status: Draft → Completed when all boxes are checked  

Related: `adr-0050-amadeus-google-places-stripe-hybrid.md`, `0027-spec-accommodations-amadeus-google-stripe.md`

## Phase 0 – Safety & Branching

- [x] Create feature branch: `feat/amadeus-accommodations`.

- [x] Enable CI for new branch.

- [ ] Snapshot current tests for `accommodations` domain, tools, and UI.

## Phase 1 – Introduce Amadeus (no behavior change yet)

- [x] Add `amadeus` dependency to `frontend/package.json`.

- [x] Create `src/domain/amadeus/client.ts`, `schemas.ts`, `mappers.ts`.
- Notes:
  - Implemented lazy singleton client with env validation.
  - Added base schemas for hotel, offer, booking plus mapping helpers.

- [x] Write unit tests for Amadeus client and mappers with fixtures.

- [ ] Commit as "Amadeus scaffolding only (not wired)".

## Phase 2 – Swap Provider in Container

- [x] Ensure `AmadeusProviderAdapter` implements `AccommodationProviderAdapter`.

- [x] Update `src/domain/accommodations/container.ts` to use `new AmadeusProviderAdapter()`.
- Notes:
  - Provider types rewritten to be provider-agnostic.
  - Container now builds Amadeus adapter with Upstash rate limiter defaults.

- [x] Run tests; fix any type errors in service and booking orchestrator.
  - Tests: `pnpm test:unit --project=unit` (frontend) – passes after adding Amadeus client/mappers/service/orchestrator specs.
  - Addressed: updated provider-agnostic booking orchestrator, fixed TypeScript errors, and ensured service uses Amadeus adapter.

## Global Reviews, Security Notes, and Cross-Cutting Changes

- Architecture (zen.analyze):
  - Identified risks: Places geocoding/enrichment lacked retries/telemetry; Amadeus booking payload used placeholder card; persistence still wrote to `eps_booking_id`.
  - Actions taken: added retry/backoff + telemetry spans for Places geocode/details; normalized geocode cache keys; persisted bookings now use `provider_booking_id` via Supabase migration 20251121090000. Payment payload validation with Amadeus still open.
  - New: Added OTEL spans for details/availability/booking flows and enforced rate limiting on availability/booking paths.
- Code Review (zen.codereview):
  - Issues: hard-coded Amadeus card payload; empty-hotel search path; geocode failures surfacing as location_not_found; legacy `eps_booking_id` field.
  - Fixes applied: removed hard-coded payment card (bookings now pay-at-property/agency hold), short-circuit when no hotels, geocode now throws on provider errors with telemetry, added provider-neutral booking persistence.
- Security (zen.secaudit):
  - Findings: spoofable `x-user-id` header; client-controlled booking amount/currency.
  - Fixes applied: tools now derive user from Supabase auth; booking charges now derive amount/currency from cached checkAvailability price (client values ignored); removed server-key exposure for Places photos by switching to browser-safe key in UI.
  - Remaining: rotate server key in ops runbook; consider additional auth hardening for non-auth search flows.

## Phase 3 – Migrate Search & Details

- [x] Remove `@schemas/expedia` usage from `service.ts`.

- [x] Implement Amadeus-based search with Upstash caching and rate limiting.

- [x] Implement details enrichment with Google Places Place Details for hotels.

- [x] Update unit tests for search and details.

## Phase 4 – Migrate Availability & Booking

- [x] Update `checkAvailability` to use provider adapter and Amadeus.

- [x] Generalize `runBookingOrchestrator` to provider-agnostic `ProviderBookingResult`.

- [x] Update Supabase booking persistence mapping.

- [x] Ensure Stripe PaymentIntents flow remains unchanged. (Pending: align Amadeus booking payload with Stripe payments/virtual card.)
  - Payment now reuses cached availability price, ignoring client-provided amounts; provider payload embeds Stripe PaymentIntent reference and amount/currency and is covered by adapter unit test. Remaining risk: production validation against Amadeus `/v1/booking/hotel-bookings` response requirements.
  - Added orchestrator unit tests to ensure refunds occur on provider failure and provider_booking_id is persisted.

## Phase 5 – AI Tools & Agent

- [x] Update `ai/tools/server/accommodations.ts` descriptions and remove Rapid-specific helpers.

- [x] Ensure all tools remain schema-compatible with `@schemas/accommodations`.

- [x] Validate `runAccommodationAgent` still runs with updated tools.

## Phase 6 – UI & UX

- [x] Wire `ModernHotelResults` into hotel search pages.
  - Implemented server action `searchHotelsAction` to call accommodations service and feed `ModernHotelResults` with normalized data (Amadeus pricing + Places ratings/photos). Nights calculation guarded.
- [x] Confirm `AccommodationCard` displays Amadeus prices and Google Places ratings.
  - Card now surfaces Places ratings/photos when present and defaults safely when enrichment missing.
- [x] Confirm shadcn/ui components behave correctly for loading and errors.
  - Verified skeleton states and error boundaries; client uses browser-safe photo key instead of server key to avoid leakage.

## Phase 7 – Remove Expedia

- [x] Remove `src/domain/expedia/*` and `src/domain/schemas/expedia.ts`.
  - Deleted Expedia domain and schema modules; container now instantiates Amadeus adapter only.
- [x] Remove Expedia env vars from `.env.example`.
  - Verified `.env.example` contains only Amadeus/Places/Stripe variables; no EPS keys remain.

- [ ] Run TS compile; resolve any lingering imports.

- [x] Mark old Expedia ADR/specs as `Superseded` pointing to ADR-0050.
  - Updated ADR decision log with ADR-0050 accepted; ADR-0043/0049 listed as superseded and headers already reflect status.

## Phase 8 – Final QA

- [ ] Run full unit/integration test suite.

- [ ] Manual test:

  - Search for a city.

  - Inspect hotel list and cards.

  - Run test booking in Amadeus sandbox.

  - Verify booking in Supabase and Stripe dashboard.
