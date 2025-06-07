import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchResultsStore } from "../search-results-store";

describe("Search Results Store", () => {
  beforeEach(() => {
    act(() => {
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
    });
  });

  describe("Initial State", () => {
    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      expect(result.current.results).toEqual({});
      expect(result.current.status).toBe("idle");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchProgress).toBe(0);
      expect(result.current.error).toBeNull();
      expect(result.current.currentSearchId).toBeNull();
      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.currentContext).toBeNull();
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

      let searchId: string;
      act(() => {
        searchId = result.current.startSearch("flight", searchParams);
      });

      expect(result.current.status).toBe("searching");
      expect(result.current.isSearching).toBe(true);
      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.currentSearchId).toBe(searchId);
      expect(result.current.searchProgress).toBe(0);
      expect(result.current.error).toBeNull();

      const context = result.current.currentContext;
      expect(context).not.toBeNull();
      expect(context?.searchType).toBe("flight");
      expect(context?.searchParams).toEqual(searchParams);
      expect(context?.searchId).toBe(searchId);
      expect(context?.startedAt).toBeDefined();
    });

    it("generates unique search IDs", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      let searchId1: string;
      let searchId2: string;

      act(() => {
        searchId1 = result.current.startSearch("flight", {});
      });

      act(() => {
        searchId2 = result.current.startSearch("accommodation", {});
      });

      expect(searchId1).not.toBe(searchId2);
    });

    it("updates search progress", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        result.current.startSearch("flight", {});
      });

      act(() => {
        result.current.setSearchProgress(25);
      });

      expect(result.current.searchProgress).toBe(25);

      act(() => {
        result.current.setSearchProgress(75);
      });

      expect(result.current.searchProgress).toBe(75);
    });

    it("clamps search progress between 0 and 100", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        result.current.setSearchProgress(-10);
      });

      expect(result.current.searchProgress).toBe(0);

      act(() => {
        result.current.setSearchProgress(150);
      });

      expect(result.current.searchProgress).toBe(100);
    });

    it("completes search successfully", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const mockResults = {
        flights: [
          {
            id: "flight-1",
            airline: "Test Airlines",
            price: 299,
            departure: "08:00",
            arrival: "11:00",
          },
        ],
      };

      act(() => {
        result.current.completeSearch(searchId, mockResults);
      });

      expect(result.current.status).toBe("completed");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.results[searchId]).toEqual(mockResults);
      expect(result.current.searchProgress).toBe(100);

      const context = result.current.currentContext;
      expect(context?.completedAt).toBeDefined();
    });

    it("fails search with error", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const errorMessage = "Search failed due to network error";

      act(() => {
        result.current.failSearch(searchId, errorMessage);
      });

      expect(result.current.status).toBe("failed");
      expect(result.current.isSearching).toBe(false);
      expect(result.current.error).toBe(errorMessage);

      const context = result.current.currentContext;
      expect(context?.failedAt).toBeDefined();
      expect(context?.error).toBe(errorMessage);
    });

    it("cancels search", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});

      act(() => {
        result.current.cancelSearch(searchId);
      });

      expect(result.current.status).toBe("cancelled");
      expect(result.current.isSearching).toBe(false);

      const context = result.current.currentContext;
      expect(context?.cancelledAt).toBeDefined();
    });
  });

  describe("Results Management", () => {
    it("stores results by search ID", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId1 = result.current.startSearch("flight", {});
      const searchId2 = result.current.startSearch("accommodation", {});

      const flightResults = { flights: [{ id: "f1", price: 299 }] };
      const hotelResults = { hotels: [{ id: "h1", price: 150 }] };

      act(() => {
        result.current.completeSearch(searchId1, flightResults);
        result.current.completeSearch(searchId2, hotelResults);
      });

      expect(result.current.results[searchId1]).toEqual(flightResults);
      expect(result.current.results[searchId2]).toEqual(hotelResults);
    });

    it("gets results by search ID", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const mockResults = { flights: [{ id: "f1", price: 299 }] };

      act(() => {
        result.current.completeSearch(searchId, mockResults);
      });

      const retrievedResults = result.current.getResults(searchId);
      expect(retrievedResults).toEqual(mockResults);
    });

    it("returns undefined for non-existent search ID", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const retrievedResults = result.current.getResults("non-existent-id");
      expect(retrievedResults).toBeUndefined();
    });

    it("clears all results", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId1 = result.current.startSearch("flight", {});
      const searchId2 = result.current.startSearch("accommodation", {});

      act(() => {
        result.current.completeSearch(searchId1, { flights: [] });
        result.current.completeSearch(searchId2, { hotels: [] });
      });

      expect(Object.keys(result.current.results)).toHaveLength(2);

      act(() => {
        result.current.clearAllResults();
      });

      expect(result.current.results).toEqual({});
      expect(result.current.currentSearchId).toBeNull();
      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.currentContext).toBeNull();
      expect(result.current.status).toBe("idle");
    });

    it("clears specific search results", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId1 = result.current.startSearch("flight", {});
      const searchId2 = result.current.startSearch("accommodation", {});

      act(() => {
        result.current.completeSearch(searchId1, { flights: [] });
        result.current.completeSearch(searchId2, { hotels: [] });
      });

      expect(Object.keys(result.current.results)).toHaveLength(2);

      act(() => {
        result.current.clearResults(searchId1);
      });

      expect(result.current.results[searchId1]).toBeUndefined();
      expect(result.current.results[searchId2]).toBeDefined();
    });
  });

  describe("Metadata Management", () => {
    it("sets and gets results metadata", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchId = result.current.startSearch("flight", {});
      const metadata = {
        totalResults: 25,
        searchDuration: 1500,
        providers: ["airline1", "airline2"],
      };

      act(() => {
        result.current.setResultsMetadata(searchId, metadata);
      });

      expect(result.current.resultsMetadata[searchId]).toEqual(metadata);

      const retrievedMetadata = result.current.getResultsMetadata(searchId);
      expect(retrievedMetadata).toEqual(metadata);
    });

    it("returns undefined for non-existent metadata", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const metadata = result.current.getResultsMetadata("non-existent-id");
      expect(metadata).toBeUndefined();
    });
  });

  describe("Search Context", () => {
    it("maintains search context throughout lifecycle", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const searchParams = {
        origin: "NYC",
        destination: "LAX",
        departureDate: "2025-07-15",
      };

      const searchId = result.current.startSearch("flight", searchParams);

      // Verify initial context
      let context = result.current.currentContext!;
      expect(context.searchId).toBe(searchId);
      expect(context.searchType).toBe("flight");
      expect(context.searchParams).toEqual(searchParams);
      expect(context.startedAt).toBeDefined();
      expect(context.completedAt).toBeUndefined();

      // Complete search and verify context update
      act(() => {
        result.current.completeSearch(searchId, { flights: [] });
      });

      context = result.current.currentContext!;
      expect(context.completedAt).toBeDefined();
      expect(context.error).toBeUndefined();
    });
  });

  describe("Error Handling", () => {
    it("sets general error", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      const errorMessage = "Network connection failed";

      act(() => {
        result.current.setError(errorMessage);
      });

      expect(result.current.error).toBe(errorMessage);
    });

    it("clears error", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      act(() => {
        result.current.setError("Some error");
      });

      expect(result.current.error).toBe("Some error");

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe.skip("Search Status", () => {
    it("provides correct search status getters", () => {
      const { result } = renderHook(() => useSearchResultsStore());

      // Initially idle
      expect(result.current.isIdle).toBe(true);
      expect(result.current.isSearching).toBe(false);
      expect(result.current.isCompleted).toBe(false);
      expect(result.current.isFailed).toBe(false);
      expect(result.current.isCancelled).toBe(false);

      // Start search
      const searchId = result.current.startSearch("flight", {});

      expect(result.current.isIdle).toBe(false);
      expect(result.current.isSearching).toBe(true);
      expect(result.current.isCompleted).toBe(false);

      // Complete search
      act(() => {
        result.current.completeSearch(searchId, {});
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.isCompleted).toBe(true);
      expect(result.current.isFailed).toBe(false);
    });
  });
});
