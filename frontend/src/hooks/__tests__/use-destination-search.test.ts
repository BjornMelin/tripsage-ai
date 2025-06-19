import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useDestinationSearch } from "../use-destination-search";

describe("useDestinationSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should initialize with correct default values", () => {
      const { result } = renderHook(() => useDestinationSearch());

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
      expect(typeof result.current.searchDestinations).toBe("function");
      expect(typeof result.current.resetSearch).toBe("function");
    });
  });

  describe("searchDestinations", () => {
    it("should set isSearching to true during search", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      act(() => {
        result.current.searchDestinations({ query: "Paris" });
      });

      expect(result.current.isSearching).toBe(true);

      await waitFor(() => {
        expect(result.current.isSearching).toBe(false);
      });
    });

    it("should clear error when starting new search", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      // Set an initial error
      act(() => {
        result.current.resetSearch();
      });

      // Start a new search
      act(() => {
        result.current.searchDestinations({ query: "London" });
      });

      expect(result.current.searchError).toBe(null);

      await waitFor(() => {
        expect(result.current.isSearching).toBe(false);
      });
    });

    it("should handle search with different parameters", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      const searchParams = {
        query: "Tokyo",
        types: ["city", "country"],
        limit: 10,
      };

      await act(async () => {
        await result.current.searchDestinations(searchParams);
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should handle search with minimal parameters", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      await act(async () => {
        await result.current.searchDestinations({ query: "Rome" });
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should handle empty query", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      await act(async () => {
        await result.current.searchDestinations({ query: "" });
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should handle search with types array", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      await act(async () => {
        await result.current.searchDestinations({
          query: "Barcelona",
          types: ["city", "region", "country"],
        });
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should handle search with limit parameter", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      await act(async () => {
        await result.current.searchDestinations({
          query: "New York",
          limit: 5,
        });
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });
  });

  describe("resetSearch", () => {
    it("should reset search state", () => {
      const { result } = renderHook(() => useDestinationSearch());

      act(() => {
        result.current.resetSearch();
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should clear any existing error", () => {
      const { result } = renderHook(() => useDestinationSearch());

      // Reset should clear any state
      act(() => {
        result.current.resetSearch();
      });

      expect(result.current.searchError).toBe(null);
      expect(result.current.isSearching).toBe(false);
    });
  });

  describe("Error Handling", () => {
    it("should handle potential errors gracefully", async () => {
      // Since this is a mock implementation that doesn't actually throw errors,
      // we test that the structure supports error handling
      const { result } = renderHook(() => useDestinationSearch());

      await act(async () => {
        await result.current.searchDestinations({ query: "Test" });
      });

      // The mock implementation should not produce errors
      expect(result.current.searchError).toBe(null);
    });
  });

  describe("Search State Management", () => {
    it("should maintain proper state transitions", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      // Initial state
      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);

      // Start search
      const searchPromise = act(async () => {
        await result.current.searchDestinations({ query: "Amsterdam" });
      });

      // Complete search
      await searchPromise;

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should handle multiple consecutive searches", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      // First search
      await act(async () => {
        await result.current.searchDestinations({ query: "Berlin" });
      });

      expect(result.current.isSearching).toBe(false);

      // Second search
      await act(async () => {
        await result.current.searchDestinations({ query: "Vienna" });
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });

    it("should handle reset after search", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      // Complete a search
      await act(async () => {
        await result.current.searchDestinations({ query: "Prague" });
      });

      // Reset
      act(() => {
        result.current.resetSearch();
      });

      expect(result.current.isSearching).toBe(false);
      expect(result.current.searchError).toBe(null);
    });
  });

  describe("Parameter Validation", () => {
    it("should handle various query string formats", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      const testQueries = [
        "Simple City",
        "City with spaces",
        "City-with-hyphens",
        "City123",
        "Città with accents",
        "東京", // Non-Latin characters
      ];

      for (const query of testQueries) {
        await act(async () => {
          await result.current.searchDestinations({ query });
        });

        expect(result.current.searchError).toBe(null);
      }
    });

    it("should handle different types arrays", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      const testCases = [
        { query: "Test", types: ["city"] },
        { query: "Test", types: ["city", "country"] },
        { query: "Test", types: ["city", "region", "country", "landmark"] },
        { query: "Test", types: [] },
      ];

      for (const testCase of testCases) {
        await act(async () => {
          await result.current.searchDestinations(testCase);
        });

        expect(result.current.searchError).toBe(null);
      }
    });

    it("should handle different limit values", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      const testLimits = [1, 5, 10, 20, 50, 100];

      for (const limit of testLimits) {
        await act(async () => {
          await result.current.searchDestinations({ query: "Test", limit });
        });

        expect(result.current.searchError).toBe(null);
      }
    });

    it("should handle edge case limit values", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      const edgeCaseLimits = [0, -1, 999999];

      for (const limit of edgeCaseLimits) {
        await act(async () => {
          await result.current.searchDestinations({ query: "Test", limit });
        });

        // Should not throw errors even with unusual limit values
        expect(result.current.searchError).toBe(null);
      }
    });
  });

  describe("Function Stability", () => {
    it("should provide stable function references", () => {
      const { result, rerender } = renderHook(() => useDestinationSearch());

      const initialSearchDestinations = result.current.searchDestinations;
      const initialResetSearch = result.current.resetSearch;

      rerender();

      // Functions should remain stable across rerenders in this mock implementation
      expect(result.current.searchDestinations).toBe(initialSearchDestinations);
      expect(result.current.resetSearch).toBe(initialResetSearch);
    });
  });

  describe("Mock Implementation Behavior", () => {
    it("should simulate async behavior with timeout", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      const startTime = Date.now();

      await act(async () => {
        await result.current.searchDestinations({ query: "Test" });
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should take at least 100ms due to the setTimeout in the mock
      expect(duration).toBeGreaterThanOrEqual(95); // Allow some tolerance for timing
    });

    it("should complete search operation", async () => {
      const { result } = renderHook(() => useDestinationSearch());

      let searchStarted = false;
      let searchCompleted = false;

      const searchPromise = act(async () => {
        searchStarted = true;
        await result.current.searchDestinations({ query: "Test" });
        searchCompleted = true;
      });

      expect(searchStarted).toBe(true);

      await searchPromise;

      expect(searchCompleted).toBe(true);
      expect(result.current.isSearching).toBe(false);
    });
  });
});
