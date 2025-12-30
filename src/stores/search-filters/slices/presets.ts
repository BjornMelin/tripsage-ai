/**
 * @fileoverview Filter presets slice for the search filters store.
 */

import type { ActiveFilter, FilterPreset } from "@schemas/stores";
import { filterPresetSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import type { SearchFiltersState, SearchFiltersStoreDeps } from "../types";

type SearchFiltersPresetsSlice = Pick<
  SearchFiltersState,
  | "deleteFilterPreset"
  | "duplicateFilterPreset"
  | "filterPresets"
  | "incrementPresetUsage"
  | "loadFilterPreset"
  | "saveFilterPreset"
  | "updateFilterPreset"
>;

export const createSearchFiltersPresetsSlice =
  (
    deps: SearchFiltersStoreDeps
  ): StateCreator<SearchFiltersState, [], [], SearchFiltersPresetsSlice> =>
  (set, get) => ({
    deleteFilterPreset: (presetId) => {
      set((state) => ({
        activePreset: state.activePreset?.id === presetId ? null : state.activePreset,
        filterPresets: state.filterPresets.filter((p) => p.id !== presetId),
      }));
    },

    duplicateFilterPreset: (presetId, newName) => {
      const { filterPresets } = get();
      const originalPreset = filterPresets.find((p) => p.id === presetId);

      if (!originalPreset) return null;

      const duplicatedPreset: FilterPreset = {
        ...originalPreset,
        createdAt: deps.nowIso(),
        id: deps.generateId(),
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

    filterPresets: [],

    incrementPresetUsage: (presetId) => {
      set((state) => ({
        filterPresets: state.filterPresets.map((preset) =>
          preset.id === presetId
            ? { ...preset, usageCount: preset.usageCount + 1 }
            : preset
        ),
      }));
    },

    loadFilterPreset: (presetId) => {
      const { filterPresets } = get();
      const preset = filterPresets.find((p) => p.id === presetId);

      if (!preset) return false;

      try {
        set({ isApplyingFilters: true });

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

        get().incrementPresetUsage(presetId);
        return true;
      } catch (error) {
        deps.logger.error("Failed to load filter preset", { error });
        set({ isApplyingFilters: false });
        return false;
      }
    },

    saveFilterPreset: (name, description) => {
      const { currentSearchType, activeFilters, activeSortOption } = get();
      if (!currentSearchType) return null;

      try {
        const presetId = deps.generateId();
        const newPreset: FilterPreset = {
          createdAt: deps.nowIso(),
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

        deps.logger.error("Invalid filter preset", { error: result.error });
        return null;
      } catch (error) {
        deps.logger.error("Failed to save filter preset", { error });
        return null;
      }
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
        deps.logger.error("Failed to update filter preset", { error });
        return false;
      }
    },
  });
