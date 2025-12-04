/**
 * @fileoverview Search parameters store.
 */

import type {
  ActivitySearchParams,
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
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { registerAllHandlers } from "./search-params/handlers";
import { getHandler } from "./search-params/registry";

// Ensure handlers are registered deterministically at startup
registerAllHandlers();

const logger = createStoreLogger({ storeName: "search-params" });

/** Schema registry for parameter validation by search type */
const PARAM_SCHEMAS = {
  accommodation: accommodationSearchParamsStoreSchema,
  activity: activitySearchParamsStoreSchema,
  destination: destinationSearchParamsStoreSchema,
  flight: flightSearchParamsStoreSchema,
} as const;

/** Keys for params in state by search type */
const PARAMS_KEY_MAP: Record<
  SearchType,
  "flightParams" | "accommodationParams" | "activityParams" | "destinationParams"
> = {
  accommodation: "accommodationParams",
  activity: "activityParams",
  destination: "destinationParams",
  flight: "flightParams",
};

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
  updateParams: (type: SearchType, params: Partial<SearchParams>) => Promise<boolean>;
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

/** Get default parameters for a search type using the handler. */
const getDefaultParams = (type: SearchType): Partial<SearchParams> => {
  return getHandler(type).getDefaults() as Partial<SearchParams>;
};

/** Validate search parameters using the handler. */
const validateSearchParams = (
  params: Partial<SearchParams>,
  type: SearchType
): boolean => {
  const result = getHandler(type).validate(params);
  if (!result.success) {
    logger.error(`Validation failed for ${type}`, { error: result.error });
  }
  return result.success;
};

/** Check if required parameters are present using the handler. */
const hasRequiredParams = (
  params: Partial<SearchParams>,
  type: SearchType
): boolean => {
  return getHandler(type).hasRequiredParams(params);
};

/** Get current params for a search type from state. */
const getParamsForType = (
  state: {
    flightParams: Partial<ValidatedFlightParams>;
    accommodationParams: Partial<ValidatedAccommodationParams>;
    activityParams: Partial<ValidatedActivityParams>;
    destinationParams: Partial<ValidatedDestinationParams>;
  },
  type: SearchType
): Partial<SearchParams> => {
  const paramsMap: Record<SearchType, Partial<SearchParams>> = {
    accommodation: state.accommodationParams as Partial<SearchParams>,
    activity: state.activityParams as Partial<SearchParams>,
    destination: state.destinationParams as Partial<SearchParams>,
    flight: state.flightParams as Partial<SearchParams>,
  };
  return paramsMap[type];
};

/** Compute derived current params and validity for the given state snapshot. */
const computeDerivedState = (
  state: Pick<
    SearchParamsState,
    | "accommodationParams"
    | "activityParams"
    | "currentSearchType"
    | "destinationParams"
    | "flightParams"
  >
): Pick<SearchParamsState, "currentParams" | "hasValidParams"> => {
  if (!state.currentSearchType) {
    return { currentParams: null, hasValidParams: false };
  }

  const currentParams = getParamsForType(
    state,
    state.currentSearchType
  ) as SearchParams;
  return {
    currentParams,
    hasValidParams: hasRequiredParams(currentParams, state.currentSearchType),
  };
};

/** Create a search params store instance. */
export const useSearchParamsStore = create<SearchParamsState>()(
  devtools(
    persist(
      (set, get) => ({
        accommodationParams: {},
        activityParams: {},

        /** Clear a specific validation error. */
        clearValidationError: (type) => {
          set((state) => ({
            validationErrors: {
              ...state.validationErrors,
              [type]: null,
            },
          }));
        },

        /** Clear all validation errors. */
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

        /** Create a template of current params for a search type. */
        createParamsTemplate: () => {
          const { currentParams } = get();
          return currentParams ? { ...currentParams } : null;
        },
        currentParams: null,

        // Initial state
        currentSearchType: null,
        destinationParams: {},
        flightParams: {},

        hasValidParams: false,

        get isDirty() {
          const state = get();
          if (!state.currentSearchType) return false;

          const defaultParams = getDefaultParams(state.currentSearchType);
          const currentParams = getParamsForType(state, state.currentSearchType);
          return JSON.stringify(currentParams) !== JSON.stringify(defaultParams);
        },

        /** Validation states. */
        isValidating: {
          accommodation: false,
          activity: false,
          destination: false,
          flight: false,
        },

        /** Load params from a template for a search type. */
        loadParamsFromTemplate: async (template, type) => {
          try {
            const updateFns: Record<
              SearchType,
              (params: Partial<SearchParams>) => Promise<boolean>
            > = {
              accommodation: (p) =>
                get().updateAccommodationParams(
                  p as Partial<ValidatedAccommodationParams>
                ),
              activity: (p) =>
                get().updateActivityParams(p as Partial<ValidatedActivityParams>),
              destination: (p) =>
                get().updateDestinationParams(p as Partial<ValidatedDestinationParams>),
              flight: (p) =>
                get().updateFlightParams(p as Partial<ValidatedFlightParams>),
            };
            const updateFn = updateFns[type];
            return updateFn ? await updateFn(template) : false;
          } catch (error) {
            logger.error("Failed to load params from template", { error });
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
            currentParams: null,
            currentSearchType: null,
            destinationParams: {},
            flightParams: {},
            hasValidParams: false,
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
            set((state) => {
              const updates = {
                accommodationParams: {},
                activityParams: {},
                destinationParams: {},
                flightParams: {},
              };
              const derived = computeDerivedState({ ...state, ...updates });
              return { ...updates, ...derived };
            });
            return;
          }

          const defaults = getHandler(type).getDefaults();
          const keyMap: Record<
            SearchType,
            keyof Pick<
              SearchParamsState,
              | "flightParams"
              | "accommodationParams"
              | "activityParams"
              | "destinationParams"
            >
          > = {
            accommodation: "accommodationParams",
            activity: "activityParams",
            destination: "destinationParams",
            flight: "flightParams",
          };
          const key = keyMap[type];
          const stateUpdate = { [key]: defaults } satisfies Partial<SearchParamsState>;
          set((state) => {
            const nextState = { ...state, ...stateUpdate } as SearchParamsState;
            const derived = computeDerivedState(nextState);
            return { ...stateUpdate, ...derived };
          });
        },

        setAccommodationParams: (params) => {
          const result = accommodationSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set((state) => {
              const updates = { accommodationParams: result.data };
              const derived = computeDerivedState({ ...state, ...updates });
              return { ...updates, ...derived };
            });
          } else {
            logger.error("Invalid accommodation parameters", {
              error: result.error,
            });
          }
        },

        /** Set activity parameters using the handler. */
        setActivityParams: (params) => {
          const result = activitySearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set((state) => {
              const updates = { activityParams: result.data };
              const derived = computeDerivedState({ ...state, ...updates });
              return { ...updates, ...derived };
            });
          } else {
            logger.error("Invalid activity parameters", {
              error: result.error,
            });
          }
        },

        /** Set destination parameters using the handler. */
        setDestinationParams: (params) => {
          const result = destinationSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set((state) => {
              const updates = { destinationParams: result.data };
              const derived = computeDerivedState({ ...state, ...updates });
              return { ...updates, ...derived };
            });
          } else {
            logger.error("Invalid destination parameters", {
              error: result.error,
            });
          }
        },

        /** Set flight parameters using the handler. */
        setFlightParams: (params) => {
          const result = flightSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set((state) => {
              const updates = { flightParams: result.data };
              const derived = computeDerivedState({ ...state, ...updates });
              return { ...updates, ...derived };
            });
          } else {
            logger.error("Invalid flight parameters", { error: result.error });
          }
        },

        /** Set search type and initialize default parameters. */
        setSearchType: (type) => {
          const result = searchTypeSchema.safeParse(type);
          if (result.success) {
            set((state) => {
              const updatedState: Partial<SearchParamsState> = {
                currentSearchType: result.data,
              };

              // Initialize default parameters if not set yet
              const paramsKeyMap: Record<
                SearchType,
                keyof Pick<
                  SearchParamsState,
                  | "flightParams"
                  | "accommodationParams"
                  | "activityParams"
                  | "destinationParams"
                >
              > = {
                accommodation: "accommodationParams",
                activity: "activityParams",
                destination: "destinationParams",
                flight: "flightParams",
              };
              const key = paramsKeyMap[result.data];
              const currentParams = state[key] as Record<string, unknown>;
              if (Object.keys(currentParams).length === 0) {
                const defaults = getHandler(result.data).getDefaults();
                const defaultsUpdate = {
                  [key]: defaults,
                } satisfies Partial<SearchParamsState>;
                Object.assign(updatedState, defaultsUpdate);
              }

              const nextState = { ...state, ...updatedState } as SearchParamsState;
              const derived = computeDerivedState(nextState);
              return { ...updatedState, ...derived };
            });
          } else {
            logger.error("Invalid search type", { error: result.error });
          }
        },

        /** Type-safe accommodation params update. */
        updateAccommodationParams: (params: Partial<SearchAccommodationParams>) =>
          get().updateParams("accommodation", params as Partial<SearchParams>),

        /** Type-safe activity params update. */
        updateActivityParams: (params: Partial<ActivitySearchParams>) =>
          get().updateParams("activity", params as Partial<SearchParams>),

        /** Type-safe destination params update. */
        updateDestinationParams: (params: Partial<ValidatedDestinationParams>) =>
          get().updateParams("destination", params as Partial<SearchParams>),

        /** Type-safe flight params update. */
        updateFlightParams: (params: Partial<FlightSearchParams>) =>
          get().updateParams("flight", params as Partial<SearchParams>),

        /** Generic parameter update with validation. */
        updateParams: (type, params) => {
          const paramsKey = PARAMS_KEY_MAP[type];
          const schema = PARAM_SCHEMAS[type];

          set((state) => ({
            isValidating: { ...state.isValidating, [type]: true },
            validationErrors: { ...state.validationErrors, [type]: null },
          }));

          try {
            const currentParams = get()[paramsKey];
            const merged = { ...currentParams, ...params };
            const result = schema.safeParse(merged);

            if (result.success) {
              set((state) => {
                const updates = {
                  [paramsKey]: result.data,
                  isValidating: { ...state.isValidating, [type]: false },
                } as Partial<SearchParamsState>;
                const nextState = { ...state, ...updates } as SearchParamsState;
                const derived = computeDerivedState(nextState);
                return { ...updates, ...derived };
              });
              return Promise.resolve(true);
            }
            throw new Error(`Invalid ${type} parameters`);
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              isValidating: { ...state.isValidating, [type]: false },
              validationErrors: { ...state.validationErrors, [type]: message },
            }));
            return Promise.resolve(false);
          }
        },

        /** Validate current parameters using the handler. */
        validateCurrentParams: async () => {
          const { currentSearchType } = get();
          if (!currentSearchType) return false;

          return await get().validateParams(currentSearchType);
        },

        /** Validate parameters using the handler. */
        validateParams: (type) => {
          const state = get();
          const params = getParamsForType(state, type);
          return Promise.resolve(validateSearchParams(params, type));
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
  return getParamsForType(state, state.currentSearchType) as SearchParams;
};
