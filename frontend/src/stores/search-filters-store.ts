/**
 * @fileoverview Zustand store for managing search filters, sort options, and presets.
 */

import type { SearchType } from "@schemas/search";
import {
  type ActiveFilter,
  type FilterPreset,
  type FilterValue,
  filterOptionSchema,
  filterPresetSchema,
  filterValueSchema,
  type SortDirection,
  searchTypeSchema,
  sortOptionSchema,
  type ValidatedFilterOption,
  type ValidatedSortOption,
} from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { nowIso, secureId } from "@/lib/security/random";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { createComputeFn, withComputed } from "./middleware/computed";

const logger = createStoreLogger({ storeName: "search-filters" });

// Validation schemas imported from @schemas/stores

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

  // Filter configuration actions
  setAvailableFilters: (
    searchType: SearchType,
    filters: ValidatedFilterOption[]
  ) => void;
  addAvailableFilter: (searchType: SearchType, filter: ValidatedFilterOption) => void;
  updateAvailableFilter: (
    searchType: SearchType,
    filterId: string,
    updates: Partial<ValidatedFilterOption>
  ) => void;
  removeAvailableFilter: (searchType: SearchType, filterId: string) => void;

  // Sort options configuration
  setAvailableSortOptions: (
    searchType: SearchType,
    options: ValidatedSortOption[]
  ) => void;
  addAvailableSortOption: (searchType: SearchType, option: ValidatedSortOption) => void;
  updateAvailableSortOption: (
    searchType: SearchType,
    optionId: string,
    updates: Partial<ValidatedSortOption>
  ) => void;
  removeAvailableSortOption: (searchType: SearchType, optionId: string) => void;

  // Active filter management
  setActiveFilter: (filterId: string, value: FilterValue) => boolean;
  removeActiveFilter: (filterId: string) => void;
  updateActiveFilter: (filterId: string, value: FilterValue) => boolean;
  clearAllFilters: () => void;
  clearFiltersByCategory: (category: string) => void;

  // Bulk filter operations
  setMultipleFilters: (filters: Record<string, FilterValue>) => boolean;
  applyFiltersFromObject: (filterObject: Record<string, unknown>) => boolean;
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

  // Filter insights and analytics
  getFilterUsageStats: () => Record<string, { count: number; lastUsed: string }>;
  getMostUsedFilters: (
    searchType?: SearchType,
    limit?: number
  ) => ValidatedFilterOption[];
  getFilterDependencies: (filterId: string) => ValidatedFilterOption[];

  // Utility actions
  clearValidationErrors: () => void;
  clearValidationError: (filterId: string) => void;
  reset: () => void;
  softReset: () => void; // Keeps configuration but clears active state
}

// Helper functions
const GENERATE_ID = () => secureId(12);
const GET_CURRENT_TIMESTAMP = () => nowIso();

