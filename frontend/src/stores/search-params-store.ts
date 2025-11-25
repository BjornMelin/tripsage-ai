import type {
  ActivitySearchParams,
  DestinationSearchParams,
  FlightSearchParams,
  SearchAccommodationParams,
  SearchParams,
} from "@schemas/search";
import {
  accommodationSearchParamsStoreSchema,
  activitySearchParamsStoreSchema,
  destinationSearchParamsStoreSchema,
  flightSearchParamsStoreSchema,
  type SearchType,
  searchTypeSchema,
  type ValidatedAccommodationParams,
  type ValidatedActivityParams,
  type ValidatedDestinationParams,
  type ValidatedFlightParams,
} from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Schemas are consumed directly from @schemas/stores; no local re-exports.

// Search parameters store interface
interface SearchParamsState {
  // Current search context
  currentSearchType: SearchType | null;

  // Search parameters for each type
  flightParams: Partial<ValidatedFlightParams>;
  accommodationParams: Partial<ValidatedAccommodationParams>;
  activityParams: Partial<ValidatedActivityParams>;
  destinationParams: Partial<ValidatedDestinationParams>;

  // Validation states
  isValidating: Record<SearchType, boolean>;
  validationErrors: Record<SearchType, string | null>;

  // Computed properties
  currentParams: SearchParams | null;
  hasValidParams: boolean;
  isDirty: boolean;

  // Parameter management actions
  setSearchType: (type: SearchType) => void;
  updateFlightParams: (params: Partial<ValidatedFlightParams>) => Promise<boolean>;
  updateAccommodationParams: (
    params: Partial<ValidatedAccommodationParams>
  ) => Promise<boolean>;
  updateActivityParams: (params: Partial<ValidatedActivityParams>) => Promise<boolean>;
  updateDestinationParams: (
    params: Partial<ValidatedDestinationParams>
  ) => Promise<boolean>;

  // Bulk operations
  setFlightParams: (params: Partial<ValidatedFlightParams>) => void;
  setAccommodationParams: (params: Partial<ValidatedAccommodationParams>) => void;
  setActivityParams: (params: Partial<ValidatedActivityParams>) => void;
  setDestinationParams: (params: Partial<ValidatedDestinationParams>) => void;

  // Reset and validation
  resetParams: (type?: SearchType) => void;
  resetCurrentParams: () => void;
  validateParams: (type: SearchType) => Promise<boolean>;
  validateCurrentParams: () => Promise<boolean>;

  // Template and presets
  loadParamsFromTemplate: (
    template: SearchParams,
    type: SearchType
  ) => Promise<boolean>;
  createParamsTemplate: () => SearchParams | null;

  // Utility actions
  clearValidationErrors: () => void;
  clearValidationError: (type: SearchType) => void;
  markClean: () => void;
  reset: () => void;
}

// Helper functions
// const generateId = () =>
//   Date.now().toString(36) + Math.random().toString(36).substring(2, 5); // Future use
// const getCurrentTimestamp = () => new Date().toISOString(); // Future use

// Default parameter generators
const GET_DEFAULT_FLIGHT_PARAMS = (): Partial<ValidatedFlightParams> => ({
  adults: 1,
  cabinClass: "economy",
  children: 0,
  directOnly: false,
  excludedAirlines: [],
  infants: 0,
  preferredAirlines: [],
});

const GET_DEFAULT_ACCOMMODATION_PARAMS = (): Partial<ValidatedAccommodationParams> => ({
  adults: 1,
  amenities: [],
  children: 0,
  infants: 0,
  rooms: 1,
});

const GET_DEFAULT_ACTIVITY_PARAMS = (): Partial<ValidatedActivityParams> => ({
  adults: 1,
  children: 0,
  infants: 0,
});

const GET_DEFAULT_DESTINATION_PARAMS = (): Partial<ValidatedDestinationParams> => ({
  limit: 10,
  query: "",
  types: ["locality", "country"],
});

