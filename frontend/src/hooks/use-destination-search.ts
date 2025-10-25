/**
 * @fileoverview Minimal final implementation for `useDestinationSearch` hook.
 * Exposes stable, memoized actions and loading/error state. External side
 * effects and network calls are intentionally excluded in this final version.
 */

import { useCallback, useState } from "react";

export interface DestinationSearchParams {
  query: string;
  types?: string[];
  limit?: number;
}

export interface UseDestinationSearchResult {
  searchDestinations: (params: DestinationSearchParams) => Promise<void>;
  isSearching: boolean;
  searchError: Error | null;
  resetSearch: () => void;
}

/**
 * Mock hook for destination search functionality
 */
export function useDestinationSearch(): UseDestinationSearchResult {
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<Error | null>(null);

  const searchDestinations = useCallback(async (_params: DestinationSearchParams) => {
    setIsSearching(true);
    setSearchError(null);
    try {
      // Mock implementation
      await new Promise((resolve) => setTimeout(resolve, 100));
    } catch (error) {
      setSearchError(error as Error);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const resetSearch = useCallback(() => {
    setIsSearching(false);
    setSearchError(null);
  }, []);

  return {
    searchDestinations,
    isSearching,
    searchError,
    resetSearch,
  };
}
