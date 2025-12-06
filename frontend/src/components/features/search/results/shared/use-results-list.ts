/**
 * @fileoverview Shared hook for results list state management.
 *
 * Encapsulates common patterns across flight/hotel/activity results:
 * - Sorting with configurable fields and direction
 * - View mode toggling (list/grid)
 * - Selection set for comparison or wishlist
 * - Optimistic selection with transition
 */

"use client";

import { useCallback, useMemo, useOptimistic, useState, useTransition } from "react";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

/** View mode options for results display. */
export type ViewMode = "list" | "grid" | "map";

/** Sort direction options. */
export type SortDirection = "asc" | "desc";

/** Configuration for the useResultsList hook. */
export interface UseResultsListOptions<T, S extends string> {
  /** Array of results to manage. */
  results: T[];
  /** Function to extract unique ID from an item. */
  getId: (item: T) => string;
  /** Default sort field. */
  defaultSort: S;
  /** Default sort direction. */
  defaultDirection?: SortDirection;
  /** Default view mode. */
  defaultViewMode?: ViewMode;
  /** Comparator function for sorting. */
  compare: (a: T, b: T, sortBy: S, direction: SortDirection) => number;
  /** Maximum items that can be selected for comparison. */
  maxSelections?: number;
  /** Context name for error logging. */
  errorContext?: string;
}

/** Return type for the useResultsList hook. */
export interface UseResultsListReturn<T, S extends string> {
  /** Sorted results array. */
  sortedResults: T[];
  /** Current sort field. */
  sortBy: S;
  /** Current sort direction. */
  sortDirection: SortDirection;
  /** Current view mode. */
  viewMode: ViewMode;
  /** Whether a transition is pending. */
  isPending: boolean;
  /** Set of selected item IDs. */
  selectedIds: Set<string>;
  /** ID of item currently being optimistically selected. */
  optimisticSelectingId: string;

  /** Set the sort field. */
  setSortBy: (field: S) => void;
  /** Toggle sort direction between asc and desc. */
  toggleSortDirection: () => void;
  /** Set sort direction explicitly. */
  setSortDirection: (direction: SortDirection) => void;
  /** Set view mode. */
  setViewMode: (mode: ViewMode) => void;
  /** Toggle an item in the selection set. */
  toggleSelection: (id: string) => void;
  /** Clear all selections. */
  clearSelection: () => void;
  /** Check if an item is selected. */
  isSelected: (id: string) => boolean;
  /** Get selected items from the results. */
  getSelectedItems: () => T[];
  /**
   * Handle item selection with optimistic UI and error handling.
   * Wraps the async callback in a transition.
   */
  handleSelect: (item: T, onSelect: (item: T) => Promise<void>) => void;
}

/**
 * Hook for managing results list state.
 *
 * Consolidates common patterns from flight/hotel/activity results:
 * - Sorting logic with configurable comparator
 * - View mode toggling
 * - Selection management for comparison features
 * - Optimistic selection with React transitions
 *
 * @example
 * ```tsx
 * const {
 *   sortedResults,
 *   sortBy,
 *   setSortBy,
 *   viewMode,
 *   setViewMode,
 *   handleSelect,
 * } = useResultsList({
 *   results: flights,
 *   getId: (f) => f.id,
 *   defaultSort: "price",
 *   compare: (a, b, sortBy, dir) => {
 *     const mul = dir === "asc" ? 1 : -1;
 *     return mul * (a.price - b.price);
 *   },
 *   errorContext: "FlightResults",
 * });
 * ```
 */
export function useResultsList<T, S extends string>({
  results,
  getId,
  defaultSort,
  defaultDirection = "asc",
  defaultViewMode = "list",
  compare,
  maxSelections = 3,
  errorContext = "ResultsList",
}: UseResultsListOptions<T, S>): UseResultsListReturn<T, S> {
  const [isPending, startTransition] = useTransition();
  const [sortBy, setSortBy] = useState<S>(defaultSort);
  const [sortDirection, setSortDirection] = useState<SortDirection>(defaultDirection);
  const [viewMode, setViewMode] = useState<ViewMode>(defaultViewMode);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

  // Optimistic selection state
  const [optimisticSelectingId, setOptimisticSelectingId] = useOptimistic(
    "",
    (_state, id: string) => id
  );

  // Memoized sorted results
  const sortedResults = useMemo(() => {
    const cloned = [...results];
    return cloned.sort((a, b) => compare(a, b, sortBy, sortDirection));
  }, [results, sortBy, sortDirection, compare]);

  // Toggle sort direction
  const toggleSortDirection = useCallback(() => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  }, []);

  // Toggle selection for comparison/wishlist
  const toggleSelection = useCallback(
    (id: string) => {
      setSelectedIds((prev) => {
        const newSet = new Set(prev);
        if (newSet.has(id)) {
          newSet.delete(id);
        } else if (newSet.size < maxSelections) {
          newSet.add(id);
        }
        return newSet;
      });
    },
    [maxSelections]
  );

  // Clear all selections
  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Check if item is selected
  const isSelected = useCallback((id: string) => selectedIds.has(id), [selectedIds]);

  // Get selected items
  const getSelectedItems = useCallback(() => {
    return sortedResults.filter((item) => selectedIds.has(getId(item)));
  }, [sortedResults, selectedIds, getId]);

  // Handle item selection with optimistic UI
  const handleSelect = useCallback(
    (item: T, onSelect: (item: T) => Promise<void>) => {
      const itemId = getId(item);
      startTransition(async () => {
        setOptimisticSelectingId(itemId);
        try {
          await onSelect(item);
        } catch (error) {
          recordClientErrorOnActiveSpan(
            error instanceof Error ? error : new Error(String(error)),
            {
              action: "handleSelect",
              context: errorContext,
              itemId,
            }
          );
        } finally {
          setOptimisticSelectingId("");
        }
      });
    },
    [getId, errorContext, setOptimisticSelectingId]
  );

  return {
    clearSelection,
    getSelectedItems,
    handleSelect,
    isPending,
    isSelected,
    optimisticSelectingId,
    selectedIds,
    setSortBy,
    setSortDirection,
    setViewMode,
    sortBy,
    sortDirection,
    sortedResults,
    toggleSelection,
    toggleSortDirection,
    viewMode,
  };
}
