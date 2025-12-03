/**
 * @fileoverview Zustand store for managing search results, pagination, and performance metrics.
 */

import type { SearchResults, SearchType } from "@schemas/search";
import type {
  ErrorDetails,
  SearchContext,
  SearchMetrics,
  SearchStatus,
} from "@schemas/stores";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { nowIso, secureId } from "@/lib/security/random";
import { createComputeFn, withComputed } from "./middleware/computed";

// Schemas imported from @schemas/stores

// Search results store interface
interface SearchResultsState {
  // Current search state
  status: SearchStatus;
  currentSearchId: string | null;
  currentSearchType: SearchType | null;

  // Results data
  results: SearchResults;
  resultsBySearch: Record<string, SearchResults>;

  // Search context and metadata
  searchHistory: SearchContext[];
  currentContext: SearchContext | null;

  // Error handling
  error: ErrorDetails | null;
  errorHistory: Array<ErrorDetails & { searchId: string }>;

  // Loading and progress
  isSearching: boolean;
  searchProgress: number; // 0-100

  // Pagination and performance
  pagination: {
    currentPage: number;
    totalPages: number;
    resultsPerPage: number;
    totalResults: number;
    hasNextPage: boolean;
    hasPreviousPage: boolean;
  };

  // Performance tracking
  metrics: SearchMetrics | null;
  performanceHistory: Array<SearchMetrics & { searchId: string }>;

  // Computed properties
  hasResults: boolean;
  isEmptyResults: boolean;
  canRetry: boolean;
  searchDuration: number | null;

  // Search execution actions
  startSearch: (searchType: SearchType, params: Record<string, unknown>) => string;
  updateSearchProgress: (searchId: string, progress: number) => void;
  setSearchResults: (
    searchId: string,
    results: SearchResults,
    metrics?: SearchMetrics
  ) => void;
  setSearchError: (searchId: string, error: ErrorDetails) => void;
  cancelSearch: (searchId?: string) => void;
  completeSearch: (searchId: string) => void;

  // Results management
  clearResults: (searchType?: SearchType) => void;
  clearAllResults: () => void;
  appendResults: (searchId: string, newResults: SearchResults) => void;

  // Pagination actions
  setPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  setResultsPerPage: (perPage: number) => void;

  // Search history management
  getSearchById: (searchId: string) => SearchContext | null;
  getResultsById: (searchId: string) => SearchResults | null;
  getRecentSearches: (searchType?: SearchType, limit?: number) => SearchContext[];
  clearSearchHistory: () => void;
  removeSearchFromHistory: (searchId: string) => void;

  // Error management
  retryLastSearch: () => Promise<string | null>;
  clearError: () => void;
  clearErrorHistory: () => void;

  // Performance monitoring
  getAverageSearchDuration: (searchType?: SearchType) => number;
  getSearchSuccessRate: (searchType?: SearchType) => number;
  getPerformanceInsights: () => {
    averageDuration: number;
    successRate: number;
    totalSearches: number;
    errorRate: number;
  };

  // Utility actions
  reset: () => void;
  softReset: () => void; // Keeps history but clears current state
}

// Helper functions
const GENERATE_SEARCH_ID = () => `search_${secureId(12)}`;
const GET_CURRENT_TIMESTAMP = () => nowIso();

// Helper to check if there are any results
const getHasResults = (state: SearchResultsState): boolean =>
  Object.keys(state.results || {}).some((key) => {
    const typeResults = state.results?.[key as keyof SearchResults];
    return Array.isArray(typeResults) && typeResults.length > 0;
  });

// Helper to compute derived state
const computeResultsState = createComputeFn<SearchResultsState>({
  canRetry: (state) =>
    state.status === "error" && (!state.error || state.error.retryable),
  hasResults: (state) => getHasResults(state),
  isEmptyResults: (state) => state.status === "success" && !getHasResults(state),
  searchDuration: (state) => {
    if (state.currentContext?.completedAt) {
      const startTime = new Date(state.currentContext.startedAt).getTime();
      const endTime = new Date(state.currentContext.completedAt).getTime();
      return endTime - startTime;
    }
    return null;
  },
});

// Default states
const DEFAULT_PAGINATION = {
  currentPage: 1,
  hasNextPage: false,
  hasPreviousPage: false,
  resultsPerPage: 20,
  totalPages: 1,
  totalResults: 0,
};

