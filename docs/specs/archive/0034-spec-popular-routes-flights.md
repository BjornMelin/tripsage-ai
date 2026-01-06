# Popular Routes for Flights — Functional & Technical Spec

## 0. Metadata

- **Spec ID**: SPEC-0034
- **Status**: Proposed
- **Date**: 2025-12-03
- **Owners**: Flights/Frontend
- **Related ADRs**: ADR-0056, ADR-0045, ADR-0050
- **Related Docs**: `docs/architecture/decisions/adr-0056-popular-routes-flights.md`

## 1. Summary

Deliver production-grade “Popular Routes” data on the flights search page. Replace placeholder cards with Amadeus-backed routes (origin, destination, price, dates, airline, source) using cached results and personalization where possible. Provide a typed API route, Zod schemas, React Query hook, and UI states (loading/error/fallback) while keeping API costs low via aggressive caching and rate limiting.

## 2. Goals

- Serve actual popular routes with prices and dates, using Amadeus Flight Offers Search and Flight Destinations (inspiration).
- Cache results in Upstash (prices ~1h TTL, routes ~24h TTL) with per-origin keys and invalidation hooks.
- Provide a single API contract `/api/flights/popular-routes` consumed by a `usePopularRoutes(origin?)` hook.
- Preserve UX resilience: fallback curated cards when API/caching fails; clear loading/error states.
- Keep provider keys server-side and respect repository telemetry/logging patterns.

## 3. Non-Goals

- Booking and payment flows unchanged.
- Only Amadeus will be used; no multi-provider arbitration.
- Flight offer deep-linking deferred; focus on list retrieval.
- Mobile layout unchanged; retain current cards + skeleton/error handling.

## 4. User Stories / UX

- As a traveler, I want to see trending/cheap routes with prices so I can pick a destination quickly.
- As a returning user, I want routes influenced by my recent searches (origin preference) when available.
- As a user on spotty networks, I should still see curated fallback cards rather than blank space.

## 5. Functional Requirements

1) API route `POST/GET /api/flights/popular-routes` (use GET; accept optional `origin`, `limit`, `currency`).  
2) Response: array of `PopularRoute` objects:  
   - `origin`: `{ code, name }`  
   - `destination`: `{ code, name }`  
   - `price`: number, `currency`: string  
   - `departureDate`: ISO date string  
   - `returnDate?`: ISO date string | undefined  
   - `airline?`: string  
   - `source`: `"amadeus" | "cached" | "user_history"`  
3) Caching:  
   - Key: `popular-routes:${origin || "any"}:${currency || "USD"}`  
   - TTL: 3600s for priced results; 86400s for route-only fallback.  
   - Cache payload includes timestamp + source for observability.  
4) Personalization: if user is authenticated and has recent search origin, prefer that origin for the query; otherwise use default curated origins list.  
5) Fallback: If Amadeus fails, return curated routes (existing static cards) with `source: "cached"`.  
6) Errors: return 502 on upstream failure after fallback exhaustion; 400 on invalid params; include `retryAfter` when rate-limited.  
7) Logging/Telemetry: use `withTelemetrySpan` in handler; record cache hit/miss and upstream latency; no `console.*` in server code.  
8) Rate limiting: reuse Upstash rate limiter pattern (see ADR-0032) per-IP/per-user for this route.

## 6. Architecture / Data Flow

```text
Client (usePopularRoutes hook)
    -> /api/flights/popular-routes (Next.js route handler)
        -> construct Amadeus client (server-only) on demand
        -> check Upstash cache
        -> if miss: call Amadeus
            -> flightDestinations (inspiration) to pick origin/destination pairs
            -> flightOffersSearch to price selected pairs
        -> normalize to PopularRoute DTO, store in cache, return to client
```

## 7. Contracts & Schemas

- Zod module `@schemas/flights` additions:  
  - `popularRouteSchema` (strictObject with fields above).  
  - `popularRoutesResponseSchema = z.strictObject({ routes: z.array(popularRouteSchema) })`.  
- Hook return type: `{ data?: PopularRoute[]; isLoading: boolean; isError: boolean; refetch: () => Promise<...> }`.

## 8. Client Integration

- New hook `src/hooks/use-popular-routes.ts` using React Query; key `["popular-routes", origin]`; `staleTime = 5 * 60 * 1000`, `gcTime = 30 * 60 * 1000`.
- Update `FlightSearchPage` to:
  - call `usePopularRoutes` (origin optional from URL params or defaults),
  - render skeleton while loading,
  - show error callout + retry button on failure,
  - keep current hardcoded cards as fallback when `data` absent.

## 9. Backend Implementation Notes

- Route handler location: `src/app/api/flights/popular-routes/route.ts`.
- Build Amadeus client per request (no module-scope state) using existing factory patterns.
- Caching via `@/lib/cache/upstash` with request-scoped Redis client; avoid global singletons.
- Convert Amadeus responses to DTOs; clamp/round prices to two decimals; guard against missing dates.
- Include `Cache-Control: private, max-age=300` for HTTP clients (non-shared).

## 10. Observability, Limits, Resilience

- Wrap handler in `withTelemetrySpan("popular-routes")`.
- Capture counters: cache_hit, cache_miss, upstream_success, upstream_error.
- Rate limit: e.g., 30 req/5m per IP; configurable via env if needed.
- Backoff: if upstream returns 429/5xx, return cached data (if any) plus `source: "cached"`; otherwise 502.

## 11. Security & Privacy

- Keep Amadeus credentials server-side only.  
- No PII stored; personalization only uses recent search origin per user session/id.  
- Ensure responses exclude user-identifying data.  
- Validate inputs with Zod; reject invalid origin codes early.

## 12. Testing Strategy

- Unit: schema validation, cache key TTL logic, Amadeus mapper.  
- Integration (route):  
  - success with cache miss → upstream → cache write,  
  - cache hit path,  
  - upstream failure falls back to curated data,  
  - rate-limit response.  
- MSW handlers for Amadeus in `test/msw/handlers/amadeus.ts`.  
- Hook tests: loading/error/fallback branches; ensures query key uses origin.  
- E2E: flights page shows real data when backend returns routes; fallback when offline.

## 13. Rollout Plan

- Phase 1: build route, schemas, hook behind existing UI with fallback.  
- Phase 2: enable personalization (origin from recent searches).  
- Phase 3: tune caching TTLs and rate limits based on metrics; add alert on 5xx > threshold.  
- Feature is on by default once merged; fallback guarantees safe deploy.

## 14. Risks & Mitigations

- **Cost overrun**: enforce caching and rate limiting; monitor call counts.  
- **Upstream instability**: fallback curated data; exponential backoff on retries.  
- **Data staleness**: TTLs capped at 24h; include `source` field for transparency.  
- **Schema drift**: keep Zod schemas in `@schemas/flights`; reuse in route + hook tests.

## 15. Open Questions

- Should we expose a `limit` query param (default 6)?  
- Should personalization use geo-IP when user not logged in?  
- Preferred currency selection—respect user profile vs. default USD?

## 16. Milestones / Checklist

- [ ] Add Zod schemas (`popularRouteSchema`, `popularRoutesResponseSchema`).  
- [ ] Extend Amadeus client with flight offers + inspiration helpers.  
- [ ] Implement `/api/flights/popular-routes` route with caching and rate limiting.  
- [ ] Add `usePopularRoutes` hook and integrate into flights page with skeleton/error UI.  
- [ ] Add MSW mocks + unit/integration tests + E2E coverage.  
- [ ] Monitor and adjust TTL/rate limits post-deploy; document metrics dashboards.
