/**
 * @vitest-environment node
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FlightSearchParams } from "@/lib/schemas/search";
import { useSearchFiltersStore } from "../search-filters-store";
import { useSearchHistoryStore } from "../search-history-store";
import { useSearchParamsStore } from "../search-params-store";
import { useSearchResultsStore } from "../search-results-store";
import { useSearchStore } from "../search-store";

describe("Search Store Orchestrator", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Reset all stores to initial state
    useSearchParamsStore.getState().reset();
    useSearchResultsStore.getState().reset();
    useSearchFiltersStore.getState().reset();
    useSearchHistoryStore.getState().reset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Initial State", () => {
    it("initializes with null search type and no params", () => {
      const store = useSearchStore.getState();
      expect(store.currentSearchType).toBeNull();
      expect(store.currentParams).toBeNull();
      expect(store.hasActiveFilters).toBe(false);
      expect(store.hasResults).toBe(false);
      expect(store.isSearching).toBe(false);
    });

    it("exposes all required orchestrator methods", () => {
      const store = useSearchStore.getState();
      expect(typeof store.initializeSearch).toBe("function");
      expect(typeof store.executeSearch).toBe("function");
      expect(typeof store.resetSearch).toBe("function");
      expect(typeof store.loadSavedSearch).toBe("function");
      expect(typeof store.duplicateCurrentSearch).toBe("function");
      expect(typeof store.validateAndExecuteSearch).toBe("function");
      expect(typeof store.applyFiltersAndSearch).toBe("function");
      expect(typeof store.retryLastSearch).toBe("function");
      expect(typeof store.syncStores).toBe("function");
      expect(typeof store.getSearchSummary).toBe("function");
    });
  });

  describe("Search Initialization", () => {
    it("initializes search type across all stores", () => {
      const store = useSearchStore.getState();
      store.initializeSearch("flight");

      expect(store.currentSearchType).toBe("flight");
      expect(useSearchParamsStore.getState().currentSearchType).toBe("flight");
    });
  });

  describe("Search Execution", () => {
    it("executes search with valid params", async () => {
      const store = useSearchStore.getState();
      const flightParams: FlightSearchParams = {
        adults: 1,
        cabinClass: "economy" as const,
        children: 0,
        departureDate: "2025-07-15",
        destination: "LAX",
        directOnly: false,
        excludedAirlines: [],
        infants: 0,
        origin: "NYC",
        preferredAirlines: [],
      };

      store.initializeSearch("flight");
      await useSearchParamsStore.getState().updateFlightParams(flightParams);

      // Verify params are set
      expect(useSearchParamsStore.getState().currentSearchType).toBe("flight");
      expect(useSearchParamsStore.getState().flightParams).toMatchObject(flightParams);

      // Execute search - use fake timers to skip delays
      const searchPromise = store.executeSearch(flightParams);
      // Fast-forward through all setTimeout calls (3 x 500ms = 1500ms)
      await vi.runAllTimersAsync();
      const searchId = await searchPromise;

      expect(searchId).toBeTruthy();
      expect(useSearchResultsStore.getState().hasResults).toBe(true);
    });

    it("throws error when executing without search type", async () => {
      const store = useSearchStore.getState();
      await expect(store.executeSearch()).rejects.toThrow("No search type selected");
    });

    it("validates params before executing", async () => {
      const store = useSearchStore.getState();
      store.initializeSearch("flight");
      // Set invalid params (missing required fields)
      useSearchParamsStore.getState().setFlightParams({
        adults: 1,
        cabinClass: "economy",
        children: 0,
        directOnly: false,
        excludedAirlines: [],
        infants: 0,
        preferredAirlines: [],
      });

      await expect(store.validateAndExecuteSearch()).rejects.toThrow();
    });
  });

  describe("Search Reset", () => {
    it("resets all stores to initial state", () => {
      const store = useSearchStore.getState();
      store.initializeSearch("flight");
      useSearchParamsStore.getState().setFlightParams({
        adults: 2,
        cabinClass: "business",
        children: 1,
        directOnly: true,
        excludedAirlines: [],
        infants: 0,
        origin: "NYC",
        preferredAirlines: [],
      });
      useSearchFiltersStore.getState().setActiveFilter("price_range", {
        min: 100,
      });

      expect(store.currentSearchType).toBe("flight");
      expect(store.hasActiveFilters).toBe(true);

      store.resetSearch();

      expect(store.currentSearchType).toBeNull();
      expect(store.hasActiveFilters).toBe(false);
      expect(useSearchParamsStore.getState().currentSearchType).toBeNull();
      expect(useSearchFiltersStore.getState().hasActiveFilters).toBe(false);
    });
  });

  describe("State Synchronization", () => {
    it("syncs search type across stores", () => {
      const store = useSearchStore.getState();
      useSearchParamsStore.getState().setSearchType("flight");
      store.syncStores();

      expect(store.currentSearchType).toBe("flight");
    });
  });

  describe("Search Summary", () => {
    it("provides accurate search summary", () => {
      const store = useSearchStore.getState();
      store.initializeSearch("flight");
      const summary = store.getSearchSummary();

      expect(summary.searchType).toBe("flight");
      expect(summary.hasResults).toBe(false);
      expect(summary.resultCount).toBe(0);
      expect(summary.hasFilters).toBe(false);
      expect(summary.filterCount).toBe(0);
    });
  });
});
