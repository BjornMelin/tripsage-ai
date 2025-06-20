/**
 * Example of Zustand store with comprehensive Zod validation
 * Demonstrates runtime type safety for store state and mutations
 */

import {
  type SearchParams,
  type SearchResponse,
  type SearchResults,
  type SearchType,
  accommodationSearchParamsSchema,
  activitySearchParamsSchema,
  destinationSearchParamsSchema,
  flightSearchParamsSchema,
  searchResponseSchema,
  searchTypeSchema,
} from "@/lib/schemas/search";
import { searchStoreStateSchema } from "@/lib/schemas/stores";
import {
  ValidationContext,
  validateStoreState,
  validateStrict,
} from "@/lib/validation";
import { create } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";

// Combined store interface with state and actions
interface ValidatedSearchStore {
  // State
  currentSearchType: SearchType | null;
  currentParams: SearchParams | null;
  results: SearchResults;
  filters: Record<string, unknown>;
  sorting:
    | {
        field: string;
        direction: "asc" | "desc";
      }
    | undefined;
  pagination:
    | {
        page: number;
        pageSize: number;
        total: number;
        hasNext: boolean;
        hasPrevious: boolean;
      }
    | undefined;
  recentSearches: Array<{
    id: string;
    type: SearchType;
    params: SearchParams;
    timestamp: string;
  }>;
  savedSearches: Array<{
    id: string;
    name: string;
    type: SearchType;
    params: SearchParams;
    createdAt: string;
    lastUsed?: string;
  }>;
  isLoading: boolean;
  error: string | null;
  lastUpdated?: string;

  // Actions with validation
  setSearchType: (type: SearchType) => void;
  updateParams: (params: Partial<SearchParams>) => void;
  executeSearch: (params?: SearchParams) => Promise<string>;
  clearResults: () => void;
  setFilters: (filters: Record<string, unknown>) => void;
  setSorting: (field: string, direction: "asc" | "desc") => void;
  loadMore: () => Promise<void>;
  saveSearch: (name: string) => Promise<string>;
  loadSavedSearch: (searchId: string) => Promise<boolean>;
  deleteSavedSearch: (searchId: string) => void;
  addToRecentSearches: (type: SearchType, params: SearchParams) => void;
  clearRecentSearches: () => void;
  reset: () => void;

  // Validation helpers
  validateCurrentState: () => boolean;
  getValidationErrors: () => string[];
}

// Mock API functions (replace with actual API calls)
const mockSearchApi = {
  search: async (type: SearchType, _params: SearchParams): Promise<SearchResponse> => {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Mock response based on search type
    const mockResults: SearchResults = {};

    switch (type) {
      case "flight":
        mockResults.flights = [
          {
            id: "fl_1",
            airline: "Test Airlines",
            flightNumber: "TA123",
            origin: "NYC",
            destination: "LAX",
            departureTime: "2025-07-15T08:00:00Z",
            arrivalTime: "2025-07-15T11:30:00Z",
            duration: 210,
            stops: 0,
            price: 299,
            cabinClass: "economy",
            seatsAvailable: 15,
          },
        ];
        break;
      case "accommodation":
        mockResults.accommodations = [
          {
            id: "acc_1",
            name: "Test Hotel",
            type: "hotel",
            location: "Los Angeles, CA",
            checkIn: "2025-07-15",
            checkOut: "2025-07-18",
            pricePerNight: 150,
            totalPrice: 450,
            rating: 4.5,
            amenities: ["wifi", "pool"],
            images: [],
          },
        ];
        break;
      case "activity":
        mockResults.activities = [
          {
            id: "act_1",
            name: "City Tour",
            type: "sightseeing",
            location: "Los Angeles, CA",
            date: "2025-07-15",
            duration: 180,
            price: 75,
            rating: 4.3,
            description: "Explore the city's highlights",
            images: [],
          },
        ];
        break;
      case "destination":
        mockResults.destinations = [
          {
            id: "dest_1",
            name: "Los Angeles",
            description: "City of Angels",
            formattedAddress: "Los Angeles, CA, USA",
            types: ["city"],
            coordinates: { lat: 34.0522, lng: -118.2437 },
          },
        ];
        break;
    }

    return {
      results: mockResults,
      totalResults: Object.values(mockResults).flat().length,
      metadata: {
        searchTime: "1000ms",
        provider: "MockProvider",
      },
    };
  },
};

