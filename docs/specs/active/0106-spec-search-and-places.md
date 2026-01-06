# SPEC-0106: Search and places (travel intelligence)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Provide place search and details retrieval (POIs, restaurants, hotels).
- Cache popular queries short TTL.
- Integrate into trip planning and chat tools.

## Requirements

- Unified search interface:
  - searchPlaces(query, locationBias, filters)
  - getPlaceDetails(placeId)
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
