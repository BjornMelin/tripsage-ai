/**
 * @fileoverview Saved searches slice for search history store.
 */

import type { SearchParams } from "@schemas/search";
import type { ValidatedSavedSearch } from "@schemas/stores";
import { savedSearchSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { generateId, getCurrentTimestamp } from "@/features/shared/store/helpers";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import type { SavedSearchesSlice, SearchHistoryState } from "./types";

const logger = createStoreLogger({ storeName: "search-history" });

export const createSavedSearchesSlice: StateCreator<
  SearchHistoryState,
  [],
  [],
  SavedSearchesSlice
> = (set, get) => ({
  clearError: () => {
    set({ error: null });
  },

  deleteSavedSearch: (searchId) => {
    set({ isLoading: true });

    try {
      set((state) => ({
        isLoading: false,
        savedSearches: state.savedSearches.filter((search) => search.id !== searchId),
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
  error: null,

  getSavedSearchesByTag: (tag) => {
    return get().savedSearches.filter((search) => search.tags.includes(tag));
  },

  getSavedSearchesByType: (searchType) => {
    return get().savedSearches.filter((search) => search.searchType === searchType);
  },
  isLoading: false,

  markSearchAsUsed: (searchId) => {
    set((state) => ({
      savedSearches: state.savedSearches.map((search) =>
        search.id === searchId
          ? {
              ...search,
              lastUsed: getCurrentTimestamp(),
              usageCount: search.usageCount + 1,
            }
          : search
      ),
    }));
  },
  savedSearches: [],

  saveSearch: (name, searchType, params, options = {}) => {
    set({ isLoading: true });

    try {
      const searchId = generateId();
      const timestamp = getCurrentTimestamp();

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

      const result = savedSearchSchema.safeParse(newSavedSearch);
      if (result.success) {
        set((state) => ({
          isLoading: false,
          savedSearches: [...state.savedSearches, result.data],
        }));

        return Promise.resolve(searchId);
      }
      logger.error("Invalid saved search data", {
        error: result.error,
        input: newSavedSearch,
      });
      throw new Error("Invalid saved search data");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save search";
      set({ error: message, isLoading: false });
      return Promise.resolve(null);
    }
  },

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
      filtered = filtered.filter((search) => search.searchType === filters.searchType);
    }

    if (filters.tags && filters.tags.length > 0) {
      filtered = filtered.filter((search) =>
        filters.tags?.some((tag) => search.tags.includes(tag))
      );
    }

    if (filters.isFavorite !== undefined) {
      filtered = filtered.filter((search) => search.isFavorite === filters.isFavorite);
    }

    return filtered.sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  },

  toggleSearchFavorite: (searchId) => {
    set((state) => ({
      savedSearches: state.savedSearches.map((search) =>
        search.id === searchId ? { ...search, isFavorite: !search.isFavorite } : search
      ),
    }));
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
              updatedAt: getCurrentTimestamp(),
            };

            const result = savedSearchSchema.safeParse(updatedSearch);
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
});
