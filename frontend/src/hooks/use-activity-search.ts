/**
 * @fileoverview Minimal final implementation for `useActivitySearch` hook.
 * Provides stable, no-op behaviors for search/save operations to align with
 * the current UI while legacy API/store behaviors have been removed.
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
 * Hook surface for activity search. This final version intentionally avoids
 * side effects and external dependencies. Callers can compose behavior using
 * higher-level services or feature stores.
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
