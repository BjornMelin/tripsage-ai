/**
 * @fileoverview Accommodation tool model output schemas.
 */

import { z } from "zod";

// ===== MODEL OUTPUT SCHEMAS =====

/** GeoCode for model consumption. */
const geoCodeModelOutputSchema = z
  .strictObject({
    latitude: z.number(),
    longitude: z.number(),
  })
  .optional();

/**
 * Coerce string-or-number to number, returning undefined for non-parseable values.
 */
const coerceToNumber = z
  .union([z.string(), z.number()])
  .optional()
  .transform((val) => {
    if (val === undefined || val === null) return undefined;
    if (typeof val === "number") return val;
    const parsed = Number(val);
    return Number.isNaN(parsed) ? undefined : parsed;
  });

/**
 * Accommodation listing entry for model consumption.
 * Fields are normalized to numbers via transforms to ensure type safety downstream.
 */
const accommodationListingModelOutputSchema = z.strictObject({
  amenities: z.array(z.string()).optional(),
  geoCode: geoCodeModelOutputSchema,
  id: coerceToNumber,
  lowestPrice: coerceToNumber,
  name: z.string().optional(),
  rating: z.number().optional(),
  starRating: z.number().optional(),
});

/** Accommodation search result output schema for model consumption. */
export const accommodationModelOutputSchema = z.strictObject({
  avgPrice: z.number().optional(),
  fromCache: z.boolean(),
  listingCount: z.number().int(),
  listings: z.array(accommodationListingModelOutputSchema),
  maxPrice: z.number().optional(),
  minPrice: z.number().optional(),
  provider: z.enum(["amadeus", "cache"]),
  resultsReturned: z.number().int(),
  totalResults: z.number().int(),
});

export type AccommodationModelOutput = z.infer<typeof accommodationModelOutputSchema>;
