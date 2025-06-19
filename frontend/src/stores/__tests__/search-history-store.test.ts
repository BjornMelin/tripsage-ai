import type { SearchType } from "@/types/search";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchHistoryStore } from "../search-history-store";
import type {
  QuickSearch,
  SearchCollection,
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "../search-history-store";

// Mock console.error to avoid noise in tests
global.console.error = vi.fn();

describe("Search History Store", () => {
  beforeEach(() => {
    act(() => {
      useSearchHistoryStore.setState({
        recentSearches: [],
        savedSearches: [],
        searchCollections: [],
        quickSearches: [],
        searchSuggestions: [],
        popularSearchTerms: [],
        maxRecentSearches: 50,
        autoSaveEnabled: true,
        autoCleanupDays: 30,
        isLoading: false,
        isSyncing: false,
        lastSyncAt: null,
        error: null,
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

    it.skip("computes totalSavedSearches correctly", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      expect(result.current.totalSavedSearches).toBe(0);

      const mockSavedSearches: ValidatedSavedSearch[] = [
        {
          id: "search-1",
          name: "Test Search 1",
          searchType: "flight",
          params: {},
          tags: [],
          isPublic: false,
          isFavorite: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
        {
          id: "search-2",
          name: "Test Search 2",
          searchType: "accommodation",
          params: {},
          tags: [],
          isPublic: false,
          isFavorite: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ savedSearches: mockSavedSearches });
      });

      expect(result.current.totalSavedSearches).toBe(2);
    });

    it.skip("computes favoriteSearches correctly", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const mockSavedSearches: ValidatedSavedSearch[] = [
        {
          id: "search-1",
          name: "Normal Search",
          searchType: "flight",
          params: {},
          tags: [],
          isPublic: false,
          isFavorite: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
        {
          id: "search-2",
          name: "Favorite Search",
          searchType: "accommodation",
          params: {},
          tags: [],
          isPublic: false,
          isFavorite: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ savedSearches: mockSavedSearches });
      });

      expect(result.current.favoriteSearches).toHaveLength(1);
      expect(result.current.favoriteSearches[0].name).toBe("Favorite Search");
    });

    it.skip("computes recentSearchesByType correctly", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const mockRecentSearches: SearchHistoryItem[] = [
        {
          id: "recent-1",
          searchType: "flight",
          params: { origin: "NYC", destination: "LAX" },
          timestamp: new Date().toISOString(),
        },
        {
          id: "recent-2",
          searchType: "accommodation",
          params: { destination: "Paris" },
          timestamp: new Date().toISOString(),
        },
        {
          id: "recent-3",
          searchType: "flight",
          params: { origin: "SFO", destination: "LHR" },
          timestamp: new Date().toISOString(),
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ recentSearches: mockRecentSearches });
      });

      const grouped = result.current.recentSearchesByType;
      expect(grouped.flight).toHaveLength(2);
      expect(grouped.accommodation).toHaveLength(1);
      expect(grouped.activity).toHaveLength(0);
      expect(grouped.destination).toHaveLength(0);
    });
  });

  describe("Recent Search Management", () => {
    it("adds a new recent search", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { origin: "NYC", destination: "LAX" };

      act(() => {
        result.current.addRecentSearch("flight", searchParams);
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.recentSearches[0].searchType).toBe("flight");
      expect(result.current.recentSearches[0].params).toEqual(searchParams);
    });

    it("updates existing search timestamp for duplicate", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { origin: "NYC", destination: "LAX" };

      act(() => {
        result.current.addRecentSearch("flight", searchParams);
      });

      const firstTimestamp = result.current.recentSearches[0].timestamp;

      // Wait a small amount to ensure different timestamp
      await new Promise((resolve) => setTimeout(resolve, 1));

      // Add same search again
      act(() => {
        result.current.addRecentSearch("flight", searchParams);
      });

      // Should still have only one search, but with updated timestamp
      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.recentSearches[0].timestamp).not.toBe(firstTimestamp);
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
            origin: `Origin${i}`,
            destination: `Dest${i}`,
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
        result.current.addRecentSearch("flight", { origin: "NYC", destination: "LAX" });
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
        result.current.addRecentSearch("flight", { origin: "NYC", destination: "LAX" });
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
        result.current.addRecentSearch("flight", { origin: "NYC", destination: "LAX" });
        result.current.addRecentSearch("accommodation", { destination: "Paris" });
        result.current.addRecentSearch("flight", { origin: "SFO", destination: "LHR" });
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
        searchType: "flight",
        params: { origin: "NYC", destination: "LAX" },
        timestamp: oldDate.toISOString(),
      };

      const recentSearch: SearchHistoryItem = {
        id: "recent-search",
        searchType: "accommodation",
        params: { destination: "Paris" },
        timestamp: recentDate,
      };

      act(() => {
        useSearchHistoryStore.setState({
          recentSearches: [oldSearch, recentSearch],
          autoCleanupDays: 30,
        });
      });

      act(() => {
        result.current.cleanupOldSearches();
      });

      expect(result.current.recentSearches).toHaveLength(1);
      expect(result.current.recentSearches[0].id).toBe("recent-search");
    });
  });

  describe("Saved Search Management", () => {
    it("saves a new search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const searchParams = { origin: "NYC", destination: "LAX" };

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

      const searchParams = { origin: "NYC", destination: "LAX" };
      const options = {
        description: "Budget flight search",
        tags: ["budget", "domestic"],
        isFavorite: true,
        isPublic: false,
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

      // Then update it
      await act(async () => {
        const success = await result.current.updateSavedSearch(searchId!, {
          name: "Updated Name",
          description: "Updated description",
          isFavorite: true,
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

      // Then delete it
      await act(async () => {
        const success = await result.current.deleteSavedSearch(searchId!);
        expect(success).toBe(true);
      });

      expect(result.current.savedSearches).toHaveLength(0);
    });

    it("duplicates a saved search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const originalParams = { origin: "NYC", destination: "LAX" };

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

      // Then duplicate it
      let duplicateId: string | null = null;
      await act(async () => {
        duplicateId = await result.current.duplicateSavedSearch(
          originalId!,
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

      // Mark as used
      act(() => {
        result.current.markSearchAsUsed(searchId!);
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

      // Toggle to favorite
      act(() => {
        result.current.toggleSearchFavorite(searchId!);
      });

      expect(result.current.savedSearches[0].isFavorite).toBe(true);

      // Toggle back
      act(() => {
        result.current.toggleSearchFavorite(searchId!);
      });

      expect(result.current.savedSearches[0].isFavorite).toBe(false);
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

      // Update collection
      await act(async () => {
        const success = await result.current.updateCollection(collectionId!, {
          name: "Updated Name",
          description: "Updated description",
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

      // Delete collection
      await act(async () => {
        const success = await result.current.deleteCollection(collectionId!);
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

      // Add search to collection
      act(() => {
        result.current.addSearchToCollection(collectionId!, searchId!);
      });

      const collection = result.current.searchCollections[0];
      expect(collection.searchIds).toContain(searchId);
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

      // Add then remove search from collection
      act(() => {
        result.current.addSearchToCollection(collectionId!, searchId!);
      });

      expect(result.current.searchCollections[0].searchIds).toContain(searchId);

      act(() => {
        result.current.removeSearchFromCollection(collectionId!, searchId!);
      });

      expect(result.current.searchCollections[0].searchIds).not.toContain(searchId);
    });
  });

  describe("Quick Searches", () => {
    it("creates a quick search", async () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const params = { origin: "NYC", destination: "LAX" };
      const options = {
        icon: "✈️",
        color: "#3B82F6",
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

      // Update quick search
      await act(async () => {
        const success = await result.current.updateQuickSearch(quickSearchId!, {
          label: "Updated Label",
          icon: "🚀",
          isVisible: false,
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

      // Delete quick search
      act(() => {
        result.current.deleteQuickSearch(quickSearchId!);
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
          quickSearchIds.push(id!);
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

  describe("Search Suggestions", () => {
    beforeEach(() => {
      // Setup some test data
      const recentSearches: SearchHistoryItem[] = [
        {
          id: "recent-1",
          searchType: "flight",
          params: { origin: "NYC", destination: "LAX" },
          timestamp: new Date().toISOString(),
        },
        {
          id: "recent-2",
          searchType: "accommodation",
          params: { destination: "Paris" },
          timestamp: new Date().toISOString(),
        },
      ];

      const savedSearches: ValidatedSavedSearch[] = [
        {
          id: "saved-1",
          name: "Budget NYC Flights",
          searchType: "flight",
          params: { origin: "NYC", destination: "BOS" },
          tags: [],
          isPublic: false,
          isFavorite: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 5,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({
          recentSearches,
          savedSearches,
        });
      });
    });

    it("updates search suggestions from recent and saved searches", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      act(() => {
        result.current.updateSearchSuggestions();
      });

      expect(result.current.searchSuggestions.length).toBeGreaterThan(0);

      const suggestions = result.current.searchSuggestions;
      const nycSuggestions = suggestions.filter((s) => s.text.includes("NYC"));
      expect(nycSuggestions.length).toBeGreaterThan(0);
    });

    it("gets filtered search suggestions", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // First update suggestions
      act(() => {
        result.current.updateSearchSuggestions();
      });

      // Get suggestions for "NYC"
      const nycSuggestions = result.current.getSearchSuggestions("NYC");
      expect(nycSuggestions.length).toBeGreaterThan(0);

      // All suggestions should contain "NYC"
      nycSuggestions.forEach((suggestion) => {
        expect(suggestion.text.toLowerCase()).toContain("nyc");
      });
    });

    it("filters suggestions by search type", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // First update suggestions
      act(() => {
        result.current.updateSearchSuggestions();
      });

      // Get flight suggestions only
      const flightSuggestions = result.current.getSearchSuggestions("", "flight");
      flightSuggestions.forEach((suggestion) => {
        expect(suggestion.searchType).toBe("flight");
      });
    });

    it("adds search terms and tracks popularity", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      expect(result.current.popularSearchTerms).toHaveLength(0);

      // Add a search term
      act(() => {
        result.current.addSearchTerm("Tokyo", "destination");
      });

      expect(result.current.popularSearchTerms).toHaveLength(1);
      expect(result.current.popularSearchTerms[0].term).toBe("Tokyo");
      expect(result.current.popularSearchTerms[0].count).toBe(1);

      // Add the same term again
      act(() => {
        result.current.addSearchTerm("Tokyo", "destination");
      });

      expect(result.current.popularSearchTerms).toHaveLength(1);
      expect(result.current.popularSearchTerms[0].count).toBe(2);
    });
  });

  describe("Search and Filtering", () => {
    beforeEach(() => {
      const savedSearches: ValidatedSavedSearch[] = [
        {
          id: "search-1",
          name: "NYC Flights",
          description: "Flights from New York",
          searchType: "flight",
          params: {},
          tags: ["business", "domestic"],
          isPublic: false,
          isFavorite: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
        {
          id: "search-2",
          name: "Paris Hotels",
          description: "Luxury hotels in Paris",
          searchType: "accommodation",
          params: {},
          tags: ["luxury", "europe"],
          isPublic: false,
          isFavorite: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
      ];

      act(() => {
        useSearchHistoryStore.setState({ savedSearches });
      });
    });

    it("searches saved searches by query", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const results = result.current.searchSavedSearches("NYC");
      expect(results).toHaveLength(1);
      expect(results[0].name).toBe("NYC Flights");
    });

    it("searches saved searches by description", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const results = result.current.searchSavedSearches("Luxury");
      expect(results).toHaveLength(1);
      expect(results[0].name).toBe("Paris Hotels");
    });

    it("filters saved searches by search type", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const flightResults = result.current.searchSavedSearches("", {
        searchType: "flight",
      });
      expect(flightResults).toHaveLength(1);
      expect(flightResults[0].searchType).toBe("flight");

      const accommodationResults = result.current.searchSavedSearches("", {
        searchType: "accommodation",
      });
      expect(accommodationResults).toHaveLength(1);
      expect(accommodationResults[0].searchType).toBe("accommodation");
    });

    it("filters saved searches by tags", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const businessResults = result.current.searchSavedSearches("", {
        tags: ["business"],
      });
      expect(businessResults).toHaveLength(1);
      expect(businessResults[0].tags).toContain("business");
    });

    it("filters saved searches by favorite status", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const favoriteResults = result.current.searchSavedSearches("", {
        isFavorite: true,
      });
      expect(favoriteResults).toHaveLength(1);
      expect(favoriteResults[0].isFavorite).toBe(true);

      const nonFavoriteResults = result.current.searchSavedSearches("", {
        isFavorite: false,
      });
      expect(nonFavoriteResults).toHaveLength(1);
      expect(nonFavoriteResults[0].isFavorite).toBe(false);
    });

    it("gets saved searches by type", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const flightSearches = result.current.getSavedSearchesByType("flight");
      expect(flightSearches).toHaveLength(1);
      expect(flightSearches[0].searchType).toBe("flight");
    });

    it("gets saved searches by tag", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      const businessSearches = result.current.getSavedSearchesByTag("business");
      expect(businessSearches).toHaveLength(1);
      expect(businessSearches[0].tags).toContain("business");
    });

    it("gets recent searches by type with limit", () => {
      const { result } = renderHook(() => useSearchHistoryStore());

      // Add some recent searches
      act(() => {
        result.current.addRecentSearch("flight", { origin: "NYC", destination: "LAX" });
        result.current.addRecentSearch("flight", { origin: "SFO", destination: "LHR" });
        result.current.addRecentSearch("accommodation", { destination: "Paris" });
      });

      const flightSearches = result.current.getRecentSearchesByType("flight", 1);
      expect(flightSearches).toHaveLength(1);
      expect(flightSearches[0].searchType).toBe("flight");
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
        savedSearches: [
          {
            id: "imported-1",
            name: "Imported Search",
            searchType: "flight",
            params: {},
            tags: [],
            isPublic: false,
            isFavorite: false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            usageCount: 0,
          },
        ],
        searchCollections: [],
        quickSearches: [],
        popularSearchTerms: [],
        exportedAt: new Date().toISOString(),
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
        const success = await result.current.syncWithServer();
        expect(success).toBe(true);
      });

      expect(result.current.isSyncing).toBe(false);
      expect(result.current.lastSyncAt).toBeTruthy();
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
          maxRecentSearches: 100,
          autoSaveEnabled: false,
          autoCleanupDays: 60,
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
        searchType: "flight",
        params: {},
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
          searchType: "flight",
          params: {},
          timestamp: new Date().toISOString(),
          searchDuration: 1500,
        },
        {
          id: "search-2",
          searchType: "accommodation",
          params: {},
          timestamp: new Date().toISOString(),
          searchDuration: 2000,
        },
        {
          id: "search-3",
          searchType: "flight",
          params: {},
          timestamp: new Date().toISOString(),
          searchDuration: 1000,
        },
      ];

      const savedSearches: ValidatedSavedSearch[] = [
        {
          id: "saved-1",
          name: "Popular Search",
          searchType: "flight",
          params: {},
          tags: [],
          isPublic: false,
          isFavorite: false,
          createdAt: new Date().toISOString(),
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
              id: "test",
              name: "Test",
              searchType: "flight",
              params: {},
              tags: [],
              isPublic: false,
              isFavorite: false,
              createdAt: new Date().toISOString(),
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
          maxRecentSearches: 100,
          autoSaveEnabled: false,
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
