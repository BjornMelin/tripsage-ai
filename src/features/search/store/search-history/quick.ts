/**
 * @fileoverview Quick searches slice for search history store.
 */

import type { QuickSearch } from "@schemas/stores";
import { quickSearchSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { generateId, getCurrentTimestamp } from "@/features/shared/store/helpers";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import type { QuickSearchesSlice, SearchHistoryState } from "./types";

const logger = createStoreLogger({ storeName: "search-history" });

export const createQuickSearchesSlice: StateCreator<
  SearchHistoryState,
  [],
  [],
  QuickSearchesSlice
> = (set, get) => ({
  createQuickSearch: (label, searchType, params, options = {}) => {
    try {
      const quickSearchId = generateId();
      const timestamp = getCurrentTimestamp();

      const newQuickSearch: QuickSearch = {
        color: options.color,
        createdAt: timestamp,
        icon: options.icon,
        id: quickSearchId,
        isVisible: true,
        label,
        params: params as Record<string, unknown>,
        searchType,
        sortOrder: options.sortOrder || get().quickSearches.length,
      };

      const result = quickSearchSchema.safeParse(newQuickSearch);
      if (result.success) {
        set((state) => ({
          quickSearches: [...state.quickSearches, result.data],
        }));

        return Promise.resolve(quickSearchId);
      }
      logger.error("Invalid quick search data", {
        error: result.error,
        input: newQuickSearch,
      });
      throw new Error("Invalid quick search data");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create quick search";
      set({ error: message });
      return Promise.resolve(null);
    }
  },

  deleteQuickSearch: (quickSearchId) => {
    set((state) => ({
      quickSearches: state.quickSearches.filter(
        (quickSearch) => quickSearch.id !== quickSearchId
      ),
    }));
  },
  quickSearches: [],

  reorderQuickSearches: (quickSearchIds) => {
    set((state) => {
      const reorderedQuickSearches = quickSearchIds
        .map((id, index) => {
          const quickSearch = state.quickSearches.find((qs) => qs.id === id);
          return quickSearch ? { ...quickSearch, sortOrder: index } : null;
        })
        .filter(Boolean) as QuickSearch[];

      return { quickSearches: reorderedQuickSearches };
    });
  },

  updateQuickSearch: (quickSearchId, updates) => {
    try {
      set((state) => ({
        quickSearches: state.quickSearches.map((quickSearch) => {
          if (quickSearch.id === quickSearchId) {
            const updatedQuickSearch = { ...quickSearch, ...updates };
            const result = quickSearchSchema.safeParse(updatedQuickSearch);
            return result.success ? result.data : quickSearch;
          }
          return quickSearch;
        }),
      }));

      return Promise.resolve(true);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to update quick search";
      set({ error: message });
      return Promise.resolve(false);
    }
  },
});
