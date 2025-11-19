/**
 * @fileoverview Weather tools using OpenWeatherMap API.
 *
 * Uses direct HTTP GET requests to OpenWeatherMap API. Implements caching,
 * retry logic, and standardized error handling.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  getCurrentWeatherInputSchema,
  type WEATHER_RESULT_SCHEMA,
} from "@ai/tools/schemas/weather";
import type { z } from "zod";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { fetchWithRetry } from "@/lib/http/fetch-retry";
import { WEATHER_CACHE_TTL_SECONDS } from "./constants";

/**
 * Execute weather query via HTTP GET to OpenWeatherMap API.
 *
 * Supports city name (q), coordinates (lat/lon), or ZIP code (zip).
 * Uses the standard Current Weather Data API endpoint.
 *
 * @param params - The weather query parameters (city, coordinates, or zip; units, lang).
 * @returns Promise resolving to weather data and provider identifier ("http_get").
 * @throws {Error} Error with `code` property indicating failure reason:
 *   - "weather_not_configured": No API key configured
 *   - "weather_timeout": Request timed out
 *   - "weather_failed": Network or API error
 *   - "weather_rate_limited": Rate limit exceeded (429)
 *   - "weather_unauthorized": Authentication failed (401)
 *   - "weather_not_found": City/location not found (404)
 */
async function executeWeatherQuery(
  params: Record<string, unknown>
): Promise<{ data: unknown; provider: string }> {
  const { getServerEnvVar } = await import("@/lib/env/server");
  let apiKey: string | undefined;
  try {
    apiKey = getServerEnvVar("OPENWEATHERMAP_API_KEY") as unknown as string;
  } catch {
    const error: Error & { code?: string } = new Error("weather_not_configured");
    error.code = "weather_not_configured";
    throw error;
  }
  if (!apiKey) {
    const error: Error & { code?: string } = new Error("weather_not_configured");
    error.code = "weather_not_configured";
    throw error;
  }

  const url = new URL("https://api.openweathermap.org/data/2.5/weather");
  if (params.q) {
    url.searchParams.set("q", String(params.q));
  } else if (typeof params.lat !== "undefined" && typeof params.lon !== "undefined") {
    url.searchParams.set("lat", String(params.lat));
    url.searchParams.set("lon", String(params.lon));
  } else if (params.zip) {
    url.searchParams.set("zip", String(params.zip));
  }
  url.searchParams.set("appid", apiKey);
  if (params.units) url.searchParams.set("units", String(params.units));
  if (params.lang) url.searchParams.set("lang", String(params.lang));

  const res = await fetchWithRetry(
    url.toString(),
    {
      headers: {
        "content-type": "application/json",
      },
      method: "GET",
    },
    { retries: 2, timeoutMs: 12000 }
  ).catch((err) => {
    // Map generic fetch errors to domain-specific codes
    const errWithCode = err as Error & {
      code?: string;
      meta?: Record<string, unknown>;
    };
    if (errWithCode.code === "fetch_timeout") {
      const error: Error & { code?: string; meta?: Record<string, unknown> } =
        new Error("weather_timeout");
      error.code = "weather_timeout";
      error.meta = errWithCode.meta;
      throw error;
    }
    if (errWithCode.code === "fetch_failed") {
      const error: Error & { code?: string; meta?: Record<string, unknown> } =
        new Error("weather_failed");
      error.code = "weather_failed";
      error.meta = errWithCode.meta;
      throw error;
    }
    throw err;
  });

  if (!res.ok) {
    const text = await res.text();
    const error: Error & { code?: string; meta?: Record<string, unknown> } = new Error(
      res.status === 429
        ? "weather_rate_limited"
        : res.status === 401
          ? "weather_unauthorized"
          : res.status === 404
            ? "weather_not_found"
            : "weather_failed"
    );
    error.code =
      res.status === 429
        ? "weather_rate_limited"
        : res.status === 401
          ? "weather_unauthorized"
          : res.status === 404
            ? "weather_not_found"
            : "weather_failed";
    error.meta = { status: res.status, text: text.slice(0, 200) };
    throw error;
  }

  const data = await res.json();
  return { data, provider: "http_get" };
}

/**
 * Get current weather tool.
 *
 * Retrieves current weather conditions for a specified location (city,
 * coordinates, or ZIP code) using OpenWeatherMap API via direct HTTP GET.
 * Results are cached for performance (10 minute TTL). Returns comprehensive
 * weather data including temperature (with min/max), humidity, wind (with
 * gusts), pressure, visibility, clouds, precipitation (rain/snow), and
 * sunrise/sunset times. Includes weather icon ID for UI display.
 *
 * @returns WeatherResult with current conditions, metadata, and provider information.
 * @throws {Error} Error with `code` property indicating failure reason:
 *   - "weather_not_configured": No API key configured
 *   - "weather_timeout": Request timed out
 *   - "weather_failed": Network or API error
 *   - "weather_rate_limited": Rate limit exceeded (429)
 *   - "weather_unauthorized": Authentication failed (401)
 *   - "weather_not_found": City/location not found (404)
 */
