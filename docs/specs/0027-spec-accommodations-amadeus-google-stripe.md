# TripSage Accommodations Spec: Amadeus + Google Places + Stripe

**Version**: 1.0  
**Status**: Final  
**Date**: 2025-11-21  
**Category**: Architecture  
**Domain**: Travel Supply Integrations  
**Related ADRs**: ADR-0050  

> IMPORTANT: This spec **supersedes all Expedia Rapid–specific docs and ADRs**.  
> Any instructions, types, or tools that mention EPS Rapid MUST be treated as
> historical only and replaced by the architecture described here.

---

## 0. Scope and Goals

This document is the **implementation guide** for migrating TripSage’s
accommodations features from **Expedia Rapid** to a hybrid of:

- **Amadeus Self-Service APIs** (hotels search and booking).:contentReference[oaicite:37]{index=37}  
- **Google Places API (New)** for hotel discovery, photos, and ratings.:contentReference[oaicite:38]{index=38}  
- **Stripe** for card payments via PaymentIntents.:contentReference[oaicite:39]{index=39}  

This spec is intended to be fed directly to an AI coding agent. All tasks are
broken into phases with checklists and concrete file paths.

---

## 1. High-Level Architecture

### 1.1 Existing pipeline (to be replaced)

1. AI tools (`@ai/tools/server/accommodations.ts`) call:
   - `AccommodationsService` via `getAccommodationsService()`.  
2. `AccommodationsService`:
   - Uses `ExpediaProviderAdapter` to call `ExpediaClient` (`@domain/expedia/client`).  
   - Maps Rapid-specific responses into:
     - `ACCOMMODATION_SEARCH_OUTPUT_SCHEMA`
     - `ACCOMMODATION_DETAILS_OUTPUT_SCHEMA`
     - `ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA`
     - `ACCOMMODATION_BOOKING_OUTPUT_SCHEMA`.  
   - Uses Upstash Redis for caching search and Ratelimit for per-user caps.  
3. `runBookingOrchestrator`:
   - Calls Stripe (`processBookingPayment` / `refundBookingPayment`) and `provider.createBooking`, then persists the booking to Supabase.  
4. UI uses:
   - `useAccommodationSearch` hook and `accommodation-card.tsx` to display results.  

### 1.2 Target pipeline

1. AI tools (same names) invoke the same `AccommodationsService`, but:
   - The provider is now `AmadeusProviderAdapter`.
   - The details path enriches listings with Google Places hotel data.

2. `AmadeusProviderAdapter` (new):

   - Wraps the **Amadeus Node SDK**.:contentReference[oaicite:46]{index=46}  
   - Implements `AccommodationProviderAdapter` with methods:
     - `search(params, ctx)`
     - `getDetails(params, ctx)`
     - `checkAvailability(params, ctx)`
     - `createBooking(params, ctx)`

3. `AccommodationsService`:

   - Uses Amadeus endpoints:
     - Geocode → `reference-data/locations/hotels/by-geocode` for hotels near a lat/lng.:contentReference[oaicite:47]{index=47}  
     - Offers → `/v3/shopping/hotel-offers` for real-time prices and availability.:contentReference[oaicite:48]{index=48}  
   - When enriching details:
     - Calls Google Places API (New) Place Details & Photos with `type=lodging`.:contentReference[oaicite:49]{index=49}  

4. Booking flow:

   - AI `bookAccommodation` tool:
     - Ensures user/approval context.
     - Triggers Stripe `PaymentIntent` creation via `processBookingPayment`.:contentReference[oaicite:50]{index=50}  
   - `runBookingOrchestrator`:
     - Calls `AmadeusProviderAdapter.createBooking(...)`.
     - Persists booking to Supabase (same `bookings` table).
     - Uses Amadeus `id/confirmationId` fields for booking reference.:contentReference[oaicite:51]{index=51}  

5. UI:

   - Hotel search pages in `app/(dashboard)/trips/[tripId]/stay/page.tsx` and
     `app/(marketing)/stays/page.tsx` are wired to `useAccommodationSearch` and
     render results using new shadcn/ui components:
     `ModernHotelResults` + `AccommodationCard`.:contentReference[oaicite:52]{index=52}  

---

## 2. Environment Configuration

### 2.1 Add Amadeus environment variables

Files:

