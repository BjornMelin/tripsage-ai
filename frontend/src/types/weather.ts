/**
 * @fileoverview TypeScript types for weather tools.
 *
 * Types mirror the Zod schemas in weather.ts to provide type-safe
 * interfaces without requiring Zod imports at call sites.
 */

/**
 * Parameters for getting current weather.
 *
 * Supports city name, coordinates, or ZIP code. Includes units selection,
 * language preference, and optional cache bypass flag.
 */
export type WeatherParams = {
  city?: string;
  coordinates?: {
    lat: number;
    lon: number;
  };
  fresh?: boolean;
  lang?: string;
  units?: "metric" | "imperial";
  zip?: string;
};

/**
 * Result of a weather query operation.
 *
 * Contains current weather conditions, temperature (including min/max),
 * humidity, wind (including gusts), pressure, visibility, clouds,
 * precipitation data, and other meteorological data along with metadata.
 */
export type WeatherResult = {
  city: string;
  clouds?: number | null;
  country?: string;
  description: string | null;
  feelsLike: number | null;
  fromCache: boolean;
  humidity: number | null;
  icon?: string | null;
  pressure: number | null;
  provider: string;
  rain?: number | null;
  snow?: number | null;
  status: "success";
  sunrise?: number | null;
  sunset?: number | null;
  temp: number | null;
  tempMax?: number | null;
  tempMin?: number | null;
  timezone?: number | null;
  tookMs: number;
  visibility?: number | null;
  windDirection?: number | null;
  windGust?: number | null;
  windSpeed?: number | null;
};
