/**
 * @fileoverview Shared place id normalization helpers for trips.
 */

/**
 * Strips the "places/" prefix from a Google Places resource name if present.
 *
 * @param placeId - The place ID or resource name (e.g., "places/ChIJ..." or "ChIJ...").
 * @returns The normalized place ID without the prefix.
 */
export function normalizePlaceIdForStorage(placeId: string): string {
  return placeId.startsWith("places/") ? placeId.slice("places/".length) : placeId;
}
