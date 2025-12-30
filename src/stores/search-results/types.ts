/**
 * @fileoverview Shared types for the search results Zustand store slices.
 */

import type { SearchResults, SearchType } from "@schemas/search";
import type {
  ErrorDetails,
  SearchContext,
  SearchMetrics,
  SearchStatus,
} from "@schemas/stores";

export type SearchResultsStoreDeps = {
  generateSearchId: () => string;
  nowIso: () => string;
};

export interface SearchResultsState {
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
