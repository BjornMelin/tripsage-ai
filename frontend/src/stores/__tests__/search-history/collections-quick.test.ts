/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSearchHistoryStore } from "@/stores/search-history-store";

describe("Search History Store - Collections and Quick Searches", () => {
  beforeEach(() => {
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

  describe("Search Collections", () => {
    it("creates a new collection", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      let collectionId: string | null = null;
      await act(async () => {
        collectionId = await result.current.createCollection(
          "Travel Plans",
          "Collection of my travel searches"
        );
      });

      expect(collectionId).toBeTruthy();
      expect(result.current.searchCollections).toHaveLength(1);
      expect(result.current.searchCollections[0].name).toBe("Travel Plans");
      expect(result.current.searchCollections[0].description).toBe(
        "Collection of my travel searches"
      );
    });

    it("updates a collection", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create collection first
      let collectionId: string | null = null;
      await act(async () => {
        collectionId = await result.current.createCollection("Original Name");
      });

      if (!collectionId) {
        throw new Error("Collection ID is null");
      }

      const savedCollectionId = collectionId;

      // Update collection
      await act(async () => {
        const success = await result.current.updateCollection(savedCollectionId, {
          description: "Updated description",
          name: "Updated Name",
        });
        expect(success).toBe(true);
      });

      const updatedCollection = result.current.searchCollections[0];
      expect(updatedCollection.name).toBe("Updated Name");
      expect(updatedCollection.description).toBe("Updated description");
    });

    it("deletes a collection", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create collection first
      let collectionId: string | null = null;
      await act(async () => {
        collectionId = await result.current.createCollection("Test Collection");
      });

      expect(result.current.searchCollections).toHaveLength(1);

      if (!collectionId) {
        throw new Error("Collection ID is null");
      }

      const savedCollectionId = collectionId;

      // Delete collection
      await act(async () => {
        const success = await result.current.deleteCollection(savedCollectionId);
        expect(success).toBe(true);
      });

      expect(result.current.searchCollections).toHaveLength(0);
    });

    it("adds search to collection", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create collection and saved search
      let collectionId: string | null = null;
      let searchId: string | null = null;

      await act(async () => {
        collectionId = await result.current.createCollection("Test Collection");
        searchId = await result.current.saveSearch("Test Search", "flight", {});
      });

      if (!collectionId || !searchId) {
        throw new Error("Collection ID or Search ID is null");
      }

      const savedCollectionId = collectionId;
      const savedSearchId = searchId;

      // Add search to collection
      act(() => {
        result.current.addSearchToCollection(savedCollectionId, savedSearchId);
      });

      const collection = result.current.searchCollections[0];
      expect(collection.searchIds).toContain(savedSearchId);
    });

    it("removes search from collection", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create collection and saved search
      let collectionId: string | null = null;
      let searchId: string | null = null;

      await act(async () => {
        collectionId = await result.current.createCollection("Test Collection");
        searchId = await result.current.saveSearch("Test Search", "flight", {});
      });

      if (!collectionId || !searchId) {
        throw new Error("Collection ID or Search ID is null");
      }

      const savedCollectionId = collectionId;
      const savedSearchId = searchId;

      // Add then remove search from collection
      act(() => {
        result.current.addSearchToCollection(savedCollectionId, savedSearchId);
      });

      expect(result.current.searchCollections[0].searchIds).toContain(savedSearchId);

      act(() => {
        result.current.removeSearchFromCollection(savedCollectionId, savedSearchId);
      });

      expect(result.current.searchCollections[0].searchIds).not.toContain(
        savedSearchId
      );
    });
  });

  describe("Quick Searches", () => {
    it("creates a quick search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const params = { destination: "LAX", origin: "NYC" };
      const options = {
        color: "#3B82F6",
        icon: "✈️",
        sortOrder: 1,
      };

      let quickSearchId: string | null = null;
      await act(async () => {
        quickSearchId = await result.current.createQuickSearch(
          "NYC ✈️ LAX",
          "flight",
          params,
          options
        );
      });

      expect(quickSearchId).toBeTruthy();
      expect(result.current.quickSearches).toHaveLength(1);

      const quickSearch = result.current.quickSearches[0];
      expect(quickSearch.label).toBe("NYC ✈️ LAX");
      expect(quickSearch.searchType).toBe("flight");
      expect(quickSearch.params).toEqual(params);
      expect(quickSearch.icon).toBe("✈️");
      expect(quickSearch.color).toBe("#3B82F6");
    });

    it("updates a quick search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create quick search first
      let quickSearchId: string | null = null;
      await act(async () => {
        quickSearchId = await result.current.createQuickSearch(
          "Original",
          "flight",
          {}
        );
      });

      if (!quickSearchId) {
        throw new Error("Quick search ID is null");
      }

      const savedQuickSearchId = quickSearchId;

      // Update quick search
      await act(async () => {
        const success = await result.current.updateQuickSearch(savedQuickSearchId, {
          icon: "🚀",
          isVisible: false,
          label: "Updated Label",
        });
        expect(success).toBe(true);
      });

      const updatedQuickSearch = result.current.quickSearches[0];
      expect(updatedQuickSearch.label).toBe("Updated Label");
      expect(updatedQuickSearch.icon).toBe("🚀");
      expect(updatedQuickSearch.isVisible).toBe(false);
    });

    it("deletes a quick search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create quick search first
      let quickSearchId: string | null = null;
      await act(async () => {
        quickSearchId = await result.current.createQuickSearch(
          "Test Quick Search",
          "flight",
          {}
        );
      });

      expect(result.current.quickSearches).toHaveLength(1);

      if (!quickSearchId) {
        throw new Error("Quick search ID is null");
      }

      const savedQuickSearchId = quickSearchId;

      // Delete quick search
      act(() => {
        result.current.deleteQuickSearch(savedQuickSearchId);
      });

      expect(result.current.quickSearches).toHaveLength(0);
    });

    it("reorders quick searches", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Create multiple quick searches
      const quickSearchIds: string[] = [];
      for (let i = 1; i <= 3; i++) {
        await act(async () => {
          const id = await result.current.createQuickSearch(
            `Search ${i}`,
            "flight",
            {}
          );
          if (id) {
            quickSearchIds.push(id);
          }
        });
      }

      expect(result.current.quickSearches).toHaveLength(3);

      // Reorder: reverse the order
      const reversedIds = [...quickSearchIds].reverse();
      act(() => {
        result.current.reorderQuickSearches(reversedIds);
      });

      // Check new order
      const reorderedSearches = result.current.quickSearches.sort(
        (a, b) => a.sortOrder - b.sortOrder
      );
      expect(reorderedSearches[0].label).toBe("Search 3");
      expect(reorderedSearches[1].label).toBe("Search 2");
      expect(reorderedSearches[2].label).toBe("Search 1");
    });
  });
});
