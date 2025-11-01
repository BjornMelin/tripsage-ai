/**
 * Zod schemas for search functionality
 * Runtime validation for all search-related data types
 */

import { z } from "zod";

// Base validation helpers
const coordinatesSchema = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

const dateStringSchema = z.string().datetime().or(z.string().date());
const positiveIntSchema = z.number().int().positive();
const nonNegativeIntSchema = z.number().int().nonnegative();

// Base search parameters schema
export const baseSearchParamsSchema = z.object({
  destination: z.string().min(1, "Destination is required"),
  startDate: dateStringSchema,
  endDate: dateStringSchema,
  adults: positiveIntSchema.max(20, "Too many adults"),
  children: nonNegativeIntSchema.max(20, "Too many children"),
  infants: nonNegativeIntSchema.max(20, "Too many infants"),
});

// Flight specific search parameters
export const flightSearchParamsSchema = z.object({
  origin: z.string().optional(),
  destination: z.string().optional(),
  departureDate: dateStringSchema.optional(),
  returnDate: dateStringSchema.optional(),
  cabinClass: z.enum(["economy", "premium_economy", "business", "first"]).optional(),
  directOnly: z.boolean().optional(),
  maxStops: z.number().int().nonnegative().max(3).optional(),
  preferredAirlines: z.array(z.string()).optional(),
  excludedAirlines: z.array(z.string()).optional(),
  adults: positiveIntSchema.max(20).optional(),
  children: nonNegativeIntSchema.max(20).optional(),
  infants: nonNegativeIntSchema.max(20).optional(),
});

// Accommodation specific search parameters
export const accommodationSearchParamsSchema = z.object({
  destination: z.string().optional(),
  checkIn: dateStringSchema.optional(),
  checkOut: dateStringSchema.optional(),
  rooms: positiveIntSchema.max(20, "Too many rooms").optional(),
  amenities: z.array(z.string()).optional(),
  propertyType: z.enum(["hotel", "apartment", "villa", "hostel", "resort"]).optional(),
  priceRange: z
    .object({
      min: z.number().nonnegative().optional(),
      max: z.number().positive().optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      message: "Min price must be less than or equal to max price",
    })
    .optional(),
  minRating: z.number().min(0).max(5).optional(),
  adults: positiveIntSchema.max(20).optional(),
  children: nonNegativeIntSchema.max(20).optional(),
  infants: nonNegativeIntSchema.max(20).optional(),
});

// Activity specific search parameters
export const activitySearchParamsSchema = z.object({
  destination: z.string().optional(),
  date: dateStringSchema.optional(),
  category: z.string().optional(),
  duration: z
    .object({
      min: z.number().positive().optional(),
      max: z.number().positive().optional(),
    })
    .refine((data) => !data.min || !data.max || data.min <= data.max, {
      message: "Min duration must be less than or equal to max duration",
    })
    .optional(),
  difficulty: z.enum(["easy", "moderate", "challenging", "extreme"]).optional(),
  indoor: z.boolean().optional(),
  adults: positiveIntSchema.max(20).optional(),
  children: nonNegativeIntSchema.max(20).optional(),
  infants: nonNegativeIntSchema.max(20).optional(),
});

// Destination specific search parameters
export const destinationSearchParamsSchema = z.object({
  query: z.string().min(1, "Search query is required"),
  types: z
    .array(z.enum(["locality", "country", "administrative_area", "establishment"]))
    .optional(),
  language: z.string().min(2).max(3).optional(),
  region: z.string().optional(),
  components: z
    .object({
      country: z.array(z.string()).optional(),
    })
    .optional(),
  limit: z.number().int().positive().max(100).optional(),
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
  id: z.string().min(1),
  airline: z.string().min(1),
  flightNumber: z.string().min(1),
  origin: z.string().min(1),
  destination: z.string().min(1),
  departureTime: dateStringSchema,
  arrivalTime: dateStringSchema,
  duration: positiveIntSchema,
  stops: nonNegativeIntSchema,
  price: z.number().positive(),
  cabinClass: z.string(),
  seatsAvailable: nonNegativeIntSchema,
  layovers: z
    .array(
      z.object({
        airport: z.string().min(1),
        duration: positiveIntSchema,
      })
    )
    .optional(),
});

// Accommodation search result schema
export const accommodationSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  type: z.string().min(1),
  location: z.string().min(1),
  checkIn: dateStringSchema,
  checkOut: dateStringSchema,
  pricePerNight: z.number().positive(),
  totalPrice: z.number().positive(),
  rating: z.number().min(0).max(5),
  amenities: z.array(z.string()),
  images: z.array(z.string().url()).optional(),
  coordinates: coordinatesSchema.optional(),
});

// Activity search result schema
export const activitySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  type: z.string().min(1),
  location: z.string().min(1),
  date: dateStringSchema,
  duration: positiveIntSchema,
  price: z.number().nonnegative(),
  rating: z.number().min(0).max(5),
  description: z.string(),
  images: z.array(z.string().url()).optional(),
  coordinates: coordinatesSchema.optional(),
});

// Destination search result schema
export const destinationSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string(),
  formattedAddress: z.string().min(1),
  types: z.array(z.string()),
  coordinates: coordinatesSchema,
  photos: z.array(z.string().url()).optional(),
  placeId: z.string().optional(),
  country: z.string().optional(),
  region: z.string().optional(),
  rating: z.number().min(0).max(5).optional(),
  popularityScore: z.number().min(0).max(10).optional(),
  climate: z
    .object({
      season: z.string(),
      averageTemp: z.number(),
      rainfall: z.number().nonnegative(),
    })
    .optional(),
  attractions: z.array(z.string()).optional(),
  bestTimeToVisit: z.array(z.string()).optional(),
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
  flights: z.array(flightSchema).optional(),
  accommodations: z.array(accommodationSchema).optional(),
  activities: z.array(activitySchema).optional(),
  destinations: z.array(destinationSchema).optional(),
});

// Saved search schema
export const savedSearchSchema = z.object({
  id: z.string().min(1),
  type: searchTypeSchema,
  name: z.string().min(1, "Search name is required").max(100, "Name too long"),
  params: searchParamsSchema,
  createdAt: dateStringSchema,
  lastUsed: dateStringSchema.optional(),
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
  results: searchResultsSchema,
  totalResults: nonNegativeIntSchema,
  filters: z.record(z.string(), filterValueSchema).optional(),
  metadata: z.record(z.string(), metadataValueSchema).optional(),
});

// Filter option schema
export const filterOptionSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  value: filterValueSchema,
  type: z.enum(["checkbox", "radio", "range", "select"]),
  count: nonNegativeIntSchema.optional(),
  options: z
    .array(
      z.object({
        label: z.string().min(1),
        value: filterValueSchema,
        count: nonNegativeIntSchema.optional(),
      })
    )
    .optional(),
});

// Sort option schema
export const sortOptionSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  value: z.string().min(1),
  direction: z.enum(["asc", "desc"]),
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
    return { success: true, data: validateSearchParams(data, searchType) };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Validation failed",
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
