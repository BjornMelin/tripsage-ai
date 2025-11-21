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

- **Amadeus Self-Service APIs** (hotels search and booking).
- **Google Places API (New)** for hotel discovery, photos, and ratings.
- **Stripe** for card payments via PaymentIntents.

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

   - Wraps the **Amadeus Node SDK**.
   - Implements `AccommodationProviderAdapter` with methods:
     - `search(params, ctx)`
     - `getDetails(params, ctx)`
     - `checkAvailability(params, ctx)`
     - `createBooking(params, ctx)`

3. `AccommodationsService`:

   - Uses Amadeus endpoints:
     - Geocode → `reference-data/locations/hotels/by-geocode` for hotels near a lat/lng.
     - Offers → `/v3/shopping/hotel-offers` for real-time prices and availability.
   - When enriching details:
     - Calls Google Places API (New) Place Details & Photos with `type=lodging`.

4. Booking flow:

   - AI `bookAccommodation` tool:
     - Ensures user/approval context.
     - Triggers Stripe `PaymentIntent` creation via `processBookingPayment`.
   - `runBookingOrchestrator`:
     - Calls `AmadeusProviderAdapter.createBooking(...)`.
     - Persists booking to Supabase (same `bookings` table).
     - Uses Amadeus `id/confirmationId` fields for booking reference.

5. UI:

   - Hotel search pages in `app/(dashboard)/trips/[tripId]/stay/page.tsx` and
     `app/(marketing)/stays/page.tsx` are wired to `useAccommodationSearch` and
     render results using new shadcn/ui components:
     `ModernHotelResults` + `AccommodationCard`.

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
