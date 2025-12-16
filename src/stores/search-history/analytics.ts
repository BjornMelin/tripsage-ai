/**
 * @fileoverview Analytics slice for search history store.
 */

import type { SearchType } from "@schemas/search";
import type { StateCreator } from "zustand";
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

    const totalSearches = filteredSearches.length;
    const searchesByType: Record<SearchType, number> = {
      accommodation: 0,
      activity: 0,
      destination: 0,
      flight: 0,
    };

    filteredSearches.forEach((search) => {
      searchesByType[search.searchType]++;
    });

    const averageSearchDuration =
      filteredSearches.reduce((sum, search) => {
        return sum + (search.searchDuration || 0);
      }, 0) / totalSearches || 0;

    const mostUsedSearchTypes = Object.entries(searchesByType)
      .map(([type, count]) => ({
        count,
        percentage: totalSearches > 0 ? (count / totalSearches) * 100 : 0,
        type: type as SearchType,
      }))
      .sort((a, b) => b.count - a.count);

    // Generate search trends (last 30 days)
    const searchTrends: Array<{ date: string; count: number }> = [];
    for (let i = 29; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split("T")[0];

      const count = filteredSearches.filter((search) =>
        search.timestamp.startsWith(dateStr)
      ).length;

      searchTrends.push({ count, date: dateStr });
    }

    // Popular search times (by hour)
    const popularSearchTimes: Array<{ hour: number; count: number }> = [];
    for (let hour = 0; hour < 24; hour++) {
      const count = filteredSearches.filter((search) => {
        const searchHour = new Date(search.timestamp).getHours();
        return searchHour === hour;
      }).length;

      popularSearchTimes.push({ count, hour });
    }

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
      topDestinations: [], // Would be populated from actual search data
      totalSearches,
    };
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
