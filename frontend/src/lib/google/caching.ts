/**
 * @fileoverview Google Maps Platform caching utilities with compliance enforcement.
 *
 * Enforces Google Maps Platform policies:
 * - place_id can be stored indefinitely
 * - lat/lng can be cached for max 30 days (2592000 seconds)
 * - Other Places content must not be persisted
 */

import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

/**
 * Maximum TTL for cached latitude/longitude values per Google Maps Platform policy.
 *
 * Policy: "Customer may temporarily cache latitude and longitude values from
 * the Places API for up to 30 consecutive calendar days."
 */
const MAX_LAT_LNG_TTL_SECONDS = 30 * 24 * 60 * 60; // 30 days = 2592000 seconds

/**
 * Cache a place_id value indefinitely (policy-compliant).
 *
 * Place IDs are exempt from caching restrictions and can be stored indefinitely.
 *
 * @param key Cache key (should include "place_id" prefix).
 * @param placeId Place ID value to cache.
 */
export async function cachePlaceId(key: string, placeId: string): Promise<void> {
  await setCachedJson(key, placeId);
}

/**
 * Retrieve a cached place_id value.
 *
 * @param key Cache key.
 * @returns Cached place ID or null if not found.
 */
export async function getCachedPlaceId(key: string): Promise<string | null> {
  return await getCachedJson<string>(key);
}

/**
 * Cache latitude/longitude coordinates with policy-compliant TTL.
 *
 * Enforces 30-day maximum TTL per Google Maps Platform policy. If provided
 * TTL exceeds maximum, it is capped to 30 days.
 *
 * @param key Cache key (should include "lat_lng" or "geocode" prefix).
 * @param coords Coordinates object with lat and lon.
 * @param ttlSeconds Requested TTL in seconds (will be capped to 30 days max).
 */
export async function cacheLatLng(
  key: string,
  coords: { lat: number; lon: number },
  ttlSeconds?: number
): Promise<void> {
  const cappedTtl = ttlSeconds
    ? Math.min(ttlSeconds, MAX_LAT_LNG_TTL_SECONDS)
    : MAX_LAT_LNG_TTL_SECONDS;
  await setCachedJson(key, coords, cappedTtl);
}

/**
 * Retrieve cached latitude/longitude coordinates.
 *
 * @param key Cache key.
 * @returns Cached coordinates or null if not found.
 */
export async function getCachedLatLng(
  key: string
): Promise<{ lat: number; lon: number } | null> {
  return await getCachedJson<{ lat: number; lon: number }>(key);
}

/**
 * Maximum allowed TTL for lat/lng caching (30 days in seconds).
 */
export const MAX_LAT_LNG_CACHE_TTL = MAX_LAT_LNG_TTL_SECONDS;
