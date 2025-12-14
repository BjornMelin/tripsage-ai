/**
 * @fileoverview Collections slice for search history store.
 */

import type { SearchCollection } from "@schemas/stores";
import { searchCollectionSchema } from "@schemas/stores";
import type { StateCreator } from "zustand";
import { unique } from "@/lib/collection-utils";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { generateId, getCurrentTimestamp } from "../helpers";
import type { CollectionsSlice, SearchHistoryState } from "./types";

const logger = createStoreLogger({ storeName: "search-history" });

export const createCollectionsSlice: StateCreator<
  SearchHistoryState,
  [],
  [],
  CollectionsSlice
> = (set, _get) => ({
  addSearchToCollection: (collectionId, searchId) => {
    set((state) => ({
      searchCollections: state.searchCollections.map((collection) =>
        collection.id === collectionId
          ? {
              ...collection,
              searchIds: unique([...collection.searchIds, searchId]),
              updatedAt: getCurrentTimestamp(),
            }
          : collection
      ),
    }));
  },

  createCollection: (name, description, searchIds = []) => {
    set({ isLoading: true });

    try {
      const collectionId = generateId();
      const timestamp = getCurrentTimestamp();

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

      const result = searchCollectionSchema.safeParse(newCollection);
      if (result.success) {
        set((state) => ({
          isLoading: false,
          searchCollections: [...state.searchCollections, result.data],
        }));

        return Promise.resolve(collectionId);
      }
      logger.error("Invalid collection data", {
        error: result.error,
        input: newCollection,
      });
      throw new Error("Invalid collection data");
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create collection";
      set({ error: message, isLoading: false });
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
  searchCollections: [],

  updateCollection: (collectionId, updates) => {
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

            const result = searchCollectionSchema.safeParse(updatedCollection);
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
});
