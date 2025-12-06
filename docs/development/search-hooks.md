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
// Example simplified for clarity; imports (React, React Query, apiClient) omitted.
// AccommodationSearchResponse below is a sample response contract—replace with your real type.
type AccommodationSearchResponse = { results: Accommodation[] };
export function useAccommodationSearch() {
  const { updateAccommodationParams } = useSearchParamsStore();
  const { startSearch, setSearchResults, setSearchError, completeSearch } =
    useSearchResultsStore();
  const currentSearchIdRef = useRef<string | null>(null);
  const getSuggestions = useQuery({
    queryKey: ["accommodation-suggestions"],
    // Replace with your suggestions endpoint/client
    queryFn: () => apiClient.get<AccommodationSuggestion[]>("/accommodations/suggestions"),
    staleTime: 5 * 60 * 1000,
  });

  const searchMutation = useMutation({
    mutationFn: async (params: SearchAccommodationParams) => {
      const response = await apiClient.post<AccommodationSearchResponse>(
        "/accommodations/search",
        params
      );
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
      setSearchError(error as Error);
      setResults(null);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const resetSearch = useCallback(() => {
    setIsSearching(false);
    setSearchError(null);
    setResults(null);
    setSearchMetadata(null);
    // Optional: abort any in-flight request here.
  }, []);

  const saveSearch = useCallback((params: ActivitySearchParams) => {
    // Persist locally; replace with API call if needed.
    localStorage.setItem("latest-activity-search", JSON.stringify(params));
    setSearchMetadata((prev) => ({
      ...(prev ?? {}),
      savedAt: new Date().toISOString(),
      source: "local",
    }));
  }, []);

  return {
    isSearching,
    searchError,
    results,
    searchMetadata,
    searchActivities,
    resetSearch,
    saveSearch,
    // Add more helpers as needed (e.g., debounce, cache hydration)
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
// Example assumes a Google Places API key (e.g., from env) and a normalize helper.
export function useDestinationSearch() {
  const [results, setResults] = useState<Destination[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_PLACES_KEY;

  const normalizeGooglePlace = (place: GooglePlace): Destination => ({
    id: place.id,
    name: place.displayName.text,
    country: place.addressComponents?.country,
    formattedAddress: place.formattedAddress,
  });

  const search = useCallback(async (query: string) => {
    // Cancel previous request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    setIsSearching(true);
    setError(null);

    if (!apiKey) {
      setError(new Error("Google Places API key is not configured"));
      setIsSearching(false);
      return;
    }

    try {
      const response = await fetch(
        "https://places.googleapis.com/v1/places:searchText",
        {
          body: JSON.stringify({ textQuery: query }),
          headers: {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": apiKey,
          },
          method: "POST",
          signal: abortControllerRef.current.signal,
        }
      );

      const data = await response.json();
      // Normalize to internal Destination type
      const destinations = (data.places ?? []).map(normalizeGooglePlace);
      setResults(destinations);
    } catch (error) {
      if ((error as Error).name !== "AbortError") {
        setError(error as Error);
      }
    } finally {
      setIsSearching(false);
    }
  }, [apiKey]);

  return { results, search, isSearching, error };
}
```

If the same normalization logic is needed in other hooks, extract
`normalizeGooglePlace` into a shared utility to avoid duplication.

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
