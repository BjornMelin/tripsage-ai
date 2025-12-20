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

/** Accommodation listing entry for model consumption. */
const accommodationListingModelOutputSchema = z.strictObject({
  amenities: z.array(z.string()).optional(),
  geoCode: geoCodeModelOutputSchema,
  id: z.union([z.string(), z.number()]).optional(),
  lowestPrice: z.union([z.string(), z.number()]).optional(),
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
