# Activity Search & Booking – Functional & Technical Spec

**Version**: 1.0.0
**Status**: Implemented
**Date**: 2025-01-15
**Implementation Date**: 2025-11-24
**Category**: Feature Implementation
**Domain**: Travel Supply Integrations
**Related ADRs**: ADR-0053
**Related Specs**: SPEC-0027 (Accommodations pattern reference)

## 1. Summary

Implement an end-to-end **Activity Search & Booking** feature using a **hybrid provider model**:

- **Primary deterministic layer**: Google Places API (New) Text Search + Place Details for activity discovery and metadata (name, location, rating, photos, price level).  
- **Guarded AI/web fallback**: existing `web_search` tool (Firecrawl + AI SDK v6) when Places is insufficient (zero results / low coverage), returning clearly labeled `ai_fallback` suggestions.  
- **Typed orchestration**: Activities service + AI SDK v6 tools (`searchActivities`, `getActivityDetails`) + Next.js route handlers with `withApiGuards`.  
- **Caching**: Supabase `search_activities` table as durable cache for authenticated users only; anonymous searches are not cached; no new Redis cache layer for MVP; Upstash Redis remains used for rate limiting.

## 2. Goals

- Enable users to search for activities (tours, experiences, attractions) by destination, category, date, and filters
- Provide activity details (photos, ratings, descriptions, location) via **Google Places API (New)** with field masks and ToS-compliant data usage
- Integrate activity search into AI chat via `searchActivities` tool and existing AI SDK v6 chat/agent routes
- Cache structured search results in Supabase `search_activities` (durable JSONB cache with RLS) for authenticated users only; anonymous searches bypass caching; rely on existing Upstash Redis usage only for **rate limiting**
- Support activity booking flow (initially via external links; Stripe integration deferred; **no partner/approval-based booking APIs**)
- Maintain consistency with accommodations/flights patterns and reuse shared infrastructure (tool factory, route factories, Supabase SSR, OTEL)

## 3. Non-Goals

- Direct booking API integration (Viator/GetYourGuide) in initial implementation
- Real-time availability/pricing from booking providers
- Activity agent creation (deferred to separate work)
- Stripe payment integration for activities (deferred)

## 4. User Stories

- As a user, I want to search for activities in a destination with filters (category, date, price, difficulty) so I can discover experiences
- As a user, I want to see activity details (photos, ratings, descriptions) so I can make informed decisions
- As a user, I want to save favorite activities so I can reference them later
- As a user, I want to ask the AI assistant "What activities are available in Paris?" and get relevant, trustworthy results, with clearly labeled AI-suggested ideas
- As a developer, I want activity search to follow the same patterns as accommodations/flights for maintainability

## 5. User Flows

### 5.1 Activity Search Flow

1. User navigates to `/search/activities` or uses search form
2. User enters destination, optional filters (category, date, price range, difficulty)
3. Frontend calls `POST /api/activities/search` with search params
4. Backend:
   - Validates input with `activitySearchParamsSchema`
   - **For authenticated users only**: Computes a deterministic `query_hash` and checks Supabase `search_activities` for a matching row (`user_id`, `destination`, `activity_type`, `query_hash`, `expires_at > now()`)
   - **For authenticated users**: If cache hit, returns cached `results` with `metadata.cached = true`, `metadata.source = "googleplaces"` or `"ai_fallback"`
   - If cache miss (or anonymous user):
     - Calls Google Places API (New) Text Search with activity-specific queries and **field masks**:
       - Search field mask: `places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types,places.priceLevel`
     - Maps Google Places results into `Activity` schema (see §6) with approximate pricing (`priceLevel` → `price` index 0–4)
     - **For authenticated users only**: Persists results into `search_activities` with `source = 'googleplaces'` and appropriate TTL (e.g. 24h). Anonymous searches are not cached.
     - If Places returns `ZERO_RESULTS` or clearly underperforms (e.g. very low result count in a popular destination), triggers **AI/web fallback**:
       - Invokes `web_search` tool (`frontend/src/ai/tools/server/web-search.ts`) with a query like `"things to do in {destination}"`.
       - Normalizes AI/web results into a **secondary suggestions list** shaped as `Activity[]` where possible, flagged as `source = 'ai_fallback'`.
       - **For authenticated users only**: Persists fallback results in `search_activities` with shorter TTL (e.g. 6h) and `source = 'ai_fallback'`. Anonymous searches are not cached.
   - Returns combined result:
     - Primary `googleplaces` activities first, then `ai_fallback` suggestions (if any), with `metadata` describing sources.
