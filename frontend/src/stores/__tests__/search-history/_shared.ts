/**
 * @fileoverview Shared test utilities and helpers for search history store tests.
 */

import { act } from "@testing-library/react";
import type {
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "@/stores/search-history-store";
import { useSearchHistoryStore } from "@/stores/search-history-store";

/**
 * Resets the search history store to its initial state.
 */
export const resetSearchHistoryStore = (): void => {
  act(() => {
    useSearchHistoryStore.setState({
      autoCleanupDays: 30,
      autoSaveEnabled: true,
      error: null,
      isLoading: false,
      isSyncing: false,
      lastSyncAt: null,
      maxRecentSearches: 50,
      popularSearchTerms: [],
      quickSearches: [],
      recentSearches: [],
      savedSearches: [],
      searchCollections: [],
      searchSuggestions: [],
      syncError: null,
    });
  });
};

/**
 * Creates a mock search history item with optional overrides.
 *
 * @param overrides - Partial search history item to override defaults
 * @returns A complete search history item
 */
export const createMockSearchItem = (
  overrides: Partial<SearchHistoryItem> = {}
): SearchHistoryItem => ({
  id: "test-id",
  params: {},
  searchType: "flight",
  timestamp: new Date().toISOString(),
  ...overrides,
});

/**
 * Creates a mock saved search with optional overrides.
 *
 * @param overrides - Partial saved search to override defaults
 * @returns A complete saved search
 */
export const createMockSavedSearch = (
  overrides: Partial<ValidatedSavedSearch> = {}
): ValidatedSavedSearch => ({
  createdAt: new Date().toISOString(),
  id: "test-search-id",
  isFavorite: false,
  isPublic: false,
  name: "Test Search",
  params: {},
  searchType: "flight",
  tags: [],
  updatedAt: new Date().toISOString(),
  usageCount: 0,
  ...overrides,
});
