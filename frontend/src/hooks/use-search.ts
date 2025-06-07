"use client";

import { useApiMutation, useApiQuery } from "@/hooks/use-api-query";
import {
  useSearchFiltersStore,
  useSearchHistoryStore,
  useSearchParamsStore,
  useSearchResultsStore,
  useSearchStore,
} from "@/stores/search-store";
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
import { useCallback, useEffect } from "react";

/**
 * Hook for searching flights, accommodations, and activities
 */
export function useSearch() {
  // Use the slice stores directly for detailed operations
  const { currentSearchType, currentParams } = useSearchParamsStore();
  const { results, isSearching: isLoading, error } = useSearchResultsStore();
  const { activeFilters, activeSortOption } = useSearchFiltersStore();

  // Get actions from the appropriate stores
  const {
    setSearchType,
    updateFlightParams,
    updateAccommodationParams,
    updateActivityParams,
    reset: resetParams,
  } = useSearchParamsStore();
  const { clearAllResults: clearResults, setSearchResults: setResults } =
    useSearchResultsStore();
  const {
    setActiveFilter,
    clearAllFilters: clearFilters,
    setActiveSortOption,
  } = useSearchFiltersStore();
  const { addRecentSearch } = useSearchHistoryStore();

  // Use the orchestrator for complex operations
  const { executeSearch, initializeSearch } = useSearchStore();

  // Search mutation
  const searchMutation = useApiMutation<
    SearchResponse,
    { type: SearchType; params: SearchParams }
  >("/api/search");

  // Handle search success
  useEffect(() => {
    if (searchMutation.data && currentSearchType && currentParams) {
      // Generate a search ID for this result
      const searchId = `search_${Date.now()}`;
      setResults(searchId, searchMutation.data.results, {
        totalResults: searchMutation.data.totalResults || 0,
        searchDuration: 0, // searchTime not available in current response type
        provider: "SearchAPI",
        requestId: searchId,
        resultsPerPage: 20,
        currentPage: 1,
        hasMoreResults: false,
      });
      // Add to recent searches
      addRecentSearch(currentSearchType, currentParams, {
        resultsCount: searchMutation.data.totalResults || 0,
        searchDuration: 0, // searchTime not available in current response type
      });
    }
  }, [
    searchMutation.data,
    setResults,
    addRecentSearch,
    currentSearchType,
    currentParams,
  ]);

  // Handle search error
  useEffect(() => {
    if (searchMutation.error) {
      // For now, just log the error since setError isn't available directly
      console.error(
        "Search error:",
        searchMutation.error.message || "Failed to perform search"
      );
    }
  }, [searchMutation.error]);

  // Function to start a search
  const search = useCallback(async () => {
    if (!currentSearchType || !currentParams) {
      console.error("Search type or parameters not set");
      return;
    }

    clearResults();

    // Apply any active filters to the search params
    const paramsWithFilters = {
      ...currentParams,
      filters: Object.keys(activeFilters).length > 0 ? activeFilters : undefined,
      sort: activeSortOption?.field,
      sortDirection: activeSortOption?.direction,
    };

    try {
      await executeSearch(paramsWithFilters as SearchParams);
    } catch (error) {
      console.error("Search failed:", error);
    }
  }, [
    currentSearchType,
    currentParams,
    activeFilters,
    activeSortOption,
    clearResults,
    executeSearch,
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
  const { savedSearches, saveSearch, deleteSavedSearch } = useSearchHistoryStore();

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
  >("/api/search/save");

  // Handle save search success
  useEffect(() => {
    if (saveSearchMutation.data) {
      // Refetch saved searches after saving a new one
      savedSearchesQuery.refetch();
    }
  }, [saveSearchMutation.data, savedSearchesQuery]);

  // Mutation for deleting a saved search
  const deleteSearchMutation = useApiMutation<{ success: boolean }, string>(
    "/api/search/saved/delete"
  );

  // Handle delete search success
  useEffect(() => {
    if (deleteSearchMutation.data) {
      // Refetch saved searches after deleting one
      savedSearchesQuery.refetch();
    }
  }, [deleteSearchMutation.data, savedSearchesQuery]);

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
    useSearchParamsStore.getState().setSearchType(type);

    switch (type) {
      case "flight":
        useSearchParamsStore
          .getState()
          .updateFlightParams(params as FlightSearchParams);
        break;
      case "accommodation":
        useSearchParamsStore
          .getState()
          .updateAccommodationParams(params as AccommodationSearchParams);
        break;
      case "activity":
        useSearchParamsStore
          .getState()
          .updateActivityParams(params as ActivitySearchParams);
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
    deleteSavedSearch,
    deleteSearchRemote: deleteSearchMutation.mutate,
    loadSavedSearch,
    refreshSavedSearches: savedSearchesQuery.refetch,
  };
}

/**
 * Hook for managing recent searches
 */
export function useRecentSearches() {
  const { recentSearches, clearRecentSearches } = useSearchHistoryStore();

  // Function to load a recent search
  const loadRecentSearch = useCallback((type: SearchType, params: SearchParams) => {
    useSearchParamsStore.getState().setSearchType(type);

    switch (type) {
      case "flight":
        useSearchParamsStore
          .getState()
          .updateFlightParams(params as FlightSearchParams);
        break;
      case "accommodation":
        useSearchParamsStore
          .getState()
          .updateAccommodationParams(params as AccommodationSearchParams);
        break;
      case "activity":
        useSearchParamsStore
          .getState()
          .updateActivityParams(params as ActivitySearchParams);
        break;
    }
  }, []);

  return {
    recentSearches,
    loadRecentSearch,
    clearRecentSearches,
  };
}