5. UI displays activities in `ActivityCard` components
6. User can click activity for details or save to favorites

### 5.2 Activity Details Flow

1. User clicks activity card or requests details via AI tool
2. Frontend calls `GET /api/activities/[id]` (where `id` is Google Place ID)
3. Backend:
   - Validates Place ID
   - **For authenticated users only**: Checks cache for details (either in `search_activities` metadata or a dedicated details cache, e.g. `search_activities` row keyed by `activity_id`)
   - If cache miss (or anonymous user): Calls Google Places API (New) Place Details with strict field mask:
     - Details field mask: `id,displayName,formattedAddress,location,rating,userRatingCount,photos,types,editorialSummary,regularOpeningHours,priceLevel`
   - Enriches with photos, reviews, opening hours
   - **For authenticated users only**: Caches details (TTL: 7 days). Anonymous requests are not cached.
   - Returns `Activity` object
4. UI displays detailed activity view

### 5.3 AI Chat Integration Flow

1. User asks AI: "What activities are available in Tokyo?"
2. AI calls `searchActivities` tool with parsed parameters
3. Tool executes service layer search (same as API route)
4. Tool returns structured activity list plus metadata:
   - Which results came from `googleplaces` vs `ai_fallback`
   - Any notable caveats (e.g. "AI suggestions are based on web content, not live availability")
5. AI formats response with activity cards (AI Elements `card.v1` schema), visually distinguishing:
   - Verified activities (Places) vs. AI-suggested inspirations
6. User can request details or booking via follow-up messages

### 5.4 Booking Flow (Future)

1. User selects activity and clicks "Book"
2. System checks if booking API available (future: Viator/GetYourGuide)
3. If available: Create Stripe PaymentIntent, redirect to booking
4. If not: Show external booking link (Google Maps, provider website)
5. Persist booking reference in `bookings` table (future)

## 6. Data Model & Schemas

### 6.1 Existing Schemas (No Changes)

```typescript
// @schemas/search.ts
export const activitySearchParamsSchema = z.object({
  adults: z.number().int().positive().max(20).optional(),
  category: z.string().optional(),
  children: z.number().int().nonnegative().max(20).optional(),
  date: z.string().optional(), // ISO date string
  destination: z.string().optional(),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  duration: z.object({
    max: z.number().positive().optional(),
    min: z.number().positive().optional(),
  }).optional(),
  indoor: z.boolean().optional(),
  infants: z.number().int().nonnegative().max(20).optional(),
});

export const activitySchema = z.object({
  coordinates: z.object({ lat: z.number(), lng: z.number() }).optional(),
  date: z.string(), // ISO date string
  description: z.string(),
  duration: z.number().int().positive(), // minutes
  id: z.string().min(1), // Google Place ID
  images: z.array(z.string().url()).optional(),
  location: z.string().min(1),
  name: z.string().min(1),
  /**
   * Approximate per-person price INDEX, not a precise currency amount.
   *
   * - For Google Places: derived from `priceLevel` (0–4) where
   *   0 = free, 1 = inexpensive, 2 = moderate, 3 = expensive, 4 = very expensive.
   * - For AI fallback suggestions: always provide a numeric index. When
   *   pricing is unknown, set `price` to `0` and surface "approximate" copy in
   *   the UI; do not omit the field so validation remains consistent.
   */
  price: z.number().nonnegative(),
  rating: z.number().min(0).max(5),
  type: z.string().min(1), // category
});
```

