import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ValidatedFilterOption } from "@/stores/search-filters-store";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { resetSearchFiltersStore } from "./_shared";

describe("Search Filters Store - Presets", () => {
  beforeEach(() => {
    resetSearchFiltersStore();
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
});
