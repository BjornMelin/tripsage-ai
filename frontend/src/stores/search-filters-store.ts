/**
 * @fileoverview Zustand store for managing search filters, sort options, and presets.
 */

import type { SearchType } from "@schemas/search";
import {
  type ActiveFilter,
  type FilterPreset,
  type FilterValue,
  filterPresetSchema,
  filterValueSchema,
  searchTypeSchema,
  sortOptionSchema,
  type ValidatedFilterOption,
  type ValidatedSortOption,
} from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { generateId, getCurrentTimestamp } from "./helpers";
import { createComputeFn, withComputed } from "./middleware/computed";
import {
  FILTER_CONFIGS,
  getDefaultSortOptions,
  SORT_CONFIGS,
} from "./search-filters/filter-configs";

const logger = createStoreLogger({ storeName: "search-filters" });

// Search filters store interface
interface SearchFiltersState {
  // Available filters and sort options by search type
  availableFilters: Record<SearchType, ValidatedFilterOption[]>;
  availableSortOptions: Record<SearchType, ValidatedSortOption[]>;

  // Active filters and sorting
  activeFilters: Record<string, ActiveFilter>;
  activeSortOption: ValidatedSortOption | null;
  currentSearchType: SearchType | null;

  // Filter presets
  filterPresets: FilterPreset[];
  activePreset: FilterPreset | null;

  // Filter state management
  isApplyingFilters: boolean;
  filterValidationErrors: Record<string, string>;

  // Computed properties
  hasActiveFilters: boolean;
  activeFilterCount: number;
  canClearFilters: boolean;
  currentFilters: ValidatedFilterOption[];
  currentSortOptions: ValidatedSortOption[];
  appliedFilterSummary: string;

  // Sort options configuration

  // Active filter management
  setActiveFilter: (filterId: string, value: FilterValue) => boolean;
  removeActiveFilter: (filterId: string) => void;
  updateActiveFilter: (filterId: string, value: FilterValue) => boolean;
  clearAllFilters: () => void;
  clearFiltersByCategory: (category: string) => void;

  // Bulk filter operations
  setMultipleFilters: (filters: Record<string, FilterValue>) => boolean;
  applyFiltersFromObject: (filterObject: Record<string, unknown>) => boolean;

  // Reset filters to default (optionally scoped by search type)
  resetFiltersToDefault: (searchType?: SearchType) => void;

  // Sort management
  setActiveSortOption: (option: ValidatedSortOption | null) => void;
  setSortById: (optionId: string) => void;
  toggleSortDirection: () => void;
  resetSortToDefault: (searchType?: SearchType) => void;

  // Filter presets
  saveFilterPreset: (name: string, description?: string) => string | null;
  loadFilterPreset: (presetId: string) => boolean;
  updateFilterPreset: (presetId: string, updates: Partial<FilterPreset>) => boolean;
  deleteFilterPreset: (presetId: string) => void;
  duplicateFilterPreset: (presetId: string, newName: string) => string | null;
  incrementPresetUsage: (presetId: string) => void;

  // Filter validation
  validateFilter: (filterId: string, value: FilterValue) => boolean;
  validateAllFilters: () => boolean;
  getFilterValidationError: (filterId: string) => string | null;

  // Search type context
  setSearchType: (searchType: SearchType) => void;

  // Utility actions
  clearValidationErrors: () => void;
  clearValidationError: (filterId: string) => void;
  reset: () => void;
  softReset: () => void; // Keeps configuration but clears active state
}

/** Validate a range filter value against min/max constraints. */
const validateRangeValue = (
  value: FilterValue,
  config: ValidatedFilterOption
): { valid: boolean; error?: string } => {
  if (typeof value !== "object" || value === null) {
    return { error: "Range value must be an object with min/max", valid: false };
  }

  const rangeValue = value as { min?: unknown; max?: unknown };
  const validation = config.validation;

  const min = rangeValue.min;
  const max = rangeValue.max;

  if (min !== undefined && typeof min !== "number") {
    return { error: "Minimum value must be a number", valid: false };
  }

  if (max !== undefined && typeof max !== "number") {
    return { error: "Maximum value must be a number", valid: false };
  }

  if (min !== undefined && max !== undefined && min > max) {
    return { error: "Minimum value cannot exceed maximum", valid: false };
  }

  if (!validation) {
    return { valid: true };
  }

  if (min !== undefined && validation.min !== undefined && min < validation.min) {
    return { error: `Minimum value must be at least ${validation.min}`, valid: false };
  }

  if (max !== undefined && validation.max !== undefined && max > validation.max) {
    return { error: `Maximum value must be at most ${validation.max}`, valid: false };
  }

  return { valid: true };
};

