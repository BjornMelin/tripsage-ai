/**
 * @fileoverview Zustand store for managing search history, saved searches, and analytics.
 */

import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { nowIso, secureId } from "@/lib/security/random";
import type { SearchParams, SearchType } from "@/types/search";

// Validation schemas for search history
const SEARCH_TYPE_SCHEMA = z.enum([
  "flight",
  "accommodation",
  "activity",
  "destination",
]);

const SEARCH_HISTORY_ITEM_SCHEMA = z.object({
  id: z.string(),
  location: z
    .object({
      city: z.string().optional(),
      coordinates: z
        .object({
          lat: z.number(),
          lng: z.number(),
        })
        .optional(),
      country: z.string().optional(),
    })
    .optional(),
  params: z.record(z.string(), z.unknown()),
  resultsCount: z.number().min(0).optional(),
  searchDuration: z.number().min(0).optional(),
  searchType: SEARCH_TYPE_SCHEMA,
  timestamp: z.string(),
  userAgent: z.string().optional(),
});

const SAVED_SEARCH_SCHEMA = z.object({
  createdAt: z.string(),
  description: z.string().max(500).optional(),
  id: z.string(),
  isFavorite: z.boolean().default(false),
  isPublic: z.boolean().default(false),
  lastUsed: z.string().optional(),
  metadata: z
    .object({
      originalSearchId: z.string().optional(),
      source: z.string().optional(), // e.g., "manual", "auto-save", "import"
      version: z.string().default("1.0"),
    })
    .optional(),
  name: z.string().min(1).max(100),
  params: z.record(z.string(), z.unknown()),
  searchType: SEARCH_TYPE_SCHEMA,
  tags: z.array(z.string()).default([]),
  updatedAt: z.string(),
  usageCount: z.number().min(0).default(0),
});

const SEARCH_COLLECTION_SCHEMA = z.object({
  createdAt: z.string(),
  createdBy: z.string().optional(),
  description: z.string().max(500).optional(),
  id: z.string(),
  isPublic: z.boolean().default(false),
  name: z.string().min(1).max(100),
  searchIds: z.array(z.string()),
  tags: z.array(z.string()).default([]),
  updatedAt: z.string(),
});

const QUICK_SEARCH_SCHEMA = z.object({
  color: z.string().optional(),
  createdAt: z.string(),
  icon: z.string().optional(),
  id: z.string(),
  isVisible: z.boolean().default(true),
  label: z.string().min(1).max(50),
  params: z.record(z.string(), z.unknown()),
  searchType: SEARCH_TYPE_SCHEMA,
  sortOrder: z.number().default(0),
});

// Types derived from schemas
export type SearchHistoryItem = z.infer<typeof SEARCH_HISTORY_ITEM_SCHEMA>;
export type ValidatedSavedSearch = z.infer<typeof SAVED_SEARCH_SCHEMA>;
export type SearchCollection = z.infer<typeof SEARCH_COLLECTION_SCHEMA>;
export type QuickSearch = z.infer<typeof QUICK_SEARCH_SCHEMA>;

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
  mostUsedSearchTypes: Array<{ type: SearchType; count: number; percentage: number }>;
  searchTrends: Array<{ date: string; count: number }>;
  popularSearchTimes: Array<{ hour: number; count: number }>;
  topDestinations: Array<{ destination: string; count: number }>;
  savedSearchUsage: Array<{ searchId: string; name: string; usageCount: number }>;
}

// Search history store interface
interface SearchHistoryState {
  // Search history data
  recentSearches: SearchHistoryItem[];
  savedSearches: ValidatedSavedSearch[];
  searchCollections: SearchCollection[];
  quickSearches: QuickSearch[];

  // Search suggestions and auto-complete
  searchSuggestions: SearchSuggestion[];
  popularSearchTerms: Array<{ term: string; count: number; searchType: SearchType }>;

  // Auto-save and cleanup settings
  maxRecentSearches: number;
  autoSaveEnabled: boolean;
  autoCleanupDays: number;

  // Loading and sync states
  isLoading: boolean;
  isSyncing: boolean;
  lastSyncAt: string | null;

  // Error states
  error: string | null;
  syncError: string | null;

