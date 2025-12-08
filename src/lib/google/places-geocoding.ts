/**
 * @fileoverview Google Places geocoding helper with policy-compliant caching.
 *
 * Resolves location strings to lat/lng coordinates using Google Places Text Search.
 * Caches results for up to 30 days per Google Maps Platform policy.
 */

import "server-only";

import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { postPlacesSearch } from "@/lib/google/client";
import {
  buildGeocodeCacheKey,
  normalizePlacesTextQuery,
} from "@/lib/google/places-utils";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Field mask for geocoding requests (minimal fields needed for lat/lng).
 */
const PLACES_GEOCODE_FIELD_MASK = "places.id,places.location";

/**
 * Resolves a location string to geographic coordinates.
 *
 * Uses cached results when available to reduce API calls. Caches successful
 * lookups for 30 days per Google Maps Platform policy.
 *
 * @param location - Location string to geocode (e.g., "New York, NY").
 * @returns Coordinates object with lat/lon, or null if location not found or API unavailable.
 */
export async function resolveLocationToLatLng(
  location: string
): Promise<{ lat: number; lon: number } | null> {
  const normalized = normalizePlacesTextQuery(location);
  const cacheKey = buildGeocodeCacheKey(normalized);

  const cached = await getCachedLatLng(cacheKey);
  if (cached) {
    return cached;
  }

  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    return null;
  }

  const response = await withTelemetrySpan(
    "google.places.geocode",
    {
      attributes: { location: normalized },
      redactKeys: ["location"],
    },
    async () =>
      await postPlacesSearch({
        apiKey,
        body: { maxResultCount: 1, textQuery: location },
        fieldMask: PLACES_GEOCODE_FIELD_MASK,
      })
  );

  if (!response.ok) {
    return null;
  }

  const data = await response.json();
  const place = (data.places ?? [])[0];
  const coords =
    place?.location?.latitude !== undefined && place?.location?.longitude !== undefined
      ? { lat: place.location.latitude, lon: place.location.longitude }
      : null;

  if (coords) {
    await cacheLatLng(cacheKey, coords, 30 * 24 * 60 * 60);
  }

  return coords;
}
