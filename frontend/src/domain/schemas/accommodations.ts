/**
 * @fileoverview Accommodation tool schemas with validation.
 * Includes search parameters, results, details, availability checks, and booking schemas for accommodation tools.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for accommodation management

/**
 * Zod schema for supported property types in accommodation search.
 * Defines available accommodation categories.
 */
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

/** TypeScript type for property types. */
export type PropertyType = z.infer<typeof PROPERTY_TYPE_ENUM>;

/**
 * Zod schema for accommodation search sort criteria.
 * Defines available sorting options for search results.
 */
export const SORT_BY_ENUM = z.enum(["relevance", "price", "rating", "distance"]);

/** TypeScript type for sort criteria. */
export type SortBy = z.infer<typeof SORT_BY_ENUM>;

/**
 * Zod schema for accommodation search sort order directions.
 * Defines ascending and descending sort options.
 */
export const SORT_ORDER_ENUM = z.enum(["asc", "desc"]);

/** TypeScript type for sort order directions. */
export type SortOrder = z.infer<typeof SORT_ORDER_ENUM>;

// ===== TOOL INPUT SCHEMAS =====
// Schemas for accommodation tool input validation and processing

/**
 * Zod schema for accommodation search input parameters.
 * Validates all search criteria including dates, location, guest counts, and filters.
 * Used for AI tool input validation.
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
    currency: primitiveSchemas.isoCurrency.default("USD").optional(),
    freeCancellation: z.boolean().optional(),
    fresh: z.boolean().default(false).optional(),
    guests: z.number().int().min(1).max(16).default(1),
    infants: z.number().int().min(0).max(16).optional(),
    instantBook: z.boolean().optional(),
    location: z.string().min(2),
    lat: z.number().optional(),
    lng: z.number().optional(),
    maxDistanceKm: z.number().nonnegative().optional(),
    minRating: z.number().min(0).max(5).optional(),
    priceMax: z.number().nonnegative().optional(),
    priceMin: z.number().nonnegative().optional(),
    propertyTypes: z.array(PROPERTY_TYPE_ENUM).optional(),
    semanticQuery: z.string().optional(), // For RAG semantic search
    sortBy: SORT_BY_ENUM.default("relevance").optional(),
    sortOrder: SORT_ORDER_ENUM.default("asc").optional(),
    tripId: z.string().optional(),
  })
  .refine((data) => new Date(data.checkout) > new Date(data.checkin), {
    error: "checkout must be after checkin",
  })
  .refine(
    (data) =>
      data.priceMin === undefined ||
      data.priceMax === undefined ||
      (data.priceMax as number) >= (data.priceMin as number),
    { error: "priceMax must be >= priceMin" }
  );

/** TypeScript type for accommodation search parameters. */
export type AccommodationSearchParams = z.infer<
  typeof ACCOMMODATION_SEARCH_INPUT_SCHEMA
>;

/**
 * Zod schema for accommodation search result data.
 * Contains search results, pricing info, and metadata from providers.
 */
export const ACCOMMODATION_SEARCH_OUTPUT_SCHEMA = z.strictObject({
  avgPrice: z.number().optional(),
  fromCache: z.boolean(),
  listings: z.array(z.unknown()).default([]),
  maxPrice: z.number().optional(),
  minPrice: z.number().optional(),
  provider: z.enum(["amadeus", "cache"]),
  resultsReturned: z.number(),
  searchId: z.string(),
  searchParameters: z.record(z.string(), z.unknown()),
  status: z.literal("success"),
  tookMs: z.number(),
  totalResults: z.number(),
});

/** TypeScript type for accommodation search results. */
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

/** TypeScript type for accommodation details parameters. */
export type AccommodationDetailsParams = z.infer<
  typeof ACCOMMODATION_DETAILS_INPUT_SCHEMA
>;

/**
 * Zod schema for accommodation details output parameters.
 * Contains detailed listing information from providers.
 */
