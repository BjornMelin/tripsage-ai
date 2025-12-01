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

/**
 * Schema for lookupPoiContext tool response.
 *
 * Represents either an error response or a successful POI lookup result.
 */
export const lookupPoiResponseSchema = z.union([
  z.object({
    error: z.string().optional().describe("Error message if lookup failed"),
    inputs: z.unknown().describe("Original input parameters"),
    pois: z.array(z.unknown()).describe("Empty array on error"),
    provider: z.string().describe("Provider name"),
  }),
  z.object({
    fromCache: z.boolean().optional().describe("Whether result was cached"),
    inputs: z.unknown().describe("Original input parameters"),
    pois: z.array(z.unknown()).describe("Array of POI results"),
    provider: z.string().describe("Provider name"),
  }),
]);

/** TypeScript type for lookupPoiContext tool response. */
export type LookupPoiResponse = z.infer<typeof lookupPoiResponseSchema>;
