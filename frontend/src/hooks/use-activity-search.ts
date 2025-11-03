/**
 * @fileoverview Mock implementation of activity search hook.
 *
 * Placeholder implementation for activity search functionality.
 * Provides interface for search methods and state management.
 */

import type { Activity, ActivitySearchParams, SavedSearch } from "@/types/search";

export type { ActivitySearchParams };

export interface UseActivitySearchResult {
  searchActivities: (params: ActivitySearchParams) => Promise<void>;
  isSearching: boolean;
  searchError: Error | null;
  resetSearch: () => void;
  saveSearch: (name: string, params: ActivitySearchParams) => Promise<void>;
  savedSearches: SavedSearch[];
  popularActivities: Activity[];
  isSavingSearch: boolean;
  saveSearchError: Error | null;
}

/**
 * Hook for activity search functionality.
 *
 * @returns Object with search methods and state
 */
export function useActivitySearch(): UseActivitySearchResult {
  return {
    isSavingSearch: false,
    isSearching: false,
    popularActivities: [],
    resetSearch: () => {},
    savedSearches: [],
    saveSearch: async () => {},
    saveSearchError: null,
    searchActivities: async () => {},
    searchError: null,
  };
}
