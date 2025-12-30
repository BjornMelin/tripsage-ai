/**
 * @fileoverview Core slice for the search filters store (config + sort + lifecycle).
 */

import { searchTypeSchema, sortOptionSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { FILTER_CONFIGS, getDefaultSortOptions, SORT_CONFIGS } from "../filter-configs";
import { selectCurrentSortOptions } from "../selectors";
import type { SearchFiltersState, SearchFiltersStoreDeps } from "../types";

type SearchFiltersCoreSlice = Pick<
  SearchFiltersState,
  | "activePreset"
  | "activeSortOption"
  | "appliedFilterSummary"
  | "availableFilters"
  | "availableSortOptions"
  | "currentSearchType"
  | "reset"
  | "resetFiltersToDefault"
  | "resetSortToDefault"
  | "setActiveSortOption"
  | "setSearchType"
  | "setSortById"
  | "softReset"
  | "toggleSortDirection"
>;

export const createSearchFiltersCoreSlice =
  (
    deps: SearchFiltersStoreDeps
  ): StateCreator<SearchFiltersState, [], [], SearchFiltersCoreSlice> =>
  (set, get) => ({
    activePreset: null,
    activeSortOption: null,
    appliedFilterSummary: "",

    availableFilters: FILTER_CONFIGS,
    availableSortOptions: SORT_CONFIGS,

    currentSearchType: null,

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

    setActiveSortOption: (option) => {
      if (option) {
        const result = sortOptionSchema.safeParse(option);
        if (result.success) {
          set({
            activePreset: null,
            activeSortOption: result.data,
          });
        } else {
          deps.logger.error("Invalid sort option", { error: result.error });
        }
        return;
      }

      set({ activeSortOption: null });
    },

    setSearchType: (searchType) => {
      const result = searchTypeSchema.safeParse(searchType);
      if (result.success) {
        const { availableSortOptions } = get();
        const defaultSort = availableSortOptions[result.data]?.find((s) => s.isDefault);

        set({
          activePreset: null,
          activeSortOption: defaultSort || null,
          currentSearchType: result.data,
        });
        return;
      }

      deps.logger.error("Invalid search type", { error: result.error });
    },

    setSortById: (optionId) => {
      const currentSortOptions = selectCurrentSortOptions(get());
      const option = currentSortOptions.find((o) => o.id === optionId);
      if (option) {
        get().setActiveSortOption(option);
      } else {
        deps.logger.warn("Sort option not found", {
          currentSortOptionIds: currentSortOptions.map((current) => current.id),
          optionId,
        });
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
      if (!activeSortOption) return;

      const newDirection = activeSortOption.direction === "asc" ? "desc" : "asc";
      get().setActiveSortOption({ ...activeSortOption, direction: newDirection });
    },
  });
