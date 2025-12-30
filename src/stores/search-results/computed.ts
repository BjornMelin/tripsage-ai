/**
 * @fileoverview Computed state helpers for the search results store.
 */

import type { SearchResults } from "@schemas/search";
import { createComputeFn } from "../middleware/computed";
import type { SearchResultsState } from "./types";

export const DEFAULT_PAGINATION: SearchResultsState["pagination"] = {
  currentPage: 1,
  hasNextPage: false,
  hasPreviousPage: false,
  resultsPerPage: 20,
  totalPages: 1,
  totalResults: 0,
};

function hasAnyResults(results: SearchResults): boolean {
  return Object.keys(results).some((key) => {
    const typeResults = results[key as keyof SearchResults];
    return Array.isArray(typeResults) && typeResults.length > 0;
  });
}

export const computeResultsState = createComputeFn<SearchResultsState>({
  canRetry: (state) =>
    state.status === "error" && (!state.error || state.error.retryable),
  hasResults: (state) => hasAnyResults(state.results),
  isEmptyResults: (state) =>
    state.status === "success" && !hasAnyResults(state.results),
  searchDuration: (state) => {
    if (state.currentContext?.completedAt) {
      const startTime = new Date(state.currentContext.startedAt).getTime();
      const endTime = new Date(state.currentContext.completedAt).getTime();
      return endTime - startTime;
    }
    return null;
  },
});
