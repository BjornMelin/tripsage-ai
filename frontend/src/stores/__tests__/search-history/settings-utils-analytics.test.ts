/** @vitest-environment jsdom */

import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchHistoryStore } from "@/stores/search-history-store";

describe("Search History Store - Settings, Utils, and Analytics", () => {
  beforeEach(() => {
    vi.useRealTimers();
    act(() => {
      useSearchHistoryStore.setState({
        autoCleanupDays: 30,
        autoSaveEnabled: true,
        error: null,
        isLoading: false,
        maxRecentSearches: 50,
        popularSearchTerms: [],
        quickSearches: [],
        recentSearches: [],
        savedSearches: [],
        searchCollections: [],
        searchSuggestions: [],
      });
    });
  });

  describe("Settings Management", () => {
    it("updates settings", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      expect(result.current.maxRecentSearches).toBe(50);
      expect(result.current.autoSaveEnabled).toBe(true);
      expect(result.current.autoCleanupDays).toBe(30);

      act(() => {
        result.current.updateSettings({
          autoCleanupDays: 60,
          autoSaveEnabled: false,
          maxRecentSearches: 100,
        });
      });

      expect(result.current.maxRecentSearches).toBe(100);
      expect(result.current.autoSaveEnabled).toBe(false);
      expect(result.current.autoCleanupDays).toBe(60);
    });

    it("applies cleanup when autoCleanupDays is updated", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Add an old search
      const oldDate = new Date();
      oldDate.setDate(oldDate.getDate() - 40);

      const oldSearch: SearchHistoryItem = {
        id: "old-search",
        params: {},
        searchType: "flight",
        timestamp: oldDate.toISOString(),
      };

      act(() => {
        useSearchHistoryStore.setState({ recentSearches: [oldSearch] });
      });

      expect(result.current.recentSearches).toHaveLength(1);

      // Update cleanup settings to trigger cleanup
      act(() => {
        result.current.updateSettings({ autoCleanupDays: 30 });
      });

      expect(result.current.recentSearches).toHaveLength(0);
    });
  });

  describe("Analytics", () => {
    beforeEach(() => {
      const recentSearches: SearchHistoryItem[] = [
        {
          id: "search-1",
          params: {},
          searchDuration: 1500,
          searchType: "flight",
          timestamp: new Date().toISOString(),
        },
        {
          id: "search-2",
          params: {},
          searchDuration: 2000,
          searchType: "accommodation",
          timestamp: new Date().toISOString(),
        },
        {
          id: "search-3",
          params: {},
          searchDuration: 1000,
          searchType: "flight",
          timestamp: new Date().toISOString(),
        },
      ];

      const savedSearches: ValidatedSavedSearch[] = [
        {
          createdAt: new Date().toISOString(),
          id: "saved-1",
          isFavorite: false,
          isPublic: false,
          name: "Popular Search",
          params: {},
          searchType: "flight",
          tags: [],
          updatedAt: new Date().toISOString(),
          usageCount: 10,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ recentSearches, savedSearches });
      });
    });

    it("gets search analytics", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const analytics = result.current.getSearchAnalytics();

      expect(analytics.totalSearches).toBe(3);
      expect(analytics.searchesByType.flight).toBe(2);
      expect(analytics.searchesByType.accommodation).toBe(1);
      expect(analytics.averageSearchDuration).toBe(1500); // (1500 + 2000 + 1000) / 3

      expect(analytics.mostUsedSearchTypes).toHaveLength(4);
      expect(analytics.mostUsedSearchTypes[0].type).toBe("flight");
      expect(analytics.mostUsedSearchTypes[0].count).toBe(2);

      expect(analytics.searchTrends).toHaveLength(30); // Last 30 days
      expect(analytics.popularSearchTimes).toHaveLength(24); // 24 hours
    });

    it("gets most used searches", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const mostUsed = result.current.getMostUsedSearches(5);
      expect(mostUsed).toHaveLength(1);
      expect(mostUsed[0].usageCount).toBe(10);
      expect(mostUsed[0].name).toBe("Popular Search");
    });

    it("gets search trends", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const trends = result.current.getSearchTrends("flight", 7);
      expect(trends).toHaveLength(7);

      // Today should have 2 flight searches
      const today = trends[trends.length - 1];
      expect(today.count).toBe(2);
    });
  });

  describe("Utility Actions", () => {
    it("clears all data", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Add some data first
      act(() => {
        result.current.addRecentSearch("flight", {});
        useSearchHistoryStore.setState({
          savedSearches: [
            {
              createdAt: new Date().toISOString(),
              id: "test",
              isFavorite: false,
              isPublic: false,
              name: "Test",
              params: {},
              searchType: "flight",
              tags: [],
              updatedAt: new Date().toISOString(),
              usageCount: 0,
            },
          ],
        });
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.savedSearches).toHaveLength(1);

      act(() => {
        result.current.clearAllData();
      });

      expect(result.current.recentSearches).toHaveLength(0);
      expect(result.current.savedSearches).toHaveLength(0);
      expect(result.current.searchCollections).toHaveLength(0);
      expect(result.current.quickSearches).toHaveLength(0);
    });

    it("clears errors", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      act(() => {
        useSearchHistoryStore.setState({
          error: "Test error",
        });
      });

      expect(result.current.error).toBe("Test error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it("resets to initial state", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Modify some state
      act(() => {
        result.current.addRecentSearch("flight", {});
        useSearchHistoryStore.setState({
          autoSaveEnabled: false,
          maxRecentSearches: 100,
        });
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.maxRecentSearches).toBe(100);
      expect(result.current.autoSaveEnabled).toBe(false);

      act(() => {
        result.current.reset();
      });

      expect(result.current.recentSearches).toHaveLength(0);
      expect(result.current.maxRecentSearches).toBe(50);
      expect(result.current.autoSaveEnabled).toBe(true);
    });
  });
});
