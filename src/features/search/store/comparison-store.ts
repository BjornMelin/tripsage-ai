/**
 * @fileoverview Zustand store for managing comparison items across search types.
 */

import {
  type Accommodation,
  type Activity,
  accommodationSchema,
  activitySchema,
  type Destination,
  destinationSchema,
  type FlightResult,
  flightResultSchema,
  type SearchType,
} from "@schemas/search";
import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { nowIso } from "@/lib/security/random";
import { withComputed } from "@/stores/middleware/computed";

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
const EMPTY_COMPARISON_ITEMS: ComparisonItem[] = [];
const PERSISTED_COMPARISON_ITEM_SCHEMA = z
  .discriminatedUnion("type", [
    z.strictObject({
      addedAt: z.iso.datetime(),
      data: flightResultSchema,
      id: z.string().min(1),
      type: z.literal("flight"),
    }),
    z.strictObject({
      addedAt: z.iso.datetime(),
      data: accommodationSchema,
      id: z.string().min(1),
      type: z.literal("accommodation"),
    }),
    z.strictObject({
      addedAt: z.iso.datetime(),
      data: activitySchema,
      id: z.string().min(1),
      type: z.literal("activity"),
    }),
    z.strictObject({
      addedAt: z.iso.datetime(),
      data: destinationSchema,
      id: z.string().min(1),
      type: z.literal("destination"),
    }),
  ])
  .refine((item) => item.id === item.data.id, {
    error: "Persisted comparison item IDs must match their data IDs",
    path: ["id"],
  });
const PERSISTED_COMPARISON_ITEMS_SCHEMA = z
  .array(PERSISTED_COMPARISON_ITEM_SCHEMA)
  .max(DEFAULT_MAX_ITEMS)
  .refine((items) => new Set(items.map((item) => item.id)).size === items.length, {
    error: "Persisted comparison item IDs must be unique",
  });
const PERSISTED_COMPARISON_STATE_SCHEMA = z.strictObject({
  items: PERSISTED_COMPARISON_ITEMS_SCHEMA.optional(),
  // Accepted only so existing snapshots retain valid items; policy is never restored.
  maxItems: z.unknown().optional(),
});

const initialState = {
  items: [] as ComparisonItem[],
  maxItems: DEFAULT_MAX_ITEMS,
};

function computeComparisonState(
  state: Pick<ComparisonState, "items" | "maxItems">
): ComputedState {
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
}

/** Persisted comparison store with derived lookup state. */
export const useComparisonStore = create<ComparisonState & ComputedState>()(
  devtools(
    persist(
      withComputed<ComparisonState & ComputedState>(
        {
          compute: computeComparisonState,
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
        merge: (persistedState, currentState) => {
          const restoredState = PERSISTED_COMPARISON_STATE_SCHEMA.safeParse(
            persistedState ?? {}
          );
          const mergedState = {
            ...currentState,
            items:
              restoredState.success && restoredState.data.items
                ? restoredState.data.items
                : currentState.items,
          };

          return {
            ...mergedState,
            ...computeComparisonState(mergedState),
          };
        },
        name: "comparison-storage",
        partialize: (state) => ({
          items: state.items,
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
  useComparisonStore(
    (state) => state.itemsByTypeMap.get(type) ?? EMPTY_COMPARISON_ITEMS
  );

export const useHasComparisonItem = (id: string) =>
  useComparisonStore((state) => state.hasItem(id));