const GET_DEFAULT_PARAMS = (type: SearchType): Partial<SearchParams> => {
  switch (type) {
    case "flight":
      return GET_DEFAULT_FLIGHT_PARAMS() as Partial<SearchParams>;
    case "accommodation":
      return GET_DEFAULT_ACCOMMODATION_PARAMS() as Partial<SearchParams>;
    case "activity":
      return GET_DEFAULT_ACTIVITY_PARAMS() as Partial<SearchParams>;
    case "destination":
      return GET_DEFAULT_DESTINATION_PARAMS() as Partial<SearchParams>;
    default:
      return {};
  }
};

// Validation helpers
const VALIDATE_SEARCH_PARAMS = (
  params: Partial<SearchParams>,
  type: SearchType
): boolean => {
  try {
    switch (type) {
      case "flight":
        flightSearchParamsStoreSchema.parse(params);
        break;
      case "accommodation":
        accommodationSearchParamsStoreSchema.parse(params);
        break;
      case "activity":
        activitySearchParamsStoreSchema.parse(params);
        break;
      case "destination":
        destinationSearchParamsStoreSchema.parse(params);
        break;
      default:
        throw new Error(`Unknown search type: ${type}`);
    }
    return true;
  } catch (error) {
    console.error(`Validation failed for ${type}:`, error);
    return false;
  }
};

