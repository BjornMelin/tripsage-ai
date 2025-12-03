/**
 * @fileoverview Search orchestration hook that replaces the search-store.ts orchestrator.
 *
 * This hook composes the search params, results, filters, and history stores
 * to provide high-level search operations without cross-store getState() calls.
 */

"use client";

import type {
  Accommodation,
  Activity,
  Destination,
  Flight,
  SearchParams,
  SearchResults,
  SearchType,
} from "@schemas/search";
import { useCallback, useMemo } from "react";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { useSearchHistoryStore } from "@/stores/search-history-store";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";

const logger = createStoreLogger({ storeName: "search-orchestration" });

/**
 * Search orchestration hook result interface.
 */
export interface UseSearchOrchestrationResult {
  // Current state (derived from stores)
  currentSearchType: SearchType | null;
  currentParams: SearchParams | null;
  hasActiveFilters: boolean;
  hasResults: boolean;
  isSearching: boolean;

  // High-level search operations
  initializeSearch: (searchType: SearchType) => void;
  executeSearch: (params?: SearchParams) => Promise<string | null>;
  resetSearch: () => void;

  // Cross-store operations
  loadSavedSearch: (savedSearchId: string) => Promise<boolean>;
  duplicateCurrentSearch: (name: string) => Promise<string | null>;

  // Search workflow helpers
  validateAndExecuteSearch: () => Promise<string | null>;
  applyFiltersAndSearch: () => Promise<string | null>;
  retryLastSearch: () => Promise<string | null>;

  // Quick access helpers
  getSearchSummary: () => {
    searchType: SearchType | null;
    params: SearchParams | null;
    hasResults: boolean;
    resultCount: number;
    hasFilters: boolean;
    filterCount: number;
    isValid: boolean;
  };
}

/**
 * Hook for orchestrating search operations across multiple stores.
 *
 * Replaces the search-store.ts orchestrator with a hook-based approach
 * that uses React subscriptions instead of cross-store getState() calls.
 *
 * @returns Search orchestration result with state and actions.
 */
