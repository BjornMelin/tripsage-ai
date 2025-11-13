/**
 * @fileoverview Zod v4 schemas for accommodation tools (single source of truth).
 */

import { z } from "zod";

/** Enumeration of supported property types for accommodation search. */
export const PROPERTY_TYPE_ENUM = z.enum([
  "hotel",
  "apartment",
  "house",
  "villa",
  "resort",
  "hostel",
  "bed_and_breakfast",
  "guest_house",
  "other",
]);

/** Enumeration of sort criteria for accommodation search results. */
export const SORT_BY_ENUM = z.enum(["relevance", "price", "rating", "distance"]);

/** Enumeration of sort order directions. */
export const SORT_ORDER_ENUM = z.enum(["asc", "desc"]);

/**
 * Zod schema for accommodation search input parameters.
 * Validates all search criteria including dates, location, guest counts, and filters.
 */
export const ACCOMMODATION_SEARCH_INPUT_SCHEMA = z
  .strictObject({
    accessibilityFeatures: z.array(z.string()).optional(),
    adults: z.number().int().min(1).max(16).optional(),
    amenities: z.array(z.string()).optional(),
    bathrooms: z.number().nonnegative().max(10).optional(),
    bedrooms: z.number().int().min(0).max(10).optional(),
    beds: z.number().int().min(0).max(20).optional(),
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    children: z.number().int().min(0).max(16).optional(),
    currency: z.string().length(3).default("USD").optional(),
    freeCancellation: z.boolean().optional(),
    fresh: z.boolean().default(false).optional(),
    guests: z.number().int().min(1).max(16).default(1),
    infants: z.number().int().min(0).max(16).optional(),
    instantBook: z.boolean().optional(),
    location: z.string().min(2),
    maxDistanceKm: z.number().nonnegative().optional(),
    minRating: z.number().min(0).max(5).optional(),
    priceMax: z.number().nonnegative().optional(),
    priceMin: z.number().nonnegative().optional(),
    propertyTypes: z.array(PROPERTY_TYPE_ENUM).optional(),
    sortBy: SORT_BY_ENUM.default("relevance").optional(),
    sortOrder: SORT_ORDER_ENUM.default("asc").optional(),
    tripId: z.string().optional(),
  })
  .refine(
    (data) => new Date(data.checkout) > new Date(data.checkin),
    "checkout must be after checkin"
  )
  .refine(
    (data) =>
      data.priceMin === undefined ||
      data.priceMax === undefined ||
      (data.priceMax as number) >= (data.priceMin as number),
    "priceMax must be >= priceMin"
  );
/** TypeScript type inferred from the accommodation search input schema. */
export type AccommodationSearchParams = z.infer<
  typeof ACCOMMODATION_SEARCH_INPUT_SCHEMA
>;

/**
 * Zod schema for accommodation search result data.
 * Contains search results, pricing info, and metadata.
 */
export const ACCOMMODATION_SEARCH_OUTPUT_SCHEMA = z.strictObject({
  avgPrice: z.number().optional(),
  fromCache: z.boolean(),
  listings: z.array(z.unknown()).default([]),
  maxPrice: z.number().optional(),
  minPrice: z.number().optional(),
  provider: z.string(),
  resultsReturned: z.number(),
  searchId: z.string(),
  searchParameters: z.record(z.string(), z.unknown()),
  status: z.literal("success"),
  tookMs: z.number(),
  totalResults: z.number(),
});
/** TypeScript type inferred from the accommodation search output schema. */
export type AccommodationSearchResult = z.infer<
  typeof ACCOMMODATION_SEARCH_OUTPUT_SCHEMA
>;

/**
 * Zod schema for accommodation details request parameters.
 * Used to fetch detailed information about a specific listing.
 */
export const ACCOMMODATION_DETAILS_INPUT_SCHEMA = z.strictObject({
  adults: z.number().int().min(1).max(16).default(1).optional(),
  checkin: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  checkout: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  children: z.number().int().min(0).max(16).default(0).optional(),
  infants: z.number().int().min(0).max(16).default(0).optional(),
  listingId: z.string().min(1),
});
/** TypeScript type inferred from the accommodation details input schema. */
export type AccommodationDetailsParams = z.infer<
  typeof ACCOMMODATION_DETAILS_INPUT_SCHEMA
>;

/** Zod schema for accommodation details output parameters. */
export const ACCOMMODATION_DETAILS_OUTPUT_SCHEMA = z.strictObject({
  listing: z.unknown(),
  provider: z.string(),
  status: z.literal("success"),
});
/** TypeScript type inferred from the accommodation details output schema. */
export type AccommodationDetailsResult = z.infer<
  typeof ACCOMMODATION_DETAILS_OUTPUT_SCHEMA
>;

/** Zod schema for accommodation booking input parameters. */
export const ACCOMMODATION_BOOKING_INPUT_SCHEMA = z
  .strictObject({
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    guestEmail: z.string().email(),
    guestName: z.string().min(1),
    guestPhone: z.string().optional(),
    guests: z.number().int().min(1).max(16).default(1),
    holdOnly: z.boolean().default(false).optional(),
    idempotencyKey: z.string().optional(),
    listingId: z.string().min(1),
    paymentMethod: z.string().optional(),
    sessionId: z.string().min(6).optional(),
    specialRequests: z.string().optional(),
    tripId: z.string().optional(),
  })
  .refine(
    (data) => new Date(data.checkout) > new Date(data.checkin),
    "checkout must be after checkin"
  );
/** TypeScript type inferred from the accommodation booking input schema. */
export type AccommodationBookingRequest = z.infer<
  typeof ACCOMMODATION_BOOKING_INPUT_SCHEMA
>;

export const ACCOMMODATION_BOOKING_OUTPUT_SCHEMA = z.strictObject({
  bookingId: z.string(),
  bookingStatus: z.enum(["hold_created", "pending_confirmation"]),
  checkin: z.string(),
  checkout: z.string(),
  guestEmail: z.string(),
  guestName: z.string(),
  guestPhone: z.string().optional(),
  guests: z.number(),
  holdOnly: z.boolean(),
  idempotencyKey: z.string(),
  listingId: z.string(),
  message: z.string(),
  paymentMethod: z.string().optional(),
  reference: z.string(),
  specialRequests: z.string().optional(),
  status: z.literal("success"),
  tripId: z.string().optional(),
});
/** TypeScript type inferred from the accommodation booking output schema. */
export type AccommodationBookingResult = z.infer<
  typeof ACCOMMODATION_BOOKING_OUTPUT_SCHEMA
>;
