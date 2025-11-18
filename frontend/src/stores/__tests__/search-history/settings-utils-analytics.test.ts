/** @vitest-environment jsdom */

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "@/stores/search-history-store";
import { useSearchHistoryStore } from "@/stores/search-history-store";

describe("Search History Store - Settings, Utils, and Analytics", () => {
  beforeEach(() => {
    act(() => {
      useSearchHistoryStore.setState({
        autoCleanupDays: 30,
        autoSaveEnabled: true,
        error: null,
        isLoading: false,
        isSyncing: false,
        lastSyncAt: null,
        maxRecentSearches: 50,
        popularSearchTerms: [],
        quickSearches: [],
        recentSearches: [],
        savedSearches: [],
        searchCollections: [],
        searchSuggestions: [],
        syncError: null,
      });
    });
  });

  describe("Data Management", () => {
    it("exports search history", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Add some data first
      await act(async () => {
        await result.current.saveSearch("Test Search", "flight", {});
        await result.current.createCollection("Test Collection");
        await result.current.createQuickSearch("Test Quick", "flight", {});
      });

      const exportedData = result.current.exportSearchHistory();
      expect(exportedData).toBeTruthy();

      const parsed = JSON.parse(exportedData);
      expect(parsed.savedSearches).toHaveLength(1);
      expect(parsed.searchCollections).toHaveLength(1);
      expect(parsed.quickSearches).toHaveLength(1);
      expect(parsed.exportedAt).toBeDefined();
      expect(parsed.version).toBe("1.0");
    });

    it("imports search history", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const importData = {
        exportedAt: new Date().toISOString(),
        popularSearchTerms: [],
        quickSearches: [],
        savedSearches: [
          {
            createdAt: new Date().toISOString(),
            id: "imported-1",
            isFavorite: false,
            isPublic: false,
            name: "Imported Search",
            params: {},
            searchType: "flight",
            tags: [],
            updatedAt: new Date().toISOString(),
            usageCount: 0,
          },
        ],
        searchCollections: [],
        version: "1.0",
      };

      await act(async () => {
        const success = await result.current.importSearchHistory(
          JSON.stringify(importData)
        );
        expect(success).toBe(true);
      });

      expect(result.current.savedSearches).toHaveLength(1);
      expect(result.current.savedSearches[0].name).toBe("Imported Search");
    });

    it("syncs with server", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      expect(result.current.isSyncing).toBe(false);
      expect(result.current.lastSyncAt).toBeNull();

      await act(async () => {
        const promise = result.current.syncWithServer();
        await waitFor(() => {
          expect(result.current.isSyncing).toBe(false);
        });
        const success = await promise;
        expect(success).toBe(true);
      });

      await waitFor(() => {
        expect(result.current.lastSyncAt).toBeTruthy();
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
          syncError: "Sync error",
        });
      });

      expect(result.current.error).toBe("Test error");
      expect(result.current.syncError).toBe("Sync error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
      expect(result.current.syncError).toBeNull();
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
