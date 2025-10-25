/**
 * @fileoverview Hook for activity search state. Exposes search/save methods,
 * loading flags, errors, and cached lists without performing side effects.
 */

import type { ActivitySearchParams } from "@/types/search";

export type { ActivitySearchParams };

export interface UseActivitySearchResult {
  searchActivities: (params: ActivitySearchParams) => Promise<void>;
  isSearching: boolean;
  searchError: Error | null;
  resetSearch: () => void;
  saveSearch: (name: string, params: ActivitySearchParams) => Promise<void>;
  savedSearches: any[];
  popularActivities: any[];
  isSavingSearch: boolean;
  saveSearchError: Error | null;
}

/**
 * Hook surface for activity search.
 * @returns Stable actions, flags, and caches for activity search.
 */
export function useActivitySearch(): UseActivitySearchResult {
  return {
    searchActivities: async () => {},
    isSearching: false,
    searchError: null,
    resetSearch: () => {},
    saveSearch: async () => {},
    savedSearches: [],
    popularActivities: [],
    isSavingSearch: false,
    saveSearchError: null,
  };
}
