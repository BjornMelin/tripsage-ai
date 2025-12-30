/**
 * @fileoverview Zustand store for managing search filters, sort options, and presets.
 */

import type { SearchType } from "@schemas/search";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { generateId, getCurrentTimestamp } from "./helpers";
import { withComputed } from "./middleware/computed";
import { computeFilterState } from "./search-filters/computed";
import {
  selectCurrentFilters,
  selectCurrentSortOptions,
} from "./search-filters/selectors";
import { createSearchFiltersCoreSlice } from "./search-filters/slices/core";
import { createSearchFiltersFiltersSlice } from "./search-filters/slices/filters";
import { createSearchFiltersPresetsSlice } from "./search-filters/slices/presets";
import type {
  SearchFiltersState,
  SearchFiltersStoreDeps,
} from "./search-filters/types";

const logger = createStoreLogger({ storeName: "search-filters" });

const deps: SearchFiltersStoreDeps = {
  generateId: () => generateId(12),
  logger,
  nowIso: getCurrentTimestamp,
};

export const useSearchFiltersStore = create<SearchFiltersState>()(
  devtools(
    persist(
      withComputed({ compute: computeFilterState }, (...args) => ({
        ...createSearchFiltersCoreSlice(deps)(...args),
        ...createSearchFiltersFiltersSlice(deps)(...args),
        ...createSearchFiltersPresetsSlice(deps)(...args),
      })),
      {
        name: "search-filters-storage",
        partialize: (state) => ({
          availableFilters: state.availableFilters,
          availableSortOptions: state.availableSortOptions,
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
  useSearchFiltersStore((state) => selectCurrentFilters(state));
export const useCurrentSortOptions = () =>
  useSearchFiltersStore((state) => selectCurrentSortOptions(state));
export const useHasActiveFilters = () =>
  useSearchFiltersStore((state) => Object.keys(state.activeFilters).length > 0);
export const useActiveFilterCount = () =>
  useSearchFiltersStore((state) => Object.keys(state.activeFilters).length);
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
