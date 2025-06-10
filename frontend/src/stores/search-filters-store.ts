import type { FilterOption, SearchType, SortOption } from "@/types/search";
import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

// Validation schemas for filters and sorting
const SearchTypeSchema = z.enum(["flight", "accommodation", "activity", "destination"]);
const SortDirectionSchema = z.enum(["asc", "desc"]);

const FilterValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.string()),
  z.array(z.number()),
  z.object({
    min: z.number().optional(),
    max: z.number().optional(),
  }),
]);

const FilterOptionSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.enum([
    "text",
    "number",
    "boolean",
    "select",
    "multiselect",
    "range",
    "date",
    "daterange",
  ]),
  category: z.string().optional(),
  description: z.string().optional(),
  required: z.boolean().default(false),
  defaultValue: FilterValueSchema.optional(),
  options: z
    .array(
      z.object({
        value: z.string(),
        label: z.string(),
        disabled: z.boolean().optional(),
      })
    )
    .optional(),
  validation: z
    .object({
      min: z.number().optional(),
      max: z.number().optional(),
      pattern: z.string().optional(),
      required: z.boolean().optional(),
    })
    .optional(),
  dependencies: z.array(z.string()).optional(), // Filter IDs this filter depends on
});

const SortOptionSchema = z.object({
  id: z.string(),
  label: z.string(),
  field: z.string(),
  direction: SortDirectionSchema.default("asc"),
  category: z.string().optional(),
  description: z.string().optional(),
  isDefault: z.boolean().default(false),
});

const ActiveFilterSchema = z.object({
  filterId: z.string(),
  value: FilterValueSchema,
  displayValue: z.string().optional(),
  appliedAt: z.string(),
});

const FilterPresetSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  searchType: SearchTypeSchema,
  filters: z.array(ActiveFilterSchema),
  sortOption: SortOptionSchema.optional(),
  isBuiltIn: z.boolean().default(false),
  createdAt: z.string(),
  usageCount: z.number().default(0),
});

