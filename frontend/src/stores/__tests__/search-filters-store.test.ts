import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSearchFiltersStore } from "../search-filters-store";
import type {
  FilterValue,
  ValidatedFilterOption,
  ValidatedSortOption,
} from "../search-filters-store";

describe("Search Filters Store", () => {
  beforeEach(() => {
    act(() => {
      useSearchFiltersStore.setState({
        availableFilters: {
          flight: [],
          accommodation: [],
          activity: [],
          destination: [],
        },
        availableSortOptions: {
          flight: [],
          accommodation: [],
          activity: [],
          destination: [],
        },
        activeFilters: {},
        activeSortOption: null,
        currentSearchType: null,
        filterPresets: [],
        activePreset: null,
        isApplyingFilters: false,
        filterValidationErrors: {},
      });
    });
  });

  describe("Initial State", () => {
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

    it.skip("computes hasActiveFilters correctly", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      expect(result.current.hasActiveFilters).toBe(false);

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
          },
        });
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });

    it.skip("computes activeFilterCount correctly", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      expect(result.current.activeFilterCount).toBe(0);

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
            airline: {
              filterId: "airline",
              value: ["AA", "UA"],
              appliedAt: new Date().toISOString(),
            },
          },
        });
      });

      expect(result.current.activeFilterCount).toBe(2);
    });
  });

  describe("Search Type Management", () => {
    it("sets search type and initializes default sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockSortOptions: ValidatedSortOption[] = [
        {
          id: "relevance",
          label: "Relevance",
          field: "score",
          direction: "desc",
          isDefault: true,
        },
        {
          id: "price_low",
          label: "Price: Low to High",
          field: "price",
          direction: "asc",
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
        id: "preset-1",
        name: "Test Preset",
        searchType: "flight" as const,
        filters: [],
        isBuiltIn: false,
        createdAt: new Date().toISOString(),
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

    it.skip("provides current filters for active search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters: ValidatedFilterOption[] = [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
        },
        {
          id: "stops",
          label: "Number of Stops",
          type: "select",
          category: "routing",
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

      expect(result.current.currentFilters).toEqual(mockFilters);
    });
  });

  describe("Filter Configuration Management", () => {
    it("sets available filters for search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters: ValidatedFilterOption[] = [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
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
        id: "airline",
        label: "Airlines",
        type: "multiselect",
        category: "airline",
      };

      act(() => {
        result.current.addAvailableFilter("flight", newFilter);
      });

      expect(result.current.availableFilters.flight).toContain(newFilter);
    });

    it("updates existing filter configuration", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const initialFilter: ValidatedFilterOption = {
        id: "price_range",
        label: "Price Range",
        type: "range",
        category: "pricing",
      };

      act(() => {
        result.current.setAvailableFilters("flight", [initialFilter]);
      });

      act(() => {
        result.current.updateAvailableFilter("flight", "price_range", {
          label: "Updated Price Range",
          description: "Filter flights by price",
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
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
        },
        {
          id: "airline",
          label: "Airlines",
          type: "multiselect",
          category: "airline",
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

  describe("Sort Options Management", () => {
    it("sets available sort options for search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockSortOptions: ValidatedSortOption[] = [
        {
          id: "price_low",
          label: "Price: Low to High",
          field: "price",
          direction: "asc",
        },
      ];

      act(() => {
        result.current.setAvailableSortOptions("flight", mockSortOptions);
      });

      expect(result.current.availableSortOptions.flight).toEqual(mockSortOptions);
    });

    it("adds individual sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const newSortOption: ValidatedSortOption = {
        id: "duration",
        label: "Duration",
        field: "totalDuration",
        direction: "asc",
      };

      act(() => {
        result.current.addAvailableSortOption("flight", newSortOption);
      });

      expect(result.current.availableSortOptions.flight).toContain(newSortOption);
    });

    it("updates existing sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const initialSortOption: ValidatedSortOption = {
        id: "price_low",
        label: "Price: Low to High",
        field: "price",
        direction: "asc",
      };

      act(() => {
        result.current.setAvailableSortOptions("flight", [initialSortOption]);
      });

      act(() => {
        result.current.updateAvailableSortOption("flight", "price_low", {
          label: "Price: Lowest First",
          description: "Sort by price ascending",
        });
      });

      const updatedOption = result.current.availableSortOptions.flight.find(
        (o) => o.id === "price_low"
      );
      expect(updatedOption?.label).toBe("Price: Lowest First");
      expect(updatedOption?.description).toBe("Sort by price ascending");
    });

    it("removes sort option from search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const sortOptions: ValidatedSortOption[] = [
        {
          id: "price_low",
          label: "Price: Low to High",
          field: "price",
          direction: "asc",
        },
        {
          id: "duration",
          label: "Duration",
          field: "totalDuration",
          direction: "asc",
        },
      ];

      act(() => {
        result.current.setAvailableSortOptions("flight", sortOptions);
      });

      act(() => {
        result.current.removeAvailableSortOption("flight", "duration");
      });

      expect(result.current.availableSortOptions.flight).toHaveLength(1);
      expect(result.current.availableSortOptions.flight[0].id).toBe("price_low");
    });
  });

  describe("Active Filter Management", () => {
    beforeEach(() => {
      const mockFilters: ValidatedFilterOption[] = [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
          validation: { min: 0, max: 10000 },
        },
        {
          id: "airline",
          label: "Airlines",
          type: "multiselect",
          category: "airline",
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

    it("sets active filter with validation", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const filterValue: FilterValue = { min: 100, max: 500 };

      await act(async () => {
        const success = await result.current.setActiveFilter(
          "price_range",
          filterValue
        );
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
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
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

    it("updates active filter", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Set initial filter
      await act(async () => {
        await result.current.setActiveFilter("price_range", { min: 100, max: 500 });
      });

      // Update filter
      await act(async () => {
        const success = await result.current.updateActiveFilter("price_range", {
          min: 200,
          max: 800,
        });
        expect(success).toBe(true);
      });

      expect(result.current.activeFilters.price_range.value).toEqual({
        min: 200,
        max: 800,
      });
    });

    it("clears all filters", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
            airline: {
              filterId: "airline",
              value: ["AA", "UA"],
              appliedAt: new Date().toISOString(),
            },
          },
          activeSortOption: {
            id: "price_low",
            label: "Price: Low to High",
            field: "price",
            direction: "asc",
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
    });

    it("clears filters by category", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
            airline: {
              filterId: "airline",
              value: ["AA", "UA"],
              appliedAt: new Date().toISOString(),
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

    it("sets multiple filters at once", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const multipleFilters = {
        price_range: { min: 100, max: 500 },
        airline: ["AA", "UA"],
      };

      await act(async () => {
        const success = await result.current.setMultipleFilters(multipleFilters);
        expect(success).toBe(true);
      });

      expect(result.current.activeFilters.price_range).toBeDefined();
      expect(result.current.activeFilters.airline).toBeDefined();
      expect(result.current.activeFilterCount).toBe(2);
    });
  });

  describe("Sort Management", () => {
    beforeEach(() => {
      const mockSortOptions: ValidatedSortOption[] = [
        {
          id: "relevance",
          label: "Relevance",
          field: "score",
          direction: "desc",
          isDefault: true,
        },
        {
          id: "price_low",
          label: "Price: Low to High",
          field: "price",
          direction: "asc",
        },
      ];

      act(() => {
        useSearchFiltersStore.setState({
          availableSortOptions: {
            ...useSearchFiltersStore.getState().availableSortOptions,
            flight: mockSortOptions,
          },
          currentSearchType: "flight",
        });
      });
    });

    it("sets active sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const sortOption: ValidatedSortOption = {
        id: "price_low",
        label: "Price: Low to High",
        field: "price",
        direction: "asc",
      };

      act(() => {
        result.current.setActiveSortOption(sortOption);
      });

      expect(result.current.activeSortOption).toEqual(sortOption);
    });

    it("sets sort by ID", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        result.current.setSortById("price_low");
      });

      expect(result.current.activeSortOption?.id).toBe("price_low");
    });

    it("toggles sort direction", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        result.current.setSortById("price_low");
      });

      expect(result.current.activeSortOption?.direction).toBe("asc");

      act(() => {
        result.current.toggleSortDirection();
      });

      expect(result.current.activeSortOption?.direction).toBe("desc");

      act(() => {
        result.current.toggleSortDirection();
      });

      expect(result.current.activeSortOption?.direction).toBe("asc");
    });

    it("resets sort to default", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        result.current.setSortById("price_low");
      });

      expect(result.current.activeSortOption?.id).toBe("price_low");

      act(() => {
        result.current.resetSortToDefault();
      });

      expect(result.current.activeSortOption?.id).toBe("relevance");
      expect(result.current.activeSortOption?.isDefault).toBe(true);
    });
  });

  describe("Filter Validation", () => {
    beforeEach(() => {
      const mockFilters: ValidatedFilterOption[] = [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
          validation: { min: 0, max: 10000 },
        },
        {
          id: "required_field",
          label: "Required Field",
          type: "text",
          validation: { required: true },
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

    it("validates filter value successfully", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const isValid = await result.current.validateFilter("price_range", {
        min: 100,
        max: 500,
      });
      expect(isValid).toBe(true);
      expect(result.current.filterValidationErrors.price_range).toBeUndefined();
    });

    it("validates required field", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Test empty value for required field
      const isValid = await result.current.validateFilter("required_field", "");
      expect(isValid).toBe(false);
      expect(result.current.filterValidationErrors.required_field).toBe(
        "This filter is required"
      );
    });

    it("validates numeric range constraints", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Test value below minimum
      const isValidMin = await result.current.validateFilter("price_range", {
        min: -10,
        max: 500,
      });
      expect(isValidMin).toBe(false);

      // Test value above maximum
      const isValidMax = await result.current.validateFilter("price_range", {
        min: 100,
        max: 15000,
      });
      expect(isValidMax).toBe(false);
    });

    it("validates all active filters", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
            required_field: {
              filterId: "required_field",
              value: "valid value",
              appliedAt: new Date().toISOString(),
            },
          },
        });
      });

      const allValid = await result.current.validateAllFilters();
      expect(allValid).toBe(true);
    });

    it("gets validation error for specific filter", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      await result.current.validateFilter("required_field", "");

      const error = result.current.getFilterValidationError("required_field");
      expect(error).toBe("This filter is required");
    });

    it("clears validation errors", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Set some validation errors
      await result.current.validateFilter("required_field", "");
      expect(result.current.filterValidationErrors.required_field).toBeDefined();

      act(() => {
        result.current.clearValidationErrors();
      });

      expect(result.current.filterValidationErrors).toEqual({});
    });

    it("clears specific validation error", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Set validation errors for multiple filters
      await result.current.validateFilter("required_field", "");
      await result.current.validateFilter("price_range", { min: -10, max: 500 });

      expect(Object.keys(result.current.filterValidationErrors)).toHaveLength(2);

      act(() => {
        result.current.clearValidationError("required_field");
      });

      expect(result.current.filterValidationErrors.required_field).toBeUndefined();
      expect(result.current.filterValidationErrors.price_range).toBeDefined();
    });
  });

  describe("Filter Presets", () => {
    beforeEach(() => {
      act(() => {
        useSearchFiltersStore.setState({
          currentSearchType: "flight",
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
          },
          activeSortOption: {
            id: "price_low",
            label: "Price: Low to High",
            field: "price",
            direction: "asc",
          },
        });
      });
    });

    it("saves filter preset", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const presetId = await result.current.saveFilterPreset(
        "Budget Flights",
        "Flights under $500"
      );
      expect(presetId).toBeTruthy();
      expect(result.current.filterPresets).toHaveLength(1);

      const savedPreset = result.current.filterPresets[0];
      expect(savedPreset.name).toBe("Budget Flights");
      expect(savedPreset.description).toBe("Flights under $500");
      expect(savedPreset.searchType).toBe("flight");
      expect(savedPreset.filters).toHaveLength(1);
    });

    it("loads filter preset", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Save a preset first
      const presetId = await result.current.saveFilterPreset("Budget Flights");

      // Clear current filters
      act(() => {
        result.current.clearAllFilters();
      });

      expect(result.current.activeFilterCount).toBe(0);

      // Load the preset
      const success = await result.current.loadFilterPreset(presetId!);
      expect(success).toBe(true);
      expect(result.current.activeFilterCount).toBe(1);
      expect(result.current.activePreset?.id).toBe(presetId);
    });

    it("updates filter preset", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const presetId = await result.current.saveFilterPreset("Budget Flights");

      const success = await result.current.updateFilterPreset(presetId!, {
        name: "Cheap Flights",
        description: "Updated description",
      });

      expect(success).toBe(true);

      const updatedPreset = result.current.filterPresets.find((p) => p.id === presetId);
      expect(updatedPreset?.name).toBe("Cheap Flights");
      expect(updatedPreset?.description).toBe("Updated description");
    });

    it("deletes filter preset", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const presetId = await result.current.saveFilterPreset("Budget Flights");
      expect(result.current.filterPresets).toHaveLength(1);

      act(() => {
        result.current.deleteFilterPreset(presetId!);
      });

      expect(result.current.filterPresets).toHaveLength(0);
    });

    it("duplicates filter preset", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const originalPresetId = await result.current.saveFilterPreset("Budget Flights");

      const duplicatedPresetId = await result.current.duplicateFilterPreset(
        originalPresetId!,
        "Budget Flights Copy"
      );

      expect(duplicatedPresetId).toBeTruthy();
      expect(result.current.filterPresets).toHaveLength(2);

      const duplicatedPreset = result.current.filterPresets.find(
        (p) => p.id === duplicatedPresetId
      );
      expect(duplicatedPreset?.name).toBe("Budget Flights Copy");
      expect(duplicatedPreset?.usageCount).toBe(0);
    });

    it("increments preset usage count", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const presetId = await result.current.saveFilterPreset("Budget Flights");

      const originalPreset = result.current.filterPresets.find(
        (p) => p.id === presetId
      );
      expect(originalPreset?.usageCount).toBe(0);

      act(() => {
        result.current.incrementPresetUsage(presetId!);
      });

      const updatedPreset = result.current.filterPresets.find((p) => p.id === presetId);
      expect(updatedPreset?.usageCount).toBe(1);
    });
  });

  describe("Utility Actions", () => {
    it("resets all state", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Set some state
      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
          },
          currentSearchType: "flight",
          filterPresets: [
            {
              id: "preset-1",
              name: "Test Preset",
              searchType: "flight",
              filters: [],
              isBuiltIn: false,
              createdAt: new Date().toISOString(),
              usageCount: 0,
            },
          ],
        });
      });

      expect(result.current.activeFilterCount).toBeGreaterThan(0);
      expect(result.current.currentSearchType).toBe("flight");
      expect(result.current.filterPresets).toHaveLength(1);

      act(() => {
        result.current.reset();
      });

      expect(result.current.activeFilters).toEqual({});
      expect(result.current.currentSearchType).toBeNull();
      expect(result.current.filterPresets).toEqual([]);
    });

    it("soft resets active state only", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters: ValidatedFilterOption[] = [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
        },
      ];

      // Set some state
      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
          },
          currentSearchType: "flight",
          availableFilters: {
            ...useSearchFiltersStore.getState().availableFilters,
            flight: mockFilters,
          },
        });
      });

      expect(result.current.activeFilterCount).toBeGreaterThan(0);
      expect(result.current.availableFilters.flight).toEqual(mockFilters);

      act(() => {
        result.current.softReset();
      });

      expect(result.current.activeFilters).toEqual({});
      expect(result.current.availableFilters.flight).toEqual(mockFilters); // Preserved
    });
  });

  describe.skip("Computed Properties", () => {
    it("computes canClearFilters correctly", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      expect(result.current.canClearFilters).toBe(false);

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              appliedAt: new Date().toISOString(),
            },
          },
        });
      });

      expect(result.current.canClearFilters).toBe(true);

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {},
          activeSortOption: {
            id: "price_low",
            label: "Price: Low to High",
            field: "price",
            direction: "asc",
          },
        });
      });

      expect(result.current.canClearFilters).toBe(true);
    });

    it("generates applied filter summary", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockFilters: ValidatedFilterOption[] = [
        {
          id: "price_range",
          label: "Price Range",
          type: "range",
          category: "pricing",
        },
        {
          id: "airline",
          label: "Airlines",
          type: "multiselect",
          category: "airline",
        },
      ];

      act(() => {
        useSearchFiltersStore.setState({
          availableFilters: {
            ...useSearchFiltersStore.getState().availableFilters,
            flight: mockFilters,
          },
          currentSearchType: "flight",
          activeFilters: {
            price_range: {
              filterId: "price_range",
              value: { min: 100, max: 500 },
              displayValue: "$100 - $500",
              appliedAt: new Date().toISOString(),
            },
            airline: {
              filterId: "airline",
              value: ["AA", "UA"],
              displayValue: "American Airlines, United Airlines",
              appliedAt: new Date().toISOString(),
            },
          },
        });
      });

      const summary = result.current.appliedFilterSummary;
      expect(summary).toContain("Price Range: $100 - $500");
      expect(summary).toContain("Airlines: American Airlines, United Airlines");
    });
  });
});
