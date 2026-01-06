/**
 * @fileoverview Selector utilities for deriving current filter and sort options.
 */

import type { ValidatedFilterOption, ValidatedSortOption } from "@schemas/stores";
import type { SearchFiltersState } from "./types";

const EMPTY_FILTERS: ValidatedFilterOption[] = [];
const EMPTY_SORT_OPTIONS: ValidatedSortOption[] = [];

type CurrentConfigsState = Pick<
  SearchFiltersState,
  "availableFilters" | "availableSortOptions" | "currentSearchType"
>;

export function selectCurrentFilters(state: CurrentConfigsState) {
  return state.currentSearchType
    ? state.availableFilters[state.currentSearchType] || EMPTY_FILTERS
    : EMPTY_FILTERS;
}

export function selectCurrentSortOptions(state: CurrentConfigsState) {
  return state.currentSearchType
    ? state.availableSortOptions[state.currentSearchType] || EMPTY_SORT_OPTIONS
    : EMPTY_SORT_OPTIONS;
}