// Types derived from schemas
export type FilterValue = z.infer<typeof FilterValueSchema>;
export type ValidatedFilterOption = z.infer<typeof FilterOptionSchema>;
export type ValidatedSortOption = z.infer<typeof SortOptionSchema>;
export type ActiveFilter = z.infer<typeof ActiveFilterSchema>;
export type FilterPreset = z.infer<typeof FilterPresetSchema>;
export type SortDirection = z.infer<typeof SortDirectionSchema>;

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
  setActiveFilter: (filterId: string, value: FilterValue) => Promise<boolean>;
  removeActiveFilter: (filterId: string) => void;
  updateActiveFilter: (filterId: string, value: FilterValue) => Promise<boolean>;
  clearAllFilters: () => void;
  clearFiltersByCategory: (category: string) => void;

  // Bulk filter operations
  setMultipleFilters: (filters: Record<string, FilterValue>) => Promise<boolean>;
  applyFiltersFromObject: (filterObject: Record<string, unknown>) => Promise<boolean>;
  resetFiltersToDefault: (searchType?: SearchType) => void;

  // Sort management
  setActiveSortOption: (option: ValidatedSortOption | null) => void;
  setSortById: (optionId: string) => void;
  toggleSortDirection: () => void;
  resetSortToDefault: (searchType?: SearchType) => void;

  // Filter presets
  saveFilterPreset: (name: string, description?: string) => Promise<string | null>;
  loadFilterPreset: (presetId: string) => Promise<boolean>;
  updateFilterPreset: (
    presetId: string,
    updates: Partial<FilterPreset>
  ) => Promise<boolean>;
  deleteFilterPreset: (presetId: string) => void;
  duplicateFilterPreset: (presetId: string, newName: string) => Promise<string | null>;
  incrementPresetUsage: (presetId: string) => void;

  // Filter validation
  validateFilter: (filterId: string, value: FilterValue) => Promise<boolean>;
  validateAllFilters: () => Promise<boolean>;
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
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Default filter configurations by search type
const getDefaultFilters = (searchType: SearchType): ValidatedFilterOption[] => {
  switch (searchType) {
    case "flight":
      return [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          required: false,
          category: "pricing",
          validation: { min: 0, max: 10000 },
        },
        {
          id: "stops",
          label: "Number of Stops",
          type: "select",
          required: false,
          category: "routing",
          options: [
            { value: "0", label: "Direct flights only" },
            { value: "1", label: "1 stop" },
            { value: "2", label: "2+ stops" },
          ],
        },
        {
          id: "airlines",
          label: "Airlines",
          type: "multiselect",
          required: false,
          category: "airline",
          options: [], // Would be populated dynamically
        },
        {
          id: "departure_time",
          label: "Departure Time",
          type: "select",
          required: false,
          category: "timing",
          options: [
            { value: "early_morning", label: "Early Morning (6:00-9:00)" },
            { value: "morning", label: "Morning (9:00-12:00)" },
            { value: "afternoon", label: "Afternoon (12:00-18:00)" },
            { value: "evening", label: "Evening (18:00+)" },
          ],
        },
      ];
    case "accommodation":
      return [
        {
          id: "price_range",
          label: "Price per Night",
          type: "range",
          required: false,
          category: "pricing",
          validation: { min: 0, max: 2000 },
        },
        {
          id: "rating",
          label: "Minimum Rating",
          type: "select",
          required: false,
          category: "quality",
          options: [
            { value: "3", label: "3+ stars" },
            { value: "4", label: "4+ stars" },
            { value: "5", label: "5 stars" },
          ],
        },
        {
          id: "property_type",
          label: "Property Type",
          type: "multiselect",
          required: false,
          category: "type",
          options: [
            { value: "hotel", label: "Hotel" },
            { value: "apartment", label: "Apartment" },
            { value: "villa", label: "Villa" },
            { value: "resort", label: "Resort" },
          ],
        },
        {
          id: "amenities",
          label: "Amenities",
          type: "multiselect",
          required: false,
          category: "features",
          options: [
            { value: "wifi", label: "Free WiFi" },
            { value: "parking", label: "Free Parking" },
            { value: "pool", label: "Swimming Pool" },
            { value: "gym", label: "Fitness Center" },
            { value: "spa", label: "Spa" },
            { value: "restaurant", label: "Restaurant" },
          ],
        },
      ];
    case "activity":
      return [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          required: false,
          category: "pricing",
          validation: { min: 0, max: 500 },
        },
        {
          id: "duration",
          label: "Duration",
          type: "range",
          required: false,
          category: "timing",
          validation: { min: 1, max: 480 }, // minutes
        },
        {
          id: "difficulty",
          label: "Difficulty Level",
          type: "select",
          required: false,
          category: "experience",
          options: [
            { value: "easy", label: "Easy" },
            { value: "moderate", label: "Moderate" },
            { value: "challenging", label: "Challenging" },
            { value: "extreme", label: "Extreme" },
          ],
        },
        {
          id: "category",
          label: "Activity Type",
          type: "multiselect",
          required: false,
          category: "type",
          options: [
            { value: "outdoor", label: "Outdoor Adventures" },
            { value: "cultural", label: "Cultural Experiences" },
            { value: "food", label: "Food & Drink" },
            { value: "sightseeing", label: "Sightseeing" },
            { value: "sports", label: "Sports & Recreation" },
          ],
        },
      ];
    case "destination":
      return [
        {
          id: "destination_type",
          label: "Destination Type",
          type: "multiselect",
          required: false,
          category: "type",
          options: [
            { value: "city", label: "Cities" },
            { value: "country", label: "Countries" },
            { value: "region", label: "Regions" },
            { value: "landmark", label: "Landmarks" },
          ],
        },
        {
          id: "population",
          label: "Population Size",
          type: "select",
          required: false,
          category: "demographics",
          options: [
            { value: "small", label: "Small (< 100k)" },
            { value: "medium", label: "Medium (100k - 1M)" },
            { value: "large", label: "Large (1M+)" },
          ],
        },
      ];
    default:
      return [];
  }
};

