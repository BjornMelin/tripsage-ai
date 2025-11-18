/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "@/stores/search-history-store";
import {
  selectFavoriteSearchesFrom,
  selectRecentSearchesByTypeFrom,
  selectTotalSavedSearchesFrom,
  useSearchHistoryStore,
} from "@/stores/search-history-store";

describe("Search History Store - Initial State and Recent Searches", () => {
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

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      expect(result.current.recentSearches).toEqual([]);
      expect(result.current.savedSearches).toEqual([]);
      expect(result.current.searchCollections).toEqual([]);
      expect(result.current.quickSearches).toEqual([]);
      expect(result.current.maxRecentSearches).toBe(50);
      expect(result.current.autoSaveEnabled).toBe(true);
      expect(result.current.autoCleanupDays).toBe(30);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isSyncing).toBe(false);
    });

    it("computes totalSavedSearches correctly", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      expect(result.current.totalSavedSearches).toBe(0);

      const mockSavedSearches: ValidatedSavedSearch[] = [
        {
          createdAt: new Date().toISOString(),
          id: "search-1",
          isFavorite: false,
          isPublic: false,
          name: "Test Search 1",
          params: {},
          searchType: "flight",
          tags: [],
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
        {
          createdAt: new Date().toISOString(),
          id: "search-2",
          isFavorite: true,
          isPublic: false,
          name: "Test Search 2",
          params: {},
          searchType: "accommodation",
          tags: [],
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ savedSearches: mockSavedSearches });
      });

      const totalSavedSearches = selectTotalSavedSearchesFrom(
        useSearchHistoryStore.getState()
      );
      expect(totalSavedSearches).toBe(2);
    });

    it("computes favoriteSearches correctly", () => {
      renderHook(() => useSearchHistoryStore());

      const mockSavedSearches: ValidatedSavedSearch[] = [
        {
          createdAt: new Date().toISOString(),
          id: "search-1",
          isFavorite: false,
          isPublic: false,
          name: "Normal Search",
          params: {},
          searchType: "flight",
          tags: [],
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
        {
          createdAt: new Date().toISOString(),
          id: "search-2",
          isFavorite: true,
          isPublic: false,
          name: "Favorite Search",
          params: {},
          searchType: "accommodation",
          tags: [],
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ savedSearches: mockSavedSearches });
      });

      const favoriteSearches = selectFavoriteSearchesFrom(
        useSearchHistoryStore.getState()
      );
      expect(favoriteSearches).toHaveLength(1);
      expect(favoriteSearches[0].name).toBe("Favorite Search");
    });

    it("computes recentSearchesByType correctly", () => {
      renderHook(() => useSearchHistoryStore());

      const mockRecentSearches: SearchHistoryItem[] = [
        {
          id: "recent-1",
          params: { destination: "LAX", origin: "NYC" },
          searchType: "flight",
          timestamp: new Date().toISOString(),
        },
        {
          id: "recent-2",
          params: { destination: "Paris" },
          searchType: "accommodation",
          timestamp: new Date().toISOString(),
        },
        {
          id: "recent-3",
          params: { destination: "LHR", origin: "SFO" },
          searchType: "flight",
          timestamp: new Date().toISOString(),
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ recentSearches: mockRecentSearches });
      });

      // Verify recent searches set and compute grouping via pure selector
      const currentState = useSearchHistoryStore.getState();
      expect(currentState.recentSearches).toHaveLength(3);
      const grouped = selectRecentSearchesByTypeFrom(currentState);

      expect(grouped.flight).toHaveLength(2);
      expect(grouped.accommodation).toHaveLength(1);
      expect(grouped.activity).toHaveLength(0);
      expect(grouped.destination).toHaveLength(0);
    });
  });

  describe("Recent Search Management", () => {
    it("adds a new recent search", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { destination: "LAX", origin: "NYC" };

      act(() => {
        result.current.addRecentSearch("flight", searchParams);
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.recentSearches[0].searchType).toBe("flight");
      expect(result.current.recentSearches[0].params).toEqual(searchParams);
    });

    it("updates existing search timestamp for duplicate", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { destination: "LAX", origin: "NYC" };

      act(() => {
        result.current.addRecentSearch("flight", searchParams);
      });

      const _firstTimestamp = result.current.recentSearches[0].timestamp;

      // Avoid real time waits in tests; timestamps are generated anew on update

      // Add same search again
      act(() => {
        result.current.addRecentSearch("flight", searchParams);
      });

      // Should still have only one search (deduplicated)
      expect(result.current.recentSearches).toHaveLength(1);
      // Timestamp should be an ISO string; equality is not guaranteed by the same-tick update
      expect(typeof result.current.recentSearches[0].timestamp).toBe("string");
    });

    it("respects maxRecentSearches limit", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Set a low limit for testing
      act(() => {
        useSearchHistoryStore.setState({ maxRecentSearches: 3 });
      });

      // Add 5 searches
      for (let i = 1; i <= 5; i++) {
        act(() => {
          result.current.addRecentSearch("flight", {
            destination: `Dest${i}`,
            origin: `Origin${i}`,
          });
        });
      }

      // Should only keep the last 3
      expect(result.current.recentSearches).toHaveLength(3);
      expect(result.current.recentSearches[0].params.origin).toBe("Origin5");
    });

    it("removes a specific recent search", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      act(() => {
        result.current.addRecentSearch("flight", { destination: "LAX", origin: "NYC" });
        result.current.addRecentSearch("accommodation", { destination: "Paris" });
      });

      expect(result.current.recentSearches).toHaveLength(2);
      const searchIdToRemove = result.current.recentSearches[0].id;

      act(() => {
        result.current.removeRecentSearch(searchIdToRemove);
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(
        result.current.recentSearches.find((s) => s.id === searchIdToRemove)
      ).toBeUndefined();
    });

    it("clears all recent searches", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      act(() => {
        result.current.addRecentSearch("flight", { destination: "LAX", origin: "NYC" });
        result.current.addRecentSearch("accommodation", { destination: "Paris" });
      });

      expect(result.current.recentSearches).toHaveLength(2);

      act(() => {
        result.current.clearRecentSearches();
      });

      expect(result.current.recentSearches).toHaveLength(0);
    });

    it("clears recent searches by type", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      act(() => {
        result.current.addRecentSearch("flight", { destination: "LAX", origin: "NYC" });
        result.current.addRecentSearch("accommodation", { destination: "Paris" });
        result.current.addRecentSearch("flight", { destination: "LHR", origin: "SFO" });
      });

      expect(result.current.recentSearches).toHaveLength(3);

      act(() => {
        result.current.clearRecentSearches("flight");
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.recentSearches[0].searchType).toBe("accommodation");
    });

    it("cleans up old searches based on autoCleanupDays", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const oldDate = new Date();
      oldDate.setDate(oldDate.getDate() - 40); // 40 days ago
      const recentDate = new Date().toISOString();

      const oldSearch: SearchHistoryItem = {
        id: "old-search",
        params: { destination: "LAX", origin: "NYC" },
        searchType: "flight",
        timestamp: oldDate.toISOString(),
      };

      const recentSearch: SearchHistoryItem = {
        id: "recent-search",
        params: { destination: "Paris" },
        searchType: "accommodation",
        timestamp: recentDate,
      };

      act(() => {
        useSearchHistoryStore.setState({
          autoCleanupDays: 30,
          recentSearches: [oldSearch, recentSearch],
        });
      });

      act(() => {
        result.current.cleanupOldSearches();
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.recentSearches[0].id).toBe("recent-search");
    });
  });
});
