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
