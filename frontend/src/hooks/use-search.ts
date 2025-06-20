/**
 * Mock implementation of use-search
 * This file exists to satisfy test imports that expect this module
 */

export interface UseSearchResult {
  search: (query: string) => Promise<void>;
  isSearching: boolean;
  results: any[];
  error: Error | null;
  clearSearch: () => void;
}

/**
 * Mock hook for general search functionality
 */
export function useSearch(): UseSearchResult {
  return {
    search: async () => {},
    isSearching: false,
    results: [],
    error: null,
    clearSearch: () => {},
  };
}
