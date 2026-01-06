/**
 * @fileoverview Computed state helpers for the search filters store.
 */

import { createComputeFn } from "@/stores/middleware/computed";
import { selectCurrentFilters } from "./selectors";
import type { SearchFiltersState } from "./types";

type RangeValue = { min?: number; max?: number };

function isRangeValue(value: unknown): value is RangeValue {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  if (!("min" in record) && !("max" in record)) return false;

  const isOptionalFiniteNumber = (item: unknown): item is number | undefined =>
    item === undefined || (typeof item === "number" && Number.isFinite(item));

  return isOptionalFiniteNumber(record.min) && isOptionalFiniteNumber(record.max);
}

export const computeFilterState = createComputeFn<SearchFiltersState>({
  appliedFilterSummary: (state) => {
    const currentFilters = selectCurrentFilters(state);
    const filterMap = new Map(currentFilters.map((filter) => [filter.id, filter]));
    const summaries: string[] = [];

    Object.entries(state.activeFilters || {}).forEach(([filterId, activeFilter]) => {
      const filter = filterMap.get(filterId);
      if (!filter) return;

      const valueStr = Array.isArray(activeFilter.value)
        ? activeFilter.value.join(", ")
        : isRangeValue(activeFilter.value)
          ? `${activeFilter.value.min ?? ""} - ${activeFilter.value.max ?? ""}`
          : String(activeFilter.value);

      summaries.push(`${filter.label}: ${valueStr}`);
    });

    return summaries.join("; ");
  },
});