// Create the validated store
export const useValidatedSearchStore = create<ValidatedSearchStore>()(
  subscribeWithSelector(
    devtools(
      (set, get) => ({
        // Initial state
        currentSearchType: null,
        currentParams: null,
        results: {},
        filters: {},
        sorting: undefined,
        pagination: undefined,
        recentSearches: [],
        savedSearches: [],
        isLoading: false,
        error: null,

        // Validated actions
        setSearchType: (type: SearchType) => {
          try {
            const validatedType = validateStrict(
              searchTypeSchema,
              type,
              ValidationContext.STORE
            );

            set((state: ValidatedSearchStore) => ({
              ...state,
              currentSearchType: validatedType,
              currentParams: null,
              results: {},
              error: null,
              lastUpdated: new Date().toISOString(),
            }));
          } catch (error) {
            console.error("Invalid search type:", error);
            set((state: ValidatedSearchStore) => ({
              ...state,
              error: error instanceof Error ? error.message : "Invalid search type",
            }));
          }
        },

        updateParams: (params: Partial<SearchParams>): void => {
          try {
            const currentType = get().currentSearchType;
            if (!currentType) {
              throw new Error("No search type selected");
            }

            // Validate params based on search type
            let validatedParams: SearchParams;
            const currentParams = get().currentParams || {};
            const mergedParams = { ...currentParams, ...params };

            switch (currentType) {
              case "flight":
                validatedParams = validateStrict(
                  flightSearchParamsSchema,
                  mergedParams,
                  ValidationContext.STORE
                );
                break;
              case "accommodation":
                validatedParams = validateStrict(
                  accommodationSearchParamsSchema,
                  mergedParams,
                  ValidationContext.STORE
                );
                break;
              case "activity":
                validatedParams = validateStrict(
                  activitySearchParamsSchema,
                  mergedParams,
                  ValidationContext.STORE
                );
                break;
              case "destination":
                validatedParams = validateStrict(
                  destinationSearchParamsSchema,
                  mergedParams,
                  ValidationContext.STORE
                );
                break;
              default:
                throw new Error(`Unsupported search type: ${currentType}`);
            }

            set((state: ValidatedSearchStore) => ({
              ...state,
              currentParams: validatedParams,
              error: null,
              lastUpdated: new Date().toISOString(),
            }));
          } catch (error) {
            console.error("Invalid search params:", error);
            set((state: ValidatedSearchStore) => ({
              ...state,
              error:
                error instanceof Error ? error.message : "Invalid search parameters",
            }));
          }
        },

        executeSearch: async (params?: SearchParams): Promise<string> => {
          const state = get();
          const searchType = state.currentSearchType;
          const searchParams = params || state.currentParams;

          if (!searchType) {
            const error = "No search type selected";
            set((prevState: ValidatedSearchStore) => ({ ...prevState, error }));
            throw new Error(error);
          }

          if (!searchParams) {
            const error = "No search parameters provided";
            set((prevState: ValidatedSearchStore) => ({ ...prevState, error }));
            throw new Error(error);
          }

          const searchId = `search_${Date.now()}`;

          set((state: ValidatedSearchStore) => ({
            ...state,
            isLoading: true,
            error: null,
            lastUpdated: new Date().toISOString(),
          }));

          try {
            // Validate search params before API call
            let validatedParams: SearchParams;
            switch (searchType) {
              case "flight":
                validatedParams = validateStrict(
                  flightSearchParamsSchema,
                  searchParams,
                  ValidationContext.API
                );
                break;
              case "accommodation":
                validatedParams = validateStrict(
                  accommodationSearchParamsSchema,
                  searchParams,
                  ValidationContext.API
                );
                break;
              case "activity":
                validatedParams = validateStrict(
                  activitySearchParamsSchema,
                  searchParams,
                  ValidationContext.API
                );
                break;
              case "destination":
                validatedParams = validateStrict(
                  destinationSearchParamsSchema,
                  searchParams,
                  ValidationContext.API
                );
                break;
              default:
                throw new Error(`Unsupported search type: ${searchType}`);
            }

            // Execute search
            const response = await mockSearchApi.search(searchType, validatedParams);

            // Validate API response
            const validatedResponse = validateStrict(
              searchResponseSchema,
              response,
              ValidationContext.API
            );

            // Add to recent searches
            get().addToRecentSearches(searchType, validatedParams);

            set((state: ValidatedSearchStore) => ({
              ...state,
              currentParams: validatedParams,
              results: validatedResponse.results,
              pagination: {
                page: 1,
                pageSize: 20,
                total: validatedResponse.totalResults,
                hasNext: validatedResponse.totalResults > 20,
                hasPrevious: false,
              },
              isLoading: false,
              lastUpdated: new Date().toISOString(),
            }));

            return searchId;
          } catch (error) {
            const errorMessage =
              error instanceof Error ? error.message : "Search failed";

            set((state: ValidatedSearchStore) => ({
              ...state,
              isLoading: false,
              error: errorMessage,
              lastUpdated: new Date().toISOString(),
            }));

            throw error;
          }
        },

        clearResults: () => {
          set((state: ValidatedSearchStore) => ({
            ...state,
            results: {},
            pagination: undefined,
            error: null,
            lastUpdated: new Date().toISOString(),
          }));
        },

        setFilters: (filters: Record<string, unknown>): void => {
          set((state: ValidatedSearchStore) => ({
            ...state,
            filters,
            lastUpdated: new Date().toISOString(),
          }));
        },

        setSorting: (field: string, direction: "asc" | "desc"): void => {
          set((state: ValidatedSearchStore) => ({
            ...state,
            sorting: { field, direction },
            lastUpdated: new Date().toISOString(),
          }));
        },

        loadMore: async () => {
          const state = get();
          if (!state.pagination?.hasNext || state.isLoading) return;

          set((prevState: ValidatedSearchStore) => ({ ...prevState, isLoading: true }));

          try {
            // Simulate loading more results
            await new Promise((resolve) => setTimeout(resolve, 500));

            set((state: ValidatedSearchStore) => ({
              ...state,
              pagination: state.pagination
                ? {
                    ...state.pagination,
                    page: state.pagination.page + 1,
                    hasNext: false, // Simulate no more results
                  }
                : undefined,
              isLoading: false,
              lastUpdated: new Date().toISOString(),
            }));
          } catch (error) {
            set((state: ValidatedSearchStore) => ({
              ...state,
              isLoading: false,
              error:
                error instanceof Error ? error.message : "Failed to load more results",
            }));
          }
        },

        saveSearch: async (name: string): Promise<string> => {
          const state = get();
          if (!state.currentSearchType || !state.currentParams) {
            throw new Error("No search to save");
          }

          const searchId = `saved_${Date.now()}`;
          const savedSearch = {
            id: searchId,
            name,
            type: state.currentSearchType,
            params: state.currentParams,
            createdAt: new Date().toISOString(),
          };

          set((state: ValidatedSearchStore) => ({
            ...state,
            savedSearches: [...state.savedSearches, savedSearch],
            lastUpdated: new Date().toISOString(),
          }));

          return searchId;
        },

        loadSavedSearch: async (searchId: string): Promise<boolean> => {
          const state = get();
          const savedSearch = state.savedSearches.find((s: any) => s.id === searchId);

          if (!savedSearch) {
            return false;
          }

          set((state: ValidatedSearchStore) => ({
            ...state,
            currentSearchType: savedSearch.type,
            currentParams: savedSearch.params,
            savedSearches: state.savedSearches.map((s) =>
              s.id === searchId ? { ...s, lastUsed: new Date().toISOString() } : s
            ),
            lastUpdated: new Date().toISOString(),
          }));

          return true;
        },

        deleteSavedSearch: (searchId: string): void => {
          set((state: ValidatedSearchStore) => ({
            ...state,
            savedSearches: state.savedSearches.filter((s) => s.id !== searchId),
            lastUpdated: new Date().toISOString(),
          }));
        },

        addToRecentSearches: (type: SearchType, params: SearchParams): void => {
          const searchEntry = {
            id: `recent_${Date.now()}`,
            type,
            params,
            timestamp: new Date().toISOString(),
          };

          set((state: ValidatedSearchStore) => ({
            ...state,
            recentSearches: [searchEntry, ...state.recentSearches.slice(0, 9)], // Keep last 10
            lastUpdated: new Date().toISOString(),
          }));
        },

        clearRecentSearches: () => {
          set((state: ValidatedSearchStore) => ({
            ...state,
            recentSearches: [],
            lastUpdated: new Date().toISOString(),
          }));
        },

        reset: () => {
          set({
            currentSearchType: null,
            currentParams: null,
            results: {},
            filters: {},
            sorting: undefined,
            pagination: undefined,
            recentSearches: [],
            savedSearches: [],
            isLoading: false,
            error: null,
            lastUpdated: new Date().toISOString(),
          });
        },

        // Validation helpers
        validateCurrentState: () => {
          const state = get();
          const result = validateStoreState(
            searchStoreStateSchema,
            state,
            "ValidatedSearchStore"
          );
          return result.success;
        },

        getValidationErrors: () => {
          const state = get();
          const result = validateStoreState(
            searchStoreStateSchema,
            state,
            "ValidatedSearchStore"
          );

          if (result.success) {
            return [];
          }

          return (
            result.errors?.map((error) => error.message) || ["Unknown validation error"]
          );
        },
      }),
      { name: "ValidatedSearchStore" }
    )
  )
);

