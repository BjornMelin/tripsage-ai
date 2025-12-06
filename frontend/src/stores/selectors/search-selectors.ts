/**
 * @fileoverview Cross-store selectors for search domain.
 *
 * Provides unified access to search state across params, filters, results, and history stores.
 */

"use client";

import type { SearchResults, SearchType } from "@schemas/search";
import { useSearchFiltersStore } from "../search-filters-store";
import { useSearchHistoryStore } from "../search-history-store";
import { useSearchParamsStore } from "../search-params-store";
import { useSearchResultsStore } from "../search-results-store";

/** Get result array length for a search type */
const getResultCount = (results: SearchResults, searchType: SearchType): number => {
  switch (searchType) {
    case "flight":
      return results.flights?.length ?? 0;
    case "accommodation":
      return results.accommodations?.length ?? 0;
    case "activity":
      return results.activities?.length ?? 0;
    case "destination":
      return results.destinations?.length ?? 0;
    default:
      return 0;
  }
};

type SearchResultArray<T extends SearchType> = T extends "flight"
  ? NonNullable<SearchResults["flights"]>
  : T extends "accommodation"
    ? NonNullable<SearchResults["accommodations"]>
    : T extends "activity"
      ? NonNullable<SearchResults["activities"]>
      : T extends "destination"
        ? NonNullable<SearchResults["destinations"]>
        : never;

/** Get result array for a search type */
const getResultsForType = <T extends SearchType>(
  results: SearchResults,
  searchType: T
): SearchResultArray<T> => {
  switch (searchType) {
    case "flight":
      return (results.flights ?? []) as SearchResultArray<T>;
    case "accommodation":
      return (results.accommodations ?? []) as SearchResultArray<T>;
    case "activity":
      return (results.activities ?? []) as SearchResultArray<T>;
    case "destination":
      return (results.destinations ?? []) as SearchResultArray<T>;
    default: {
      // Exhaustive check: ensure all SearchType cases are handled
      const _exhaustiveCheck: never = searchType;
      return _exhaustiveCheck;
    }
  }
};

/**
 * Combined search state summary for display.
 */
export const useSearchSummary = () => {
  const searchType = useSearchParamsStore((s) => s.currentSearchType);
  const hasValidParams = useSearchParamsStore((s) => s.hasValidParams);
  const activeFilterCount = useSearchFiltersStore((s) => s.activeFilterCount);
  const isSearching = useSearchResultsStore((s) => s.isSearching);
  const hasResults = useSearchResultsStore((s) => s.hasResults);
  const results = useSearchResultsStore((s) => s.results);

  const resultCount = searchType ? getResultCount(results, searchType) : 0;

  return {
    activeFilterCount,
    hasResults,
    hasValidParams,
    isSearching,
    resultCount,
    searchType,
  };
};

/**
 * Active filters summary for display.
 */
export const useActiveFiltersSummary = () => {
  const summary = useSearchFiltersStore((s) => s.appliedFilterSummary);
  const count = useSearchFiltersStore((s) => s.activeFilterCount);
  const hasFilters = useSearchFiltersStore((s) => s.hasActiveFilters);

  return { count, hasFilters, summary };
};

/**
 * Search validation state across stores.
 */
export const useSearchValidation = () => {
  const isParamsValid = useSearchParamsStore((s) => s.hasValidParams);
  const paramsValidating = useSearchParamsStore((s) => s.isValidating);
  const paramsErrors = useSearchParamsStore((s) => s.validationErrors);
  const filterErrors = useSearchFiltersStore((s) => s.filterValidationErrors);

  return {
    filterErrors,
    isValid: isParamsValid && Object.keys(filterErrors).length === 0,
    paramsErrors,
    paramsValidating,
  };
};

/**
 * Combined search history context.
 */
export const useSearchHistorySummary = () => {
  const totalRecent = useSearchHistoryStore((s) => s.recentSearches.length);
  const totalSaved = useSearchHistoryStore((s) => s.totalSavedSearches);
  const favoriteCount = useSearchHistoryStore((s) => s.favoriteSearches.length);
  const collectionCount = useSearchHistoryStore((s) => s.searchCollections.length);

  return { collectionCount, favoriteCount, totalRecent, totalSaved };
};

/**
 * Search results context for a specific type.
 */
export const useSearchResultsByType = (searchType: SearchType | null) => {
  const allResults = useSearchResultsStore((s) => s.results);
  const metrics = useSearchResultsStore((s) => s.metrics);
  const isSearching = useSearchResultsStore((s) => s.isSearching);
  const error = useSearchResultsStore((s) => s.error);

  const results = searchType ? getResultsForType(allResults, searchType) : [];

  return {
    count: results.length,
    error,
    isSearching,
    metrics,
    results,
  };
};

/**
 * Search suggestions for autocomplete.
 */
export const useSearchSuggestionsSelector = (
  query: string,
  searchType?: SearchType,
  limit = 10
) => {
  const suggestions = useSearchHistoryStore((s) =>
    s.getSearchSuggestions(query, searchType, limit)
  );

  return { suggestions };
};
