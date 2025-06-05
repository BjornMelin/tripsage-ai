"use client";

import { api } from "@/lib/api/client";
import { useSearchStore } from "@/stores/search-store";
import type { Accommodation, AccommodationSearchParams } from "@/types/search";
import { useMutation, useQuery } from "@tanstack/react-query";

export interface AccommodationSearchResponse {
  results: Accommodation[];
  totalResults: number;
  filters?: Record<string, string | number | boolean | string[]>;
  metadata?: Record<string, string | number | boolean | Record<string, unknown>>;
}

export function useAccommodationSearch() {
  const { updateAccommodationParams, setResults, setIsLoading, setError } =
    useSearchStore();

  const searchMutation = useMutation({
    mutationFn: async (params: AccommodationSearchParams) => {
      const response = await api.post<AccommodationSearchResponse>(
        "/api/accommodations/search",
        params
      );
      return response;
    },
    onSuccess: (data) => {
      setResults({ accommodations: data.results });
      setIsLoading(false);
    },
    onError: (error: Error) => {
      setError(error.message || "Failed to search accommodations");
      setIsLoading(false);
    },
    onMutate: () => {
      setIsLoading(true);
      setError(null);
    },
  });

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
