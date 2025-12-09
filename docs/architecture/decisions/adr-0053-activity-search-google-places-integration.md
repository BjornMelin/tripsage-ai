# ADR-0053: Activity Search & Booking via Google Places API Integration

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-01-15
**Implementation Date**: 2025-11-24
**Category**: Architecture
**Domain**: Travel Supply Integrations
**Related ADRs**: ADR-0050 (Amadeus + Google Places), ADR-0044 (Tool Registry), ADR-0029 (DI Route Handlers)
**Related Specs**: SPEC-0030 (Activity Search & Booking)

## Context

TripSage AI currently has an incomplete activity search feature:

- UI components exist (`/search/activities` page, `forms/activity-search-form`, `cards/activity-card`)
- Zod schemas defined (`@schemas/search.ts`: `activitySchema`, `activitySearchParamsSchema`)
- Database table exists (`search_activities` for durable search caching)
- Hook placeholder exists (`useActivitySearch` with TODOs)
- **Missing**: Backend API routes, AI SDK v6 tools, service layer, Google Places integration

The accommodations feature (ADR-0050) uses Amadeus + Google Places for hotel search. Activities require a different approach:

- No single booking API like Amadeus for activities
- Google Places API (New) provides POI discovery, details, photos, ratings
- Booking integration can be deferred or handled via external links initially

## Decision

We will implement activity search and (future) booking using a **hybrid provider model**:

1. **Google Places API (New)** as the **primary deterministic provider**  
   - Use HTTP `places:searchText` + Place Details with **field masks** to limit cost and data surface.
   - Only request Essentials-tier fields needed for the TripSage `Activity` schema (id, displayName, location, types, rating, userRatingCount, photos metadata, price level).
   - Reuse existing `postPlacesSearch` and geocoding helpers (`src/lib/google/places-geocoding.ts`, `src/lib/google/client.ts`, `src/lib/google/places-utils.ts`).

2. **Hybrid architecture with guarded AI/web fallback (Option B)**
   - When Google Places returns `ZERO_RESULTS`, errors, or clearly insufficient coverage for the query, call the existing `web_search` AI tool (`src/ai/tools/server/web-search.ts`) via AI SDK v6.  
   - Fallback is **advisory only**: results are clearly labeled as `ai_fallback` in response metadata and are not used for in‑app booking; they serve as inspiration and long‑tail coverage.  
   - The hybrid design (deterministic primary + AI fallback) is the selected option after applying the decision framework with a weighted score **≥ 9.0/10.0**.

3. **AI SDK v6 Tools** for activities
   - New tools in `src/ai/tools/server/activities.ts`:
     - `searchActivities` - wraps the activities service search (Places + cache + optional AI fallback).
     - `getActivityDetails` - wraps Place Details for a given Place ID.
     - `bookActivity` - reserved for future integration; no partner/approval‑based APIs in scope.
   - Tools are defined using `createAiTool` (`src/ai/lib/tool-factory.ts`) with Zod v4 input schemas from `@schemas/search.ts` and OTEL guardrails (caching, rate limiting, telemetry).

4. **Service Layer** (`src/domain/activities/service.ts`)
   - Pure, DI-friendly orchestrator that:
     - Accepts `ActivitySearchParams` + context (userId, locale, ip, feature flags).
     - Checks Supabase `search_activities` for cached results.
     - On cache miss, calls Google Places (New) with normalized queries and field masks.
     - Optionally invokes AI/web fallback when deterministic provider underperforms.
     - Returns strongly-typed `ActivitySearchResult` for tools, HTTP routes, and UI.

5. **API Routes** (`src/app/api/activities/*`) using `withApiGuards`
   - `POST /api/activities/search` → DI handler calling the activities service; reuses auth, rate limiting, telemetry, and error handling patterns from `src/lib/api/factory.ts`.  
   - `GET /api/activities/[id]` → Place Details + enrichment via service.  
   - Rate limits wired via `@upstash/ratelimit` + `Redis.fromEnv()` and the central `ROUTE_RATE_LIMITS` registry.

