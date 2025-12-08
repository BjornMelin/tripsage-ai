# ADR-0050: Replace Expedia Rapid with Amadeus + Google Places + Stripe

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-20  
**Category**: Architecture  
**Domain**: Travel Supply Integrations  
**Related ADRs**: ADR-0020, ADR-0024, ADR-0026, ADR-0031, ADR-0036, ADR-0039, ADR-0042  
**Related Specs**: SPEC-0027, SPEC-001, SPEC-0010, SPEC-0015  
**Supersedes**: ADR-0043, ADR-0049

- Any Expedia Rapid–focused ADRs under `docs/architecture/decisions/` (e.g. `adr-00N-expedia-rapid-hotel-provider.md`)  
- Any Expedia Rapid–focused specs under `docs/specs/` (e.g. `expedia-rapid-accommodations.md`)

## 1. Supersession Instructions

1. Locate existing Expedia Rapid ADRs and specs:

   - `docs/architecture/decisions/adr-00N-expedia-rapid-*.md`
   - `docs/specs/expedia-rapid-*.md`
   - Any other Expedia Rapid–specific docs referenced from the README or `docs/`

2. At the top of each Expedia-specific ADR/spec:
   - Change `Status:` to `Superseded`.
   - Add a line:  
     `Superseded by: ADR-00X-amadeus-google-places-stripe-hybrid.md`

3. Update navigation / index docs (if present) to:
   - Remove Expedia as “current provider”.
   - Point “Accommodations provider” to ADR-00X and the new spec:
     `docs/specs/0027-spec-accommodations-amadeus-google-stripe.md`.

## 2. Context

**Existing implementation:**

- **Core domain:** `frontend/src/domain/accommodations/*`  
  - **Service orchestrator and caching:**  
    `frontend/src/domain/accommodations/service.ts`  
  - **Provider container:**  
    `frontend/src/domain/accommodations/container.ts` (hard-wired to `ExpediaProviderAdapter`)  
  - **Provider adapter:**  
    `frontend/src/domain/accommodations/providers/expedia-adapter.ts` (wrapping `@domain/expedia/client`)  
  - **Booking orchestration with Stripe:**  
    `frontend/src/domain/accommodations/booking-orchestrator.ts`  

- **Expedia-specific domain & schemas:**
  - **Rapid client, types, utils:**  
    `frontend/src/domain/expedia/*`  
  - **Zod schemas for Rapid:**  
    `frontend/src/domain/schemas/expedia.ts` (imported as `@schemas/expedia`)  

- **Accommodations schemas** (provider-agnostic surface but Expedia-shaped):  
  `frontend/src/domain/schemas/accommodations.ts` (and sometimes aliased as `@schemas/accommodations`)  

**AI tools:**

- **Search, details, checkAvailability, book:**
  `frontend/src/ai/tools/server/accommodations.ts` (search, details, checkAvailability, book; all described as “via Expedia Partner Solutions” and using `normalizePhoneForRapid`, `splitGuestName`, `extractTokenFromHref`)  

**Agent orchestration:**  
  `frontend/src/lib/agents/accommodation-agent.ts` (AI SDK v6 `streamText`, tools: `searchAccommodations`, `getAccommodationDetails`, `checkAvailability`, `bookAccommodation`)  

**UI:**

- **Search pages:**
    `frontend/src/app/(dashboard)/trips/[tripId]/stay/page.tsx` and `frontend/src/app/(marketing)/stays/page.tsx` (hero, forms, but results placeholder commented out)  
- **Cards and lists:**
    `frontend/src/components/features/search/cards/accommodation-card.tsx` and related hotel UI.  

**Infrastructure:**

- **Upstash Redis client / caching:** `frontend/src/lib/redis.ts`, `frontend/src/lib/cache/upstash.ts`  
- **Upstash Ratelimit:** `@upstash/ratelimit` used in `accommodations/container.ts` and AI tools.  
- **Supabase booking persistence:** in `runBookingOrchestrator` via `bookings` table.  
- **Stripe payment orchestration:** `frontend/src/lib/payments/booking-payment.ts` (called from `bookAccommodation`).  

**Problems with Expedia Rapid:**

- Partner-only, commercial API: you must apply, be approved, then obtain credentials; sandbox access is gated behind partner approval.:contentReference[oaicite:15]{index=15}  
- Approval requires business justification, certification, and integration with their portal; not ideal for an indie / self-service app.:contentReference[oaicite:16]{index=16}  

**Requirements:**

- Remove the dependency on Expedia Rapid across code and docs.
- Introduce a hybrid architecture:
  - Amadeus Self-Service APIs for hotel offers and bookings.:contentReference[oaicite:17]{index=17}  
  - Google Places API (“Google Hotels layer”) for discovery, photos, ratings, and rich context.:contentReference[oaicite:18]{index=18}  
  - Existing Stripe PaymentIntents for payments.:contentReference[oaicite:19]{index=19}  

- Preserve:
  - AI tool surface (`searchAccommodations`, `getAccommodationDetails`, `checkAvailability`, `bookAccommodation`).
  - Accommodations agent interface (`runAccommodationAgent`).
  - Booking persistence semantics and Supabase schema.
  - Guardrails: Upstash cache, rate limiting, telemetry, approvals.

## 3. Options & Decision Framework

### 3.1 Provider choice for accommodations

**Options:**

1. Hybrid: Amadeus (offers + bookings) + Google Places (discovery + enrichment).
2. Amadeus only.
3. Google Places only (no transactional provider).
4. Continue with Expedia.

**Scoring rubric (1–10):**

