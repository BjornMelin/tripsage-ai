import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { ValidatedSortOption } from "@/stores/search-filters-store";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { resetSearchFiltersStore } from "./_shared";

describe("Search Filters Store - Sort Operations", () => {
  beforeEach(() => {
    resetSearchFiltersStore();
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