// Default filter configurations by search type
const GET_DEFAULT_FILTERS = (searchType: SearchType): ValidatedFilterOption[] => {
  switch (searchType) {
    case "flight":
      return [
        {
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
          validation: { max: 10000, min: 0 },
        },
        {
          category: "routing",
          id: "stops",
          label: "Number of Stops",
          options: [
            { label: "Direct flights only", value: "0" },
            { label: "1 stop", value: "1" },
            { label: "2+ stops", value: "2" },
          ],
          required: false,
          type: "select",
        },
        {
          category: "airline",
          id: "airlines",
          label: "Airlines",
          options: [], // Would be populated dynamically
          required: false,
          type: "multiselect",
        },
        {
          category: "timing",
          id: "departure_time",
          label: "Departure Time",
          options: [
            { label: "Early Morning (6:00-9:00)", value: "early_morning" },
            { label: "Morning (9:00-12:00)", value: "morning" },
            { label: "Afternoon (12:00-18:00)", value: "afternoon" },
            { label: "Evening (18:00+)", value: "evening" },
          ],
          required: false,
          type: "select",
        },
      ];
    case "accommodation":
      return [
        {
          category: "pricing",
          id: "price_range",
          label: "Price per Night",
          required: false,
          type: "range",
          validation: { max: 2000, min: 0 },
        },
        {
          category: "quality",
          id: "rating",
          label: "Minimum Rating",
          options: [
            { label: "3+ stars", value: "3" },
            { label: "4+ stars", value: "4" },
            { label: "5 stars", value: "5" },
          ],
          required: false,
          type: "select",
        },
        {
          category: "type",
          id: "property_type",
          label: "Property Type",
          options: [
            { label: "Hotel", value: "hotel" },
            { label: "Apartment", value: "apartment" },
            { label: "Villa", value: "villa" },
            { label: "Resort", value: "resort" },
          ],
          required: false,
          type: "multiselect",
        },
        {
          category: "features",
          id: "amenities",
          label: "Amenities",
          options: [
            { label: "Free WiFi", value: "wifi" },
            { label: "Free Parking", value: "parking" },
            { label: "Swimming Pool", value: "pool" },
            { label: "Fitness Center", value: "gym" },
            { label: "Spa", value: "spa" },
            { label: "Restaurant", value: "restaurant" },
          ],
          required: false,
          type: "multiselect",
        },
      ];
    case "activity":
      return [
        {
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
          validation: { max: 500, min: 0 },
        },
        {
          category: "timing",
          id: "duration",
          label: "Duration",
          required: false,
          type: "range",
          validation: { max: 480, min: 1 }, // minutes
        },
        {
          category: "experience",
          id: "difficulty",
          label: "Difficulty Level",
          options: [
            { label: "Easy", value: "easy" },
            { label: "Moderate", value: "moderate" },
            { label: "Challenging", value: "challenging" },
            { label: "Extreme", value: "extreme" },
          ],
          required: false,
          type: "select",
        },
        {
          category: "type",
          id: "category",
          label: "Activity Type",
          options: [
            { label: "Outdoor Adventures", value: "outdoor" },
            { label: "Cultural Experiences", value: "cultural" },
            { label: "Food & Drink", value: "food" },
            { label: "Sightseeing", value: "sightseeing" },
            { label: "Sports & Recreation", value: "sports" },
          ],
          required: false,
          type: "multiselect",
        },
      ];
    case "destination":
      return [
        {
          category: "type",
          id: "destination_type",
          label: "Destination Type",
          options: [
            { label: "Cities", value: "city" },
            { label: "Countries", value: "country" },
            { label: "Regions", value: "region" },
            { label: "Landmarks", value: "landmark" },
          ],
          required: false,
          type: "multiselect",
        },
        {
          category: "demographics",
          id: "population",
          label: "Population Size",
          options: [
            { label: "Small (< 100k)", value: "small" },
            { label: "Medium (100k - 1M)", value: "medium" },
            { label: "Large (1M+)", value: "large" },
          ],
          required: false,
          type: "select",
        },
      ];
    default:
      return [];
  }
};