export const useSearchParamsStore = create<SearchParamsState>()(
  devtools(
    persist(
      (set, get) => ({
        accommodationParams: {},
        activityParams: {},

        clearValidationError: (type) => {
          set((state) => ({
            validationErrors: {
              ...state.validationErrors,
              [type]: null,
            },
          }));
        },

        // Utility actions
        clearValidationErrors: () => {
          set({
            validationErrors: {
              accommodation: null,
              activity: null,
              destination: null,
              flight: null,
            },
          });
        },

        createParamsTemplate: () => {
          const { currentParams } = get();
          return currentParams ? { ...currentParams } : null;
        },

        // Computed properties
        get currentParams() {
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
              return accommodationParams as SearchAccommodationParams;
            case "activity":
              return activityParams as ActivitySearchParams;
            case "destination":
              return destinationParams as DestinationSearchParams;
            default:
              return null;
          }
        },
        // Initial state
        currentSearchType: null,
        destinationParams: {},
        flightParams: {},

        get hasValidParams() {
          const { currentSearchType, currentParams } = get();
          if (!currentSearchType || !currentParams) return false;

          switch (currentSearchType) {
            case "flight":
              return (
                !!(currentParams as FlightSearchParams).origin &&
                !!(currentParams as FlightSearchParams).destination &&
                !!(currentParams as FlightSearchParams).departureDate
              );
            case "accommodation":
              return (
                !!(currentParams as SearchAccommodationParams).destination &&
                !!(currentParams as SearchAccommodationParams).checkIn &&
                !!(currentParams as SearchAccommodationParams).checkOut
              );
            case "activity":
              return !!(currentParams as ActivitySearchParams).destination;
            case "destination":
              return !!(currentParams as DestinationSearchParams).query;
            default:
              return false;
          }
        },

        get isDirty() {
          const {
            currentSearchType,
            flightParams,
            accommodationParams,
            activityParams,
            destinationParams,
          } = get();

          if (!currentSearchType) return false;

          const defaultParams = GET_DEFAULT_PARAMS(currentSearchType);
          let currentParams: Partial<SearchParams>;

          switch (currentSearchType) {
            case "flight":
              currentParams = flightParams;
              break;
            case "accommodation":
              currentParams = accommodationParams;
              break;
            case "activity":
              currentParams = activityParams;
              break;
            case "destination":
              currentParams = destinationParams as Partial<SearchParams>;
              break;
            default:
              return false;
          }

          return JSON.stringify(currentParams) !== JSON.stringify(defaultParams);
        },

        // Validation states
        isValidating: {
          accommodation: false,
          activity: false,
          destination: false,
          flight: false,
        },

        // Template and presets
        loadParamsFromTemplate: async (template, type) => {
          try {
            switch (type) {
              case "flight":
                return await get().updateFlightParams(
                  template as Partial<ValidatedFlightParams>
                );
              case "accommodation":
                return await get().updateAccommodationParams(
                  template as Partial<ValidatedAccommodationParams>
                );
              case "activity":
                return await get().updateActivityParams(
                  template as Partial<ValidatedActivityParams>
                );
              case "destination":
                return await get().updateDestinationParams(
                  template as Partial<ValidatedDestinationParams>
                );
              default:
                return false;
            }
          } catch (error) {
            console.error("Failed to load params from template:", error);
            return false;
          }
        },

        markClean: () => {
          // This getter will automatically update the isDirty computed property
          get().isDirty;
        },

        reset: () => {
          set({
            accommodationParams: {},
            activityParams: {},
            currentSearchType: null,
            destinationParams: {},
            flightParams: {},
            isValidating: {
              accommodation: false,
              activity: false,
              destination: false,
              flight: false,
            },
            validationErrors: {
              accommodation: null,
              activity: null,
              destination: null,
              flight: null,
            },
          });
        },

        resetCurrentParams: () => {
          const { currentSearchType } = get();
          if (currentSearchType) {
            get().resetParams(currentSearchType);
          }
        },

        // Reset and validation
        resetParams: (type) => {
          if (!type) {
            set({
              accommodationParams: {},
              activityParams: {},
              destinationParams: {},
              flightParams: {},
            });
            return;
          }

          switch (type) {
            case "flight":
              set({ flightParams: GET_DEFAULT_FLIGHT_PARAMS() });
              break;
            case "accommodation":
              set({ accommodationParams: GET_DEFAULT_ACCOMMODATION_PARAMS() });
              break;
            case "activity":
              set({ activityParams: GET_DEFAULT_ACTIVITY_PARAMS() });
              break;
            case "destination":
              set({ destinationParams: GET_DEFAULT_DESTINATION_PARAMS() });
              break;
          }
        },

        setAccommodationParams: (params) => {
          const result = accommodationSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set({ accommodationParams: result.data });
          } else {
            console.error("Invalid accommodation parameters:", result.error);
          }
        },

        setActivityParams: (params) => {
          const result = activitySearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set({ activityParams: result.data });
          } else {
            console.error("Invalid activity parameters:", result.error);
          }
        },

        setDestinationParams: (params) => {
          const result = destinationSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set({ destinationParams: result.data });
          } else {
            console.error("Invalid destination parameters:", result.error);
          }
        },

        // Bulk operations
        setFlightParams: (params) => {
          const result = flightSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set({ flightParams: result.data });
          } else {
            console.error("Invalid flight parameters:", result.error);
          }
        },

        // Parameter management actions
        setSearchType: (type) => {
          const result = searchTypeSchema.safeParse(type);
          if (result.success) {
            set((state) => {
              const updatedState: Partial<SearchParamsState> = {
                currentSearchType: result.data,
              };

              // Initialize default parameters if not set yet
              switch (result.data) {
                case "flight":
                  if (Object.keys(state.flightParams).length === 0) {
                    updatedState.flightParams = GET_DEFAULT_FLIGHT_PARAMS();
                  }
                  break;
                case "accommodation":
                  if (Object.keys(state.accommodationParams).length === 0) {
                    updatedState.accommodationParams =
                      GET_DEFAULT_ACCOMMODATION_PARAMS();
                  }
                  break;
                case "activity":
                  if (Object.keys(state.activityParams).length === 0) {
                    updatedState.activityParams = GET_DEFAULT_ACTIVITY_PARAMS();
                  }
                  break;
                case "destination":
                  if (Object.keys(state.destinationParams).length === 0) {
                    updatedState.destinationParams = GET_DEFAULT_DESTINATION_PARAMS();
                  }
                  break;
              }

              return updatedState;
            });
          } else {
            console.error("Invalid search type:", result.error);
          }
        },

        updateAccommodationParams: (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, accommodation: true },
            validationErrors: { ...state.validationErrors, accommodation: null },
          }));

          try {
            const updatedParams = { ...get().accommodationParams, ...params };
            const result =
              accommodationSearchParamsStoreSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                accommodationParams: result.data,
                isValidating: { ...state.isValidating, accommodation: false },
              }));
              return Promise.resolve(true);
            }
            throw new Error("Invalid accommodation parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, accommodation: false },
              validationErrors: { ...state.validationErrors, accommodation: message },
            }));
            return Promise.resolve(false);
          }
        },

        updateActivityParams: (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, activity: true },
            validationErrors: { ...state.validationErrors, activity: null },
          }));

          try {
            const updatedParams = { ...get().activityParams, ...params };
            const result = activitySearchParamsStoreSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                activityParams: result.data,
                isValidating: { ...state.isValidating, activity: false },
              }));
              return Promise.resolve(true);
            }
            throw new Error("Invalid activity parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, activity: false },
              validationErrors: { ...state.validationErrors, activity: message },
            }));
            return Promise.resolve(false);
          }
        },

        updateDestinationParams: (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, destination: true },
            validationErrors: { ...state.validationErrors, destination: null },
          }));

          try {
            const updatedParams = { ...get().destinationParams, ...params };
            const result = destinationSearchParamsStoreSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                destinationParams: result.data,
                isValidating: { ...state.isValidating, destination: false },
              }));
              return Promise.resolve(true);
            }
            throw new Error("Invalid destination parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, destination: false },
              validationErrors: { ...state.validationErrors, destination: message },
            }));
            return Promise.resolve(false);
          }
        },

        updateFlightParams: (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, flight: true },
            validationErrors: { ...state.validationErrors, flight: null },
          }));

          try {
            const updatedParams = { ...get().flightParams, ...params };
            const result = flightSearchParamsStoreSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                flightParams: result.data,
                isValidating: { ...state.isValidating, flight: false },
              }));
              return Promise.resolve(true);
            }
            throw new Error("Invalid flight parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, flight: false },
              validationErrors: { ...state.validationErrors, flight: message },
            }));
            return Promise.resolve(false);
          }
        },

        validateCurrentParams: async () => {
          const { currentSearchType } = get();
          if (!currentSearchType) return false;

          return await get().validateParams(currentSearchType);
        },

        validateParams: (type) => {
          const {
            flightParams,
            accommodationParams,
            activityParams,
            destinationParams,
          } = get();

          let params: Partial<SearchParams>;
          switch (type) {
            case "flight":
              params = flightParams;
              break;
            case "accommodation":
              params = accommodationParams;
              break;
            case "activity":
              params = activityParams;
              break;
            case "destination":
              params = destinationParams as Partial<SearchParams>;
              break;
            default:
              return Promise.resolve(false);
          }

          return Promise.resolve(VALIDATE_SEARCH_PARAMS(params, type));
        },
        validationErrors: {
          accommodation: null,
          activity: null,
          destination: null,
          flight: null,
        },
      }),
      {
        name: "search-params-storage",
        partialize: (state) => ({
          accommodationParams: state.accommodationParams,
          activityParams: state.activityParams,
          // Only persist parameters, not validation states
          currentSearchType: state.currentSearchType,
          destinationParams: state.destinationParams,
          flightParams: state.flightParams,
        }),
      }
    ),
    { name: "SearchParamsStore" }
  )
);

