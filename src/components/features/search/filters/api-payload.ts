/**
 * @fileoverview API payload builders for search filters.
 *
 * Transforms Zustand filter state into API request parameters.
 * Bridges the UI filter state to backend search APIs.
 */

import type { FilterValue } from "@schemas/stores";
import { FILTER_IDS } from "./constants";
import { isRangeObject, isStringArray, isStringValue } from "./utils";

/** Active filter record from the store. */
export type ActiveFilters = Record<string, { value: FilterValue }>;

/** Flight API filter parameters. */
export interface FlightApiFilters {
  /** Maximum number of stops (0 = direct only). */
  maxStops?: number;
  /** Airlines to exclude from results. */
  excludedAirlines?: string[];
  /** Maximum price in currency units. */
  maxPrice?: number;
  /** Direct flights only flag. */
  directOnly?: boolean;
}

/** Hotel API filter parameters. */
export interface HotelApiFilters {
  /** Price range for hotels. */
  priceRange?: { min: number; max: number };
  /** Minimum star rating (1-5). */
  minRating?: number;
  /** Required amenities. */
  amenities?: string[];
}

/** Activity API filter parameters. */
export interface ActivityApiFilters {
  /** Price range for activities. */
  priceRange?: { min: number; max: number };
  /** Activity categories to include. */
  categories?: string[];
  /** Maximum duration in minutes. */
  maxDuration?: number;
}

/**
 * Convert stops filter value to maxStops API parameter.
 * Maps "any" -> undefined, "direct" -> 0, "one" -> 1, "two+" -> 2
 */
function stopsToMaxStops(value: string | undefined): number | undefined {
  if (!value || value === "any") return undefined;
  switch (value) {
    case "direct":
      return 0;
    case "one":
      return 1;
    case "two+":
      return 2;
    default:
      return undefined;
  }
}

/**
 * Build flight API filter parameters from active filters.
 *
 * @param filters - Active filters from the search-filters store
 * @returns Flight API filter object ready for API request
 *
 * @example
 * ```ts
 * const { activeFilters } = useSearchFiltersStore();
 * const apiFilters = buildFlightApiPayload(activeFilters);
 * // Pass to flight search API: { maxStops: 1, maxPrice: 500 }
 * ```
 */
export function buildFlightApiPayload(filters: ActiveFilters): FlightApiFilters {
  const result: FlightApiFilters = {};

  // Stops filter
  const stopsEntry = filters[FILTER_IDS.stops];
  if (stopsEntry && isStringValue(stopsEntry.value)) {
    const maxStops = stopsToMaxStops(stopsEntry.value);
    if (maxStops !== undefined) {
      result.maxStops = maxStops;
      result.directOnly = maxStops === 0;
    }
  }

  // Airlines filter (multi-select)
  const airlinesEntry = filters[FILTER_IDS.airlines];
  if (
    airlinesEntry &&
    isStringArray(airlinesEntry.value) &&
    airlinesEntry.value.length > 0
  ) {
    result.excludedAirlines = airlinesEntry.value;
  }

  // Price range filter
  const priceEntry = filters[FILTER_IDS.priceRange];
  if (priceEntry && isRangeObject(priceEntry.value)) {
    result.maxPrice = priceEntry.value.max;
  }

  return result;
}

/**
 * Build hotel API filter parameters from active filters.
 *
 * @param filters - Active filters from the search-filters store
 * @returns Hotel API filter object ready for API request
 */
export function buildHotelApiPayload(filters: ActiveFilters): HotelApiFilters {
  const result: HotelApiFilters = {};

  // Price range filter
  const priceEntry = filters[FILTER_IDS.priceRange];
  if (priceEntry && isRangeObject(priceEntry.value)) {
    result.priceRange = priceEntry.value;
  }

  return result;
}

/**
 * Build activity API filter parameters from active filters.
 *
 * @param filters - Active filters from the search-filters store
 * @returns Activity API filter object ready for API request
 */
export function buildActivityApiPayload(filters: ActiveFilters): ActivityApiFilters {
  const result: ActivityApiFilters = {};

  // Price range filter
  const priceEntry = filters[FILTER_IDS.priceRange];
  if (priceEntry && isRangeObject(priceEntry.value)) {
    result.priceRange = priceEntry.value;
  }

  // Duration filter
  const durationEntry = filters[FILTER_IDS.duration];
  if (durationEntry && isRangeObject(durationEntry.value)) {
    result.maxDuration = durationEntry.value.max;
  }

  return result;
}
