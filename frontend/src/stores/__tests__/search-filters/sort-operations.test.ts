/** @vitest-environment jsdom */

import type { ValidatedSortOption } from "@schemas/stores";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSearchFiltersStore } from "@/stores/search-filters-store";

describe("Search Filters Store - Sort Operations", () => {
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
});
