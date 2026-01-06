/**
 * @fileoverview Selector hooks for search history store.
 */

import type { SearchType } from "@schemas/search";
import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import { useSearchHistoryStore } from "./index";
import type { SearchHistoryState } from "./types";

// Basic selectors
export const useRecentSearches = (searchType?: SearchType, limit?: number) =>
  useSearchHistoryStore((state) =>
    searchType
      ? state.getRecentSearchesByType(searchType, limit)
      : state.recentSearches.slice(0, limit || 10)
  );

export const useSavedSearches = (searchType?: SearchType) =>
  useSearchHistoryStore((state) =>
    searchType ? state.getSavedSearchesByType(searchType) : state.savedSearches
  );

export const useFavoriteSearches = () =>
  useSearchHistoryStore((state) => state.favoriteSearches);

export const useSearchCollections = () =>
  useSearchHistoryStore((state) => state.searchCollections);

export const useQuickSearches = () =>
  useSearchHistoryStore((state) =>
    state.quickSearches
      .filter((qs) => qs.isVisible)
      .sort((a, b) => a.sortOrder - b.sortOrder)
  );

export const useSearchSuggestions = (
  query: string,
  searchType?: SearchType,
  limit?: number
) =>
  useSearchHistoryStore((state) =>
    state.getSearchSuggestions(query, searchType, limit)
  );

export const useSearchAnalytics = (dateRange?: { start: string; end: string }) =>
  useSearchHistoryStore((state) => state.getSearchAnalytics(dateRange));

export const useSearchHistoryLoading = () =>
  useSearchHistoryStore((state) => ({
    error: state.error,
    isLoading: state.isLoading,
  }));

// Compute selectors (for external use without hooks)
export const selectRecentSearchesByTypeFrom = (
  state: SearchHistoryState
): Record<SearchType, SearchHistoryItem[]> => {
  const grouped: Record<SearchType, SearchHistoryItem[]> = {
    accommodation: [],
    activity: [],
    destination: [],
    flight: [],
  };
  state.recentSearches.forEach((search) => {
    grouped[search.searchType].push(search);
  });
  return grouped;
};

export const selectFavoriteSearchesFrom = (
  state: SearchHistoryState
): ValidatedSavedSearch[] => state.savedSearches.filter((s) => s.isFavorite);

export const selectTotalSavedSearchesFrom = (state: SearchHistoryState): number =>
  state.savedSearches.length;