export function useSearchOrchestration(): UseSearchOrchestrationResult {
  // Subscribe to relevant state from each store
  const currentSearchType = useSearchParamsStore((state) => state.currentSearchType);
  const currentParams = useSearchParamsStore((state) => state.currentParams);
  const hasValidParams = useSearchParamsStore((state) => state.hasValidParams);
  const validateCurrentParams = useSearchParamsStore(
    (state) => state.validateCurrentParams
  );
  const setParamsSearchType = useSearchParamsStore((state) => state.setSearchType);
  const loadParamsFromTemplate = useSearchParamsStore(
    (state) => state.loadParamsFromTemplate
  );
  const resetParams = useSearchParamsStore((state) => state.reset);
  const flightParams = useSearchParamsStore((state) => state.flightParams);
  const accommodationParams = useSearchParamsStore(
    (state) => state.accommodationParams
  );
  const activityParams = useSearchParamsStore((state) => state.activityParams);
  const destinationParams = useSearchParamsStore((state) => state.destinationParams);

  const hasActiveFilters = useSearchFiltersStore((state) => state.hasActiveFilters);
  const activeFilterCount = useSearchFiltersStore((state) => state.activeFilterCount);
  const setFiltersSearchType = useSearchFiltersStore((state) => state.setSearchType);
  const validateAllFilters = useSearchFiltersStore((state) => state.validateAllFilters);
  const softResetFilters = useSearchFiltersStore((state) => state.softReset);

  const hasResults = useSearchResultsStore((state) => state.hasResults);
  const isSearching = useSearchResultsStore((state) => state.isSearching);
  const results = useSearchResultsStore((state) => state.results);
  const canRetry = useSearchResultsStore((state) => state.canRetry);
  const startSearch = useSearchResultsStore((state) => state.startSearch);
  const updateSearchProgress = useSearchResultsStore(
    (state) => state.updateSearchProgress
  );
  const setSearchResults = useSearchResultsStore((state) => state.setSearchResults);
  const setSearchError = useSearchResultsStore((state) => state.setSearchError);
  const clearResults = useSearchResultsStore((state) => state.clearResults);
  const clearAllResults = useSearchResultsStore((state) => state.clearAllResults);
  const retryLastSearchAction = useSearchResultsStore((state) => state.retryLastSearch);

  const savedSearches = useSearchHistoryStore((state) => state.savedSearches);
  const addRecentSearch = useSearchHistoryStore((state) => state.addRecentSearch);
  const saveSearch = useSearchHistoryStore((state) => state.saveSearch);
  const markSearchAsUsed = useSearchHistoryStore((state) => state.markSearchAsUsed);

  /**
   * Initialize search for a specific type.
   */
  const initializeSearch = useCallback(
    (searchType: SearchType) => {
      setParamsSearchType(searchType);
      setFiltersSearchType(searchType);
      clearResults(searchType);
    },
    [setParamsSearchType, setFiltersSearchType, clearResults]
  );

  /**
   * Execute a search with the given or current parameters.
   */
  const executeSearch = useCallback(
    async (params?: SearchParams): Promise<string | null> => {
      if (!currentSearchType) {
        throw new Error("No search type selected");
      }

      // Use provided params or derive from current state
      let searchParams = params || currentParams;

      // If computed currentParams is not available, derive from slice state
      if (!searchParams && currentSearchType) {
        switch (currentSearchType) {
          case "flight":
            searchParams = flightParams as SearchParams;
            break;
          case "accommodation":
            searchParams = accommodationParams as SearchParams;
            break;
          case "activity":
            searchParams = activityParams as SearchParams;
            break;
          case "destination":
            searchParams = destinationParams as SearchParams;
            break;
        }
      }

      if (!searchParams) {
        throw new Error("No search parameters available");
      }

      // Validate parameters
      const isValid = await validateCurrentParams();
      if (!isValid) {
        throw new Error("Invalid search parameters");
      }

      // Start the search
      const searchId = startSearch(
        currentSearchType,
        searchParams as Record<string, unknown>
      );

      try {
        // Add to recent searches
        addRecentSearch(currentSearchType, searchParams, {
          resultsCount: 0,
          searchDuration: 0,
        });

        // Simulate search progress (replace with actual search implementation)
        updateSearchProgress(searchId, 25);
        await new Promise((resolve) => setTimeout(resolve, 500));

        updateSearchProgress(searchId, 50);
        await new Promise((resolve) => setTimeout(resolve, 500));

        updateSearchProgress(searchId, 75);
        await new Promise((resolve) => setTimeout(resolve, 500));

        // Mock search results (replace with actual API calls)
        const mockResults: SearchResults = generateMockResults(currentSearchType);

        // Set the results
        setSearchResults(searchId, mockResults, {
          currentPage: 1,
          hasMoreResults: false,
          provider: "MockProvider",
          requestId: searchId,
          resultsPerPage: 20,
          searchDuration: 1500,
          totalResults: Object.values(mockResults).flat().length,
        });

        return searchId;
      } catch (error) {
        const errorDetails = {
          code: "SEARCH_FAILED",
          message: error instanceof Error ? error.message : "Search failed",
          occurredAt: new Date().toISOString(),
          retryable: true,
        };

        setSearchError(searchId, errorDetails);
        throw error;
      }
    },
    [
      currentSearchType,
      currentParams,
      flightParams,
      accommodationParams,
      activityParams,
      destinationParams,
      validateCurrentParams,
      startSearch,
      addRecentSearch,
      updateSearchProgress,
      setSearchResults,
      setSearchError,
    ]
  );

  /**
   * Reset all search state.
   */
  const resetSearch = useCallback(() => {
    resetParams();
    clearAllResults();
    softResetFilters();
  }, [resetParams, clearAllResults, softResetFilters]);

  /**
   * Load a saved search by ID.
   */
  const loadSavedSearch = useCallback(
    async (savedSearchId: string): Promise<boolean> => {
      const savedSearch = savedSearches.find((search) => search.id === savedSearchId);

      if (!savedSearch) return false;

      try {
        // Initialize search type
        initializeSearch(savedSearch.searchType);

        // Load parameters
        await loadParamsFromTemplate(
          savedSearch.params as SearchParams,
          savedSearch.searchType
        );

        // Mark as used
        markSearchAsUsed(savedSearchId);

        return true;
      } catch (error) {
        logger.error("Failed to load saved search", {
          error,
          savedSearchId,
          searchType: savedSearch.searchType,
        });
        return false;
      }
    },
    [savedSearches, initializeSearch, loadParamsFromTemplate, markSearchAsUsed]
  );

  /**
   * Duplicate the current search with a new name.
   */
  const duplicateCurrentSearch = useCallback(
    async (name: string): Promise<string | null> => {
      let params = currentParams;

      // Derive params from slice state if needed
      if (currentSearchType && !params) {
        switch (currentSearchType) {
          case "flight":
            params = flightParams as SearchParams;
            break;
          case "accommodation":
            params = accommodationParams as SearchParams;
            break;
          case "activity":
            params = activityParams as SearchParams;
            break;
          case "destination":
            params = destinationParams as SearchParams;
            break;
        }
      }

      if (!currentSearchType || !params) return null;

      return await saveSearch(name, currentSearchType, params);
    },
    [
      currentSearchType,
      currentParams,
      flightParams,
      accommodationParams,
      activityParams,
      destinationParams,
      saveSearch,
    ]
  );

  /**
   * Validate parameters and execute search.
   */
  const validateAndExecuteSearch = useCallback(async (): Promise<string | null> => {
    const isValid = await validateCurrentParams();
    if (!isValid) {
      throw new Error("Search parameters are invalid");
    }

    return await executeSearch();
  }, [validateCurrentParams, executeSearch]);

  /**
   * Validate filters and execute search.
   */
  const applyFiltersAndSearch = useCallback(async (): Promise<string | null> => {
    const filtersValid = await validateAllFilters();
    if (!filtersValid) {
      throw new Error("Some filters are invalid");
    }

    return await validateAndExecuteSearch();
  }, [validateAllFilters, validateAndExecuteSearch]);

  /**
   * Retry the last search.
   */
  const retryLastSearch = useCallback(async (): Promise<string | null> => {
    if (!canRetry) {
      throw new Error("Cannot retry search");
    }

    return await retryLastSearchAction();
  }, [canRetry, retryLastSearchAction]);

  /**
   * Get a summary of the current search state.
   */
  const getSearchSummary = useCallback(() => {
    const resultCount = Object.values(results).reduce((total, typeResults) => {
      if (Array.isArray(typeResults)) {
        return total + typeResults.length;
      }
      return total;
    }, 0);

    return {
      filterCount: activeFilterCount,
      hasFilters: hasActiveFilters,
      hasResults,
      isValid: hasValidParams,
      params: currentParams,
      resultCount,
      searchType: currentSearchType,
    };
  }, [
    results,
    activeFilterCount,
    hasActiveFilters,
    hasResults,
    hasValidParams,
    currentParams,
    currentSearchType,
  ]);

  return useMemo(
    () => ({
      // Operations
      applyFiltersAndSearch,
      // State
      currentParams,
      currentSearchType,
      duplicateCurrentSearch,
      executeSearch,
      getSearchSummary,
      hasActiveFilters,
      hasResults,
      initializeSearch,
      isSearching,
      loadSavedSearch,
      resetSearch,
      retryLastSearch,
      validateAndExecuteSearch,
    }),
    [
      currentParams,
      currentSearchType,
      hasActiveFilters,
      hasResults,
      isSearching,
      applyFiltersAndSearch,
      duplicateCurrentSearch,
      executeSearch,
      getSearchSummary,
      initializeSearch,
      loadSavedSearch,
      resetSearch,
      retryLastSearch,
      validateAndExecuteSearch,
    ]
  );
}