  // Computed properties
  totalSavedSearches: number;
  recentSearchesByType: Record<SearchType, SearchHistoryItem[]>;
  favoriteSearches: ValidatedSavedSearch[];
  searchAnalytics: SearchAnalytics;

  // Recent search management
  addRecentSearch: (
    searchType: SearchType,
    params: SearchParams,
    metadata?: Partial<SearchHistoryItem>
  ) => void;
  clearRecentSearches: (searchType?: SearchType) => void;
  removeRecentSearch: (searchId: string) => void;
  cleanupOldSearches: () => void;

  // Saved search management
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

  // Search collections
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

  // Quick searches
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

  // Search suggestions and auto-complete
  getSearchSuggestions: (
    query: string,
    searchType?: SearchType,
    limit?: number
  ) => SearchSuggestion[];
  updateSearchSuggestions: () => void;
  addSearchTerm: (term: string, searchType: SearchType) => void;

  // Data management and sync
  exportSearchHistory: () => string;
  importSearchHistory: (data: string) => Promise<boolean>;
  syncWithServer: () => Promise<boolean>;

  // Search and filtering
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
  getRecentSearchesByType: (
    searchType: SearchType,
    limit?: number
  ) => SearchHistoryItem[];

  // Analytics and insights
  getSearchAnalytics: (dateRange?: { start: string; end: string }) => SearchAnalytics;
  getMostUsedSearches: (limit?: number) => ValidatedSavedSearch[];
  getSearchTrends: (
    searchType?: SearchType,
    days?: number
  ) => Array<{ date: string; count: number }>;

  // Settings management
  updateSettings: (settings: {
    maxRecentSearches?: number;
    autoSaveEnabled?: boolean;
    autoCleanupDays?: number;
  }) => void;

  // Utility actions
  clearAllData: () => void;
  clearError: () => void;
  reset: () => void;
}

// Helper functions
const GENERATE_ID = () => secureId(12);
const GET_CURRENT_TIMESTAMP = () => nowIso();

// Default settings
const DEFAULT_MAX_RECENT_SEARCHES = 50;
const DEFAULT_AUTO_CLEANUP_DAYS = 30;

