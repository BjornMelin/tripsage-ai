/**
 * Zod schemas for search functionality
 * Runtime validation for all search-related data types
 */

import { z } from "zod";

// Base validation helpers
const COORDINATES_SCHEMA = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

const DATE_STRING_SCHEMA = z.iso.datetime().or(z.iso.date());
const POSITIVE_INT_SCHEMA = z.number().int().positive();
const NON_NEGATIVE_INT_SCHEMA = z.number().int().nonnegative();

// Base search parameters schema
export const baseSearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20, "Too many adults"),
  children: NON_NEGATIVE_INT_SCHEMA.max(20, "Too many children"),
  destination: z.string().min(1, "Destination is required"),
  endDate: DATE_STRING_SCHEMA,
  infants: NON_NEGATIVE_INT_SCHEMA.max(20, "Too many infants"),
  startDate: DATE_STRING_SCHEMA,
});

// Flight specific search parameters
export const flightSearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20).optional(),
  cabinClass: z.enum(["economy", "premium_economy", "business", "first"]).optional(),
  children: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  departureDate: DATE_STRING_SCHEMA.optional(),
  destination: z.string().optional(),
  directOnly: z.boolean().optional(),
  excludedAirlines: z.array(z.string()).optional(),
  infants: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  maxStops: z.number().int().nonnegative().max(3).optional(),
  origin: z.string().optional(),
  preferredAirlines: z.array(z.string()).optional(),
  returnDate: DATE_STRING_SCHEMA.optional(),
});

// Accommodation specific search parameters
export const accommodationSearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20).optional(),
  amenities: z.array(z.string()).optional(),
  checkIn: DATE_STRING_SCHEMA.optional(),
  checkOut: DATE_STRING_SCHEMA.optional(),
  children: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  destination: z.string().optional(),
  infants: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  minRating: z.number().min(0).max(5).optional(),
  priceRange: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().nonnegative().optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      message: "Min price must be less than or equal to max price",
    })
    .optional(),
  propertyType: z.enum(["hotel", "apartment", "villa", "hostel", "resort"]).optional(),
  rooms: POSITIVE_INT_SCHEMA.max(20, "Too many rooms").optional(),
});

// Activity specific search parameters
export const activitySearchParamsSchema = z.object({
  adults: POSITIVE_INT_SCHEMA.max(20).optional(),
  category: z.string().optional(),
  children: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
  date: DATE_STRING_SCHEMA.optional(),
  destination: z.string().optional(),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  duration: z
    .object({
      max: z.number().positive().optional(),
      min: z.number().positive().optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      message: "Min duration must be less than or equal to max duration",
    })
    .optional(),
  indoor: z.boolean().optional(),
  infants: NON_NEGATIVE_INT_SCHEMA.max(20).optional(),
});

// Destination specific search parameters
export const destinationSearchParamsSchema = z.object({
  components: z
    .object({
      country: z.array(z.string()).optional(),
    })
    .optional(),
  language: z.string().min(2).max(3).optional(),
  limit: z.number().int().positive().max(100).optional(),
  query: z.string().min(1, "Search query is required"),
  region: z.string().optional(),
  types: z
    .array(z.enum(["locality", "country", "administrative_area", "establishment"]))
    .optional(),
});

// Union schema for all search parameters
export const searchParamsSchema = z.union([
  flightSearchParamsSchema,
  accommodationSearchParamsSchema,
  activitySearchParamsSchema,
  destinationSearchParamsSchema,
]);

// Search type schema
export const searchTypeSchema = z.enum([
  "flight",
  "accommodation",
  "activity",
  "destination",
]);

// Flight search result schema
export const flightSchema = z.object({
  airline: z.string().min(1),
  arrivalTime: DATE_STRING_SCHEMA,
  cabinClass: z.string(),
  departureTime: DATE_STRING_SCHEMA,
  destination: z.string().min(1),
  duration: POSITIVE_INT_SCHEMA,
  flightNumber: z.string().min(1),
  id: z.string().min(1),
  layovers: z
    .array(
      z.object({
        airport: z.string().min(1),
        duration: POSITIVE_INT_SCHEMA,
      })
    )
    .optional(),
  origin: z.string().min(1),
  price: z.number().positive(),
  seatsAvailable: NON_NEGATIVE_INT_SCHEMA,
  stops: NON_NEGATIVE_INT_SCHEMA,
});

// Accommodation search result schema
export const accommodationSchema = z.object({
  amenities: z.array(z.string()),
  checkIn: DATE_STRING_SCHEMA,
  checkOut: DATE_STRING_SCHEMA,
  coordinates: COORDINATES_SCHEMA.optional(),
  id: z.string().min(1),
  images: z.array(z.url()).optional(),
  location: z.string().min(1),
  name: z.string().min(1),
  pricePerNight: z.number().positive(),
  rating: z.number().min(0).max(5),
  totalPrice: z.number().positive(),
  type: z.string().min(1),
});