- Solution Leverage (SL) – 35%  
- Application Value (AV) – 30%  
- Maintenance & Cognitive Load (MCL) – 25%  
- Architectural Adaptability (AA) – 10%

| Option | SL | AV | MCL | AA | Weighted Total |
|--------|----|----|-----|----|----------------|
| Amadeus + Google Places (Hybrid) | 9 | 9 | 8 | 8 | 8.65 |
| Amadeus only | 8 | 8 | 8 | 8 | 8.00 |
| Google Places only | 6 | 5 | 8 | 7 | 6.30 |
| Keep Expedia Rapid | 7 | 7 | 4 | 6 | 6.15 |

**Rationale:**

- Hybrid scores highest:  
  - Amadeus covers hotel offers, availability, and bookings via self-service APIs with free monthly quota and straightforward pricing.:contentReference[oaicite:20]{index=20}  
  - Google Places provides high-quality POI, photos, and ratings but no direct booking/pricing, so combining both delivers the best UX.:contentReference[oaicite:21]{index=21}  
  - Expedia remains partner-gated and slows iteration.:contentReference[oaicite:22]{index=22}  

**Decision:** Adopt hybrid Amadeus + Google Places for accommodations, fully deprecating Expedia Rapid.

### 3.2 Amadeus client implementation

**Options:**

1. Official Amadeus Node SDK (`amadeus` on npm).:contentReference[oaicite:23]{index=23}  
2. Custom HTTP client (`fetch` + Zod), modeled after existing Expedia client.

| Option    | SL | AV | MCL | AA | Weighted Total |
|-----------|----|----|-----|----|----------------|
| Node SDK  |  9 |  8 |   9 |  7 | 8.50           |
| Custom    |  7 |  8 |   6 |  8 | 7.15           |

**Rationale:**

- Node SDK takes care of auth, endpoints, and retries; reduces custom HTTP plumbing and keeps us aligned with Amadeus documentation and examples.:contentReference[oaicite:24]{index=24}  
- We can still wrap SDK calls in domain adapters for telemetry and error normalization, preserving existing patterns in `ExpediaProviderAdapter`.  

**Decision:** Use official Amadeus Node SDK behind an `AmadeusProviderAdapter` wrapper.

## 4. Decision

- Replace Expedia Rapid with:
  - Amadeus Self-Service Hotel APIs for:
    - Hotel list / offers search (`/v1/reference-data/locations/hotels` and `/v3/shopping/hotel-offers`).:contentReference[oaicite:26]{index=26}  
    - Hotel booking (`/v1/booking/hotel-bookings`).:contentReference[oaicite:27]{index=27}  
  - Google Places API (New) for:
    - Place autocomplete, text search, details, photos and ratings for hotels (`type=lodging`).:contentReference[oaicite:28]{index=28}  
  - Stripe PaymentIntents for charge/authorization, as already used in `booking-payment.ts`.:contentReference[oaicite:29]{index=29}  

- Maintain the existing public surface:
  - AI tools in `frontend/src/ai/tools/server/accommodations.ts`.
  - Schemas in `frontend/src/domain/schemas/accommodations.ts`.
  - Agent API in `frontend/src/lib/agents/accommodation-agent.ts`.

- Adapt the domain so that:
  - `AccommodationsService` talks to a new `AmadeusProviderAdapter` implementing `AccommodationProviderAdapter`.  
  - Booking orchestration (`runBookingOrchestrator`) is generalized to provider-agnostic result payloads; Expedia-specific fields move into the adapter layer.  

- Remove all runtime dependencies on:
  - `frontend/src/domain/expedia/*`
  - `@schemas/expedia`
  - Any `Expedia*` env vars.

## 5. Consequences

**Positive:**

- Immediate unblocking: Amadeus self-service can be used without partner contracts, with a free quota and pay-as-you-go pricing beyond that.:contentReference[oaicite:32]{index=32}  
- Better UX: Google Places data (photos, ratings, reviews) + Amadeus real-time offers and booking yields richer cards and more compelling hotel selection flows.:contentReference[oaicite:33]{index=33}  
- Cleaner layering: provider-specific types and quirks remain in adapters; schemas and agents stay provider-agnostic.

**Negative/Risks:**

- Dual-provider quotas and keys must be managed (Amadeus + Google Places).
- Booking semantics differ slightly between Expedia and Amadeus (e.g., booking identifiers, cancellation policies); requires mapping to our normalized `AccommodationBookingResult`.:contentReference[oaicite:34]{index=34}  

**Mitigations:**

- Centralize provider selection in `accommodations/container.ts`.
- Add Quota/usage telemetry fields (e.g. `amadeus.api.calls`, `places.api.calls`) using existing OpenTelemetry helpers.  

## 6. Implementation Summary

**Implementation is described in detail in:**

- `docs/specs/archive/0027-spec-accommodations-amadeus-google-stripe.md`

**That spec defines:**

- File-level changes (add/modify/remove).
- AI tool wiring.
- UI composition using shadcn/ui and Next.js app router best practices.:contentReference[oaicite:36]{index=36}  
- Tests and telemetry coverage.

## 7. Post-acceptance Updates (2025-11-24)

- **Provider timeouts:** Amadeus adapter now enforces an 8s per-attempt timeout with retry/backoff; timeouts surface as `provider_timeout` (HTTP 408) for telemetry and retry classification.
- **Deterministic session propagation:** Service-to-provider context now normalizes `sessionId` from the caller or `userId`, preventing regenerated session identifiers and keeping availability/booking caches correlated.
- **Outstanding review items closed:** The above changes resolve the remaining action items tracked in the 2025-11-19 accommodations review; ADR-0043 remains superseded by this ADR.
