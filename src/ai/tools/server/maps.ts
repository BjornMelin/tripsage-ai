/**
 * @fileoverview Google Maps tools: geocode, distance matrix.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { distanceMatrixInputSchema, geocodeInputSchema } from "@ai/tools/schemas/maps";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { getGoogleMapsServerKey } from "@/lib/env/server";

/** Get Google Maps server API key or null if not configured. */
function getGmapsKeyOrNull(): string | null {
  try {
    return getGoogleMapsServerKey() || null;
  } catch {
    return null;
  }
}

/**
 * Tool for geocoding a location using Google Maps Geocoding API.
 *
 * Uses Google Maps Geocoding API to convert location strings to coordinates.
 * Returns array of geocoding results with address, latitude, and longitude.
 *
 * @param address Location address to geocode.
 * @returns Promise resolving to geocoding results.
 */
export const geocode = createAiTool({
  description: "Geocode a location using Google Maps Geocoding API.",
  execute: async ({ address }) => {
    const key = getGmapsKeyOrNull();
    if (!key) throw new Error("gmaps_not_configured");
    const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
    url.searchParams.set("address", address);
    url.searchParams.set("key", key);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`gmaps_failed:${res.status}`);
    const data = await res.json();
    return data?.results ?? [];
  },
  guardrails: {
    cache: {
      key: (p) => p.address.toLowerCase(),
      ttlSeconds: 3600,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: geocodeInputSchema,
  name: "geocode",
});

/**
 * Tool for computing distances between origins and destinations via Google Distance Matrix.
 *
 * Uses Google Distance Matrix API to compute distances between sets of origins and destinations.
 * Returns distance matrix with travel times and distances for each origin-destination pair.
 *
 * @param origins Array of origin addresses.
 * @param destinations Array of destination addresses.
 * @param units Distance units ("metric" or "imperial").
 * @returns Promise resolving to distance matrix.
 */
export const distanceMatrix = createAiTool({
  description:
    "Compute distances between origins and destinations via Google Distance Matrix.",
  execute: async ({ origins, destinations, units }) => {
    const key = getGmapsKeyOrNull();
    if (!key) throw new Error("gmaps_not_configured");
    const url = new URL("https://maps.googleapis.com/maps/api/distancematrix/json");
    url.searchParams.set("origins", origins.join("|"));
    url.searchParams.set("destinations", destinations.join("|"));
    url.searchParams.set("units", units);
    url.searchParams.set("key", key);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`gmaps_dm_failed:${res.status}`);
    return await res.json();
  },
  guardrails: {
    cache: {
      key: (p) => JSON.stringify(p),
      ttlSeconds: 3600,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: distanceMatrixInputSchema,
  name: "distanceMatrix",
});
