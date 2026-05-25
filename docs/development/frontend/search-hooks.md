# Search Hooks Patterns

This document describes the intentional pattern differences in search hooks and when to use each approach.

## Overview

The TripSage search domain uses three distinct client patterns, each optimized for different use cases:

| Pattern | Surface | Best For |
|---------|---------|----------|
| Route-backed orchestration | `useSearchOrchestration` | Flight, hotel, and activity searches through API routes and Zustand stores |
| Server action validation + client execution | `submitActivitySearch` + `ActivitiesSearchClient` | Page flows that need server-side validation before client fetch/store updates |
| External API integration | `useDestinationSearch` | Third-party APIs via BFF routes (`/api/places/**`) |

## Pattern 1: Route-Backed Orchestration

**Example:** `useSearchOrchestration`

**Characteristics:**

- Initializes the active search type across params and filters stores.
- Executes route-backed searches through `SEARCH_ENDPOINTS`.
- Maps route responses into `SearchResults`.
- Tracks search lifecycle, metrics, errors, history, and retry state in Zustand stores.

**Dependencies:**

- `search-params-store`
- `search-filters-store`
- `search-results-store`
- `search-history-store`

**Use when:**

- Building route-backed flight, hotel, or activity pages.
- Results need to participate in global search state, filters, history, retry, or saved-search flows.
- The route response needs mapping into the shared `SearchResults` shape.

**Code pattern:**

```typescript
const { initializeSearch, executeSearch, isSearching } = useSearchOrchestration();

useEffect(() => {
  initializeSearch("activity");
}, [initializeSearch]);

async function handleSearch(params: ActivitySearchParams, signal?: AbortSignal) {
  await executeSearch(params, signal);
}
```

## Pattern 2: Server Action Validation + Client Execution

**Example:** activity search page flow

**Characteristics:**

- Uses a Server Action for validation and telemetry.
- Executes the route-backed search on the client through `useSearchOrchestration`.
- Uses an `AbortController` to cancel stale requests.
- Keeps page-local UI state, such as selected activity and trip-selection modal state, inside the page client component.

**Dependencies:**

- `src/app/(app)/dashboard/search/activities/actions.ts`
- `src/app/(app)/dashboard/search/activities/activities-search-client.tsx`
- `useSearchOrchestration`
- `useAbortableSearchTask`

**Use when:**

- Search params need server-side validation or telemetry before execution.
- The page needs route-backed results plus page-specific UI state.
- The flow must prevent stale in-flight searches from updating the UI.

**Code pattern:**

```typescript
const { executeSearch } = useSearchOrchestration();
const { clearSearchController, startSearchController } = useAbortableSearchTask();

const handleSearch = useCallback(async (params: ActivitySearchParams) => {
  const controller = startSearchController();
  try {
    const normalizedParams = await onSubmitServer(params);
    if (controller.signal.aborted || !normalizedParams.ok) return;

    await executeSearch(normalizedParams.data, controller.signal);
  } finally {
    clearSearchController(controller);
  }
}, [clearSearchController, executeSearch, onSubmitServer, startSearchController]);
```

## Pattern 3: External API Integration

**Example:** `useDestinationSearch`

**Characteristics:**

- Uses AbortController for request cancellation
- Implements debouncing for text input
- Normalizes external API responses to internal types
- Calls server BFF routes (secrets stay server-only)

**Dependencies:**

- `AbortController` for cancellation
- Optional debounce utility
- Result normalization functions

**Use when:**

- Integrating with third-party APIs via server routes (Google Places, Amadeus, etc.)
- Need request cancellation for typeahead/autocomplete
- Response format differs from internal types
- API has unique rate-limiting requirements.

**Code pattern:**

```typescript
// Example uses the Places BFF route (`/api/places/search`) and normalizes to internal types.
const normalizePlace = (place: PlaceSummary): Destination => ({
  formattedAddress: place.formattedAddress,
  id: place.placeId,
  name: place.name,
});

export function useDestinationSearch() {
  const [results, setResults] = useState<Destination[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const search = useCallback(async (query: string) => {
    // Cancel previous request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    setIsSearching(true);
    setError(null);

    try {
      const response = await fetch(
        "/api/places/search",
        {
          body: JSON.stringify({ textQuery: query }),
          headers: {
            "Content-Type": "application/json",
          },
          method: "POST",
          signal: abortControllerRef.current.signal,
        }
      );

      const data = await response.json();
      // Normalize to internal Destination type
      const destinations = (data.places ?? []).map(normalizePlace);
      setResults(destinations);
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        setError(error as Error);
      }
    } finally {
      setIsSearching(false);
    }
  }, []);

  return { results, search, isSearching, error };
}
```

If the same normalization logic is needed in other hooks, extract
`normalizePlace` into a shared utility to avoid duplication.

## Decision Guide

### Default to Pattern 1 (Route-Backed Orchestration)

Use for new search types when:

- Building primary search flows
- Need route-backed execution and shared result mapping
- Want integration with search history and saved searches
- Need consistent error handling, metrics, and retry state

### Use Pattern 2 (Server Action Validation + Client Execution) when

- Server-side validation, auth-aware lookups, or telemetry should happen before client execution.
- Page-local UI state is larger than the shared search result state.
- Stale in-flight requests must be explicitly cancelled.

### Use Pattern 3 (External API) when

- Integrating with third-party services
- Need request cancellation (autocomplete, typeahead)
- Response normalization is required
- API has unique authentication or rate limiting

## Related Components

### SearchFormShell

Use `SearchFormShell` component for consistent form handling:

```typescript
import { SearchFormShell } from "@/features/search/components/common/search-form-shell";

<SearchFormShell
  form={form}
  onSubmit={handleSearch}
  telemetrySpanName="flight.search"
>
  {(form) => (
    <>
      <FormField name="origin" control={form.control} ... />
      <FormField name="destination" control={form.control} ... />
    </>
  )}
</SearchFormShell>
```

### Cross-Store Selectors

Use cross-store selectors for unified state access:

```typescript
import { useSearchOrchestration } from "@/features/search/hooks/search/use-search-orchestration";
import {
  useActiveFilterCount,
  useHasActiveFilters,
} from "@/features/search/store/search-filters-store";
import {
  useSearchParamsValidation,
  useSearchType,
} from "@/features/search/store/search-params-store";

function SearchDashboard() {
  const { getSearchSummary, isSearching } = useSearchOrchestration();
  const searchType = useSearchType();
  const filterCount = useActiveFilterCount();
  const hasFilters = useHasActiveFilters();
  const { hasValidParams, validationErrors } = useSearchParamsValidation();
  const summary = getSearchSummary();

  // Unified view of search state from multiple stores
}
```

## Store Integration

All search hooks should integrate with these stores:

| Store | Purpose |
|-------|---------|
| `search-params-store` | Search type and parameters |
| `search-filters-store` | Active filters and sort options |
| `search-results-store` | Search results and status |
| `search-history-store` | Recent and saved searches |

Use `useSearchOrchestration` hook for high-level operations that coordinate across stores.
