/**
 * @fileoverview Search history store composed from modular slices.
 */

import type { SearchType } from "@schemas/search";
import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createAnalyticsSlice } from "./analytics";
import { createCollectionsSlice } from "./collections";
import { createQuickSearchesSlice } from "./quick";
import {
  createRecentSearchesSlice,
  DEFAULT_AUTO_CLEANUP_DAYS,
  DEFAULT_MAX_RECENT_SEARCHES,
} from "./recent";
import { createSavedSearchesSlice } from "./saved";
import { createSuggestionsSlice } from "./suggestions";
import type { SearchHistoryState } from "./types";

export const useSearchHistoryStore = create<SearchHistoryState>()(
  devtools(
    persist(
      (...args) => {
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

          get favoriteSearches(): ValidatedSavedSearch[] {
            return get().savedSearches.filter((search) => search.isFavorite);
          },

          get recentSearchesByType() {
            const { recentSearches } = get();
            const grouped: Record<SearchType, SearchHistoryItem[]> = {
              accommodation: [],
              activity: [],
              destination: [],
              flight: [],
            };

            recentSearches.forEach((search) => {
              grouped[search.searchType].push(search);
            });

            return grouped;
          },

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

          get searchAnalytics() {
            return get().getSearchAnalytics();
          },

          // Computed properties (defined at composition level where get() is available)
          get totalSavedSearches() {
            return get().savedSearches.length;
          },

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
      },
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
