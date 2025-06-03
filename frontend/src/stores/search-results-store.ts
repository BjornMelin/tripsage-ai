import { create } from "zustand";
import { persist, devtools } from "zustand/middleware";
import { z } from "zod";
import type { SearchResults, SearchType } from "@/types/search";

// Validation schemas for search results
const SearchStatusSchema = z.enum([
  "idle",
  "searching",
  "success",
  "error",
  "cancelled",
]);
const SearchTypeSchema = z.enum(["flight", "accommodation", "activity", "destination"]);

const SearchMetricsSchema = z.object({
  totalResults: z.number().min(0).default(0),
  searchDuration: z.number().min(0).optional(),
  provider: z.string().optional(),
  requestId: z.string().optional(),
  resultsPerPage: z.number().min(1).default(20),
  currentPage: z.number().min(1).default(1),
  hasMoreResults: z.boolean().default(false),
});

const SearchContextSchema = z.object({
  searchId: z.string(),
  searchType: SearchTypeSchema,
  searchParams: z.record(z.unknown()),
  startedAt: z.string(),
  completedAt: z.string().optional(),
  metrics: SearchMetricsSchema.optional(),
});

const ErrorDetailsSchema = z.object({
  code: z.string().optional(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
  retryable: z.boolean().default(true),
  occurredAt: z.string(),
});

// Types derived from schemas
export type SearchStatus = z.infer<typeof SearchStatusSchema>;
export type SearchMetrics = z.infer<typeof SearchMetricsSchema>;
export type SearchContext = z.infer<typeof SearchContextSchema>;
export type ErrorDetails = z.infer<typeof ErrorDetailsSchema>;

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
const generateSearchId = () =>
  `search_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
const getCurrentTimestamp = () => new Date().toISOString();

// Default states
const defaultPagination = {
  currentPage: 1,
  totalPages: 1,
  resultsPerPage: 20,
  totalResults: 0,
  hasNextPage: false,
  hasPreviousPage: false,
};

export const useSearchResultsStore = create<SearchResultsState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        status: "idle",
        currentSearchId: null,
        currentSearchType: null,

        // Results data
        results: {},
        resultsBySearch: {},

        // Search context and metadata
        searchHistory: [],
        currentContext: null,

        // Error handling
        error: null,
        errorHistory: [],

        // Loading and progress
        isSearching: false,
        searchProgress: 0,

        // Pagination
        pagination: defaultPagination,

        // Performance tracking
        metrics: null,
        performanceHistory: [],

        // Computed properties
        get hasResults() {
          const { results } = get();
          return Object.keys(results).some((key) => {
            const typeResults = results[key as keyof SearchResults];
            return Array.isArray(typeResults) && typeResults.length > 0;
          });
        },

        get isEmptyResults() {
          const { status, hasResults } = get();
          return status === "success" && !hasResults;
        },

        get canRetry() {
          const { error, status } = get();
          return status === "error" && (!error || error.retryable);
        },

        get searchDuration() {
          const { currentContext } = get();
          if (!currentContext || !currentContext.completedAt) return null;

          const startTime = new Date(currentContext.startedAt).getTime();
          const endTime = new Date(currentContext.completedAt).getTime();
          return endTime - startTime;
        },

        // Search execution actions
        startSearch: (searchType, params) => {
          const searchId = generateSearchId();
          const timestamp = getCurrentTimestamp();

          const newContext: SearchContext = {
            searchId,
            searchType,
            searchParams: params,
            startedAt: timestamp,
          };

          set({
            status: "searching",
            currentSearchId: searchId,
            currentSearchType: searchType,
            currentContext: newContext,
            isSearching: true,
            searchProgress: 0,
            error: null,
            results: {}, // Clear previous results
          });

          return searchId;
        },

        updateSearchProgress: (searchId, progress) => {
          const { currentSearchId } = get();
          if (currentSearchId === searchId) {
            const validProgress = Math.max(0, Math.min(100, progress));
            set({ searchProgress: validProgress });
          }
        },

        setSearchResults: (searchId, results, metrics) => {
          const { currentSearchId, searchHistory, currentContext } = get();

          if (currentSearchId === searchId && currentContext) {
            const completedAt = getCurrentTimestamp();
            const duration =
              new Date(completedAt).getTime() -
              new Date(currentContext.startedAt).getTime();

            const finalMetrics: SearchMetrics = {
              ...metrics,
              searchDuration: duration,
              totalResults: Object.values(results).reduce((total, typeResults) => {
                if (Array.isArray(typeResults)) {
                  return total + typeResults.length;
                }
                return total;
              }, 0),
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
              status: "success",
              results,
              isSearching: false,
              searchProgress: 100,
              currentContext: updatedContext,
              metrics: finalMetrics,
              pagination: {
                ...get().pagination,
                totalResults,
                totalPages,
                hasNextPage: get().pagination.currentPage < totalPages,
                hasPreviousPage: get().pagination.currentPage > 1,
              },
              resultsBySearch: {
                ...get().resultsBySearch,
                [searchId]: results,
              },
              searchHistory: [...searchHistory, updatedContext],
              performanceHistory: [
                ...get().performanceHistory,
                { ...finalMetrics, searchId },
              ].slice(-50), // Keep last 50 searches
            });
          }
        },

        setSearchError: (searchId, error) => {
          const { currentSearchId, errorHistory } = get();

          if (currentSearchId === searchId) {
            const errorWithTimestamp: ErrorDetails = {
              ...error,
              occurredAt: getCurrentTimestamp(),
            };

            set({
              status: "error",
              error: errorWithTimestamp,
              isSearching: false,
              searchProgress: 0,
              errorHistory: [
                ...errorHistory,
                { ...errorWithTimestamp, searchId },
              ].slice(-20), // Keep last 20 errors
            });
          }
        },

        cancelSearch: (searchId) => {
          const { currentSearchId } = get();
          const targetSearchId = searchId || currentSearchId;

          if (currentSearchId === targetSearchId) {
            set({
              status: "cancelled",
              isSearching: false,
              searchProgress: 0,
            });
          }
        },

        completeSearch: (searchId) => {
          const { currentSearchId, currentContext } = get();

          if (currentSearchId === searchId && currentContext) {
            const completedAt = getCurrentTimestamp();
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

        // Results management
        clearResults: (searchType) => {
          if (searchType) {
            set((state) => ({
              results: {
                ...state.results,
                [searchType]: [],
              },
            }));
          } else {
            set({
              results: {},
              status: "idle",
              error: null,
              searchProgress: 0,
            });
          }
        },

        clearAllResults: () => {
          set({
            results: {},
            resultsBySearch: {},
            status: "idle",
            currentSearchId: null,
            currentSearchType: null,
            currentContext: null,
            error: null,
            isSearching: false,
            searchProgress: 0,
            pagination: defaultPagination,
            metrics: null,
          });
        },

        appendResults: (searchId, newResults) => {
          const { resultsBySearch, currentSearchId, results } = get();

          if (currentSearchId === searchId) {
            const mergedResults: SearchResults = { ...results };

            Object.entries(newResults).forEach(([type, typeResults]) => {
              if (Array.isArray(typeResults)) {
                const existingResults =
                  mergedResults[type as keyof SearchResults] || [];
                mergedResults[type as keyof SearchResults] = [
                  ...(Array.isArray(existingResults) ? existingResults : []),
                  ...typeResults,
                ] as any;
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

        // Pagination actions
        setPage: (page) => {
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

        nextPage: () => {
          const { pagination } = get();
          if (pagination.hasNextPage) {
            get().setPage(pagination.currentPage + 1);
          }
        },

        previousPage: () => {
          const { pagination } = get();
          if (pagination.hasPreviousPage) {
            get().setPage(pagination.currentPage - 1);
          }
        },

        setResultsPerPage: (perPage) => {
          const { pagination } = get();
          const validPerPage = Math.max(1, Math.min(100, perPage));
          const totalPages = Math.ceil(pagination.totalResults / validPerPage);
          const currentPage = Math.min(pagination.currentPage, totalPages);

          set({
            pagination: {
              ...pagination,
              resultsPerPage: validPerPage,
              totalPages,
              currentPage: Math.max(1, currentPage),
              hasNextPage: currentPage < totalPages,
              hasPreviousPage: currentPage > 1,
            },
          });
        },

        // Search history management
        getSearchById: (searchId) => {
          const { searchHistory } = get();
          return searchHistory.find((search) => search.searchId === searchId) || null;
        },

        getResultsById: (searchId) => {
          const { resultsBySearch } = get();
          return resultsBySearch[searchId] || null;
        },

        getRecentSearches: (searchType, limit = 10) => {
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

        clearSearchHistory: () => {
          set({
            searchHistory: [],
            resultsBySearch: {},
            performanceHistory: [],
            errorHistory: [],
          });
        },

        removeSearchFromHistory: (searchId) => {
          set((state) => ({
            searchHistory: state.searchHistory.filter(
              (search) => search.searchId !== searchId
            ),
            resultsBySearch: (() => {
              const newResults = { ...state.resultsBySearch };
              delete newResults[searchId];
              return newResults;
            })(),
            performanceHistory: state.performanceHistory.filter(
              (perf) => perf.searchId !== searchId
            ),
            errorHistory: state.errorHistory.filter(
              (error) => error.searchId !== searchId
            ),
          }));
        },

        // Error management
        retryLastSearch: async () => {
          const { currentContext } = get();
          if (!currentContext) return null;

          // Start a new search with the same parameters
          return get().startSearch(
            currentContext.searchType,
            currentContext.searchParams
          );
        },

        clearError: () => {
          set({ error: null });
        },

        clearErrorHistory: () => {
          set({ errorHistory: [] });
        },

        // Performance monitoring
        getAverageSearchDuration: (searchType) => {
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

        getSearchSuccessRate: (searchType) => {
          const { searchHistory } = get();
          let relevantSearches = searchHistory;

          if (searchType) {
            relevantSearches = searchHistory.filter(
              (search) => search.searchType === searchType
            );
          }

          if (relevantSearches.length === 0) return 0;

          const successfulSearches = relevantSearches.filter(
            (search) => search.completedAt
          ).length;
          return (successfulSearches / relevantSearches.length) * 100;
        },

        getPerformanceInsights: () => {
          const { searchHistory, performanceHistory, errorHistory } = get();
          const totalSearches = searchHistory.length;
          const totalErrors = errorHistory.length;

          return {
            averageDuration: get().getAverageSearchDuration(),
            successRate: get().getSearchSuccessRate(),
            totalSearches,
            errorRate: totalSearches > 0 ? (totalErrors / totalSearches) * 100 : 0,
          };
        },

        // Utility actions
        reset: () => {
          set({
            status: "idle",
            currentSearchId: null,
            currentSearchType: null,
            results: {},
            resultsBySearch: {},
            searchHistory: [],
            currentContext: null,
            error: null,
            errorHistory: [],
            isSearching: false,
            searchProgress: 0,
            pagination: defaultPagination,
            metrics: null,
            performanceHistory: [],
          });
        },

        softReset: () => {
          set({
            status: "idle",
            currentSearchId: null,
            currentSearchType: null,
            results: {},
            currentContext: null,
            error: null,
            isSearching: false,
            searchProgress: 0,
            pagination: defaultPagination,
            metrics: null,
          });
        },
      }),
      {
        name: "search-results-storage",
        partialize: (state) => ({
          // Persist search history and cached results, but not current search state
          searchHistory: state.searchHistory.slice(-20), // Keep last 20 searches
          resultsBySearch: Object.fromEntries(
            Object.entries(state.resultsBySearch).slice(-10) // Keep last 10 result sets
          ),
          performanceHistory: state.performanceHistory.slice(-30), // Keep last 30 performance records
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