/**
 * TODO: Generate mock search results for a search type.
 * This should be replaced with actual API calls.
 */
function generateMockResults(searchType: SearchType): SearchResults {
  const mockResults: SearchResults = {};

  switch (searchType) {
    case "flight":
      mockResults.flights = [
        {
          airline: "Example Airlines",
          arrivalTime: "2025-07-15T13:30:00Z",
          cabinClass: "economy",
          departureTime: "2025-07-15T08:00:00Z",
          destination: "LAX",
          duration: 330,
          flightNumber: "EX123",
          id: "1",
          origin: "NYC",
          price: 450,
          seatsAvailable: 10,
          stops: 0,
        },
        {
          airline: "Demo Air",
          arrivalTime: "2025-07-15T15:15:00Z",
          cabinClass: "economy",
          departureTime: "2025-07-15T09:00:00Z",
          destination: "LAX",
          duration: 375,
          flightNumber: "DA456",
          id: "2",
          origin: "NYC",
          price: 520,
          seatsAvailable: 5,
          stops: 1,
        },
      ] as Flight[];
      break;
    case "accommodation":
      mockResults.accommodations = [
        {
          amenities: ["wifi", "pool"],
          checkIn: "2025-07-15",
          checkOut: "2025-07-18",
          coordinates: { lat: 34.0522, lng: -118.2437 },
          id: "1",
          images: [],
          location: "123 Main St, Los Angeles, USA",
          name: "Example Hotel",
          pricePerNight: 120,
          rating: 4.5,
          totalPrice: 360,
          type: "hotel",
        },
        {
          amenities: ["wifi", "pool", "spa"],
          checkIn: "2025-07-15",
          checkOut: "2025-07-18",
          coordinates: { lat: 34.0522, lng: -118.2437 },
          id: "2",
          images: [],
          location: "456 Beach Blvd, Los Angeles, USA",
          name: "Demo Resort",
          pricePerNight: 180,
          rating: 4.8,
          totalPrice: 540,
          type: "resort",
        },
      ] as Accommodation[];
      break;
    case "activity":
      mockResults.activities = [
        {
          coordinates: { lat: 34.0522, lng: -118.2437 },
          date: "2025-07-15",
          description: "Explore the city",
          duration: 180,
          id: "1",
          images: [],
          location: "Downtown, Los Angeles, USA",
          name: "City Tour",
          price: 45,
          rating: 4.2,
          type: "tours",
        },
        {
          coordinates: { lat: 34.0522, lng: -118.2437 },
          date: "2025-07-15",
          description: "Visit the local museum",
          duration: 120,
          id: "2",
          images: [],
          location: "Museum District, Los Angeles, USA",
          name: "Museum Visit",
          price: 25,
          rating: 4.0,
          type: "cultural",
        },
      ] as Activity[];
      break;
    case "destination":
      mockResults.destinations = [
        {
          attractions: [],
          bestTimeToVisit: ["spring", "fall"],
          climate: {
            averageTemp: 15,
            rainfall: 50,
            season: "temperate",
          },
          coordinates: { lat: 48.8566, lng: 2.3522 },
          country: "France",
          description: "The City of Light",
          formattedAddress: "Paris, France",
          id: "1",
          name: "Paris",
          photos: [],
          popularityScore: 9.5,
          rating: 4.5,
          region: "Europe",
          types: ["city"],
        },
        {
          attractions: [],
          bestTimeToVisit: ["spring", "fall"],
          climate: {
            averageTemp: 20,
            rainfall: 80,
            season: "humid_subtropical",
          },
          coordinates: { lat: 35.6762, lng: 139.6503 },
          country: "Japan",
          description: "A vibrant metropolis",
          formattedAddress: "Tokyo, Japan",
          id: "2",
          name: "Tokyo",
          photos: [],
          popularityScore: 9.3,
          rating: 4.7,
          region: "Asia",
          types: ["city"],
        },
      ] as Destination[];
      break;
  }

  return mockResults;
}

// Re-export the hook as useSearchStore for backward compatibility
export { useSearchOrchestration as useSearchStore };
