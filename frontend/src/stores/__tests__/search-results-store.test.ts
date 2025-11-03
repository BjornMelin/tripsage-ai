import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { Accommodation, Flight, SearchResults } from "@/types/search";
import {
  type ErrorDetails,
  type SearchMetrics,
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
        departureDate: "2025-07-15",
        destination: "LAX",
        origin: "NYC",
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

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      const mockResults: SearchResults = {
        flights: [
          {
            airline: "Test Airlines",
            arrivalTime: "2025-07-15T11:00:00Z",
            cabinClass: "economy",
            departureTime: "2025-07-15T08:00:00Z",
            destination: "LAX",
            duration: 180,
            flightNumber: "TA123",
            id: "flight-1",
            origin: "NYC",
            price: 299,
            seatsAvailable: 10,
            stops: 0,
          },
        ],
      };

      const mockMetrics: SearchMetrics = {
        currentPage: 1,
        hasMoreResults: false,
        provider: "test-provider",
        requestId: "req-123",
        resultsPerPage: 20,
        searchDuration: 1500,
        totalResults: 1,
      };

      act(() => {
        result.current.setSearchResults(searchId!, mockResults, mockMetrics);
      });

      expect(result.current.status).toBe("success");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.results).toEqual(mockResults);
      expect(result.current.searchProgress).toBe(100);

      // Check the results object directly
      expect(result.current.results.flights).toBeDefined();
      expect(result.current.results.flights).toHaveLength(1);

      expect(result.current.hasResults).toBe(true);
      expect(result.current.isEmptyResults).toBe(false);

      // Check that metrics are set correctly (without checking searchDuration which is calculated)
      expect(result.current.metrics).toMatchObject({
        currentPage: 1,
        hasMoreResults: false,
        provider: "test-provider",
        requestId: "req-123",
        resultsPerPage: 20,
        totalResults: 1,
      });

      // Check that results are stored by search ID
      expect(result.current.resultsBySearch[searchId!]).toEqual(mockResults);
    });

    it("handles search errors", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      const errorDetails: ErrorDetails = {
        code: "NETWORK_ERROR",
        message: "Search failed due to network error",
        occurredAt: new Date().toISOString(),
        retryable: true,
      };

      act(() => {
        result.current.setSearchError(searchId!, errorDetails);
      });

      expect(result.current.status).toBe("error");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.error).toMatchObject({
        code: errorDetails.code,
        message: errorDetails.message,
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

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      const mockResults = {
        accommodations: [{ id: "a1" }] as Partial<Accommodation>[],
        flights: [{ id: "f1" }] as Partial<Flight>[],
      } as SearchResults;

      act(() => {
        result.current.setSearchResults(searchId!, mockResults);
      });

      act(() => {
        result.current.clearResults("flight");
      });

      expect(result.current.results.flights).toEqual([]);
      expect(result.current.results.accommodations).toEqual([{ id: "a1" }]);
    });

    it("clears all results", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId1: string;
      let searchId2: string;

      act(() => {
        searchId1 = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchResults(searchId1!, {
          flights: [
            {
              airline: "Test Airline",
              arrivalTime: "2023-01-01T14:00:00Z",
              cabinClass: "economy",
              departureTime: "2023-01-01T10:00:00Z",
              destination: "LAX",
              duration: 240,
              flightNumber: "TA123",
              id: "f1",
              origin: "NYC",
              price: 299,
              seatsAvailable: 100,
              stops: 0,
            },
          ],
        });
      });

      act(() => {
        searchId2 = result.current.startSearch("accommodation", {});
      });

      act(() => {
        result.current.setSearchResults(searchId2!, {
          accommodations: [
            {
              amenities: ["wifi", "parking"],
              checkIn: "2023-01-01",
              checkOut: "2023-01-03",
              id: "a1",
              images: ["test.jpg"],
              location: "Test City",
              name: "Test Hotel",
              pricePerNight: 150,
              rating: 4.5,
              totalPrice: 300,
              type: "hotel",
            },
          ],
        });
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

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      const initialResults = {
        flights: [{ id: "f1", price: 299 }] as Partial<Flight>[],
      } as SearchResults;
      const newResults = {
        flights: [{ id: "f2", price: 399 }] as Partial<Flight>[],
      } as SearchResults;

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
      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchResults(searchId!, { flights: [] }, {
          currentPage: 1,
          hasMoreResults: true,
          resultsPerPage: 20,
          totalResults: 100,
        } as SearchMetrics);
      });

      // Verify initial state
      expect(result.current.pagination.totalPages).toBe(5); // 100 / 20

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
      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchResults(searchId!, { flights: [] }, {
          currentPage: 1,
          hasMoreResults: true,
          resultsPerPage: 20,
          totalResults: 100,
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

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", { origin: "NYC" });
      });

      const mockResults: SearchResults = { flights: [] };

      act(() => {
        result.current.setSearchResults(searchId!, mockResults);
      });

      const search = result.current.getSearchById(searchId!);
      expect(search).not.toBeNull();
      expect(search?.searchId).toBe(searchId!);
      expect(search?.searchType).toBe("flight");

      const results = result.current.getResultsById(searchId!);
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

      const originalParams = { destination: "LAX", origin: "NYC" };
      let searchId: string;

      act(() => {
        searchId = result.current.startSearch("flight", originalParams);
      });

      act(() => {
        result.current.setSearchError(searchId!, {
          message: "Network error",
          occurredAt: new Date().toISOString(),
          retryable: true,
        });
      });

      let newSearchId: string | null = null;
      await act(async () => {
        newSearchId = await result.current.retryLastSearch();
      });

      expect(newSearchId).toBeTruthy();
      expect(newSearchId).not.toBe(searchId!);
      expect(result.current.currentContext?.searchParams).toEqual(originalParams);
      expect(result.current.status).toBe("searching");
    });

    it("clears error", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchError(searchId!, {
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

      // First search
      let id1: string;
      act(() => {
        id1 = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchResults(id1!, { flights: [] }, {
          currentPage: 1,
          hasMoreResults: false,
          resultsPerPage: 20,
          searchDuration: 1000,
          totalResults: 10,
        } as SearchMetrics);
      });

      // Second search
      let id2: string;
      act(() => {
        id2 = result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchResults(id2!, { flights: [] }, {
          currentPage: 1,
          hasMoreResults: false,
          resultsPerPage: 20,
          searchDuration: 2000,
          totalResults: 20,
        } as SearchMetrics);
      });

      const avgDuration = result.current.getAverageSearchDuration("flight");
      // Since searchDuration gets recalculated based on actual time, we can't expect exact values
      expect(avgDuration).toBeGreaterThan(0);
    });

    it("calculates search success rate", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Successful search
      let id1: string;
      act(() => {
        id1 = result.current.startSearch("flight", {});
      });
      act(() => {
        result.current.setSearchResults(id1!, { flights: [] });
      });

      // Failed search
      let id2: string;
      act(() => {
        id2 = result.current.startSearch("flight", {});
      });
      act(() => {
        result.current.setSearchError(id2!, {
          message: "Error",
          occurredAt: new Date().toISOString(),
          retryable: false,
        });
      });

      // Another successful search
      let id3: string;
      act(() => {
        id3 = result.current.startSearch("flight", {});
      });
      act(() => {
        result.current.setSearchResults(id3!, { flights: [] });
      });

      const successRate = result.current.getSearchSuccessRate("flight");
      expect(successRate).toBeCloseTo(66.67, 1); // 2 out of 3 successful
    });

    it("provides performance insights", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // First search - success
      let id1: string;
      act(() => {
        id1 = result.current.startSearch("flight", {});
      });
      act(() => {
        result.current.setSearchResults(id1!, { flights: [] }, {
          currentPage: 1,
          hasMoreResults: false,
          resultsPerPage: 20,
          searchDuration: 1500,
          totalResults: 10,
        } as SearchMetrics);
      });

      // Second search - error
      let id2: string;
      act(() => {
        id2 = result.current.startSearch("accommodation", {});
      });
      act(() => {
        result.current.setSearchError(id2!, {
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
