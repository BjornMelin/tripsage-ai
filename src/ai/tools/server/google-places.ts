/**
 * @fileoverview Google Places API POI lookup tool.
 *
 * Provides point-of-interest lookup using Google Places API (New) Text Search
 * with caching and rate limiting. Uses Google Maps Geocoding API for
 * destination-based lookups. Complies with Google Maps Platform policies:
 * - place_id can be stored indefinitely
 * - lat/lng cached for max 30 days
 * - Field masks used to minimize costs
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { lookupPoiInputSchema } from "@ai/tools/schemas/google-places";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { upstreamPlacesSearchResponseSchema } from "@schemas/api";
import { hashInputForCache } from "@/lib/cache/hash";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { postPlacesSearch } from "@/lib/google/client";
import { resolveLocationToLatLng } from "@/lib/google/places-geocoding";

/** Normalized POI result structure matching Google Places API (New) fields. */
type NormalizedPoi = {
  placeId: string;
  name: string;
  lat: number;
  lon: number;
  types?: string[];
  rating?: number;
  userRatingCount?: number;
  formattedAddress?: string;
  photoName?: string;
  url?: string;
};

/**
 * Fetch POIs from Google Places API (New) Text Search.
 *
 * Uses centralized client with retry logic and Zod validation.
 * Returns normalized POI array with place_id, location, and essential fields.
 *
 * @param query Search query (e.g., "restaurants in Tokyo").
 * @param locationBias Optional location bias circle.
 * @param apiKey Google Maps server API key.
 * @returns Promise resolving to normalized POI array.
 */
async function fetchPoisFromPlacesApi(
  query: string,
  locationBias: { lat: number; lon: number; radiusMeters: number } | null,
  apiKey: string
): Promise<NormalizedPoi[]> {
  const body: Record<string, unknown> = {
    maxResultCount: 20,
    textQuery: query,
  };

  if (locationBias) {
    body.locationBias = {
      circle: {
        center: {
          latitude: locationBias.lat,
          longitude: locationBias.lon,
        },
        radius: locationBias.radiusMeters,
      },
    };
  }

  const fieldMask =
    "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos.name,places.types";

  const response = await postPlacesSearch({ apiKey, body, fieldMask });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Google Places API error: ${response.status}. Details: ${errorText.slice(0, 200)}`
    );
  }

  let rawData: unknown;
  try {
    rawData = await response.json();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Failed to parse JSON response from Places API: ${message}`);
  }

  const parseResult = upstreamPlacesSearchResponseSchema.safeParse(rawData);

  if (!parseResult.success) {
    const zodError = parseResult.error.format();
    throw new Error(
      `Invalid response from Google Places API: ${JSON.stringify(zodError)}`
    );
  }

  // Filter and map places with valid coordinates
  const placesWithCoords = parseResult.data.places.filter(
    (
      place
    ): place is typeof place & { location: { latitude: number; longitude: number } } =>
      place.location?.latitude != null && place.location?.longitude != null
  );

  return placesWithCoords.map((place) => ({
    formattedAddress: place.formattedAddress,
    lat: place.location.latitude,
    lon: place.location.longitude,
    name: place.displayName?.text ?? "Unnamed Place",
    photoName: place.photos?.[0]?.name,
    placeId: place.id,
    rating: place.rating,
    types: place.types,
    url: place.id
      ? `https://www.google.com/maps/place/?q=place_id:${place.id}`
      : undefined,
    userRatingCount: place.userRatingCount,
  }));
}

/**
 * Tool for looking up points of interest near a destination or coordinate.
 *
 * Uses Google Places API (New) Text Search with field mask to minimize costs.
 * Returns normalized POI array with place_id, location, and essential fields only.
 *
 * @param params Input parameters (destination, query, lat/lon, radius).
 * @returns Promise resolving to lookup results.
 */
export const lookupPoiContext = createAiTool({
  description:
    "Lookup points of interest near a destination or coordinate using Google Places API.",
  execute: async (params) => {
    const validated = await lookupPoiInputSchema.parseAsync(params);
    let apiKey: string;
    try {
      apiKey = getGoogleMapsServerKey();
    } catch {
      return {
        inputs: validated,
        pois: [],
        provider: "stub",
        status: "success" as const,
      };
    }

    let lat: number;
    let lon: number;
    let searchQuery: string;

    if (typeof validated.lat === "number" && typeof validated.lon === "number") {
      lat = validated.lat;
      lon = validated.lon;
      searchQuery = validated.query ?? `points of interest near ${lat},${lon}`;
    } else if (validated.destination) {
      const coords = await resolveLocationToLatLng(validated.destination);

      if (!coords) {
        return {
          error: "Geocoding not available",
          inputs: validated,
          pois: [],
          provider: "googleplaces",
          status: "error" as const,
        };
      }
      lat = coords.lat;
      lon = coords.lon;
      searchQuery = validated.query ?? `points of interest in ${validated.destination}`;
    } else if (validated.query) {
      const pois = await fetchPoisFromPlacesApi(validated.query, null, apiKey);
      return {
        fromCache: false,
        inputs: validated,
        pois,
        provider: "googleplaces",
        status: "success" as const,
      };
    } else {
      throw new Error("Missing coordinates, destination, or query");
    }

    const pois = await fetchPoisFromPlacesApi(
      searchQuery,
      { lat, lon, radiusMeters: validated.radiusMeters },
      apiKey
    );

    return {
      fromCache: false,
      inputs: validated,
      pois,
      provider: "googleplaces",
      status: "success" as const,
    };
  },
  guardrails: {
    cache: {
      key: (params) =>
        `v1:${hashInputForCache(
          canonicalizeParamsForCache({
            destination: params.destination?.trim().toLowerCase() ?? null,
            lat: params.lat ?? null,
            lon: params.lon ?? null,
            query: params.query?.trim().toLowerCase() ?? null,
            radiusMeters: params.radiusMeters,
          })
        )}`,
      ttlSeconds: 600,
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 20,
      window: "1 m",
    },
  },
  inputSchema: lookupPoiInputSchema,
  name: "lookupPoiContext",
});
