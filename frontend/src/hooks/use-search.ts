"use client";

import { useApiMutation, useApiQuery } from "@/hooks/use-api-query";
import { useSearchStore } from "@/stores/search-store";
import type {
  AccommodationSearchParams,
  ActivitySearchParams,
  FlightSearchParams,
  SavedSearch,
  SearchParams,
  SearchResponse,
  SearchResults,
  SearchType,
} from "@/types/search";
import { useCallback } from "react";

/**
 * Hook for searching flights, accommodations, and activities
 */
export function useSearch() {
  const {
    currentSearchType,
    currentParams,
    results,
    isLoading,
    error,
    activeFilters,
    activeSortOption,
    setSearchType,
    updateFlightParams,
    updateAccommodationParams,
    updateActivityParams,
    resetParams,
    setResults,
    setIsLoading,
    setError,
    clearResults,
    setActiveFilter,
    clearFilters,
    setActiveSortOption,
    addRecentSearch,
  } = useSearchStore();

  // Search mutation
  const searchMutation = useApiMutation<
    SearchResponse,
    { type: SearchType; params: SearchParams }
  >("/api/search", {
    onSuccess: (data) => {
      setResults(data.results);
      // Add to recent searches
      addRecentSearch();
    },
    onError: (error: any) => {
      setError(error.message || "Failed to perform search");
    },
  });

  // Function to start a search
  const search = useCallback(() => {
    if (!currentSearchType || !currentParams) {
      setError("Search type or parameters not set");
      return;
    }

    setIsLoading(true);
    clearResults();

    // Apply any active filters to the search params
    const paramsWithFilters = {
      ...currentParams,
      filters: Object.keys(activeFilters).length > 0 ? activeFilters : undefined,
      sort: activeSortOption?.value,
      sortDirection: activeSortOption?.direction,
    };

    searchMutation.mutate({
      type: currentSearchType,
      params: paramsWithFilters as SearchParams,
    });
  }, [
    currentSearchType,
    currentParams,
    activeFilters,
    activeSortOption,
    setIsLoading,
    clearResults,
    searchMutation,
    setError,
  ]);

  // Update search parameters based on type
  const updateParams = useCallback(
    (params: Partial<SearchParams>) => {
      if (!currentSearchType) return;

      switch (currentSearchType) {
        case "flight":
          updateFlightParams(params as Partial<FlightSearchParams>);
          break;
        case "accommodation":
          updateAccommodationParams(params as Partial<AccommodationSearchParams>);
          break;
        case "activity":
          updateActivityParams(params as Partial<ActivitySearchParams>);
          break;
      }
    },
    [
      currentSearchType,
      updateFlightParams,
      updateAccommodationParams,
      updateActivityParams,
    ]
  );

  return {
    // State
    currentSearchType,
    currentParams,
    results,
    isLoading: isLoading || searchMutation.isPending,
    error,
    activeFilters,
    activeSortOption,

    // Actions
    setSearchType,
    updateParams,
    resetParams,
    search,
    setActiveFilter,
    clearFilters,
    setActiveSortOption,
  };
}

/**
 * Hook for managing saved searches
 */
export function useSavedSearches() {
  const { savedSearches, saveSearch, deleteSearch } = useSearchStore();

  // Query for fetching saved searches from backend
  const savedSearchesQuery = useApiQuery<{ searches: SavedSearch[] }>(
    "/api/search/saved",
    {},
    {
      // Don't auto-fetch, only when component using this hook mounts
      enabled: false,
    }
  );

  // Mutation for saving a search
  const saveSearchMutation = useApiMutation<
    { search: SavedSearch },
    { name: string; type: SearchType; params: SearchParams }
  >("/api/search/save", {
    onSuccess: () => {
      // Refetch saved searches after saving a new one
      savedSearchesQuery.refetch();
    },
  });

  // Mutation for deleting a saved search
  const deleteSearchMutation = useApiMutation<{ success: boolean }, string>(
    "/api/search/saved/delete",
    {
      onSuccess: () => {
        // Refetch saved searches after deleting one
        savedSearchesQuery.refetch();
      },
    }
  );

  // Function to save a search to the backend
  const saveSearchRemote = useCallback(
    (name: string, type: SearchType, params: SearchParams) => {
      saveSearchMutation.mutate({ name, type, params });
    },
    [saveSearchMutation]
  );

  // Function to load a saved search
  const loadSavedSearch = useCallback((search: SavedSearch) => {
    const { type, params } = search;
    useSearchStore.getState().setSearchType(type);

    switch (type) {
      case "flight":
        useSearchStore.getState().updateFlightParams(params as FlightSearchParams);
        break;
      case "accommodation":
        useSearchStore
          .getState()
          .updateAccommodationParams(params as AccommodationSearchParams);
        break;
      case "activity":
        useSearchStore.getState().updateActivityParams(params as ActivitySearchParams);
        break;
    }
  }, []);

  return {
    // Local state
    savedSearches,

    // Remote state
    remoteSavedSearches: savedSearchesQuery.data?.searches || [],
    isLoading:
      savedSearchesQuery.isLoading ||
      saveSearchMutation.isPending ||
      deleteSearchMutation.isPending,

    // Actions
    saveSearch,
    saveSearchRemote,
    deleteSearch,
    deleteSearchRemote: deleteSearchMutation.mutate,
    loadSavedSearch,
    refreshSavedSearches: savedSearchesQuery.refetch,
  };
}

/**
 * Hook for managing recent searches
 */
export function useRecentSearches() {
  const { recentSearches, clearRecentSearches } = useSearchStore();

  // Function to load a recent search
  const loadRecentSearch = useCallback((type: SearchType, params: SearchParams) => {
    useSearchStore.getState().setSearchType(type);

    switch (type) {
      case "flight":
        useSearchStore.getState().updateFlightParams(params as FlightSearchParams);
        break;
      case "accommodation":
        useSearchStore
          .getState()
          .updateAccommodationParams(params as AccommodationSearchParams);
        break;
      case "activity":
        useSearchStore.getState().updateActivityParams(params as ActivitySearchParams);
        break;
    }
  }, []);

  return {
    recentSearches,
    loadRecentSearch,
    clearRecentSearches,
  };
}
