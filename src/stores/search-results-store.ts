/**
 * @fileoverview Zustand store for managing search results, pagination, and performance metrics.
 */

import type { SearchType } from "@schemas/search";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { generateId, getCurrentTimestamp } from "./helpers";
import { withComputed } from "./middleware/computed";
import { computeResultsState } from "./search-results/computed";
import { createSearchResultsCoreSlice } from "./search-results/slices/core";
import { createSearchResultsHistorySlice } from "./search-results/slices/history";
import { createSearchResultsPaginationSlice } from "./search-results/slices/pagination";
import type {
  SearchResultsState,
  SearchResultsStoreDeps,
} from "./search-results/types";

const logger = createStoreLogger({ storeName: "search-results" });

const deps: SearchResultsStoreDeps = {
  generateSearchId: () => `search_${generateId(12)}`,
  logger,
  nowIso: getCurrentTimestamp,
};

export const useSearchResultsStore = create<SearchResultsState>()(
  devtools(
    persist(
      withComputed({ compute: computeResultsState }, (...args) => ({
        ...createSearchResultsCoreSlice(deps)(...args),
        ...createSearchResultsHistorySlice(...args),
        ...createSearchResultsPaginationSlice(...args),
      })),
      {
        name: "search-results-storage",
        partialize: (state) => ({
          performanceHistory: state.performanceHistory.slice(-30),
          resultsBySearch: Object.fromEntries(
            Object.entries(state.resultsBySearch).slice(-10)
          ),
          searchHistory: state.searchHistory.slice(-20),
        }),
      }
    ),
    { name: "SearchResultsStore" }
  )
);

// Utility selectors for common use cases
export const useSearchStatus = () => useSearchResultsStore((state) => state.status);
export const useSearchResults = () => useSearchResultsStore((state) => state.results);
export const useIsSearching = () => useSearchResultsStore((state) => state.isSearching);
export const useSearchProgress = () =>
  useSearchResultsStore((state) => state.searchProgress);
export const useSearchError = () => useSearchResultsStore((state) => state.error);
export const useSearchPagination = () =>
  useSearchResultsStore((state) => state.pagination);
export const useSearchMetrics = () => useSearchResultsStore((state) => state.metrics);
export const useSearchHistory = (searchType?: SearchType, limit?: number) =>
  useSearchResultsStore((state) => state.getRecentSearches(searchType, limit));
export const useHasSearchResults = () =>
  useSearchResultsStore((state) => state.hasResults);
export const useCanRetrySearch = () => useSearchResultsStore((state) => state.canRetry);
