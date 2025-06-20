import type {
  AccommodationSearchParams,
  ActivitySearchParams,
  DestinationSearchParams,
  FlightSearchParams,
  SearchParams,
  SearchType,
} from "@/types/search";
import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas for search parameters
const SearchTypeSchema = z.enum(["flight", "accommodation", "activity", "destination"]);

const BaseSearchParamsSchema = z.object({
  adults: z.number().min(1).max(20).default(1),
  children: z.number().min(0).max(10).default(0),
  infants: z.number().min(0).max(5).default(0),
});

const FlightSearchParamsSchema = BaseSearchParamsSchema.extend({
  origin: z.string().optional(),
  destination: z.string().optional(),
  departureDate: z.string().optional(),
  returnDate: z.string().optional(),
  cabinClass: z
    .enum(["economy", "premium_economy", "business", "first"])
    .default("economy"),
  directOnly: z.boolean().default(false),
  maxStops: z.number().min(0).max(3).optional(),
  preferredAirlines: z.array(z.string()).default([]),
  excludedAirlines: z.array(z.string()).default([]),
});

const AccommodationSearchParamsSchema = BaseSearchParamsSchema.extend({
  destination: z.string().optional(),
  checkIn: z.string().optional(),
  checkOut: z.string().optional(),
  rooms: z.number().min(1).max(10).default(1),
  propertyType: z.enum(["hotel", "apartment", "villa", "hostel", "resort"]).optional(),
  minRating: z.number().min(1).max(5).optional(),
  amenities: z.array(z.string()).default([]),
  priceRange: z
    .object({
      min: z.number().min(0).optional(),
      max: z.number().min(0).optional(),
    })
    .optional(),
});

const ActivitySearchParamsSchema = BaseSearchParamsSchema.extend({
  destination: z.string().optional(),
  date: z.string().optional(),
  category: z.string().optional(),
  duration: z
    .object({
      min: z.number().min(0).optional(),
      max: z.number().min(0).optional(),
    })
    .optional(),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  indoor: z.boolean().optional(),
});

const DestinationSearchParamsSchema = z.object({
  query: z.string().default(""),
  limit: z.number().min(1).max(50).default(10),
  types: z.array(z.string()).default(["locality", "country"]),
  bounds: z
    .object({
      north: z.number(),
      south: z.number(),
      east: z.number(),
      west: z.number(),
    })
    .optional(),
  countryCode: z.string().optional(),
});

// Types derived from schemas
export type ValidatedFlightParams = z.infer<typeof FlightSearchParamsSchema>;
export type ValidatedAccommodationParams = z.infer<
  typeof AccommodationSearchParamsSchema
>;
export type ValidatedActivityParams = z.infer<typeof ActivitySearchParamsSchema>;
export type ValidatedDestinationParams = z.infer<typeof DestinationSearchParamsSchema>;

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
const _generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const _getCurrentTimestamp = () => new Date().toISOString();

// Default parameter generators
const getDefaultFlightParams = (): Partial<ValidatedFlightParams> => ({
  adults: 1,
  children: 0,
  infants: 0,
  cabinClass: "economy",
  directOnly: false,
  preferredAirlines: [],
  excludedAirlines: [],
});

const getDefaultAccommodationParams = (): Partial<ValidatedAccommodationParams> => ({
  adults: 1,
  children: 0,
  infants: 0,
  rooms: 1,
  amenities: [],
});

const getDefaultActivityParams = (): Partial<ValidatedActivityParams> => ({
  adults: 1,
  children: 0,
  infants: 0,
});

const getDefaultDestinationParams = (): Partial<ValidatedDestinationParams> => ({
  query: "",
  limit: 10,
  types: ["locality", "country"],
});

const getDefaultParams = (type: SearchType): Partial<SearchParams> => {
  switch (type) {
    case "flight":
      return getDefaultFlightParams() as Partial<SearchParams>;
    case "accommodation":
      return getDefaultAccommodationParams() as Partial<SearchParams>;
    case "activity":
      return getDefaultActivityParams() as Partial<SearchParams>;
    case "destination":
      return getDefaultDestinationParams() as Partial<SearchParams>;
    default:
      return {};
  }
};

