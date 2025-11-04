import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type {
  FilterValue,
  ValidatedFilterOption,
  ValidatedSortOption,
} from "../search-filters-store";
import { useSearchFiltersStore } from "../search-filters-store";

describe("Search Filters Store", () => {
  beforeEach(() => {
    act(() => {
      // Get current state to preserve any nested beforeEach setup
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
        currentSearchType: currentState.currentSearchType || null,
        filterPresets: [],
        filterValidationErrors: {},
        isApplyingFilters: false,
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
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
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

      expect(result.current.activeFilterCount).toBe(2);
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

    it.skip("provides current filters for active search type", () => {
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

  describe("Sort Options Management", () => {
    it("sets available sort options for search type", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const mockSortOptions: ValidatedSortOption[] = [
        {
          direction: "asc",
          field: "price",
          id: "price_low",
          isDefault: false,
          label: "Price: Low to High",
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
        direction: "asc",
        field: "totalDuration",
        id: "duration",
        isDefault: false,
        label: "Duration",
      };

      act(() => {
        result.current.addAvailableSortOption("flight", newSortOption);
      });

      const addedOption = result.current.availableSortOptions.flight.find(
        (o) => o.id === "duration"
      );
      expect(addedOption).toBeDefined();
      expect(addedOption).toMatchObject(newSortOption);
    });

    it("updates existing sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const initialSortOption: ValidatedSortOption = {
        direction: "asc",
        field: "price",
        id: "price_low",
        isDefault: false,
        label: "Price: Low to High",
      };

      act(() => {
        result.current.setAvailableSortOptions("flight", [initialSortOption]);
      });

      act(() => {
        result.current.updateAvailableSortOption("flight", "price_low", {
          description: "Sort by price ascending",
          label: "Price: Lowest First",
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
          direction: "asc",
          field: "price",
          id: "price_low",
          isDefault: false,
          label: "Price: Low to High",
        },
        {
          direction: "asc",
          field: "totalDuration",
          id: "duration",
          isDefault: false,
          label: "Duration",
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

  describe("Sort Management", () => {
    beforeEach(() => {
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
          currentSearchType: "flight",
        });
      });
    });

    it("sets active sort option", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      const sortOption: ValidatedSortOption = {
        direction: "asc",
        field: "price",
        id: "price_low",
        isDefault: false,
        label: "Price: Low to High",
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
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
          validation: { max: 10000, min: 0 },
        },
        {
          id: "required_field",
          label: "Required Field",
          required: true,
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
        max: 500,
        min: 100,
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
        max: 500,
        min: -10,
      });
      expect(isValidMin).toBe(false);

      // Test value above maximum
      const isValidMax = await result.current.validateFilter("price_range", {
        max: 15000,
        min: 100,
      });
      expect(isValidMax).toBe(false);
    });

    it("validates all active filters", async () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
            required_field: {
              appliedAt: new Date().toISOString(),
              filterId: "required_field",
              value: "valid value",
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
      await result.current.validateFilter("price_range", { max: 500, min: -10 });

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
          activeFilters: {
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
          currentSearchType: "flight",
        });
      });
    });

    it("saves filter preset", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      let presetId!: string | null;
      act(() => {
        presetId = result.current.saveFilterPreset(
          "Budget Flights",
          "Flights under $500"
        );
      });
      expect(presetId).toBeTruthy();
      expect(result.current.filterPresets).toHaveLength(1);

      const savedPreset = result.current.filterPresets[0];
      expect(savedPreset.name).toBe("Budget Flights");
      expect(savedPreset.description).toBe("Flights under $500");
      expect(savedPreset.searchType).toBe("flight");
      expect(savedPreset.filters).toHaveLength(1);
    });

    it("loads filter preset", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      // Save a preset first
      let presetId!: string | null;
      act(() => {
        presetId = result.current.saveFilterPreset("Budget Flights");
      });

      // Clear current filters
      act(() => {
        result.current.clearAllFilters();
      });

      expect(result.current.activeFilterCount).toBe(0);

      // Load the preset
      if (!presetId) {
        throw new Error("Preset ID is null");
      }
      let success = false;
      act(() => {
        success = result.current.loadFilterPreset(presetId as string);
      });
      expect(success).toBe(true);
      expect(result.current.activeFilterCount).toBe(1);
      expect(result.current.activePreset?.id).toBe(presetId);
    });

    it("updates filter preset", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      let presetId!: string | null;
      act(() => {
        presetId = result.current.saveFilterPreset("Budget Flights");
      });
      expect(presetId).toBeDefined();

      let success!: boolean;
      act(() => {
        success = result.current.updateFilterPreset(presetId as string, {
          description: "Updated description",
          name: "Cheap Flights",
        });
      });

      expect(success).toBe(true);

      const updatedPreset = result.current.filterPresets.find((p) => p.id === presetId);
      expect(updatedPreset?.name).toBe("Cheap Flights");
      expect(updatedPreset?.description).toBe("Updated description");
    });

    it("deletes filter preset", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      let presetId!: string | null;
      act(() => {
        presetId = result.current.saveFilterPreset("Budget Flights");
      });
      expect(presetId).toBeDefined();
      expect(result.current.filterPresets).toHaveLength(1);

      act(() => {
        result.current.deleteFilterPreset(presetId as string);
      });

      expect(result.current.filterPresets).toHaveLength(0);
    });

    it("duplicates filter preset", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      let originalPresetId!: string | null;
      act(() => {
        originalPresetId = result.current.saveFilterPreset("Budget Flights");
      });
      expect(originalPresetId).toBeDefined();

      let duplicatedPresetId!: string | null;
      act(() => {
        duplicatedPresetId = result.current.duplicateFilterPreset(
          originalPresetId as string,
          "Budget Flights Copy"
        );
      });

      expect(duplicatedPresetId).toBeTruthy();
      expect(result.current.filterPresets).toHaveLength(2);

      const duplicatedPreset = result.current.filterPresets.find(
        (p) => p.id === duplicatedPresetId
      );
      expect(duplicatedPreset?.name).toBe("Budget Flights Copy");
      expect(duplicatedPreset?.usageCount).toBe(0);
    });

    it("increments preset usage count", () => {
      const { result } = renderHook(() => useSearchFiltersStore());

      let presetId!: string | null;
      act(() => {
        presetId = result.current.saveFilterPreset("Budget Flights");
      });
      expect(presetId).toBeDefined();

      const originalPreset = result.current.filterPresets.find(
        (p) => p.id === presetId
      );
      expect(originalPreset?.usageCount).toBe(0);

      act(() => {
        result.current.incrementPresetUsage(presetId as string);
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
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
          currentSearchType: "flight",
          filterPresets: [
            {
              createdAt: new Date().toISOString(),
              filters: [],
              id: "preset-1",
              isBuiltIn: false,
              name: "Test Preset",
              searchType: "flight",
              usageCount: 0,
            },
          ],
        });
      });

      // Force re-render to ensure computed properties are updated
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
          category: "pricing",
          id: "price_range",
          label: "Price Range",
          required: false,
          type: "range",
        },
      ];

      // Set some state
      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            price_range: {
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
          availableFilters: {
            ...useSearchFiltersStore.getState().availableFilters,
            flight: mockFilters,
          },
          currentSearchType: "flight",
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
              appliedAt: new Date().toISOString(),
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
        });
      });

      expect(result.current.canClearFilters).toBe(true);

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {},
          activeSortOption: {
            direction: "asc",
            field: "price",
            id: "price_low",
            isDefault: false,
            label: "Price: Low to High",
          },
        });
      });

      expect(result.current.canClearFilters).toBe(true);
    });

    it("generates applied filter summary", () => {
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
          category: "airline",
          id: "airline",
          label: "Airlines",
          required: false,
          type: "multiselect",
        },
      ];

      act(() => {
        useSearchFiltersStore.setState({
          activeFilters: {
            airline: {
              appliedAt: new Date().toISOString(),
              displayValue: "American Airlines, United Airlines",
              filterId: "airline",
              value: ["AA", "UA"],
            },
            price_range: {
              appliedAt: new Date().toISOString(),
              displayValue: "$100 - $500",
              filterId: "price_range",
              value: { max: 500, min: 100 },
            },
          },
          availableFilters: {
            ...useSearchFiltersStore.getState().availableFilters,
            flight: mockFilters,
          },
          currentSearchType: "flight",
        });
      });

      const summary = result.current.appliedFilterSummary;
      expect(summary).toContain("Price Range: $100 - $500");
      expect(summary).toContain("Airlines: American Airlines, United Airlines");
    });
  });
});
