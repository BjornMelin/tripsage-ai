/**
 * @fileoverview Google Places enrichment helper with policy-compliant caching.
 *
 * Enriches hotel-like listings with Google Places data. Only caches place_id
 * (indefinite) and lat/lng (30 days max) per Google Maps Platform policy.
 * Full place details are always fetched fresh and never persisted.
 */

import "server-only";

import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, cachePlaceId, getCachedPlaceId } from "@/lib/google/caching";
import { getPlaceDetails, postPlacesSearch } from "@/lib/google/client";
import {
  buildGeocodeCacheKey,
  buildQueryToPlaceIdKey,
  normalizePlacesTextQuery,
} from "@/lib/google/places-utils";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Field mask for Places search when finding place_id (minimal fields).
 */
const PLACES_ENRICH_SEARCH_FIELD_MASK = "places.id,places.location";

/**
 * Field mask for Places details (full UI fields).
 */
const PLACES_DETAILS_FIELD_MASK =
  "id,displayName,formattedAddress,location,rating,userRatingCount,internationalPhoneNumber,photos.name,googleMapsUri";

/**
 * Hotel-like listing structure expected for enrichment.
 */
export type HotelLikeListing = {
  hotel?: {
    name?: string;
    address?: {
      cityName?: string;
      lines?: string[];
    };
  };
};

/**
 * Enriches a hotel-like listing with Google Places data.
 *
 * Searches for the property by name and address, then fetches detailed place
 * information. Only caches place_id and lat/lng per Google policy; details
 * are always fetched fresh.
 *
 * @param listing - Accommodation listing with hotel name and address.
 * @returns Enriched listing with place and placeDetails properties, or original listing if enrichment fails.
 */
export async function enrichHotelListingWithPlaces<T extends HotelLikeListing>(
  listing: T
): Promise<T & { place?: unknown; placeDetails?: unknown }> {
  let apiKey: string;
  try {
    apiKey = getGoogleMapsServerKey();
  } catch {
    return listing;
  }

  const name = listing.hotel?.name;
  const address = listing.hotel?.address;
  const query = name
    ? `${name} ${address?.cityName ?? ""} ${(address?.lines ?? []).join(" ")}`
    : undefined;
  if (!query) {
    return listing;
  }

  const normalizedQuery = normalizePlacesTextQuery(query);
  const queryToPlaceIdKey = buildQueryToPlaceIdKey(normalizedQuery);

  // Check for cached place_id mapping (policy-compliant: place_id can be cached indefinitely)
  const cachedPlaceId = await getCachedPlaceId(queryToPlaceIdKey);
  let placeId: string | undefined = cachedPlaceId ?? undefined;

  // If no cached mapping, search for place_id
  if (!placeId) {
    const searchRes = await withTelemetrySpan(
      "google.places.enrich.search",
      { attributes: { query: normalizedQuery }, redactKeys: ["query"] },
      async () =>
        await postPlacesSearch({
          apiKey,
          body: { maxResultCount: 1, textQuery: query },
          fieldMask: PLACES_ENRICH_SEARCH_FIELD_MASK,
        })
    );

    if (!searchRes.ok) {
      return listing;
    }

    const searchData = await searchRes.json();
    const place = (searchData.places ?? [])[0];
    placeId = place?.id;

    if (!placeId) {
      return listing;
    }

    // Cache place_id mapping (indefinite) and lat/lng separately (30 days)
    const coords =
      place?.location?.latitude !== undefined &&
      place?.location?.longitude !== undefined
        ? { lat: place.location.latitude, lon: place.location.longitude }
        : undefined;

    // Cache place_id indefinitely (policy-compliant)
    await cachePlaceId(queryToPlaceIdKey, placeId);

    // Cache lat/lng separately with 30-day TTL (policy-compliant)
    if (coords) {
      const geocodeKey = buildGeocodeCacheKey(normalizedQuery);
      await cacheLatLng(geocodeKey, coords, 30 * 24 * 60 * 60);
    }
  }

  // Always fetch fresh details (never cache full payloads per policy)
  const detailsRes = await withTelemetrySpan(
    "google.places.enrich.details",
    { attributes: { placeId }, redactKeys: [] },
    async () =>
      await getPlaceDetails({
        apiKey,
        fieldMask: PLACES_DETAILS_FIELD_MASK,
        placeId,
      })
  );

  if (!detailsRes.ok) {
    // Return listing with minimal place info if details fetch fails
    return { ...listing, place: { id: placeId } };
  }

  const details = await detailsRes.json();
  const place = { id: placeId };

  // Return enriched listing with fresh details (not cached)
  return { ...listing, place, placeDetails: details };
}
