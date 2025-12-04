# Search Hooks Patterns

This document describes the intentional pattern differences in search hooks and when to use each approach.

## Overview

The TripSage search domain uses three distinct hook patterns, each optimized for different use cases:

| Pattern | Hook | Best For |
|---------|------|----------|
| React Query Integration | `useAccommodationSearch` | Store-integrated searches with caching |
| Self-Contained State | `useActivitySearch` | Searches with custom metadata |
| External API Integration | `useDestinationSearch` | Third-party APIs (Google Places) |

## Pattern 1: React Query Integration

**Example:** `useAccommodationSearch`

**Characteristics:**

- Uses `useMutation` for search operations
- Uses `useQuery` for suggestions with stale time caching
- Integrates with `search-params-store` and `search-results-store`
- Tracks search lifecycle in Zustand stores

**Dependencies:**

- `@tanstack/react-query`
- `search-params-store`
- `search-results-store`

**Use when:**

- Search results should be cached
- Need integration with centralized store state
- Want automatic retry and error handling from React Query
- Building a primary search flow

**Code pattern:**

```typescript
export function useAccommodationSearch() {
  const { updateAccommodationParams } = useSearchParamsStore();
  const { startSearch, setSearchResults, setSearchError, completeSearch } =
    useSearchResultsStore();

  const searchMutation = useMutation({
    mutationFn: async (params: SearchAccommodationParams) => {
      const response = await apiClient.post<...>("/accommodations/search", params);
      return response;
    },
    onMutate: (params) => {
      // Track in store
      currentSearchIdRef.current = startSearch("accommodation", { ...params });
    },
  });

  // Handle success/error in useEffect to update stores
  useEffect(() => {
    if (searchMutation.data && currentSearchIdRef.current) {
      setSearchResults(currentSearchIdRef.current, {
        accommodations: searchMutation.data.results,
      });
      completeSearch(currentSearchIdRef.current);
    }
  }, [searchMutation.data, setSearchResults, completeSearch]);

  return {
    isSearching: searchMutation.isPending,
    search: searchMutation.mutate,
    searchAsync: searchMutation.mutateAsync,
    searchError: searchMutation.error,
    suggestions: getSuggestions.data,
    updateParams: updateAccommodationParams,
  };
}
```

## Pattern 2: Self-Contained State

**Example:** `useActivitySearch`

**Characteristics:**

- Uses local `useState` for all state management
- Provides custom metadata beyond results (source, cached flag)
- Direct fetch calls without React Query
- More control over state transitions

**Dependencies:**

- React `useState`, `useCallback`
- No external state library required

**Use when:**

- Need custom metadata tracking (e.g., data source, cache status)
- Search is self-contained and doesn't need global coordination
- Want simpler state management without query library
- Building secondary or specialized search flows

**Code pattern:**

```typescript
export function useActivitySearch(): UseActivitySearchResult {
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<Error | null>(null);
  const [results, setResults] = useState<Activity[] | null>(null);
  const [searchMetadata, setSearchMetadata] = useState<Metadata | null>(null);

  const searchActivities = useCallback(async (params: ActivitySearchParams) => {
    setIsSearching(true);
    setSearchError(null);

    try {
      const response = await fetch("/api/activities/search", {
        body: JSON.stringify(params),
        method: "POST",
      });

      const data = await response.json();
      setResults(data.activities);
      setSearchMetadata(data.metadata);
    } catch (error) {
      setSearchError(error);
      setResults(null);
    } finally {
      setIsSearching(false);
    }
  }, []);

  return {
    isSearching,
    searchError,
    results,
    searchMetadata,
    searchActivities,
    resetSearch,
    saveSearch,
    // ... other methods
  };
}
```

## Pattern 3: External API Integration

**Example:** `useDestinationSearch`

**Characteristics:**

- Uses AbortController for request cancellation
- Implements debouncing for text input
- Normalizes external API responses to internal types
- Handles API-specific authentication

**Dependencies:**

- `AbortController` for cancellation
- Optional debounce utility
- Result normalization functions

**Use when:**

- Integrating with third-party APIs (Google Places, Amadeus, etc.)
- Need request cancellation for typeahead/autocomplete
- Response format differs from internal types
- API has unique rate limiting or auth requirements

**Code pattern:**

```typescript
export function useDestinationSearch() {
  const [results, setResults] = useState<Destination[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const search = useCallback(async (query: string) => {
    // Cancel previous request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(
        `https://places.googleapis.com/v1/places:searchText`,
        {
          body: JSON.stringify({ textQuery: query }),
          headers: {
            "X-Goog-Api-Key": apiKey,
          },
          method: "POST",
          signal: abortControllerRef.current.signal,
        }
      );

      const data = await response.json();
      // Normalize to internal Destination type
      const destinations = data.places.map(normalizeGooglePlace);
      setResults(destinations);
    } catch (error) {
      if (error.name !== "AbortError") {
        setError(error);
      }
    }
  }, []);

  return { results, search, isSearching, error };
}
```

## Decision Guide

### Default to Pattern 1 (React Query)

Use for new search types when:

- Building primary search flows
- Need caching and automatic background refetching
- Want integration with search history and saved searches
- Need consistent error handling and retry logic

### Use Pattern 2 (Self-Contained) when

- Metadata tracking is important (source, cache status, timing)
- Search is specialized and standalone
- Want full control over state transitions
- Avoiding React Query dependency for simplicity

### Use Pattern 3 (External API) when

- Integrating with third-party services
- Need request cancellation (autocomplete, typeahead)
- Response normalization is required
- API has unique authentication or rate limiting

## Related Components

### SearchFormShell

Use `SearchFormShell` component for consistent form handling:

```typescript
import { SearchFormShell } from "@/components/features/search/common/search-form-shell";

<SearchFormShell
  schema={flightSearchSchema}
  defaultValues={{ origin: "", destination: "" }}
  onSubmit={handleSearch}
  telemetrySpanName="flight.search"
  popularItems={popularDestinations}
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
import {
  useSearchSummary,
  useActiveFiltersSummary,
  useSearchValidation,
} from "@/stores/selectors/search-selectors";

function SearchDashboard() {
  const { searchType, resultCount, isSearching } = useSearchSummary();
  const { count: filterCount, hasFilters } = useActiveFiltersSummary();
  const { isValid, paramsErrors } = useSearchValidation();

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