const GET_DEFAULT_SORT_OPTIONS = (searchType: SearchType): ValidatedSortOption[] => {
  const commonSorts = [
    {
      direction: "desc" as SortDirection,
      field: "score",
      id: "relevance",
      isDefault: true,
      label: "Relevance",
    },
    {
      direction: "asc" as SortDirection,
      field: "price",
      id: "price_low",
      isDefault: false,
      label: "Price: Low to High",
    },
    {
      direction: "desc" as SortDirection,
      field: "price",
      id: "price_high",
      isDefault: false,
      label: "Price: High to Low",
    },
  ];

  switch (searchType) {
    case "flight":
      return [
        ...commonSorts,
        {
          direction: "asc" as SortDirection,
          field: "totalDuration",
          id: "duration",
          isDefault: false,
          label: "Duration",
        },
        {
          direction: "asc" as SortDirection,
          field: "departureTime",
          id: "departure",
          isDefault: false,
          label: "Departure Time",
        },
        {
          direction: "asc" as SortDirection,
          field: "arrivalTime",
          id: "arrival",
          isDefault: false,
          label: "Arrival Time",
        },
        {
          direction: "asc" as SortDirection,
          field: "stops",
          id: "stops",
          isDefault: false,
          label: "Fewest Stops",
        },
      ];
    case "accommodation":
      return [
        ...commonSorts,
        {
          direction: "desc" as SortDirection,
          field: "rating",
          id: "rating",
          isDefault: false,
          label: "Highest Rated",
        },
        {
          direction: "asc" as SortDirection,
          field: "distance",
          id: "distance",
          isDefault: false,
          label: "Distance",
        },
        {
          direction: "desc" as SortDirection,
          field: "reviewCount",
          id: "reviews",
          isDefault: false,
          label: "Most Reviews",
        },
      ];
    case "activity":
      return [
        ...commonSorts,
        {
          direction: "desc" as SortDirection,
          field: "rating",
          id: "rating",
          isDefault: false,
          label: "Highest Rated",
        },
        {
          direction: "asc" as SortDirection,
          field: "duration",
          id: "duration",
          isDefault: false,
          label: "Duration",
        },
        {
          direction: "desc" as SortDirection,
          field: "bookingCount",
          id: "popularity",
          isDefault: false,
          label: "Most Popular",
        },
      ];
    case "destination":
      return [
        {
          direction: "desc" as SortDirection,
          field: "score",
          id: "relevance",
          isDefault: true,
          label: "Relevance",
        },
        {
          direction: "asc" as SortDirection,
          field: "name",
          id: "alphabetical",
          isDefault: false,
          label: "Alphabetical",
        },
        {
          direction: "desc" as SortDirection,
          field: "population",
          id: "population",
          isDefault: false,
          label: "Population",
        },
        {
          direction: "asc" as SortDirection,
          field: "distance",
          id: "distance",
          isDefault: false,
          label: "Distance",
        },
      ];
    default:
      return commonSorts;
  }
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

export const useSearchFiltersStore = create<SearchFiltersState>()(
  devtools(
    persist(
      withComputed({ compute: computeFilterState }, (set, get) => ({
        activeFilterCount: 0,

        // Active filters and sorting
        activeFilters: {},
        activePreset: null,
        activeSortOption: null,

        addAvailableFilter: (searchType: SearchType, filter: ValidatedFilterOption) => {
          const result = filterOptionSchema.safeParse(filter);
          if (result.success) {
            set((state) => ({
              availableFilters: {
                ...state.availableFilters,
                [searchType]: [
                  ...(state.availableFilters[searchType] || []),
                  result.data,
                ],
              },
            }));
          } else {
            logger.error("Invalid filter", { error: result.error });
          }
        },

        addAvailableSortOption: (searchType, option) => {
          const result = sortOptionSchema.safeParse(option);
          if (result.success) {
            set((state) => ({
              availableSortOptions: {
                ...state.availableSortOptions,
                [searchType]: [
                  ...(state.availableSortOptions[searchType] || []),
                  result.data,
                ],
              },
            }));
          } else {
            logger.error("Invalid sort option", { error: result.error });
          }
        },
        appliedFilterSummary: "",

        applyFiltersFromObject: (filterObject) => {
          // Convert Record<string, unknown> to Record<string, FilterValue>
          const validatedFilters: Record<string, FilterValue> = {};
          for (const [key, value] of Object.entries(filterObject)) {
            // Only include values that match FilterValue type
            if (
              typeof value === "string" ||
              typeof value === "number" ||
              typeof value === "boolean" ||
              Array.isArray(value) ||
              (typeof value === "object" &&
                value !== null &&
                ("min" in value || "max" in value))
            ) {
              validatedFilters[key] = value as FilterValue;
            }
          }
          return get().setMultipleFilters(validatedFilters);
        },
        // Initial state
        availableFilters: {
          accommodation: GET_DEFAULT_FILTERS("accommodation"),
          activity: GET_DEFAULT_FILTERS("activity"),
          destination: GET_DEFAULT_FILTERS("destination"),
          flight: GET_DEFAULT_FILTERS("flight"),
        },
        availableSortOptions: {
          accommodation: GET_DEFAULT_SORT_OPTIONS("accommodation"),
          activity: GET_DEFAULT_SORT_OPTIONS("activity"),
          destination: GET_DEFAULT_SORT_OPTIONS("destination"),
          flight: GET_DEFAULT_SORT_OPTIONS("flight"),
        },
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

          set({ activeFilters: newActiveFilters });
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
            createdAt: GET_CURRENT_TIMESTAMP(),
            id: GENERATE_ID(),
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

        getFilterDependencies: (filterId) => {
          const { currentFilters } = get();
          const filter = currentFilters.find((f) => f.id === filterId);

          if (!filter || !filter.dependencies) return [];

          return currentFilters.filter((f) => filter.dependencies?.includes(f.id));
        },

        // Filter insights and analytics
        getFilterUsageStats: () => {
          const { filterPresets } = get();
          const stats: Record<string, { count: number; lastUsed: string }> = {};

          filterPresets.forEach((preset) => {
            preset.filters.forEach((filter) => {
              const filterId = filter.filterId;
              if (!stats[filterId]) {
                stats[filterId] = { count: 0, lastUsed: "" };
              }
              stats[filterId].count += preset.usageCount;
              if (filter.appliedAt > stats[filterId].lastUsed) {
                stats[filterId].lastUsed = filter.appliedAt;
              }
            });
          });

          return stats;
        },

        getFilterValidationError: (filterId) => {
          return get().filterValidationErrors[filterId] || null;
        },

        getMostUsedFilters: (searchType, limit = 5) => {
          const { currentFilters } = get();
          const targetFilters = searchType
            ? get().availableFilters[searchType] || []
            : currentFilters;

          const usageStats = get().getFilterUsageStats();

          return targetFilters
            .map((filter) => ({
              ...filter,
              usageCount: usageStats[filter.id]?.count || 0,
            }))
            .sort((a, b) => b.usageCount - a.usageCount)
            .slice(0, limit);
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

        removeAvailableFilter: (searchType: SearchType, filterId: string) => {
          set((state) => ({
            availableFilters: {
              ...state.availableFilters,
              [searchType]: (state.availableFilters[searchType] || []).filter(
                (f) => f.id !== filterId
              ),
            },
          }));
        },

        removeAvailableSortOption: (searchType, optionId) => {
          set((state) => ({
            availableSortOptions: {
              ...state.availableSortOptions,
              [searchType]: (state.availableSortOptions[searchType] || []).filter(
                (o) => o.id !== optionId
              ),
            },
          }));
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

          GET_DEFAULT_FILTERS(targetSearchType); // Get default filters
          const defaultSort = GET_DEFAULT_SORT_OPTIONS(targetSearchType).find(
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

          const defaultSort = GET_DEFAULT_SORT_OPTIONS(targetSearchType).find(
            (s) => s.isDefault
          );
          set({ activeSortOption: defaultSort || null });
        },

        // Filter presets
        saveFilterPreset: (name, description) => {
          const { currentSearchType, activeFilters, activeSortOption } = get();
          if (!currentSearchType) return null;

          try {
            const presetId = GENERATE_ID();
            const newPreset: FilterPreset = {
              createdAt: GET_CURRENT_TIMESTAMP(),
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
              appliedAt: GET_CURRENT_TIMESTAMP(),
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

        // Filter configuration actions
        setAvailableFilters: (
          searchType: SearchType,
          filters: ValidatedFilterOption[]
        ) => {
          // Validate filters
          const validatedFilters = filters.filter((filter: ValidatedFilterOption) => {
            const result = filterOptionSchema.safeParse(filter);
            if (!result.success) {
              logger.error(`Invalid filter for ${searchType}`, {
                error: result.error,
              });
              return false;
            }
            return true;
          });

          set((state) => ({
            availableFilters: {
              ...state.availableFilters,
              [searchType]: validatedFilters,
            },
          }));
        },

        // Sort options configuration
        setAvailableSortOptions: (searchType, options) => {
          const validatedOptions = options.filter((option) => {
            const result = sortOptionSchema.safeParse(option);
            if (!result.success) {
              logger.error(`Invalid sort option for ${searchType}`, {
                error: result.error,
              });
              return false;
            }
            return true;
          });

          set((state) => ({
            availableSortOptions: {
              ...state.availableSortOptions,
              [searchType]: validatedOptions,
            },
          }));
        },

        // Bulk filter operations
        setMultipleFilters: (filters) => {
          set({ isApplyingFilters: true });

          try {
            const newActiveFilters: Record<string, ActiveFilter> = {};
            const timestamp = GET_CURRENT_TIMESTAMP();

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

        updateAvailableFilter: (
          searchType: SearchType,
          filterId: string,
          updates: Partial<ValidatedFilterOption>
        ) => {
          set((state) => {
            const filters = state.availableFilters[searchType] || [];
            const updatedFilters = filters.map((filter: ValidatedFilterOption) => {
              if (filter.id === filterId) {
                const updatedFilter = { ...filter, ...updates };
                const result = filterOptionSchema.safeParse(updatedFilter);
                return result.success ? result.data : filter;
              }
              return filter;
            });

            return {
              availableFilters: {
                ...state.availableFilters,
                [searchType]: updatedFilters,
              },
            };
          });
        },

        updateAvailableSortOption: (searchType, optionId, updates) => {
          set((state) => {
            const options = state.availableSortOptions[searchType] || [];
            const updatedOptions = options.map((option) => {
              if (option.id === optionId) {
                const updatedOption = { ...option, ...updates };
                const result = sortOptionSchema.safeParse(updatedOption);
                return result.success ? result.data : option;
              }
              return option;
            });

            return {
              availableSortOptions: {
                ...state.availableSortOptions,
                [searchType]: updatedOptions,
              },
            };
          });
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

          if (!filterConfig) {
            set((state) => ({
              filterValidationErrors: {
                ...state.filterValidationErrors,
                [filterId]: "Filter configuration not found",
              },
            }));
            return false;
          }

          try {
            // Validate value against filter configuration
            const valueResult = filterValueSchema.safeParse(value);
            if (!valueResult.success) {
              throw new Error("Invalid filter value format");
            }

            // Type-specific validation
            if (filterConfig.validation) {
              const { min, max, pattern, required } = filterConfig.validation;

              if (required && (value === null || value === undefined || value === "")) {
                throw new Error("This filter is required");
              }

              if (typeof value === "number") {
                if (min !== undefined && value < min) {
                  throw new Error(`Value must be at least ${min}`);
                }
                if (max !== undefined && value > max) {
                  throw new Error(`Value must be at most ${max}`);
                }
              }

              // Handle range type filters
              if (
                filterConfig.type === "range" &&
                typeof value === "object" &&
                value !== null
              ) {
                const rangeValue = value as { min?: number; max?: number };
                if (
                  rangeValue.min !== undefined &&
                  min !== undefined &&
                  rangeValue.min < min
                ) {
                  throw new Error(`Minimum value must be at least ${min}`);
                }
                if (
                  rangeValue.max !== undefined &&
                  max !== undefined &&
                  rangeValue.max > max
                ) {
                  throw new Error(`Maximum value must be at most ${max}`);
                }
              }

              if (typeof value === "string" && pattern) {
                const regex = new RegExp(pattern);
                if (!regex.test(value)) {
                  throw new Error("Value format is invalid");
                }
              }
            }

            // Clear any existing validation error
            set((state) => {
              const newErrors = { ...state.filterValidationErrors };
              delete newErrors[filterId];
              return { filterValidationErrors: newErrors };
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            set((state) => ({
              filterValidationErrors: {
                ...state.filterValidationErrors,
                [filterId]: message,
              },
            }));
            return false;
          }
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
