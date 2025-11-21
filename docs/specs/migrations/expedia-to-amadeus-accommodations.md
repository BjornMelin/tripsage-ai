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
  - Identified risks: Places geocoding/enrichment lacked retries/telemetry; Amadeus booking payload used placeholder card; persistence still writes to `eps_booking_id`.
  - Actions taken: added retry/backoff + telemetry spans for Places geocode/details; normalized geocode cache keys. Payment alignment and persistence column rename remain open.
- Code Review (zen.codereview):
  - Issues: hard-coded Amadeus card payload; empty-hotel search path; geocode failures surfacing as location_not_found; legacy `eps_booking_id` field.
  - Fixes applied: removed hard-coded payment card (bookings now pay-at-property/agency hold), short-circuit when no hotels, geocode now throws on provider errors with telemetry, maintained note to migrate bookings persistence to provider-neutral field.
- Security (zen.secaudit):
  - Findings: spoofable `x-user-id` header; client-controlled booking amount/currency.
  - Fixes applied: tools now derive user from Supabase auth; booking charges now derive amount/currency from cached checkAvailability price (client values ignored).
  - Remaining: persist provider-neutral booking identifiers in database; consider additional auth hardening for non-auth search flows.

## Phase 3 – Migrate Search & Details

- [ ] Remove `@schemas/expedia` usage from `service.ts`.

- [ ] Implement Amadeus-based search with Upstash caching and rate limiting.

- [ ] Implement details enrichment with Google Places Place Details for hotels.

- [ ] Update unit tests for search and details.

## Phase 4 – Migrate Availability & Booking

- [ ] Update `checkAvailability` to use provider adapter and Amadeus.

- [ ] Generalize `runBookingOrchestrator` to provider-agnostic `ProviderBookingResult`.

- [ ] Update Supabase booking persistence mapping.

- [ ] Ensure Stripe PaymentIntents flow remains unchanged.

## Phase 5 – AI Tools & Agent

- [ ] Update `ai/tools/server/accommodations.ts` descriptions and remove Rapid-specific helpers.

- [ ] Ensure all tools remain schema-compatible with `@schemas/accommodations`.

- [ ] Validate `runAccommodationAgent` still runs with updated tools.

## Phase 6 – UI & UX

- [ ] Wire `ModernHotelResults` into hotel search pages.

- [ ] Confirm `AccommodationCard` displays Amadeus prices and Google Places ratings.

- [ ] Confirm shadcn/ui components behave correctly for loading and errors.

## Phase 7 – Remove Expedia

- [ ] Remove `src/domain/expedia/*` and `src/domain/schemas/expedia.ts`.

- [ ] Remove Expedia env vars from `.env.example`.

- [ ] Run TS compile; resolve any lingering imports.

- [ ] Mark old Expedia ADR/specs as `Superseded` pointing to ADR-0050.

## Phase 8 – Final QA

- [ ] Run full unit/integration test suite.

- [ ] Manual test:

  - Search for a city.

  - Inspect hotel list and cards.

  - Run test booking in Amadeus sandbox.

  - Verify booking in Supabase and Stripe dashboard.
