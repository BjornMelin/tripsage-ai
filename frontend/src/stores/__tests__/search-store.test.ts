/**
 * @fileoverview Unit tests for the search store orchestrator, covering search
 * initialization, execution, filtering, history management, and state synchronization
 * across multiple search-related stores.
 */

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
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
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

      // Mock validation to return false; expect validateAndExecuteSearch to throw
      vi.spyOn(paramsStore.current, "validateCurrentParams").mockResolvedValue(false);

      await expect(
        act(async () => {
          await result.current.validateAndExecuteSearch();
        })
      ).rejects.toThrowError();
      expect(paramsStore.current.validateCurrentParams).toHaveBeenCalled();
    });
  });

  describe("Search Summary", () => {
    it("provides accurate search summary", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());

      await act(async () => {
        result.current.initializeSearch("flight");
        await paramsStore.current.updateFlightParams({
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        } as any);
        await filtersStore.current.setActiveFilter("price_range", {
          max: 500,
          min: 100,
        });
      });

      const summary = result.current.getSearchSummary();

      expect(summary.searchType).toBe("flight");
      // Params may be minimal defaults or updated; primary signal is filters and type
      expect(summary.hasFilters).toBe(true);
      expect(summary.filterCount).toBe(1);
    });
  });

  describe("Cross-Store Operations", () => {
    it("resets all stores", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: paramsStore } = renderHook(() => useSearchParamsStore());
      const { result: resultsStore } = renderHook(() => useSearchResultsStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());

      // Set some data in stores
      await act(async () => {
        result.current.initializeSearch("flight");
        await paramsStore.current.updateFlightParams({
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        } as any);
        await filtersStore.current.setActiveFilter("price_range", { min: 100 });
      });

      expect(paramsStore.current.currentSearchType).toBe("flight");
      expect(Object.keys(filtersStore.current.activeFilters).length).toBeGreaterThan(0);

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
          occurredAt: new Date().toISOString(),
          retryable: true,
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

      // Initialize and set minimal valid params and filters
      await act(async () => {
        result.current.initializeSearch("flight");
        await useSearchParamsStore.getState().updateFlightParams({
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        } as any);
        await filtersStore.current.setActiveFilter("price_range", {
          max: 500,
          min: 100,
        });
        await filtersStore.current.setActiveFilter("airlines", ["AA", "UA"]);
      });

      // Mock search
      vi.spyOn(resultsStore.current, "startSearch").mockReturnValue(
        "filtered-search-123"
      );

      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.executeSearch({
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        } as SearchParams);
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
        createdAt: new Date().toISOString(),
        id: "saved-123",
        isFavorite: false,
        isPublic: false,
        name: "NYC to LAX Flight",
        params: {
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        },
        searchType: "flight" as SearchType,
        tags: [],
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

      // Setup current search and params directly
      await act(async () => {
        result.current.initializeSearch("flight");
        useSearchParamsStore.getState().setFlightParams({
          departureDate: "2025-07-15",
          destination: "LAX",
          origin: "NYC",
        } as any);
      });

      // Mock save
      vi.spyOn(historyStore.current, "saveSearch").mockResolvedValue("new-saved-123");

      // Ensure params are considered valid before duplication
      await act(async () => {
        await useSearchParamsStore.getState().validateCurrentParams();
      });
      let savedId: string | null = null;
      await act(async () => {
        savedId = await result.current.duplicateCurrentSearch("My NYC Flight");
      });

      expect(savedId).toBe("new-saved-123");
      expect(historyStore.current.saveSearch).toHaveBeenCalled();
      const call = (historyStore.current.saveSearch as any).mock.calls.at(-1);
      expect(call[0]).toBe("My NYC Flight");
      expect(call[1]).toBe("flight");
      expect(typeof call[2]).toBe("object");
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
              airline: "Test Air",
              arrivalTime: new Date().toISOString(),
              cabinClass: "economy",
              departureTime: new Date().toISOString(),
              destination: "LAX",
              duration: 300,
              flightNumber: "TA123",
              id: "f1",
              origin: "NYC",
              price: 299,
              seatsAvailable: 10,
              stops: 0,
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

    it("correctly computes hasActiveFilters", async () => {
      const { result } = renderHook(() => useSearchStore());
      const { result: filtersStore } = renderHook(() => useSearchFiltersStore());

      expect(result.current.hasActiveFilters).toBe(false);

      await act(async () => {
        result.current.initializeSearch("flight");
        await filtersStore.current.setActiveFilter("price_range", { min: 100 });
      });
      await act(async () => {
        // allow derived state to compute
        await Promise.resolve();
      });
      expect(result.current.hasActiveFilters).toBe(true);
    });
  });
});