export const ACCOMMODATION_DETAILS_OUTPUT_SCHEMA = z.strictObject({
  listing: z.unknown(),
  provider: z.enum(["amadeus"]),
  status: z.literal("success"),
});

/** TypeScript type for accommodation details results. */
export type AccommodationDetailsResult = z.infer<
  typeof ACCOMMODATION_DETAILS_OUTPUT_SCHEMA
>;

/**
 * Zod schema for accommodation availability check input parameters.
 * Validates parameters for checking property availability and pricing.
 */
export const ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA = z.strictObject({
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  guests: z.number().int().min(1).max(16),
  priceCheckToken: z.string().min(1),
  propertyId: z.string().min(1),
  rateId: z.string().min(1),
  roomId: z.string().min(1),
});

/** TypeScript type for accommodation availability check parameters. */
export type AccommodationCheckAvailabilityParams = z.infer<
  typeof ACCOMMODATION_CHECK_AVAILABILITY_INPUT_SCHEMA
>;

/**
 * Zod schema for accommodation availability check output parameters.
 * Contains booking token, pricing breakdown, and expiration information.
 */
export const ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA = z.strictObject({
  bookingToken: z.string(),
  expiresAt: primitiveSchemas.isoDateTime, // ISO 8601 timestamp
  price: z.object({
    breakdown: z
      .object({
        base: z.string().optional(),
        fees: z.string().optional(),
        taxes: z.string().optional(),
      })
      .optional(),
    currency: primitiveSchemas.isoCurrency,
    total: z.string(),
  }),
  propertyId: z.string(),
  rateId: z.string(),
  status: z.literal("success"),
});

/** TypeScript type for accommodation availability check results. */
export type AccommodationCheckAvailabilityResult = z.infer<
  typeof ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA
>;

/**
 * Zod schema for accommodation booking input parameters.
 * Validates booking parameters including guest information, dates, and payment details.
 */
export const ACCOMMODATION_BOOKING_INPUT_SCHEMA = z
  .strictObject({
    amount: z.number().positive(), // Total amount in cents from checkAvailability
    bookingToken: z.string().min(1), // From checkAvailability
    checkin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    checkout: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    currency: primitiveSchemas.isoCurrency, // Currency code from checkAvailability
    guestEmail: primitiveSchemas.email,
    guestName: z.string().min(1),
    guestPhone: z.string().optional(),
    guests: z.number().int().min(1).max(16).default(1),
    holdOnly: z.boolean().default(false).optional(),
    idempotencyKey: z.string().optional(),
    listingId: z.string().min(1), // Property ID for reference
    paymentMethodId: z.string().min(1), // Stripe payment method ID
    sessionId: z.string().min(6).optional(),
    specialRequests: z.string().optional(),
    tripId: z.string().optional(),
  })
  .refine((data) => new Date(data.checkout) > new Date(data.checkin), {
    error: "checkout must be after checkin",
  });

/** TypeScript type for accommodation booking requests. */
export type AccommodationBookingRequest = z.infer<
  typeof ACCOMMODATION_BOOKING_INPUT_SCHEMA
>;

/**
 * Zod schema for accommodation booking output parameters.
 * Contains booking confirmation details including booking ID, status, and payment information.
 */
export const ACCOMMODATION_BOOKING_OUTPUT_SCHEMA = z.strictObject({
  bookingId: z.string(),
  bookingStatus: z.enum(["hold_created", "pending_confirmation", "confirmed"]),
  checkin: z.string(),
  checkout: z.string(),
  epsBookingId: z.string().optional(), // EPS booking confirmation ID
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
  stripePaymentIntentId: z.string().optional(), // Stripe payment intent ID
  tripId: z.string().optional(),
});

/** TypeScript type for accommodation booking results. */
export type AccommodationBookingResult = z.infer<
  typeof ACCOMMODATION_BOOKING_OUTPUT_SCHEMA
>;
