/**
 * @fileoverview Places schemas with validation. Includes canonical place DTOs, API/tool inputs, and saved place snapshots.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====

const PLACE_ID_PATTERN = /^(places\/)?[A-Za-z0-9_-]+$/;

/**
 * Canonical place ID schema (provider-specific format allowed, without forcing prefix).
 *
 * Google Places IDs may be returned as `places/{id}` or `{id}` depending on call site.
 * We validate the allowed character set and let callers normalize the prefix where needed.
 */
export const placeIdSchema = z
  .string()
  .transform((value) => value.normalize("NFKC").trim())
  .refine((value) => value.length > 0, { error: "placeId must not be empty" })
  .refine((value) => PLACE_ID_PATTERN.test(value), {
    error: "placeId has an invalid format",
  });

export type PlaceId = z.infer<typeof placeIdSchema>;

export const locationBiasSchema = z.strictObject({
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
  radiusMeters: z.number().int().positive().max(50_000),
});

export type LocationBias = z.infer<typeof locationBiasSchema>;

const normalizedQuerySchema = z
  .string()
  .transform((value) => value.normalize("NFKC").trim())
  .refine((value) => value.length > 0, { error: "query must not be empty" })
  .refine((value) => value.length <= 200, { error: "query is too long" });

export const searchPlacesParamsSchema = z.strictObject({
  filters: z
    .strictObject({
      includedTypes: z.array(z.string().min(1)).min(1).optional(),
    })
    .optional(),
  locationBias: locationBiasSchema.optional(),
  maxResults: z.number().int().min(1).max(20).default(20),
  query: normalizedQuerySchema,
});

export type SearchPlacesParams = z.infer<typeof searchPlacesParamsSchema>;

export const placeCoordinatesSchema = z.strictObject({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

export type PlaceCoordinates = z.infer<typeof placeCoordinatesSchema>;

export const placeSummarySchema = z.strictObject({
  coordinates: placeCoordinatesSchema.optional(),
  formattedAddress: z.string().optional(),
  name: z.string().min(1, { error: "name is required" }),
  photoName: z.string().optional(),
  placeId: placeIdSchema,
  rating: z.number().min(0).max(5).optional(),
  types: z.array(z.string()).default([]),
  url: z.url().optional(),
  userRatingCount: z.number().int().nonnegative().optional(),
});

export type PlaceSummary = z.infer<typeof placeSummarySchema>;

export const searchPlacesResultSchema = z.strictObject({
  places: z.array(placeSummarySchema),
});

export type SearchPlacesResult = z.infer<typeof searchPlacesResultSchema>;

export const placeDetailsParamsSchema = z.strictObject({
  placeId: placeIdSchema,
  sessionToken: z
    .string()
    .transform((value) => value.normalize("NFKC").trim())
    .refine((value) => value.length > 0, { error: "sessionToken must not be empty" })
    .optional(),
});

export type PlaceDetailsParams = z.infer<typeof placeDetailsParamsSchema>;

export const placeOpeningHoursSchema = z.strictObject({
  openNow: z.boolean().optional(),
  weekdayDescriptions: z.array(z.string()).optional(),
});

export const placeDetailsSchema = placeSummarySchema.extend({
  businessStatus: z.string().optional(),
  editorialSummary: z.string().optional(),
  internationalPhoneNumber: z.string().optional(),
  regularOpeningHours: placeOpeningHoursSchema.optional(),
  websiteUri: z.url().optional(),
});

export type PlaceDetails = z.infer<typeof placeDetailsSchema>;

// ===== SAVED PLACES =====

export const savedPlaceSnapshotSchema = z.strictObject({
  place: placeSummarySchema,
  savedAt: primitiveSchemas.isoDateTime.optional(),
});

export type SavedPlaceSnapshot = z.infer<typeof savedPlaceSnapshotSchema>;

// ===== TOOL INPUT SCHEMAS =====

export const searchPlacesToolInputSchema = searchPlacesParamsSchema;
export const placeDetailsToolInputSchema = placeDetailsParamsSchema;

export const savePlaceToTripToolInputSchema = z.strictObject({
  place: placeSummarySchema,
  tripId: z.number().int().positive(),
  userId: primitiveSchemas.uuid,
});

export type SavePlaceToTripToolInput = z.infer<typeof savePlaceToTripToolInputSchema>;

// ===== TOOL OUTPUT SCHEMAS =====

export const searchPlacesToolOutputSchema = searchPlacesResultSchema;
export const placeDetailsToolOutputSchema = placeDetailsSchema;
export const savePlaceToTripToolOutputSchema = savedPlaceSnapshotSchema;

export type SavePlaceToTripToolOutput = z.infer<typeof savePlaceToTripToolOutputSchema>;
