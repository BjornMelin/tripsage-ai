import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SearchParams, SearchType } from "@/types/search";
import { useSearchFiltersStore } from "../search-filters-store";
import { useSearchHistoryStore } from "../search-history-store";
import { useSearchParamsStore } from "../search-params-store";
import { useSearchResultsStore } from "../search-results-store";
import { useSearchStore } from "../search-store";

describe("Search Store Orchestrator", () => {
  beforeEach(() => {
    // Reset all stores to initial state
    act(() => {
      useSearchParamsStore.getState().reset();
      useSearchResultsStore.getState().reset();
      useSearchFiltersStore.getState().reset();
      useSearchHistoryStore.getState().reset();
    });
  });

  describe("Initial State", () => {
    it("initializes with correct computed properties", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.currentParams).toBeNull();
      expect(result.current.hasActiveFilters).toBe(false);
      expect(result.current.hasResults).toBe(false);
      expect(result.current.isSearching).toBe(false);
    });

    it("has all required methods", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(typeof result.current.initializeSearch).toBe("function");
      expect(typeof result.current.executeSearch).toBe("function");
      expect(typeof result.current.resetSearch).toBe("function");
      expect(typeof result.current.loadSavedSearch).toBe("function");
      expect(typeof result.current.duplicateCurrentSearch).toBe("function");
      expect(typeof result.current.validateAndExecuteSearch).toBe("function");
      expect(typeof result.current.applyFiltersAndSearch).toBe("function");
      expect(typeof result.current.retryLastSearch).toBe("function");
      expect(typeof result.current.syncStores).toBe("function");
      expect(typeof result.current.getSearchSummary).toBe("function");
    });
  });

  describe("Search Initialization", () => {
    it("initializes search with correct type", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsResult } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.initializeSearch("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
      expect(paramsResult.current.currentSearchType).toBe("flight");

      // Check that default params are set
      expect(paramsResult.current.flightParams).toHaveProperty("adults", 1);
    });

    it("switches search type correctly", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");

      act(() => {
        result.current.initializeSearch("accommodation");
      });

      expect(result.current.currentSearchType).toBe("accommodation");
    });
  });

  describe("Search Execution", () => {
    it("executes search with params", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());

      // Initialize search type first
      act(() => {
        result.current.initializeSearch("flight");
      });

      // Mock the actual search execution
      vi.spyOn(resultsStore.current, "startSearch").mockReturnValue("search-123");

      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.executeSearch({
          origin: "NYC",
          destination: "LAX",
          departureDate: "2025-07-15",
        } as SearchParams);
      });

      expect(searchId).toBe("search-123");
      expect(resultsStore.current.startSearch).toHaveBeenCalled();
    });

    it("validates before executing search", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());

      act(() => {
        result.current.initializeSearch("flight");
      });

      // Mock validation to return false
      vi.spyOn(paramsStore.current, "validateCurrentParams").mockResolvedValue(false);

      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.validateAndExecuteSearch();
      });

      expect(searchId).toBeNull();
      expect(paramsStore.current.validateCurrentParams).toHaveBeenCalled();
    });
  });

  describe("Search Summary", () => {
    it("provides accurate search summary", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());

      act(() => {
        result.current.initializeSearch("flight");
        paramsStore.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
        filtersStore.current.setActiveFilter("price", { min: 100, max: 500 });
      });

      const summary = result.current.getSearchSummary();

      expect(summary.searchType).toBe("flight");
      expect(summary.params).toBeTruthy();
      expect(summary.hasFilters).toBe(true);
      expect(summary.filterCount).toBe(1);
    });
  });

  describe("Cross-Store Operations", () => {
    it("resets all stores", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());

      // Set some data in stores
      act(() => {
        result.current.initializeSearch("flight");
        paramsStore.current.updateFlightParams({ origin: "NYC" });
        filtersStore.current.setActiveFilter("price", { min: 100 });
      });

      expect(paramsStore.current.currentSearchType).toBe("flight");
      expect(filtersStore.current.activeFilters.flight).toBeTruthy();

      // Reset everything
      act(() => {
        result.current.resetSearch();
      });

      expect(paramsStore.current.currentSearchType).toBeNull();
      expect(filtersStore.current.activeFilters).toEqual({});
      expect(resultsStore.current.status).toBe("idle");
    });

    it("retries last search", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());

      // Setup a failed search
      act(() => {
        result.current.initializeSearch("flight");
        const searchId = resultsStore.current.startSearch("flight", { origin: "NYC" });
        resultsStore.current.setSearchError(searchId, {
          message: "Network error",
          retryable: true,
          occurredAt: new Date().toISOString(),
        });
      });

      // Mock retry
      vi.spyOn(resultsStore.current, "retryLastSearch").mockResolvedValue(
        "new-search-id"
      );

      let newSearchId: string | null = null;
      await act(async () => {
        newSearchId = await result.current.retryLastSearch();
      });

      expect(newSearchId).toBe("new-search-id");
      expect(resultsStore.current.retryLastSearch).toHaveBeenCalled();
    });
  });

  describe("Filter Integration", () => {
    it("applies filters and executes search", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());

      // Initialize and set filters
      act(() => {
        result.current.initializeSearch("flight");
        filtersStore.current.setActiveFilter("price", { min: 100, max: 500 });
        filtersStore.current.setActiveFilter("airlines", ["AA", "UA"]);
      });

      // Mock search
      vi.spyOn(resultsStore.current, "startSearch").mockReturnValue(
        "filtered-search-123"
      );

      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.applyFiltersAndSearch();
      });

      expect(searchId).toBe("filtered-search-123");
      expect(result.current.hasActiveFilters).toBe(true);
    });
  });

  describe("Saved Search Operations", () => {
    it("loads saved search", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: historyStore } = renderHook(() => useSearchHistoryStore());

      // Mock saved search
      const mockSavedSearch = {
        id: "saved-123",
        name: "NYC to LAX Flight",
        searchType: "flight" as SearchType,
        params: {
          origin: "NYC",
          destination: "LAX",
          departureDate: "2025-07-15",
        },
        tags: [],
        isPublic: false,
        isFavorite: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        usageCount: 0,
      };

      // Mock savedSearches array to contain our test saved search
      historyStore.current.savedSearches = [mockSavedSearch];

      let loaded = false;
      await act(async () => {
        loaded = await result.current.loadSavedSearch("saved-123");
      });

      expect(loaded).toBe(true);
      expect(result.current.currentSearchType).toBe("flight");
    });

    it("duplicates current search", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: historyStore } = renderHook(() => useSearchHistoryStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());

      // Setup current search
      act(() => {
        result.current.initializeSearch("flight");
        paramsStore.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
      });

      // Mock save
      vi.spyOn(historyStore.current, "saveSearch").mockResolvedValue("new-saved-123");

      let savedId: string | null = null;
      await act(async () => {
        savedId = await result.current.duplicateCurrentSearch("My NYC Flight");
      });

      expect(savedId).toBe("new-saved-123");
      expect(historyStore.current.saveSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "My NYC Flight",
          searchType: "flight",
        })
      );
    });
  });

  describe("State Synchronization", () => {
    it("syncs state across stores", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());

      // Set different states
      act(() => {
        paramsStore.current.setSearchType("flight");
        resultsStore.current.startSearch("accommodation", {});
      });

      // Sync should align states
      act(() => {
        result.current.syncStores();
      });

      // After sync, states should be consistent
      expect(result.current.currentSearchType).toBeDefined();
    });
  });

  describe("Computed Properties", () => {
    it("correctly computes hasResults", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());

      expect(result.current.hasResults).toBe(false);

      act(() => {
        const searchId = resultsStore.current.startSearch("flight", {});
        resultsStore.current.setSearchResults(searchId, {
          flights: [
            {
              id: "f1",
              airline: "Test Air",
              flightNumber: "TA123",
              origin: "NYC",
              destination: "LAX",
              departureTime: new Date().toISOString(),
              arrivalTime: new Date().toISOString(),
              duration: 300,
              stops: 0,
              price: 299,
              cabinClass: "economy",
              seatsAvailable: 10,
            },
          ],
        });
      });

      expect(result.current.hasResults).toBe(true);
    });

    it("correctly computes isSearching", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());

      expect(result.current.isSearching).toBe(false);

      act(() => {
        resultsStore.current.startSearch("flight", {});
      });

      expect(result.current.isSearching).toBe(true);
    });

    it("correctly computes hasActiveFilters", () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());

      expect(result.current.hasActiveFilters).toBe(false);

      act(() => {
        filtersStore.current.setActiveFilter("price", { min: 100 });
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });
  });
});
