/**
 * @fileoverview Factory for creating Filter and Sort test data.
 */

export interface FilterOption {
  id: string;
  category: string;
  label: string;
  value: string | number | boolean;
  enabled?: boolean;
}

export interface SortOption {
  id: string;
  field: string;
  direction: "asc" | "desc";
  label?: string;
}

export interface FilterPreset {
  id: string;
  name: string;
  filters: FilterOption[];
  sortOptions?: SortOption[];
  createdAt?: string;
}

let filterIdCounter = 1;
let presetIdCounter = 1;

/**
 * Creates a mock FilterOption with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete FilterOption object
 */
export const createFilter = (overrides: Partial<FilterOption> = {}): FilterOption => {
  const id = overrides.id ?? `filter-${filterIdCounter++}`;

  return {
    category: overrides.category ?? "pricing",
    enabled: overrides.enabled ?? true,
    id,
    label: overrides.label ?? "Budget Friendly",
    value: overrides.value ?? 500,
  };
};

/**
 * Creates a mock SortOption with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete SortOption object
 */
export const createSortOption = (overrides: Partial<SortOption> = {}): SortOption => {
  const id = overrides.id ?? `sort-${filterIdCounter++}`;

  return {
    direction: overrides.direction ?? "asc",
    field: overrides.field ?? "price",
    id,
    label: overrides.label ?? "Price: Low to High",
  };
};

/**
 * Creates a mock FilterPreset with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete FilterPreset object
 */
export const createFilterPreset = (
  overrides: Partial<FilterPreset> = {}
): FilterPreset => {
  const id = overrides.id ?? `preset-${presetIdCounter++}`;

  return {
    createdAt: overrides.createdAt ?? new Date().toISOString(),
    filters: overrides.filters ?? [createFilter()],
    id,
    name: overrides.name ?? "My Preset",
    sortOptions: overrides.sortOptions ?? [createSortOption()],
  };
};

/**
 * Creates multiple filters at once.
 *
 * @param count - Number of filters to create
 * @param overridesFn - Optional function to customize each filter (receives index)
 * @returns Array of FilterOption objects
 */
export const createFilters = (
  count: number,
  overridesFn?: (index: number) => Partial<FilterOption>
): FilterOption[] => {
  return Array.from({ length: count }, (_, i) =>
    createFilter(overridesFn ? overridesFn(i) : {})
  );
};

/**
 * Creates a preset with common price filters.
 *
 * @returns A FilterPreset configured for price filtering
 */
export const createPriceFilterPreset = (): FilterPreset => {
  return createFilterPreset({
    filters: [
      createFilter({ category: "pricing", label: "Under $500", value: 500 }),
      createFilter({ category: "pricing", label: "$500-$1000", value: 1000 }),
      createFilter({
        category: "pricing",
        enabled: false,
        label: "Over $1000",
        value: 1000,
      }),
    ],
    name: "Price Filters",
    sortOptions: [createSortOption({ direction: "asc", field: "price" })],
  });
};

/**
 * Creates a preset with common rating filters.
 *
 * @returns A FilterPreset configured for rating filtering
 */
export const createRatingFilterPreset = (): FilterPreset => {
  return createFilterPreset({
    filters: [
      createFilter({ category: "rating", label: "4+ Stars", value: 4 }),
      createFilter({ category: "rating", enabled: false, label: "3+ Stars", value: 3 }),
    ],
    name: "Rating Filters",
    sortOptions: [createSortOption({ direction: "desc", field: "rating" })],
  });
};

/**
 * Resets all filter-related ID counters for deterministic test data.
 */
export const resetFilterFactory = (): void => {
  filterIdCounter = 1;
  presetIdCounter = 1;
};
