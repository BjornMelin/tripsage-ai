/**
 * @fileoverview React hook for accommodation search functionality.
 *
 * Provides hooks for searching accommodations, managing search parameters,
 * and handling search results with caching and error handling.
 */

"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { apiClient } from "@/lib/api/api-client";
import type { Accommodation, AccommodationSearchParams } from "@/lib/schemas/search";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";

export interface AccommodationSearchResponse {
  results: Accommodation[];
  totalResults: number;
  filters?: Record<string, string | number | boolean | string[]>;
  metadata?: Record<string, string | number | boolean | Record<string, unknown>>;
}

/**
 * Hook for accommodation search functionality.
 *
 * Provides methods for searching accommodations, managing search state,
 * and accessing search suggestions.
 *
 * @returns Object with search methods and state
 */
export function useAccommodationSearch() {
  const { updateAccommodationParams } = useSearchParamsStore();
  const { startSearch, setSearchResults, setSearchError, completeSearch } =
    useSearchResultsStore();

  const currentSearchIdRef = useRef<string | null>(null);

  const searchMutation = useMutation({
    mutationFn: async (params: AccommodationSearchParams) => {
      const response = await apiClient.post<
        AccommodationSearchParams,
        AccommodationSearchResponse
      >("/accommodations/search", params);
      return response;
    },
    onMutate: (params) => {
      currentSearchIdRef.current = startSearch("accommodation", { ...params } as Record<
        string,
        unknown
      >);
    },
  });

  // Handle search success
  useEffect(() => {
    if (searchMutation.data && currentSearchIdRef.current) {
      setSearchResults(currentSearchIdRef.current, {
        accommodations: searchMutation.data.results,
      });
      completeSearch(currentSearchIdRef.current);
    }
  }, [searchMutation.data, setSearchResults, completeSearch]);

  // Handle search error
  useEffect(() => {
    if (searchMutation.error && currentSearchIdRef.current) {
      setSearchError(currentSearchIdRef.current, {
        code: "SEARCH_ERROR",
        message: searchMutation.error.message || "Failed to search accommodations",
        occurredAt: new Date().toISOString(),
        retryable: true,
      });
    }
  }, [searchMutation.error, setSearchError]);

  const getSuggestions = useQuery({
    queryFn: async () => {
      const response = await apiClient.get<Accommodation[]>(
        "/accommodations/suggestions"
      );
      return response;
    },
    queryKey: ["accommodation-suggestions"],
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    isSearching: searchMutation.isPending,
    isSuggestionsLoading: getSuggestions.isLoading,
    search: searchMutation.mutate,
    searchAsync: searchMutation.mutateAsync,
    searchError: searchMutation.error,
    suggestions: getSuggestions.data,
    updateParams: updateAccommodationParams,
  };
}
