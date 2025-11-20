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
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";

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
 * Geocode a destination name to coordinates using Google Maps Geocoding API.
 *
 * Uses Google Maps Geocoding API to convert destination strings to coordinates.
 * Returns null if geocoding fails or API key is not configured.
 *
 * @param destination Destination name to geocode.
 * @param apiKey Google Maps server API key.
 * @returns Promise resolving to coordinates or null.
 */
async function geocodeDestinationWithGoogleMaps(
  destination: string,
  apiKey: string
): Promise<{ lat: number; lon: number } | null> {
  try {
    const url = new URL("https://maps.googleapis.com/maps/api/geocode/json");
    url.searchParams.set("address", destination);
    url.searchParams.set("key", apiKey);

    const res = await fetch(url);
    if (!res.ok) return null;

    const data = await res.json();
    if (data.status !== "OK" || !data.results?.[0]?.geometry?.location) return null;

    const { lat, lng } = data.results[0].geometry.location;
    return { lat, lon: lng };
  } catch {
    return null;
  }
}

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
    let apiKey: string;
    try {
      apiKey = getGoogleMapsServerKey();
    } catch {
      return { inputs: params, pois: [], provider: "stub" };
    }

    let lat: number;
    let lon: number;
    let searchQuery: string;

    if (typeof params.lat === "number" && typeof params.lon === "number") {
      lat = params.lat;
      lon = params.lon;
      searchQuery = params.query ?? `points of interest near ${lat},${lon}`;
    } else if (params.destination) {
      const normalizedDestination = params.destination.toLowerCase().trim();
      const geocodeCacheKey = `googleplaces:geocode:${normalizedDestination}`;
      let coords = await getCachedLatLng(geocodeCacheKey);

      if (!coords) {
        coords = await geocodeDestinationWithGoogleMaps(params.destination, apiKey);
        if (coords) {
          await cacheLatLng(geocodeCacheKey, coords, 30 * 24 * 60 * 60);
        }
      }

      if (!coords) {
        return {
          error: "Geocoding not available",
          inputs: params,
          pois: [],
          provider: "googleplaces",
        };
      }
      lat = coords.lat;
      lon = coords.lon;
      searchQuery = params.query ?? `points of interest in ${params.destination}`;
    } else if (params.query) {
      const pois = await fetchPoisFromPlacesApi(params.query, null, apiKey);
      return { fromCache: false, inputs: params, pois, provider: "googleplaces" };
    } else {
      throw new Error("Missing coordinates, destination, or query");
    }

    const pois = await fetchPoisFromPlacesApi(
      searchQuery,
      { lat, lon, radiusMeters: params.radiusMeters },
      apiKey
    );

    return { fromCache: false, inputs: params, pois, provider: "googleplaces" };
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
