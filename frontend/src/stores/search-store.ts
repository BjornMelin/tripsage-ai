import type { 
  SearchParams, 
  SearchResults, 
  SearchType, 
  Flight, 
  Accommodation, 
  Activity, 
  Destination 
} from "@/types/search";
import { create } from "zustand";
import { devtools } from "zustand/middleware";

import { useSearchFiltersStore } from "./search-filters-store";
import { useSearchHistoryStore } from "./search-history-store";
// Import the slice stores
import { useSearchParamsStore } from "./search-params-store";
import { useSearchResultsStore } from "./search-results-store";

// Combined search store interface that orchestrates all search operations
interface SearchOrchestratorState {
  // Computed properties that aggregate data from slice stores
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

  // State synchronization
  syncStores: () => void;

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

// Main search store that orchestrates the slice stores
export const useSearchStore = create<SearchOrchestratorState>()(
  devtools(
    (set, get) => ({
      // Computed properties
      get currentSearchType() {
        return useSearchParamsStore.getState().currentSearchType;
      },

      get currentParams() {
        return useSearchParamsStore.getState().currentParams;
      },

      get hasActiveFilters() {
        return useSearchFiltersStore.getState().hasActiveFilters;
      },

      get hasResults() {
        return useSearchResultsStore.getState().hasResults;
      },

      get isSearching() {
        return useSearchResultsStore.getState().isSearching;
      },

      // High-level search operations
      initializeSearch: (searchType) => {
        // Initialize all stores for the search type
        useSearchParamsStore.getState().setSearchType(searchType);
        useSearchFiltersStore.getState().setSearchType(searchType);
        useSearchResultsStore.getState().clearResults(searchType);

        // Sync the stores
        get().syncStores();
      },

      executeSearch: async (params) => {
        const paramsStore = useSearchParamsStore.getState();
        const resultsStore = useSearchResultsStore.getState();
        const filtersStore = useSearchFiltersStore.getState();
        const historyStore = useSearchHistoryStore.getState();

        const searchType = paramsStore.currentSearchType;
        if (!searchType) {
          throw new Error("No search type selected");
        }

        // Use provided params or current params
        const searchParams = params || paramsStore.currentParams;
        if (!searchParams) {
          throw new Error("No search parameters available");
        }

        // Validate parameters
        const isValid = await paramsStore.validateCurrentParams();
        if (!isValid) {
          throw new Error("Invalid search parameters");
        }

        // Start the search
        const searchId = resultsStore.startSearch(
          searchType,
          searchParams as Record<string, unknown>
        );

        try {
          // Add to recent searches
          historyStore.addRecentSearch(searchType, searchParams, {
            resultsCount: 0,
            searchDuration: 0,
          });

          // Simulate search progress (replace with actual search implementation)
          resultsStore.updateSearchProgress(searchId, 25);
          await new Promise((resolve) => setTimeout(resolve, 500));

          resultsStore.updateSearchProgress(searchId, 50);
          await new Promise((resolve) => setTimeout(resolve, 500));

          resultsStore.updateSearchProgress(searchId, 75);
          await new Promise((resolve) => setTimeout(resolve, 500));

          // Mock search results (replace with actual API calls)
          const mockResults: SearchResults = {};

          switch (searchType) {
            case "flight":
              mockResults.flights = [
                {
                  id: "1",
                  price: 450,
                  airline: "Example Airlines",
                  duration: "5h 30m",
                },
                { id: "2", price: 520, airline: "Demo Air", duration: "6h 15m" },
              ] as Flight[];
              break;
            case "accommodation":
              mockResults.accommodations = [
                { id: "1", name: "Example Hotel", price: 120, rating: 4.5 },
                { id: "2", name: "Demo Resort", price: 180, rating: 4.8 },
              ] as Accommodation[];
              break;
            case "activity":
              mockResults.activities = [
                { id: "1", name: "City Tour", price: 45, duration: "3 hours" },
                { id: "2", name: "Museum Visit", price: 25, duration: "2 hours" },
              ] as Activity[];
              break;
            case "destination":
              mockResults.destinations = [
                { id: "1", name: "Paris", country: "France", type: "city" },
                { id: "2", name: "Tokyo", country: "Japan", type: "city" },
              ] as Destination[];
              break;
          }

          // Set the results
          resultsStore.setSearchResults(searchId, mockResults, {
            totalResults: Object.values(mockResults).flat().length,
            resultsPerPage: 20,
            currentPage: 1,
            hasMoreResults: false,
            searchDuration: 1500,
            provider: "MockProvider",
            requestId: searchId,
          });

          return searchId;
        } catch (error) {
          const errorDetails = {
            code: "SEARCH_FAILED",
            message: error instanceof Error ? error.message : "Search failed",
            retryable: true,
            occurredAt: new Date().toISOString(),
          };

          resultsStore.setSearchError(searchId, errorDetails);
          throw error;
        }
      },

      resetSearch: () => {
        useSearchParamsStore.getState().reset();
        useSearchResultsStore.getState().clearAllResults();
        useSearchFiltersStore.getState().softReset();
      },

      // Cross-store operations
      loadSavedSearch: async (savedSearchId) => {
        const historyStore = useSearchHistoryStore.getState();
        const savedSearches = historyStore.savedSearches;
        const savedSearch = savedSearches.find((search) => search.id === savedSearchId);

        if (!savedSearch) return false;

        try {
          // Initialize search type
          get().initializeSearch(savedSearch.searchType);

          // Load parameters
          const paramsStore = useSearchParamsStore.getState();
          await paramsStore.loadParamsFromTemplate(
            savedSearch.params as SearchParams,
            savedSearch.searchType
          );

          // Mark as used
          historyStore.markSearchAsUsed(savedSearchId);

          return true;
        } catch (error) {
          console.error("Failed to load saved search:", error);
          return false;
        }
      },

      duplicateCurrentSearch: async (name) => {
        const paramsStore = useSearchParamsStore.getState();
        const historyStore = useSearchHistoryStore.getState();

        const { currentSearchType, currentParams } = paramsStore;
        if (!currentSearchType || !currentParams) return null;

        return await historyStore.saveSearch(name, currentSearchType, currentParams);
      },

      // Search workflow helpers
      validateAndExecuteSearch: async () => {
        const paramsStore = useSearchParamsStore.getState();

        // Validate parameters first
        const isValid = await paramsStore.validateCurrentParams();
        if (!isValid) {
          throw new Error("Search parameters are invalid");
        }

        return await get().executeSearch();
      },

      applyFiltersAndSearch: async () => {
        const filtersStore = useSearchFiltersStore.getState();

        // Validate filters
        const filtersValid = await filtersStore.validateAllFilters();
        if (!filtersValid) {
          throw new Error("Some filters are invalid");
        }

        return await get().validateAndExecuteSearch();
      },

      retryLastSearch: async () => {
        const resultsStore = useSearchResultsStore.getState();

        if (!resultsStore.canRetry) {
          throw new Error("Cannot retry search");
        }

        return await resultsStore.retryLastSearch();
      },

      // State synchronization
      syncStores: () => {
        const paramsStore = useSearchParamsStore.getState();
        const filtersStore = useSearchFiltersStore.getState();

        // Ensure filter store knows about current search type
        if (
          paramsStore.currentSearchType &&
          paramsStore.currentSearchType !== filtersStore.currentSearchType
        ) {
          filtersStore.setSearchType(paramsStore.currentSearchType);
        }
      },

      // Quick access helpers
      getSearchSummary: () => {
        const paramsStore = useSearchParamsStore.getState();
        const resultsStore = useSearchResultsStore.getState();
        const filtersStore = useSearchFiltersStore.getState();

        const results = resultsStore.results;
        const resultCount = Object.values(results).reduce((total, typeResults) => {
          if (Array.isArray(typeResults)) {
            return total + typeResults.length;
          }
          return total;
        }, 0);

        return {
          searchType: paramsStore.currentSearchType,
          params: paramsStore.currentParams,
          hasResults: resultsStore.hasResults,
          resultCount,
          hasFilters: filtersStore.hasActiveFilters,
          filterCount: filtersStore.activeFilterCount,
          isValid: paramsStore.hasValidParams,
        };
      },
    }),
    { name: "SearchOrchestratorStore" }
  )
);

// Re-export the slice stores for direct access when needed
export {
  useSearchParamsStore,
  useSearchResultsStore,
  useSearchFiltersStore,
  useSearchHistoryStore,
};

// Re-export utility selectors
export {
  useSearchType,
  useCurrentSearchParams,
  useSearchParamsValidation,
} from "./search-params-store";

export {
  useSearchStatus,
  useSearchResults,
  useIsSearching,
  useSearchProgress,
  useSearchError,
  useHasSearchResults,
} from "./search-results-store";

export {
  useActiveFilters,
  useActiveSortOption,
  useCurrentFilters,
  useHasActiveFilters,
  useFilterPresets,
} from "./search-filters-store";

export {
  useRecentSearches,
  useSavedSearches,
  useFavoriteSearches,
  useSearchSuggestions,
  useSearchAnalytics,
} from "./search-history-store";
