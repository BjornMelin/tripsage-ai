/**
 * @fileoverview Filter constants and typed IDs for search filter components.
 *
 * Provides type-safe filter identifiers and option definitions used across
 * filter-panel and filter components.
 */

/**
 * Typed filter IDs with const assertion for compile-time safety.
 * Use these instead of magic strings throughout filter components.
 */
export const FILTER_IDS = {
  airlines: "airlines",
  departureTime: "departure_time",
  duration: "duration",
  priceRange: "price_range",
  stops: "stops",
} as const;

/** Type representing valid filter ID values. */
export type FilterId = (typeof FILTER_IDS)[keyof typeof FILTER_IDS];

/** Option type for filter selections. */
export interface FilterOption {
  readonly label: string;
  readonly value: string;
  readonly disabled?: boolean;
  readonly icon?: React.ReactNode;
}

/** Flight stops options. */
export const STOPS_OPTIONS: readonly FilterOption[] = [
  { label: "Any", value: "any" },
  { label: "Nonstop", value: "0" },
  { label: "1 Stop", value: "1" },
  { label: "2+", value: "2+" },
] as const;

/** Departure time options. */
export const TIME_OPTIONS: readonly FilterOption[] = [
  { label: "Early (12a-6a)", value: "early_morning" },
  { label: "Morning (6a-12p)", value: "morning" },
  { label: "Afternoon (12p-6p)", value: "afternoon" },
  { label: "Evening (6p-12a)", value: "evening" },
] as const;

/** Airlines options (typical major carriers). */
export const AIRLINES_OPTIONS: readonly FilterOption[] = [
  { label: "American Airlines", value: "AA" },
  { label: "United Airlines", value: "UA" },
  { label: "Delta Air Lines", value: "DL" },
  { label: "Southwest Airlines", value: "WN" },
  { label: "Alaska Airlines", value: "AS" },
  { label: "JetBlue Airways", value: "B6" },
] as const;

/** Default price range bounds. */
export const PRICE_RANGE_DEFAULTS = {
  max: 2000,
  min: 0,
  step: 10,
} as const;

/** Default duration range bounds (in minutes). */
export const DURATION_RANGE_DEFAULTS = {
  max: 1440,
  min: 0,
  step: 30,
} as const;
