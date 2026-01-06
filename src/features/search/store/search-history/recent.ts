/**
 * @fileoverview Recent searches slice for search history store.
 */

import type { SearchHistoryItem } from "@schemas/stores";
import { searchHistoryItemSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { generateId, getCurrentTimestamp } from "@/features/shared/store/helpers";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import type { RecentSearchesSlice, SearchHistoryState } from "./types";

const logger = createStoreLogger({ storeName: "search-history" });

export const DEFAULT_MAX_RECENT_SEARCHES = 50;
export const DEFAULT_AUTO_CLEANUP_DAYS = 30;

export const createRecentSearchesSlice: StateCreator<
  SearchHistoryState,
  [],
  [],
  RecentSearchesSlice
> = (set, get) => ({
  addRecentSearch: (searchType, params, metadata = {}) => {
    const { maxRecentSearches, recentSearches } = get();
    const timestamp = getCurrentTimestamp();

    // Check if similar search already exists (avoid duplicates)
    const paramsString = JSON.stringify(params);
    const existingIndex = recentSearches.findIndex(
      (search) =>
        search.searchType === searchType &&
        JSON.stringify(search.params) === paramsString
    );

    if (existingIndex >= 0) {
      // Update existing search timestamp
      set((state) => ({
        recentSearches: [
          {
            ...state.recentSearches[existingIndex],
            timestamp,
          },
          ...state.recentSearches.filter((_, index) => index !== existingIndex),
        ],
      }));
      return;
    }

    // Add new search
    const newSearch: SearchHistoryItem = {
      id: generateId(),
      params: params as Record<string, unknown>,
      searchType,
      timestamp,
      ...metadata,
    };

    const result = searchHistoryItemSchema.safeParse(newSearch);
    if (result.success) {
      set((state) => ({
        recentSearches: [
          result.data,
          ...state.recentSearches.slice(0, maxRecentSearches - 1),
        ],
      }));

      // Update search suggestions
      get().updateSearchSuggestions();
    } else {
      logger.error("Invalid search history item", {
        error: result.error,
        input: newSearch,
      });
      throw new Error("Failed to validate search history item");
    }
  },
  autoCleanupDays: DEFAULT_AUTO_CLEANUP_DAYS,
  autoSaveEnabled: true,

  cleanupOldSearches: () => {
    const { autoCleanupDays } = get();
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - autoCleanupDays);

    set((state) => ({
      recentSearches: state.recentSearches.filter(
        (search) => new Date(search.timestamp) > cutoffDate
      ),
    }));
  },

  clearRecentSearches: (searchType) => {
    if (searchType) {
      set((state) => ({
        recentSearches: state.recentSearches.filter(
          (search) => search.searchType !== searchType
        ),
      }));
    } else {
      set({ recentSearches: [] });
    }
  },

  getRecentSearchesByType: (searchType, limit = 10) => {
    return get()
      .recentSearches.filter((search) => search.searchType === searchType)
      .slice(0, limit);
  },
  maxRecentSearches: DEFAULT_MAX_RECENT_SEARCHES,
  recentSearches: [],

  removeRecentSearch: (searchId) => {
    set((state) => ({
      recentSearches: state.recentSearches.filter((search) => search.id !== searchId),
    }));
  },
});
