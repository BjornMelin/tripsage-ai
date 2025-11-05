/**
 * @fileoverview Shared test utilities and helpers for search filters store tests.
 */

import { act } from "@testing-library/react";
import { useSearchFiltersStore } from "@/stores/search-filters-store";

/**
 * Resets the search filters store to its initial state.
 */
export const resetSearchFiltersStore = (): void => {
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
};
