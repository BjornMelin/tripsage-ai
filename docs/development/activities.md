# Activities Developer Guide

Activity search and booking via Google Places API (New) with optional AI/web fallback. See SPEC-0030 and ADR-0053 for architecture details.

## Overview

The activities feature provides:

- **Search**: Find activities (tours, experiences, attractions) by destination, category, date, and filters
- **Details**: Retrieve comprehensive activity information (photos, ratings, descriptions, location)
- **Hybrid Provider Model**: Google Places API (New) as primary deterministic provider, with guarded AI/web fallback

## Architecture

### Service Layer

**File**: `frontend/src/domain/activities/service.ts`

The `ActivitiesService` is a pure, DI-friendly orchestrator:

```typescript
import { getActivitiesService } from "@domain/activities/container";

const service = getActivitiesService();

// Search activities
const result = await service.search(
  {
    destination: "Paris",
    category: "museums",
    date: "2025-06-15",
  },
  { userId: "user-123" }
);

// Get activity details
const activity = await service.details("ChIJN1t_tDeuEmsRUsoyG83frY4", {
  userId: "user-123",
});
```

**Key Features:**

- Supabase-backed caching (`search_activities` table)
- Google Places API (New) integration with field masks
- Heuristically-gated AI/web fallback
- Telemetry spans for observability

### API Routes

**Search**: `POST /api/activities/search`

```typescript
// Request
const response = await fetch("/api/activities/search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    destination: "Paris",
    category: "museums",
    adults: 2,
  }),
});

// Response
const data = await response.json();
// {
//   activities: Activity[],
//   metadata: {
//     total: number,
//     cached: boolean,
//     primarySource: "googleplaces" | "ai_fallback" | "mixed",
//     sources: Array<"googleplaces" | "ai_fallback" | "cached">,
//     notes?: string[]
//   }
// }
```

**Details**: `GET /api/activities/[id]`

```typescript
const response = await fetch("/api/activities/ChIJN1t_tDeuEmsRUsoyG83frY4");
const activity = await response.json(); // Activity object
```

**Rate Limits:**

- Search: 20 requests per minute
- Details: 30 requests per minute

**Authentication**: Optional (anonymous searches allowed)

### AI SDK v6 Tools

**File**: `frontend/src/ai/tools/server/activities.ts`

Tools are registered in `frontend/src/ai/tools/index.ts` and available to chat/agents:

```typescript
import { searchActivities, getActivityDetails } from "@ai/tools/server/activities";

// In chat route or agent
const result = await searchActivities.execute({
  destination: "Tokyo",
  category: "tours",
});
```

**Available Tools:**

- `searchActivities` - Search with Google Places + optional AI fallback
- `getActivityDetails` - Retrieve activity details by Place ID
- `bookActivity` - Placeholder (deferred - no partner APIs)

**Tool Features:**

- Zod schema validation
- Rate limiting (via `createAiTool` guardrails)
- Telemetry spans
- Error handling

## Data Models

### Activity Search Parameters

```typescript
import type { ActivitySearchParams } from "@schemas/search";

const params: ActivitySearchParams = {
  destination: "Paris", // Required
  category: "museums", // Optional
  date: "2025-06-15", // Optional ISO date string
  adults: 2, // Optional (1-20)
  children: 1, // Optional (0-20)
  infants: 0, // Optional (0-20)
  duration: {
    min: 60, // Optional minutes
    max: 240, // Optional minutes
  },
  difficulty: "easy", // Optional: "easy" | "moderate" | "challenging" | "extreme"
  indoor: true, // Optional boolean
};
```

### Activity Schema

```typescript
import type { Activity } from "@schemas/search";

const activity: Activity = {
  id: "ChIJN1t_tDeuEmsRUsoyG83frY4", // Google Place ID
  name: "Museum of Modern Art",
  description: "A great museum experience",
  location: "11 W 53rd St, New York, NY 10019",
  coordinates: {
    lat: 40.7614,
    lng: -73.9776,
  },
  rating: 4.6, // 0-5
  price: 2, // Price index: 0=free, 1=inexpensive, 2=moderate, 3=expensive, 4=very expensive
  type: "museum", // Activity category
  duration: 120, // Minutes
  date: "2025-06-15", // ISO date string
  images: ["https://..."], // Optional array of image URLs
};
```

## Caching Strategy

**Supabase `search_activities` Table:**

- **Primary Results** (Google Places): 24-hour TTL
- **Fallback Results** (AI/web): 6-hour TTL
- **Cache Key**: Normalized `query_hash` computed from search parameters
- **Source Tracking**: `source` field distinguishes `googleplaces`, `ai_fallback`, `cached`