// Validation helpers
const validateSearchParams = async (
  params: Partial<SearchParams>,
  type: SearchType
): Promise<boolean> => {
  try {
    switch (type) {
      case "flight":
        FlightSearchParamsSchema.parse(params);
        break;
      case "accommodation":
        AccommodationSearchParamsSchema.parse(params);
        break;
      case "activity":
        ActivitySearchParamsSchema.parse(params);
        break;
      case "destination":
        DestinationSearchParamsSchema.parse(params);
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
        // Initial state
        currentSearchType: null,
        flightParams: {},
        accommodationParams: {},
        activityParams: {},
        destinationParams: {},

        // Validation states
        isValidating: {
          flight: false,
          accommodation: false,
          activity: false,
          destination: false,
        },
        validationErrors: {
          flight: null,
          accommodation: null,
          activity: null,
          destination: null,
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
              return accommodationParams as AccommodationSearchParams;
            case "activity":
              return activityParams as ActivitySearchParams;
            case "destination":
              return destinationParams as DestinationSearchParams;
            default:
              return null;
          }
        },

        get hasValidParams() {
          const { currentSearchType, currentParams } = get();
          if (!currentSearchType || !currentParams) return false;

          // Check if required fields are present based on search type
          switch (currentSearchType) {
            case "flight":
              return (
                !!(currentParams as FlightSearchParams).origin &&
                !!(currentParams as FlightSearchParams).destination &&
                !!(currentParams as FlightSearchParams).departureDate
              );
            case "accommodation":
              return (
                !!(currentParams as AccommodationSearchParams).destination &&
                !!(currentParams as AccommodationSearchParams).checkIn &&
                !!(currentParams as AccommodationSearchParams).checkOut
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

          const defaultParams = getDefaultParams(currentSearchType);
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

        // Parameter management actions
        setSearchType: (type) => {
          const result = SearchTypeSchema.safeParse(type);
          if (result.success) {
            set((state) => {
              const updatedState: Partial<SearchParamsState> = {
                currentSearchType: result.data,
              };

              // Initialize default parameters if not set yet
              switch (result.data) {
                case "flight":
                  if (Object.keys(state.flightParams).length === 0) {
                    updatedState.flightParams = getDefaultFlightParams();
                  }
                  break;
                case "accommodation":
                  if (Object.keys(state.accommodationParams).length === 0) {
                    updatedState.accommodationParams = getDefaultAccommodationParams();
                  }
                  break;
                case "activity":
                  if (Object.keys(state.activityParams).length === 0) {
                    updatedState.activityParams = getDefaultActivityParams();
                  }
                  break;
                case "destination":
                  if (Object.keys(state.destinationParams).length === 0) {
                    updatedState.destinationParams = getDefaultDestinationParams();
                  }
                  break;
              }

              return updatedState;
            });
          } else {
            console.error("Invalid search type:", result.error);
          }
        },

        updateFlightParams: async (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, flight: true },
            validationErrors: { ...state.validationErrors, flight: null },
          }));

          try {
            const updatedParams = { ...get().flightParams, ...params };
            const result = FlightSearchParamsSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                flightParams: result.data,
                isValidating: { ...state.isValidating, flight: false },
              }));
              return true;
            }
            throw new Error("Invalid flight parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, flight: false },
              validationErrors: { ...state.validationErrors, flight: message },
            }));
            return false;
          }
        },

        updateAccommodationParams: async (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, accommodation: true },
            validationErrors: { ...state.validationErrors, accommodation: null },
          }));

          try {
            const updatedParams = { ...get().accommodationParams, ...params };
            const result = AccommodationSearchParamsSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                accommodationParams: result.data,
                isValidating: { ...state.isValidating, accommodation: false },
              }));
              return true;
            }
            throw new Error("Invalid accommodation parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, accommodation: false },
              validationErrors: { ...state.validationErrors, accommodation: message },
            }));
            return false;
          }
        },

        updateActivityParams: async (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, activity: true },
            validationErrors: { ...state.validationErrors, activity: null },
          }));

          try {
            const updatedParams = { ...get().activityParams, ...params };
            const result = ActivitySearchParamsSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                activityParams: result.data,
                isValidating: { ...state.isValidating, activity: false },
              }));
              return true;
            }
            throw new Error("Invalid activity parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, activity: false },
              validationErrors: { ...state.validationErrors, activity: message },
            }));
            return false;
          }
        },

        updateDestinationParams: async (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, destination: true },
            validationErrors: { ...state.validationErrors, destination: null },
          }));

          try {
            const updatedParams = { ...get().destinationParams, ...params };
            const result = DestinationSearchParamsSchema.safeParse(updatedParams);

            if (result.success) {
              set((state) => ({
                destinationParams: result.data,
                isValidating: { ...state.isValidating, destination: false },
              }));
              return true;
            }
            throw new Error("Invalid destination parameters");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, destination: false },
              validationErrors: { ...state.validationErrors, destination: message },
            }));
            return false;
          }
        },

        // Bulk operations
        setFlightParams: (params) => {
          const result = FlightSearchParamsSchema.safeParse(params);
          if (result.success) {
            set({ flightParams: result.data });
          } else {
            console.error("Invalid flight parameters:", result.error);
          }
        },

        setAccommodationParams: (params) => {
          const result = AccommodationSearchParamsSchema.safeParse(params);
          if (result.success) {
            set({ accommodationParams: result.data });
          } else {
            console.error("Invalid accommodation parameters:", result.error);
          }
        },

        setActivityParams: (params) => {
          const result = ActivitySearchParamsSchema.safeParse(params);
          if (result.success) {
            set({ activityParams: result.data });
          } else {
            console.error("Invalid activity parameters:", result.error);
          }
        },

        setDestinationParams: (params) => {
          const result = DestinationSearchParamsSchema.safeParse(params);
          if (result.success) {
            set({ destinationParams: result.data });
          } else {
            console.error("Invalid destination parameters:", result.error);
          }
        },

        // Reset and validation
        resetParams: (type) => {
          if (!type) {
            set({
              flightParams: {},
              accommodationParams: {},
              activityParams: {},
              destinationParams: {},
            });
            return;
          }

          switch (type) {
            case "flight":
              set({ flightParams: getDefaultFlightParams() });
              break;
            case "accommodation":
              set({ accommodationParams: getDefaultAccommodationParams() });
              break;
            case "activity":
              set({ activityParams: getDefaultActivityParams() });
              break;
            case "destination":
              set({ destinationParams: getDefaultDestinationParams() });
              break;
          }
        },

        resetCurrentParams: () => {
          const { currentSearchType } = get();
          if (currentSearchType) {
            get().resetParams(currentSearchType);
          }
        },

        validateParams: async (type) => {
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
              return false;
          }

          return await validateSearchParams(params, type);
        },

        validateCurrentParams: async () => {
          const { currentSearchType } = get();
          if (!currentSearchType) return false;

          return await get().validateParams(currentSearchType);
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

        createParamsTemplate: () => {
          const { currentParams } = get();
          return currentParams ? { ...currentParams } : null;
        },

        // Utility actions
        clearValidationErrors: () => {
          set({
            validationErrors: {
              flight: null,
              accommodation: null,
              activity: null,
              destination: null,
            },
          });
        },

        clearValidationError: (type) => {
          set((state) => ({
            validationErrors: {
              ...state.validationErrors,
              [type]: null,
            },
          }));
        },

        markClean: () => {
          // This getter will automatically update the isDirty computed property
          get().isDirty;
        },

        reset: () => {
          set({
            currentSearchType: null,
            flightParams: {},
            accommodationParams: {},
            activityParams: {},
            destinationParams: {},
            isValidating: {
              flight: false,
              accommodation: false,
              activity: false,
              destination: false,
            },
            validationErrors: {
              flight: null,
              accommodation: null,
              activity: null,
              destination: null,
            },
          });
        },
      }),
      {
        name: "search-params-storage",
        partialize: (state) => ({
          // Only persist parameters, not validation states
          currentSearchType: state.currentSearchType,
          flightParams: state.flightParams,
          accommodationParams: state.accommodationParams,
          activityParams: state.activityParams,
          destinationParams: state.destinationParams,
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
    isValidating: state.isValidating,
    validationErrors: state.validationErrors,
    hasValidParams: state.hasValidParams,
    isDirty: state.isDirty,
  }));
