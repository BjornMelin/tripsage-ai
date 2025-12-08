/**
 * @fileoverview Shared utilities for Google Places API integration.
 *
 * Provides normalization and cache key helpers for Places queries.
 */

import "server-only";

import { hashInputForCache } from "@/lib/cache/hash";

/**
 * Normalizes a text query for Google Places search.
 *
 * Trims whitespace, lowercases, and collapses multiple spaces into one.
 * Used consistently across geocoding and enrichment to ensure cache hits.
 *
 * @param text - Raw text query (e.g., "New York, NY" or hotel name/address).
 * @returns Normalized query string.
 */
export function normalizePlacesTextQuery(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, " ");
}

/**
 * Builds a hashed cache key for geocoding queries.
 *
 * Uses SHA-256 hash to avoid exposing raw location strings in Redis keys.
 *
 * @param normalizedQuery - Normalized location query string.
 * @returns Cache key like "googleplaces:geocode:<hash>".
 */
export function buildGeocodeCacheKey(normalizedQuery: string): string {
  const hash = hashInputForCache(normalizedQuery);
  return `googleplaces:geocode:${hash}`;
}

/**
 * Builds a hashed cache key for query-to-place-id mappings.
 *
 * Uses SHA-256 hash to avoid exposing raw search queries in Redis keys.
 * This mapping stores only place_id (policy-compliant).
 *
 * @param normalizedQuery - Normalized search query string.
 * @returns Cache key like "places:q2id:<hash>".
 */
export function buildQueryToPlaceIdKey(normalizedQuery: string): string {
  const hash = hashInputForCache(normalizedQuery);
  return `places:q2id:${hash}`;
}
