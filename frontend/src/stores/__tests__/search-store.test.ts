import type { AccommodationSearchParams, FlightSearchParams } from "@/types/search";
import { act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";
import { useSearchStore } from "../search-store";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  persist: (fn) => fn,
}));

describe("useSearchStore", () => {
  // Clear the store before each test
  beforeEach(() => {
    act(() => {
      useSearchStore.setState({
        currentSearchType: null,
        flightParams: {},
        accommodationParams: {},
        activityParams: {},
        results: {},
        isLoading: false,
        error: null,
        availableFilters: {
          flight: [],
          accommodation: [],
          activity: [],
        },
        activeFilters: {},
        availableSortOptions: {
          flight: [],
          accommodation: [],
          activity: [],
        },
        activeSortOption: null,
        savedSearches: [],
        recentSearches: [],
      });
    });
  });

  describe("Search Type & Parameters", () => {
    it("initializes with default values", () => {
      const { result } = renderHook(() => useSearchStore());

      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.flightParams).toEqual({});
      expect(result.current.accommodationParams).toEqual({});
      expect(result.current.activityParams).toEqual({});
      expect(result.current.results).toEqual({});
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("sets search type and initializes default params", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.flightParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
      });

      // Change to accommodation type
      act(() => {
        result.current.setSearchType("accommodation");
      });

      expect(result.current.currentSearchType).toBe("accommodation");
      expect(result.current.accommodationParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        rooms: 1,
      });
    });

    it("updates flight search parameters", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setSearchType("flight");
      });

      const flightParams: Partial<FlightSearchParams> = {
        origin: "NYC",
        destination: "LAX",
        startDate: "2025-06-01",
        endDate: "2025-06-08",
        cabinClass: "business",
      };

      act(() => {
        result.current.updateFlightParams(flightParams);
      });

      expect(result.current.flightParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "business",
        directOnly: false,
        origin: "NYC",
        destination: "LAX",
        startDate: "2025-06-01",
        endDate: "2025-06-08",
      });
    });

    it("updates accommodation search parameters", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setSearchType("accommodation");
      });

      const accommodationParams: Partial<AccommodationSearchParams> = {
        destination: "Paris",
        startDate: "2025-07-01",
        endDate: "2025-07-08",
        rooms: 2,
        amenities: ["wifi", "pool"],
      };

      act(() => {
        result.current.updateAccommodationParams(accommodationParams);
      });

      expect(result.current.accommodationParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        rooms: 2,
        destination: "Paris",
        startDate: "2025-07-01",
        endDate: "2025-07-08",
        amenities: ["wifi", "pool"],
      });
    });

    it("resets search parameters", () => {
      const { result } = renderHook(() => useSearchStore());

      // Set up flight params
      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
      });

      // Reset flight params
      act(() => {
        result.current.resetParams("flight");
      });

      expect(result.current.flightParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
      });

      // Set up and reset all params
      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
        result.current.setSearchType("accommodation");
        result.current.updateAccommodationParams({
          destination: "Paris",
        });
        result.current.resetParams();
      });

      expect(result.current.flightParams).toEqual({});
      expect(result.current.accommodationParams).toEqual({});
    });

    it("returns the correct current parameters", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
      });

      expect(result.current.currentParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
        origin: "NYC",
        destination: "LAX",
      });

      act(() => {
        result.current.setSearchType("accommodation");
      });

      expect(result.current.currentParams).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        rooms: 1,
      });
    });
  });

  describe("Search Results", () => {
    it("sets and clears search results", () => {
      const { result } = renderHook(() => useSearchStore());

      const mockResults = {
        flights: [
          {
            id: "flight-1",
            airline: "Test Airlines",
            flightNumber: "TA123",
            origin: "NYC",
            destination: "LAX",
            departureTime: "2025-06-01T08:00:00Z",
            arrivalTime: "2025-06-01T11:00:00Z",
            duration: 3 * 60,
            stops: 0,
            price: 299.99,
            cabinClass: "economy",
            seatsAvailable: 10,
          },
        ],
      };

      act(() => {
        result.current.setResults(mockResults);
      });

      expect(result.current.results).toEqual(mockResults);
      expect(result.current.isLoading).toBe(false);

      act(() => {
        result.current.clearResults();
      });

      expect(result.current.results).toEqual({});
      expect(result.current.error).toBeNull();
    });

    it("sets loading state", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setIsLoading(true);
      });

      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.setIsLoading(false);
      });

      expect(result.current.isLoading).toBe(false);
    });

    it("sets error state", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setError("Test error message");
      });

      expect(result.current.error).toBe("Test error message");
      expect(result.current.isLoading).toBe(false);

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("Filters and Sorting", () => {
    it("sets available filters", () => {
      const { result } = renderHook(() => useSearchStore());

      const mockFilters = [
        {
          id: "airline",
          label: "Airline",
          type: "checkbox" as const,
          options: [
            { label: "Test Airlines", value: "test-airlines", count: 5 },
            { label: "Mock Airways", value: "mock-airways", count: 3 },
          ],
        },
      ];

      act(() => {
        result.current.setAvailableFilters("flight", mockFilters);
      });

      expect(result.current.availableFilters.flight).toEqual(mockFilters);
    });

    it("sets active filters", () => {
      const { result } = renderHook(() => useSearchStore());

      act(() => {
        result.current.setActiveFilter("airline", ["test-airlines"]);
      });

      expect(result.current.activeFilters).toEqual({
        airline: ["test-airlines"],
      });

      act(() => {
        result.current.setActiveFilter("price", { min: 100, max: 500 });
      });

      expect(result.current.activeFilters).toEqual({
        airline: ["test-airlines"],
        price: { min: 100, max: 500 },
      });

      act(() => {
        result.current.clearFilters();
      });

      expect(result.current.activeFilters).toEqual({});
    });

    it("sets available sort options", () => {
      const { result } = renderHook(() => useSearchStore());

      const mockSortOptions = [
        {
          id: "price",
          label: "Price",
          value: "price",
          direction: "asc" as const,
        },
        {
          id: "duration",
          label: "Duration",
          value: "duration",
          direction: "asc" as const,
        },
      ];

      act(() => {
        result.current.setAvailableSortOptions("flight", mockSortOptions);
      });

      expect(result.current.availableSortOptions.flight).toEqual(mockSortOptions);
    });

    it("sets active sort option", () => {
      const { result } = renderHook(() => useSearchStore());

      const mockSortOption = {
        id: "price",
        label: "Price",
        value: "price",
        direction: "asc" as const,
      };

      act(() => {
        result.current.setActiveSortOption(mockSortOption);
      });

      expect(result.current.activeSortOption).toEqual(mockSortOption);

      act(() => {
        result.current.setActiveSortOption(null);
      });

      expect(result.current.activeSortOption).toBeNull();
    });
  });

  describe("Saved and Recent Searches", () => {
    it("saves a search", () => {
      const { result } = renderHook(() => useSearchStore());

      // Set up search parameters
      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
          startDate: "2025-06-01",
          endDate: "2025-06-08",
        });
      });

      // Save the search
      act(() => {
        result.current.saveSearch("NYC to LAX Trip");
      });

      expect(result.current.savedSearches.length).toBe(1);
      expect(result.current.savedSearches[0].name).toBe("NYC to LAX Trip");
      expect(result.current.savedSearches[0].type).toBe("flight");
      expect(result.current.savedSearches[0].params).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
        origin: "NYC",
        destination: "LAX",
        startDate: "2025-06-01",
        endDate: "2025-06-08",
      });
    });

    it("deletes a saved search", () => {
      const { result } = renderHook(() => useSearchStore());

      // Set up and save a search
      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
        result.current.saveSearch("NYC to LAX Trip");
      });

      const savedSearchId = result.current.savedSearches[0].id;

      // Delete the search
      act(() => {
        result.current.deleteSearch(savedSearchId);
      });

      expect(result.current.savedSearches.length).toBe(0);
    });

    it("adds a recent search", () => {
      const { result } = renderHook(() => useSearchStore());

      // Set up search parameters
      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
          startDate: "2025-06-01",
          endDate: "2025-06-08",
        });
      });

      // Add to recent searches
      act(() => {
        result.current.addRecentSearch();
      });

      expect(result.current.recentSearches.length).toBe(1);
      expect(result.current.recentSearches[0].type).toBe("flight");
      expect(result.current.recentSearches[0].params).toEqual({
        adults: 1,
        children: 0,
        infants: 0,
        cabinClass: "economy",
        directOnly: false,
        origin: "NYC",
        destination: "LAX",
        startDate: "2025-06-01",
        endDate: "2025-06-08",
      });
    });

    it("limits recent searches to 10", () => {
      const { result } = renderHook(() => useSearchStore());

      // Add 11 recent searches
      for (let i = 0; i < 11; i++) {
        act(() => {
          result.current.setSearchType("flight");
          result.current.updateFlightParams({
            origin: "NYC",
            destination: `DEST-${i}`,
          });
          result.current.addRecentSearch();
        });
      }

      expect(result.current.recentSearches.length).toBe(10);
      // The most recent one should be first
      expect(result.current.recentSearches[0].params.destination).toBe("DEST-10");
    });

    it("clears recent searches", () => {
      const { result } = renderHook(() => useSearchStore());

      // Add a recent search
      act(() => {
        result.current.setSearchType("flight");
        result.current.updateFlightParams({
          origin: "NYC",
          destination: "LAX",
        });
        result.current.addRecentSearch();
      });

      // Clear recent searches
      act(() => {
        result.current.clearRecentSearches();
      });

      expect(result.current.recentSearches.length).toBe(0);
    });
  });
});
