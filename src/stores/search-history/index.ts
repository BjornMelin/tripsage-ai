/**
 * @fileoverview Search history store composed from modular slices.
 */

import type { SearchType } from "@schemas/search";
import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { withComputed } from "@/stores/middleware/computed";
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
import type { SearchAnalytics, SearchHistoryState } from "./types";

const MS_PER_DAY = 86_400_000;

/**
 * Build a fixed-length (N days) search trend series from per-day counts.
 *
 * Dates are normalized to UTC and returned as `YYYY-MM-DD` strings.
 *
 * @param searchesByDay - Map keyed by `YYYY-MM-DD` with daily counts.
 * @param now - Reference time (defaults to `new Date()`).
 * @param days - Number of days to include (defaults to `30`).
 * @returns Array of `{ date, count }` entries ordered oldest → newest.
 */
export const buildSearchTrends = (
  searchesByDay: Map<string, number>,
  now: Date = new Date(),
  days: number = 30
): Array<{ date: string; count: number }> => {
  const baseUtcMs = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const trends: Array<{ date: string; count: number }> = [];

  for (let i = days - 1; i >= 0; i -= 1) {
    const date = new Date(baseUtcMs - i * MS_PER_DAY);
    const dateStr = date.toISOString().slice(0, 10);
    trends.push({ count: searchesByDay.get(dateStr) ?? 0, date: dateStr });
  }

  return trends;
};

const computeSearchAnalytics = (
  recentSearches: SearchHistoryItem[],
  savedSearches: ValidatedSavedSearch[]
): SearchAnalytics => {
  const totalSearches = recentSearches.length;
  const searchesByType: Record<SearchType, number> = {
    accommodation: 0,
    activity: 0,
    destination: 0,
    flight: 0,
  };

  const searchesByDay = new Map<string, number>();
  const searchesByHour = new Array<number>(24).fill(0);

  let totalDuration = 0;

  for (const search of recentSearches) {
    searchesByType[search.searchType] += 1;
    totalDuration += search.searchDuration ?? 0;

    const ts = new Date(search.timestamp);
    const tsMs = ts.getTime();
    if (!Number.isFinite(tsMs)) continue;

    const dateKey = ts.toISOString().slice(0, 10);
    searchesByDay.set(dateKey, (searchesByDay.get(dateKey) ?? 0) + 1);

    const hour = ts.getUTCHours();
    if (!Number.isFinite(hour)) continue;
    searchesByHour[hour] += 1;
  }

  const averageSearchDuration = totalSearches > 0 ? totalDuration / totalSearches : 0;

  const mostUsedSearchTypes = Object.entries(searchesByType)
    .map(([type, count]) => ({
      count,
      percentage: totalSearches > 0 ? (count / totalSearches) * 100 : 0,
      type: type as SearchType,
    }))
    .sort((a, b) => b.count - a.count);

  const searchTrends = buildSearchTrends(searchesByDay);

  const popularSearchTimes: Array<{ hour: number; count: number }> = searchesByHour.map(
    (count, hour) => ({ count, hour })
  );

  return {
    averageSearchDuration,
    mostUsedSearchTypes,
    popularSearchTimes,
    savedSearchUsage: savedSearches
      .filter((search) => search.usageCount > 0)
      .sort((a, b) => b.usageCount - a.usageCount)
      .slice(0, 10)
      .map((search) => ({
        name: search.name,
        searchId: search.id,
        usageCount: search.usageCount,
      })),
    searchesByType,
    searchTrends,
    topDestinations: [],
    totalSearches,
  };
};

/** Compute derived search history properties. */
const computeSearchHistory = (
  state: SearchHistoryState
): Partial<SearchHistoryState> => {
  // Compute favoriteSearches
  const favoriteSearches: ValidatedSavedSearch[] = state.savedSearches.filter(
    (search) => search.isFavorite
  );

  // Compute recentSearchesByType
  const recentSearchesByType: Record<SearchType, SearchHistoryItem[]> = {
    accommodation: [],
    activity: [],
    destination: [],
    flight: [],
  };
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
          recentSearchesByType: {
            accommodation: [],
            activity: [],
            destination: [],
            flight: [],
          } satisfies Record<SearchType, SearchHistoryItem[]>,

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
            searchesByType: {
              accommodation: 0,
              activity: 0,
              destination: 0,
              flight: 0,
            },
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
