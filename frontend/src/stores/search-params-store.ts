/**
 * @fileoverview Search parameters store.
 */

import type { SearchParams } from "@schemas/search";
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

        /** Get current params for a search type from state. */
        get currentParams() {
          const state = get();
          if (!state.currentSearchType) return null;
          return getParamsForType(state, state.currentSearchType) as SearchParams;
        },
        // Initial state
        currentSearchType: null,
        destinationParams: {},
        flightParams: {},

        get hasValidParams() {
          const { currentSearchType, currentParams } = get();
          if (!currentSearchType || !currentParams) return false;
          return hasRequiredParams(currentParams, currentSearchType);
        },

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
          set(stateUpdate);
        },

        setAccommodationParams: (params) => {
          const result = accommodationSearchParamsStoreSchema.safeParse(params);
          if (result.success) {
            set({ accommodationParams: result.data });
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
            set({ activityParams: result.data });
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
            set({ destinationParams: result.data });
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
            set({ flightParams: result.data });
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

              return updatedState;
            });
          } else {
            logger.error("Invalid search type", { error: result.error });
          }
        },

        /** Update accommodation parameters using the handler. */
        updateAccommodationParams: (params) => {
          set((state) => ({
            isValidating: { ...state.isValidating, accommodation: true },
            validationErrors: {
              ...state.validationErrors,
              accommodation: null,
            },
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
              validationErrors: {
                ...state.validationErrors,
                accommodation: message,
              },
            }));
            return Promise.resolve(false);
          }
        },

        /** Update activity parameters using the handler. */
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
              validationErrors: {
                ...state.validationErrors,
                activity: message,
              },
            }));
            return Promise.resolve(false);
          }
        },

        /** Update destination parameters using the handler. */
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
              validationErrors: {
                ...state.validationErrors,
                destination: message,
              },
            }));
            return Promise.resolve(false);
          }
        },

        /** Update flight parameters using the handler. */
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
