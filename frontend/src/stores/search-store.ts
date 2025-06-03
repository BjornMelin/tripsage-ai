import type {
  AccommodationSearchParams,
  ActivitySearchParams,
  DestinationSearchParams,
  FilterOption,
  FlightSearchParams,
  SavedSearch,
  SearchParams,
  SearchResults,
  SearchType,
  SortOption,
} from "@/types/search";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SearchState {
  // Search parameters
  currentSearchType: SearchType | null;
  flightParams: Partial<FlightSearchParams>;
  accommodationParams: Partial<AccommodationSearchParams>;
  activityParams: Partial<ActivitySearchParams>;
  destinationParams: Partial<DestinationSearchParams>;

  // Results
  results: SearchResults;
  isLoading: boolean;
  error: string | null;

  // Filters and sorting
  availableFilters: Record<SearchType, FilterOption[]>;
  activeFilters: Record<string, any>;
  availableSortOptions: Record<SearchType, SortOption[]>;
  activeSortOption: SortOption | null;

  // Saved searches
  savedSearches: SavedSearch[];
  recentSearches: Array<{
    type: SearchType;
    params: SearchParams;
    timestamp: string;
  }>;

  // Computed properties
  currentParams: SearchParams | null;

  // Actions
  setSearchType: (type: SearchType) => void;
  updateFlightParams: (params: Partial<FlightSearchParams>) => void;
  updateAccommodationParams: (params: Partial<AccommodationSearchParams>) => void;
  updateActivityParams: (params: Partial<ActivitySearchParams>) => void;
  updateDestinationParams: (params: Partial<DestinationSearchParams>) => void;
  resetParams: (type?: SearchType) => void;

  setResults: (results: SearchResults) => void;
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearResults: () => void;

  setAvailableFilters: (type: SearchType, filters: FilterOption[]) => void;
  setActiveFilter: (filterId: string, value: any) => void;
  clearFilters: () => void;

  setAvailableSortOptions: (type: SearchType, options: SortOption[]) => void;
  setActiveSortOption: (option: SortOption | null) => void;

  saveSearch: (name: string) => void;
  deleteSearch: (id: string) => void;
  addRecentSearch: () => void;
  clearRecentSearches: () => void;
}

const getDefaultSearchParams = (type: SearchType): Partial<SearchParams> => {
  const baseParams = {
    adults: 1,
    children: 0,
    infants: 0,
  };

  switch (type) {
    case "flight":
      return {
        ...baseParams,
        cabinClass: "economy" as const,
        directOnly: false,
      };
    case "accommodation":
      return {
        ...baseParams,
        rooms: 1,
      };
    case "activity":
      return {
        ...baseParams,
      };
    case "destination":
      return {
        query: "",
        limit: 10,
        types: ["locality", "country"],
      };
    default:
      return baseParams;
  }
};

const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

