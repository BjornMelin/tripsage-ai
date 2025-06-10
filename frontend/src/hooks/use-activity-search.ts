"use client";

import { api } from "@/lib/api/client";
import { useSearchStore } from "@/stores/search-store";
import type { ActivitySearchParams, SearchResponse } from "@/types/search";
import { useMutation, useQuery } from "@tanstack/react-query";

interface ActivitySearchResponse extends SearchResponse {
  results: {
    activities?: Array<{
      id: string;
      name: string;
      type: string;
      location: string;
      date: string;
      duration: number;
      price: number;
      rating: number;
      description: string;
      images: string[];
      coordinates?: {
        lat: number;
        lng: number;
      };
    }>;
  };
}

export function useActivitySearch() {
  const { updateActivityParams, setResults, setIsLoading, setError } = useSearchStore();

  // Mutation for searching activities
  const searchMutation = useMutation({
    mutationFn: async (params: ActivitySearchParams) => {
      const response = await api.post<ActivitySearchResponse>(
        "/api/activities/search",
        params
      );
      return response;
    },
    onMutate: () => {
      setIsLoading(true);
      setError(null);
    },
    onSuccess: (data) => {
      setResults({
        activities: data.results.activities || [],
      });
      setIsLoading(false);
    },
    onError: (error) => {
      console.error("Activity search failed:", error);
      setError("Failed to search activities. Please try again.");
      setIsLoading(false);
    },
  });

  // Query for saved activity searches
  const savedSearchesQuery = useQuery({
    queryKey: ["saved-activity-searches"],
    queryFn: async () => {
      const response = await api.get("/api/activities/saved-searches");
      return response;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Function to save an activity search
  const saveSearchMutation = useMutation({
    mutationFn: async (params: {
      name: string;
      searchParams: ActivitySearchParams;
    }) => {
      const response = await api.post("/api/activities/save-search", params);
      return response;
    },
    onSuccess: () => {
      savedSearchesQuery.refetch();
    },
  });

  // Function to get popular activities for a destination
  const popularActivitiesQuery = useQuery({
    queryKey: ["popular-activities"],
    queryFn: async () => {
      const response = await api.get("/api/activities/popular");
      return response;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes
  });

  const searchActivities = (params: ActivitySearchParams) => {
    updateActivityParams(params);
    searchMutation.mutate(params);
  };

  const saveSearch = (name: string, searchParams: ActivitySearchParams) => {
    saveSearchMutation.mutate({ name, searchParams });
  };

  return {
    // Search functions
    searchActivities,
    saveSearch,

    // Search state
    isSearching: searchMutation.isPending,
    searchError: searchMutation.error,

    // Saved searches
    savedSearches: savedSearchesQuery.data || [],
    isLoadingSavedSearches: savedSearchesQuery.isLoading,

    // Popular activities
    popularActivities: popularActivitiesQuery.data || [],
    isLoadingPopularActivities: popularActivitiesQuery.isLoading,

    // Save search state
    isSavingSearch: saveSearchMutation.isPending,
    saveSearchError: saveSearchMutation.error,
  };
}
