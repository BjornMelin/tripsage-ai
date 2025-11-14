/**
 * @fileoverview Zod v4 schema for Weather tool results and params.
 */

import { z } from "zod";

/** Zod schema for weather API request parameters. */
export const WEATHER_PARAMS_SCHEMA = z.object({
  city: z.string().optional(),
  coordinates: z
    .object({
      lat: z.number(),
      lon: z.number(),
    })
    .optional(),
  fresh: z.boolean().optional(),
  lang: z.string().optional(),
  units: z.enum(["metric", "imperial"]).optional(),
  zip: z.string().optional(),
});
/** TypeScript type for weather parameters. */
export type WeatherParams = z.infer<typeof WEATHER_PARAMS_SCHEMA>;

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