type GetCurrentWeatherInput = z.infer<typeof getCurrentWeatherInputSchema>;
type WeatherResult = z.infer<typeof WEATHER_RESULT_SCHEMA>;

export const getCurrentWeather = createAiTool<GetCurrentWeatherInput, WeatherResult>({
  description:
    "Get current weather by city name, coordinates, or ZIP code via OpenWeatherMap API. " +
    "Returns temperature (with min/max), humidity, wind (with gusts), pressure, visibility, " +
    "clouds, precipitation (rain/snow), sunrise/sunset times, and weather icon. " +
    "Results cached for 10 minutes.",
  execute: async (params) => {
    const validated = getCurrentWeatherInputSchema.parse(params);
    const startedAt = Date.now();

    const queryParams: Record<string, unknown> = {
      units: validated.units,
    };
    if (validated.city) {
      queryParams.q = validated.city.trim();
    } else if (validated.coordinates) {
      queryParams.lat = validated.coordinates.lat;
      queryParams.lon = validated.coordinates.lon;
    } else if (validated.zip) {
      queryParams.zip = validated.zip.trim();
    }
    if (validated.lang) queryParams.lang = validated.lang;

    const { data, provider } = await executeWeatherQuery(queryParams);
    const weatherData = data as Record<string, unknown>;
    const tookMs = Date.now() - startedAt;

    const main = weatherData.main as Record<string, unknown> | undefined;
    const weather = (weatherData.weather as unknown[])?.[0] as
      | Record<string, unknown>
      | undefined;
    const sys = weatherData.sys as Record<string, unknown> | undefined;
    const wind = weatherData.wind as Record<string, unknown> | undefined;
    const clouds = weatherData.clouds as Record<string, unknown> | undefined;
    const rain = weatherData.rain as Record<string, unknown> | undefined;
    const snow = weatherData.snow as Record<string, unknown> | undefined;

    const rainValue = (rain?.["1h"] as number) ?? (rain?.["3h"] as number) ?? null;
    const snowValue = (snow?.["1h"] as number) ?? (snow?.["3h"] as number) ?? null;

    return {
      city: (weatherData.name as string) || validated.city || "Unknown",
      clouds: (clouds?.all as number) ?? null,
      country: sys?.country as string | undefined,
      description: (weather?.description as string) ?? null,
      feelsLike: (main?.feels_like as number) ?? null,
      fromCache: false,
      humidity: (main?.humidity as number) ?? null,
      icon: (weather?.icon as string) ?? null,
      pressure: (main?.pressure as number) ?? null,
      provider,
      rain: rainValue,
      snow: snowValue,
      status: "success",
      sunrise: (sys?.sunrise as number) ?? null,
      sunset: (sys?.sunset as number) ?? null,
      temp: (main?.temp as number) ?? null,
      tempMax: (main?.temp_max as number) ?? null,
      tempMin: (main?.temp_min as number) ?? null,
      timezone: weatherData.timezone as number | null | undefined,
      tookMs,
      visibility: weatherData.visibility as number | null | undefined,
      windDirection: (wind?.deg as number) ?? null,
      windGust: (wind?.gust as number) ?? null,
      windSpeed: (wind?.speed as number) ?? null,
    };
  },
  guardrails: {
    cache: {
      hashInput: true,
      key: (params) =>
        canonicalizeParamsForCache({
          city: params.city?.trim().toLowerCase(),
          lang: params.lang,
          lat: params.coordinates?.lat,
          lon: params.coordinates?.lon,
          units: params.units,
          zip: params.zip?.trim(),
        }),
      namespace: "tool:weather:current",
      onHit: (cached, _params, meta) => ({
        ...cached,
        fromCache: true,
        provider: cached.provider ?? "cache",
        tookMs: Date.now() - meta.startedAt,
      }),
      shouldBypass: (params) => Boolean(params.fresh),
      ttlSeconds: WEATHER_CACHE_TTL_SECONDS,
    },
    telemetry: {
      attributes: (params) => ({
        hasCoordinates: Boolean(params.coordinates),
        hasZip: Boolean(params.zip),
        units: params.units,
      }),
      redactKeys: ["city", "zip"],
    },
  },
  inputSchema: getCurrentWeatherInputSchema,
  name: "getCurrentWeather",
});
