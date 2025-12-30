/**
 * @fileoverview Shared types for the search filters Zustand store slices.
 */

import type { SearchType } from "@schemas/search";
import type {
  ActiveFilter,
  FilterPreset,
  FilterValue,
  ValidatedFilterOption,
  ValidatedSortOption,
} from "@schemas/stores";

export type SearchFiltersStoreLogger = {
  error: (message: string, context?: Record<string, unknown>) => void;
};

export type SearchFiltersStoreDeps = {
  generateId: () => string;
  logger: SearchFiltersStoreLogger;
  nowIso: () => string;
};

export interface SearchFiltersState {
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
  currentFilters: ValidatedFilterOption[];
  currentSortOptions: ValidatedSortOption[];
  appliedFilterSummary: string;

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
