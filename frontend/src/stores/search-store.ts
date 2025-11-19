/**
 * @fileoverview Search store orchestrator using Zustand for managing search state,
 * coordinating multiple slice stores, and providing high-level search operations
 * with cross-store synchronization and workflow management.
 */

import type {
  Accommodation,
  Activity,
  Destination,
  Flight,
  SearchParams,
  SearchResults,
  SearchType,
} from "@schemas/search";
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
      applyFiltersAndSearch: async () => {
        const filtersStore = useSearchFiltersStore.getState();

        // Validate filters
        const filtersValid = await filtersStore.validateAllFilters();
        if (!filtersValid) {
          throw new Error("Some filters are invalid");
        }

        return await get().validateAndExecuteSearch();
      },

      get currentParams() {
        return useSearchParamsStore.getState().currentParams;
      },
      // Computed properties
      get currentSearchType() {
        return useSearchParamsStore.getState().currentSearchType;
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

          // Set the results
          resultsStore.setSearchResults(searchId, mockResults, {
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

          resultsStore.setSearchError(searchId, errorDetails);
          throw error;
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
          filterCount: filtersStore.activeFilterCount,
          hasFilters: filtersStore.hasActiveFilters,
          hasResults: resultsStore.hasResults,
          isValid: paramsStore.hasValidParams,
          params: paramsStore.currentParams,
          resultCount,
          searchType: paramsStore.currentSearchType,
        };
      },

      get hasActiveFilters() {
        return useSearchFiltersStore.getState().hasActiveFilters;
      },

      get hasResults() {
        return useSearchResultsStore.getState().hasResults;
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

      get isSearching() {
        return useSearchResultsStore.getState().isSearching;
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

      resetSearch: () => {
        useSearchParamsStore.getState().reset();
        useSearchResultsStore.getState().clearAllResults();
        useSearchFiltersStore.getState().softReset();
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
    }),
    { name: "SearchOrchestratorStore" }
  )
);
