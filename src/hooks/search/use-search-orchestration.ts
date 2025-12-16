/**
 * @fileoverview Search orchestration hook that replaces the search-store.ts orchestrator.
 *
 * This hook composes the search params, results, filters, and history stores
 * to provide high-level search operations without cross-store getState() calls.
 */

"use client";

import type { SearchParams, SearchResults, SearchType } from "@schemas/search";
import type {
  ValidatedAccommodationParams,
  ValidatedActivityParams,
  ValidatedDestinationParams,
  ValidatedFlightParams,
} from "@schemas/stores";
import { useCallback, useMemo } from "react";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { useSearchHistoryStore } from "@/stores/search-history";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import {
  getEmptyResults,
  mapAccommodationResponse,
  mapActivityResponse,
  mapFlightResponse,
  SEARCH_ENDPOINTS,
} from "./utils/response-mappers";

/** Type for params slices from the store */
interface ParamsSlices {
  accommodationParams: Partial<ValidatedAccommodationParams>;
  activityParams: Partial<ValidatedActivityParams>;
  destinationParams: Partial<ValidatedDestinationParams>;
  flightParams: Partial<ValidatedFlightParams>;
}

/** Type-safe extraction of params from slices based on search type */
const getParamsFromSlices = (
  slices: ParamsSlices,
  searchType: SearchType
): Partial<SearchParams> | null => {
  switch (searchType) {
    case "flight":
      return slices.flightParams as Partial<SearchParams>;
    case "accommodation":
      return slices.accommodationParams as Partial<SearchParams>;
    case "activity":
      return slices.activityParams as Partial<SearchParams>;
    case "destination":
      return slices.destinationParams as Partial<SearchParams>;
    default:
      return null;
  }
};

const logger = createStoreLogger({ storeName: "search-orchestration" });

/**
 * Performs the actual search request to the appropriate API endpoint.
 */
async function performSearchRequest(
  searchType: SearchType,
  params: SearchParams,
  onProgress?: () => void,
  signal?: AbortSignal
): Promise<{ results: SearchResults; provider: string }> {
  const endpoint = SEARCH_ENDPOINTS[searchType];
  if (!endpoint) {
    throw new Error(`Unknown search type: ${searchType}`);
  }

  // Destination searches are handled by a separate hook (useDestinationSearch)
  // This orchestration hook focuses on activity, flight, and accommodation searches
  if (searchType === "destination") {
    return {
      provider: "GooglePlaces",
      results: { destinations: [] },
    };
  }

  try {
    onProgress?.();

    const response = await fetch(endpoint, {
      body: JSON.stringify(params),
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage =
        errorData.reason ?? errorData.message ?? `Search failed: ${response.status}`;

      // Graceful failure: return empty results with warning
      logger.warn("Search API returned error, returning empty results", {
        endpoint,
        errorMessage,
        searchType,
        status: response.status,
      });

      return {
        provider: "Error",
        results: getEmptyResults(searchType),
      };
    }

    const data = await response.json();
    onProgress?.();

    // Map response to SearchResults format based on search type
    switch (searchType) {
      case "activity":
        return {
          provider: data.metadata?.primarySource ?? "GooglePlaces",
          results: { activities: mapActivityResponse(data) },
        };

      case "flight":
        return {
          provider: data.provider ?? "Duffel",
          results: { flights: mapFlightResponse(data) },
        };

      case "accommodation":
        return {
          provider: data.provider ?? "Amadeus",
          results: { accommodations: mapAccommodationResponse(data, params) },
        };

      default:
        return { provider: "Unknown", results: {} };
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    // Graceful failure: return empty results instead of throwing
    logger.error("Search request failed", {
      endpoint,
      error: error instanceof Error ? error.message : String(error),
      searchType,
    });

    return {
      provider: "Error",
      results: getEmptyResults(searchType),
    };
  }
}

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
  executeSearch: (
    params?: SearchParams,
    signal?: AbortSignal
  ) => Promise<string | null>;
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
   * Derive current params from store slices (memoized separately to reduce executeSearch dependencies).
   */
  const deriveCurrentParams = useCallback((): SearchParams | null => {
    if (!currentSearchType) return null;

    if (currentParams) return currentParams;

    const partialParams = getParamsFromSlices(
      { accommodationParams, activityParams, destinationParams, flightParams },
      currentSearchType
    );

    if (!partialParams) return null;

    const hasUndefined = Object.values(partialParams).some(
      (value) => value === undefined
    );
    return hasUndefined ? null : (partialParams as SearchParams);
  }, [
    currentSearchType,
    currentParams,
    flightParams,
    accommodationParams,
    activityParams,
    destinationParams,
  ]);

  /**
   * Execute a search with the given or current parameters.
   */
  const executeSearch = useCallback(
    async (params?: SearchParams, signal?: AbortSignal): Promise<string | null> => {
      if (!currentSearchType) {
        throw new Error("No search type selected");
      }

      if (signal?.aborted) return null;

      // Use provided params or derive from state
      const searchParams = params || deriveCurrentParams();

      if (!searchParams) {
        throw new Error("No search parameters available");
      }

      // Validate parameters
      const isValid = await validateCurrentParams();
      if (!isValid) {
        throw new Error("Invalid search parameters");
      }

      if (signal?.aborted) return null;

      // Start the search
      const searchId = startSearch(
        currentSearchType,
        searchParams as Record<string, unknown>
      );

      try {
        const startTime = Date.now();

        // Add to recent searches (will update resultsCount after search completes)
        addRecentSearch(currentSearchType, searchParams, {
          resultsCount: 0,
          searchDuration: 0,
        });

        updateSearchProgress(searchId, 25);

        // Perform real API search based on search type
        const { results, provider } = await performSearchRequest(
          currentSearchType,
          searchParams,
          () => updateSearchProgress(searchId, 50),
          signal
        );

        if (signal?.aborted) return null;

        updateSearchProgress(searchId, 75);

        const searchDuration = Date.now() - startTime;
        const totalResults = Object.values(results)
          .filter(Array.isArray)
          .reduce((sum, arr) => sum + arr.length, 0);

        // Set the results
        setSearchResults(searchId, results, {
          currentPage: 1,
          hasMoreResults: false,
          provider,
          requestId: searchId,
          resultsPerPage: 20,
          searchDuration,
          totalResults,
        });

        return searchId;
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          return null;
        }
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
      deriveCurrentParams,
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
      if (!currentSearchType) return null;

      const params = deriveCurrentParams();
      if (!params) return null;

      return await saveSearch(name, currentSearchType, params);
    },
    [currentSearchType, deriveCurrentParams, saveSearch]
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

// Re-export the hook as useSearchStore for backward compatibility
export { useSearchOrchestration as useSearchStore };
