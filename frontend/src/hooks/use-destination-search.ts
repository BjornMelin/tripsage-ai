/**
 * @fileoverview Hook for destination search state. Provides memoized actions
 * and loading/error state without performing network calls.
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
 * Hook surface for destination search.
 * @returns Actions and flags for destination search without side effects.
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
