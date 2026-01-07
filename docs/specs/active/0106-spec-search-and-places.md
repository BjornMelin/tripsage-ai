# SPEC-0106: Search and places (travel intelligence)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Provide place search and details retrieval (POIs, restaurants, hotels).
- Cache popular queries short TTL.
- Integrate into trip planning and chat tools.

## Requirements

- Unified search interface (provider-agnostic):
  - `searchPlaces(query, locationBias, filters): Promise<SearchPlacesResult>`
  - `getPlaceDetails(placeId): Promise<PlaceDetailsResult>`
  - Expected error cases:
    - Validation errors for invalid inputs (e.g., empty query, invalid placeId)
    - Provider quota/availability errors (rate limits, upstream outages)
    - Not found errors for missing placeId/details
  - Cache semantics:
    - Search results may be cached with a short TTL.
    - Place details caching must follow provider policy (e.g., cache stable identifiers like `placeId`, but fetch full details fresh when policy requires it).
- Support provider abstraction if multiple APIs are used.
- Persist “saved places” to trips.

## Implementation notes (reference)

- **Provider**: Google Places API (New), per ADR-0050 and ADR-0053.
- **Canonical server module**: `src/features/search/server/places/places-service.ts`.
- **Canonical DTO + tool schemas**: `src/domain/schemas/places.ts` (`@schemas/places`).
- **API surface**:
  - `POST /api/places/search` → canonical `{ places: PlaceSummary[] }`
  - `GET /api/places/details/[id]` → canonical `PlaceDetails`
  - `GET /api/places/photo` → photo byte proxy (use `name=...` from `photoName`)
  - `POST /api/places/nearby` → nearby search (Google Places API New)
- **Caching**:
  - Search results: Upstash Redis short TTL (default 10 minutes, clamped 5–15 minutes).
  - Cache keys must not include raw user query strings (hash/canonicalize first).
  - Place details: fetched fresh (no caching of full payloads).
- **SSRF / abuse controls**:
  - All outbound requests use fixed, allowlisted hosts (e.g., `places.googleapis.com`).
  - No user-controlled URL fetch is permitted.
  - Photo proxy validates `photoName` format and dimensions before requesting media.
- **Persistence**:
  - `public.saved_places` stores a minimal `place_snapshot` (no raw upstream payloads) and is protected by trip-membership RLS.
  - Uniqueness is enforced per `(trip_id, place_id)`.

## Tooling

Agent tools:

- search.places
- search.placeDetails
- trips.savePlace(tripId, place)

## Notes

- Provider keys must stay server-only.
- Validate all outbound provider responses with Zod.
- Prefer shared schemas in `src/domain/schemas/*` (e.g., `src/domain/schemas/search.ts`); follow boundary validation conventions in [ADR-0063](../../architecture/decisions/adr-0063-zod-v4-boundary-validation-and-schema-organization.md).
- Do not persist raw third-party provider payloads unless explicitly required by policy and product needs.
