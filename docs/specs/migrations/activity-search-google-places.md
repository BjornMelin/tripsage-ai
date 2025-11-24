# Migration Plan – Activity Search & Booking via Google Places

## 1. Preconditions

- [ ] Google Places API (New) enabled in Google Cloud Console
- [ ] `GOOGLE_MAPS_SERVER_API_KEY` environment variable configured
- [ ] Upstash Redis & Ratelimit already configured for the project (no new cache layer required)
- [ ] Supabase `search_activities` table exists (already exists)
- [ ] Review ADR-0053 and SPEC-0030 for design decisions

## 2. Code Changes

### 2.1 Service Layer

- [ ] Create `frontend/src/domain/activities/service.ts`
  - [ ] Implement `ActivitiesService` interface
  - [ ] Integrate Google Places API client (`@/lib/google/places.ts`)
  - [ ] Implement search method with Supabase `search_activities` caching (no new Redis cache)
  - [ ] Implement details method with caching
  - [ ] Add error handling and retries
  - [ ] Add telemetry spans

- [ ] Create `frontend/src/domain/activities/__tests__/service.test.ts`
  - [ ] Test search with cache hit/miss
  - [ ] Test details retrieval
  - [ ] Test error handling
  - [ ] Test query construction

### 2.2 Google Places Integration

- [ ] Extend `frontend/src/lib/google/places.ts` (if needed)
  - [ ] Add activity-specific query helpers
  - [ ] Add photo URL resolution helper
  - [ ] Add field mask constants
  - [ ] Ensure all Places requests use **Places API (New)** endpoints and field masks

- [ ] Create `frontend/src/test/msw/handlers/google-places.ts` (if not exists)
  - [ ] Mock Text Search endpoint
  - [ ] Mock Place Details endpoint
  - [ ] Mock Photo endpoint

### 2.3 AI SDK v6 Tools

- [ ] Create `frontend/src/ai/tools/server/activities.ts`
  - [ ] Implement `searchActivities` tool using `createAiTool`
  - [ ] Implement `getActivityDetails` tool
  - [ ] Add input/output schemas (reuse `@schemas/search.ts`)
  - [ ] Add error mapping
  - [ ] Add telemetry
  - [ ] Integrate optional `ai_fallback` behavior by delegating to `web_search` tool using **heuristics only** (for example, zero or very low Places results for a popular destination)

- [ ] Update `frontend/src/ai/tools/index.ts`
  - [ ] Export `searchActivities`, `getActivityDetails`
  - [ ] Add to `toolRegistry` if needed

- [ ] Create `frontend/src/ai/tools/server/__tests__/activities.test.ts`
  - [ ] Test tool execution
  - [ ] Test schema validation
  - [ ] Test error handling

### 2.4 API Routes

- [ ] Create `frontend/src/app/api/activities/search/route.ts`
  - [ ] Use `withApiGuards` factory
  - [ ] Parse request body with `activitySearchParamsSchema`
  - [ ] Call service layer
  - [ ] Return JSON response
  - [ ] Add rate limiting (`activities:search`)

- [ ] Create `frontend/src/app/api/activities/[id]/route.ts`
  - [ ] Use `withApiGuards` factory
  - [ ] Validate Place ID
  - [ ] Call service layer
  - [ ] Return JSON response
  - [ ] Add rate limiting (`activities:details`)

- [ ] Create `frontend/src/app/api/activities/__tests__/route.test.ts`
  - [ ] Test authentication
  - [ ] Test rate limiting
  - [ ] Test request/response formats
  - [ ] Test error handling

### 2.5 Hook Implementation

- [ ] Complete `frontend/src/hooks/use-activity-search.ts`
  - [ ] Implement `searchActivities` function (call `/api/activities/search`)
  - [ ] Implement `saveSearch` function (persist to Supabase)
  - [ ] Implement `resetSearch` function
  - [ ] Add loading/error state management
  - [ ] Integrate with `useSearchStore` if needed

- [ ] Create `frontend/src/hooks/__tests__/use-activity-search.test.ts`
  - [ ] Test hook behavior
  - [ ] Test API integration
  - [ ] Test error handling

### 2.6 Database Migration

- [ ] Update `search_activities.source` CHECK constraint
  - [ ] Add migration: `supabase/migrations/YYYYMMDDHHMMSS_add_googleplaces_source.sql`
  - [ ] Update constraint to include `'googleplaces'` and `'ai_fallback'`

- [ ] Verify `search_activities` table RLS policies (if any)

### 2.7 UI Updates

- [ ] Update `frontend/src/app/(dashboard)/search/activities/page.tsx`
  - [ ] Remove `console.log` statements
  - [ ] Integrate completed `useActivitySearch` hook
  - [ ] Add error handling UI
  - [ ] Add loading states

- [ ] Update `frontend/src/components/features/search/activity-search-form.tsx`
  - [ ] Remove `console.log` statements
  - [ ] Ensure form validation works

- [ ] Verify `frontend/src/components/features/search/activity-card.tsx` displays correctly
  - [ ] If both Places and AI suggestions are present, visually differentiate sources (badges/labels)

### 2.8 Rate Limiting

- [ ] Add rate limit configs to `frontend/src/lib/ratelimit/routes.ts`
  - [ ] `activities:search`: 20 req/min
  - [ ] `activities:details`: 30 req/min

### 2.9 Web Search and Crawl Tool Scope

- [ ] Confirm that:
  - [ ] `webSearch` is only invoked from the activities service as a **fallback** (never as the primary provider).
  - [ ] `webSearchBatch` and Firecrawl crawl tools (for example, `crawlUrl`, `crawlSite`) are **not** used by `/api/activities/search` or `/api/activities/[id]` and remain reserved for higher-level agents.

## 3. Data Migrations

- [ ] Run database migration for `search_activities.source` constraint
- [ ] Verify no existing data conflicts with new constraint

## 4. Feature Flags / Rollout

- [ ] No feature flags needed (direct implementation)
- [ ] Consider gradual rollout if Google Places API costs are concern

## 5. Observability & Alerts

- [ ] Add telemetry spans for activity search operations
- [ ] Set up alerts for Google Places API error rate > 5%
- [ ] Monitor cache hit rate (target: > 60%), segmented by provider source (`googleplaces`, `ai_fallback`)
- [ ] Monitor search latency (target: p95 < 500ms)
- [ ] Monitor fallback invocation rate (target: tuned based on production data; should generally be a minority of traffic)

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
