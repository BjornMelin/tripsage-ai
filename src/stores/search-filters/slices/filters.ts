/**
 * @fileoverview Active filter + validation slice for the search filters store.
 */

import type { ActiveFilter, FilterValue, ValidatedFilterOption } from "@schemas/stores";
import { filterValueSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import type { SearchFiltersState, SearchFiltersStoreDeps } from "../types";
import { validateRangeValue } from "../validation";

type SearchFiltersFiltersSlice = Pick<
  SearchFiltersState,
  | "activeFilters"
  | "applyFiltersFromObject"
  | "clearAllFilters"
  | "clearFiltersByCategory"
  | "clearValidationError"
  | "clearValidationErrors"
  | "filterValidationErrors"
  | "getFilterValidationError"
  | "isApplyingFilters"
  | "removeActiveFilter"
  | "setActiveFilter"
  | "setMultipleFilters"
  | "updateActiveFilter"
  | "validateAllFilters"
  | "validateFilter"
>;

const getFilterConfig = (
  currentFilters: ValidatedFilterOption[],
  filterId: string
): ValidatedFilterOption | undefined => currentFilters.find((f) => f.id === filterId);

export const createSearchFiltersFiltersSlice =
  (
    deps: SearchFiltersStoreDeps
  ): StateCreator<SearchFiltersState, [], [], SearchFiltersFiltersSlice> =>
  (set, get) => ({
    activeFilters: {},

    applyFiltersFromObject: (filterObject) => {
      set({ isApplyingFilters: true });

      try {
        const { currentFilters } = get();
        const validFilterIds = new Set(currentFilters.map((f) => f.id));
        const filtersToApply: Record<string, FilterValue> = {};

        for (const [key, value] of Object.entries(filterObject)) {
          if (validFilterIds.has(key) && value !== undefined && value !== null) {
            const result = filterValueSchema.safeParse(value);
            if (result.success) {
              filtersToApply[key] = result.data;
            }
          }
        }

        if (Object.keys(filtersToApply).length === 0) {
          set({ isApplyingFilters: false });
          return false;
        }

        return get().setMultipleFilters(filtersToApply);
      } catch (error) {
        deps.logger.error("Failed to apply filters from object", { error });
        set({ isApplyingFilters: false });
        return false;
      }
    },

    clearAllFilters: () => {
      set({
        activeFilters: {},
        activePreset: null,
        activeSortOption: null,
        filterValidationErrors: {},
      });
    },

    clearFiltersByCategory: (category) => {
      const { currentFilters, activeFilters } = get();
      const filtersInCategory = currentFilters
        .filter((f) => f.category === category)
        .map((f) => f.id);

      const newActiveFilters = { ...activeFilters };
      filtersInCategory.forEach((filterId) => {
        delete newActiveFilters[filterId];
      });

      set({
        activeFilters: newActiveFilters,
        activePreset: null,
      });
    },

    clearValidationError: (filterId) => {
      set((state) => {
        const newErrors = { ...state.filterValidationErrors };
        delete newErrors[filterId];
        return { filterValidationErrors: newErrors };
      });
    },

    clearValidationErrors: () => {
      set({ filterValidationErrors: {} });
    },

    filterValidationErrors: {},

    getFilterValidationError: (filterId) => {
      return get().filterValidationErrors[filterId] || null;
    },

    isApplyingFilters: false,

    removeActiveFilter: (filterId) => {
      set((state) => {
        const newActiveFilters = { ...state.activeFilters };
        delete newActiveFilters[filterId];

        return {
          activeFilters: newActiveFilters,
          activePreset: null,
        };
      });
    },

    setActiveFilter: (filterId, value) => {
      set({ isApplyingFilters: true });

      try {
        const isValid = get().validateFilter(filterId, value);
        if (!isValid) {
          set({ isApplyingFilters: false });
          return false;
        }

        const newActiveFilter: ActiveFilter = {
          appliedAt: deps.nowIso(),
          filterId,
          value,
        };

        set((state) => ({
          activeFilters: {
            ...state.activeFilters,
            [filterId]: newActiveFilter,
          },
          activePreset: null,
          isApplyingFilters: false,
        }));

        return true;
      } catch (error) {
        deps.logger.error("Failed to set active filter", { error });
        set({ isApplyingFilters: false });
        return false;
      }
    },

    setMultipleFilters: (filters) => {
      set({ isApplyingFilters: true });

      try {
        const newActiveFilters: Record<string, ActiveFilter> = {};
        const timestamp = deps.nowIso();
        let allValid = true;
        const invalidFilterIds: string[] = [];

        for (const [filterId, value] of Object.entries(filters)) {
          const isValid = get().validateFilter(filterId, value);
          if (!isValid) {
            allValid = false;
            invalidFilterIds.push(filterId);
          }
          if (isValid) {
            newActiveFilters[filterId] = {
              appliedAt: timestamp,
              filterId,
              value,
            };
          }
        }

        set({
          activeFilters: { ...get().activeFilters, ...newActiveFilters },
          activePreset: null,
          isApplyingFilters: false,
        });

        if (!allValid) {
          deps.logger.error("Some filters failed validation in batch update", {
            invalidFilterIds,
          });
        }

        return allValid;
      } catch (error) {
        deps.logger.error("Failed to set multiple filters", { error });
        set({ isApplyingFilters: false });
        return false;
      }
    },

    updateActiveFilter: (filterId, value) => {
      return get().setActiveFilter(filterId, value);
    },

    validateAllFilters: () => {
      const { activeFilters } = get();
      const results = Object.entries(activeFilters).map(([filterId, filter]) => {
        return get().validateFilter(filterId, filter.value);
      });

      return results.every((result) => result);
    },

    validateFilter: (filterId, value) => {
      const { currentFilters } = get();
      const filterConfig = getFilterConfig(currentFilters, filterId);

      const setError = (error: string) => {
        set((state) => ({
          filterValidationErrors: {
            ...state.filterValidationErrors,
            [filterId]: error,
          },
        }));
        return false;
      };

      const clearError = () => {
        set((state) => {
          const newErrors = { ...state.filterValidationErrors };
          delete newErrors[filterId];
          return { filterValidationErrors: newErrors };
        });
        return true;
      };

      if (!filterConfig) {
        return setError("Filter configuration not found");
      }

      const valueResult = filterValueSchema.safeParse(value);
      if (!valueResult.success) {
        return setError("Invalid filter value format");
      }

      const validation = filterConfig.validation;
      if (validation) {
        const { min, max, pattern, required } = validation;

        if (required && (value === null || value === undefined || value === "")) {
          return setError("This filter is required");
        }

        if (typeof value === "number") {
          if (min !== undefined && value < min) {
            return setError(`Value must be at least ${min}`);
          }
          if (max !== undefined && value > max) {
            return setError(`Value must be at most ${max}`);
          }
        }

        if (filterConfig.type === "range") {
          const rangeResult = validateRangeValue(value, filterConfig);
          if (!rangeResult.valid) {
            return setError(rangeResult.error ?? "Invalid range value");
          }
        }

        if (typeof value === "string" && pattern) {
          const MaxPatternLength = 200;
          const MaxValueLength = 500;

          if (pattern.length > MaxPatternLength) {
            deps.logger.error("Filter validation pattern too long", {
              filterId,
              patternLength: pattern.length,
            });
            return setError("Value format is invalid");
          }

          if (value.length > MaxValueLength) {
            return setError("Value is too long");
          }

          let regex: RegExp;
          try {
            regex = new RegExp(pattern);
          } catch (error) {
            deps.logger.error("Invalid filter validation pattern", { error, filterId });
            return setError("Value format is invalid");
          }
          if (!regex.test(value)) {
            return setError("Value format is invalid");
          }
        }
      }

      return clearError();
    },
  });
