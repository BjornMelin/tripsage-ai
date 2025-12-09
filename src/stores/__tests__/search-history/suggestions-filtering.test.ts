/** @vitest-environment jsdom */

import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSearchHistoryStore } from "@/stores/search-history-store";

describe("Search History Store - Suggestions and Filtering", () => {
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

  describe("Search Suggestions", () => {
    beforeEach(() => {
      // Setup some test data
      const recentSearches: SearchHistoryItem[] = [
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
      ];

      const savedSearches: ValidatedSavedSearch[] = [
        {
          createdAt: new Date().toISOString(),
          id: "saved-1",
          isFavorite: false,
          isPublic: false,
          name: "Budget NYC Flights",
          params: { destination: "BOS", origin: "NYC" },
          searchType: "flight",
          tags: [],
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
          createdAt: new Date().toISOString(),
          description: "Flights from New York",
          id: "search-1",
          isFavorite: true,
          isPublic: false,
          name: "NYC Flights",
          params: {},
          searchType: "flight",
          tags: ["business", "domestic"],
          updatedAt: new Date().toISOString(),
          usageCount: 0,
        },
        {
          createdAt: new Date().toISOString(),
          description: "Luxury hotels in Paris",
          id: "search-2",
          isFavorite: false,
          isPublic: false,
          name: "Paris Hotels",
          params: {},
          searchType: "accommodation",
          tags: ["luxury", "europe"],
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
        result.current.addRecentSearch("flight", { destination: "LAX", origin: "NYC" });
        result.current.addRecentSearch("flight", { destination: "LHR", origin: "SFO" });
        result.current.addRecentSearch("accommodation", { destination: "Paris" });
      });

      const flightSearches = result.current.getRecentSearchesByType("flight", 1);
      expect(flightSearches).toHaveLength(1);
      expect(flightSearches[0].searchType).toBe("flight");
    });
  });
});