**Cache Lookup:**

1. Compute normalized `query_hash` from search parameters
2. Check `search_activities` for matching row with `expires_at > now()`
3. Return cached results if found
4. Otherwise, call Google Places API and persist results

## Fallback Behavior

**Heuristic Triggers:**

- Zero Places results, or
- Very few Places results (< 3) for popular destinations, or
- Explicit user intent for "off the beaten path" content

**Fallback Process:**

1. Invoke `webSearch` tool with compact query (`"things to do in {destination}"`)
2. Normalize web search results into `Activity[]` format
3. Label as `source = 'ai_fallback'`
4. Persist with shorter TTL (6 hours)
5. Return combined results with metadata indicating sources

**Important:** AI fallback results are clearly labeled and should not be used for booking or treated as authoritative.

## Google Places Integration

**Field Masks** (cost optimization):

- **Search**: `places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types,places.priceLevel`
- **Details**: `id,displayName,formattedAddress,location,rating,userRatingCount,photos,types,editorialSummary,regularOpeningHours,priceLevel`

**Query Construction:**

```typescript
import { buildActivitySearchQuery } from "@/lib/google/places-activities";

const query = buildActivitySearchQuery("Paris", "museums");
// Returns: "museums activities in Paris"
```

**Photo URLs:**

Photo names from Places API are returned as identifiers. Full URL resolution can be done via `GET /v1/{photoName}` if needed.

## React Hook

**File**: `frontend/src/hooks/use-activity-search.ts`

```typescript
import { useActivitySearch } from "@/hooks/use-activity-search";

function ActivitySearchComponent() {
  const {
    searchActivities,
    isSearching,
    searchError,
    results,
    searchMetadata,
    resetSearch,
  } = useActivitySearch();

  const handleSearch = async () => {
    await searchActivities({
      destination: "Paris",
      category: "museums",
    });
  };

  return (
    <div>
      {isSearching && <p>Searching...</p>}
      {searchError && <p>Error: {searchError.message}</p>}
      {results?.map((activity) => (
        <ActivityCard key={activity.id} activity={activity} />
      ))}
    </div>
  );
}
```

## Testing

**Service Layer Tests**: `frontend/src/domain/activities/__tests__/service.test.ts`

- Cache hit/miss behavior
- Google Places integration
- AI fallback heuristics
- Error handling

**API Route Tests**: `frontend/src/app/api/activities/__tests__/route.test.ts`

- Authentication and rate limiting
- Request-response formats
- Error handling

**Tool Tests**: `frontend/src/ai/tools/server/__tests__/activities.test.ts`

- Tool execution
- Schema validation
- Error mapping

**Hook Tests**: `frontend/src/hooks/__tests__/use-activity-search.test.tsx`

- Hook behavior
- API integration
- State management

**MSW Handlers**: `frontend/src/test/msw/handlers/google-places.ts`

- Mock Google Places API responses
- Activity-specific search responses

## Observability

**Telemetry Spans:**

- `activities.search` - Activity search operation
- `activities.details` - Activity details retrieval
- `activities.cache.hit` - Cache hit event
- `activities.cache.miss` - Cache miss event
- `activities.google_places.api` - Google Places API call
- `activities.fallback.invoked` - AI/web fallback triggered
- `activities.fallback.suppressed` - Fallback conditions not met

**Logging:**

- Use `createServerLogger("activities.service")` for service layer logs
- Log sanitized search parameters, result counts, cache decisions
- Log Google Places API errors with status codes

## Error Handling

**Service Layer:**

- Validates `destination` is required
- Validates Place ID format for details
- Handles Google Places API errors gracefully
- Falls back to AI/web search when appropriate

**API Routes:**

- Return 400 for invalid requests
- Return 404 for not found activities
- Return 429 for rate limit exceeded
- Return 500 for internal errors

**Tools:**

- Map domain errors to standardized tool errors
- Include error codes for programmatic handling

## Rate Limiting

Rate limits are configured in `frontend/src/lib/ratelimit/routes.ts`:

- `activities:search`: 20 requests per minute
- `activities:details`: 30 requests per minute

Limits are enforced via Upstash Redis and `withApiGuards` factory.

## Related Documentation

- **SPEC-0030**: Activity Search & Booking - Functional & Technical Spec
- **ADR-0053**: Activity Search & Booking via Google Places API Integration
- **API Reference**: `docs/api/api-reference.md`