// Helper to compute derived state using shared middleware
const computeFilterState = createComputeFn<SearchFiltersState>({
  activeFilterCount: (state) => Object.keys(state.activeFilters || {}).length,
  appliedFilterSummary: (state) => {
    const currentFilters = state.currentSearchType
      ? state.availableFilters?.[state.currentSearchType] || []
      : [];
    const summaries: string[] = [];
    Object.entries(state.activeFilters || {}).forEach(([filterId, activeFilter]) => {
      const filter = currentFilters.find((f) => f.id === filterId);
      if (filter) {
        const valueStr = Array.isArray(activeFilter.value)
          ? activeFilter.value.join(", ")
          : typeof activeFilter.value === "object" && activeFilter.value !== null
            ? `${(activeFilter.value as { min?: number; max?: number }).min || ""} - ${
                (activeFilter.value as { min?: number; max?: number }).max || ""
              }`
            : String(activeFilter.value);
        summaries.push(`${filter.label}: ${valueStr}`);
      }
    });
    return summaries.join("; ");
  },
  canClearFilters: (state) =>
    Object.keys(state.activeFilters || {}).length > 0 ||
    state.activeSortOption !== null,
  currentFilters: (state) =>
    state.currentSearchType
      ? state.availableFilters?.[state.currentSearchType] || []
      : [],
  currentSortOptions: (state) =>
    state.currentSearchType
      ? state.availableSortOptions?.[state.currentSearchType] || []
      : [],
  hasActiveFilters: (state) => Object.keys(state.activeFilters || {}).length > 0,
});

