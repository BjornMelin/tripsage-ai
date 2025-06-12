import type { SearchResults, SearchType } from "@/types/search";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  type ErrorDetails,
  type SearchContext,
  type SearchMetrics,
  type SearchStatus,
  useSearchResultsStore,
} from "../search-results-store";

describe("Search Results Store", () => {
  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useSearchResultsStore.getState().reset();
    });
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      expect(result.current.status).toBe("idle");
      expect(result.current.currentSearchId).toBeNull();
      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.results).toEqual({});
      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchProgress).toBe(0);
      expect(result.current.error).toBeNull();
      expect(result.current.hasResults).toBe(false);
      expect(result.current.isEmptyResults).toBe(false);
      expect(result.current.canRetry).toBe(false);
      expect(result.current.searchDuration).toBeNull();
    });
  });

  describe("Search Lifecycle", () => {
    it("starts a search correctly", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchParams = {
        origin: "NYC",
        destination: "LAX",
        departureDate: "2025-07-15",
      };

      let searchId = "";
      act(() => {
        searchId = result.current.startSearch("flight", searchParams);
      });

      expect(searchId).toBeTruthy();
      expect(result.current.status).toBe("searching");
      expect(result.current.isSearching).toBe(true);
      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.currentSearchId).toBe(searchId);
      expect(result.current.searchProgress).toBe(0);
      expect(result.current.error).toBeNull();
      expect(result.current.results).toEqual({}); // Results cleared on new search

      const context = result.current.currentContext;
      expect(context).not.toBeNull();
      expect(context?.searchType).toBe("flight");
      expect(context?.searchParams).toEqual(searchParams);
      expect(context?.searchId).toBe(searchId);
      expect(context?.startedAt).toBeDefined();
    });

    it("generates unique search IDs", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId1 = "";
      let searchId2 = "";

      act(() => {
        searchId1 = result.current.startSearch("flight", {});
      });

      act(() => {
        searchId2 = result.current.startSearch("accommodation", {});
      });

      expect(searchId1).not.toBe(searchId2);
      expect(searchId1).toBeTruthy();
      expect(searchId2).toBeTruthy();
    });

    it("updates search progress", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId = "";
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.updateSearchProgress(searchId, 25);
      });

      expect(result.current.searchProgress).toBe(25);

      act(() => {
        result.current.updateSearchProgress(searchId, 75);
      });

      expect(result.current.searchProgress).toBe(75);
    });

    it("clamps search progress between 0 and 100", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId = "";
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.updateSearchProgress(searchId, -10);
      });

      expect(result.current.searchProgress).toBe(0);

      act(() => {
        result.current.updateSearchProgress(searchId, 150);
      });

      expect(result.current.searchProgress).toBe(100);
    });

    it("sets search results successfully", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const mockResults: SearchResults = {
        flights: [
          {
            id: "flight-1",
            airline: "Test Airlines",
            flightNumber: "TA123",
            price: 299,
            departureTime: "2025-07-15T08:00:00Z",
            arrivalTime: "2025-07-15T11:00:00Z",
            origin: "NYC",
            destination: "LAX",
            duration: 180,
            stops: 0,
            cabinClass: "economy",
            seatsAvailable: 10,
          },
        ],
      };

      const mockMetrics: SearchMetrics = {
        totalResults: 1,
        searchDuration: 1500,
        provider: "test-provider",
        requestId: "req-123",
        resultsPerPage: 20,
        currentPage: 1,
        hasMoreResults: false,
      };

      act(() => {
        result.current.setSearchResults(searchId, mockResults, mockMetrics);
      });

      expect(result.current.status).toBe("success");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.results).toEqual(mockResults);
      expect(result.current.searchProgress).toBe(100);
      expect(result.current.hasResults).toBe(true);
      expect(result.current.isEmptyResults).toBe(false);
      expect(result.current.metrics).toEqual(mockMetrics);

      // Check that results are stored by search ID
      expect(result.current.resultsBySearch[searchId]).toEqual(mockResults);
    });

    it("handles search errors", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const errorDetails: ErrorDetails = {
        message: "Search failed due to network error",
        code: "NETWORK_ERROR",
        retryable: true,
        occurredAt: new Date().toISOString(),
      };

      act(() => {
        result.current.setSearchError(searchId, errorDetails);
      });

      expect(result.current.status).toBe("error");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.error).toMatchObject({
        message: errorDetails.message,
        code: errorDetails.code,
        retryable: true,
      });
      expect(result.current.canRetry).toBe(true);
    });

    it("cancels search", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});

      act(() => {
        result.current.cancelSearch(searchId);
      });

      expect(result.current.status).toBe("cancelled");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchProgress).toBe(0);
    });

    it("completes search", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});

      act(() => {
        result.current.completeSearch(searchId);
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.currentContext?.completedAt).toBeDefined();
    });
  });

  describe("Results Management", () => {
    it("clears results by search type", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const mockResults: SearchResults = {
        flights: [{ id: "f1" }] as any,
        accommodations: [{ id: "a1" }] as any,
      };

      act(() => {
        result.current.setSearchResults(searchId, mockResults);
      });

      act(() => {
        result.current.clearResults("flight");
      });

      expect(result.current.results.flights).toEqual([]);
      expect(result.current.results.accommodations).toEqual([{ id: "a1" }]);
    });

    it("clears all results", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId1 = result.current.startSearch("flight", {});
      const searchId2 = result.current.startSearch("accommodation", {});

      act(() => {
        result.current.setSearchResults(searchId1, { flights: [] });
        result.current.setSearchResults(searchId2, { accommodations: [] });
      });

      expect(Object.keys(result.current.resultsBySearch)).toHaveLength(2);

      act(() => {
        result.current.clearAllResults();
      });

      expect(result.current.results).toEqual({});
      expect(result.current.resultsBySearch).toEqual({});
      expect(result.current.status).toBe("idle");
      expect(result.current.currentSearchId).toBeNull();
      expect(result.current.currentSearchType).toBeNull();
    });

    it("appends results to existing results", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const initialResults: SearchResults = {
        flights: [{ id: "f1", price: { amount: 299, currency: "USD" } }] as any,
      };
      const newResults: SearchResults = {
        flights: [{ id: "f2", price: { amount: 399, currency: "USD" } }] as any,
      };

      act(() => {
        result.current.setSearchResults(searchId, initialResults);
      });

      act(() => {
        result.current.appendResults(searchId, newResults);
      });

      expect(result.current.results.flights).toHaveLength(2);
      expect(result.current.results.flights?.[0].id).toBe("f1");
      expect(result.current.results.flights?.[1].id).toBe("f2");
    });
  });

  describe("Pagination", () => {
    it("sets page correctly", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Set up pagination with multiple pages
      act(() => {
        const searchId = result.current.startSearch("flight", {});
        result.current.setSearchResults(searchId, { flights: [] }, {
          totalResults: 100,
          resultsPerPage: 20,
          currentPage: 1,
          hasMoreResults: true,
        } as SearchMetrics);
      });

      act(() => {
        result.current.setPage(3);
      });

      expect(result.current.pagination.currentPage).toBe(3);
      expect(result.current.pagination.hasNextPage).toBe(true);
      expect(result.current.pagination.hasPreviousPage).toBe(true);
    });

    it("navigates pages correctly", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Set up pagination
      act(() => {
        const searchId = result.current.startSearch("flight", {});
        result.current.setSearchResults(searchId, { flights: [] }, {
          totalResults: 100,
          resultsPerPage: 20,
          currentPage: 1,
          hasMoreResults: true,
        } as SearchMetrics);
      });

      act(() => {
        result.current.nextPage();
      });

      expect(result.current.pagination.currentPage).toBe(2);

      act(() => {
        result.current.previousPage();
      });

      expect(result.current.pagination.currentPage).toBe(1);
    });
  });

  describe("Search History", () => {
    it("retrieves search by ID", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", { origin: "NYC" });
      const mockResults: SearchResults = { flights: [] };

      act(() => {
        result.current.setSearchResults(searchId, mockResults);
      });

      const search = result.current.getSearchById(searchId);
      expect(search).not.toBeNull();
      expect(search?.searchId).toBe(searchId);
      expect(search?.searchType).toBe("flight");

      const results = result.current.getResultsById(searchId);
      expect(results).toEqual(mockResults);
    });

    it("gets recent searches filtered by type", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        const id1 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id1, { flights: [] });

        const id2 = result.current.startSearch("accommodation", {});
        result.current.setSearchResults(id2, { accommodations: [] });

        const id3 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id3, { flights: [] });
      });

      const flightSearches = result.current.getRecentSearches("flight", 10);
      expect(flightSearches).toHaveLength(2);
      expect(flightSearches.every((s) => s.searchType === "flight")).toBe(true);

      const allSearches = result.current.getRecentSearches();
      expect(allSearches.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Error Management", () => {
    it("retries last search", async () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const originalParams = { origin: "NYC", destination: "LAX" };
      const searchId = result.current.startSearch("flight", originalParams);

      act(() => {
        result.current.setSearchError(searchId, {
          message: "Network error",
          retryable: true,
          occurredAt: new Date().toISOString(),
        });
      });

      let newSearchId: string | null = null;
      await act(async () => {
        newSearchId = await result.current.retryLastSearch();
      });

      expect(newSearchId).toBeTruthy();
      expect(newSearchId).not.toBe(searchId);
      expect(result.current.currentContext?.searchParams).toEqual(originalParams);
      expect(result.current.status).toBe("searching");
    });

    it("clears error", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      act(() => {
        result.current.setSearchError(searchId, {
          message: "Error",
          occurredAt: new Date().toISOString(),
          retryable: true,
        });
      });

      expect(result.current.error).not.toBeNull();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("Performance Monitoring", () => {
    it("calculates average search duration", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Simulate multiple searches with different durations
      act(() => {
        const id1 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id1, { flights: [] }, {
          searchDuration: 1000,
          totalResults: 10,
        } as SearchMetrics);

        const id2 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id2, { flights: [] }, {
          searchDuration: 2000,
          totalResults: 20,
        } as SearchMetrics);
      });

      const avgDuration = result.current.getAverageSearchDuration("flight");
      expect(avgDuration).toBe(1500); // (1000 + 2000) / 2
    });

    it("calculates search success rate", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        // Successful search
        const id1 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id1, { flights: [] });

        // Failed search
        const id2 = result.current.startSearch("flight", {});
        result.current.setSearchError(id2, {
          message: "Error",
          occurredAt: new Date().toISOString(),
          retryable: false,
        });

        // Another successful search
        const id3 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id3, { flights: [] });
      });

      const successRate = result.current.getSearchSuccessRate("flight");
      expect(successRate).toBeCloseTo(66.67, 1); // 2 out of 3 successful
    });

    it("provides performance insights", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        const id1 = result.current.startSearch("flight", {});
        result.current.setSearchResults(id1, { flights: [] }, {
          searchDuration: 1500,
          totalResults: 10,
        } as SearchMetrics);

        const id2 = result.current.startSearch("accommodation", {});
        result.current.setSearchError(id2, {
          message: "Error",
          occurredAt: new Date().toISOString(),
          retryable: true,
        });
      });

      const insights = result.current.getPerformanceInsights();
      expect(insights.totalSearches).toBe(2);
      expect(insights.averageDuration).toBeGreaterThan(0);
      expect(insights.successRate).toBe(50); // 1 success, 1 failure
      expect(insights.errorRate).toBe(50);
    });
  });

  describe("Utility Actions", () => {
    it("resets entire store", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Populate store with data
      act(() => {
        const searchId = result.current.startSearch("flight", {});
        result.current.setSearchResults(searchId, { flights: [] });
        result.current.setSearchError(searchId, {
          message: "Test error",
          occurredAt: new Date().toISOString(),
          retryable: true,
        });
      });

      expect(result.current.searchHistory.length).toBeGreaterThan(0);

      act(() => {
        result.current.reset();
      });

      expect(result.current.status).toBe("idle");
      expect(result.current.currentSearchId).toBeNull();
      expect(result.current.results).toEqual({});
      expect(result.current.searchHistory).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it("soft resets keeping history", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Populate store
      act(() => {
        const searchId = result.current.startSearch("flight", {});
        result.current.setSearchResults(searchId, { flights: [] });
      });

      const historyLength = result.current.searchHistory.length;

      act(() => {
        result.current.softReset();
      });

      expect(result.current.status).toBe("idle");
      expect(result.current.currentSearchId).toBeNull();
      expect(result.current.results).toEqual({});
      expect(result.current.searchHistory.length).toBe(historyLength); // History preserved
    });
  });
});
