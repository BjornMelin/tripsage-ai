import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import type { SearchParams, SearchType } from "@/types/search";

// Validation schemas for search history
const SearchTypeSchema = z.enum(["flight", "accommodation", "activity", "destination"]);

const SearchHistoryItemSchema = z.object({
  id: z.string(),
  searchType: SearchTypeSchema,
  params: z.record(z.unknown()),
  timestamp: z.string(),
  resultsCount: z.number().min(0).optional(),
  searchDuration: z.number().min(0).optional(),
  userAgent: z.string().optional(),
  location: z
    .object({
      country: z.string().optional(),
      city: z.string().optional(),
      coordinates: z
        .object({
          lat: z.number(),
          lng: z.number(),
        })
        .optional(),
    })
    .optional(),
});

const SavedSearchSchema = z.object({
  id: z.string(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  searchType: SearchTypeSchema,
  params: z.record(z.unknown()),
  tags: z.array(z.string()).default([]),
  isPublic: z.boolean().default(false),
  isFavorite: z.boolean().default(false),
  createdAt: z.string(),
  updatedAt: z.string(),
  lastUsed: z.string().optional(),
  usageCount: z.number().min(0).default(0),
  metadata: z
    .object({
      version: z.string().default("1.0"),
      source: z.string().optional(), // e.g., "manual", "auto-save", "import"
      originalSearchId: z.string().optional(),
    })
    .optional(),
});

const SearchCollectionSchema = z.object({
  id: z.string(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  searchIds: z.array(z.string()),
  tags: z.array(z.string()).default([]),
  isPublic: z.boolean().default(false),
  createdAt: z.string(),
  updatedAt: z.string(),
  createdBy: z.string().optional(),
});

const QuickSearchSchema = z.object({
  id: z.string(),
  label: z.string().min(1).max(50),
  searchType: SearchTypeSchema,
  params: z.record(z.unknown()),
  icon: z.string().optional(),
  color: z.string().optional(),
  sortOrder: z.number().default(0),
  isVisible: z.boolean().default(true),
  createdAt: z.string(),
});

// Types derived from schemas
export type SearchHistoryItem = z.infer<typeof SearchHistoryItemSchema>;
export type ValidatedSavedSearch = z.infer<typeof SavedSearchSchema>;
export type SearchCollection = z.infer<typeof SearchCollectionSchema>;
export type QuickSearch = z.infer<typeof QuickSearchSchema>;

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
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Default settings
const DEFAULT_MAX_RECENT_SEARCHES = 50;
const DEFAULT_AUTO_CLEANUP_DAYS = 30;

export const useSearchHistoryStore = create<SearchHistoryState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        recentSearches: [],
        savedSearches: [],
        searchCollections: [],
        quickSearches: [],

        // Search suggestions
        searchSuggestions: [],
        popularSearchTerms: [],

        // Settings
        maxRecentSearches: DEFAULT_MAX_RECENT_SEARCHES,
        autoSaveEnabled: true,
        autoCleanupDays: DEFAULT_AUTO_CLEANUP_DAYS,

        // Loading and sync states
        isLoading: false,
        isSyncing: false,
        lastSyncAt: null,

        // Error states
        error: null,
        syncError: null,

        // Computed properties
        get totalSavedSearches() {
          return get().savedSearches.length;
        },

        get recentSearchesByType() {
          const { recentSearches } = get();
          const grouped: Record<SearchType, SearchHistoryItem[]> = {
            flight: [],
            accommodation: [],
            activity: [],
            destination: [],
          };

          recentSearches.forEach((search) => {
            grouped[search.searchType].push(search);
          });

          return grouped;
        },

        get favoriteSearches() {
          return get().savedSearches.filter((search) => search.isFavorite);
        },

        get searchAnalytics() {
          return get().getSearchAnalytics();
        },

        // Recent search management
        addRecentSearch: (searchType, params, metadata = {}) => {
          const { maxRecentSearches, recentSearches } = get();
          const timestamp = getCurrentTimestamp();

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
            id: generateId(),
            searchType,
            params: params as Record<string, unknown>,
            timestamp,
            ...metadata,
          };

          const result = SearchHistoryItemSchema.safeParse(newSearch);
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

        removeRecentSearch: (searchId) => {
          set((state) => ({
            recentSearches: state.recentSearches.filter(
              (search) => search.id !== searchId
            ),
          }));
        },

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

        // Saved search management
        saveSearch: async (name, searchType, params, options = {}) => {
          set({ isLoading: true });

          try {
            const searchId = generateId();
            const timestamp = getCurrentTimestamp();

            const newSavedSearch: ValidatedSavedSearch = {
              id: searchId,
              name,
              description: options.description,
              searchType,
              params: params as Record<string, unknown>,
              tags: options.tags || [],
              isPublic: options.isPublic || false,
              isFavorite: options.isFavorite || false,
              createdAt: timestamp,
              updatedAt: timestamp,
              usageCount: 0,
              metadata: {
                version: "1.0",
                source: "manual",
              },
            };

            const result = SavedSearchSchema.safeParse(newSavedSearch);
            if (result.success) {
              set((state) => ({
                savedSearches: [...state.savedSearches, result.data],
                isLoading: false,
              }));

              return searchId;
            }
            throw new Error("Invalid saved search data");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to save search";
            set({ error: message, isLoading: false });
            return null;
          }
        },

        updateSavedSearch: async (searchId, updates) => {
          set({ isLoading: true });

          try {
            set((state) => {
              const updatedSearches = state.savedSearches.map((search) => {
                if (search.id === searchId) {
                  const updatedSearch = {
                    ...search,
                    ...updates,
                    updatedAt: getCurrentTimestamp(),
                  };

                  const result = SavedSearchSchema.safeParse(updatedSearch);
                  return result.success ? result.data : search;
                }
                return search;
              });

              return {
                savedSearches: updatedSearches,
                isLoading: false,
              };
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update search";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        deleteSavedSearch: async (searchId) => {
          set({ isLoading: true });

          try {
            set((state) => ({
              savedSearches: state.savedSearches.filter(
                (search) => search.id !== searchId
              ),
              searchCollections: state.searchCollections.map((collection) => ({
                ...collection,
                searchIds: collection.searchIds.filter((id) => id !== searchId),
              })),
              isLoading: false,
            }));

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to delete search";
            set({ error: message, isLoading: false });
            return false;
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
              tags: [...originalSearch.tags],
              isFavorite: false,
              isPublic: originalSearch.isPublic,
            }
          );
        },

        markSearchAsUsed: (searchId) => {
          set((state) => ({
            savedSearches: state.savedSearches.map((search) =>
              search.id === searchId
                ? {
                    ...search,
                    usageCount: search.usageCount + 1,
                    lastUsed: getCurrentTimestamp(),
                  }
                : search
            ),
          }));
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

        // Search collections
        createCollection: async (name, description, searchIds = []) => {
          set({ isLoading: true });

          try {
            const collectionId = generateId();
            const timestamp = getCurrentTimestamp();

            const newCollection: SearchCollection = {
              id: collectionId,
              name,
              description,
              searchIds,
              tags: [],
              isPublic: false,
              createdAt: timestamp,
              updatedAt: timestamp,
            };

            const result = SearchCollectionSchema.safeParse(newCollection);
            if (result.success) {
              set((state) => ({
                searchCollections: [...state.searchCollections, result.data],
                isLoading: false,
              }));

              return collectionId;
            }
            throw new Error("Invalid collection data");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to create collection";
            set({ error: message, isLoading: false });
            return null;
          }
        },

        updateCollection: async (collectionId, updates) => {
          set({ isLoading: true });

          try {
            set((state) => {
              const updatedCollections = state.searchCollections.map((collection) => {
                if (collection.id === collectionId) {
                  const updatedCollection = {
                    ...collection,
                    ...updates,
                    updatedAt: getCurrentTimestamp(),
                  };

                  const result = SearchCollectionSchema.safeParse(updatedCollection);
                  return result.success ? result.data : collection;
                }
                return collection;
              });

              return {
                searchCollections: updatedCollections,
                isLoading: false,
              };
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update collection";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        deleteCollection: async (collectionId) => {
          set({ isLoading: true });

          try {
            set((state) => ({
              searchCollections: state.searchCollections.filter(
                (collection) => collection.id !== collectionId
              ),
              isLoading: false,
            }));

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to delete collection";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        addSearchToCollection: (collectionId, searchId) => {
          set((state) => ({
            searchCollections: state.searchCollections.map((collection) =>
              collection.id === collectionId
                ? {
                    ...collection,
                    searchIds: [...new Set([...collection.searchIds, searchId])],
                    updatedAt: getCurrentTimestamp(),
                  }
                : collection
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
                    updatedAt: getCurrentTimestamp(),
                  }
                : collection
            ),
          }));
        },

        // Quick searches
        createQuickSearch: async (label, searchType, params, options = {}) => {
          try {
            const quickSearchId = generateId();
            const timestamp = getCurrentTimestamp();

            const newQuickSearch: QuickSearch = {
              id: quickSearchId,
              label,
              searchType,
              params: params as Record<string, unknown>,
              icon: options.icon,
              color: options.color,
              sortOrder: options.sortOrder || get().quickSearches.length,
              isVisible: true,
              createdAt: timestamp,
            };

            const result = QuickSearchSchema.safeParse(newQuickSearch);
            if (result.success) {
              set((state) => ({
                quickSearches: [...state.quickSearches, result.data],
              }));

              return quickSearchId;
            }
            throw new Error("Invalid quick search data");
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to create quick search";
            set({ error: message });
            return null;
          }
        },

        updateQuickSearch: async (quickSearchId, updates) => {
          try {
            set((state) => ({
              quickSearches: state.quickSearches.map((quickSearch) => {
                if (quickSearch.id === quickSearchId) {
                  const updatedQuickSearch = { ...quickSearch, ...updates };
                  const result = QuickSearchSchema.safeParse(updatedQuickSearch);
                  return result.success ? result.data : quickSearch;
                }
                return quickSearch;
              }),
            }));

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update quick search";
            set({ error: message });
            return false;
          }
        },

        deleteQuickSearch: (quickSearchId) => {
          set((state) => ({
            quickSearches: state.quickSearches.filter(
              (quickSearch) => quickSearch.id !== quickSearchId
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

        updateSearchSuggestions: () => {
          const { recentSearches, savedSearches, popularSearchTerms } = get();
          const suggestions: SearchSuggestion[] = [];

          // Generate suggestions from recent searches
          recentSearches.forEach((search) => {
            const text = extractSearchText(search.params);
            if (text) {
              suggestions.push({
                id: `recent_${search.id}`,
                text,
                searchType: search.searchType,
                frequency: 1,
                lastUsed: search.timestamp,
                source: "history",
              });
            }
          });

          // Generate suggestions from saved searches
          savedSearches.forEach((search) => {
            const text = extractSearchText(search.params);
            if (text) {
              suggestions.push({
                id: `saved_${search.id}`,
                text,
                searchType: search.searchType,
                frequency: search.usageCount,
                lastUsed: search.lastUsed || search.createdAt,
                source: "saved",
              });
            }
          });

          // Add popular search terms
          popularSearchTerms.forEach((term) => {
            suggestions.push({
              id: `popular_${term.term}`,
              text: term.term,
              searchType: term.searchType,
              frequency: term.count,
              lastUsed: getCurrentTimestamp(),
              source: "popular",
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
                { term, count: 1, searchType },
              ].slice(0, 200), // Keep top 200 terms
            };
          });
        },

        // Data management and sync
        exportSearchHistory: () => {
          const {
            savedSearches,
            searchCollections,
            quickSearches,
            popularSearchTerms,
          } = get();
          const exportData = {
            savedSearches,
            searchCollections,
            quickSearches,
            popularSearchTerms,
            exportedAt: getCurrentTimestamp(),
            version: "1.0",
          };

          return JSON.stringify(exportData, null, 2);
        },

        importSearchHistory: async (data) => {
          set({ isLoading: true });

          try {
            const importData = JSON.parse(data);

            if (importData.savedSearches) {
              const validatedSearches = importData.savedSearches.filter(
                (search: unknown) => {
                  const result = SavedSearchSchema.safeParse(search);
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
                  const result = SearchCollectionSchema.safeParse(collection);
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
                  const result = QuickSearchSchema.safeParse(quickSearch);
                  return result.success;
                }
              );

              set((state) => ({
                quickSearches: [...state.quickSearches, ...validatedQuickSearches],
              }));
            }

            set({ isLoading: false });
            return true;
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : "Failed to import search history";
            set({ error: message, isLoading: false });
            return false;
          }
        },

        syncWithServer: async () => {
          set({ isSyncing: true, syncError: null });

          try {
            // Mock sync operation - replace with actual implementation
            await new Promise((resolve) => setTimeout(resolve, 1000));

            set({
              isSyncing: false,
              lastSyncAt: getCurrentTimestamp(),
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

        getSavedSearchesByType: (searchType) => {
          return get().savedSearches.filter(
            (search) => search.searchType === searchType
          );
        },

        getSavedSearchesByTag: (tag) => {
          return get().savedSearches.filter((search) => search.tags.includes(tag));
        },

        getRecentSearchesByType: (searchType, limit = 10) => {
          return get()
            .recentSearches.filter((search) => search.searchType === searchType)
            .slice(0, limit);
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
            flight: 0,
            accommodation: 0,
            activity: 0,
            destination: 0,
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
              type: type as SearchType,
              count,
              percentage: totalSearches > 0 ? (count / totalSearches) * 100 : 0,
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

            searchTrends.push({ date: dateStr, count });
          }

          // Popular search times (by hour)
          const popularSearchTimes: Array<{ hour: number; count: number }> = [];
          for (let hour = 0; hour < 24; hour++) {
            const count = filteredSearches.filter((search) => {
              const searchHour = new Date(search.timestamp).getHours();
              return searchHour === hour;
            }).length;

            popularSearchTimes.push({ hour, count });
          }

          return {
            totalSearches,
            searchesByType,
            averageSearchDuration,
            mostUsedSearchTypes,
            searchTrends,
            popularSearchTimes,
            topDestinations: [], // Would be populated from actual search data
            savedSearchUsage: savedSearches
              .filter((search) => search.usageCount > 0)
              .sort((a, b) => b.usageCount - a.usageCount)
              .slice(0, 10)
              .map((search) => ({
                searchId: search.id,
                name: search.name,
                usageCount: search.usageCount,
              })),
          };
        },

        getMostUsedSearches: (limit = 10) => {
          return get()
            .savedSearches.filter((search) => search.usageCount > 0)
            .sort((a, b) => b.usageCount - a.usageCount)
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

            trends.push({ date: dateStr, count });
          }

          return trends;
        },

        // Settings management
        updateSettings: (settings) => {
          set((state) => ({
            maxRecentSearches: settings.maxRecentSearches ?? state.maxRecentSearches,
            autoSaveEnabled: settings.autoSaveEnabled ?? state.autoSaveEnabled,
            autoCleanupDays: settings.autoCleanupDays ?? state.autoCleanupDays,
          }));

          // Apply cleanup if enabled
          if (settings.autoCleanupDays !== undefined) {
            get().cleanupOldSearches();
          }
        },

        // Utility actions
        clearAllData: () => {
          set({
            recentSearches: [],
            savedSearches: [],
            searchCollections: [],
            quickSearches: [],
            searchSuggestions: [],
            popularSearchTerms: [],
          });
        },

        clearError: () => {
          set({ error: null, syncError: null });
        },

        reset: () => {
          set({
            recentSearches: [],
            savedSearches: [],
            searchCollections: [],
            quickSearches: [],
            searchSuggestions: [],
            popularSearchTerms: [],
            maxRecentSearches: DEFAULT_MAX_RECENT_SEARCHES,
            autoSaveEnabled: true,
            autoCleanupDays: DEFAULT_AUTO_CLEANUP_DAYS,
            isLoading: false,
            isSyncing: false,
            lastSyncAt: null,
            error: null,
            syncError: null,
          });
        },
      }),
      {
        name: "search-history-storage",
        partialize: (state) => ({
          // Persist all data except loading states
          recentSearches: state.recentSearches,
          savedSearches: state.savedSearches,
          searchCollections: state.searchCollections,
          quickSearches: state.quickSearches,
          searchSuggestions: state.searchSuggestions,
          popularSearchTerms: state.popularSearchTerms,
          maxRecentSearches: state.maxRecentSearches,
          autoSaveEnabled: state.autoSaveEnabled,
          autoCleanupDays: state.autoCleanupDays,
          lastSyncAt: state.lastSyncAt,
        }),
      }
    ),
    { name: "SearchHistoryStore" }
  )
);

// Helper function to extract search text from params
const extractSearchText = (params: Record<string, unknown>): string => {
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
    isLoading: state.isLoading,
    isSyncing: state.isSyncing,
    error: state.error,
    syncError: state.syncError,
  }));
