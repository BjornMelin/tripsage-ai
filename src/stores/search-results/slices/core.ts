/**
 * @fileoverview Core slice for the search results store (state + lifecycle).
 */

import type { SearchResults, SearchType } from "@schemas/search";
import type { ErrorDetails, SearchContext, SearchMetrics } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { DEFAULT_PAGINATION } from "../computed";
import type { SearchResultsState, SearchResultsStoreDeps } from "../types";

const assertNever = (value: never): never => {
  throw new Error(`Unhandled search type: ${value satisfies SearchType}`);
};

type SearchResultsCoreSlice = Pick<
  SearchResultsState,
  | "appendResults"
  | "cancelSearch"
  | "canRetry"
  | "clearAllResults"
  | "clearError"
  | "clearErrorHistory"
  | "clearResults"
  | "completeSearch"
  | "currentContext"
  | "currentSearchId"
  | "currentSearchType"
  | "error"
  | "errorHistory"
  | "hasResults"
  | "isEmptyResults"
  | "isSearching"
  | "metrics"
  | "pagination"
  | "performanceHistory"
  | "reset"
  | "results"
  | "resultsBySearch"
  | "retryLastSearch"
  | "searchDuration"
  | "searchHistory"
  | "searchProgress"
  | "setSearchError"
  | "setSearchResults"
  | "softReset"
  | "startSearch"
  | "status"
  | "updateSearchProgress"
>;

const mapSearchTypeToResultsKey = (searchType: SearchType): keyof SearchResults => {
  switch (searchType) {
    case "accommodation":
      return "accommodations";
    case "activity":
      return "activities";
    case "destination":
      return "destinations";
    case "flight":
      return "flights";
    default:
      return assertNever(searchType);
  }
};

