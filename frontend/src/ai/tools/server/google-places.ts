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
import { getGoogleMapsServerKey } from "@/lib/env/server";
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
 * Uses Text Search (New) with field mask to minimize costs. Returns normalized
 * POI array with place_id, location, and essential fields only.
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
  const url = "https://places.googleapis.com/v1/places:searchText";
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

  const response = await fetch(url, {
    body: JSON.stringify(body),
    headers: {
      "Content-Type": "application/json",
      "X-Goog-Api-Key": apiKey,
      "X-Goog-FieldMask": fieldMask,
    },
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Google Places API error: ${response.status}`);
  }

  const data = await response.json();
  // biome-ignore lint/suspicious/noExplicitAny: Google API response
  return (data.places ?? []).map((place: any) => ({
    formattedAddress: place.formattedAddress,
    lat: place.location?.latitude,
    lon: place.location?.longitude,
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
      key: (params) => JSON.stringify(params),
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
