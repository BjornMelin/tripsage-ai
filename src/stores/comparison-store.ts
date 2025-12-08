/**
 * @fileoverview Zustand store for managing comparison items across search types.
 *
 * Replaces sessionStorage-based comparison lists with a centralized store that
 * supports cross-type comparisons, persistence, and computed derived state.
 */

import type {
  Accommodation,
  Activity,
  Destination,
  FlightResult,
  SearchType,
} from "@schemas/search";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { nowIso } from "@/lib/security/random";
import { withComputed } from "./middleware/computed";

type ComparisonData<T extends SearchType> = T extends "flight"
  ? FlightResult
  : T extends "accommodation"
    ? Accommodation
    : T extends "activity"
      ? Activity
      : T extends "destination"
        ? Destination
        : unknown;

/** Single item in the comparison list. */
export interface ComparisonItem<T extends SearchType = SearchType> {
  id: string;
  type: T;
  data: ComparisonData<T>;
  addedAt: string;
}

/** Core state for comparison management. */
interface ComparisonState {
  items: ComparisonItem[];
  maxItems: number;

  // Actions
  addItem: <T extends SearchType>(
    type: T,
    id: string,
    data: ComparisonData<T> | Record<string, unknown>
  ) => boolean;
  removeItem: (id: string) => void;
  clearByType: (type: SearchType) => void;
  clearAll: () => void;
  hasItem: (id: string) => boolean;
  getItemsByType: (type: SearchType) => ComparisonItem[];
  reset: () => void;
}

/** Computed derived state. */
interface ComputedState {
  itemCount: number;
  canAdd: boolean;
  itemsByTypeMap: Map<SearchType, ComparisonItem[]>;
  idsSet: Set<string>;
}

const DEFAULT_MAX_ITEMS = 3;

const initialState = {
  items: [] as ComparisonItem[],
  maxItems: DEFAULT_MAX_ITEMS,
};

export const useComparisonStore = create<ComparisonState & ComputedState>()(
  devtools(
    persist(
      withComputed<ComparisonState & ComputedState>(
        {
          compute: (state) => {
            const itemsByTypeMap = new Map<SearchType, ComparisonItem[]>();
            const idsSet = new Set<string>();

            for (const item of state.items) {
              idsSet.add(item.id);
              const existing = itemsByTypeMap.get(item.type);
              if (existing) {
                existing.push(item);
              } else {
                itemsByTypeMap.set(item.type, [item]);
              }
            }

            return {
              canAdd: state.items.length < state.maxItems,
              idsSet,
              itemCount: state.items.length,
              itemsByTypeMap,
            };
          },
        },
        (set, get) => ({
          ...initialState,

          addItem: <T extends SearchType>(
            type: T,
            id: string,
            data: ComparisonData<T> | Record<string, unknown>
          ): boolean => {
            const { items, maxItems, idsSet } = get();

            // Check if already at max or item exists
            if (items.length >= maxItems) return false;
            if (idsSet.has(id)) return false;

            const newItem: ComparisonItem<T> = {
              addedAt: nowIso(),
              data: data as ComparisonData<T>,
              id,
              type,
            };

            set((state) => ({
              items: [...state.items, newItem],
            }));

            return true;
          },

          // Computed properties (initialized, will be overwritten by middleware)
          canAdd: true,

          clearAll: (): void => {
            set({ items: [] });
          },

          clearByType: (type: SearchType): void => {
            set((state) => ({
              items: state.items.filter((item) => item.type !== type),
            }));
          },

          getItemsByType: (type: SearchType): ComparisonItem[] => {
            const fromMap = get().itemsByTypeMap.get(type);
            return fromMap ?? [];
          },

          hasItem: (id: string): boolean => {
            return get().idsSet.has(id);
          },
          idsSet: new Set<string>(),
          itemCount: 0,
          itemsByTypeMap: new Map<SearchType, ComparisonItem[]>(),

          removeItem: (id: string): void => {
            set((state) => ({
              items: state.items.filter((item) => item.id !== id),
            }));
          },

          reset: (): void => {
            set(initialState);
          },
        })
      ),
      {
        name: "comparison-storage",
        partialize: (state) => ({
          items: state.items,
          maxItems: state.maxItems,
        }),
      }
    ),
    { name: "ComparisonStore" }
  )
);

// Utility selectors
export const useComparisonItems = () => useComparisonStore((state) => state.items);

export const useComparisonItemCount = () =>
  useComparisonStore((state) => state.itemCount);

export const useCanAddComparison = () => useComparisonStore((state) => state.canAdd);

export const useComparisonItemsByType = (type: SearchType) =>
  useComparisonStore((state) => state.getItemsByType(type));

export const useHasComparisonItem = (id: string) =>
  useComparisonStore((state) => state.hasItem(id));
