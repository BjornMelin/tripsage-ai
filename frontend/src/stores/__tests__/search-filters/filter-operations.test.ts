/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  FilterValue,
  ValidatedFilterOption,
  ValidatedSortOption,
} from "@/stores/search-filters-store";
import { useSearchFiltersStore } from "@/stores/search-filters-store";

describe("Search Filters Store - Filter Operations", () => {
  beforeEach(() => {
    act(() => {
      const currentState = useSearchFiltersStore.getState();
      useSearchFiltersStore.setState({
        activeFilters: {},
        activePreset: null,
        activeSortOption: null,
        availableFilters: {
          accommodation: currentState.availableFilters?.accommodation || [],
          activity: currentState.availableFilters?.activity || [],
          destination: currentState.availableFilters?.destination || [],
          flight: currentState.availableFilters?.flight || [],
        },
        availableSortOptions: {
          accommodation: currentState.availableSortOptions?.accommodation || [],
          activity: currentState.availableSortOptions?.activity || [],
          destination: currentState.availableSortOptions?.destination || [],
          flight: currentState.availableSortOptions?.flight || [],
        },
        currentSearchType: null,
        filterPresets: [],
        filterValidationErrors: {},
        isApplyingFilters: false,
      });
    });
  });

  describe("Search Type Management", () => {
    it("sets search type and initializes default sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockSortOptions: ValidatedSortOption[] = [
        {
          direction: "desc",
          field: "score",
          id: "relevance",
          isDefault: true,
          label: "Relevance",
        },
        {
          direction: "asc",
          field: "price",
          id: "price_low",
          isDefault: false,
          label: "Price: Low to High",
        },
      ];

      act(() => {
        useSearchFiltersStore.setState({
          availableSortOptions: {
            ...useSearchFiltersStore.getState().availableSortOptions,
            flight: mockSortOptions,
          },
        });
      });

      act(() => {
        result.current.setSearchType("flight");
      });

      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.activeSortOption).toEqual(mockSortOptions[0]);
    });

    it("clears active preset when changing search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockPreset = {
        createdAt: new Date().toISOString(),
        filters: [],
        id: "preset-1",
        isBuiltIn: false,
        name: "Test Preset",
        searchType: "flight" as const,
        usageCount: 0,
      };

      act(() => {
        useSearchFiltersStore.setState({
          activePreset: mockPreset,
          currentSearchType: "flight",
        });
      });

      expect(result.current.activePreset).toEqual(mockPreset);

      act(() => {
        result.current.setSearchType("accommodation");
      });

      expect(result.current.activePreset).toBeNull();
    });

    it("provides current filters for active search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters: ValidatedFilterOption[] = [
        {
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
        },
        {
          category: "routing",
          id: "stops",
          label: "Number of Stops",
          required: false,
          type: "select",
        },
      ];

      act(() => {
        result.current.setAvailableFilters("flight", mockFilters);
        result.current.setSearchType("flight");
      });

      expect(result.current.currentFilters).toEqual(mockFilters);
    });
  });

  describe("Filter Configuration Management", () => {
    it("sets available filters for search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters: ValidatedFilterOption[] = [
        {
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
        },
      ];

      act(() => {
        result.current.setAvailableFilters("flight", mockFilters);
      });

      expect(result.current.availableFilters.flight).toEqual(mockFilters);
    });

    it("adds individual filter to search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const newFilter: ValidatedFilterOption = {
        category: "airline",
        id: "airline",
        label: "Airlines",
        required: false,
        type: "multiselect",
      };

      act(() => {
        result.current.addAvailableFilter("flight", newFilter);
      });

      const addedFilter = result.current.availableFilters.flight.find(
        (f) => f.id === "airline"
      );
      expect(addedFilter).toBeDefined();
      expect(addedFilter).toMatchObject(newFilter);
    });

    it("updates existing filter configuration", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const initialFilter: ValidatedFilterOption = {
        category: "pricing",
        id: "price_range",
        label: "Price Range",
        required: false,
        type: "range",
      };

      act(() => {
        result.current.setAvailableFilters("flight", [initialFilter]);
      });

      act(() => {
        result.current.updateAvailableFilter("flight", "price_range", {
          description: "Filter flights by price",
          label: "Updated Price Range",
        });
      });

      const updatedFilter = result.current.availableFilters.flight.find(
        (f) => f.id === "price_range"
      );
      expect(updatedFilter?.label).toBe("Updated Price Range");
      expect(updatedFilter?.description).toBe("Filter flights by price");
    });

    it("removes filter from search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const filters: ValidatedFilterOption[] = [
        {
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
        },
        {
          category: "airline",
          id: "airline",
          label: "Airlines",
          required: false,
          type: "multiselect",
        },
      ];

      act(() => {
        result.current.setAvailableFilters("flight", filters);
      });

      act(() => {
        result.current.removeAvailableFilter("flight", "airline");
      });

      expect(result.current.availableFilters.flight).toHaveLength(1);
      expect(result.current.availableFilters.flight[0].id).toBe("price_range");
    });
  });

  describe("Active Filter Management", () => {
    beforeEach(() => {
      const mockFilters: ValidatedFilterOption[] = [
        {
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
          validation: { max: 10000, min: 0 },
        },
        {
          category: "airline",
          id: "airline",
          label: "Airlines",
          required: false,
          type: "multiselect",
        },
      ];

      act(() => {
        useSearchFiltersStore.setState({
          availableFilters: {
            ...useSearchFiltersStore.getState().availableFilters,
            flight: mockFilters,
          },
          currentSearchType: "flight",
        });
      });
    });

    it("sets active filter with validation", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const filterValue: FilterValue = { max: 500, min: 100 };

      // First set the search type to ensure current filters are available
      act(() => {
        result.current.setSearchType("flight");
      });

      act(() => {
        const success = result.current.setActiveFilter("price_range", filterValue);
        expect(success).toBe(true);
      });

      expect(result.current.activeFilters.price_range).toBeDefined();
      expect(result.current.activeFilters.price_range.value).toEqual(filterValue);
      expect(result.current.activeFilters.price_range.filterId).toBe("price_range");
    });

    it("removes active filter", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
        });
      });

      expect(result.current.activeFilters.price_range).toBeDefined();

      act(() => {
        result.current.removeActiveFilter("price_range");
      });

      expect(result.current.activeFilters.price_range).toBeUndefined();
    });

    it("updates active filter", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // First set the search type to ensure current filters are available
      act(() => {
        result.current.setSearchType("flight");
      });

      // Set initial filter
      act(() => {
        result.current.setActiveFilter("price_range", { max: 500, min: 100 });
      });

      // Update filter
      act(() => {
        const success = result.current.updateActiveFilter("price_range", {
          max: 800,
          min: 200,
        });
        expect(success).toBe(true);
      });

      expect(result.current.activeFilters.price_range.value).toEqual({
        max: 800,
        min: 200,
      });
    });

    it("clears all filters", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            airline: {
              appliedAt: new Date().toISOString(),
              filterId: "airline",
              value: ["AA", "UA"],
            },
            price_range: {
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
          activeSortOption: {
            direction: "asc",
            field: "price",
            id: "price_low",
            isDefault: false,
            label: "Price: Low to High",
          },
        });
      });

      expect(Object.keys(result.current.activeFilters)).toHaveLength(2);
      expect(result.current.activeSortOption).not.toBeNull();

      act(() => {
        result.current.clearAllFilters();
      });

      expect(result.current.activeFilters).toEqual({});
      expect(result.current.activeSortOption).toBeNull();
      // clearAllFilters does not clear currentSearchType
    });

    it("clears filters by category", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            airline: {
              appliedAt: new Date().toISOString(),
              filterId: "airline",
              value: ["AA", "UA"],
            },
            price_range: {
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
        });
      });

      act(() => {
        result.current.clearFiltersByCategory("pricing");
      });

      expect(result.current.activeFilters.price_range).toBeUndefined();
      expect(result.current.activeFilters.airline).toBeDefined();
    });

    it("sets multiple filters at once", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // First set the search type to ensure current filters are available
      act(() => {
        result.current.setSearchType("flight");
      });

      const multipleFilters = {
        airline: ["AA", "UA"],
        price_range: { max: 500, min: 100 },
      };

      act(() => {
        const success = result.current.setMultipleFilters(multipleFilters);
        expect(success).toBe(true);
      });

      expect(result.current.activeFilters.price_range).toBeDefined();
      expect(result.current.activeFilters.airline).toBeDefined();
      expect(result.current.activeFilterCount).toBe(2);
    });
  });

  describe("Initial State", () => {
    beforeEach(() => {
      act(() => {
        const currentState = useSearchFiltersStore.getState();
        useSearchFiltersStore.setState({
          activeFilters: {},
          activePreset: null,
          activeSortOption: null,
          availableFilters: {
            accommodation: currentState.availableFilters?.accommodation || [],
            activity: currentState.availableFilters?.activity || [],
            destination: currentState.availableFilters?.destination || [],
            flight: currentState.availableFilters?.flight || [],
          },
          availableSortOptions: {
            accommodation: currentState.availableSortOptions?.accommodation || [],
            activity: currentState.availableSortOptions?.activity || [],
            destination: currentState.availableSortOptions?.destination || [],
            flight: currentState.availableSortOptions?.flight || [],
          },
          currentSearchType: null,
          filterPresets: [],
          filterValidationErrors: {},
          isApplyingFilters: false,
        });
      });
    });

    it("initializes with correct default values", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      expect(result.current.activeFilters).toEqual({});
      expect(result.current.activeSortOption).toBeNull();
      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.filterPresets).toEqual([]);
      expect(result.current.activePreset).toBeNull();
      expect(result.current.isApplyingFilters).toBe(false);
      expect(result.current.filterValidationErrors).toEqual({});
    });

    it("computes hasActiveFilters correctly", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      expect(result.current.hasActiveFilters).toBe(false);

      // Set up filters first
      act(() => {
        result.current.setSearchType("flight");
        result.current.setAvailableFilters("flight", [
          {
            category: "pricing",
            id: "price_range",
            label: "Price Range",
            required: false,
            type: "range",
            validation: { max: 10000, min: 0 },
          },
        ]);
      });

      act(() => {
        result.current.setActiveFilter("price_range", { max: 500, min: 100 });
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("computes activeFilterCount correctly", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      expect(result.current.activeFilterCount).toBe(0);

      // Set up filters first
      act(() => {
        result.current.setSearchType("flight");
        result.current.setAvailableFilters("flight", [
          {
            category: "pricing",
            id: "price_range",
            label: "Price Range",
            required: false,
            type: "range",
            validation: { max: 10000, min: 0 },
          },
          {
            category: "airline",
            id: "airline",
            label: "Airlines",
            required: false,
            type: "multiselect",
          },
        ]);
      });

      act(() => {
        result.current.setActiveFilter("airline", ["AA", "UA"]);
        result.current.setActiveFilter("price_range", { max: 500, min: 100 });
      });

      expect(result.current.activeFilterCount).toBe(2);
    });
  });
});
