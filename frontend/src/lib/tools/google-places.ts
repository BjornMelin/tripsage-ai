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

import type { ToolCallOptions } from "ai";
import { tool } from "ai";
import { z } from "zod";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Normalized POI result structure matching Google Places API (New) fields.
 */
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
    if (!res.ok) {
      return null;
    }

    const data = (await res.json()) as {
      status?: string;
      results?: Array<{
        geometry?: {
          location?: { lat?: number; lng?: number };
        };
      }>;
    };

    if (data.status !== "OK" || !data.results || data.results.length === 0) {
      return null;
    }

    const firstResult = data.results[0];
    const location = firstResult.geometry?.location;
    if (
      location &&
      typeof location.lat === "number" &&
      typeof location.lng === "number"
    ) {
      return { lat: location.lat, lon: location.lng };
    }

    return null;
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

  const body: {
    textQuery: string;
    maxResultCount?: number;
    locationBias?: {
      circle?: {
        center: { latitude: number; longitude: number };
        radius: number;
      };
    };
  } = {
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

  const data = (await response.json()) as {
    places?: Array<{
      id?: string;
      displayName?: { text?: string };
      formattedAddress?: string;
      location?: { latitude?: number; longitude?: number };
      rating?: number;
      userRatingCount?: number;
      photos?: Array<{ name?: string }>;
      types?: string[];
    }>;
  };

  const pois: NormalizedPoi[] = [];

  for (const place of data.places ?? []) {
    if (!place.id || !place.location) continue;

    const lat = place.location.latitude;
    const lon = place.location.longitude;
    if (typeof lat !== "number" || typeof lon !== "number") continue;

    const poi: NormalizedPoi = {
      formattedAddress: place.formattedAddress,
      lat,
      lon,
      name: place.displayName?.text ?? "Unnamed Place",
      photoName: place.photos?.[0]?.name,
      placeId: place.id,
      rating: place.rating,
      types: place.types,
      userRatingCount: place.userRatingCount,
    };

    if (place.id) {
      poi.url = `https://www.google.com/maps/place/?q=place_id:${place.id}`;
    }

    pois.push(poi);
  }

  return pois;
}

/**
 * Zod input schema for lookup POI context tool.
 *
 * Exported for use in guardrails validation and cache key generation.
 */
export const lookupPoiInputSchema = z
  .object({
    destination: z.string().optional(),
    lat: z.number().optional(),
    lon: z.number().optional(),
    query: z.string().optional(),
    radiusMeters: z.number().int().positive().default(1000),
  })
  .refine(
    (o) =>
      Boolean(o.destination) ||
      Boolean(o.query) ||
      (typeof o.lat === "number" && typeof o.lon === "number"),
    { message: "Provide destination, query, or lat/lon" }
  );

export const lookupPoiContext = tool({
  description:
    "Lookup points of interest near a destination or coordinate using Google Places API.",
  execute: async (params, _callOptions?: ToolCallOptions) => {
    // Validate input at boundary (AI SDK validates, but ensure for direct calls)
    const validatedParams = lookupPoiInputSchema.parse(params);
    return await withTelemetrySpan(
      "tool.googleplaces.lookup",
      {
        attributes: {
          hasCoordinates:
            typeof params.lat === "number" && typeof params.lon === "number",
          hasDestination: Boolean(params.destination),
          hasQuery: Boolean(params.query),
          "tool.name": "lookupPoiContext",
        },
      },
      async () => {
        let apiKey: string;
        try {
          apiKey = getGoogleMapsServerKey();
        } catch {
          // Fallback to stub if API key not configured
          return {
            inputs: validatedParams,
            pois: [],
            provider: "stub",
          } as const;
        }

        let lat: number;
        let lon: number;
        let searchQuery: string;

        if (
          typeof validatedParams.lat === "number" &&
          typeof validatedParams.lon === "number"
        ) {
          lat = validatedParams.lat;
          lon = validatedParams.lon;
          searchQuery =
            validatedParams.query ?? `points of interest near ${lat},${lon}`;
        } else if (validatedParams.destination) {
          // Normalize destination for cache key (Google Maps geocoding)
          const normalizedDestination = validatedParams.destination
            .toLowerCase()
            .trim();
          const geocodeCacheKey = `googleplaces:geocode:${normalizedDestination}`;

          // Check cache for Google Maps geocoding result
          let coords = await getCachedLatLng(geocodeCacheKey);

          // If not cached, geocode with Google Maps and cache the result
          if (!coords) {
            coords = await geocodeDestinationWithGoogleMaps(
              validatedParams.destination,
              apiKey
            );
            if (coords) {
              // Cache Google Maps geocoding result (30 days max per policy)
              await cacheLatLng(geocodeCacheKey, coords, 30 * 24 * 60 * 60);
            }
          }

          if (!coords) {
            return {
              error: "Geocoding not available",
              inputs: validatedParams,
              pois: [],
              provider: "googleplaces",
            } as const;
          }
          lat = coords.lat;
          lon = coords.lon;
          searchQuery =
            validatedParams.query ??
            `points of interest in ${validatedParams.destination}`;
        } else if (validatedParams.query) {
          // Query-only search without location bias
          const pois = await fetchPoisFromPlacesApi(
            validatedParams.query,
            null,
            apiKey
          );
          return {
            fromCache: false,
            inputs: validatedParams,
            pois,
            provider: "googleplaces",
          } as const;
        } else {
          // Should not reach here due to Zod validation, but handle defensively
          throw new Error("Missing coordinates, destination, or query");
        }

        const radiusMeters = validatedParams.radiusMeters ?? 1000;
        // Note: Per Google policy, we cannot cache Places API results except place_id.
        // We'll fetch fresh results each time but cache geocoding results.

        // Fetch from API with location bias
        const pois = await fetchPoisFromPlacesApi(
          searchQuery,
          { lat, lon, radiusMeters },
          apiKey
        );

        return {
          fromCache: false,
          inputs: validatedParams,
          pois,
          provider: "googleplaces",
        } as const;
      }
    );
  },
  inputSchema: lookupPoiInputSchema,
});
