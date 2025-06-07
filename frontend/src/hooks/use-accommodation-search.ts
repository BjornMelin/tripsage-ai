"use client";

import { api } from "@/lib/api/client";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import type { Accommodation, AccommodationSearchParams } from "@/types/search";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

export interface AccommodationSearchResponse {
  results: Accommodation[];
  totalResults: number;
  filters?: Record<string, string | number | boolean | string[]>;
  metadata?: Record<string, string | number | boolean | Record<string, unknown>>;
}

export function useAccommodationSearch() {
  const { updateAccommodationParams } = useSearchParamsStore();
  const { startSearch, setSearchResults, setSearchError, completeSearch } =
    useSearchResultsStore();

  let currentSearchId: string | null = null;

  const searchMutation = useMutation({
    mutationFn: async (params: AccommodationSearchParams) => {
      const response = await api.post<AccommodationSearchResponse>(
        "/api/accommodations/search",
        params
      );
      return response;
    },
    onMutate: (params) => {
      currentSearchId = startSearch("accommodation", { ...params } as Record<
        string,
        unknown
      >);
    },
  });

  // Handle search success
  useEffect(() => {
    if (searchMutation.data && currentSearchId) {
      setSearchResults(currentSearchId, {
        accommodations: searchMutation.data.results,
      });
      completeSearch(currentSearchId);
    }
  }, [searchMutation.data, currentSearchId, setSearchResults, completeSearch]);

  // Handle search error
  useEffect(() => {
    if (searchMutation.error && currentSearchId) {
      setSearchError(currentSearchId, {
        message: searchMutation.error.message || "Failed to search accommodations",
        code: "SEARCH_ERROR",
        occurredAt: new Date().toISOString(),
        retryable: true,
      });
    }
  }, [searchMutation.error, currentSearchId, setSearchError]);

  const getSuggestions = useQuery({
    queryKey: ["accommodation-suggestions"],
    queryFn: async () => {
      const response = await api.get<Accommodation[]>(
        "/api/accommodations/suggestions"
      );
      return response;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    search: searchMutation.mutate,
    searchAsync: searchMutation.mutateAsync,
    isSearching: searchMutation.isPending,
    searchError: searchMutation.error,
    suggestions: getSuggestions.data,
    isSuggestionsLoading: getSuggestions.isLoading,
    updateParams: updateAccommodationParams,
  };
}