### 6.2 Database Schema (Already Exists)

```sql
-- search_activities table (already exists)
CREATE TABLE IF NOT EXISTS public.search_activities (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  destination TEXT NOT NULL,
  activity_type TEXT,
  query_parameters JSONB NOT NULL,
  query_hash TEXT NOT NULL,
  results JSONB NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('viator','getyourguide','googleplaces','ai_fallback','external_api','cached')),
  search_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Note**: Update `source` CHECK constraint to include `'googleplaces'`:

```sql
ALTER TABLE public.search_activities
  DROP CONSTRAINT IF EXISTS search_activities_source_check,
  ADD CONSTRAINT search_activities_source_check
    CHECK (source IN ('viator','getyourguide','googleplaces','ai_fallback','external_api','cached'));
```

## 7. API Design & Integration Points

### 7.1 API Routes

#### POST /api/activities/search

**Request Body**:

```typescript
{
  destination: string;
  category?: string;
  date?: string; // ISO date
  adults?: number;
  children?: number;
  infants?: number;
  duration?: { min?: number; max?: number };
  difficulty?: "easy" | "moderate" | "challenging" | "extreme";
  indoor?: boolean;
}
```

**Response**:

```typescript
{
  activities: Activity[];
  metadata: {
    total: number;
    cached: boolean;
    primarySource: "googleplaces" | "ai_fallback" | "mixed";
    sources: Array<"googleplaces" | "ai_fallback" | "cached">;
    // Optional notes to surface caveats to the UI/chat:
    notes?: string[];
  };
}
```

**Implementation**: `frontend/src/app/api/activities/search/route.ts`

#### GET /api/activities/[id]

**Path Params**: `id` (Google Place ID)

**Response**: `Activity` object

**Implementation**: `frontend/src/app/api/activities/[id]/route.ts`

### 7.2 AI SDK v6 Tools

#### searchActivities

**Input Schema**: `activitySearchParamsSchema`
**Output Schema**: `z.object({ activities: z.array(activitySchema), metadata: z.object({ ... }) })`
**Implementation**: `frontend/src/ai/tools/server/activities.ts`

#### getActivityDetails

**Input Schema**: `z.object({ placeId: z.string() })`
**Output Schema**: `activitySchema`
**Implementation**: `frontend/src/ai/tools/server/activities.ts`

#### bookActivity (Future)

**Input Schema**: `z.object({ placeId: z.string(), date: z.string(), participants: z.object({ ... }) })`
**Output Schema**: `z.object({ bookingId: z.string(), status: z.string() })`
**Implementation**: Deferred

### 7.3 Service Layer

**File**: `frontend/src/domain/activities/service.ts`

**Interface**:

```typescript
export interface ActivitiesService {
  search(params: ActivitySearchParams, ctx: ServiceContext): Promise<ActivitySearchResult>;
  details(placeId: string, ctx: ServiceContext): Promise<Activity>;
}
```

**Dependencies**:

- Google Places helper stack:
  - `frontend/src/lib/google/places-geocoding.ts` (lat/lng geocoding with 30‑day cache)
  - `frontend/src/lib/google/client.ts` (`postPlacesSearch` wrapper)
  - `frontend/src/lib/google/places-utils.ts` (normalization, cache keys)
- Supabase client for `search_activities` table via `TypedServerSupabase`
- Upstash Ratelimit via `@upstash/ratelimit` and `Redis.fromEnv()` for per-route limits (no new Redis cache for MVP)

### 7.4 Google Places API Integration

**Endpoints Used**:

- `POST /v1/places:searchText` - Text search for activities
- `GET /v1/places/{placeId}` - Place details
- `GET /v1/{photoName}` - Photo URLs

**Field Masks** (cost optimization):

- Search: `places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types`
- Details: `id,displayName,formattedAddress,location,rating,userRatingCount,photos,types,editorialSummary,regularOpeningHours`

**Query Construction**:

- Base query: `"{category} activities in {destination}"`
- Examples: `"outdoor activities in Tokyo"`, `"guided tours in Paris"`, `"museums in New York"`

## 8. UI / UX States

### 8.1 Search Page States

- **Loading**: Show `LoadingSpinner` while fetching
- **Empty**: Show "No activities found" message with search tips
- **Error**: Display error message with retry button
- **Success**: Display activity cards in grid/list layout
- **Cached**: Show cached indicator (optional), with tooltip clarifying age/source
- **Hybrid Sources**: When both Places and AI suggestions are present:
  - Group sections: “Verified activities” and “More ideas powered by AI”
  - Visually differentiate cards (badges, subtle labels)

### 8.2 Activity Card States

- **Default**: Show name, image, rating, price, location
- **Hover**: Show quick actions (save, share, details)
- **Selected**: Highlighted border, show details panel
- **Loading Details**: Skeleton loader for details view

### 8.3 AI Chat Integration

- **Tool Call**: Show "Searching activities..." indicator
- **Results**: Render activity cards inline in chat
- **Error**: Show error message, suggest retry and optionally offer “web search” style exploration when deterministic provider fails
- **Source Transparency**: Clearly label AI-sourced suggestions in chat (“Suggested by AI based on web results, not live availability”)

## 9. Observability & Telemetry

### 9.1 Telemetry Spans

- `activities.search` - Activity search operation
- `activities.details` - Activity details retrieval
- `activities.cache.hit` - Cache hit event
- `activities.cache.miss` - Cache miss event
- `activities.google_places.api` - Google Places API call
- `activities.fallback.invoked` - AI/web fallback triggered
- `activities.fallback.suppressed` - Conditions met but fallback intentionally not used (feature flag / guardrail)

### 9.2 Logging

- Use `createServerLogger("activities.service")` for service layer
- Log search parameters (sanitized), result counts, cache hits/misses
- Log Google Places API errors with status codes

### 9.3 Metrics

- Search latency (p50, p95, p99)
- Cache hit rate (per-provider: `googleplaces`, `ai_fallback`) - metrics only apply to authenticated users
- Google Places API error rate
- Search result count distribution
- Fallback invocation rate (% of requests requiring `ai_fallback`)
- Quota and billing indicators for Places (requests per day, per minute)

## 10. Testing Strategy

### 10.1 Unit Tests

- **Service Layer**: `frontend/src/domain/activities/__tests__/service.test.ts`
  - Mock Google Places API responses
  - Test cache hit/miss logic
  - Test query construction
  - Test error handling

- **AI Tools**: `frontend/src/ai/tools/server/__tests__/activities.test.ts`
  - Mock service layer
  - Test tool input/output schemas
  - Test error mapping

### 10.2 Integration Tests

- **API Routes**: `frontend/src/app/api/activities/__tests__/route.test.ts`
  - Mock Supabase client
  - Mock Google Places API
  - Test authentication/rate limiting
  - Test response formats

### 10.3 E2E Tests

- **Search Flow**: `frontend/e2e/activity-search.spec.ts`
  - Navigate to search page
  - Enter search criteria
  - Verify results display
  - Click activity for details

### 10.4 Test Data

- Use MSW handlers for Google Places API (`frontend/src/test/msw/handlers/google-places.ts`)
- Mock Place IDs: `ChIJN1t_tDeuEmsRUsoyG83frY4` (Sydney Opera House), etc.

## 11. Risks & Open Questions

### 11.1 Risks

- **Google Places API Costs**: Text Search costs $32 per 1000 requests. Mitigation: Aggressive caching, field masks.
- **Limited Booking Data**: No real-time availability/pricing. Mitigation: Defer to external links initially.
- **Place ID Stability**: Google Place IDs are stable but may change. Mitigation: Store Place IDs, handle not-found gracefully.
- **AI Fallback Quality**: AI/web suggestions might be out of date or low quality. Mitigation: mark clearly as suggestions, avoid enabling booking for `ai_fallback` entries, and track fallback quality via telemetry.

### 11.2 Open Questions

- Should we support multiple activity providers (Viator, GetYourGuide) in future?
- How to handle activity availability without booking API?
- Should we create an activity agent similar to accommodation agent?
- What heuristic thresholds (result count, destination popularity, query intent) should trigger AI fallback vs. returning deterministic-only results?

## 12. Implementation Phases

### Phase 1: Core Search (MVP) ✅ COMPLETED

- [x] Service layer with Google Places integration (no AI fallback yet; deterministic only)
- [x] API route `/api/activities/search`
- [x] AI tool `searchActivities`
- [x] Complete `useActivitySearch` hook
- [x] Basic Supabase `search_activities` caching and rate limiting

### Phase 2: Details & Enrichment ✅ COMPLETED

- [x] API route `/api/activities/[id]`
- [x] AI tool `getActivityDetails`
- [x] Photo URL resolution (via Places API photo names)
- [x] Reviews/ratings enrichment (via Places API)

### Phase 3: Hybrid Fallback Enablement ✅ COMPLETED

- [x] Integrate guarded `ai_fallback` path using `web_search` tool
- [x] Add metadata fields to distinguish sources and surface caveats
- [x] Instrument fallback metrics and tune thresholds based on production data
- [x] Normalize web search results into Activity[] format

### Phase 4: Booking Integration ✅ COMPLETED

- [x] External booking link handling (Google Maps place URLs)
- [x] Booking helper functions (`getActivityBookingUrl`, `openActivityBooking`)
- [x] UI integration for booking flow
- [ ] Stripe PaymentIntent creation (deferred - no partner APIs)
- [ ] Booking persistence (deferred - no partner APIs)

### Phase 5: Agent & Optimization ✅ COMPLETED

- [x] Activity agent type added to configuration schema (`activityAgent`)
- [x] Tools registered and available for agent use
- [ ] Advanced caching strategies (can be optimized based on production data)
- [ ] Performance optimization (can be optimized based on production data)

## 13. Web Search Integration Strategy

- **Primary provider**: For `/api/activities/search` and `/api/activities/[id]`, Google Places API (New) is the only provider on the happy path when it returns sufficient results. All core flows (UI + tools) should first rely on Places data and Supabase caching.
- **Heuristically gated fallback**:
  - Trigger `web_search` only when:
    - Places returns no results, or
    - Places returns very few results (for example, fewer than three) for a destination that is typically rich in activities, or
    - The user’s intent (in chat) clearly asks for non-standard/local/“off the beaten path” content where web articles add value.
  - Fallback queries use compact prompts such as `"things to do in {destination}"` with small limits and `fresh = false` by default to maximize cache hits.
- **Tool scope and exclusions**:
  - `webSearch` (`frontend/src/ai/tools/server/web-search.ts`) is the **only** Firecrawl-based tool used by the activities service, and only on the fallback path described above.
  - `webSearchBatch` and crawl tools (`crawlUrl`, `crawlSite`) remain reserved for higher-level agents (for example, itinerary/budget/deep research flows) and are **not** part of the `/api/activities/search` or `/api/activities/[id]` implementations in this spec.
- **Operational safeguards**:
  - Respect `webSearch`’s own rate limits and TTL heuristics; do not add parallel, redundant Firecrawl integrations.
  - Track fallback usage via `activities.fallback.invoked` and keep it within a small fraction of overall searches (target under 20% in normal operation).
  - Ensure UI and chat surfaces clearly label `ai_fallback` results and never treat them as authoritative for booking or guaranteed availability.