// Activity search result schema
export const activitySchema = z.object({
  coordinates: COORDINATES_SCHEMA.optional(),
  date: DATE_STRING_SCHEMA,
  description: z.string(),
  duration: POSITIVE_INT_SCHEMA,
  id: z.string().min(1),
  images: z.array(z.url()).optional(),
  location: z.string().min(1),
  name: z.string().min(1),
  price: z.number().nonnegative(),
  rating: z.number().min(0).max(5),
  type: z.string().min(1),
});

// Destination search result schema
export const destinationSchema = z.object({
  attractions: z.array(z.string()).optional(),
  bestTimeToVisit: z.array(z.string()).optional(),
  climate: z
    .object({
      averageTemp: z.number(),
      rainfall: z.number().nonnegative(),
      season: z.string(),
    })
    .optional(),
  coordinates: COORDINATES_SCHEMA,
  country: z.string().optional(),
  description: z.string(),
  formattedAddress: z.string().min(1),
  id: z.string().min(1),
  name: z.string().min(1),
  photos: z.array(z.url()).optional(),
  placeId: z.string().optional(),
  popularityScore: z.number().min(0).max(10).optional(),
  rating: z.number().min(0).max(5).optional(),
  region: z.string().optional(),
  types: z.array(z.string()),
});

// Union schema for all search results
export const searchResultSchema = z.union([
  flightSchema,
  accommodationSchema,
  activitySchema,
  destinationSchema,
]);

// Search results grouped by type
export const searchResultsSchema = z.object({
  accommodations: z.array(accommodationSchema).optional(),
  activities: z.array(activitySchema).optional(),
  destinations: z.array(destinationSchema).optional(),
  flights: z.array(flightSchema).optional(),
});

// Saved search schema
export const savedSearchSchema = z.object({
  createdAt: DATE_STRING_SCHEMA,
  id: z.string().min(1),
  lastUsed: DATE_STRING_SCHEMA.optional(),
  name: z.string().min(1, "Search name is required").max(100, "Name too long"),
  params: searchParamsSchema,
  type: searchTypeSchema,
});

// Filter value schema
export const filterValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.string()),
  z.array(z.number()),
]);

// Metadata value schema
export const metadataValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.record(z.string(), z.unknown()),
]);

// Search response from API schema
export const searchResponseSchema = z.object({
  filters: z.record(z.string(), filterValueSchema).optional(),
  metadata: z.record(z.string(), metadataValueSchema).optional(),
  results: searchResultsSchema,
  totalResults: NON_NEGATIVE_INT_SCHEMA,
});

// Filter option schema
export const filterOptionSchema = z.object({
  count: NON_NEGATIVE_INT_SCHEMA.optional(),
  id: z.string().min(1),
  label: z.string().min(1),
  options: z
    .array(
      z.object({
        count: NON_NEGATIVE_INT_SCHEMA.optional(),
        label: z.string().min(1),
        value: filterValueSchema,
      })
    )
    .optional(),
  type: z.enum(["checkbox", "radio", "range", "select"]),
  value: filterValueSchema,
});

// Sort option schema
export const sortOptionSchema = z.object({
  direction: z.enum(["asc", "desc"]),
  id: z.string().min(1),
  label: z.string().min(1),
  value: z.string().min(1),
});

// Search validation utilities
export const validateSearchParams = (data: unknown, searchType: string) => {
  try {
    switch (searchType) {
      case "flight":
        return flightSearchParamsSchema.parse(data);
      case "accommodation":
        return accommodationSearchParamsSchema.parse(data);
      case "activity":
        return activitySearchParamsSchema.parse(data);
      case "destination":
        return destinationSearchParamsSchema.parse(data);
      default:
        throw new Error(`Unknown search type: ${searchType}`);
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new Error(
        `Search parameters validation failed: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

export const safeValidateSearchParams = (data: unknown, searchType: string) => {
  try {
    return { data: validateSearchParams(data, searchType), success: true };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Validation failed",
      success: false,
    };
  }
};

// Type exports
export type BaseSearchParams = z.infer<typeof baseSearchParamsSchema>;
export type FlightSearchParams = z.infer<typeof flightSearchParamsSchema>;
export type AccommodationSearchParams = z.infer<typeof accommodationSearchParamsSchema>;
export type ActivitySearchParams = z.infer<typeof activitySearchParamsSchema>;
export type DestinationSearchParams = z.infer<typeof destinationSearchParamsSchema>;
export type SearchParams = z.infer<typeof searchParamsSchema>;
export type SearchType = z.infer<typeof searchTypeSchema>;
export type Flight = z.infer<typeof flightSchema>;
export type Accommodation = z.infer<typeof accommodationSchema>;
export type Activity = z.infer<typeof activitySchema>;
export type Destination = z.infer<typeof destinationSchema>;
export type SearchResult = z.infer<typeof searchResultSchema>;
export type SearchResults = z.infer<typeof searchResultsSchema>;
export type SavedSearch = z.infer<typeof savedSearchSchema>;
export type FilterValue = z.infer<typeof filterValueSchema>;
export type MetadataValue = z.infer<typeof metadataValueSchema>;
export type SearchResponse = z.infer<typeof searchResponseSchema>;
export type FilterOption = z.infer<typeof filterOptionSchema>;
export type SortOption = z.infer<typeof sortOptionSchema>;
