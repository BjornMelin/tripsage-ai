# Migration Plan – Activity Search & Booking via Google Places

## 1. Preconditions

- [x] Google Places API (New) enabled in Google Cloud Console
- [x] `GOOGLE_MAPS_SERVER_API_KEY` environment variable configured
- [x] Upstash Redis & Ratelimit already configured for the project (no new cache layer required)
- [x] Supabase `search_activities` table exists (already exists)
- [x] Review ADR-0053 and SPEC-0030 for design decisions

## 2. Code Changes

### 2.1 Service Layer

- [x] Create `frontend/src/domain/activities/service.ts`
  - [x] Implement `ActivitiesService` interface
  - [x] Integrate Google Places API client (`@/lib/google/places-activities.ts`)
  - [x] Implement search method with Supabase `search_activities` caching (no new Redis cache)
  - [x] Implement details method with caching
  - [x] Add error handling and retries
  - [x] Add telemetry spans

- [x] Create `frontend/src/domain/activities/__tests__/service.test.ts`
  - [x] Test search with cache hit/miss
  - [x] Test details retrieval
  - [x] Test error handling
  - [x] Test query construction

### 2.2 Google Places Integration

- [x] Create `frontend/src/lib/google/places-activities.ts`
  - [x] Add activity-specific query helpers
  - [x] Add photo URL resolution helper
  - [x] Add field mask constants
  - [x] Ensure all Places requests use **Places API (New)** endpoints and field masks

- [x] Update `frontend/src/test/msw/handlers/google-places.ts`
  - [x] Mock Text Search endpoint (extended for activities)
  - [x] Mock Place Details endpoint
  - [x] Mock Photo endpoint

### 2.3 AI SDK v6 Tools

- [x] Create `frontend/src/ai/tools/server/activities.ts`
  - [x] Implement `searchActivities` tool using `createAiTool`
  - [x] Implement `getActivityDetails` tool
  - [x] Add input/output schemas (reuse `@schemas/search.ts`)
  - [x] Add error mapping
  - [x] Add telemetry
  - [x] Integrate optional `ai_fallback` behavior by delegating to `web_search` tool using **heuristics only** (for example, zero or very low Places results for a popular destination)

- [x] Update `frontend/src/ai/tools/index.ts`
  - [x] Export `searchActivities`, `getActivityDetails`
  - [x] Add to `toolRegistry` if needed

- [ ] Create `frontend/src/ai/tools/server/__tests__/activities.test.ts`
  - [ ] Test tool execution
  - [ ] Test schema validation
  - [ ] Test error handling

### 2.4 API Routes

- [x] Create `frontend/src/app/api/activities/search/route.ts`
  - [x] Use `withApiGuards` factory
  - [x] Parse request body with `activitySearchParamsSchema`
  - [x] Call service layer
  - [x] Return JSON response
  - [x] Add rate limiting (`activities:search`)

- [x] Create `frontend/src/app/api/activities/[id]/route.ts`
  - [x] Use `withApiGuards` factory
  - [x] Validate Place ID
  - [x] Call service layer
  - [x] Return JSON response
  - [x] Add rate limiting (`activities:details`)

- [ ] Create `frontend/src/app/api/activities/__tests__/route.test.ts`
  - [ ] Test authentication
  - [ ] Test rate limiting
  - [ ] Test request/response formats
  - [ ] Test error handling

### 2.5 Hook Implementation

- [x] Complete `frontend/src/hooks/use-activity-search.ts`
  - [x] Implement `searchActivities` function (call `/api/activities/search`)
  - [x] Implement `saveSearch` function (basic implementation)
  - [x] Implement `resetSearch` function
  - [x] Add loading/error state management
  - [x] Add results and metadata state

- [ ] Create `frontend/src/hooks/__tests__/use-activity-search.test.ts`
  - [ ] Test hook behavior
  - [ ] Test API integration
  - [ ] Test error handling

### 2.6 Database Migration

- [x] Update `search_activities.source` CHECK constraint
  - [x] Add migration: `supabase/migrations/20250124021402_add_googleplaces_source_to_search_activities.sql`
  - [x] Update constraint to include `'googleplaces'` and `'ai_fallback'`

- [x] Verify `search_activities` table RLS policies (if any)

### 2.7 UI Updates

- [x] Update `frontend/src/app/(dashboard)/search/activities/page.tsx`
  - [x] Remove `console.log` statements
  - [x] Integrate completed `useActivitySearch` hook
  - [x] Add error handling UI
  - [x] Add loading states
  - [x] Add hybrid source display (verified vs AI suggestions)

- [x] Update `frontend/src/components/features/search/activity-search-form.tsx`
  - [x] Remove `console.log` statements
  - [x] Ensure form validation works

- [x] Update `frontend/src/components/features/search/activity-card.tsx`
  - [x] Add source label support
  - [x] If both Places and AI suggestions are present, visually differentiate sources (badges/labels)

### 2.8 Rate Limiting

- [x] Add rate limit configs to `frontend/src/lib/ratelimit/routes.ts`
  - [x] `activities:search`: 20 req/min
  - [x] `activities:details`: 30 req/min

### 2.9 Web Search and Crawl Tool Scope

- [x] Confirm that:
  - [x] `webSearch` is only invoked from the activities service as a **fallback** (never as the primary provider).
  - [x] `webSearchBatch` and Firecrawl crawl tools (for example, `crawlUrl`, `crawlSite`) are **not** used by `/api/activities/search` or `/api/activities/[id]` and remain reserved for higher-level agents.

## 3. Data Migrations

- [ ] Run database migration for `search_activities.source` constraint
- [ ] Verify no existing data conflicts with new constraint

## 4. Feature Flags / Rollout

- [ ] No feature flags needed (direct implementation)
- [ ] Consider gradual rollout if Google Places API costs are concern

## 5. Observability & Alerts

- [x] Add telemetry spans for activity search operations (`activities.search`, `activities.details`, `activities.google_places.api`, `activities.cache.hit`, `activities.cache.miss`, `activities.fallback.invoked`, `activities.fallback.suppressed`)
- [ ] Set up alerts for Google Places API error rate > 5% (requires production monitoring setup)
- [ ] Monitor cache hit rate (target: > 60%), segmented by provider source (`googleplaces`, `ai_fallback`) (requires production monitoring setup)
- [ ] Monitor search latency (target: p95 < 500ms) (requires production monitoring setup)
- [ ] Monitor fallback invocation rate (target: tuned based on production data; should generally be a minority of traffic) (requires production monitoring setup)

## 6. Documentation

- [ ] Update `docs/api/api-reference.md`
  - [ ] Document `/api/activities/search` endpoint
  - [ ] Document `/api/activities/[id]` endpoint
  - [ ] Remove "stub" language

- [ ] Update `frontend/README.md`
  - [ ] Add activity search to feature list

- [ ] Create `docs/developers/activities.md` (optional)
  - [ ] Document service layer usage
  - [ ] Document tool usage
  - [ ] Document API usage

## 7. Release & Post-Release Verification

- [ ] Run full test suite: `pnpm test:run`
- [ ] Run type check: `pnpm type-check`
- [ ] Run linter: `pnpm biome:check`
- [ ] Verify Google Places API integration in staging
- [ ] Verify caching works correctly
- [ ] Verify AI chat integration (test `searchActivities` tool)
- [ ] Monitor error rates and latency post-deployment
- [ ] Verify `search_activities` table is being populated
- [ ] Verify `source` values stored are limited to the new allowed set (`googleplaces`, `ai_fallback`, `external_api`, `cached`, legacy values if present)
