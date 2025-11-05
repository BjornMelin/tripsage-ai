import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSearchHistoryStore } from "@/stores/search-history-store";
import { resetSearchHistoryStore } from "./_shared";

describe("Search History Store - Saved Searches", () => {
  beforeEach(() => {
    resetSearchHistoryStore();
  });

  describe("Saved Search Management", () => {
    it("saves a new search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { destination: "LAX", origin: "NYC" };

      let savedId: string | null = null;
      await act(async () => {
        savedId = await result.current.saveSearch("NYC to LAX", "flight", searchParams);
      });

      expect(savedId).toBeTruthy();
      expect(result.current.savedSearches).toHaveLength(1);
      expect(result.current.savedSearches[0].name).toBe("NYC to LAX");
      expect(result.current.savedSearches[0].searchType).toBe("flight");
      expect(result.current.savedSearches[0].params).toEqual(searchParams);
    });

    it("saves search with options", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { destination: "LAX", origin: "NYC" };
      const options = {
        description: "Budget flight search",
        isFavorite: true,
        isPublic: false,
        tags: ["budget", "domestic"],
      };

      await act(async () => {
        await result.current.saveSearch("NYC to LAX", "flight", searchParams, options);
      });

      const savedSearch = result.current.savedSearches[0];
      expect(savedSearch.description).toBe("Budget flight search");
      expect(savedSearch.tags).toEqual(["budget", "domestic"]);
      expect(savedSearch.isFavorite).toBe(true);
      expect(savedSearch.isPublic).toBe(false);
    });

    it("updates a saved search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // First save a search
      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.saveSearch("Original Name", "flight", {});
      });

      if (!searchId) {
        throw new Error("Search ID is null");
      }

      const savedSearchId = searchId;

      // Then update it
      await act(async () => {
        const success = await result.current.updateSavedSearch(savedSearchId, {
          description: "Updated description",
          isFavorite: true,
          name: "Updated Name",
        });
        expect(success).toBe(true);
      });

      const updatedSearch = result.current.savedSearches[0];
      expect(updatedSearch.name).toBe("Updated Name");
      expect(updatedSearch.description).toBe("Updated description");
      expect(updatedSearch.isFavorite).toBe(true);
    });

    it("deletes a saved search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // First save a search
      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.saveSearch("Test Search", "flight", {});
      });

      expect(result.current.savedSearches).toHaveLength(1);

      if (!searchId) {
        throw new Error("Search ID is null");
      }

      const savedSearchId = searchId;

      // Then delete it
      await act(async () => {
        const success = await result.current.deleteSavedSearch(savedSearchId);
        expect(success).toBe(true);
      });

      expect(result.current.savedSearches).toHaveLength(0);
    });

    it("duplicates a saved search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const originalParams = { destination: "LAX", origin: "NYC" };

      // First save a search
      let originalId: string | null = null;
      await act(async () => {
        originalId = await result.current.saveSearch(
          "Original Search",
          "flight",
          originalParams,
          { description: "Original description", tags: ["test"] }
        );
      });

      if (!originalId) {
        throw new Error("Original ID is null");
      }

      const savedOriginalId = originalId;

      // Then duplicate it
      let duplicateId: string | null = null;
      await act(async () => {
        duplicateId = await result.current.duplicateSavedSearch(
          savedOriginalId,
          "Duplicated Search"
        );
      });

      expect(duplicateId).toBeTruthy();
      expect(result.current.savedSearches).toHaveLength(2);

      const duplicatedSearch = result.current.savedSearches.find(
        (s) => s.id === duplicateId
      );
      expect(duplicatedSearch?.name).toBe("Duplicated Search");
      expect(duplicatedSearch?.params).toEqual(originalParams);
      expect(duplicatedSearch?.description).toBe("Original description");
      expect(duplicatedSearch?.tags).toEqual(["test"]);
      expect(duplicatedSearch?.isFavorite).toBe(false); // Should reset to false
    });

    it("marks search as used", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // First save a search
      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.saveSearch("Test Search", "flight", {});
      });

      const initialUsageCount = result.current.savedSearches[0].usageCount;
      expect(initialUsageCount).toBe(0);

      if (!searchId) {
        throw new Error("Search ID is null");
      }

      const savedSearchId = searchId;

      // Mark as used
      act(() => {
        result.current.markSearchAsUsed(savedSearchId);
      });

      const updatedSearch = result.current.savedSearches[0];
      expect(updatedSearch.usageCount).toBe(1);
      expect(updatedSearch.lastUsed).toBeDefined();
    });

    it("toggles search favorite status", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // First save a search
      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.saveSearch("Test Search", "flight", {});
      });

      expect(result.current.savedSearches[0].isFavorite).toBe(false);

      if (!searchId) {
        throw new Error("Search ID is null");
      }

      const savedSearchId = searchId;

      // Toggle to favorite
      act(() => {
        result.current.toggleSearchFavorite(savedSearchId);
      });

      expect(result.current.savedSearches[0].isFavorite).toBe(true);

      // Toggle back
      act(() => {
        result.current.toggleSearchFavorite(savedSearchId);
      });

      expect(result.current.savedSearches[0].isFavorite).toBe(false);
    });
  });
});
