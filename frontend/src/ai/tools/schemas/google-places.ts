/**
 * @fileoverview Zod schemas for Google Places API responses and Google Places tool inputs.
 *
 * Core schemas: Google Places API parameters and data structures
 * Tool schemas: Input validation for Google Places tools (POI lookup)
 */

import { z } from "zod";

/** Schema for lookupPoiContext tool input. */
export const lookupPoiInputSchema = z
  .strictObject({
    destination: z
      .string()
      .min(1, { error: "destination must not be empty" })
      .nullable()
      .optional()
      .describe("Destination city or place name to search near"),
    lat: z
      .number()
      .nullable()
      .optional()
      .describe("Latitude coordinate for location search"),
    lon: z
      .number()
      .nullable()
      .optional()
      .describe("Longitude coordinate for location search"),
    query: z
      .string()
      .min(1, { error: "query must not be empty" })
      .nullable()
      .optional()
      .describe("Specific place or business name to search for"),
    radiusMeters: z
      .number()
      .int()
      .positive()
      .default(1000)
      .describe("Search radius in meters"),
  })
  .refine(
    (o) =>
      (o.destination !== null && o.destination !== undefined) ||
      (o.query !== null && o.query !== undefined) ||
      (typeof o.lat === "number" && typeof o.lon === "number"),
    { message: "Provide destination, query, or lat/lon" }
  );

// ===== TOOL OUTPUT SCHEMAS =====

/** Normalized POI shape returned by Google Places lookups. */
const poiSchema = z.strictObject({
  formattedAddress: z.string().optional().describe("Formatted address"),
  lat: z.number().min(-90).max(90).describe("Latitude coordinate"),
  lon: z.number().min(-180).max(180).describe("Longitude coordinate"),
  name: z.string().describe("Display name of the POI"),
  photoName: z.string().optional().describe("Photo resource identifier"),
  placeId: z.string().describe("Provider place identifier"),
  rating: z.number().min(0).max(5).optional().describe("Average user rating"),
  types: z.array(z.string()).optional().describe("Place type categories"),
  url: z.url().optional().describe("Canonical Maps URL if available"),
  userRatingCount: z
    .number()
    .int()
    .nonnegative()
    .optional()
    .describe("Number of user ratings"),
});

/**
 * Schema for lookupPoiContext tool response.
 *
 * Represents either an error response or a successful POI lookup result.
 * Uses a discriminated union with explicit status field for unambiguous parsing.
 */
export const lookupPoiResponseSchema = z.discriminatedUnion("status", [
  z.strictObject({
    error: z.string().describe("Error message if lookup failed"),
    inputs: lookupPoiInputSchema.describe("Original input parameters"),
    pois: z.array(poiSchema).describe("Empty array on error"),
    provider: z.string().describe("Provider name"),
    status: z.literal("error"),
  }),
  z.strictObject({
    fromCache: z.boolean().optional().describe("Whether result was cached"),
    inputs: lookupPoiInputSchema.describe("Original input parameters"),
    pois: z.array(poiSchema).describe("Array of POI results"),
    provider: z.string().describe("Provider name"),
    status: z.literal("success"),
  }),
]);

/** TypeScript type for lookupPoiContext tool response. */
export type LookupPoiResponse = z.infer<typeof lookupPoiResponseSchema>;
