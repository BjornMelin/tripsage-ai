/**
 * @fileoverview Search history store composed from modular slices.
 */

import type { SearchType } from "@schemas/search";
import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { withComputed } from "@/stores/middleware/computed";
import { createAnalyticsSlice } from "./analytics";
import { computeSearchAnalytics, createSearchTypeRecord } from "./analytics-utils";
import { createCollectionsSlice } from "./collections";
import { createQuickSearchesSlice } from "./quick";
import {
  createRecentSearchesSlice,
  DEFAULT_AUTO_CLEANUP_DAYS,
  DEFAULT_MAX_RECENT_SEARCHES,
} from "./recent";
import { createSavedSearchesSlice } from "./saved";
import { createSuggestionsSlice } from "./suggestions";
import type { SearchAnalytics, SearchHistoryState } from "./types";

export { buildSearchTrends } from "./analytics-utils";

/** Compute derived search history properties. */
const computeSearchHistory = (
  state: SearchHistoryState
): Partial<SearchHistoryState> => {
  // Compute favoriteSearches
  const favoriteSearches: ValidatedSavedSearch[] = state.savedSearches.filter(
    (search) => search.isFavorite
  );

  // Compute recentSearchesByType
  const recentSearchesByType = createSearchTypeRecord<SearchHistoryItem[]>(
    (): SearchHistoryItem[] => []
  );
  state.recentSearches.forEach((search) => {
    recentSearchesByType[search.searchType].push(search);
  });

  // Compute searchAnalytics
  const searchAnalytics: SearchAnalytics = computeSearchAnalytics(
    state.recentSearches,
    state.savedSearches
  );

  // Compute totalSavedSearches
  const totalSavedSearches = state.savedSearches.length;

  return {
    favoriteSearches,
    recentSearchesByType,
    searchAnalytics,
    totalSavedSearches,
  };
};

export const useSearchHistoryStore = create<SearchHistoryState>()(
  devtools(
    persist(
      withComputed({ compute: computeSearchHistory }, (...args) => {
        const [set, get] = args;

        // Compose all slices
        const recentSlice = createRecentSearchesSlice(...args);
        const savedSlice = createSavedSearchesSlice(...args);
        const collectionsSlice = createCollectionsSlice(...args);
        const quickSlice = createQuickSearchesSlice(...args);
        const suggestionsSlice = createSuggestionsSlice(...args);
        const analyticsSlice = createAnalyticsSlice(...args);

        return {
          // Spread all slices
          ...recentSlice,
          ...savedSlice,
          ...collectionsSlice,
          ...quickSlice,
          ...suggestionsSlice,
          ...analyticsSlice,

          // Utility actions
          clearAllData: () => {
            set({
              popularSearchTerms: [],
              quickSearches: [],
              recentSearches: [],
              savedSearches: [],
              searchCollections: [],
              searchSuggestions: [],
            });
          },

          // Computed properties - initial values (updated via withComputed)
          favoriteSearches: [] satisfies ValidatedSavedSearch[],
          recentSearchesByType: createSearchTypeRecord<SearchHistoryItem[]>(
            (): SearchHistoryItem[] => []
          ) satisfies Record<SearchType, SearchHistoryItem[]>,

          reset: () => {
            set({
              autoCleanupDays: DEFAULT_AUTO_CLEANUP_DAYS,
              autoSaveEnabled: true,
              error: null,
              isLoading: false,
              maxRecentSearches: DEFAULT_MAX_RECENT_SEARCHES,
              popularSearchTerms: [],
              quickSearches: [],
              recentSearches: [],
              savedSearches: [],
              searchCollections: [],
              searchSuggestions: [],
            });
          },
          searchAnalytics: {
            averageSearchDuration: 0,
            mostUsedSearchTypes: [],
            popularSearchTimes: [],
            savedSearchUsage: [],
            searchesByType: createSearchTypeRecord(() => 0),
            searchTrends: [],
            topDestinations: [],
            totalSearches: 0,
          } satisfies SearchAnalytics,
          totalSavedSearches: 0,

          // Settings management
          updateSettings: (settings) => {
            set((state) => ({
              autoCleanupDays: settings.autoCleanupDays ?? state.autoCleanupDays,
              autoSaveEnabled: settings.autoSaveEnabled ?? state.autoSaveEnabled,
              maxRecentSearches: settings.maxRecentSearches ?? state.maxRecentSearches,
            }));

            // Apply cleanup if enabled
            if (settings.autoCleanupDays !== undefined) {
              get().cleanupOldSearches();
            }
          },
        };
      }),
      {
        name: "search-history-storage",
        partialize: (state) => ({
          autoCleanupDays: state.autoCleanupDays,
          autoSaveEnabled: state.autoSaveEnabled,
          maxRecentSearches: state.maxRecentSearches,
          popularSearchTerms: state.popularSearchTerms,
          quickSearches: state.quickSearches,
          recentSearches: state.recentSearches,
          savedSearches: state.savedSearches,
          searchCollections: state.searchCollections,
          searchSuggestions: state.searchSuggestions,
        }),
      }
    ),
    { name: "SearchHistoryStore" }
  )
);
