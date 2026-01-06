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