- `frontend/.env.example`
- `frontend/.env.local` (local only, not committed)

Add:

```bash
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
AMADEUS_ENV=test # or "production"
```

Refer to the official [Amadeus "Get started with Self-Service APIs"](https://developers.amadeus.com/get-started) page for
account creation and key management.

Checklist:

- [ ] Create Amadeus developer account and self-service app.
- [ ] Copy `API Key` → `AMADEUS_CLIENT_ID`.
- [ ] Copy `API Secret` → `AMADEUS_CLIENT_SECRET`.
- [ ] Set `AMADEUS_ENV` to `"test"` for development.

### 2.2 Confirm Google Places configuration

The project already uses Google Places via routes under `frontend/src/app/api/places/*`.

Ensure:

- [ ] `GOOGLE_MAPS_API_KEY` / `GOOGLE_PLACES_API_KEY` is present in `.env.local`.
- [ ] API key has access to:

  - [Places API (New)](https://developers.google.com/maps/documentation/places/web-service) (for Place Details, Text Search, Photos).

### 2.3 Confirm Stripe configuration

Stripe is already configured for bookings via `booking-payment.ts`.

Checklist:

- [ ] Ensure `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in `.env.local`.([Stripe Docs](https://stripe.com/docs/payments/payment-intents))
- [ ] Confirm PaymentIntents are used in “automatic” or “manual” mode consistent with booking flows.

---

## 3. File Map (Add / Modify / Remove)

### 3.1 New files

- `frontend/src/domain/amadeus/`

  - `client.ts` – thin wrapper around `amadeus` Node SDK.
  - `schemas.ts` – Zod schemas for Amadeus hotel list/offers/booking responses.
  - `mappers.ts` – mapping from Amadeus entities → `Accommodation*` schemas.

- `frontend/src/domain/accommodations/providers/amadeus-adapter.ts`

  - Implements `AccommodationProviderAdapter` using Amadeus client + mapping.

- `frontend/docs/specs/migrations/expedia-to-amadeus-accommodations.md`

  - Migration checklist (see next file definition).

### 3.2 Modified files

- `frontend/src/domain/accommodations/container.ts`
- `frontend/src/domain/accommodations/service.ts`
- `frontend/src/domain/accommodations/booking-orchestrator.ts`
- `frontend/src/domain/accommodations/providers/types.ts`
- `frontend/src/domain/schemas/accommodations.ts`
- `frontend/src/ai/tools/server/accommodations.ts`
- `frontend/src/lib/agents/accommodation-agent.ts`
- `frontend/src/components/features/search/accommodation-card.tsx`
- `frontend/src/components/features/search/modern-hotel-results.tsx`
- `frontend/src/app/(dashboard)/trips/[tripId]/stay/page.tsx`
- `frontend/src/app/(marketing)/stays/page.tsx`

### 3.3 Removed files

After migration is fully complete and tests pass, remove:

- `frontend/src/domain/expedia/*`
- `frontend/src/domain/schemas/expedia.ts`
- Any Expedia-specific environment variables from `.env.example` and runtime use.

---

## 4. Domain: Amadeus Integration

### 4.1 Amadeus client

File: `frontend/src/domain/amadeus/client.ts`

Responsibilities:

- Instantiate [Amadeus Node SDK](https://developers.amadeus.com/sdks-and-libraries) (`amadeus` package).
- Provide methods:

  - `listHotelsByGeocode({ latitude, longitude, radius })`
  - `searchHotelOffers({ hotelIds, checkInDate, checkOutDate, adults, currency })`
  - `bookHotel(bookingPayload)`
- Perform minimal response handling; schema validation occurs in `schemas.ts`.

Implementation notes for AI agent:

- [ ] Add `amadeus` to `frontend/package.json` dependencies.

- [ ] Create a singleton Amadeus client using env vars:

  ```ts
  import Amadeus from "amadeus";

  let amadeus: Amadeus | undefined;

  export function getAmadeusClient() {
    if (!amadeus) {
      amadeus = new Amadeus({
        clientId: process.env.AMADEUS_CLIENT_ID!,
        clientSecret: process.env.AMADEUS_CLIENT_SECRET!,
      });
    }
    return amadeus;
  }
  ```

- [ ] Implement wrappers (for example):

  ```ts
  export async function listHotelsByGeocode(params: {
    latitude: number;
    longitude: number;
    radius?: number;
  }) {
    const client = getAmadeusClient();
    return client.referenceData.locations.hotels.byGeocode.get({
      latitude: params.latitude,
      longitude: params.longitude,
      radius: params.radius ?? 5,
      radiusUnit: "KM",
    });
  }
  ```

  Align parameter names with [official docs](https://developers.google.com/maps/documentation/places/web-service).

### 4.2 Amadeus schemas

File: `frontend/src/domain/amadeus/schemas.ts`

Responsibilities:

- Define Zod schemas for Amadeus responses we care about:

  - Hotel list items (id, name, geo, address).([Google for Developers](https://developers.google.com/maps/documentation/places/web-service))
  - Hotel offers (price, currency, check-in/out, room description, policies).([Amadeus IT Group SA](https://developers.amadeus.com/self-service))
  - Booking confirmation (id, confirmation codes, guest info).([Supabase](https://supabase.com/docs))

Tasks:

- [ ] Define `amadeusHotelSchema`, `amadeusOfferSchema`, `amadeusBookingSchema` using Zod.
- [ ] Export TS types:

  - `AmadeusHotel`, `AmadeusHotelOffer`, `AmadeusHotelBooking`.

### 4.3 Mapping to existing accommodation schemas

File: `frontend/src/domain/amadeus/mappers.ts`

Responsibilities:

- Map `AmadeusHotel` + `AmadeusHotelOffer` → existing `Accommodation` schema in `frontend/src/domain/schemas/search.ts`.

Considerations:

- `Accommodation` fields:

  - `id` → use `hotel.hotelId` (or composite `hotelId:offerId` if needed).
  - `name` → `hotel.name`.
  - `location` → from Amadeus address / geo.
  - `images[]` → will be primarily from Google Places, not Amadeus.
  - `price` / `pricePerNight` → derived from `offer.price.total` and nights count.([Amadeus IT Group SA](https://developers.amadeus.com/self-service))
  - `provider` → `"amadeus"`.

Tasks:

- [ ] Implement `mapAmadeusHotelToAccommodationCard(hotel, offers, placesData?)`.
- [ ] Ensure `AccommodationSearchResult` remains valid per `ACCOMMODATION_SEARCH_OUTPUT_SCHEMA`.

---

## 5. Accommodations Service Changes

File: `frontend/src/domain/accommodations/service.ts`

### 5.1 Generalize from Expedia-specific types

Current state:

- Tightly coupled to `EpsCheckAvailabilityRequest`, `EpsCreateBookingRequest`, `RapidAvailabilityResponse`, etc., imported from `@schemas/expedia`.

Target:

- Provider-agnostic service that depends only on:

  - `AccommodationProviderAdapter` interface.
  - `AccommodationsServiceDeps`.
  - `ACCOMMODATION_*` schemas.

Tasks:

- [ ] Remove direct imports from `@schemas/expedia` in `service.ts`.
- [ ] Introduce provider-agnostic DTOs for:

  - `ProviderAvailabilityResult` (`bookingToken`, `expiresAt`, price, propertyId, rateId).
  - `ProviderBookingPayload` (opaque `unknown` mapped inside adapter).
- [ ] Let `AccommodationsService` call:

  - `this.deps.provider.search(params, ctx)`
  - `this.deps.provider.getDetails(params, ctx)`
  - `this.deps.provider.checkAvailability(params, ctx)`
  - `this.deps.provider.createBooking(providerPayload, ctx)`

### 5.2 Search flow

Tasks:

- [ ] Replace use of Rapid search with Amadeus:

  - Input: `AccommodationSearchParams` has `location`, `lat`, `lng`, `checkIn`, `checkOut`, `guests`.
  - Use geocode-based search:

    - If lat/lng present → Amadeus by-geocode.
    - Else, resolve via [Google Places Text Search](https://developers.google.com/maps/documentation/places/web-service) to lat/lng (`/api/places/search`).
- [ ] Combine:

  - `AmadeusHotel` list.
  - For detail enrichment, later calls to Google Places via Place Details API using either:

    - `hotel.name + hotel.address` and Text Search, or
    - `hotel.geo` (lat/lng) and `type=lodging`.([Google for Developers](https://developers.google.com/maps/documentation/places/web-service))
- [ ] Use Upstash caching for search results under the same `CACHE_NAMESPACE`:

  - Key: `service:accom:search:${canonicalizeParamsForCache(params)}`.

### 5.3 Availability and booking

Tasks:

- [ ] Update `checkAvailability` implementation to call `this.deps.provider.checkAvailability(...)` and map provider-agnostic result into `ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA`.
- [ ] Update `book` implementation:

  - Remove `buildExpediaBookingPayload`.
  - Introduce `buildProviderBookingPayload` that delegates to `this.deps.provider.buildBookingPayload(params)`.
  - Keep `runBookingOrchestrator` API the same but with generic provider result.

---

## 6. Provider Adapter: Amadeus

File: `frontend/src/domain/accommodations/providers/amadeus-adapter.ts`

### 6.1 Interface

File: `frontend/src/domain/accommodations/providers/types.ts`

Tasks:

- [ ] Ensure `AccommodationProviderAdapter` has the following signature (simplified):

  ```ts
  export interface AccommodationProviderAdapter {
    readonly name: "amadeus";

    search(
      params: AccommodationSearchParams,
      ctx?: ProviderContext
    ): Promise<ProviderResult<ProviderSearchResult>>;

    getDetails(
      params: AccommodationDetailsParams,
      ctx?: ProviderContext
    ): Promise<ProviderResult<ProviderDetailsResult>>;

    checkAvailability(
      params: AccommodationCheckAvailabilityParams,
      ctx?: ProviderContext
    ): Promise<ProviderResult<ProviderAvailabilityResult>>;

    createBooking(
      payload: ProviderBookingPayload,
      ctx?: ProviderContext
    ): Promise<ProviderResult<ProviderBookingResult>>;

    buildBookingPayload(
      params: AccommodationBookingRequest
    ): ProviderBookingPayload;
  }
  ```

- [ ] `ProviderResult<T>` remains the same: `{ ok: true; value: T } | { ok: false; error: ProviderError }`.

### 6.2 Implementation details

Tasks:

- [ ] Implement `AmadeusProviderAdapter` that:

  - Wraps [Amadeus SDK](https://developers.amadeus.com/sdks-and-libraries) calls for search and booking. ([AI SDK v6](https://v6.ai-sdk.dev/docs/introduction))
  - Uses existing retry and circuit-breaker utilities (`retryWithBackoff` + `CircuitBreaker`) as seen in `ExpediaProviderAdapter`.
  - Produces normalized `ProviderError` instances for:

    - HTTP 401/403 → `unauthorized`.
    - HTTP 404 → `not_found`.
    - HTTP 429 → `rate_limited`.
    - 5xx → `provider_failed`.

- [ ] Keep telemetry:

  - Wrap each operation in `withTelemetrySpan("provider.amadeus.operation")` with attributes:

    - `provider.name = "amadeus"`.
    - `provider.operation`.
    - `provider.circuit_state`.

---

## 7. Booking Orchestrator Adjustments

File: `frontend/src/domain/accommodations/booking-orchestrator.ts`

Current state:

- Types are tied to `EpsCreateBookingRequest` and `EpsCreateBookingResponse`.
- Confirmation/external IDs read from Expedia-specific fields.

Tasks:

- [ ] Replace `EpsCreateBookingResponse` generic with `ProviderBookingResult`.

- [ ] Move Expedia-specific extraction logic into `ExpediaProviderAdapter` (and later delete that adapter).

- [ ] Update `runBookingOrchestrator`:

  - Do not inspect provider result for Expedia-specific fields.
  - Expect `providerResult.value` to be normalized:

    ```ts
    type ProviderBookingResult = {
      itineraryId?: string;
      confirmationNumber?: string;
      providerBookingId?: string;
    };
    ```

- [ ] Map:

  - `itineraryId` → `epsBookingId` (for backward DB compatibility).
  - `confirmationNumber` → `reference` and message text.
  - Keep `bookingId`, `stripePaymentIntentId`, `guest*`, `tripId` unchanged.

- [ ] Make `PersistPayload` provider-agnostic:

  ```ts
  type PersistPayload = {
    bookingId: string;
    providerBookingId?: string;
    stripePaymentIntentId: string;
    confirmationNumber?: string;
    command: BookingCommand;
  };
  ```

- [ ] Update Supabase insert in `AccommodationsService.book`:

  - Continue writing to `bookings` with existing snake_case columns (`eps_booking_id`, etc.) for now, but treat it logically as `provider_booking_id`.

---

## 8. AI Tools and Agents

### 8.1 Tools

File: `frontend/src/ai/tools/server/accommodations.ts`

Tasks:

- [ ] Update tool descriptions:

  - Replace “Expedia Partner Solutions” / “Expedia Rapid” with “Amadeus Self-Service APIs for hotels” and “Google Places API for enrichment”.
- [ ] Remove `normalizePhoneForRapid` and `extractTokenFromHref` from this file:

  - If still needed, they should live inside provider adapters.
- [ ] Keep input/output schemas unchanged (`ACCOMMODATION_*`).
- [ ] Ensure `searchAccommodations`, `getAccommodationDetails`,
  `checkAvailability`, `bookAccommodation` still call the same service methods.

### 8.2 Agent

File: `frontend/src/lib/agents/accommodation-agent.ts`

Tasks:

- [ ] Keep tool list unchanged:

  - `ACCOMMODATION_TOOLS = { searchAccommodations, getAccommodationDetails, checkAvailability, bookAccommodation }`
- [ ] Update internal instructions/prompts:

  - Avoid hard-coding the word “Expedia”.
  - Clarify that the agent is using “real-time hotel offers and bookings via Amadeus and enriches with Google Places hotel data”.

No changes to the AI SDK v6 usage are required; TripSage already uses
`streamText` and tools as recommended by [Vercel AI SDK v6 Tools](https://v6.ai-sdk.dev/docs/foundations/tools).

---

## 9. UI: shadcn/ui + Next.js

The project already uses shadcn/ui, Tailwind, and Lucide icons for rich UI
components.([shadcn/ui](https://ui.shadcn.com))

### 9.1 Results rendering

Files:

- `frontend/src/components/features/search/accommodation-card.tsx`
- `frontend/src/components/features/search/modern-hotel-results.tsx`
- `frontend/src/app/(dashboard)/trips/[tripId]/stay/page.tsx`
- `frontend/src/app/(marketing)/stays/page.tsx`

Tasks:

- [ ] Ensure `AccommodationCard` reads `provider = "amadeus"` and renders:

  - Price from `accommodation.price.total` and `currency`.
  - Rating and reviews from Google Places data included in `AccommodationDetailsResult`.
- [ ] Implement `ModernHotelResults` that:

  - Uses shadcn `Card`, `Skeleton`, `Badge`, `Tabs` for filtering.
  - Shows map integration via Google Maps JS SDK or @vis.gl/react-google-maps (optional).
- [ ] Wire `ModernHotelResults` back into the pages where results are currently commented out.

### 9.2 Next.js 16 compatibility

Next.js 16 continues the app router paradigm, React Server Components, and
improved caching/turbopack capabilities.([Next.js](https://nextjs.org/docs))

Guidelines:

- [ ] Ensure all Amadeus and Stripe code runs server-side only:

  - Use `"use server"` or `import "server-only"` where needed.([Amadeus IT Group SA](https://developers.amadeus.com/self-service))
- [ ] Keep external API calls inside:

  - Route handlers.
  - Server actions.
  - AI tool modules that import `server-only`.

---

## 10. Testing Plan

### 10.1 Unit tests

Add/Update:

- `frontend/src/domain/amadeus/__tests__/client.test.ts`
- `frontend/src/domain/amadeus/__tests__/mappers.test.ts`
- `frontend/src/domain/accommodations/__tests__/service-amadeus.test.ts`
- `frontend/src/domain/accommodations/__tests__/booking-orchestrator.test.ts`
- `frontend/src/ai/tools/server/__tests__/accommodations-tools.test.ts`

Scope:

- [ ] Amadeus client wrappers:

  - Mock `amadeus` SDK; verify correct params and error mapping.
- [ ] Mappers:

  - Given sample Amadeus responses, ensure `Accommodation` object shapes match schemas.
- [ ] Service search:

  - Caches results with Upstash.
  - Respects rate limiting when `rateLimiter` is configured.
- [ ] Booking orchestrator:

  - Refunds on provider error.
  - Persists booking with normalized provider IDs.

### 10.2 Integration tests

Using Vitest + MSW:

- [ ] Mock Amadeus HTTP endpoints (or SDK calls) to simulate:

  - Normal responses.
  - 401, 404, 429, 500 error conditions.
- [ ] Mock Google Places endpoints under `/api/places/*`.
- [ ] End-to-end tests for:

  - `searchAccommodations` tool.
  - `getAccommodationDetails` combining Amadeus & Google Places.
  - Full booking flow driven by `bookAccommodation`.

---

## 11. Phase Plan & Checklists

### Phase 1 – Setup & Skeleton

- [ ] Add Amadeus env vars and `amadeus` dependency.
- [ ] Create `frontend/src/domain/amadeus/client.ts`.
- [ ] Create `frontend/src/domain/amadeus/schemas.ts`.
- [ ] Create `frontend/src/domain/amadeus/mappers.ts`.

### Phase 2 – Provider Adapter & Container

- [ ] Implement `AccommodationProviderAdapter` updates in `providers/types.ts`.
- [ ] Implement `AmadeusProviderAdapter` in `providers/amadeus-adapter.ts`.
- [ ] Update `accommodations/container.ts` to construct `AmadeusProviderAdapter` instead of `ExpediaProviderAdapter`.

### Phase 3 – Service & Orchestrator

- [ ] Remove direct `@schemas/expedia` imports from `service.ts`.
- [ ] Implement new search/availability/book flows using provider adapter.
- [ ] Update `booking-orchestrator.ts` to be provider-agnostic.

### Phase 4 – AI Tools & Agent

- [ ] Update `ai/tools/server/accommodations.ts` descriptions and any Rapid-specific helpers.
- [ ] Confirm `searchAccommodationsInputSchema` export is unchanged.
- [ ] Confirm `runAccommodationAgent` still composes tools correctly.

### Phase 5 – UI & UX

- [ ] Re-enable `ModernHotelResults` and ensure it renders new data.
- [ ] Update `AccommodationCard` to use Google Places ratings/photos when available.
- [ ] Validate responsive behavior and A11y (labels, alt tags).

### Phase 6 – Decommission Expedia

- [ ] Remove `domain/expedia` folder and references.
- [ ] Remove `@schemas/expedia.ts` usage.
- [ ] Strip Expedia env vars from `.env.example` and code.
- [ ] Mark old Expedia ADRs/specs as `Superseded`.

### Phase 7 – Regression & Load

- [ ] Run full test suite (unit + integration).
- [ ] Add light load testing of hotel search (e.g., 100 consecutive searches).
- [ ] Verify Amadeus and Google quotas are not exceeded (Amadeus free tier; Google usage dashboard).([Amadeus IT Group SA](https://developers.amadeus.com/self-service))

---

## 12. Library Notes (for AI Agent)

### Amadeus Self-Service

- Docs: `https://developers.amadeus.com/self-service`
- Uses OAuth2 client credentials automatically via Node SDK.
- Endpoints grouped by category; we use Hotels → Hotel Search + Hotel Booking.([Amadeus Docs](https://developers.amadeus.com/self-service))

### Google Places API (New)

- Docs: `https://developers.google.com/maps/documentation/places/web-service`
- Place Details + Photo + Text Search for hotels (`type=lodging`).
- Already partially integrated in `app/api/places/*`.

### Vercel AI SDK v6

- Docs: `https://v6.ai-sdk.dev/docs/introduction`
- TripSage uses `streamText` + tool calling; no changes needed except tool semantics.

### shadcn/ui

- Docs: `https://ui.shadcn.com`
- Use for Cards, Tabs, Badges, Skeleton, Dialogs to build modern hotel result UIs.

### Upstash

- Redis client: `@upstash/redis` used via `lib/redis.ts`.
- Ratelimit: `@upstash/ratelimit` used in `accommodations/container.ts` and AI tools for sliding-window limits.

### Supabase

- Docs: `https://supabase.com/docs/guides/auth` and JS client v2 docs.([Supabase Docs](https://supabase.com/docs/guides/auth))
- Used for persistence and auth; booking persistence remains in the `bookings` table.

### Stripe

- Docs: `https://stripe.com/docs/payments/payment-intents`
- Already in `lib/payments/booking-payment.ts`; continue using PaymentIntents for accommodations.
