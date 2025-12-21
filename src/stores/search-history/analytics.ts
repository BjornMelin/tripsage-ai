/**
 * @fileoverview Analytics slice for search history store.
 */

import type { StateCreator } from "zustand";
import { computeSearchAnalytics } from "./analytics-utils";
import type { AnalyticsSlice, SearchHistoryState } from "./types";

export const createAnalyticsSlice: StateCreator<
  SearchHistoryState,
  [],
  [],
  AnalyticsSlice
> = (_set, get) => ({
  getMostUsedSearches: (limit = 10) => {
    return get()
      .savedSearches.filter((search) => search.usageCount > 0)
      .sort((a, b) => b.usageCount - a.usageCount)
      .slice(0, limit);
  },
  getSearchAnalytics: (dateRange) => {
    const { recentSearches, savedSearches } = get();
    let filteredSearches = recentSearches;

    if (dateRange) {
      const startDate = new Date(dateRange.start);
      const endDate = new Date(dateRange.end);
      filteredSearches = recentSearches.filter((search) => {
        const searchDate = new Date(search.timestamp);
        return searchDate >= startDate && searchDate <= endDate;
      });
    }

    return computeSearchAnalytics(filteredSearches, savedSearches);
  },

  getSearchTrends: (searchType, days = 30) => {
    const { recentSearches } = get();
    const trends: Array<{ date: string; count: number }> = [];

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split("T")[0];

      const count = recentSearches.filter((search) => {
        const matchesDate = search.timestamp.startsWith(dateStr);
        const matchesType = !searchType || search.searchType === searchType;
        return matchesDate && matchesType;
      }).length;

      trends.push({ count, date: dateStr });
    }

    return trends;
  },
});
