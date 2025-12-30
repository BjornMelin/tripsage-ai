/**
 * @fileoverview Computed state helpers for the search filters store.
 */

import { createComputeFn } from "../middleware/computed";
import type { SearchFiltersState } from "./types";

export const computeFilterState = createComputeFn<SearchFiltersState>({
  activeFilterCount: (state) => Object.keys(state.activeFilters || {}).length,
  appliedFilterSummary: (state) => {
    const currentFilters = state.currentSearchType
      ? state.availableFilters?.[state.currentSearchType] || []
      : [];
    const summaries: string[] = [];

    Object.entries(state.activeFilters || {}).forEach(([filterId, activeFilter]) => {
      const filter = currentFilters.find((f) => f.id === filterId);
      if (!filter) return;

      const valueStr = Array.isArray(activeFilter.value)
        ? activeFilter.value.join(", ")
        : typeof activeFilter.value === "object" && activeFilter.value !== null
          ? `${(activeFilter.value as { min?: number; max?: number }).min || ""} - ${
              (activeFilter.value as { min?: number; max?: number }).max || ""
            }`
          : String(activeFilter.value);

      summaries.push(`${filter.label}: ${valueStr}`);
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