const getDefaultSortOptions = (searchType: SearchType): ValidatedSortOption[] => {
  const commonSorts = [
    {
      id: "relevance",
      label: "Relevance",
      field: "score",
      direction: "desc" as SortDirection,
      isDefault: true,
    },
    {
      id: "price_low",
      label: "Price: Low to High",
      field: "price",
      direction: "asc" as SortDirection,
      isDefault: false,
    },
    {
      id: "price_high",
      label: "Price: High to Low",
      field: "price",
      direction: "desc" as SortDirection,
      isDefault: false,
    },
  ];

  switch (searchType) {
    case "flight":
      return [
        ...commonSorts,
        {
          id: "duration",
          label: "Duration",
          field: "totalDuration",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
        {
          id: "departure",
          label: "Departure Time",
          field: "departureTime",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
        {
          id: "arrival",
          label: "Arrival Time",
          field: "arrivalTime",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
        {
          id: "stops",
          label: "Fewest Stops",
          field: "stops",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
      ];
    case "accommodation":
      return [
        ...commonSorts,
        {
          id: "rating",
          label: "Highest Rated",
          field: "rating",
          direction: "desc" as SortDirection,
          isDefault: false,
        },
        {
          id: "distance",
          label: "Distance",
          field: "distance",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
        {
          id: "reviews",
          label: "Most Reviews",
          field: "reviewCount",
          direction: "desc" as SortDirection,
          isDefault: false,
        },
      ];
    case "activity":
      return [
        ...commonSorts,
        {
          id: "rating",
          label: "Highest Rated",
          field: "rating",
          direction: "desc" as SortDirection,
          isDefault: false,
        },
        {
          id: "duration",
          label: "Duration",
          field: "duration",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
        {
          id: "popularity",
          label: "Most Popular",
          field: "bookingCount",
          direction: "desc" as SortDirection,
          isDefault: false,
        },
      ];
    case "destination":
      return [
        {
          id: "relevance",
          label: "Relevance",
          field: "score",
          direction: "desc" as SortDirection,
          isDefault: true,
        },
        {
          id: "alphabetical",
          label: "Alphabetical",
          field: "name",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
        {
          id: "population",
          label: "Population",
          field: "population",
          direction: "desc" as SortDirection,
          isDefault: false,
        },
        {
          id: "distance",
          label: "Distance",
          field: "distance",
          direction: "asc" as SortDirection,
          isDefault: false,
        },
      ];
    default:
      return commonSorts;
  }
};

export const useSearchFiltersStore = create<SearchFiltersState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        availableFilters: {
          flight: getDefaultFilters("flight"),
          accommodation: getDefaultFilters("accommodation"),
          activity: getDefaultFilters("activity"),
          destination: getDefaultFilters("destination"),
        },
        availableSortOptions: {
          flight: getDefaultSortOptions("flight"),
          accommodation: getDefaultSortOptions("accommodation"),
          activity: getDefaultSortOptions("activity"),
          destination: getDefaultSortOptions("destination"),
        },

        // Active filters and sorting
        activeFilters: {},
        activeSortOption: null,
        currentSearchType: null,

        // Filter presets
        filterPresets: [],
        activePreset: null,

        // Filter state management
        isApplyingFilters: false,
        filterValidationErrors: {},

        // Computed properties
        get hasActiveFilters() {
          return Object.keys(get().activeFilters).length > 0;
        },

        get activeFilterCount() {
          return Object.keys(get().activeFilters).length;
        },

        get canClearFilters() {
          return get().hasActiveFilters || get().activeSortOption !== null;
        },

        get currentFilters() {
          const { currentSearchType, availableFilters } = get();
          return currentSearchType ? availableFilters[currentSearchType] || [] : [];
        },

        get currentSortOptions() {
          const { currentSearchType, availableSortOptions } = get();
          return currentSearchType ? availableSortOptions[currentSearchType] || [] : [];
        },

        get appliedFilterSummary() {
          const { activeFilters, currentFilters } = get();
          const summaries: string[] = [];

          Object.entries(activeFilters).forEach(([filterId, activeFilter]) => {
            const filterConfig = currentFilters.find((f) => f.id === filterId);
            if (filterConfig) {
              const displayValue =
                activeFilter.displayValue || String(activeFilter.value);
              summaries.push(`${filterConfig.label}: ${displayValue}`);
            }
          });

          return summaries.join(", ");
        },

        // Filter configuration actions
        setAvailableFilters: (searchType, filters) => {
          // Validate filters
          const validatedFilters = filters.filter((filter) => {
            const result = FilterOptionSchema.safeParse(filter);
            if (!result.success) {
              console.error(`Invalid filter for ${searchType}:`, result.error);
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

        addAvailableFilter: (searchType, filter) => {
          const result = FilterOptionSchema.safeParse(filter);
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
            console.error("Invalid filter:", result.error);
          }
        },

        updateAvailableFilter: (searchType, filterId, updates) => {
          set((state) => {
            const filters = state.availableFilters[searchType] || [];
            const updatedFilters = filters.map((filter) => {
              if (filter.id === filterId) {
                const updatedFilter = { ...filter, ...updates };
                const result = FilterOptionSchema.safeParse(updatedFilter);
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

        removeAvailableFilter: (searchType, filterId) => {
          set((state) => ({
            availableFilters: {
              ...state.availableFilters,
              [searchType]: (state.availableFilters[searchType] || []).filter(
                (f) => f.id !== filterId
              ),
            },
          }));
        },

        // Sort options configuration
        setAvailableSortOptions: (searchType, options) => {
          const validatedOptions = options.filter((option) => {
            const result = SortOptionSchema.safeParse(option);
            if (!result.success) {
              console.error(`Invalid sort option for ${searchType}:`, result.error);
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

        addAvailableSortOption: (searchType, option) => {
          const result = SortOptionSchema.safeParse(option);
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
            console.error("Invalid sort option:", result.error);
          }
        },

        updateAvailableSortOption: (searchType, optionId, updates) => {
          set((state) => {
            const options = state.availableSortOptions[searchType] || [];
            const updatedOptions = options.map((option) => {
              if (option.id === optionId) {
                const updatedOption = { ...option, ...updates };
                const result = SortOptionSchema.safeParse(updatedOption);
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

        // Active filter management
        setActiveFilter: async (filterId, value) => {
          set({ isApplyingFilters: true });

          try {
            const isValid = await get().validateFilter(filterId, value);
            if (!isValid) {
              set({ isApplyingFilters: false });
              return false;
            }

            const newActiveFilter: ActiveFilter = {
              filterId,
              value,
              appliedAt: getCurrentTimestamp(),
            };

            set((state) => ({
              activeFilters: {
                ...state.activeFilters,
                [filterId]: newActiveFilter,
              },
              isApplyingFilters: false,
              activePreset: null, // Clear active preset when filters change manually
            }));

            return true;
          } catch (error) {
            console.error("Failed to set active filter:", error);
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

        updateActiveFilter: async (filterId, value) => {
          return await get().setActiveFilter(filterId, value);
        },

        clearAllFilters: () => {
          set({
            activeFilters: {},
            activeSortOption: null,
            activePreset: null,
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

        // Bulk filter operations
        setMultipleFilters: async (filters) => {
          set({ isApplyingFilters: true });

          try {
            const newActiveFilters: Record<string, ActiveFilter> = {};
            const timestamp = getCurrentTimestamp();

            for (const [filterId, value] of Object.entries(filters)) {
              const isValid = await get().validateFilter(filterId, value);
              if (isValid) {
                newActiveFilters[filterId] = {
                  filterId,
                  value,
                  appliedAt: timestamp,
                };
              }
            }

            set({
              activeFilters: { ...get().activeFilters, ...newActiveFilters },
              isApplyingFilters: false,
              activePreset: null,
            });

            return true;
          } catch (error) {
            console.error("Failed to set multiple filters:", error);
            set({ isApplyingFilters: false });
            return false;
          }
        },

        applyFiltersFromObject: async (filterObject) => {
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
          return await get().setMultipleFilters(validatedFilters);
        },

        resetFiltersToDefault: (searchType) => {
          const targetSearchType = searchType || get().currentSearchType;
          if (!targetSearchType) return;

          const defaultFilters = getDefaultFilters(targetSearchType);
          const defaultSort = getDefaultSortOptions(targetSearchType).find(
            (s) => s.isDefault
          );

          set({
            activeFilters: {},
            activeSortOption: defaultSort || null,
            activePreset: null,
            filterValidationErrors: {},
          });
        },

        // Sort management
        setActiveSortOption: (option) => {
          if (option) {
            const result = SortOptionSchema.safeParse(option);
            if (result.success) {
              set({
                activeSortOption: result.data,
                activePreset: null, // Clear active preset when sort changes
              });
            } else {
              console.error("Invalid sort option:", result.error);
            }
          } else {
            set({ activeSortOption: null });
          }
        },

        setSortById: (optionId) => {
          const { currentSortOptions } = get();
          const option = currentSortOptions.find((o) => o.id === optionId);
          if (option) {
            get().setActiveSortOption(option);
          }
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

        resetSortToDefault: (searchType) => {
          const targetSearchType = searchType || get().currentSearchType;
          if (!targetSearchType) return;

          const defaultSort = getDefaultSortOptions(targetSearchType).find(
            (s) => s.isDefault
          );
          set({ activeSortOption: defaultSort || null });
        },

        // Filter presets
        saveFilterPreset: async (name, description) => {
          const { currentSearchType, activeFilters, activeSortOption } = get();
          if (!currentSearchType) return null;

          try {
            const presetId = generateId();
            const newPreset: FilterPreset = {
              id: presetId,
              name,
              description,
              searchType: currentSearchType,
              filters: Object.values(activeFilters),
              sortOption: activeSortOption || undefined,
              isBuiltIn: false,
              createdAt: getCurrentTimestamp(),
              usageCount: 0,
            };

            const result = FilterPresetSchema.safeParse(newPreset);
            if (result.success) {
              set((state) => ({
                filterPresets: [...state.filterPresets, result.data],
              }));
              return presetId;
            }
            console.error("Invalid filter preset:", result.error);
            return null;
          } catch (error) {
            console.error("Failed to save filter preset:", error);
            return null;
          }
        },

        loadFilterPreset: async (presetId) => {
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
              activeSortOption: preset.sortOption || null,
              activePreset: preset,
              isApplyingFilters: false,
            });

            // Increment usage count
            get().incrementPresetUsage(presetId);

            return true;
          } catch (error) {
            console.error("Failed to load filter preset:", error);
            set({ isApplyingFilters: false });
            return false;
          }
        },

        updateFilterPreset: async (presetId, updates) => {
          try {
            set((state) => {
              const updatedPresets = state.filterPresets.map((preset) => {
                if (preset.id === presetId) {
                  const updatedPreset = { ...preset, ...updates };
                  const result = FilterPresetSchema.safeParse(updatedPreset);
                  return result.success ? result.data : preset;
                }
                return preset;
              });

              return { filterPresets: updatedPresets };
            });

            return true;
          } catch (error) {
            console.error("Failed to update filter preset:", error);
            return false;
          }
        },

        deleteFilterPreset: (presetId) => {
          set((state) => ({
            filterPresets: state.filterPresets.filter((p) => p.id !== presetId),
            activePreset:
              state.activePreset?.id === presetId ? null : state.activePreset,
          }));
        },

        duplicateFilterPreset: async (presetId, newName) => {
          const { filterPresets } = get();
          const originalPreset = filterPresets.find((p) => p.id === presetId);

          if (!originalPreset) return null;

          const duplicatedPreset: FilterPreset = {
            ...originalPreset,
            id: generateId(),
            name: newName,
            isBuiltIn: false,
            createdAt: getCurrentTimestamp(),
            usageCount: 0,
          };

          const result = FilterPresetSchema.safeParse(duplicatedPreset);
          if (result.success) {
            set((state) => ({
              filterPresets: [...state.filterPresets, result.data],
            }));
            return duplicatedPreset.id;
          }

          return null;
        },

        incrementPresetUsage: (presetId) => {
          set((state) => ({
            filterPresets: state.filterPresets.map((preset) =>
              preset.id === presetId
                ? { ...preset, usageCount: preset.usageCount + 1 }
                : preset
            ),
          }));
        },

        // Filter validation
        validateFilter: async (filterId, value) => {
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
            const valueResult = FilterValueSchema.safeParse(value);
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

        validateAllFilters: async () => {
          const { activeFilters } = get();
          const validationPromises = Object.entries(activeFilters).map(
            async ([filterId, filter]) => {
              return await get().validateFilter(filterId, filter.value);
            }
          );

          const results = await Promise.all(validationPromises);
          return results.every((result) => result);
        },

        getFilterValidationError: (filterId) => {
          return get().filterValidationErrors[filterId] || null;
        },

        // Search type context
        setSearchType: (searchType) => {
          const result = SearchTypeSchema.safeParse(searchType);
          if (result.success) {
            const { availableSortOptions } = get();
            const defaultSort = availableSortOptions[searchType]?.find(
              (s) => s.isDefault
            );

            set({
              currentSearchType: result.data,
              activeSortOption: defaultSort || null,
              activePreset: null, // Clear preset when changing search type
            });
          } else {
            console.error("Invalid search type:", result.error);
          }
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

        getFilterDependencies: (filterId) => {
          const { currentFilters } = get();
          const filter = currentFilters.find((f) => f.id === filterId);

          if (!filter || !filter.dependencies) return [];

          return currentFilters.filter((f) => filter.dependencies?.includes(f.id));
        },

        // Utility actions
        clearValidationErrors: () => {
          set({ filterValidationErrors: {} });
        },

        clearValidationError: (filterId) => {
          set((state) => {
            const newErrors = { ...state.filterValidationErrors };
            delete newErrors[filterId];
            return { filterValidationErrors: newErrors };
          });
        },

        reset: () => {
          set({
            activeFilters: {},
            activeSortOption: null,
            currentSearchType: null,
            filterPresets: [],
            activePreset: null,
            isApplyingFilters: false,
            filterValidationErrors: {},
          });
        },

        softReset: () => {
          set({
            activeFilters: {},
            activeSortOption: null,
            activePreset: null,
            isApplyingFilters: false,
            filterValidationErrors: {},
          });
        },
      }),
      {
        name: "search-filters-storage",
        partialize: (state) => ({
          // Persist filter presets and available configurations
          filterPresets: state.filterPresets,
          availableFilters: state.availableFilters,
          availableSortOptions: state.availableSortOptions,
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
