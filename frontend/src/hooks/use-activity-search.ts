/**
 * Mock implementation of use-activity-search
 * This file exists to satisfy test imports that expect this module
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
 * Mock hook for activity search functionality
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
