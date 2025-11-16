import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { FlightSearchParams, SearchType } from "@/lib/schemas/search";
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
    it("initializes with null search type and no params", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.currentParams).toBeNull();
      expect(result.current.hasActiveFilters).toBe(false);
      expect(result.current.hasResults).toBe(false);
      expect(result.current.isSearching).toBe(false);
    });

    it("exposes all required orchestrator methods", () => {
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
    it("initializes search type across all stores", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
      expect(useSearchParamsStore.getState().currentSearchType).toBe("flight");
      expect(useSearchFiltersStore.getState().currentSearchType).toBe("flight");
    });

    it("switches between search types correctly", () => {
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

    it("initializes default params when setting search type", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
      });

      const flightParams = useSearchParamsStore.getState().flightParams;
      expect(flightParams).toHaveProperty("adults", 1);
      expect(flightParams).toHaveProperty("cabinClass", "economy");
    });
  });

  describe("Computed Properties", () => {
    it("reflects hasResults from results store", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(result.current.hasResults).toBe(false);

      act(() => {
        result.current.initializeSearch("flight");
        const searchId = useSearchResultsStore.getState().startSearch("flight", {
          destination: "LAX",
          origin: "NYC",
        });
        useSearchResultsStore.getState().setSearchResults(searchId, {
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

    it("reflects isSearching from results store", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(result.current.isSearching).toBe(false);

      act(() => {
        result.current.initializeSearch("flight");
        useSearchResultsStore.getState().startSearch("flight", {});
      });

      expect(result.current.isSearching).toBe(true);
    });

    it("reflects hasActiveFilters from filters store", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(result.current.hasActiveFilters).toBe(false);

      act(() => {
        result.current.initializeSearch("flight");
        useSearchFiltersStore.getState().setActiveFilter("price_range", {
          max: 500,
          min: 100,
        });
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });
  });

  describe("Search Execution", () => {
    it("executes search with valid params", async () => {
      const { result } = renderHook(() => useSearchStore());

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

      await act(async () => {
        result.current.initializeSearch("flight");
        await useSearchParamsStore.getState().updateFlightParams(flightParams);
      });

      // Verify params are set in the store
      const paramsStore = useSearchParamsStore.getState();
      expect(paramsStore.currentSearchType).toBe("flight");
      expect(paramsStore.flightParams).toMatchObject(flightParams);

      // Execute search with explicit params to avoid getter issues
      let searchId: string | null = null;
      await act(async () => {
        searchId = await result.current.executeSearch(flightParams);
      });

      expect(searchId).toBeTruthy();
      // Results are set asynchronously, so we check the store directly
      expect(useSearchResultsStore.getState().hasResults).toBe(true);
    });

    it("throws error when executing without search type", async () => {
      const { result } = renderHook(() => useSearchStore());

      await expect(
        act(async () => {
          await result.current.executeSearch();
        })
      ).rejects.toThrow("No search type selected");
    });

    it("validates params before executing", async () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
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
      });

      await expect(
        act(async () => {
          await result.current.validateAndExecuteSearch();
        })
      ).rejects.toThrow();
    });
  });

  describe("Search Reset", () => {
    it("resets all stores to initial state", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
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
      });

      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.hasActiveFilters).toBe(true);

      act(() => {
        result.current.resetSearch();
      });

      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.hasActiveFilters).toBe(false);
      expect(useSearchResultsStore.getState().status).toBe("idle");
    });
  });

  describe("Search Summary", () => {
    it("provides accurate search summary", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
        useSearchParamsStore.getState().setFlightParams({
          adults: 1,
          cabinClass: "economy",
          children: 0,
          departureDate: "2025-07-15",
          destination: "LAX",
          directOnly: false,
          excludedAirlines: [],
          infants: 0,
          origin: "NYC",
          preferredAirlines: [],
        });
        useSearchFiltersStore.getState().setActiveFilter("price_range", {
          max: 500,
          min: 100,
        });
      });

      const summary = result.current.getSearchSummary();

      expect(summary.searchType).toBe("flight");
      expect(summary.hasFilters).toBe(true);
      expect(summary.filterCount).toBeGreaterThan(0);
      expect(summary.hasResults).toBe(false);
      expect(summary.resultCount).toBe(0);
    });
  });

  describe("Saved Search Operations", () => {
    it("loads saved search successfully", async () => {
      const { result } = renderHook(() => useSearchStore());

      const savedSearch = {
        createdAt: new Date().toISOString(),
        id: "saved-1",
        isFavorite: false,
        isPublic: false,
        name: "NYC to LAX",
        params: {
          adults: 1,
          cabinClass: "economy",
          children: 0,
          departureDate: "2025-07-15",
          destination: "LAX",
          directOnly: false,
          excludedAirlines: [],
          infants: 0,
          origin: "NYC",
          preferredAirlines: [],
        },
        searchType: "flight" as SearchType,
        tags: [],
        updatedAt: new Date().toISOString(),
        usageCount: 0,
      };

      act(() => {
        useSearchHistoryStore.getState().savedSearches.push(savedSearch);
      });

      let loaded = false;
      await act(async () => {
        loaded = await result.current.loadSavedSearch("saved-1");
      });

      expect(loaded).toBe(true);
      expect(result.current.currentSearchType).toBe("flight");
    });

    it("returns false when saved search not found", async () => {
      const { result } = renderHook(() => useSearchStore());

      let loaded = false;
      await act(async () => {
        loaded = await result.current.loadSavedSearch("non-existent");
      });

      expect(loaded).toBe(false);
    });

    it("duplicates current search", async () => {
      const { result } = renderHook(() => useSearchStore());

      await act(async () => {
        result.current.initializeSearch("flight");
        await useSearchParamsStore.getState().updateFlightParams({
          adults: 1,
          cabinClass: "economy",
          children: 0,
          departureDate: "2025-07-15",
          destination: "LAX",
          directOnly: false,
          excludedAirlines: [],
          infants: 0,
          origin: "NYC",
          preferredAirlines: [],
        });
      });

      let savedId: string | null = null;
      await act(async () => {
        savedId = await result.current.duplicateCurrentSearch("My Flight");
      });

      expect(savedId).toBeTruthy();
      const savedSearches = useSearchHistoryStore.getState().savedSearches;
      expect(savedSearches.some((s) => s.name === "My Flight")).toBe(true);
    });

    it("returns null when duplicating without search type", async () => {
      const { result } = renderHook(() => useSearchStore());

      let savedId: string | null = null;
      await act(async () => {
        savedId = await result.current.duplicateCurrentSearch("Test");
      });

      expect(savedId).toBeNull();
    });
  });

  describe("State Synchronization", () => {
    it("syncs search type across stores", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        useSearchParamsStore.getState().setSearchType("flight");
        result.current.syncStores();
      });

      expect(useSearchFiltersStore.getState().currentSearchType).toBe("flight");
    });
  });

  describe("Filter Integration", () => {
    it("applies filters and coordinates with filters store", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
        useSearchFiltersStore.getState().setActiveFilter("price_range", {
          max: 500,
          min: 100,
        });
      });

      // Verify filters are set and orchestrator reflects it
      expect(result.current.hasActiveFilters).toBe(true);
      expect(useSearchFiltersStore.getState().activeFilters).toHaveProperty(
        "price_range"
      );
    });
  });

  describe("Retry Operations", () => {
    it("retries last search when possible", async () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.initializeSearch("flight");
        const searchId = useSearchResultsStore.getState().startSearch("flight", {
          origin: "NYC",
        });
        useSearchResultsStore.getState().setSearchError(searchId, {
          code: "SEARCH_FAILED",
          message: "Network error",
          occurredAt: new Date().toISOString(),
          retryable: true,
        });
      });

      let retryId: string | null = null;
      await act(async () => {
        retryId = await result.current.retryLastSearch();
      });

      expect(retryId).toBeTruthy();
    });

    it("throws error when retry not possible", async () => {
      const { result } = renderHook(() => useSearchStore());

      await expect(
        act(async () => {
          await result.current.retryLastSearch();
        })
      ).rejects.toThrow("Cannot retry search");
    });
  });
});