export const useSearchHistoryStore = create<SearchHistoryState>()(
  devtools(
    persist(
      (set, get) => ({
        // Recent search management
        addRecentSearch: (searchType, params, metadata = {}) => {
          const { maxRecentSearches, recentSearches } = get();
          const timestamp = GET_CURRENT_TIMESTAMP();

          // Check if similar search already exists (avoid duplicates)
          const paramsString = JSON.stringify(params);
          const existingIndex = recentSearches.findIndex(
            (search) =>
              search.searchType === searchType &&
              JSON.stringify(search.params) === paramsString
          );

          if (existingIndex >= 0) {
            // Update existing search timestamp
            set((state) => ({
              recentSearches: [
                {
                  ...state.recentSearches[existingIndex],
                  timestamp,
                },
                ...state.recentSearches.filter((_, index) => index !== existingIndex),
              ],
            }));
            return;
          }

          // Add new search
          const newSearch: SearchHistoryItem = {
            id: GENERATE_ID(),
            params: params as Record<string, unknown>,
            searchType,
            timestamp,
            ...metadata,
          };

          const result = SEARCH_HISTORY_ITEM_SCHEMA.safeParse(newSearch);
          if (result.success) {
            set((state) => ({
              recentSearches: [
                result.data,
                ...state.recentSearches.slice(0, maxRecentSearches - 1),
              ],
            }));

            // Update search suggestions
            get().updateSearchSuggestions();
          } else {
            console.error("Invalid search history item:", result.error);
          }
        },

        addSearchTerm: (term, searchType) => {
          set((state) => {
            const existingIndex = state.popularSearchTerms.findIndex(
              (t) => t.term === term && t.searchType === searchType
            );

            if (existingIndex >= 0) {
              const updatedTerms = [...state.popularSearchTerms];
              updatedTerms[existingIndex].count += 1;
              return { popularSearchTerms: updatedTerms };
            }
            return {
              popularSearchTerms: [
                ...state.popularSearchTerms,
                { count: 1, searchType, term },
              ].slice(0, 200), // Keep top 200 terms
            };
          });
        },

        addSearchToCollection: (collectionId, searchId) => {
          set((state) => ({
            searchCollections: state.searchCollections.map((collection) =>
              collection.id === collectionId
                ? {
                    ...collection,
                    searchIds: [...new Set([...collection.searchIds, searchId])],
                    updatedAt: GET_CURRENT_TIMESTAMP(),
                  }
                : collection
            ),
          }));
        },
        autoCleanupDays: DEFAULT_AUTO_CLEANUP_DAYS,
        autoSaveEnabled: true,

        cleanupOldSearches: () => {
          const { autoCleanupDays } = get();
          const cutoffDate = new Date();
          cutoffDate.setDate(cutoffDate.getDate() - autoCleanupDays);

          set((state) => ({
            recentSearches: state.recentSearches.filter(
              (search) => new Date(search.timestamp) > cutoffDate
            ),
          }));
        },

        // Utility actions
        clearAllData: () => {
          set({
            popularSearchTerms: [],
            quickSearches: [],
            recentSearches: [],
            savedSearches: [],
            searchCollections: [],
            searchSuggestions: [],
          });
        },

        clearError: () => {
          set({ error: null, syncError: null });
        },

        clearRecentSearches: (searchType) => {
          if (searchType) {
            set((state) => ({
              recentSearches: state.recentSearches.filter(
                (search) => search.searchType !== searchType
              ),
            }));
          } else {
            set({ recentSearches: [] });
          }
        },

        // Search collections
        createCollection: (name, description, searchIds = []) => {
          set({ isLoading: true });

          try {
            const collectionId = GENERATE_ID();
            const timestamp = GET_CURRENT_TIMESTAMP();

            const newCollection: SearchCollection = {
              createdAt: timestamp,
              description,
              id: collectionId,
              isPublic: false,
              name,
              searchIds,
              tags: [],
              updatedAt: timestamp,
            };

            const result = SEARCH_COLLECTION_SCHEMA.safeParse(newCollection);
            if (result.success) {
              set((state) => ({
                isLoading: false,
                searchCollections: [...state.searchCollections, result.data],
              }));

              return Promise.resolve(collectionId);
            }
            throw new Error("Invalid collection data");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to create collection";
            set({ error: message, isLoading: false });
            return Promise.resolve(null);
          }
        },

        // Quick searches
        createQuickSearch: (label, searchType, params, options = {}) => {
          try {
            const quickSearchId = GENERATE_ID();
            const timestamp = GET_CURRENT_TIMESTAMP();

            const newQuickSearch: QuickSearch = {
              color: options.color,
              createdAt: timestamp,
              icon: options.icon,
              id: quickSearchId,
              isVisible: true,
              label,
              params: params as Record<string, unknown>,
              searchType,
              sortOrder: options.sortOrder || get().quickSearches.length,
            };

            const result = QUICK_SEARCH_SCHEMA.safeParse(newQuickSearch);
            if (result.success) {
              set((state) => ({
                quickSearches: [...state.quickSearches, result.data],
              }));

              return Promise.resolve(quickSearchId);
            }
            throw new Error("Invalid quick search data");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to create quick search";
            set({ error: message });
            return Promise.resolve(null);
          }
        },

        deleteCollection: (collectionId) => {
          set({ isLoading: true });

          try {
            set((state) => ({
              isLoading: false,
              searchCollections: state.searchCollections.filter(
                (collection) => collection.id !== collectionId
              ),
            }));

            return Promise.resolve(true);
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to delete collection";
            set({ error: message, isLoading: false });
            return Promise.resolve(false);
          }
        },

        deleteQuickSearch: (quickSearchId) => {
          set((state) => ({
            quickSearches: state.quickSearches.filter(
              (quickSearch) => quickSearch.id !== quickSearchId
            ),
          }));
        },

        deleteSavedSearch: (searchId) => {
          set({ isLoading: true });

          try {
            set((state) => ({
              isLoading: false,
              savedSearches: state.savedSearches.filter(
                (search) => search.id !== searchId
              ),
              searchCollections: state.searchCollections.map((collection) => ({
                ...collection,
                searchIds: collection.searchIds.filter((id) => id !== searchId),
              })),
            }));

            return Promise.resolve(true);
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to delete search";
            set({ error: message, isLoading: false });
            return Promise.resolve(false);
          }
        },

        duplicateSavedSearch: async (searchId, newName) => {
          const { savedSearches } = get();
          const originalSearch = savedSearches.find((search) => search.id === searchId);

          if (!originalSearch) return null;

          return await get().saveSearch(
            newName,
            originalSearch.searchType,
            originalSearch.params as SearchParams,
            {
              description: originalSearch.description,
              isFavorite: false,
              isPublic: originalSearch.isPublic,
              tags: [...originalSearch.tags],
            }
          );
        },

        // Error states
        error: null,

        // Data management and sync
        exportSearchHistory: () => {
          const {
            savedSearches,
            searchCollections,
            quickSearches,
            popularSearchTerms,
          } = get();
          const exportData = {
            exportedAt: GET_CURRENT_TIMESTAMP(),
            popularSearchTerms,
            quickSearches,
            savedSearches,
            searchCollections,
            version: "1.0",
          };

          return JSON.stringify(exportData, null, 2);
        },

        get favoriteSearches() {
          return get().savedSearches.filter((search) => search.isFavorite);
        },

        getMostUsedSearches: (limit = 10) => {
          return get()
            .savedSearches.filter((search) => search.usageCount > 0)
            .sort((a, b) => b.usageCount - a.usageCount)
            .slice(0, limit);
        },

        getRecentSearchesByType: (searchType, limit = 10) => {
          return get()
            .recentSearches.filter((search) => search.searchType === searchType)
            .slice(0, limit);
        },

        getSavedSearchesByTag: (tag) => {
          return get().savedSearches.filter((search) => search.tags.includes(tag));
        },

        getSavedSearchesByType: (searchType) => {
          return get().savedSearches.filter(
            (search) => search.searchType === searchType
          );
        },

        // Analytics and insights
        getSearchAnalytics: (dateRange) => {
          const { recentSearches, savedSearches } = get();
          let filteredSearches = recentSearches;

          if (dateRange) {
            const startDate = new Date(dateRange.start);
            const endDate = new Date(dateRange.end);
            filteredSearches = recentSearches.filter((search) => {
              const searchDate = new Date(search.timestamp);
              return searchDate >= startDate && searchDate <= endDate;
            });
          }

          const totalSearches = filteredSearches.length;
          const searchesByType: Record<SearchType, number> = {
            accommodation: 0,
            activity: 0,
            destination: 0,
            flight: 0,
          };

          filteredSearches.forEach((search) => {
            searchesByType[search.searchType]++;
          });

          const averageSearchDuration =
            filteredSearches.reduce((sum, search) => {
              return sum + (search.searchDuration || 0);
            }, 0) / totalSearches || 0;

          const mostUsedSearchTypes = Object.entries(searchesByType)
            .map(([type, count]) => ({
              count,
              percentage: totalSearches > 0 ? (count / totalSearches) * 100 : 0,
              type: type as SearchType,
            }))
            .sort((a, b) => b.count - a.count);

          // Generate search trends (last 30 days)
          const searchTrends: Array<{ date: string; count: number }> = [];
          for (let i = 29; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split("T")[0];

            const count = filteredSearches.filter((search) =>
              search.timestamp.startsWith(dateStr)
            ).length;

            searchTrends.push({ count, date: dateStr });
          }

          // Popular search times (by hour)
          const popularSearchTimes: Array<{ hour: number; count: number }> = [];
          for (let hour = 0; hour < 24; hour++) {
            const count = filteredSearches.filter((search) => {
              const searchHour = new Date(search.timestamp).getHours();
              return searchHour === hour;
            }).length;

            popularSearchTimes.push({ count, hour });
          }

          return {
            averageSearchDuration,
            mostUsedSearchTypes,
            popularSearchTimes,
            savedSearchUsage: savedSearches
              .filter((search) => search.usageCount > 0)
              .sort((a, b) => b.usageCount - a.usageCount)
              .slice(0, 10)
              .map((search) => ({
                name: search.name,
                searchId: search.id,
                usageCount: search.usageCount,
              })),
            searchesByType,
            searchTrends,
            topDestinations: [], // Would be populated from actual search data
            totalSearches,
          };
        },

        // Search suggestions and auto-complete
        getSearchSuggestions: (query, searchType, limit = 10) => {
          const { searchSuggestions } = get();
          let filtered = searchSuggestions;

          if (query) {
            filtered = searchSuggestions.filter((suggestion) =>
              suggestion.text.toLowerCase().includes(query.toLowerCase())
            );
          }

          if (searchType) {
            filtered = filtered.filter(
              (suggestion) => suggestion.searchType === searchType
            );
          }

          return filtered
            .sort((a, b) => {
              // Sort by frequency and recency
              const frequencyScore = b.frequency - a.frequency;
              const recencyScore =
                new Date(b.lastUsed).getTime() - new Date(a.lastUsed).getTime();
              return frequencyScore * 0.7 + recencyScore * 0.3;
            })
            .slice(0, limit);
        },

        getSearchTrends: (searchType, days = 30) => {
          const { recentSearches } = get();
          const trends: Array<{ date: string; count: number }> = [];

          for (let i = days - 1; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split("T")[0];

            const count = recentSearches.filter((search) => {
              const matchesDate = search.timestamp.startsWith(dateStr);
              const matchesType = !searchType || search.searchType === searchType;
              return matchesDate && matchesType;
            }).length;

            trends.push({ count, date: dateStr });
          }

          return trends;
        },

        importSearchHistory: (data) => {
          set({ isLoading: true });

          try {
            const importData = JSON.parse(data);

            if (importData.savedSearches) {
              const validatedSearches = importData.savedSearches.filter(
                (search: unknown) => {
                  const result = SAVED_SEARCH_SCHEMA.safeParse(search);
                  return result.success;
                }
              );

              set((state) => ({
                savedSearches: [...state.savedSearches, ...validatedSearches],
              }));
            }

            if (importData.searchCollections) {
              const validatedCollections = importData.searchCollections.filter(
                (collection: unknown) => {
                  const result = SEARCH_COLLECTION_SCHEMA.safeParse(collection);
                  return result.success;
                }
              );

              set((state) => ({
                searchCollections: [
                  ...state.searchCollections,
                  ...validatedCollections,
                ],
              }));
            }

            if (importData.quickSearches) {
              const validatedQuickSearches = importData.quickSearches.filter(
                (quickSearch: unknown) => {
                  const result = QUICK_SEARCH_SCHEMA.safeParse(quickSearch);
                  return result.success;
                }
              );

              set((state) => ({
                quickSearches: [...state.quickSearches, ...validatedQuickSearches],
              }));
            }

            set({ isLoading: false });
            return Promise.resolve(true);
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : "Failed to import search history";
            set({ error: message, isLoading: false });
            return Promise.resolve(false);
          }
        },

        // Loading and sync states
        isLoading: false,
        isSyncing: false,
        lastSyncAt: null,

        markSearchAsUsed: (searchId) => {
          set((state) => ({
            savedSearches: state.savedSearches.map((search) =>
              search.id === searchId
                ? {
                    ...search,
                    lastUsed: GET_CURRENT_TIMESTAMP(),
                    usageCount: search.usageCount + 1,
                  }
                : search
            ),
          }));
        },

        // Settings
        maxRecentSearches: DEFAULT_MAX_RECENT_SEARCHES,
        popularSearchTerms: [],
        quickSearches: [],
        // Initial state
        recentSearches: [],

        get recentSearchesByType() {
          const { recentSearches } = get();
          const grouped: Record<SearchType, SearchHistoryItem[]> = {
            accommodation: [],
            activity: [],
            destination: [],
            flight: [],
          };

          recentSearches.forEach((search) => {
            grouped[search.searchType].push(search);
          });

          return grouped;
        },

        removeRecentSearch: (searchId) => {
          set((state) => ({
            recentSearches: state.recentSearches.filter(
              (search) => search.id !== searchId
            ),
          }));
        },

        removeSearchFromCollection: (collectionId, searchId) => {
          set((state) => ({
            searchCollections: state.searchCollections.map((collection) =>
              collection.id === collectionId
                ? {
                    ...collection,
                    searchIds: collection.searchIds.filter((id) => id !== searchId),
                    updatedAt: GET_CURRENT_TIMESTAMP(),
                  }
                : collection
            ),
          }));
        },

        reorderQuickSearches: (quickSearchIds) => {
          set((state) => {
            const reorderedQuickSearches = quickSearchIds
              .map((id, index) => {
                const quickSearch = state.quickSearches.find((qs) => qs.id === id);
                return quickSearch ? { ...quickSearch, sortOrder: index } : null;
              })
              .filter(Boolean) as QuickSearch[];

            return { quickSearches: reorderedQuickSearches };
          });
        },

        reset: () => {
          set({
            autoCleanupDays: DEFAULT_AUTO_CLEANUP_DAYS,
            autoSaveEnabled: true,
            error: null,
            isLoading: false,
            isSyncing: false,
            lastSyncAt: null,
            maxRecentSearches: DEFAULT_MAX_RECENT_SEARCHES,
            popularSearchTerms: [],
            quickSearches: [],
            recentSearches: [],
            savedSearches: [],
            searchCollections: [],
            searchSuggestions: [],
            syncError: null,
          });
        },
        savedSearches: [],

        // Saved search management
        saveSearch: (name, searchType, params, options = {}) => {
          set({ isLoading: true });

          try {
            const searchId = GENERATE_ID();
            const timestamp = GET_CURRENT_TIMESTAMP();

            const newSavedSearch: ValidatedSavedSearch = {
              createdAt: timestamp,
              description: options.description,
              id: searchId,
              isFavorite: options.isFavorite || false,
              isPublic: options.isPublic || false,
              metadata: {
                source: "manual",
                version: "1.0",
              },
              name,
              params: params as Record<string, unknown>,
              searchType,
              tags: options.tags || [],
              updatedAt: timestamp,
              usageCount: 0,
            };

            const result = SAVED_SEARCH_SCHEMA.safeParse(newSavedSearch);
            if (result.success) {
              set((state) => ({
                isLoading: false,
                savedSearches: [...state.savedSearches, result.data],
              }));

              return Promise.resolve(searchId);
            }
            throw new Error("Invalid saved search data");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to save search";
            set({ error: message, isLoading: false });
            return Promise.resolve(null);
          }
        },

        get searchAnalytics() {
          return get().getSearchAnalytics();
        },
        searchCollections: [],

        // Search and filtering
        searchSavedSearches: (query, filters = {}) => {
          const { savedSearches } = get();
          let filtered = savedSearches;

          if (query) {
            const queryLower = query.toLowerCase();
            filtered = filtered.filter(
              (search) =>
                search.name.toLowerCase().includes(queryLower) ||
                search.description?.toLowerCase().includes(queryLower) ||
                search.tags.some((tag) => tag.toLowerCase().includes(queryLower))
            );
          }

          if (filters.searchType) {
            filtered = filtered.filter(
              (search) => search.searchType === filters.searchType
            );
          }

          if (filters.tags && filters.tags.length > 0) {
            filtered = filtered.filter((search) =>
              filters.tags?.some((tag) => search.tags.includes(tag))
            );
          }

          if (filters.isFavorite !== undefined) {
            filtered = filtered.filter(
              (search) => search.isFavorite === filters.isFavorite
            );
          }

          return filtered.sort(
            (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
          );
        },

        // Search suggestions
        searchSuggestions: [],
        syncError: null,

        syncWithServer: async () => {
          set({ isSyncing: true, syncError: null });

          try {
            // Mock sync operation - replace with actual implementation
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({
              isSyncing: false,
              lastSyncAt: GET_CURRENT_TIMESTAMP(),
            });

            return true;
          } catch (error) {
            const message = error instanceof Error ? error.message : "Sync failed";
            set({
              isSyncing: false,
              syncError: message,
            });
            return false;
          }
        },

        toggleSearchFavorite: (searchId) => {
          set((state) => ({
            savedSearches: state.savedSearches.map((search) =>
              search.id === searchId
                ? { ...search, isFavorite: !search.isFavorite }
                : search
            ),
          }));
        },

        // Computed properties
        get totalSavedSearches() {
          return get().savedSearches.length;
        },

        updateCollection: (collectionId, updates) => {
          set({ isLoading: true });

          try {
            set((state) => {
              const updatedCollections = state.searchCollections.map((collection) => {
                if (collection.id === collectionId) {
                  const updatedCollection = {
                    ...collection,
                    ...updates,
                    updatedAt: GET_CURRENT_TIMESTAMP(),
                  };

                  const result = SEARCH_COLLECTION_SCHEMA.safeParse(updatedCollection);
                  return result.success ? result.data : collection;
                }
                return collection;
              });

              return {
                isLoading: false,
                searchCollections: updatedCollections,
              };
            });

            return Promise.resolve(true);
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update collection";
            set({ error: message, isLoading: false });
            return Promise.resolve(false);
          }
        },

        updateQuickSearch: (quickSearchId, updates) => {
          try {
            set((state) => ({
              quickSearches: state.quickSearches.map((quickSearch) => {
                if (quickSearch.id === quickSearchId) {
                  const updatedQuickSearch = { ...quickSearch, ...updates };
                  const result = QUICK_SEARCH_SCHEMA.safeParse(updatedQuickSearch);
                  return result.success ? result.data : quickSearch;
                }
                return quickSearch;
              }),
            }));

            return Promise.resolve(true);
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update quick search";
            set({ error: message });
            return Promise.resolve(false);
          }
        },

        updateSavedSearch: (searchId, updates) => {
          set({ isLoading: true });

          try {
            set((state) => {
              const updatedSearches = state.savedSearches.map((search) => {
                if (search.id === searchId) {
                  const updatedSearch = {
                    ...search,
                    ...updates,
                    updatedAt: GET_CURRENT_TIMESTAMP(),
                  };

                  const result = SAVED_SEARCH_SCHEMA.safeParse(updatedSearch);
                  return result.success ? result.data : search;
                }
                return search;
              });

              return {
                isLoading: false,
                savedSearches: updatedSearches,
              };
            });

            return Promise.resolve(true);
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update search";
            set({ error: message, isLoading: false });
            return Promise.resolve(false);
          }
        },

        updateSearchSuggestions: () => {
          const { recentSearches, savedSearches, popularSearchTerms } = get();
          const suggestions: SearchSuggestion[] = [];

          // Generate suggestions from recent searches
          recentSearches.forEach((search) => {
            const text = EXTRACT_SEARCH_TEXT(search.params);
            if (text) {
              suggestions.push({
                frequency: 1,
                id: `recent_${search.id}`,
                lastUsed: search.timestamp,
                searchType: search.searchType,
                source: "history",
                text,
              });
            }
          });

          // Generate suggestions from saved searches
          savedSearches.forEach((search) => {
            const text = EXTRACT_SEARCH_TEXT(search.params);
            if (text) {
              suggestions.push({
                frequency: search.usageCount,
                id: `saved_${search.id}`,
                lastUsed: search.lastUsed || search.createdAt,
                searchType: search.searchType,
                source: "saved",
                text,
              });
            }
          });

          // Add popular search terms
          popularSearchTerms.forEach((term) => {
            suggestions.push({
              frequency: term.count,
              id: `popular_${term.term}`,
              lastUsed: GET_CURRENT_TIMESTAMP(),
              searchType: term.searchType,
              source: "popular",
              text: term.term,
            });
          });

          // Deduplicate and limit
          const uniqueSuggestions = suggestions.reduce(
            (acc, suggestion) => {
              const key = `${suggestion.text}_${suggestion.searchType}`;
              if (!acc[key] || acc[key].frequency < suggestion.frequency) {
                acc[key] = suggestion;
              }
              return acc;
            },
            {} as Record<string, SearchSuggestion>
          );

          set({
            searchSuggestions: Object.values(uniqueSuggestions).slice(0, 100),
          });
        },

        // Settings management
        updateSettings: (settings) => {
          set((state) => ({
            autoCleanupDays: settings.autoCleanupDays ?? state.autoCleanupDays,
            autoSaveEnabled: settings.autoSaveEnabled ?? state.autoSaveEnabled,
            maxRecentSearches: settings.maxRecentSearches ?? state.maxRecentSearches,
          }));

          // Apply cleanup if enabled
          if (settings.autoCleanupDays !== undefined) {
            get().cleanupOldSearches();
          }
        },
      }),
      {
        name: "search-history-storage",
        partialize: (state) => ({
          autoCleanupDays: state.autoCleanupDays,
          autoSaveEnabled: state.autoSaveEnabled,
          lastSyncAt: state.lastSyncAt,
          maxRecentSearches: state.maxRecentSearches,
          popularSearchTerms: state.popularSearchTerms,
          quickSearches: state.quickSearches,
          // Persist all data except loading states
          recentSearches: state.recentSearches,
          savedSearches: state.savedSearches,
          searchCollections: state.searchCollections,
          searchSuggestions: state.searchSuggestions,
        }),
      }
    ),
    { name: "SearchHistoryStore" }
  )
);

/**
 * Extracts meaningful search text from search parameters.
 *
 * @param params - Search parameters object
 * @returns Extracted search text or empty string
 */
const EXTRACT_SEARCH_TEXT = (params: Record<string, unknown>): string => {
  // Extract meaningful text from search parameters
  const textFields = ["origin", "destination", "query", "location", "name"];

  for (const field of textFields) {
    if (params[field] && typeof params[field] === "string") {
      return params[field] as string;
    }
  }

  return "";
};

// Utility selectors for common use cases
export const useRecentSearches = (searchType?: SearchType, limit?: number) =>
  useSearchHistoryStore((state) =>
    searchType
      ? state.getRecentSearchesByType(searchType, limit)
      : state.recentSearches.slice(0, limit || 10)
  );

export const useSavedSearches = (searchType?: SearchType) =>
  useSearchHistoryStore((state) =>
    searchType ? state.getSavedSearchesByType(searchType) : state.savedSearches
  );

export const useFavoriteSearches = () =>
  useSearchHistoryStore((state) => state.favoriteSearches);

export const useSearchCollections = () =>
  useSearchHistoryStore((state) => state.searchCollections);

export const useQuickSearches = () =>
  useSearchHistoryStore((state) =>
    state.quickSearches
      .filter((qs) => qs.isVisible)
      .sort((a, b) => a.sortOrder - b.sortOrder)
  );

export const useSearchSuggestions = (
  query: string,
  searchType?: SearchType,
  limit?: number
) =>
  useSearchHistoryStore((state) =>
    state.getSearchSuggestions(query, searchType, limit)
  );

export const useSearchAnalytics = (dateRange?: { start: string; end: string }) =>
  useSearchHistoryStore((state) => state.getSearchAnalytics(dateRange));

export const useSearchHistoryLoading = () =>
  useSearchHistoryStore((state) => ({
    error: state.error,
    isLoading: state.isLoading,
    isSyncing: state.isSyncing,
    syncError: state.syncError,
  }));

/**
 * Compute recent searches grouped by type from a state snapshot.
 *
 * @param state - The search history store state snapshot.
 * @returns A map of search type to its recent searches.
 */
export const selectRecentSearchesByTypeFrom = (
  state: SearchHistoryState
): Record<SearchType, SearchHistoryItem[]> => {
  const grouped: Record<SearchType, SearchHistoryItem[]> = {
    accommodation: [],
    activity: [],
    destination: [],
    flight: [],
  };
  state.recentSearches.forEach((search) => {
    grouped[search.searchType].push(search);
  });
  return grouped;
};

/**
 * Compute favorite saved searches from a state snapshot.
 *
 * @param state - The search history store state snapshot.
 * @returns Saved searches marked as favorite.
 */
export const selectFavoriteSearchesFrom = (
  state: SearchHistoryState
): ValidatedSavedSearch[] => state.savedSearches.filter((s) => s.isFavorite);

/**
 * Compute the total number of saved searches from a state snapshot.
 *
 * @param state - The search history store state snapshot.
 * @returns The total saved search count.
 */
export const selectTotalSavedSearchesFrom = (state: SearchHistoryState): number =>
  state.savedSearches.length;
