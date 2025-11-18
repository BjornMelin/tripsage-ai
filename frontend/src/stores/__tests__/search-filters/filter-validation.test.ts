/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ValidatedFilterOption } from "@/stores/search-filters-store";
import { useSearchFiltersStore } from "@/stores/search-filters-store";

describe("Search Filters Store - Filter Validation", () => {
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

  describe("Filter Validation", () => {
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
});
