# ADR-0056: Popular Routes for Flights (Amadeus + Upstash Caching)

**Version**: 1.0.0  
**Status**: Proposed  
**Date**: 2025-12-03  
**Category**: Frontend  
**Domain**: Flights/Search  
**Related ADRs**: ADR-0045, ADR-0050, ADR-0029, ADR-0032  
**Related Specs**: SPEC-0034

## Context

The flights search page currently renders placeholder “Popular Routes” cards. The only existing backend surface is `/api/flights/popular-destinations`, which returns destinations without prices or routes. The Amadeus client in `domain/amadeus/client.ts` only implements hotel APIs—no flight pricing or inspiration endpoints are wired. We need real flight route data (origin, destination, price, dates, airline) with caching and personalization, while keeping costs and rate limits under control.

## Decision

We will implement a production “Popular Routes” pipeline backed by Amadeus flight APIs and cached in Upstash. The plan includes:

- Extend the Amadeus client with `searchFlightOffers()` (pricing) and `getFlightInspirationSearch()` (cheapest destinations).
- Add a new route handler `/api/flights/popular-routes/route.ts` that returns `PopularRoute` objects, validates responses with Zod v4, and caches results (prices 1h TTL, routes 24h TTL) in Upstash Redis.
- Support personalization via recent user searches when available; otherwise fall back to curated defaults.
- Provide a React Query hook `usePopularRoutes(origin?)` with sensible cache/stale settings and loading/error states.
- Update the flights page to consume the hook and show loading/error skeletons while keeping a hardcoded fallback for offline/error scenarios.

## Consequences

### Positive

- Real, priced route data improves UX and relevance.  
- Caching reduces Amadeus API spend and latency.  
- Shared schemas/hooks keep frontend type safety and reuse.

### Negative

- Additional Amadeus quota/cost exposure; requires monitoring and throttling.  
- More complexity in caching and personalization logic.

### Neutral

- New env dependencies (`AMADEUS_CLIENT_ID/SECRET/ENV`) already exist but become required for this feature.  
- Maintains curated fallback to avoid blank states.

## Alternatives Considered

### Keep placeholders only

Simple and zero cost, but fails UX expectations for live deals and offers no personalization.

### Third-party aggregator (e.g., Skyscanner/RapidAPI)

Would add another provider and legal/latency risks; Amadeus is already in use elsewhere (ADR-0050) and better aligned with existing contracts.

## References

- SPEC-0034 (docs/specs/active/0034-spec-popular-routes-flights.md)  
- ADR-0045 (Flights DTOs)  
- ADR-0050 (Amadeus + Google Places + Stripe)  
- Upstash caching patterns in `lib/cache/upstash.ts`