export const createSearchResultsCoreSlice =
  (
    deps: SearchResultsStoreDeps
  ): StateCreator<SearchResultsState, [], [], SearchResultsCoreSlice> =>
  (set, get) => ({
    appendResults: (searchId, newResults) => {
      const { resultsBySearch, currentSearchId, results } = get();

      if (currentSearchId !== searchId) {
        return;
      }

      const mergedResults: SearchResults = { ...results };

      Object.entries(newResults).forEach(([type, typeResults]) => {
        if (Array.isArray(typeResults)) {
          const resultKey = type as keyof SearchResults;
          const existingResults = mergedResults[resultKey] || [];
          if (Array.isArray(existingResults)) {
            (mergedResults[resultKey] as unknown[]) = [
              ...existingResults,
              ...typeResults,
            ];
          }
        }
      });

      set({
        results: mergedResults,
        resultsBySearch: {
          ...resultsBySearch,
          [searchId]: mergedResults,
        },
      });
    },

    cancelSearch: (searchId?: string) => {
      const { currentSearchId } = get();
      const targetSearchId = searchId || currentSearchId;

      if (currentSearchId === targetSearchId) {
        set({
          isSearching: false,
          searchProgress: 0,
          status: "cancelled",
        });
      }
    },
    canRetry: false,

    clearAllResults: () => {
      set({
        currentContext: null,
        currentSearchId: null,
        currentSearchType: null,
        error: null,
        isSearching: false,
        metrics: null,
        pagination: DEFAULT_PAGINATION,
        results: {},
        resultsBySearch: {},
        searchProgress: 0,
        status: "idle",
      });
    },

    clearError: () => {
      set({ error: null });
    },

    clearErrorHistory: () => {
      set({ errorHistory: [] });
    },

    clearResults: (searchType?: SearchType) => {
      if (searchType) {
        const resultKey = mapSearchTypeToResultsKey(searchType);

        set((state) => ({
          results: {
            ...state.results,
            [resultKey]: [],
          },
        }));
        return;
      }

      set({
        error: null,
        results: {},
        searchProgress: 0,
        status: "idle",
      });
    },

    completeSearch: (searchId) => {
      const { currentSearchId, currentContext } = get();

      if (currentSearchId === searchId && currentContext) {
        const completedAt = deps.nowIso();
        const updatedContext: SearchContext = {
          ...currentContext,
          completedAt,
        };

        set({
          currentContext: updatedContext,
          isSearching: false,
        });
      }
    },

    currentContext: null,
    currentSearchId: null,
    currentSearchType: null,

    error: null,
    errorHistory: [],

    hasResults: false,
    isEmptyResults: false,
    isSearching: false,

    metrics: null,

    pagination: DEFAULT_PAGINATION,
    performanceHistory: [],

    reset: () => {
      set({
        currentContext: null,
        currentSearchId: null,
        currentSearchType: null,
        error: null,
        errorHistory: [],
        isSearching: false,
        metrics: null,
        pagination: DEFAULT_PAGINATION,
        performanceHistory: [],
        results: {},
        resultsBySearch: {},
        searchHistory: [],
        searchProgress: 0,
        status: "idle",
      });
    },

    results: {},
    resultsBySearch: {},

    retryLastSearch: async () => {
      const { currentContext } = get();
      if (!currentContext) return null;

      await Promise.resolve();
      return get().startSearch(currentContext.searchType, currentContext.searchParams);
    },

    searchDuration: null,
    searchHistory: [],
    searchProgress: 0,

    setSearchError: (searchId, error) => {
      const { currentSearchId, errorHistory, currentContext, searchHistory } = get();

      if (currentSearchId === searchId && currentContext) {
        const errorWithTimestamp: ErrorDetails = {
          ...error,
          occurredAt: deps.nowIso(),
        };

        deps.logger.error("search_error", {
          code: error.code,
          message: error.message,
          searchId,
          searchType: currentContext.searchType,
        });

        const completedAt = deps.nowIso();
        const updatedContext: SearchContext = {
          ...currentContext,
          completedAt,
        };

        set({
          currentContext: updatedContext,
          error: errorWithTimestamp,
          errorHistory: [...errorHistory, { ...errorWithTimestamp, searchId }].slice(
            -20
          ),
          isSearching: false,
          searchHistory: [...searchHistory, updatedContext],
          searchProgress: 0,
          status: "error",
        });
      }
    },

    setSearchResults: (searchId, results, metrics) => {
      set((state) => {
        if (state.currentSearchId !== searchId || !state.currentContext) {
          return {};
        }

        const completedAt = deps.nowIso();
        const calculatedDuration =
          new Date(completedAt).getTime() -
          new Date(state.currentContext.startedAt).getTime();

        const calculatedTotal = Object.values(results).reduce(
          (total: number, typeResults: unknown) => {
            if (Array.isArray(typeResults)) {
              return total + typeResults.length;
            }
            return total;
          },
          0
        );

        const finalMetrics: SearchMetrics = {
          currentPage: metrics?.currentPage ?? 1,
          hasMoreResults: metrics?.hasMoreResults ?? false,
          provider: metrics?.provider,
          requestId: metrics?.requestId,
          resultsPerPage: metrics?.resultsPerPage ?? 20,
          searchDuration: metrics?.searchDuration ?? calculatedDuration,
          totalResults: metrics?.totalResults ?? calculatedTotal,
        };

        const updatedContext: SearchContext = {
          ...state.currentContext,
          completedAt,
          metrics: finalMetrics,
        };

        const totalResults = finalMetrics.totalResults;
        const resultsPerPage = finalMetrics.resultsPerPage;
        const totalPages = Math.ceil(totalResults / resultsPerPage);

        return {
          currentContext: updatedContext,
          isSearching: false,
          metrics: finalMetrics,
          pagination: {
            ...state.pagination,
            hasNextPage: state.pagination.currentPage < totalPages,
            hasPreviousPage: state.pagination.currentPage > 1,
            totalPages,
            totalResults,
          },
          performanceHistory: [
            ...state.performanceHistory,
            { ...finalMetrics, searchId },
          ].slice(-50),
          results,
          resultsBySearch: {
            ...state.resultsBySearch,
            [searchId]: results,
          },
          searchHistory: [...state.searchHistory, updatedContext],
          searchProgress: 100,
          status: "success",
        };
      });
    },

    softReset: () => {
      set({
        currentContext: null,
        currentSearchId: null,
        currentSearchType: null,
        error: null,
        isSearching: false,
        metrics: null,
        pagination: DEFAULT_PAGINATION,
        results: {},
        searchProgress: 0,
        status: "idle",
      });
    },

    startSearch: (searchType, params) => {
      const searchId = deps.generateSearchId();
      const timestamp = deps.nowIso();

      const newContext: SearchContext = {
        searchId,
        searchParams: params,
        searchType,
        startedAt: timestamp,
      };

      set({
        currentContext: newContext,
        currentSearchId: searchId,
        currentSearchType: searchType,
        error: null,
        isSearching: true,
        results: {},
        searchProgress: 0,
        status: "searching",
      });

      return searchId;
    },

    status: "idle",

    updateSearchProgress: (searchId, progress) => {
      const { currentSearchId } = get();
      if (currentSearchId === searchId) {
        const validProgress = Math.max(0, Math.min(100, progress));
        set({ searchProgress: validProgress });
      }
    },
  });
