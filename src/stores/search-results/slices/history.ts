/**
 * @fileoverview History and performance slice for the search results store.
 */

import type { SearchType } from "@schemas/search";
import type { StateCreator } from "zustand";
import type { SearchResultsState } from "../types";

type SearchResultsHistorySlice = Pick<
  SearchResultsState,
  | "clearSearchHistory"
  | "getAverageSearchDuration"
  | "getPerformanceInsights"
  | "getRecentSearches"
  | "getResultsById"
  | "getSearchById"
  | "getSearchSuccessRate"
  | "removeSearchFromHistory"
>;

export const createSearchResultsHistorySlice: StateCreator<
  SearchResultsState,
  [],
  [],
  SearchResultsHistorySlice
> = (set, get) => ({
  clearSearchHistory: () => {
    set({
      errorHistory: [],
      performanceHistory: [],
      resultsBySearch: {},
      searchHistory: [],
    });
  },

  getAverageSearchDuration: (searchType?: SearchType) => {
    const { performanceHistory, searchHistory } = get();
    let relevantMetrics = performanceHistory;

    if (searchType) {
      const searchTypeMap = new Map(
        searchHistory.map((search) => [search.searchId, search.searchType])
      );
      relevantMetrics = performanceHistory.filter((perf) => {
        return searchTypeMap.get(perf.searchId) === searchType;
      });
    }

    if (relevantMetrics.length === 0) return 0;

    const totalDuration = relevantMetrics.reduce((sum, metric) => {
      return sum + (metric.searchDuration || 0);
    }, 0);

    return totalDuration / relevantMetrics.length;
  },

  getPerformanceInsights: () => {
    const { searchHistory, errorHistory } = get();
    const totalSearches = searchHistory.length;
    const totalErrors = errorHistory.length;

    return {
      averageDuration: get().getAverageSearchDuration(),
      errorRate: totalSearches > 0 ? (totalErrors / totalSearches) * 100 : 0,
      successRate: get().getSearchSuccessRate(),
      totalSearches,
    };
  },

  getRecentSearches: (searchType?: SearchType, limit = 10) => {
    const { searchHistory } = get();
    let filtered = searchHistory;

    if (searchType) {
      filtered = searchHistory.filter((search) => search.searchType === searchType);
    }

    return filtered
      .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
      .slice(0, limit);
  },

  getResultsById: (searchId: string) => {
    const { resultsBySearch } = get();
    return resultsBySearch[searchId] || null;
  },

  getSearchById: (searchId: string) => {
    const { searchHistory } = get();
    return searchHistory.find((search) => search.searchId === searchId) || null;
  },

  getSearchSuccessRate: (searchType?: SearchType) => {
    const { searchHistory, errorHistory } = get();
    let relevantSearches = searchHistory;

    if (searchType) {
      relevantSearches = searchHistory.filter(
        (search) => search.searchType === searchType
      );
    }

    if (relevantSearches.length === 0) return 0;

    const erroredSearchIds = new Set(errorHistory.map((e) => e.searchId));
    const successfulSearches = relevantSearches.filter(
      (search) => search.completedAt && !erroredSearchIds.has(search.searchId)
    ).length;

    return (successfulSearches / relevantSearches.length) * 100;
  },

  removeSearchFromHistory: (searchId: string) => {
    set((state) => {
      const { [searchId]: _omit, ...remainingResults } = state.resultsBySearch;
      return {
        errorHistory: state.errorHistory.filter((error) => error.searchId !== searchId),
        performanceHistory: state.performanceHistory.filter(
          (perf) => perf.searchId !== searchId
        ),
        resultsBySearch: remainingResults,
        searchHistory: state.searchHistory.filter(
          (search) => search.searchId !== searchId
        ),
      };
    });
  },
});
