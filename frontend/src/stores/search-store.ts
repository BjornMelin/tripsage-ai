/**
 * @fileoverview Search store orchestrator using Zustand for managing search state,
 * coordinating multiple slice stores, and providing high-level search operations
 * with cross-store synchronization and workflow management.
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type {
  Accommodation,
  Activity,
  Destination,
  Flight,
  SearchParams,
  SearchResults,
  SearchType,
} from "@/types/search";

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

/**
 * Zustand store hook for orchestrating search operations across multiple slice stores.
 *
 * Provides high-level search workflow management, cross-store synchronization,
 * and coordinated operations for search parameters, results, filters, and history.
 *
 * @returns The search store orchestrator hook with state and actions.
 */
export const useSearchStore = create<SearchOrchestratorState>()(
  devtools(
    (_set, get) => ({
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
        useSearchFiltersStore.getState(); // Access filters store
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
                  airline: "Example Airlines",
                  flightNumber: "EX123",
                  price: 450,
                  departureTime: "2025-07-15T08:00:00Z",
                  arrivalTime: "2025-07-15T13:30:00Z",
                  origin: "NYC",
                  destination: "LAX",
                  duration: 330,
                  stops: 0,
                  cabinClass: "economy",
                  seatsAvailable: 10,
                },
                {
                  id: "2",
                  airline: "Demo Air",
                  flightNumber: "DA456",
                  price: 520,
                  departureTime: "2025-07-15T09:00:00Z",
                  arrivalTime: "2025-07-15T15:15:00Z",
                  origin: "NYC",
                  destination: "LAX",
                  duration: 375,
                  stops: 1,
                  cabinClass: "economy",
                  seatsAvailable: 5,
                },
              ] as Flight[];
              break;
            case "accommodation":
              mockResults.accommodations = [
                {
                  id: "1",
                  name: "Example Hotel",
                  type: "hotel",
                  location: "123 Main St, Los Angeles, USA",
                  checkIn: "2025-07-15",
                  checkOut: "2025-07-18",
                  pricePerNight: 120,
                  totalPrice: 360,
                  rating: 4.5,
                  amenities: ["wifi", "pool"],
                  images: [],
                  coordinates: { lat: 34.0522, lng: -118.2437 },
                },
                {
                  id: "2",
                  name: "Demo Resort",
                  type: "resort",
                  location: "456 Beach Blvd, Los Angeles, USA",
                  checkIn: "2025-07-15",
                  checkOut: "2025-07-18",
                  pricePerNight: 180,
                  totalPrice: 540,
                  rating: 4.8,
                  amenities: ["wifi", "pool", "spa"],
                  images: [],
                  coordinates: { lat: 34.0522, lng: -118.2437 },
                },
              ] as Accommodation[];
              break;
            case "activity":
              mockResults.activities = [
                {
                  id: "1",
                  name: "City Tour",
                  type: "tours",
                  location: "Downtown, Los Angeles, USA",
                  date: "2025-07-15",
                  duration: 180,
                  price: 45,
                  rating: 4.2,
                  description: "Explore the city",
                  images: [],
                  coordinates: { lat: 34.0522, lng: -118.2437 },
                },
                {
                  id: "2",
                  name: "Museum Visit",
                  type: "cultural",
                  location: "Museum District, Los Angeles, USA",
                  date: "2025-07-15",
                  duration: 120,
                  price: 25,
                  rating: 4.0,
                  description: "Visit the local museum",
                  images: [],
                  coordinates: { lat: 34.0522, lng: -118.2437 },
                },
              ] as Activity[];
              break;
            case "destination":
              mockResults.destinations = [
                {
                  id: "1",
                  name: "Paris",
                  description: "The City of Light",
                  formattedAddress: "Paris, France",
                  types: ["city"],
                  coordinates: { lat: 48.8566, lng: 2.3522 },
                  country: "France",
                  region: "Europe",
                  photos: [],
                  popularityScore: 9.5,
                  bestTimeToVisit: ["spring", "fall"],
                  attractions: [],
                  rating: 4.5,
                  climate: {
                    season: "temperate",
                    averageTemp: 15,
                    rainfall: 50,
                  },
                },
                {
                  id: "2",
                  name: "Tokyo",
                  description: "A vibrant metropolis",
                  formattedAddress: "Tokyo, Japan",
                  types: ["city"],
                  coordinates: { lat: 35.6762, lng: 139.6503 },
                  country: "Japan",
                  region: "Asia",
                  photos: [],
                  popularityScore: 9.3,
                  bestTimeToVisit: ["spring", "fall"],
                  attractions: [],
                  rating: 4.7,
                  climate: {
                    season: "humid_subtropical",
                    averageTemp: 20,
                    rainfall: 80,
                  },
                },
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

        let { currentSearchType, currentParams } = paramsStore;

        // If computed currentParams is not yet available, derive from slice state
        if (currentSearchType && !currentParams) {
          switch (currentSearchType) {
            case "flight":
              currentParams = paramsStore.flightParams as SearchParams;
              break;
            case "accommodation":
              currentParams = paramsStore.accommodationParams as SearchParams;
              break;
            case "activity":
              currentParams = paramsStore.activityParams as SearchParams;
              break;
            case "destination":
              currentParams = paramsStore.destinationParams as SearchParams;
              break;
            default:
              break;
          }
        }

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

export {
  useActiveFilters,
  useActiveSortOption,
  useCurrentFilters,
  useFilterPresets,
  useHasActiveFilters,
} from "./search-filters-store";
export {
  useFavoriteSearches,
  useRecentSearches,
  useSavedSearches,
  useSearchAnalytics,
  useSearchSuggestions,
} from "./search-history-store";
// Re-export utility selectors
export {
  useCurrentSearchParams,
  useSearchParamsValidation,
  useSearchType,
} from "./search-params-store";
export {
  useHasSearchResults,
  useIsSearching,
  useSearchError,
  useSearchProgress,
  useSearchResults,
  useSearchStatus,
} from "./search-results-store";
