/**
 * @fileoverview Factory for creating Search and SearchResult test data.
 */

let searchIdCounter = 1;
let resultIdCounter = 1;

export interface SearchQueryOverrides {
  id?: string;
  user_id?: string;
  query?: string;
  destination?: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
  passengers?: number;
  created_at?: string;
}

export interface SearchResultOverrides {
  id?: string;
  search_id?: string;
  type?: "flight" | "hotel" | "activity";
  title?: string;
  description?: string;
  price?: number;
  currency?: string;
  rating?: number;
  url?: string;
  image_url?: string;
}

export interface DealOverrides {
  id?: string;
  title?: string;
  description?: string;
  price?: number;
  original_price?: number;
  currency?: string;
  destination?: string;
  valid_from?: string;
  valid_to?: string;
  discount_percentage?: number;
  deal_type?: "flight" | "hotel" | "package";
}

/**
 * Creates a mock SearchQuery with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete SearchQuery object
 */
export const createSearchQuery = (
  overrides: SearchQueryOverrides = {}
): SearchQueryOverrides & { id: string } => {
  const id = overrides.id ?? `search-${searchIdCounter++}`;

  return {
    budget: overrides.budget ?? 1500,
    created_at: overrides.created_at ?? new Date().toISOString(),
    destination: overrides.destination ?? "Paris",
    end_date:
      overrides.end_date ??
      new Date(Date.now() + 37 * 24 * 60 * 60 * 1000).toISOString(),
    id,
    passengers: overrides.passengers ?? 2,
    query: overrides.query ?? "Flights to Paris",
    start_date:
      overrides.start_date ??
      new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    user_id: overrides.user_id ?? "user-1",
  };
};

/**
 * Creates a mock SearchResult with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete SearchResult object
 */
export const createSearchResult = (
  overrides: SearchResultOverrides = {}
): SearchResultOverrides & { id: string } => {
  const id = overrides.id ?? `result-${resultIdCounter++}`;
  const type = overrides.type ?? "flight";

  return {
    currency: overrides.currency ?? "USD",
    description: overrides.description ?? `Test ${type} result description`,
    id,
    image_url: overrides.image_url ?? `https://example.com/images/${id}.jpg`,
    price: overrides.price ?? 500,
    rating: overrides.rating ?? 4.5,
    search_id: overrides.search_id ?? "search-1",
    title:
      overrides.title ??
      `${type === "flight" ? "Flight" : type === "hotel" ? "Hotel" : "Activity"} Result`,
    type,
    url: overrides.url ?? `https://example.com/${type}/${id}`,
  };
};

/**
 * Creates a mock Deal with sensible defaults.
 *
 * @param overrides - Properties to override defaults
 * @returns A complete Deal object
 */
export const createDeal = (
  overrides: DealOverrides = {}
): DealOverrides & { id: string } => {
  const id = overrides.id ?? `deal-${resultIdCounter++}`;
  const originalPrice = overrides.original_price ?? 1000;
  const price = overrides.price ?? 750;
  const discountPercentage =
    overrides.discount_percentage ??
    Math.round(((originalPrice - price) / originalPrice) * 100);

  return {
    currency: overrides.currency ?? "USD",
    deal_type: overrides.deal_type ?? "package",
    description: overrides.description ?? "Save big on your next trip!",
    destination: overrides.destination ?? "Barcelona",
    discount_percentage: discountPercentage,
    id,
    original_price: originalPrice,
    price,
    title: overrides.title ?? "Amazing Travel Deal",
    valid_from: overrides.valid_from ?? new Date().toISOString(),
    valid_to:
      overrides.valid_to ??
      new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  };
};

/**
 * Creates multiple search results at once.
 *
 * @param count - Number of results to create
 * @param overridesFn - Optional function to customize each result (receives index)
 * @returns Array of SearchResult objects
 */
export const createSearchResults = (
  count: number,
  overridesFn?: (index: number) => SearchResultOverrides
): Array<SearchResultOverrides & { id: string }> => {
  return Array.from({ length: count }, (_, i) =>
    createSearchResult(overridesFn ? overridesFn(i) : {})
  );
};

/**
 * Creates multiple deals at once.
 *
 * @param count - Number of deals to create
 * @param overridesFn - Optional function to customize each deal (receives index)
 * @returns Array of Deal objects
 */
export const createDeals = (
  count: number,
  overridesFn?: (index: number) => DealOverrides
): Array<DealOverrides & { id: string }> => {
  return Array.from({ length: count }, (_, i) =>
    createDeal(overridesFn ? overridesFn(i) : {})
  );
};

/**
 * Resets all search-related ID counters for deterministic test data.
 */
export const resetSearchFactory = (): void => {
  searchIdCounter = 1;
  resultIdCounter = 1;
};

import type {
  SearchHistoryItem,
  ValidatedSavedSearch,
} from "@/stores/search-history-store";

/**
 * Create mock search history item.
 *
 * @param overrides - Partial search history item to override defaults
 * @returns A complete search history item
 */
export function createMockSearchItem(
  overrides: Partial<SearchHistoryItem> = {}
): SearchHistoryItem {
  return {
    id: "test-id",
    params: {},
    searchType: "flight",
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create mock saved search.
 *
 * @param overrides - Partial saved search to override defaults
 * @returns A complete saved search
 */
export function createMockSavedSearch(
  overrides: Partial<ValidatedSavedSearch> = {}
): ValidatedSavedSearch {
  return {
    createdAt: new Date().toISOString(),
    id: "test-search-id",
    isFavorite: false,
    isPublic: false,
    name: "Test Search",
    params: {},
    searchType: "flight",
    tags: [],
    updatedAt: new Date().toISOString(),
    usageCount: 0,
    ...overrides,
  };
}
