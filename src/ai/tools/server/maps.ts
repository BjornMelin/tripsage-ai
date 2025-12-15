/**
 * @fileoverview Google Maps tools: geocode, distance matrix.
 *
 * Uses centralized client functions with retry logic and Zod validation.
 * Distance matrix migrated from legacy API to Routes API computeRouteMatrix.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { distanceMatrixInputSchema, geocodeInputSchema } from "@ai/tools/schemas/maps";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import {
  upstreamGeocodeResponseSchema,
  upstreamRouteMatrixResponseSchema,
} from "@schemas/api";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { getGeocode, postComputeRouteMatrix } from "@/lib/google/client";

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
 * Uses centralized client with retry logic and Zod validation.
 * Returns array of geocoding results with address, latitude, and longitude.
 *
 * @param address Location address to geocode.
 * @returns Promise resolving to geocoding results.
 */
export const geocode = createAiTool({
  description: "Geocode a location using Google Maps Geocoding API.",
  execute: async ({ address }) => {
    const apiKey = getGmapsKeyOrNull();
    if (!apiKey) throw new Error("gmaps_not_configured");

    const response = await getGeocode({ address, apiKey });
    if (!response.ok) throw new Error(`gmaps_failed:${response.status}`);

    const rawData = await response.json();
    const parseResult = upstreamGeocodeResponseSchema.safeParse(rawData);

    if (!parseResult.success) {
      throw new Error("Invalid response from Geocoding API");
    }

    return parseResult.data.results;
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
 * Geocode an address to lat/lng coordinates.
 * Helper for distanceMatrix tool to convert addresses to waypoints.
 */
async function geocodeAddress(
  address: string,
  apiKey: string
): Promise<{ lat: number; lng: number } | null> {
  const response = await getGeocode({ address, apiKey });
  if (!response.ok) return null;

  const rawData = await response.json();
  const parseResult = upstreamGeocodeResponseSchema.safeParse(rawData);

  if (!parseResult.success || parseResult.data.results.length === 0) {
    return null;
  }

  return parseResult.data.results[0].geometry.location;
}

/**
 * Format duration from "Xs" string to human-readable format.
 */
function formatDuration(durationStr: string | undefined): {
  text: string;
  value: number;
} {
  if (!durationStr) return { text: "0 mins", value: 0 };
  const seconds = Number.parseInt(durationStr.replace("s", ""), 10) || 0;
  const minutes = Math.round(seconds / 60);
  const text = minutes === 1 ? "1 min" : `${minutes} mins`;
  return { text, value: seconds };
}

/**
 * Format distance to human-readable format.
 */
function formatDistance(
  meters: number | undefined,
  units: string
): { text: string; value: number } {
  if (!meters) return { text: "0 m", value: 0 };
  if (units === "imperial") {
    const miles = meters / 1609.344;
    const text =
      miles < 0.1 ? `${Math.round(meters * 3.281)} ft` : `${miles.toFixed(1)} mi`;
    return { text, value: meters };
  }
  const text = meters < 1000 ? `${meters} m` : `${(meters / 1000).toFixed(1)} km`;
  return { text, value: meters };
}

/**
 * Tool for computing distances between origins and destinations.
 *
 * Uses Google Routes API computeRouteMatrix (migrated from deprecated Distance Matrix API).
 * Geocodes addresses to coordinates, computes route matrix, and returns legacy-compatible format.
 *
 * @param origins Array of origin addresses.
 * @param destinations Array of destination addresses.
 * @param units Distance units ("metric" or "imperial").
 * @returns Promise resolving to distance matrix in legacy format for backward compatibility.
 */
export const distanceMatrix = createAiTool({
  description:
    "Compute distances between origins and destinations via Google Routes API.",
  execute: async ({ origins, destinations, units }) => {
    const apiKey = getGmapsKeyOrNull();
    if (!apiKey) throw new Error("gmaps_not_configured");

    // Geocode all origins and destinations to coordinates
    const originCoords = await Promise.all(
      origins.map((addr) => geocodeAddress(addr, apiKey))
    );
    const destCoords = await Promise.all(
      destinations.map((addr) => geocodeAddress(addr, apiKey))
    );

    // Check for geocoding failures
    const failedOrigins = originCoords.indexOf(null);
    const failedDests = destCoords.indexOf(null);

    if (failedOrigins !== -1) {
      throw new Error(`Failed to geocode origin: ${origins[failedOrigins]}`);
    }
    if (failedDests !== -1) {
      throw new Error(`Failed to geocode destination: ${destinations[failedDests]}`);
    }

    // Type-narrow to non-null after validation
    const validOriginCoords = originCoords as { lat: number; lng: number }[];
    const validDestCoords = destCoords as { lat: number; lng: number }[];

    // Build Routes API waypoints
    const routeOrigins = validOriginCoords.map((coord) => ({
      waypoint: {
        location: { latLng: { latitude: coord.lat, longitude: coord.lng } },
      },
    }));
    const routeDestinations = validDestCoords.map((coord) => ({
      waypoint: {
        location: { latLng: { latitude: coord.lat, longitude: coord.lng } },
      },
    }));

    // Call Routes API computeRouteMatrix
    const fieldMask = "originIndex,destinationIndex,duration,distanceMeters,status";
    const response = await postComputeRouteMatrix({
      apiKey,
      body: {
        destinations: routeDestinations,
        origins: routeOrigins,
        travelMode: "DRIVE",
      },
      fieldMask,
    });

    if (!response.ok) {
      throw new Error(`Routes API failed: ${response.status}`);
    }

    const rawData = await response.json();
    const parseResult = upstreamRouteMatrixResponseSchema.safeParse(rawData);

    if (!parseResult.success) {
      throw new Error("Invalid response from Routes API");
    }

    // Transform Routes API response to legacy Distance Matrix format
    const entries = parseResult.data;
    const rows = origins.map((_, originIdx) => ({
      elements: destinations.map((_, destIdx) => {
        const entry = entries.find(
          (e) => e.originIndex === originIdx && e.destinationIndex === destIdx
        );
        if (!entry || entry.status?.code !== 0) {
          return { status: "ZERO_RESULTS" };
        }
        return {
          distance: formatDistance(entry.distanceMeters, units),
          duration: formatDuration(entry.duration),
          status: "OK",
        };
      }),
    }));

    // Return legacy-compatible format (snake_case for backward compatibility)
    return {
      // biome-ignore lint/style/useNamingConvention: legacy Distance Matrix API format
      destination_addresses: destinations,
      // biome-ignore lint/style/useNamingConvention: legacy Distance Matrix API format
      origin_addresses: origins,
      rows,
      status: "OK",
    };
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