/** Use the search filters store */
export const useSearchFiltersStore = create<SearchFiltersState>()(
  devtools(
    persist(
      withComputed({ compute: computeFilterState }, (set, get) => ({
        activeFilterCount: 0,

        // Active filters and sorting
        activeFilters: {},
        activePreset: null,
        activeSortOption: null,

        appliedFilterSummary: "",

        applyFiltersFromObject: (filterObject) => {
          set({ isApplyingFilters: true });

          try {
            const { currentFilters } = get();
            const validFilterIds = new Set(currentFilters.map((f) => f.id));
            const filtersToApply: Record<string, FilterValue> = {};

            for (const [key, value] of Object.entries(filterObject)) {
              // Only apply if filter ID exists in current configuration
              if (validFilterIds.has(key) && value !== undefined && value !== null) {
                // Validate the value can be a FilterValue
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
            logger.error("Failed to apply filters from object", { error });
            set({ isApplyingFilters: false });
            return false;
          }
        },
        // Initial state - use pre-computed config objects
        availableFilters: FILTER_CONFIGS,
        availableSortOptions: SORT_CONFIGS,
        canClearFilters: false,

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

        // Utility actions
        clearValidationErrors: () => {
          set({ filterValidationErrors: {} });
        },
        currentFilters: [],
        currentSearchType: null,
        currentSortOptions: [],

        deleteFilterPreset: (presetId) => {
          set((state) => ({
            activePreset:
              state.activePreset?.id === presetId ? null : state.activePreset,
            filterPresets: state.filterPresets.filter((p) => p.id !== presetId),
          }));
        },

        duplicateFilterPreset: (presetId, newName) => {
          const { filterPresets } = get();
          const originalPreset = filterPresets.find((p) => p.id === presetId);

          if (!originalPreset) return null;

          const duplicatedPreset: FilterPreset = {
            ...originalPreset,
            createdAt: getCurrentTimestamp(),
            id: generateId(),
            isBuiltIn: false,
            name: newName,
            usageCount: 0,
          };

          const result = filterPresetSchema.safeParse(duplicatedPreset);
          if (result.success) {
            set((state) => ({
              filterPresets: [...state.filterPresets, result.data],
            }));
            return duplicatedPreset.id;
          }

          return null;
        },

        // Filter presets
        filterPresets: [],
        filterValidationErrors: {},

        getFilterValidationError: (filterId) => {
          return get().filterValidationErrors[filterId] || null;
        },

        // Computed properties (initialized by middleware)
        hasActiveFilters: false,

        incrementPresetUsage: (presetId) => {
          set((state) => ({
            filterPresets: state.filterPresets.map((preset) =>
              preset.id === presetId
                ? { ...preset, usageCount: preset.usageCount + 1 }
                : preset
            ),
          }));
        },

        // Filter state management
        isApplyingFilters: false,

        loadFilterPreset: (presetId) => {
          const { filterPresets } = get();
          const preset = filterPresets.find((p) => p.id === presetId);

          if (!preset) return false;

          try {
            set({ isApplyingFilters: true });

            // Convert preset filters back to active filters
            const newActiveFilters: Record<string, ActiveFilter> = {};
            preset.filters.forEach((filter) => {
              newActiveFilters[filter.filterId] = filter;
            });

            set({
              activeFilters: newActiveFilters,
              activePreset: preset,
              activeSortOption: preset.sortOption || null,
              isApplyingFilters: false,
            });

            // Increment usage count
            get().incrementPresetUsage(presetId);

            return true;
          } catch (error) {
            logger.error("Failed to load filter preset", { error });
            set({ isApplyingFilters: false });
            return false;
          }
        },

        removeActiveFilter: (filterId) => {
          set((state) => {
            const newActiveFilters = { ...state.activeFilters };
            delete newActiveFilters[filterId];

            return {
              activeFilters: newActiveFilters,
              activePreset: null, // Clear active preset when filters change
            };
          });
        },

        reset: () => {
          set({
            activeFilters: {},
            activePreset: null,
            activeSortOption: null,
            currentSearchType: null,
            filterPresets: [],
            filterValidationErrors: {},
            isApplyingFilters: false,
          });
        },

        resetFiltersToDefault: (searchType) => {
          const targetSearchType = searchType || get().currentSearchType;
          if (!targetSearchType) return;

          const defaultSort = getDefaultSortOptions(targetSearchType).find(
            (s) => s.isDefault
          );

          set({
            activeFilters: {},
            activePreset: null,
            activeSortOption: defaultSort || null,
            filterValidationErrors: {},
          });
        },

        resetSortToDefault: (searchType) => {
          const targetSearchType = searchType || get().currentSearchType;
          if (!targetSearchType) return;

          const defaultSort = getDefaultSortOptions(targetSearchType).find(
            (s) => s.isDefault
          );
          set({ activeSortOption: defaultSort || null });
        },

        // Filter presets
        saveFilterPreset: (name, description) => {
          const { currentSearchType, activeFilters, activeSortOption } = get();
          if (!currentSearchType) return null;

          try {
            const presetId = generateId();
            const newPreset: FilterPreset = {
              createdAt: getCurrentTimestamp(),
              description,
              filters: Object.values(activeFilters),
              id: presetId,
              isBuiltIn: false,
              name,
              searchType: currentSearchType,
              sortOption: activeSortOption || undefined,
              usageCount: 0,
            };

            const result = filterPresetSchema.safeParse(newPreset);
            if (result.success) {
              set((state) => ({
                filterPresets: [...state.filterPresets, result.data],
              }));
              return presetId;
            }
            logger.error("Invalid filter preset", { error: result.error });
            return null;
          } catch (error) {
            logger.error("Failed to save filter preset", { error });
            return null;
          }
        },

        // Active filter management
        setActiveFilter: (filterId, value) => {
          set({ isApplyingFilters: true });

          try {
            const isValid = get().validateFilter(filterId, value);
            if (!isValid) {
              set({ isApplyingFilters: false });
              return false;
            }

            const newActiveFilter: ActiveFilter = {
              appliedAt: getCurrentTimestamp(),
              filterId,
              value,
            };

            set((state) => ({
              activeFilters: {
                ...state.activeFilters,
                [filterId]: newActiveFilter,
              },
              activePreset: null, // Clear active preset when filters change manually
              isApplyingFilters: false,
            }));

            return true;
          } catch (error) {
            logger.error("Failed to set active filter", { error });
            set({ isApplyingFilters: false });
            return false;
          }
        },

        // Sort management
        setActiveSortOption: (option) => {
          if (option) {
            const result = sortOptionSchema.safeParse(option);
            if (result.success) {
              set({
                activePreset: null, // Clear active preset when sort changes
                activeSortOption: result.data,
              });
            } else {
              logger.error("Invalid sort option", { error: result.error });
            }
          } else {
            set({ activeSortOption: null });
          }
        },

        // Bulk filter operations
        setMultipleFilters: (filters) => {
          set({ isApplyingFilters: true });

          try {
            const newActiveFilters: Record<string, ActiveFilter> = {};
            const timestamp = getCurrentTimestamp();

            for (const [filterId, value] of Object.entries(filters)) {
              const isValid = get().validateFilter(filterId, value);
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

            return true;
          } catch (error) {
            logger.error("Failed to set multiple filters", { error });
            set({ isApplyingFilters: false });
            return false;
          }
        },

        // Search type context
        setSearchType: (searchType) => {
          const result = searchTypeSchema.safeParse(searchType);
          if (result.success) {
            const { availableSortOptions } = get();
            const defaultSort = availableSortOptions[searchType]?.find(
              (s) => s.isDefault
            );

            set({
              activePreset: null, // Clear preset when changing search type
              activeSortOption: defaultSort || null,
              currentSearchType: result.data,
            });
          } else {
            logger.error("Invalid search type", { error: result.error });
          }
        },

        setSortById: (optionId) => {
          const { currentSortOptions } = get();
          const option = currentSortOptions.find((o) => o.id === optionId);
          if (option) {
            get().setActiveSortOption(option);
          }
        },

        softReset: () => {
          set({
            activeFilters: {},
            activePreset: null,
            activeSortOption: null,
            filterValidationErrors: {},
            isApplyingFilters: false,
          });
        },

        toggleSortDirection: () => {
          const { activeSortOption } = get();
          if (activeSortOption) {
            const newDirection = activeSortOption.direction === "asc" ? "desc" : "asc";
            get().setActiveSortOption({
              ...activeSortOption,
              direction: newDirection,
            });
          }
        },

        updateActiveFilter: (filterId, value) => {
          return get().setActiveFilter(filterId, value);
        },

        updateFilterPreset: (presetId, updates) => {
          try {
            set((state) => {
              const updatedPresets = state.filterPresets.map((preset) => {
                if (preset.id === presetId) {
                  const updatedPreset = { ...preset, ...updates };
                  const result = filterPresetSchema.safeParse(updatedPreset);
                  return result.success ? result.data : preset;
                }
                return preset;
              });

              return { filterPresets: updatedPresets };
            });

            return true;
          } catch (error) {
            logger.error("Failed to update filter preset", { error });
            return false;
          }
        },

        validateAllFilters: () => {
          const { activeFilters } = get();
          const results = Object.entries(activeFilters).map(([filterId, filter]) => {
            return get().validateFilter(filterId, filter.value);
          });

          return results.every((result) => result);
        },

        // Filter validation
        validateFilter: (filterId, value) => {
          const { currentFilters } = get();
          const filterConfig = currentFilters.find((f) => f.id === filterId);

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

          // Zod schema validation first
          const valueResult = filterValueSchema.safeParse(value);
          if (!valueResult.success) {
            return setError("Invalid filter value format");
          }

          // Type-specific validation
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

            // Handle range type filters using helper
            if (filterConfig.type === "range") {
              const rangeResult = validateRangeValue(value, filterConfig);
              if (!rangeResult.valid) {
                return setError(rangeResult.error ?? "Invalid range value");
              }
            }

            if (typeof value === "string" && pattern) {
              const regex = new RegExp(pattern);
              if (!regex.test(value)) {
                return setError("Value format is invalid");
              }
            }
          }

          return clearError();
        },
      })),
      {
        name: "search-filters-storage",
        partialize: (state) => ({
          availableFilters: state.availableFilters,
          availableSortOptions: state.availableSortOptions,
          // Persist filter presets and available configurations
          filterPresets: state.filterPresets,
        }),
      }
    ),
    { name: "SearchFiltersStore" }
  )
);

// Utility selectors for common use cases
export const useActiveFilters = () =>
  useSearchFiltersStore((state) => state.activeFilters);
export const useActiveSortOption = () =>
  useSearchFiltersStore((state) => state.activeSortOption);
export const useCurrentFilters = () =>
  useSearchFiltersStore((state) => state.currentFilters);
export const useCurrentSortOptions = () =>
  useSearchFiltersStore((state) => state.currentSortOptions);
export const useHasActiveFilters = () =>
  useSearchFiltersStore((state) => state.hasActiveFilters);
export const useActiveFilterCount = () =>
  useSearchFiltersStore((state) => state.activeFilterCount);
export const useFilterPresets = (searchType?: SearchType) =>
  useSearchFiltersStore((state) =>
    searchType
      ? state.filterPresets.filter((p) => p.searchType === searchType)
      : state.filterPresets
  );
export const useFilterValidationErrors = () =>
  useSearchFiltersStore((state) => state.filterValidationErrors);
export const useIsApplyingFilters = () =>
  useSearchFiltersStore((state) => state.isApplyingFilters);
