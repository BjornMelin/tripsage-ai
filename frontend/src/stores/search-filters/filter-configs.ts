/**
 * @fileoverview Filter and sort configurations by search type.
 *
 * Extracted from search-filters-store.ts to reduce store size and improve maintainability.
 */

import type { SearchType } from "@schemas/search";
import type {
  SortDirection,
  ValidatedFilterOption,
  ValidatedSortOption,
} from "@schemas/stores";

/** Flight filter configurations */
const FLIGHT_FILTERS: ValidatedFilterOption[] = [
  {
    category: "pricing",
    id: "price_range",
    label: "Price Range",
    required: false,
    type: "range",
    validation: { max: 10000, min: 0 },
  },
  {
    category: "routing",
    id: "stops",
    label: "Number of Stops",
    options: [
      { label: "Direct flights only", value: "0" },
      { label: "1 stop", value: "1" },
      { label: "2+ stops", value: "2" },
    ],
    required: false,
    type: "select",
  },
  {
    category: "airline",
    id: "airlines",
    label: "Airlines",
    options: [], // Populated dynamically from API results
    required: false,
    type: "multiselect",
  },
  {
    category: "timing",
    id: "departure_time",
    label: "Departure Time",
    options: [
      { label: "Early Morning (6:00-9:00)", value: "early_morning" },
      { label: "Morning (9:00-12:00)", value: "morning" },
      { label: "Afternoon (12:00-18:00)", value: "afternoon" },
      { label: "Evening (18:00+)", value: "evening" },
    ],
    required: false,
    type: "select",
  },
];

/** Accommodation filter configurations */
const ACCOMMODATION_FILTERS: ValidatedFilterOption[] = [
  {
    category: "pricing",
    id: "price_range",
    label: "Price per Night",
    required: false,
    type: "range",
    validation: { max: 2000, min: 0 },
  },
  {
    category: "quality",
    id: "rating",
    label: "Minimum Rating",
    options: [
      { label: "3+ stars", value: "3" },
      { label: "4+ stars", value: "4" },
      { label: "5 stars", value: "5" },
    ],
    required: false,
    type: "select",
  },
  {
    category: "type",
    id: "property_type",
    label: "Property Type",
    options: [
      { label: "Hotel", value: "hotel" },
      { label: "Apartment", value: "apartment" },
      { label: "Villa", value: "villa" },
      { label: "Resort", value: "resort" },
    ],
    required: false,
    type: "multiselect",
  },
  {
    category: "features",
    id: "amenities",
    label: "Amenities",
    options: [
      { label: "Free WiFi", value: "wifi" },
      { label: "Free Parking", value: "parking" },
      { label: "Swimming Pool", value: "pool" },
      { label: "Fitness Center", value: "gym" },
      { label: "Spa", value: "spa" },
      { label: "Restaurant", value: "restaurant" },
    ],
    required: false,
    type: "multiselect",
  },
];

/** Activity filter configurations */
const ACTIVITY_FILTERS: ValidatedFilterOption[] = [
  {
    category: "pricing",
    id: "price_range",
    label: "Price Range",
    required: false,
    type: "range",
    validation: { max: 500, min: 0 },
  },
  {
    category: "timing",
    id: "duration",
    label: "Duration (minutes)",
    required: false,
    type: "range",
    validation: { max: 480, min: 1 },
  },
  {
    category: "experience",
    id: "difficulty",
    label: "Difficulty Level",
    options: [
      { label: "Easy", value: "easy" },
      { label: "Moderate", value: "moderate" },
      { label: "Challenging", value: "challenging" },
      { label: "Extreme", value: "extreme" },
    ],
    required: false,
    type: "select",
  },
  {
    category: "type",
    id: "category",
    label: "Activity Type",
    options: [
      { label: "Outdoor Adventures", value: "outdoor" },
      { label: "Cultural Experiences", value: "cultural" },
      { label: "Food & Drink", value: "food" },
      { label: "Sightseeing", value: "sightseeing" },
      { label: "Sports & Recreation", value: "sports" },
    ],
    required: false,
    type: "multiselect",
  },
];

/** Destination filter configurations */
const DESTINATION_FILTERS: ValidatedFilterOption[] = [
  {
    category: "type",
    id: "destination_type",
    label: "Destination Type",
    options: [
      { label: "Cities", value: "city" },
      { label: "Countries", value: "country" },
      { label: "Regions", value: "region" },
      { label: "Landmarks", value: "landmark" },
    ],
    required: false,
    type: "multiselect",
  },
  {
    category: "demographics",
    id: "population",
    label: "Population Size",
    options: [
      { label: "Small (< 100k)", value: "small" },
      { label: "Medium (100k - 1M)", value: "medium" },
      { label: "Large (1M+)", value: "large" },
    ],
    required: false,
    type: "select",
  },
];

