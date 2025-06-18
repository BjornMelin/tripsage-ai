/**
 * Mock implementation of use-activity-search
 * This file exists to satisfy test imports that expect this module
 */

export interface ActivitySearchParams {
  destination: string;
  category?: string;
  priceRange?: [number, number];
}

export interface UseActivitySearchResult {
  searchActivities: (params: ActivitySearchParams) => Promise<void>;
  isSearching: boolean;
  searchError: Error | null;
  resetSearch: () => void;
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
  };
}
