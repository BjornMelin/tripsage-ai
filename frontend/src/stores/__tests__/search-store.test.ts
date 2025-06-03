import { act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useSearchStore,
  useSearchParamsStore,
  useSearchResultsStore,
  useSearchFiltersStore,
  useSearchHistoryStore,
} from "../search-store";

// Mock all Zustand middleware
vi.mock("zustand/middleware", () => ({
  persist: vi.fn((fn) => fn),
  devtools: vi.fn((fn) => fn),
  subscribeWithSelector: vi.fn((fn) => fn),
  combine: vi.fn((fn) => fn),
}));

describe("Search Store Integration", () => {
  beforeEach(() => {
    // Reset all stores before each test
    act(() => {
      useSearchParamsStore.setState({
        currentSearchType: null,
        flightParams: {},
        accommodationParams: {},
        activityParams: {},
        destinationParams: {},
        validationErrors: {},
        isValidating: false,
      });

      useSearchResultsStore.setState({
        results: {},
        status: "idle",
        isSearching: false,
        searchProgress: 0,
        error: null,
        currentSearchId: null,
        currentSearchType: null,
        currentContext: null,
        resultsMetadata: {},
      });

      useSearchFiltersStore.setState({
        activeFilters: {},
        availableFilters: {},
        isApplyingFilters: false,
        filterPresets: {},
        activePreset: null,
        sortBy: null,
        sortOrder: "asc",
      });

      useSearchHistoryStore.setState({
        recentSearches: [],
        savedSearches: [],
        searchSuggestions: [],
        analytics: { searchCount: 0, popularSearches: {}, averageSearchTime: 0 },
        isLoading: false,
        error: null,
      });
    });
  });

  describe("Orchestrator Integration", () => {
    it("has required orchestrator methods", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(typeof result.current.initializeSearch).toBe("function");
      expect(typeof result.current.executeSearch).toBe("function");
      expect(typeof result.current.clearAll).toBe("function");
    });

    it("initializes search type correctly", () => {
      const { result: orchestratorResult } = renderHook(() => useSearchStore());
      const { result: paramsResult } = renderHook(() => useSearchParamsStore());

      act(() => {
        orchestratorResult.current.initializeSearch("flight");
      });

      expect(paramsResult.current.currentSearchType).toBe("flight");
    });

    it("clears all stores when clearAll is called", () => {
      const { result: orchestratorResult } = renderHook(() => useSearchStore());
      const { result: paramsResult } = renderHook(() => useSearchParamsStore());
      const { result: resultsResult } = renderHook(() => useSearchResultsStore());

      // Set some data first
      act(() => {
        orchestratorResult.current.initializeSearch("flight");
        resultsResult.current.setSearchProgress(50);
      });

      // Verify data is set
      expect(paramsResult.current.currentSearchType).toBe("flight");
      expect(resultsResult.current.searchProgress).toBe(50);

      // Clear all
      act(() => {
        orchestratorResult.current.clearAll();
      });

      // Verify data is cleared
      expect(paramsResult.current.currentSearchType).toBe(null);
      expect(resultsResult.current.searchProgress).toBe(0);
    });
  });

  describe("Search Params Store", () => {
    it("initializes with null search type", () => {
      const { result } = renderHook(() => useSearchParamsStore());
      expect(result.current.currentSearchType).toBe(null);
    });

    it("sets search type", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
    });

    it("updates flight parameters", () => {
      const { result } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
          adults: 2,
        });
      });

      expect(result.current.flightParams).toEqual({
        origin: "NYC",
        destination: "LAX",
        adults: 2,
      });
    });
  });

  describe("Search Results Store", () => {
    it("initializes with idle status", () => {
      const { result } = renderHook(() => useSearchResultsStore());
      expect(result.current.status).toBe("idle");
      expect(result.current.isSearching).toBe(false);
    });

    it("starts search correctly", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {
          origin: "NYC",
          destination: "LAX",
        });
      });

      expect(result.current.status).toBe("searching");
      expect(result.current.isSearching).toBe(true);
      expect(result.current.currentSearchType).toBe("flight");
      expect(searchId).toBeDefined();
      expect(typeof searchId).toBe("string");
    });

    it("sets search progress", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        result.current.setSearchProgress(75);
      });

      expect(result.current.searchProgress).toBe(75);
    });
  });

  describe("Search Filters Store", () => {
    it("initializes with empty filters", () => {
      const { result } = renderHook(() => useSearchFiltersStore());
      expect(result.current.activeFilters).toEqual({});
      expect(result.current.availableFilters).toEqual({});
    });

    it("sets available filters", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters = {
        price: { min: 100, max: 1000 },
        airline: ["Delta", "United"],
      };

      act(() => {
        result.current.setAvailableFilters(mockFilters);
      });

      expect(result.current.availableFilters).toEqual(mockFilters);
    });
  });

  describe("Search History Store", () => {
    it("initializes with empty history", () => {
      const { result } = renderHook(() => useSearchHistoryStore());
      expect(result.current.recentSearches).toEqual([]);
      expect(result.current.savedSearches).toEqual([]);
    });

    it("has save search functionality", () => {
      const { result } = renderHook(() => useSearchHistoryStore());
      expect(typeof result.current.saveSearch).toBe("function");
    });
  });
});