6. **Supabase-backed search cache (no new Redis cache for MVP)**  
   - Use `public.search_activities` as the **authoritative durable cache**, with existing RLS policy and indexes (`supabase/migrations/20251122000000_base_schema.sql`).  
   - Store normalized request parameters, hash, provider `source` (`googleplaces` or `ai_fallback`), and search metadata.  
   - Upstash Redis is used **only for rate limiting and existing shared infra**, not as an additional cache layer for this feature to keep KISS/YAGNI.

7. **Stripe integration** (deferred)
   - Future `bookActivity` implementation may reuse the existing booking payment orchestrator (`src/lib/payments/booking-payment.ts`) but **no partner/approval‑based activity APIs** (Viator/GetYourGuide, etc.) are in scope for this ADR.

## Options Considered

We applied the repository's decision framework:

- **Solution Leverage - 35%**
- **Application Value - 30%**
- **Maintenance & Cognitive Load - 25%**
- **Architectural Adaptability - 10%**

### Option A: Google Places API (New) Only

Google Places (New) Text Search + Place Details as the single provider. No AI/web fallback.

- **Pros**
  - Simple implementation; reuses existing Google Places plumbing from ADR‑0050.
  - Clear, deterministic data model (Places → `Activity` mapping).
  - Easy to reason about caching, quotas, and error handling.
- **Cons**
  - Single-provider dependency; outages or quota exhaustion directly degrade UX.
  - Limited coverage for niche/long-tail activities or emerging venues.
  - No path for richer narratives beyond Places fields.

#### Scores (Option A)

- Solution Leverage: 8.7  
- Application Value: 8.4  
- Maintenance & Cognitive Load: 9.2  
- Architectural Adaptability: 7.5  
- **Weighted Total**: **8.62 / 10**

### Option B: Hybrid - Google Places + AI/Web Fallback (Chosen)

Use Google Places (New) as primary deterministic provider, with a guarded AI/web fallback (existing `web_search` tool via Firecrawl and AI SDK v6) when Places alone is insufficient.

- **Pros**
  - High leverage on existing stack: Google Places + `web_search` + AI SDK v6 tools.  
  - Best user value: deterministic results for mainstream queries, AI-augmented coverage for tail queries.  
  - Strong adaptability: modular provider abstraction allows new deterministic sources later without redesign.  
  - No partner/approval-based APIs required; uses pay-as-you-go Google Places with $200+ credit and our existing Firecrawl integration.
- **Cons**
  - Higher complexity: requires routing logic, signals for fallback triggers, and observability.  
  - Needs careful labeling and guardrails to avoid mixing authoritative and AI‑fabricated content.  
  - Requires more nuanced caching metadata (`source`, confidence).

#### Scores (Option B)

- Solution Leverage: 9.7  
- Application Value: 9.6  
- Maintenance & Cognitive Load: 7.2  
- Architectural Adaptability: 9.4  
- **Weighted Total**: **9.02 / 10** ✅ (meets ≥ 9.0 requirement)

### Option C: Pure AI/RAG over Generic Web Search

Do not depend on any structured provider; instead, rely entirely on `web_search` + RAG to synthesize activities.

- **Pros**
  - No direct external API coupling beyond generic web search.  
  - Conceptually flexible; can surface arbitrary content.
- **Cons**
  - High risk of hallucinations and inconsistent metadata (location, pricing, timing).  
  - Difficult to enforce KISS/YAGNI due to heavy prompt engineering and post‑processing.  
  - Poor fit with existing strongly-typed schemas and caching patterns.  
  - Harder to reason about quotas and ToS across multiple search providers.

#### Scores

- Solution Leverage: 6.2  
- Application Value: 6.8  
- Maintenance & Cognitive Load: 5.5  
- Architectural Adaptability: 8.0  
- **Weighted Total**: **6.39 / 10**

### Final Decision

We adopt **Option B (Hybrid - Google Places + AI/Web Fallback)** as the definitive architecture for activity search, as it is the **only option scoring ≥ 9.0/10.0** under the weighted framework. Implementation will be phased (deterministic path first, then fallback), but the target architecture is hybrid.

