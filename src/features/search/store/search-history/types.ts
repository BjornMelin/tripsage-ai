/**
 * @fileoverview Type definitions for search history store slices.
 */

import type { SearchParams, SearchType } from "@schemas/search";
import type {
  QuickSearch,
  SearchCollection,
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "@schemas/stores";

export interface SearchSuggestion {
  id: string;
  text: string;
  searchType: SearchType;
  frequency: number;
  lastUsed: string;
  source: "history" | "saved" | "popular";
}

export interface SearchAnalytics {
  totalSearches: number;
  searchesByType: Record<SearchType, number>;
  averageSearchDuration: number;
  mostUsedSearchTypes: Array<{
    type: SearchType;
    count: number;
    percentage: number;
  }>;
  searchTrends: Array<{ date: string; count: number }>;
  popularSearchTimes: Array<{ hour: number; count: number }>;
  topDestinations: Array<{ destination: string; count: number }>;
  savedSearchUsage: Array<{
    searchId: string;
    name: string;
    usageCount: number;
  }>;
}

// Slice interfaces
export interface RecentSearchesSlice {
  recentSearches: SearchHistoryItem[];
  maxRecentSearches: number;
  autoSaveEnabled: boolean;
  autoCleanupDays: number;
  addRecentSearch: (
    searchType: SearchType,
    params: SearchParams,
    metadata?: Partial<SearchHistoryItem>
  ) => void;
  clearRecentSearches: (searchType?: SearchType) => void;
  removeRecentSearch: (searchId: string) => void;
  cleanupOldSearches: () => void;
  getRecentSearchesByType: (
    searchType: SearchType,
    limit?: number
  ) => SearchHistoryItem[];
}

export interface SavedSearchesSlice {
  savedSearches: ValidatedSavedSearch[];
  isLoading: boolean;
  error: string | null;
  saveSearch: (
    name: string,
    searchType: SearchType,
    params: SearchParams,
    options?: {
      description?: string;
      tags?: string[];
      isFavorite?: boolean;
      isPublic?: boolean;
    }
  ) => Promise<string | null>;
  updateSavedSearch: (
    searchId: string,
    updates: Partial<ValidatedSavedSearch>
  ) => Promise<boolean>;
  deleteSavedSearch: (searchId: string) => Promise<boolean>;
  duplicateSavedSearch: (searchId: string, newName: string) => Promise<string | null>;
  markSearchAsUsed: (searchId: string) => void;
  toggleSearchFavorite: (searchId: string) => void;
  searchSavedSearches: (
    query: string,
    filters?: {
      searchType?: SearchType;
      tags?: string[];
      isFavorite?: boolean;
    }
  ) => ValidatedSavedSearch[];
  getSavedSearchesByType: (searchType: SearchType) => ValidatedSavedSearch[];
  getSavedSearchesByTag: (tag: string) => ValidatedSavedSearch[];
  clearError: () => void;
}

export interface CollectionsSlice {
  searchCollections: SearchCollection[];
  createCollection: (
    name: string,
    description?: string,
    searchIds?: string[]
  ) => Promise<string | null>;
  updateCollection: (
    collectionId: string,
    updates: Partial<SearchCollection>
  ) => Promise<boolean>;
  deleteCollection: (collectionId: string) => Promise<boolean>;
  addSearchToCollection: (collectionId: string, searchId: string) => void;
  removeSearchFromCollection: (collectionId: string, searchId: string) => void;
}

export interface QuickSearchesSlice {
  quickSearches: QuickSearch[];
  createQuickSearch: (
    label: string,
    searchType: SearchType,
    params: SearchParams,
    options?: {
      icon?: string;
      color?: string;
      sortOrder?: number;
    }
  ) => Promise<string | null>;
  updateQuickSearch: (
    quickSearchId: string,
    updates: Partial<QuickSearch>
  ) => Promise<boolean>;
  deleteQuickSearch: (quickSearchId: string) => void;
  reorderQuickSearches: (quickSearchIds: string[]) => void;
}

export interface SuggestionsSlice {
  searchSuggestions: SearchSuggestion[];
  popularSearchTerms: Array<{
    term: string;
    count: number;
    searchType: SearchType;
  }>;
  getSearchSuggestions: (
    query: string,
    searchType?: SearchType,
    limit?: number
  ) => SearchSuggestion[];
  updateSearchSuggestions: () => void;
  addSearchTerm: (term: string, searchType: SearchType) => void;
}

export interface AnalyticsSlice {
  getSearchAnalytics: (dateRange?: { start: string; end: string }) => SearchAnalytics;
  getMostUsedSearches: (limit?: number) => ValidatedSavedSearch[];
  getSearchTrends: (
    searchType?: SearchType,
    days?: number
  ) => Array<{ date: string; count: number }>;
}

export interface SettingsSlice {
  updateSettings: (settings: {
    maxRecentSearches?: number;
    autoSaveEnabled?: boolean;
    autoCleanupDays?: number;
  }) => void;
}

export interface UtilitySlice {
  clearAllData: () => void;
  reset: () => void;
}

// Combined state type
export type SearchHistoryState = RecentSearchesSlice &
  SavedSearchesSlice &
  CollectionsSlice &
  QuickSearchesSlice &
  SuggestionsSlice &
  AnalyticsSlice &
  SettingsSlice &
  UtilitySlice & {
    // Computed properties
    totalSavedSearches: number;
    recentSearchesByType: Record<SearchType, SearchHistoryItem[]>;
    favoriteSearches: ValidatedSavedSearch[];
    searchAnalytics: SearchAnalytics;
  };