/** Filter configurations by search type */
export const FILTER_CONFIGS: Record<SearchType, ValidatedFilterOption[]> = {
  accommodation: ACCOMMODATION_FILTERS,
  activity: ACTIVITY_FILTERS,
  destination: DESTINATION_FILTERS,
  flight: FLIGHT_FILTERS,
};

/** Relevance sort option shared across search types */
const RELEVANCE_SORT = {
  direction: "desc",
  field: "score",
  id: "relevance",
  isDefault: true,
  label: "Relevance",
} as const satisfies ValidatedSortOption;

/** Common sort options shared across search types */
const COMMON_SORT_OPTIONS: ValidatedSortOption[] = [
  { ...RELEVANCE_SORT },
  {
    direction: "asc",
    field: "price",
    id: "price_low",
    isDefault: false,
    label: "Price: Low to High",
  },
  {
    direction: "desc",
    field: "price",
    id: "price_high",
    isDefault: false,
    label: "Price: High to Low",
  },
];

/** Flight sort options */
const FLIGHT_SORT_OPTIONS: ValidatedSortOption[] = [
  ...COMMON_SORT_OPTIONS,
  {
    direction: "asc",
    field: "totalDuration",
    id: "duration",
    isDefault: false,
    label: "Duration",
  },
  {
    direction: "asc" as SortDirection,
    field: "departureTime",
    id: "departure",
    isDefault: false,
    label: "Departure Time",
  },
  {
    direction: "asc" as SortDirection,
    field: "arrivalTime",
    id: "arrival",
    isDefault: false,
    label: "Arrival Time",
  },
  {
    direction: "asc" as SortDirection,
    field: "stops",
    id: "stops",
    isDefault: false,
    label: "Fewest Stops",
  },
];

/** Accommodation sort options */
const ACCOMMODATION_SORT_OPTIONS: ValidatedSortOption[] = [
  ...COMMON_SORT_OPTIONS,
  {
    direction: "desc" as SortDirection,
    field: "rating",
    id: "rating",
    isDefault: false,
    label: "Highest Rated",
  },
  {
    direction: "asc" as SortDirection,
    field: "distance",
    id: "distance",
    isDefault: false,
    label: "Distance",
  },
  {
    direction: "desc" as SortDirection,
    field: "reviewCount",
    id: "reviews",
    isDefault: false,
    label: "Most Reviews",
  },
];

/** Activity sort options */
const ACTIVITY_SORT_OPTIONS: ValidatedSortOption[] = [
  ...COMMON_SORT_OPTIONS,
  {
    direction: "desc" as SortDirection,
    field: "rating",
    id: "rating",
    isDefault: false,
    label: "Highest Rated",
  },
  {
    direction: "asc" as SortDirection,
    field: "duration",
    id: "duration",
    isDefault: false,
    label: "Duration",
  },
  {
    direction: "desc" as SortDirection,
    field: "bookingCount",
    id: "popularity",
    isDefault: false,
    label: "Most Popular",
  },
];

/** Destination sort options */
const DESTINATION_SORT_OPTIONS: ValidatedSortOption[] = [
  { ...RELEVANCE_SORT },
  {
    direction: "asc",
    field: "name",
    id: "alphabetical",
    isDefault: false,
    label: "Alphabetical",
  },
  {
    direction: "desc",
    field: "population",
    id: "population",
    isDefault: false,
    label: "Population",
  },
  {
    direction: "asc",
    field: "distance",
    id: "distance",
    isDefault: false,
    label: "Distance",
  },
];

/** Sort configurations by search type */
export const SORT_CONFIGS: Record<SearchType, ValidatedSortOption[]> = {
  accommodation: ACCOMMODATION_SORT_OPTIONS,
  activity: ACTIVITY_SORT_OPTIONS,
  destination: DESTINATION_SORT_OPTIONS,
  flight: FLIGHT_SORT_OPTIONS,
};

/** Get default filters for a search type */
export const getDefaultFilters = (type: SearchType): ValidatedFilterOption[] =>
  FILTER_CONFIGS[type] ?? [];

/** Get default sort options for a search type */
export const getDefaultSortOptions = (type: SearchType): ValidatedSortOption[] =>
  SORT_CONFIGS[type] ?? COMMON_SORT_OPTIONS;
