/**
 * @fileoverview Zod schemas for maps API responses and maps tool inputs.
 *
 * Core schemas: Maps/geocoding API parameters and data structures
 * Tool schemas: Input validation for maps tools (geocode, distance matrix)
 */

import { z } from "zod";

/** Schema for geocode tool input. */
export const geocodeInputSchema = z.strictObject({
  address: z.string().min(2).describe("Address or location to geocode"),
});

/** Schema for distance matrix tool input. */
export const distanceMatrixInputSchema = z.strictObject({
  destinations: z
    .array(z.string().min(2))
    .min(1)
    .describe("List of destination addresses"),
  origins: z.array(z.string().min(2)).min(1).describe("List of origin addresses"),
  units: z
    .enum(["metric", "imperial"])
    .default("metric")
    .describe("Unit system for distances"),
});
