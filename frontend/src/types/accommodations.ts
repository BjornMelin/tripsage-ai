/**
 * @fileoverview TypeScript types and Zod schemas for accommodation tools.
 *
 * Centralized schemas with strict validation for inputs and outputs.
 * Types inferred from Zod schemas ensure type safety and schema compliance.
 */

import { z } from "zod";

/**
 * Property type enum for accommodation searches.
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

/**
 * Sort by enum for accommodation searches.
 */
export const SORT_BY_ENUM = z.enum(["relevance", "price", "rating", "distance"]);

/**
 * Sort order enum for accommodation searches.
 */
export const SORT_ORDER_ENUM = z.enum(["asc", "desc"]);

/**
 * Input schema for searching accommodations.
 *
 * Validates location, dates, guest counts, filters, and sorting options.
 * Includes cross-field refinements for date ordering and price ranges.
 */
export const ACCOMMODATION_SEARCH_INPUT_SCHEMA = z
  .object({
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
  .refine((data) => {
    const checkin = new Date(data.checkin);
    const checkout = new Date(data.checkout);
    return checkout > checkin;
  }, "checkout must be after checkin")
  .refine((data) => {
    if (data.priceMin !== undefined && data.priceMax !== undefined) {
      return data.priceMax >= data.priceMin;
    }
    return true;
  }, "priceMax must be >= priceMin")
  .strict();

/**
 * Parameters for searching accommodations.
 *
 * Supports filtering by location, dates, property types, amenities, price
 * range, guest counts, and various other criteria.
 */
export type AccommodationSearchParams = z.infer<
  typeof ACCOMMODATION_SEARCH_INPUT_SCHEMA
>;

/**
 * Strict output schema for accommodation search results.
 *
 * Enforces that tool always returns a validated object matching this schema.
 */
export const ACCOMMODATION_SEARCH_OUTPUT_SCHEMA = z
  .object({
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
  })
  .strict();

/**
 * Result of an accommodation search operation.
 *
 * Contains listings, pricing information, metadata, and provider details.
 */
export type AccommodationSearchResult = z.infer<
  typeof ACCOMMODATION_SEARCH_OUTPUT_SCHEMA
>;

/**
 * Input schema for retrieving accommodation details.
 *
 * Validates listing ID and optional date/guest parameters for accurate
 * pricing and availability information.
 */
export const ACCOMMODATION_DETAILS_INPUT_SCHEMA = z
  .object({
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
  })
  .strict();

/**
 * Parameters for retrieving detailed information about a specific listing.
 *
 * Optionally includes check-in/out dates and guest counts for accurate
 * pricing and availability.
 */
export type AccommodationDetailsParams = z.infer<
  typeof ACCOMMODATION_DETAILS_INPUT_SCHEMA
>;

/**
 * Strict output schema for accommodation details results.
 *
 * Enforces that tool always returns a validated object matching this schema.
 */
export const ACCOMMODATION_DETAILS_OUTPUT_SCHEMA = z
  .object({
    listing: z.unknown(),
    provider: z.string(),
    status: z.literal("success"),
  })
  .strict();

/**
 * Result of retrieving accommodation details.
 *
 * Contains the full listing information and provider metadata.
 */
export type AccommodationDetailsResult = z.infer<
  typeof ACCOMMODATION_DETAILS_OUTPUT_SCHEMA
>;

/**
 * Input schema for booking accommodations.
 *
 * Validates guest information, dates, payment details, and optional
 * idempotency key. Includes cross-field refinement for date ordering.
 */
export const ACCOMMODATION_BOOKING_INPUT_SCHEMA = z
  .object({
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
  .refine((data) => {
    const checkin = new Date(data.checkin);
    const checkout = new Date(data.checkout);
    return checkout > checkin;
  }, "checkout must be after checkin")
  .strict();

/**
 * Parameters for booking an accommodation.
 *
 * Includes guest information, dates, payment details, and optional
 * idempotency key for safe retries.
 */
export type AccommodationBookingRequest = z.infer<
  typeof ACCOMMODATION_BOOKING_INPUT_SCHEMA
>;

/**
 * Strict output schema for accommodation booking results.
 *
 * Enforces that tool always returns a validated object matching this schema.
 */
export const ACCOMMODATION_BOOKING_OUTPUT_SCHEMA = z
  .object({
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
  })
  .strict();

/**
 * Result of a booking operation.
 *
 * Contains booking confirmation details, status, reference number, and
 * provider information.
 */
export type AccommodationBookingResult = z.infer<
  typeof ACCOMMODATION_BOOKING_OUTPUT_SCHEMA
>;