// Selectors with type safety
export const useSearchType = () =>
  useValidatedSearchStore((state) => state.currentSearchType);
export const useSearchParams = () =>
  useValidatedSearchStore((state) => state.currentParams);
export const useSearchResults = () => useValidatedSearchStore((state) => state.results);
export const useSearchLoading = () =>
  useValidatedSearchStore((state) => state.isLoading);
export const useSearchError = () => useValidatedSearchStore((state) => state.error);
export const useRecentSearches = () =>
  useValidatedSearchStore((state) => state.recentSearches);
export const useSavedSearches = () =>
  useValidatedSearchStore((state) => state.savedSearches);

// Validation hooks
export const useStoreValidation = () => {
  const validateCurrentState = useValidatedSearchStore(
    (state) => state.validateCurrentState
  );
  const getValidationErrors = useValidatedSearchStore(
    (state) => state.getValidationErrors
  );

  return {
    validateCurrentState,
    getValidationErrors,
  };
};

// Development helpers
if (process.env.NODE_ENV === "development") {
  // Subscribe to state changes for validation monitoring
  useValidatedSearchStore.subscribe(
    (state) => state,
    (state) => {
      const result = validateStoreState(
        searchStoreStateSchema,
        state,
        "ValidatedSearchStore"
      );
      if (!result.success) {
        console.warn("Store state validation failed:", result.errors);
      }
    }
  );
}