export const useSearchStore = create<SearchState>()(
  persist(
    (set, get) => ({
      // Initial state
      currentSearchType: null,
      flightParams: {},
      accommodationParams: {},
      activityParams: {},
      destinationParams: {},

      results: {},
      isLoading: false,
      error: null,

      availableFilters: {
        flight: [],
        accommodation: [],
        activity: [],
        destination: [],
      },
      activeFilters: {},
      availableSortOptions: {
        flight: [],
        accommodation: [],
        activity: [],
        destination: [],
      },
      activeSortOption: null,

      savedSearches: [],
      recentSearches: [],

      // Computed property for current parameters based on search type
      get currentParams(): SearchParams | null {
        const {
          currentSearchType,
          flightParams,
          accommodationParams,
          activityParams,
          destinationParams,
        } = get();

        if (!currentSearchType) return null;

        switch (currentSearchType) {
          case "flight":
            return flightParams as FlightSearchParams;
          case "accommodation":
            return accommodationParams as AccommodationSearchParams;
          case "activity":
            return activityParams as ActivitySearchParams;
          case "destination":
            return destinationParams as DestinationSearchParams;
          default:
            return null;
        }
      },

      // Set search type and initialize default params if empty
      setSearchType: (type) =>
        set((state) => {
          // Initialize default parameters if not set yet
          const updatedState: Partial<SearchState> = {
            currentSearchType: type,
          };

          switch (type) {
            case "flight":
              if (Object.keys(state.flightParams).length === 0) {
                updatedState.flightParams = getDefaultSearchParams("flight");
              }
              break;
            case "accommodation":
              if (Object.keys(state.accommodationParams).length === 0) {
                updatedState.accommodationParams =
                  getDefaultSearchParams("accommodation");
              }
              break;
            case "activity":
              if (Object.keys(state.activityParams).length === 0) {
                updatedState.activityParams = getDefaultSearchParams("activity");
              }
              break;
            case "destination":
              if (Object.keys(state.destinationParams).length === 0) {
                updatedState.destinationParams = getDefaultSearchParams("destination");
              }
              break;
          }

          return updatedState;
        }),

      // Update search parameters
      updateFlightParams: (params) =>
        set((state) => ({
          flightParams: { ...state.flightParams, ...params },
        })),

      updateAccommodationParams: (params) =>
        set((state) => ({
          accommodationParams: { ...state.accommodationParams, ...params },
        })),

      updateActivityParams: (params) =>
        set((state) => ({
          activityParams: { ...state.activityParams, ...params },
        })),

      updateDestinationParams: (params) =>
        set((state) => ({
          destinationParams: { ...state.destinationParams, ...params },
        })),

      // Reset search parameters
      resetParams: (type) =>
        set((state) => {
          if (!type) {
            return {
              flightParams: {},
              accommodationParams: {},
              activityParams: {},
              destinationParams: {},
            };
          }

          switch (type) {
            case "flight":
              return { flightParams: getDefaultSearchParams("flight") };
            case "accommodation":
              return {
                accommodationParams: getDefaultSearchParams("accommodation"),
              };
            case "activity":
              return { activityParams: getDefaultSearchParams("activity") };
            case "destination":
              return {
                destinationParams: getDefaultSearchParams("destination"),
              };
            default:
              return {};
          }
        }),

      // Search results management
      setResults: (results) => set({ results, isLoading: false }),
      setIsLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error, isLoading: false }),
      clearResults: () => set({ results: {}, error: null }),

      // Filter management
      setAvailableFilters: (type, filters) =>
        set((state) => ({
          availableFilters: {
            ...state.availableFilters,
            [type]: filters,
          },
        })),

      setActiveFilter: (filterId, value) =>
        set((state) => ({
          activeFilters: {
            ...state.activeFilters,
            [filterId]: value,
          },
        })),

      clearFilters: () => set({ activeFilters: {} }),

      // Sort options management
      setAvailableSortOptions: (type, options) =>
        set((state) => ({
          availableSortOptions: {
            ...state.availableSortOptions,
            [type]: options,
          },
        })),

      setActiveSortOption: (option) => set({ activeSortOption: option }),

      // Saved searches management
      saveSearch: (name) =>
        set((state) => {
          const { currentSearchType, currentParams } = state;

          if (!currentSearchType || !currentParams) return state;

          const newSavedSearch: SavedSearch = {
            id: generateId(),
            type: currentSearchType,
            name,
            params: currentParams,
            createdAt: getCurrentTimestamp(),
          };

          return {
            savedSearches: [...state.savedSearches, newSavedSearch],
          };
        }),

      deleteSearch: (id) =>
        set((state) => ({
          savedSearches: state.savedSearches.filter((search) => search.id !== id),
        })),

      addRecentSearch: () =>
        set((state) => {
          const { currentSearchType, currentParams } = state;

          if (!currentSearchType || !currentParams) return state;

          const newRecentSearch = {
            type: currentSearchType,
            params: currentParams,
            timestamp: getCurrentTimestamp(),
          };

          // Keep only the 10 most recent searches
          const recentSearches = [newRecentSearch, ...state.recentSearches].slice(
            0,
            10
          );

          return { recentSearches };
        }),

      clearRecentSearches: () => set({ recentSearches: [] }),
    }),
    {
      name: "search-storage",
      partialize: (state) => ({
        // Only persist the saved searches and recent searches, not the current search params or results
        savedSearches: state.savedSearches,
        recentSearches: state.recentSearches,
      }),
    }
  )
);