### Web Search Integration Strategy

We adopt a **heuristically gated web search fallback** pattern for this ADR:

- **Primary path**: `/api/activities/search` uses Google Places API (New) as the sole provider when it returns sufficient results; web search is not invoked on the happy path.
- **Fallback triggers** (initial heuristics, to be tuned over time):
  - Zero Places results, or
  - Very few Places results (for example, fewer than three) for destinations that are otherwise popular, or
  - Explicit user or agent intent for “off the beaten path”, “local blogs/guides”, or similar long-tail discovery.
- **Tools in scope**:
  - `webSearch` is the only Firecrawl-based tool used by the activities service and only on this fallback path.
  - `webSearchBatch` and Firecrawl crawl tools (for example, `crawlUrl`, `crawlSite`) remain reserved for higher-level agents (budget/itinerary/deep research) and are **not** called from `/api/activities/search` or `/api/activities/[id]`.
- **Cost and safety constraints**:
  - Rely on existing tool-level rate limits and TTLs defined in `webSearch`.
  - Keep fallback invocation under a target threshold (for example, fewer than 20% of activity searches) and monitor via `activities.fallback.invoked` metrics.
  - Persist all AI/web-derived activities as `source = 'ai_fallback'` in `search_activities` and surface them to users as suggestions rather than authoritative inventory or bookable items.

## Consequences

### Positive

- Completes visible feature gap in UI
- Enables activity search in AI chat via tools
- Follows established patterns (accommodations/flights) and reuses `createAiTool`, `withApiGuards`, and OTEL spans
- Leverages existing Google Places integration and geocoding helpers while aligning with Places API (New) usage/billing recommendations (field masks, minimal data)
- Reuses Supabase `search_activities` table and existing RLS/index patterns for durable search caching
- Unblocks activity agent creation on top of a stable, typed service API
- Hybrid design improves coverage for niche/long-tail activities without depending on partner/approval-based APIs
- Clear separation between deterministic (`googleplaces`) and `ai_fallback` sources in metadata improves debuggability and user trust

### Negative

- No direct booking capability initially (requires external links)
- Limited real-time availability/pricing data from Places; activity pricing remains approximate
- Additional Google Places API costs; must be managed via field masks, aggressive caching, and quotas
- Hybrid fallback path increases complexity (routing logic, instrumentation, testing)
- Requires implementing new activities service layer and tools from scratch

### Neutral

- Database table already exists; just needs to be populated
- Schemas already defined; minimal changes needed
- UI components exist; backend integration needed

## References

- ADR-0050: Amadeus + Google Places + Stripe hybrid for accommodations
- ADR-0044: AI SDK v6 Tool Registry and MCP Integration
- ADR-0029: DI Route Handlers and Testing
- SPEC-0027: Accommodations Amadeus + Google + Stripe (pattern reference)
- SPEC-0030: Activity Search & Booking - Functional & Technical Spec
- Google Places API (New) Documentation (Text Search, Place Details, Usage & Billing):  
  - <https://developers.google.com/maps/documentation/places/web-service>  
  - <https://developers.google.com/maps/documentation/places/web-service/usage-and-billing>
- Upstash Redis & Ratelimit JS (HTTP Redis, Redis.fromEnv, rate limiting patterns):  
  - <https://upstash.com/docs/redis/sdks/ts/getstarted>  
  - <https://upstash.com/docs/redis/quickstarts/nextjs-app-router>  
  - <https://github.com/upstash/ratelimit-js>
- Vercel AI SDK v6 (tools, `streamText`, Next.js route patterns):  
  - <https://v6.ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage>  
  - <https://v6.ai-sdk.dev/docs/getting-started/nextjs-app-router>
- Zod v4 (schemas, strict validation): <https://zod.dev/v4>
- Supabase RLS & Data API Hardening (for `search_activities`):  
  - <https://supabase.com/docs/guides/database/postgres/row-level-security>  
  - <https://supabase.com/docs/guides/database/hardening-data-api>
