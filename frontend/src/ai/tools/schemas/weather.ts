/**
 * @fileoverview Centralized Zod schemas for weather tools.
 *
 * Core schemas: Weather API results and data structures.
 * Tool schemas: Input validation for weather tools (current weather).
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====

/**
 * Zod schema for weather API response data.
 * Contains current weather conditions and forecast information.
 */
export const WEATHER_RESULT_SCHEMA = z.strictObject({
  city: z.string(),
  clouds: z.number().nullable().optional(),
  country: z.string().optional(),
  description: z.string().nullable(),
  feelsLike: z.number().nullable(),
  fromCache: z.boolean(),
  humidity: z.number().nullable(),
  icon: z.string().nullable().optional(),
  pressure: z.number().nullable(),
  provider: z.string(),
  rain: z.number().nullable().optional(),
  snow: z.number().nullable().optional(),
  status: z.literal("success"),
  sunrise: z.number().nullable().optional(),
  sunset: z.number().nullable().optional(),
  temp: z.number().nullable(),
  tempMax: z.number().nullable().optional(),
  tempMin: z.number().nullable().optional(),
  timezone: z.number().nullable().optional(),
  tookMs: z.number(),
  visibility: z.number().nullable().optional(),
  windDirection: z.number().nullable().optional(),
  windGust: z.number().nullable().optional(),
  windSpeed: z.number().nullable().optional(),
});

/** TypeScript type for weather result data. */
export type WeatherResult = z.infer<typeof WEATHER_RESULT_SCHEMA>;

// ===== TOOL INPUT SCHEMAS =====

/** Zod schema for weather tool input validation. */
export const getCurrentWeatherInputSchema = z
  .strictObject({
    city: z.string().min(2).nullable().describe("City name for weather lookup"),
    coordinates: z
      .strictObject({
        lat: z.number().min(-90).max(90).describe("Latitude coordinate"),
        lon: z.number().min(-180).max(180).describe("Longitude coordinate"),
      })
      .nullable()
      .describe("Geographic coordinates for weather lookup"),
    fresh: z
      .boolean()
      .default(false)
      .nullable()
      .describe("Whether to bypass cached results"),
    lang: z
      .string()
      .length(2)
      .nullable()
      .describe("Two-letter language code for weather descriptions"),
    units: z
      .enum(["metric", "imperial"])
      .default("metric")
      .describe("Temperature unit system"),
    zip: z.string().nullable().describe("ZIP/postal code for weather lookup"),
  })
  .refine(
    (data) =>
      (data.city !== null && data.city !== undefined) ||
      (data.coordinates !== null && data.coordinates !== undefined) ||
      (data.zip !== null && data.zip !== undefined),
    {
      message: "Either city, coordinates, or zip must be provided",
    }
  );