export const useSearchResultsStore = create<SearchResultsState>()(
  devtools(
    persist(
      withComputed({ compute: computeResultsState }, (set, get) => ({
        appendResults: (searchId: string, newResults: SearchResults) => {
          const { resultsBySearch, currentSearchId, results } = get();

          if (currentSearchId === searchId) {
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
          }
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

        // Results management
        clearResults: (searchType?: SearchType) => {
          if (searchType) {
            // Map singular search type to plural result key
            const resultKey =
              searchType === "accommodation"
                ? "accommodations"
                : searchType === "activity"
                  ? "activities"
                  : searchType === "destination"
                    ? "destinations"
                    : searchType === "flight"
                      ? "flights"
                      : searchType;

            set((state) => ({
              results: {
                ...state.results,
                [resultKey]: [],
              },
            }));
          } else {
            set({
              error: null,
              results: {},
              searchProgress: 0,
              status: "idle",
            });
          }
        },

        clearSearchHistory: () => {
          set({
            errorHistory: [],
            performanceHistory: [],
            resultsBySearch: {},
            searchHistory: [],
          });
        },

        completeSearch: (searchId: string) => {
          const { currentSearchId, currentContext } = get();

          if (currentSearchId === searchId && currentContext) {
            const completedAt = GET_CURRENT_TIMESTAMP();
            const updatedContext = {
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

        // Error handling
        error: null,
        errorHistory: [],

        // Performance monitoring
        getAverageSearchDuration: (searchType?: SearchType) => {
          const { performanceHistory } = get();
          let relevantMetrics = performanceHistory;

          if (searchType) {
            relevantMetrics = performanceHistory.filter((perf) => {
              const search = get().getSearchById(perf.searchId);
              return search?.searchType === searchType;
            });
          }

          if (relevantMetrics.length === 0) return 0;

          const totalDuration = relevantMetrics.reduce((sum, metric) => {
            return sum + (metric.searchDuration || 0);
          }, 0);

          return totalDuration / relevantMetrics.length;
        },

        getPerformanceInsights: () => {
          const {
            searchHistory,
            performanceHistory: _performanceHistory,
            errorHistory,
          } = get();
          const totalSearches = searchHistory.length;
          const totalErrors = errorHistory.length;

          return {
            averageDuration: get().getAverageSearchDuration(),
            errorRate: totalSearches > 0 ? (totalErrors / totalSearches) * 100 : 0,
            successRate: get().getSearchSuccessRate(),
            totalSearches,
          };
        },

        getRecentSearches: (searchType?: SearchType, limit = 10) => {
          const { searchHistory } = get();
          let filtered = searchHistory;

          if (searchType) {
            filtered = searchHistory.filter(
              (search) => search.searchType === searchType
            );
          }

          return filtered
            .sort(
              (a, b) =>
                new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
            )
            .slice(0, limit);
        },

        getResultsById: (searchId: string) => {
          const { resultsBySearch } = get();
          return resultsBySearch[searchId] || null;
        },

        // Search history management
        getSearchById: (searchId: string) => {
          const { searchHistory } = get();
          return searchHistory.find((search) => search.searchId === searchId) || null;
        },

        getSearchSuccessRate: (searchType?: SearchType) => {
          const { searchHistory, errorHistory } = get();
          let relevantSearches = searchHistory;

          if (searchType) {
            relevantSearches = searchHistory.filter(
              (search) => search.searchType === searchType
            );
          }

          if (relevantSearches.length === 0) return 0;

          // Count searches that completed without error
          const erroredSearchIds = new Set(errorHistory.map((e) => e.searchId));
          const successfulSearches = relevantSearches.filter(
            (search) => search.completedAt && !erroredSearchIds.has(search.searchId)
          ).length;

          return (successfulSearches / relevantSearches.length) * 100;
        },

        // Computed properties
        hasResults: false,
        isEmptyResults: false,

        // Loading and progress
        isSearching: false,

        // Performance tracking
        metrics: null,

        nextPage: () => {
          const { pagination } = get();
          if (pagination.hasNextPage) {
            get().setPage(pagination.currentPage + 1);
          }
        },

        // Pagination
        pagination: DEFAULT_PAGINATION,
        performanceHistory: [],

        previousPage: () => {
          const { pagination } = get();
          if (pagination.hasPreviousPage) {
            get().setPage(pagination.currentPage - 1);
          }
        },

        removeSearchFromHistory: (searchId: string) => {
          set((state) => ({
            errorHistory: state.errorHistory.filter(
              (error) => error.searchId !== searchId
            ),
            performanceHistory: state.performanceHistory.filter(
              (perf) => perf.searchId !== searchId
            ),
            resultsBySearch: (() => {
              const newResults = { ...state.resultsBySearch };
              delete newResults[searchId];
              return newResults;
            })(),
            searchHistory: state.searchHistory.filter(
              (search) => search.searchId !== searchId
            ),
          }));
        },

        // Utility actions
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

        // Results data
        results: {},
        resultsBySearch: {},

        // Error management
        retryLastSearch: async () => {
          const { currentContext } = get();
          if (!currentContext) return null;

          // Start a new search with the same parameters
          await Promise.resolve();
          return get().startSearch(
            currentContext.searchType,
            currentContext.searchParams
          );
        },
        searchDuration: null,

        // Search context and metadata
        searchHistory: [],
        searchProgress: 0,

        // Pagination actions
        setPage: (page: number) => {
          const { pagination } = get();
          const validPage = Math.max(1, Math.min(pagination.totalPages, page));

          set({
            pagination: {
              ...pagination,
              currentPage: validPage,
              hasNextPage: validPage < pagination.totalPages,
              hasPreviousPage: validPage > 1,
            },
          });
        },

        setResultsPerPage: (perPage: number) => {
          const { pagination } = get();
          const validPerPage = Math.max(1, Math.min(100, perPage));
          const totalPages = Math.ceil(pagination.totalResults / validPerPage);
          const currentPage = Math.min(pagination.currentPage, totalPages);

          set({
            pagination: {
              ...pagination,
              currentPage: Math.max(1, currentPage),
              hasNextPage: currentPage < totalPages,
              hasPreviousPage: currentPage > 1,
              resultsPerPage: validPerPage,
              totalPages,
            },
          });
        },

        setSearchError: (searchId: string, error: ErrorDetails) => {
          const { currentSearchId, errorHistory, currentContext, searchHistory } =
            get();

          if (currentSearchId === searchId && currentContext) {
            const errorWithTimestamp: ErrorDetails = {
              ...error,
              occurredAt: GET_CURRENT_TIMESTAMP(),
            };

            // Mark search as completed (with error) in history
            const completedAt = GET_CURRENT_TIMESTAMP();
            const updatedContext: SearchContext = {
              ...currentContext,
              completedAt,
            };

            set({
              currentContext: updatedContext,
              error: errorWithTimestamp,
              errorHistory: [
                ...errorHistory,
                { ...errorWithTimestamp, searchId },
              ].slice(-20), // Keep last 20 errors
              isSearching: false,
              searchHistory: [...searchHistory, updatedContext],
              searchProgress: 0,
              status: "error",
            });
          }
        },

        setSearchResults: (
          searchId: string,
          results: SearchResults,
          metrics?: SearchMetrics
        ) => {
          const { currentSearchId, searchHistory, currentContext } = get();

          if (currentSearchId === searchId && currentContext) {
            const completedAt = GET_CURRENT_TIMESTAMP();
            const calculatedDuration =
              new Date(completedAt).getTime() -
              new Date(currentContext.startedAt).getTime();

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
              ...currentContext,
              completedAt,
              metrics: finalMetrics,
            };

            // Calculate pagination based on results
            const totalResults = finalMetrics.totalResults;
            const resultsPerPage = finalMetrics.resultsPerPage;
            const totalPages = Math.ceil(totalResults / resultsPerPage);

            set({
              currentContext: updatedContext,
              isSearching: false,
              metrics: finalMetrics,
              pagination: {
                ...get().pagination,
                hasNextPage: get().pagination.currentPage < totalPages,
                hasPreviousPage: get().pagination.currentPage > 1,
                totalPages,
                totalResults,
              },
              performanceHistory: [
                ...get().performanceHistory,
                { ...finalMetrics, searchId },
              ].slice(-50), // Keep last 50 searches
              results,
              resultsBySearch: {
                ...get().resultsBySearch,
                [searchId]: results,
              },
              searchHistory: [...searchHistory, updatedContext],
              searchProgress: 100,
              status: "success",
            });
          }
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

        // Search execution actions
        startSearch: (searchType: SearchType, params: Record<string, unknown>) => {
          const searchId = GENERATE_SEARCH_ID();
          const timestamp = GET_CURRENT_TIMESTAMP();

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
            results: {}, // Clear previous results
            searchProgress: 0,
            status: "searching",
          });

          return searchId;
        },
        // Initial state
        status: "idle",

        updateSearchProgress: (searchId: string, progress: number) => {
          const { currentSearchId } = get();
          if (currentSearchId === searchId) {
            const validProgress = Math.max(0, Math.min(100, progress));
            set({ searchProgress: validProgress });
          }
        },
      })),
      {
        name: "search-results-storage",
        partialize: (state) => ({
          performanceHistory: state.performanceHistory.slice(-30), // Keep last 30 performance records
          resultsBySearch: Object.fromEntries(
            Object.entries(state.resultsBySearch).slice(-10) // Keep last 10 result sets
          ),
          // Persist search history and cached results, but not current search state
          searchHistory: state.searchHistory.slice(-20), // Keep last 20 searches
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
