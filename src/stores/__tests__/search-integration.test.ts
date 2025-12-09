/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchOrchestration } from "@/hooks/search/use-search-orchestration";
import { AllTheProviders } from "@/test/test-utils";
import { useSearchFiltersStore } from "../search-filters-store";
import { useSearchParamsStore } from "../search-params-store";
import { useSearchResultsStore } from "../search-results-store";

describe("Search Store Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset all stores to initial state
    useSearchParamsStore.getState().reset();
    useSearchFiltersStore.getState().reset();
    useSearchResultsStore.getState().reset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    React.createElement(AllTheProviders, null, children);

  describe("store synchronization", () => {
    it("should sync search type across params and filters stores", () => {
      // Set search type in params store
      useSearchParamsStore.getState().setSearchType("flight");

      expect(useSearchParamsStore.getState().currentSearchType).toBe("flight");

      // Manually sync filters store (in real usage, orchestration hook handles this)
      useSearchFiltersStore.getState().setSearchType("flight");

      expect(useSearchFiltersStore.getState().currentSearchType).toBe("flight");
    });

    it("should load default filters for search type", () => {
      useSearchFiltersStore.getState().setSearchType("flight");

      const state = useSearchFiltersStore.getState();
      expect(state.currentFilters.length).toBeGreaterThan(0);

      // Flight should have price_range and stops filters
      const filterIds = state.currentFilters.map((f) => f.id);
      expect(filterIds).toContain("price_range");
      expect(filterIds).toContain("stops");
    });

    it("should load different filters for different search types", () => {
      useSearchFiltersStore.getState().setSearchType("accommodation");

      const accFilters = useSearchFiltersStore.getState().currentFilters;

      useSearchFiltersStore.getState().setSearchType("flight");

      const flightFilters = useSearchFiltersStore.getState().currentFilters;

      // Filter sets should be different
      expect(accFilters).not.toEqual(flightFilters);
    });
  });

  describe("params validation workflow", () => {
    it("should update flight params and validate", async () => {
      useSearchParamsStore.getState().setSearchType("flight");

      const isValid = await useSearchParamsStore
        .getState()
        .updateFlightParams({ destination: "LAX", origin: "JFK" });

      expect(isValid).toBe(true);
      expect(useSearchParamsStore.getState().flightParams).toMatchObject({
        destination: "LAX",
        origin: "JFK",
      });
    });

    it("should remain invalid when required params are incomplete", async () => {
      useSearchParamsStore.getState().setSearchType("flight");

      await useSearchParamsStore.getState().updateFlightParams({
        destination: "LAX",
        origin: "JFK",
      });
      expect(useSearchParamsStore.getState().hasValidParams).toBe(false);
    });

    it("sets hasValidParams true when required flight params are provided", async () => {
      useSearchParamsStore.getState().setSearchType("flight");

      const isValid = await useSearchParamsStore.getState().updateFlightParams({
        departureDate: "2024-07-15",
        destination: "LAX",
        origin: "JFK",
      });

      expect(isValid).toBe(true);
      expect(useSearchParamsStore.getState().hasValidParams).toBe(true);
    });
  });

  describe("search results workflow", () => {
    it("should track search lifecycle: idle -> searching -> success", () => {
      // Initially idle
      expect(useSearchResultsStore.getState().status).toBe("idle");
      expect(useSearchResultsStore.getState().isSearching).toBe(false);

      // Start search
      const searchId = useSearchResultsStore.getState().startSearch("flight", {
        destination: "LAX",
        origin: "JFK",
      });

      expect(useSearchResultsStore.getState().status).toBe("searching");
      expect(useSearchResultsStore.getState().isSearching).toBe(true);
      expect(useSearchResultsStore.getState().currentSearchId).toBe(searchId);

      // Set results
      useSearchResultsStore.getState().setSearchResults(searchId, {
        flights: [
          {
            airline: "Test Air",
            arrivalTime: "2024-07-15T14:00:00Z",
            cabinClass: "economy",
            departureTime: "2024-07-15T10:00:00Z",
            destination: "LAX",
            duration: 240,
            flightNumber: "TA123",
            id: "flight-1",
            origin: "JFK",
            price: 500,
            seatsAvailable: 10,
            stops: 0,
          },
        ],
      });

      // Complete search
      useSearchResultsStore.getState().completeSearch(searchId);

      expect(useSearchResultsStore.getState().status).toBe("success");
      expect(useSearchResultsStore.getState().isSearching).toBe(false);
      expect(useSearchResultsStore.getState().results.flights).toHaveLength(1);
    });

    it("should track search errors", () => {
      const searchId = useSearchResultsStore.getState().startSearch("flight", {});

      useSearchResultsStore.getState().setSearchError(searchId, {
        code: "RATE_LIMIT",
        message: "Too many requests",
        occurredAt: new Date().toISOString(),
        retryable: true,
      });

      expect(useSearchResultsStore.getState().status).toBe("error");
      expect(useSearchResultsStore.getState().error?.code).toBe("RATE_LIMIT");
    });

    it("should clear results for a search type", () => {
      // Add some results with minimal valid flight structure
      const searchId = useSearchResultsStore.getState().startSearch("flight", {});
      const minimalFlight = {
        airline: "Test",
        arrival: { airport: "LAX", time: "14:00" },
        departure: { airport: "JFK", time: "10:00" },
        duration: "4h",
        flightNumber: "T1",
        id: "1",
        price: { amount: 100, currency: "USD" },
        segments: [],
        stops: 0,
      };
      useSearchResultsStore.getState().setSearchResults(searchId, {
        // biome-ignore lint/suspicious/noExplicitAny: Test data with minimal structure
        flights: [minimalFlight as any],
      });
      useSearchResultsStore.getState().completeSearch(searchId);

      expect(useSearchResultsStore.getState().results.flights).toHaveLength(1);

      // Clear results
      useSearchResultsStore.getState().clearResults("flight");

      expect(useSearchResultsStore.getState().results.flights).toEqual([]);
    });
  });

  describe("filter operations", () => {
    it("should set and validate filters", () => {
      useSearchFiltersStore.getState().setSearchType("flight");

      // Set a filter
      const success = useSearchFiltersStore.getState().setActiveFilter("stops", 1);

      expect(success).toBe(true);
      expect(useSearchFiltersStore.getState().activeFilters.stops).toBeDefined();
      expect(useSearchFiltersStore.getState().activeFilters.stops.value).toBe(1);
    });

    it("should track active filter count", () => {
      useSearchFiltersStore.getState().setSearchType("flight");

      expect(useSearchFiltersStore.getState().activeFilterCount).toBe(0);

      useSearchFiltersStore.getState().setActiveFilter("stops", 1);
      expect(useSearchFiltersStore.getState().activeFilterCount).toBe(1);

      useSearchFiltersStore.getState().setActiveFilter("price_range", {
        max: 500,
        min: 100,
      });
      expect(useSearchFiltersStore.getState().activeFilterCount).toBe(2);
    });

    it("should clear all filters", () => {
      useSearchFiltersStore.getState().setSearchType("flight");
      useSearchFiltersStore.getState().setActiveFilter("stops", 1);
      useSearchFiltersStore
        .getState()
        .setActiveFilter("price_range", { max: 500, min: 100 });

      expect(useSearchFiltersStore.getState().activeFilterCount).toBe(2);

      useSearchFiltersStore.getState().clearAllFilters();

      expect(useSearchFiltersStore.getState().activeFilterCount).toBe(0);
      expect(useSearchFiltersStore.getState().activeFilters).toEqual({});
    });
  });

  describe("orchestration hook integration", () => {
    it("should initialize search with correct type", () => {
      const { result } = renderHook(() => useSearchOrchestration(), { wrapper });

      act(() => {
        result.current.initializeSearch("accommodation");
      });

      expect(useSearchParamsStore.getState().currentSearchType).toBe("accommodation");
      expect(useSearchFiltersStore.getState().currentSearchType).toBe("accommodation");
    });

    it("should reset all search state", () => {
      const { result } = renderHook(() => useSearchOrchestration(), { wrapper });

      // Initialize and set some state
      act(() => {
        result.current.initializeSearch("flight");
      });

      useSearchParamsStore.getState().updateFlightParams({ origin: "JFK" });
      useSearchFiltersStore.getState().setActiveFilter("stops", 0);

      // Reset
      act(() => {
        result.current.resetSearch();
      });

      expect(useSearchParamsStore.getState().flightParams).toEqual({});
      expect(useSearchFiltersStore.getState().activeFilterCount).toBe(0);
    });

    it("should expose current search state", () => {
      const { result } = renderHook(() => useSearchOrchestration(), { wrapper });

      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.isSearching).toBe(false);
      expect(result.current.hasResults).toBe(false);

      act(() => {
        result.current.initializeSearch("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
    });

    it("should provide search summary", () => {
      const { result } = renderHook(() => useSearchOrchestration(), { wrapper });

      act(() => {
        result.current.initializeSearch("flight");
      });

      const summary = result.current.getSearchSummary();

      expect(summary.searchType).toBe("flight");
      expect(summary.hasResults).toBe(false);
      expect(summary.resultCount).toBe(0);
      expect(summary.hasFilters).toBe(false);
      expect(summary.filterCount).toBe(0);
    });
  });

  describe("cross-store computed state", () => {
    it("should compute hasValidParams correctly", () => {
      useSearchParamsStore.getState().setSearchType("flight");

      // Initially not valid (no required params)
      expect(useSearchParamsStore.getState().hasValidParams).toBe(false);
    });

    it("should compute hasActiveFilters correctly", () => {
      useSearchFiltersStore.getState().setSearchType("flight");

      expect(useSearchFiltersStore.getState().hasActiveFilters).toBe(false);

      useSearchFiltersStore.getState().setActiveFilter("stops", 1);

      expect(useSearchFiltersStore.getState().hasActiveFilters).toBe(true);
    });

    it("should compute canRetry correctly after error", () => {
      const searchId = useSearchResultsStore.getState().startSearch("flight", {});

      useSearchResultsStore.getState().setSearchError(searchId, {
        code: "SEARCH_ERROR",
        message: "Failed",
        occurredAt: new Date().toISOString(),
        retryable: true,
      });

      expect(useSearchResultsStore.getState().canRetry).toBe(true);
    });

    it("should disable retry for non-retryable errors", () => {
      const searchId = useSearchResultsStore.getState().startSearch("flight", {});
      useSearchResultsStore.getState().setSearchError(searchId, {
        code: "SEARCH_ERROR",
        message: "fatal",
        occurredAt: new Date().toISOString(),
        retryable: false,
      });
      expect(useSearchResultsStore.getState().canRetry).toBe(false);
    });
  });
});
