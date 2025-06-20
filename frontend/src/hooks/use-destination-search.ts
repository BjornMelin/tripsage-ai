/**
 * Mock implementation of use-destination-search
 * This file exists to satisfy test imports that expect this module
 */

import { useState } from "react";

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

  const searchDestinations = async (_params: DestinationSearchParams) => {
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
  };

  const resetSearch = () => {
    setIsSearching(false);
    setSearchError(null);
  };

  return {
    searchDestinations,
    isSearching,
    searchError,
    resetSearch,
  };
}
