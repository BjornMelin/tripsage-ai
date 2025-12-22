/**
 * @fileoverview Zod schemas for maps API responses and maps tool inputs.
 */

import { upstreamGeocodeResultSchema } from "@schemas/api";
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

// ===== TOOL OUTPUT SCHEMAS =====

/** Schema for geocode tool output. */
export const geocodeOutputSchema = z
  .array(upstreamGeocodeResultSchema)
  .describe("Geocoding results");

const distanceMatrixEntrySchema = z.strictObject({
  destinationIndex: z.number().int().nonnegative(),
  distanceMeters: z.number().nonnegative().nullable(),
  distanceText: z.string().nullable(),
  durationSeconds: z.number().int().nonnegative().nullable(),
  durationText: z.string().nullable(),
  originIndex: z.number().int().nonnegative(),
  status: z.enum(["OK", "ZERO_RESULTS"]),
});

/** Schema for distance matrix tool output. */
export const distanceMatrixOutputSchema = z.strictObject({
  destinations: z.array(z.string()),
  entries: z.array(distanceMatrixEntrySchema),
  origins: z.array(z.string()),
  units: z.enum(["metric", "imperial"]),
});