// Utility selectors for common use cases
export const useSearchType = () =>
  useSearchParamsStore((state) => state.currentSearchType);
export const useCurrentSearchParams = () =>
  useSearchParamsStore((state) => state.currentParams);
export const useFlightParams = () =>
  useSearchParamsStore((state) => state.flightParams);
export const useAccommodationParams = () =>
  useSearchParamsStore((state) => state.accommodationParams);
export const useActivityParams = () =>
  useSearchParamsStore((state) => state.activityParams);
export const useDestinationParams = () =>
  useSearchParamsStore((state) => state.destinationParams);
export const useSearchParamsValidation = () =>
  useSearchParamsStore((state) => ({
    hasValidParams: state.hasValidParams,
    isDirty: state.isDirty,
    isValidating: state.isValidating,
    validationErrors: state.validationErrors,
  }));

/**
 * Compute the current parameters based on the store state snapshot.
 *
 * @param state - The search params store state snapshot.
 * @returns The params object for the current search type, or null.
 */
export const selectCurrentParamsFrom = (
  state: SearchParamsState
): SearchParams | null => {
  if (!state.currentSearchType) return null;
  switch (state.currentSearchType) {
    case "flight":
      return state.flightParams as FlightSearchParams;
    case "accommodation":
      return state.accommodationParams as SearchAccommodationParams;
    case "activity":
      return state.activityParams as ActivitySearchParams;
    case "destination":
      return state.destinationParams as DestinationSearchParams;
    default:
      return null;
  }
};
