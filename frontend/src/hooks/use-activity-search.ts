/**
 * @fileoverview Activity search hook implementation.
 *
 * Provides search functionality, state management, and error handling for
 * activity searches via the /api/activities/search endpoint.
 */

import type { Activity, ActivitySearchParams, SavedSearch } from "@schemas/search";
import { useCallback, useState } from "react";

export type { ActivitySearchParams };

/**
 * Activity search result with metadata.
 */
interface ActivitySearchResponse {
  activities: Activity[];
  metadata: {
    total: number;
    cached: boolean;
    primarySource: "googleplaces" | "ai_fallback" | "mixed";
    sources: Array<"googleplaces" | "ai_fallback" | "cached">;
    notes?: string[];
  };
}

/**
 * Interface defining the return type of the useActivitySearch hook.
 */
export interface UseActivitySearchResult {
  /** Function to search for activities with given parameters. */
  searchActivities: (params: ActivitySearchParams) => Promise<void>;
  /** Indicates whether a search operation is currently in progress. */
  isSearching: boolean;
  /** Error that occurred during the last search operation, if any. */
  searchError: Error | null;
  /** Current search results. */
  results: Activity[] | null;
  /** Search metadata. */
  searchMetadata: ActivitySearchResponse["metadata"] | null;
  /** Function to reset the current search state. */
  resetSearch: () => void;
  /** Function to save a search with a given name and parameters. */
  saveSearch: (name: string, params: ActivitySearchParams) => void;
  /** Array of saved searches. */
  savedSearches: SavedSearch[];
  /** Array of popular activities. */
  popularActivities: Activity[];
  /** Indicates whether a save search operation is currently in progress. */
  isSavingSearch: boolean;
  /** Error that occurred during the last save search operation, if any. */
  saveSearchError: Error | null;
}

/**
 * Hook for activity search functionality.
 *
 * Manages search state, calls the API endpoint, and handles errors.
 *
 * @return Object containing search methods and state management properties.
 */
export function useActivitySearch(): UseActivitySearchResult {
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<Error | null>(null);
  const [results, setResults] = useState<Activity[] | null>(null);
  const [searchMetadata, setSearchMetadata] = useState<
    ActivitySearchResponse["metadata"] | null
  >(null);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [popularActivities] = useState<Activity[]>([]);
  const [isSavingSearch, setIsSavingSearch] = useState(false);
  const [saveSearchError, setSaveSearchError] = useState<Error | null>(null);

  const searchActivities = useCallback(async (params: ActivitySearchParams) => {
    setIsSearching(true);
    setSearchError(null);

    try {
      const response = await fetch("/api/activities/search", {
        body: JSON.stringify(params),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.reason ?? `Search failed with status ${response.status}`
        );
      }

      const data = (await response.json()) as ActivitySearchResponse;
      setResults(data.activities);
      setSearchMetadata(data.metadata);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      setSearchError(err);
      setResults(null);
      setSearchMetadata(null);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const resetSearch = useCallback(() => {
    setResults(null);
    setSearchMetadata(null);
    setSearchError(null);
    setIsSearching(false);
  }, []);

  const saveSearch = useCallback((name: string, params: ActivitySearchParams) => {
    setIsSavingSearch(true);
    setSaveSearchError(null);

    try {
      // TODO: Implement save search functionality (persist to Supabase)
      // For now, just store in local state
      const saved: SavedSearch = {
        createdAt: new Date().toISOString(),
        id: `saved-${Date.now()}`,
        name,
        params,
        type: "activity",
      };
      setSavedSearches((prev) => [...prev, saved]);
      setIsSavingSearch(false);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      setSaveSearchError(err);
      setIsSavingSearch(false);
    }
  }, []);

  return {
    isSavingSearch,
    isSearching,
    popularActivities,
    resetSearch,
    results,
    savedSearches,
    saveSearch,
    saveSearchError,
    searchActivities,
    searchError,
    searchMetadata,
  };
}
